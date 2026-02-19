"""Fallback tests for voice flow."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator, VoiceAgent
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, voice


class _FailingVoiceService:
    enabled = True

    async def transcribe(self, *, audio_bytes: bytes, filename: str, locale: str = "ko-KR") -> str:
        return ""

    async def synthesize_to_file(
        self,
        *,
        text: str,
        voice_preset: str = "friendly_ko",
        audio_format: str = "mp3",
    ) -> tuple[str, int]:
        return f"/static/assets/fallback_tts.{audio_format}", 10


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "voice_fallback.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.voice_agent = VoiceAgent()
    app.state.voice_service = _FailingVoiceService()
    app.include_router(chat.router, prefix="/api")
    app.include_router(voice.router, prefix="/api")
    return TestClient(app)


def test_voice_turn_returns_text_fallback_message_when_stt_fails(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    res = client.post(
        f"/api/chat/session/{session_id}/voice-turn",
        files={"audio": ("broken.wav", b"", "audio/wav")},
        data={"locale": "ko-KR", "voice_preset": "friendly_ko"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["transcript"] == ""
    assert payload["state"] == "CHAT_COLLECTING"
    assert payload["next_question"].startswith("좋아요.")
    assert "텍스트로 입력" in payload["next_question"]
