"""Tests for voice chat endpoints."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator, VoiceAgent
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, voice


class _FakeVoiceService:
    enabled = True

    async def transcribe(self, *, audio_bytes: bytes, filename: str, locale: str = "ko-KR") -> str:
        return (
            "제품명은 보이스세럼, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
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
        return f"/static/assets/fake_tts.{audio_format}", 1234


class _FakeVoiceServiceFailTranscribe(_FakeVoiceService):
    async def transcribe(self, *, audio_bytes: bytes, filename: str, locale: str = "ko-KR") -> str:
        return ""


def _build_client(tmp_path: Path, *, fail_transcribe: bool = False) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "voice_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.voice_agent = VoiceAgent()
    app.state.voice_service = _FakeVoiceServiceFailTranscribe() if fail_transcribe else _FakeVoiceService()
    app.include_router(chat.router, prefix="/api")
    app.include_router(voice.router, prefix="/api")
    return TestClient(app)


def test_voice_turn_updates_slots_and_reaches_brief_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    voice_res = client.post(
        f"/api/chat/session/{session_id}/voice-turn",
        files={"audio": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
        data={"locale": "ko-KR"},
    )
    assert voice_res.status_code == 200
    payload = voice_res.json()
    assert payload["state"] == "BRIEF_READY"
    assert payload["gate"]["ready"] is True
    assert payload["brief_slots"]["goal"]["weekly_goal"] == "purchase"


def test_assistant_voice_returns_audio_url(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    tts_res = client.post(
        f"/api/chat/session/{session_id}/assistant-voice",
        json={"text": "다음 질문입니다.", "voice_preset": "friendly_ko", "format": "mp3"},
    )
    assert tts_res.status_code == 200
    payload = tts_res.json()
    assert payload["audio_url"].startswith("/static/assets/")
    assert payload["format"] == "mp3"
    assert payload["bytes_size"] == 1234


def test_voice_turn_stream_returns_voice_events(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    stream_res = client.post(
        f"/api/chat/session/{session_id}/voice-turn/stream",
        files={"audio": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
        data={"locale": "ko-KR", "voice_preset": "friendly_ko"},
    )
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"].startswith("text/event-stream")
    assert "event: voice.delta" in stream_res.text
    assert "event: slot.updated" in stream_res.text
    assert "event: planner.delta" in stream_res.text


def test_voice_turn_transcribe_failure_returns_text_fallback(tmp_path: Path) -> None:
    client = _build_client(tmp_path, fail_transcribe=True)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    voice_res = client.post(
        f"/api/chat/session/{session_id}/voice-turn",
        files={"audio": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
        data={"locale": "ko-KR", "voice_preset": "calm_ko"},
    )
    assert voice_res.status_code == 200
    payload = voice_res.json()
    assert payload["transcript"] == ""
    assert payload["state"] == "CHAT_COLLECTING"
    assert payload["next_question"].startswith("천천히 정리해볼게요.")
    assert payload["gate"]["ready"] is False
