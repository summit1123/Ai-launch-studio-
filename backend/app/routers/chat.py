"""Session chat API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
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
)

router = APIRouter()


def _sse_event(event_type: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _compose_assistant_message(
    request: Request,
    *,
    fallback_message: str,
    state: ChatState,
    gate: GateStatus,
    brief_slots: BriefSlots,
    user_message: str,
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
        locale=locale,
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

    if record.state != "CHAT_COLLECTING":
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        assistant_message = await _compose_assistant_message(
            request,
            fallback_message="브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요.",
            state=record.state,
            gate=gate,
            brief_slots=record.brief_slots,
            user_message=user_message,
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

    turn = chat_orchestrator.process_turn(message=user_message, slots=record.brief_slots)
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=turn.assistant_message,
        state=turn.state,
        gate=turn.gate,
        brief_slots=turn.brief_slots,
        user_message=user_message,
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

    if record.state != "CHAT_COLLECTING":
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        assistant_message = await _compose_assistant_message(
            request,
            fallback_message="브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요.",
            state=record.state,
            gate=gate,
            brief_slots=record.brief_slots,
            user_message=user_message,
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
            yield _sse_event(
                "planner.delta",
                {"text": assistant_message},
            )
            yield _sse_event(
                "run.completed",
                {"state": record.state, "gate": gate.model_dump()},
            )

        return StreamingResponse(_ready_stream(), media_type="text/event-stream")

    turn = chat_orchestrator.process_turn(message=user_message, slots=record.brief_slots)
    assistant_message = await _compose_assistant_message(
        request,
        fallback_message=turn.assistant_message,
        state=turn.state,
        gate=turn.gate,
        brief_slots=turn.brief_slots,
        user_message=user_message,
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
        yield _sse_event("planner.delta", {"text": assistant_message})
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

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
