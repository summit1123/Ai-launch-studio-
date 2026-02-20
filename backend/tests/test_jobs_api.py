"""Tests for asynchronous jobs polling API."""

from __future__ import annotations

import asyncio
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
    MarketerOutput,
    MarketingAssets,
    MDOutput,
    PlannerOutput,
    ResearchOutput,
)
from app.services import MediaJobsService


class _FakeRunOrchestrator:
    async def run(self, request: LaunchRunRequest) -> LaunchPackage:
        await asyncio.sleep(0.05)
        brief = request.brief
        return LaunchPackage(
            request_id="run_async_001",
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
                poster_image_url="/static/assets/poster_async.png",
                video_url="/static/assets/video_async.mp4",
            ),
            risks_and_mitigations=[],
            timeline=[],
        )


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "jobs_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.orchestrator = _FakeRunOrchestrator()
    app.state.media_jobs = MediaJobsService()
    app.include_router(chat.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    return TestClient(app)


def _prepare_brief_ready_session(client: TestClient) -> str:
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]
    msg_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 비동기세럼, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
                "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
                "채널은 인스타와 네이버, 목표는 구매"
            )
        },
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["state"] == "BRIEF_READY"
    return session_id


def test_async_generate_and_poll_job_status(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    session_id = _prepare_brief_ready_session(client)

    gen_res = client.post(f"/api/runs/{session_id}/generate/async")
    assert gen_res.status_code == 202
    payload = gen_res.json()
    job_id = payload["job_id"]
    assert payload["session_id"] == session_id
    assert payload["status"] in {"queued", "running"}

    final_job = None
    for _ in range(40):
        job_res = client.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        final_job = job_res.json()
        if final_job["status"] == "completed":
            break
        time.sleep(0.03)

    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["run_id"] == "run_async_001"

    run_res = client.get("/api/runs/run_async_001")
    assert run_res.status_code == 200
    assert run_res.json()["state"] == "DONE"

    list_res = client.get("/api/jobs", params={"run_id": "run_async_001"})
    assert list_res.status_code == 200
    list_payload = list_res.json()
    assert list_payload["total"] >= 1
    assert any(item["job_id"] == job_id for item in list_payload["items"])


def test_async_generate_rejects_when_gate_not_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    gen_res = client.post(f"/api/runs/{session_id}/generate/async")
    assert gen_res.status_code == 409


def test_job_stream_returns_sse_until_completion(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    session_id = _prepare_brief_ready_session(client)

    gen_res = client.post(f"/api/runs/{session_id}/generate/async")
    assert gen_res.status_code == 202
    job_id = gen_res.json()["job_id"]

    stream_res = client.get(
        f"/api/jobs/{job_id}/stream",
        params={"poll_ms": 120, "timeout_seconds": 5},
    )
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"].startswith("text/event-stream")
    assert "event: job.snapshot" in stream_res.text
    assert "event: job.completed" in stream_res.text
