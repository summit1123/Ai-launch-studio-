"""Tests for chat session API endpoints."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.routers import chat


def _build_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "chat_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.include_router(chat.router, prefix="/api")
    return TestClient(app)


def test_chat_session_create_get_and_message_flow(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    assert create_res.status_code == 200
    create_payload = create_res.json()
    session_id = create_payload["session_id"]
    assert create_payload["state"] == "CHAT_COLLECTING"
    assert session_id.startswith("sess_")

    get_res = client.get(f"/api/chat/session/{session_id}")
    assert get_res.status_code == 200
    get_payload = get_res.json()
    assert get_payload["state"] == "CHAT_COLLECTING"
    assert get_payload["gate"]["ready"] is False

    message_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 런치부스터, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건, "
                "가격은 29000원, 타겟은 20대 여성, 이유는 트러블 진정, "
                "채널은 인스타와 네이버, 목표는 구매, 영상 길이는 8초"
            )
        },
    )
    assert message_res.status_code == 200
    message_payload = message_res.json()
    assert message_payload["state"] == "BRIEF_READY"
    assert message_payload["gate"]["ready"] is True
    assert message_payload["brief_slots"]["goal"]["weekly_goal"] == "purchase"
    assert message_payload["brief_slots"]["goal"]["video_seconds"] == 10
    assert "10초" in message_payload["assistant_message"]

    get_after_res = client.get(f"/api/chat/session/{session_id}")
    assert get_after_res.status_code == 200
    get_after_payload = get_after_res.json()
    assert get_after_payload["state"] == "BRIEF_READY"


def test_chat_message_stream_returns_sse_events(tmp_path: Path) -> None:
    client = _build_client(tmp_path)

    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    stream_res = client.post(
        f"/api/chat/session/{session_id}/message/stream",
        json={"message": "제품명은 런치부스터"},
    )
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"].startswith("text/event-stream")
    assert "event: planner.delta" in stream_res.text
    assert "event: run.completed" in stream_res.text
