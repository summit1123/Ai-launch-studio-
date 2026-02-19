"""Tests for session run generation endpoints."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, runs
from app.schemas import (
    BizPlanningOutput,
    DevOutput,
    LaunchPackage,
    LaunchRunRequest,
    MarketerOutput,
    MarketingAssets,
    MDOutput,
    PlannerOutput,
    ResearchOutput,
)


class _FakeRunOrchestrator:
    async def run(self, request: LaunchRunRequest) -> LaunchPackage:
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
                poster_image_url="/static/assets/poster_test.png",
                video_url="https://cdn.example.com/video_test.mp4",
            ),
            risks_and_mitigations=[],
            timeline=[],
        )


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "runs_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.orchestrator = _FakeRunOrchestrator()
    app.include_router(chat.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
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
                "채널은 인스타와 네이버, 목표는 구매"
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

    repo: SQLiteHistoryRepository = client.app.state.history_repository
    media_assets = repo.list_media_assets(run_id="run_test_001")
    assert len(media_assets) == 2
    assert {item.asset_type for item in media_assets} == {"poster_image", "video"}


def test_generate_run_rejects_when_gate_not_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 409
