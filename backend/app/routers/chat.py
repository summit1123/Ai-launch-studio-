"""Session chat API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    BriefSlots,
    ChatState,
    GateStatus,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    ChatSessionGetResponse,
    ProductImageUploadResponse,
    SlotUpdate,
)

router = APIRouter()
COLLECTABLE_STATES = {"CHAT_COLLECTING", "BRIEF_READY"}


def _sse_event(event_type: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _chunk_planner_text(text: str, *, chunk_size: int = 6) -> list[str]:
    content = text or ""
    if not content:
        return []
    if len(content) <= chunk_size:
        return [content]

    chunks: list[str] = []
    buffer = ""
    soft_break_len = max(8, chunk_size // 2)
    sentence_breaks = {".", "!", "?", "。", "\n"}

    for char in content:
        buffer += char
        should_flush = False
        if len(buffer) >= chunk_size and char in {" ", ",", "·"}:
            should_flush = True
        elif len(buffer) >= soft_break_len and char in sentence_breaks:
            should_flush = True
        elif len(buffer) >= chunk_size + 6:
            should_flush = True

        if should_flush:
            chunks.append(buffer)
            buffer = ""

    if buffer:
        chunks.append(buffer)

    return [chunk for chunk in chunks if chunk]


async def _stream_planner_delta_events(text: str) -> AsyncIterator[str]:
    chunks = _chunk_planner_text(text)
    if not chunks:
        return
    if len(chunks) == 1:
        yield _sse_event("planner.delta", {"text": chunks[0]})
        return

    # 첫 토큰이 너무 "툭" 튀지 않도록 아주 짧은 워밍업 지연을 둔다.
    await asyncio.sleep(0.08)

    punctuation_breaks = {".", "!", "?", ",", "。", "!", "?", "\n"}
    for chunk in chunks:
        yield _sse_event("planner.delta", {"text": chunk})
        # 기본 지연 + 청크 길이 비례 지연으로 사람 타이핑처럼 속도를 맞춘다.
        delay = 0.05 + (0.013 * len(chunk))
        if chunk and chunk[-1] in punctuation_breaks:
            delay += 0.09
        await asyncio.sleep(delay)


async def _compose_assistant_message(
    request: Request,
    *,
    fallback_message: str,
    state: ChatState,
    gate: GateStatus,
    brief_slots: BriefSlots,
    user_message: str,
    chat_history: list[dict[str, str]] | None = None,
    locale: str,
) -> str:
    dialogue_service = getattr(request.app.state, "onboarding_dialogue_service", None)
    if dialogue_service is None:
        return fallback_message
    return await dialogue_service.compose_reply(
        fallback_message=fallback_message,
        state=state,
        gate=gate,
        brief_slots=brief_slots,
        user_message=user_message,
        chat_history=chat_history,
        locale=locale,
    )


async def _collect_external_slot_updates(
    request: Request,
    *,
    history_repository: SQLiteHistoryRepository,
    chat_orchestrator: ChatOrchestrator,
    session_id: str,
    state: ChatState,
    gate: GateStatus,
    brief_slots: BriefSlots,
    user_message: str,
    chat_history: list[dict[str, str]] | None = None,
    locale: str,
) -> list[SlotUpdate]:
    dialogue_service = getattr(request.app.state, "onboarding_dialogue_service", None)
    if dialogue_service is None:
        return []
    if not getattr(dialogue_service, "enabled", False):
        return []

    history = chat_history or history_repository.list_chat_messages(session_id=session_id, limit=24)
    raw_updates = await dialogue_service.propose_slot_updates(
        state=state,
        gate=gate,
        brief_slots=brief_slots,
        user_message=user_message,
        chat_history=history,
        locale=locale,
    )
    return chat_orchestrator.prepare_external_updates(
        updates=raw_updates,
        slots=brief_slots,
        user_message=user_message,
    )


@router.post("/chat/session", response_model=ChatSessionCreateResponse)
async def create_chat_session(
    request_body: ChatSessionCreateRequest,
    request: Request,
) -> ChatSessionCreateResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator

    session_id = chat_orchestrator.new_session_id()
    brief_slots = chat_orchestrator.empty_slots()
    gate = chat_orchestrator.evaluate_gate(brief_slots)
    state = "CHAT_COLLECTING"
    history_repository.create_chat_session(
        session_id=session_id,
        mode=request_body.mode,
        locale=request_body.locale,
        state=state,
        brief_slots=brief_slots,
        completeness=gate.completeness,
    )
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=chat_orchestrator.first_question(),
        state=state,
        gate=gate,
        brief_slots=brief_slots,
        user_message="",
        chat_history=[],
        locale=request_body.locale,
    )
    return ChatSessionCreateResponse(
        session_id=session_id,
        state=state,
        mode=request_body.mode,
        locale=request_body.locale,
        brief_slots=brief_slots,
        gate=gate,
        assistant_message=assistant_message,
    )


@router.get("/chat/session/{session_id}", response_model=ChatSessionGetResponse)
async def get_chat_session(session_id: str, request: Request) -> ChatSessionGetResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    gate = chat_orchestrator.evaluate_gate(record.brief_slots)
    return ChatSessionGetResponse(
        session_id=record.session_id,
        state=record.state,
        mode=record.mode,
        locale=record.locale,
        brief_slots=record.brief_slots,
        gate=gate,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


@router.post("/chat/session/{session_id}/message", response_model=ChatMessageResponse)
async def post_chat_message(
    session_id: str,
    request_body: ChatMessageRequest,
    request: Request,
) -> ChatMessageResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    user_message = request_body.message.strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="message must not be blank")

    history_repository.append_chat_message(
        session_id=session_id,
        role="user",
        content=user_message,
    )

    if record.state not in COLLECTABLE_STATES:
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        chat_history = history_repository.list_chat_messages(session_id=session_id, limit=24)
        assistant_message = await _compose_assistant_message(
            request,
            fallback_message="브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요.",
            state=record.state,
            gate=gate,
            brief_slots=record.brief_slots,
            user_message=user_message,
            chat_history=chat_history,
            locale=record.locale,
        )
        history_repository.append_chat_message(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
        )
        return ChatMessageResponse(
            session_id=session_id,
            state=record.state,
            assistant_message=assistant_message,
            slot_updates=[],
            brief_slots=record.brief_slots,
            gate=gate,
        )

    current_gate = chat_orchestrator.evaluate_gate(record.brief_slots)
    chat_history = history_repository.list_chat_messages(session_id=session_id, limit=24)
    external_updates = await _collect_external_slot_updates(
        request,
        history_repository=history_repository,
        chat_orchestrator=chat_orchestrator,
        session_id=session_id,
        state=record.state,
        gate=current_gate,
        brief_slots=record.brief_slots,
        user_message=user_message,
        chat_history=chat_history,
        locale=record.locale,
    )
    turn = chat_orchestrator.process_turn(
        message=user_message,
        slots=record.brief_slots,
        external_updates=external_updates,
    )
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=turn.assistant_message,
        state=turn.state,
        gate=turn.gate,
        brief_slots=turn.brief_slots,
        user_message=user_message,
        chat_history=chat_history,
        locale=record.locale,
    )
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state=turn.state,
        brief_slots=turn.brief_slots,
        completeness=turn.gate.completeness,
    )
    history_repository.append_chat_message(
        session_id=session_id,
        role="assistant",
        content=assistant_message,
    )

    return ChatMessageResponse(
        session_id=session_id,
        state=turn.state,
        assistant_message=assistant_message,
        slot_updates=turn.slot_updates,
        brief_slots=turn.brief_slots,
        gate=turn.gate,
    )


@router.post("/chat/session/{session_id}/message/stream")
async def post_chat_message_stream(
    session_id: str,
    request_body: ChatMessageRequest,
    request: Request,
) -> StreamingResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    user_message = request_body.message.strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="message must not be blank")

    history_repository.append_chat_message(
        session_id=session_id,
        role="user",
        content=user_message,
    )

    if record.state not in COLLECTABLE_STATES:
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        chat_history = history_repository.list_chat_messages(session_id=session_id, limit=24)
        assistant_message = await _compose_assistant_message(
            request,
            fallback_message="브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요.",
            state=record.state,
            gate=gate,
            brief_slots=record.brief_slots,
            user_message=user_message,
            chat_history=chat_history,
            locale=record.locale,
        )
        history_repository.append_chat_message(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
        )

        async def _ready_stream() -> AsyncIterator[str]:
            yield _sse_event(
                "stage.changed",
                {"state": record.state},
            )
            async for planner_event in _stream_planner_delta_events(assistant_message):
                yield planner_event
            yield _sse_event(
                "run.completed",
                {"state": record.state, "gate": gate.model_dump()},
            )

        return StreamingResponse(
            _ready_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    current_gate = chat_orchestrator.evaluate_gate(record.brief_slots)
    chat_history = history_repository.list_chat_messages(session_id=session_id, limit=24)
    external_updates = await _collect_external_slot_updates(
        request,
        history_repository=history_repository,
        chat_orchestrator=chat_orchestrator,
        session_id=session_id,
        state=record.state,
        gate=current_gate,
        brief_slots=record.brief_slots,
        user_message=user_message,
        chat_history=chat_history,
        locale=record.locale,
    )
    turn = chat_orchestrator.process_turn(
        message=user_message,
        slots=record.brief_slots,
        external_updates=external_updates,
    )
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=turn.assistant_message,
        state=turn.state,
        gate=turn.gate,
        brief_slots=turn.brief_slots,
        user_message=user_message,
        chat_history=chat_history,
        locale=record.locale,
    )
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state=turn.state,
        brief_slots=turn.brief_slots,
        completeness=turn.gate.completeness,
    )
    history_repository.append_chat_message(
        session_id=session_id,
        role="assistant",
        content=assistant_message,
    )

    async def _event_stream() -> AsyncIterator[str]:
        if turn.slot_updates:
            yield _sse_event(
                "slot.updated",
                {"slot_updates": [slot.model_dump() for slot in turn.slot_updates]},
            )
        async for planner_event in _stream_planner_delta_events(assistant_message):
            yield planner_event
        if turn.state != record.state:
            yield _sse_event(
                "stage.changed",
                {"from": record.state, "to": turn.state},
            )
        if turn.gate.ready:
            yield _sse_event("gate.ready", turn.gate.model_dump())
        yield _sse_event(
            "run.completed",
            {"state": turn.state, "gate": turn.gate.model_dump()},
        )

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat/session/{session_id}/product-image",
    response_model=ProductImageUploadResponse,
)
async def upload_product_image(
    session_id: str,
    request: Request,
    image: UploadFile = File(...),
    note: str = Form(default=""),
    locale: str = Form(default="ko-KR"),
) -> ProductImageUploadResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator
    product_image_service = getattr(request.app.state, "product_image_service", None)

    if product_image_service is None:
        raise HTTPException(status_code=503, detail="Product image service is unavailable")

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if record.state not in COLLECTABLE_STATES:
        raise HTTPException(
            status_code=409,
            detail="생성 단계가 시작된 후에는 이미지 업로드를 진행할 수 없습니다.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="image must not be empty")

    original_filename = image.filename or "product.png"
    extension = Path(original_filename).suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=422, detail="Only png/jpg/jpeg/webp images are supported")

    analysis = await product_image_service.save_and_analyze(
        image_bytes=image_bytes,
        filename=original_filename,
        content_type=image.content_type,
        locale=locale,
        user_note=note,
    )

    working_slots = record.brief_slots.model_copy(deep=True)
    slot_updates = chat_orchestrator.apply_image_analysis(
        slots=working_slots,
        image_url=analysis.image_url,
        image_summary=analysis.image_summary,
        inferred_category=analysis.category,
        inferred_features=analysis.features,
    )
    gate = chat_orchestrator.evaluate_gate(working_slots)
    state = "BRIEF_READY" if gate.ready else "CHAT_COLLECTING"
    fallback_message = chat_orchestrator.compose_message_from_updates(
        slot_updates=slot_updates,
        gate=gate,
        slots=working_slots,
    )
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=fallback_message,
        state=state,
        gate=gate,
        brief_slots=working_slots,
        user_message=f"이미지 업로드 노트: {note.strip()}",
        chat_history=history_repository.list_chat_messages(session_id=session_id, limit=24),
        locale=locale,
    )

    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state=state,
        brief_slots=working_slots,
        completeness=gate.completeness,
    )
    user_content = f"[이미지 업로드] {original_filename}"
    if note.strip():
        user_content = f"{user_content} / 노트: {note.strip()}"
    history_repository.append_chat_message(session_id=session_id, role="user", content=user_content)
    history_repository.append_chat_message(
        session_id=session_id,
        role="assistant",
        content=assistant_message,
    )

    return ProductImageUploadResponse(
        session_id=session_id,
        state=state,
        image_url=analysis.image_url,
        image_summary=analysis.image_summary,
        next_question=assistant_message,
        slot_updates=slot_updates,
        brief_slots=working_slots,
        gate=gate,
    )
