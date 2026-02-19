"""End-to-end tests for session-based orchestrator pipeline."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator, VoiceAgent
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, runs, voice
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


class _FakeVoiceService:
    enabled = True

    async def transcribe(self, *, audio_bytes: bytes, filename: str, locale: str = "ko-KR") -> str:
        return (
            "제품명은 이투이세럼, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
            "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
            "채널은 인스타와 네이버, 목표는 구매"
        )

    async def synthesize_to_file(
        self,
        *,
        text: str,
        voice_preset: str = "friendly_ko",
        audio_format: str = "mp3",
    ) -> tuple[str, int]:
        return f"/static/assets/e2e_tts.{audio_format}", 234


class _FakeRunOrchestrator:
    async def run(self, request: LaunchRunRequest) -> LaunchPackage:
        brief = request.brief
        return LaunchPackage(
            request_id="e2e_run_001",
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
                poster_image_url="/static/assets/poster_e2e.png",
                video_url="/static/assets/video_e2e.mp4",
            ),
            risks_and_mitigations=[],
            timeline=[],
        )


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "orchestrator_e2e.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.voice_agent = VoiceAgent()
    app.state.voice_service = _FakeVoiceService()
    app.state.orchestrator = _FakeRunOrchestrator()
    app.include_router(chat.router, prefix="/api")
    app.include_router(voice.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    return TestClient(app)


def test_text_e2e_pipeline_completes_to_done(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]
    msg_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 이투이세럼, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
                "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
                "채널은 인스타와 네이버, 목표는 구매"
            )
        },
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["state"] == "BRIEF_READY"

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 200
    assert gen_res.json()["state"] == "DONE"

    run_res = client.get("/api/runs/e2e_run_001")
    assert run_res.status_code == 200
    assert run_res.json()["state"] == "DONE"


def test_voice_e2e_pipeline_completes_to_done(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]
    voice_res = client.post(
        f"/api/chat/session/{session_id}/voice-turn",
        files={"audio": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
        data={"locale": "ko-KR", "voice_preset": "friendly_ko"},
    )
    assert voice_res.status_code == 200
    assert voice_res.json()["state"] == "BRIEF_READY"

    gen_res = client.post(f"/api/runs/{session_id}/generate")
    assert gen_res.status_code == 200
    assert gen_res.json()["state"] == "DONE"
