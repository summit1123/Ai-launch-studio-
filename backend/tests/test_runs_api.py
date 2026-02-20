"""Tests for session run generation endpoints."""

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, jobs, runs
from app.schemas import (
    BizPlanningOutput,
    DevOutput,
    LaunchPackage,
    LaunchRunRequest,
    MarketingAssets,
    MarketerOutput,
    MDOutput,
    PlannerOutput,
    ResearchOutput,
)
from app.services import MediaJobsService


class _FakeRunOrchestrator:
    async def run(
        self,
        request: LaunchRunRequest,
        *,
        include_media: bool = True,
    ) -> LaunchPackage:
        brief = request.brief
        return LaunchPackage(
            request_id="run_test_001",
            brief=brief,
            research_summary=ResearchOutput(summary="research"),
            product_strategy=MDOutput(summary="md"),
            technical_plan=DevOutput(summary="dev"),
            launch_plan=PlannerOutput(summary="planner"),
            campaign_strategy=MarketerOutput(summary="marketer"),
            budget_and_kpi=BizPlanningOutput(summary="biz"),
            marketing_assets=MarketingAssets(
                video_script="video",
                poster_brief="poster",
                product_copy="copy",
                poster_image_url="/static/assets/poster_test.png" if include_media else None,
                video_url="https://cdn.example.com/video_test.mp4" if include_media else None,
            ),
            risks_and_mitigations=[],
            timeline=[],
        )

    async def generate_media_assets(self, package: LaunchPackage) -> MarketingAssets:
        return package.marketing_assets.model_copy(
            update={
                "poster_image_url": "/static/assets/poster_test_assets.png",
                "video_url": "https://cdn.example.com/video_test_assets.mp4",
            }
        )


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "runs_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.orchestrator = _FakeRunOrchestrator()
    app.state.media_jobs = MediaJobsService()
    app.include_router(chat.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    return TestClient(app)


def test_generate_and_get_run_from_session(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]
    msg_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 런치부스터, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
                "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
                "채널은 인스타와 네이버, 목표는 구매, 영상 길이는 8초"
            )
        },
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["state"] == "BRIEF_READY"

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 200
    gen_payload = gen_res.json()
    assert gen_payload["run_id"] == "run_test_001"
    assert gen_payload["state"] == "DONE"

    get_res = client.get("/api/runs/run_test_001")
    assert get_res.status_code == 200
    get_payload = get_res.json()
    assert get_payload["state"] == "DONE"
    assert get_payload["package"]["request_id"] == "run_test_001"
    assert get_payload["package"]["brief"]["video_seconds"] == 8
    assert get_payload["package"]["marketing_assets"]["poster_image_url"] == "/static/assets/poster_test.png"
    assert get_payload["package"]["marketing_assets"]["video_url"] == "https://cdn.example.com/video_test.mp4"

    repo: SQLiteHistoryRepository = client.app.state.history_repository
    media_assets = repo.list_media_assets(run_id="run_test_001")
    assert len(media_assets) == 2


def test_generate_assets_after_report_generation(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]
    msg_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 런치부스터, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
                "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
                "채널은 인스타와 네이버, 목표는 구매, 영상 길이는 8초"
            )
        },
    )
    assert msg_res.status_code == 200

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 200
    run_id = gen_res.json()["run_id"]

    assets_job_res = client.post(f"/api/runs/{run_id}/assets/generate/async")
    assert assets_job_res.status_code == 202
    job_id = assets_job_res.json()["job_id"]

    final_status = None
    for _ in range(40):
        job_res = client.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        final_status = job_res.json()
        if final_status["status"] == "completed":
            break
        time.sleep(0.03)

    assert final_status is not None
    assert final_status["status"] == "completed"
    assert final_status["run_id"] == run_id

    assets_res = client.get(f"/api/runs/{run_id}/assets")
    assert assets_res.status_code == 200
    assets_payload = assets_res.json()
    assert assets_payload["poster_image_url"] == "/static/assets/poster_test_assets.png"
    assert assets_payload["video_url"] == "https://cdn.example.com/video_test_assets.mp4"
    assert len(assets_payload["items"]) == 2


def test_generate_run_rejects_when_gate_not_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 409


def test_generate_run_preserves_product_image_context(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    chat_orchestrator: ChatOrchestrator = client.app.state.chat_orchestrator
    slots = chat_orchestrator.empty_slots()
    slots.product.name = "런치부스터"
    slots.product.category = "스킨케어"
    slots.product.features = ["저자극", "빠른흡수", "비건"]
    slots.product.price_band = "premium"
    slots.product.image_url = "/static/assets/product_ref_sample.png"
    slots.product.image_context = "민트톤 병 패키지, 은은한 로고, 프리미엄 스킨케어 무드"
    slots.target.who = "20대 여성"
    slots.target.why = "트러블 진정"
    slots.channel.channels = ["Instagram", "YouTube"]
    slots.goal.weekly_goal = "purchase"

    gate = chat_orchestrator.evaluate_gate(slots)
    assert gate.ready is True

    repo: SQLiteHistoryRepository = client.app.state.history_repository
    repo.update_chat_state_and_slots(
        session_id=session_id,
        state="BRIEF_READY",
        brief_slots=slots,
        completeness=gate.completeness,
    )

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 200

    run_res = client.get("/api/runs/run_test_001")
    assert run_res.status_code == 200
    brief = run_res.json()["package"]["brief"]
    assert brief["product_image_url"] == "/static/assets/product_ref_sample.png"
    assert "민트톤" in brief["product_image_context"]
