"""Tests for chat session API endpoints."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.routers import chat
from app.schemas import SlotUpdate


class _ImageAnalysis:
    def __init__(
        self,
        *,
        image_url: str,
        image_summary: str | None,
        category: str | None,
        features: list[str],
    ) -> None:
        self.image_url = image_url
        self.image_summary = image_summary
        self.category = category
        self.features = features


class _ProductImageServiceStub:
    async def save_and_analyze(
        self,
        *,
        image_bytes: bytes,
        filename: str,
        content_type: str | None,
        locale: str = "ko-KR",
        user_note: str = "",
    ) -> _ImageAnalysis:
        _ = (image_bytes, filename, content_type, locale, user_note)
        return _ImageAnalysis(
            image_url="/static/assets/product_ref_test.png",
            image_summary="민트톤 패키지의 스킨케어 제품",
            category="스킨케어",
            features=["저자극", "빠른 흡수", "비건 포뮬러"],
        )


class _DialogueServiceStub:
    enabled = True

    async def compose_reply(self, **kwargs: object) -> str:
        fallback_message = kwargs.get("fallback_message")
        return str(fallback_message or "")

    async def propose_slot_updates(self, **kwargs: object) -> list[SlotUpdate]:
        _ = kwargs
        return [
            SlotUpdate(path="product.name", value="루미 세럼", confidence=0.95),
            SlotUpdate(path="product.category", value="스킨케어", confidence=0.91),
        ]


class _DialogueLongReplyStub:
    enabled = True

    async def compose_reply(self, **kwargs: object) -> str:
        _ = kwargs
        return (
            "좋아요. 입력한 내용을 기준으로 핵심 정보를 차근차근 정리하고 있어요. "
            "이어서 제품 카테고리와 타겟 고객을 알려주시면 바로 다음 단계로 연결할게요."
        )

    async def propose_slot_updates(self, **kwargs: object) -> list[SlotUpdate]:
        _ = kwargs
        return []


class _DialogueHistoryProbeStub:
    enabled = True

    def __init__(self) -> None:
        self.compose_history: list[dict[str, str]] | None = None
        self.extract_history: list[dict[str, str]] | None = None

    async def compose_reply(self, **kwargs: object) -> str:
        history = kwargs.get("chat_history")
        if isinstance(history, list):
            self.compose_history = history
        fallback_message = kwargs.get("fallback_message")
        return str(fallback_message or "")

    async def propose_slot_updates(self, **kwargs: object) -> list[SlotUpdate]:
        history = kwargs.get("chat_history")
        if isinstance(history, list):
            self.extract_history = history
        return []


def _build_client(tmp_path: Path, *, dialogue_service: object | None = None) -> TestClient:
    app = FastAPI()
    app.state.history_repository = SQLiteHistoryRepository(db_path=str(tmp_path / "chat_api.db"))
    app.state.chat_orchestrator = ChatOrchestrator()
    app.state.product_image_service = _ProductImageServiceStub()
    if dialogue_service is not None:
        app.state.onboarding_dialogue_service = dialogue_service
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
    assert message_payload["brief_slots"]["goal"]["video_seconds"] == 8
    assert "8초" in message_payload["assistant_message"]

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


def test_chat_message_stream_sends_multiple_planner_delta_chunks(tmp_path: Path) -> None:
    client = _build_client(tmp_path, dialogue_service=_DialogueLongReplyStub())
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    stream_res = client.post(
        f"/api/chat/session/{session_id}/message/stream",
        json={"message": "제품명은 런치부스터"},
    )
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"].startswith("text/event-stream")
    assert stream_res.text.count("event: planner.delta") >= 2
    assert "event: run.completed" in stream_res.text


def test_chat_message_accepts_plain_answer_for_current_question(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    message_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={"message": "아이폰"},
    )

    assert message_res.status_code == 200
    payload = message_res.json()
    assert payload["brief_slots"]["product"]["name"] == "아이폰"
    assert "아이폰" in payload["assistant_message"]
    assert "제품 카테고리는 무엇인가요?" in payload["assistant_message"]


def test_chat_message_accepts_numeric_only_price_answer(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    client.post(f"/api/chat/session/{session_id}/message", json={"message": "루미 세럼"})
    client.post(f"/api/chat/session/{session_id}/message", json={"message": "스킨케어"})
    price_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={"message": "39000"},
    )

    assert price_res.status_code == 200
    payload = price_res.json()
    assert payload["brief_slots"]["product"]["price_band"] == "mid"


def test_chat_message_keeps_collecting_after_brief_ready(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    ready_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={
            "message": (
                "제품명은 런치부스터, 카테고리는 스킨케어, 가격은 29000원, "
                "타겟은 20대 여성, 채널은 인스타, 목표는 문의"
            )
        },
    )
    assert ready_res.status_code == 200
    assert ready_res.json()["state"] == "BRIEF_READY"

    enrich_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={"message": "특징은 저자극, 빠른 흡수, 비건 포뮬러"},
    )

    assert enrich_res.status_code == 200
    payload = enrich_res.json()
    assert payload["state"] == "BRIEF_READY"
    assert len(payload["brief_slots"]["product"]["features"]) >= 3
    assert "저자극" in payload["brief_slots"]["product"]["features"]


def test_chat_message_applies_external_dialogue_slot_updates(tmp_path: Path) -> None:
    client = _build_client(tmp_path, dialogue_service=_DialogueServiceStub())
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    message_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={"message": "자연스럽게 알아서 채워줘"},
    )

    assert message_res.status_code == 200
    payload = message_res.json()
    assert payload["brief_slots"]["product"]["name"] == "루미 세럼"
    assert payload["brief_slots"]["product"]["category"] == "스킨케어"


def test_chat_message_passes_recent_history_to_dialogue_service(tmp_path: Path) -> None:
    probe = _DialogueHistoryProbeStub()
    client = _build_client(tmp_path, dialogue_service=probe)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    message_res = client.post(
        f"/api/chat/session/{session_id}/message",
        json={"message": "제품명은 런치부스터"},
    )

    assert message_res.status_code == 200
    assert isinstance(probe.compose_history, list) and probe.compose_history
    assert isinstance(probe.extract_history, list) and probe.extract_history
    assert probe.compose_history[-1]["role"] == "user"
    assert probe.compose_history[-1]["content"] == "제품명은 런치부스터"


def test_chat_product_image_upload_updates_slots(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    create_res = client.post("/api/chat/session", json={"locale": "ko-KR", "mode": "standard"})
    session_id = create_res.json()["session_id"]

    upload_res = client.post(
        f"/api/chat/session/{session_id}/product-image",
        files={"image": ("product.png", b"fake-bytes", "image/png")},
        data={"note": "민트톤 패키지", "locale": "ko-KR"},
    )

    assert upload_res.status_code == 200
    payload = upload_res.json()
    assert payload["state"] == "CHAT_COLLECTING"
    assert payload["brief_slots"]["product"]["image_url"] == "/static/assets/product_ref_test.png"
    assert payload["brief_slots"]["product"]["image_context"] == "민트톤 패키지의 스킨케어 제품"
    assert payload["brief_slots"]["product"]["category"] == "스킨케어"
    assert len(payload["brief_slots"]["product"]["features"]) >= 3
    assert payload["gate"]["ready"] is False
    assert isinstance(payload["next_question"], str) and payload["next_question"].strip()
