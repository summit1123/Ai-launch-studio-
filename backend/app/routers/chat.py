"""Session chat API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.agents import ChatOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionCreateResponse,
    ChatSessionGetResponse,
)

router = APIRouter()


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
    return ChatSessionCreateResponse(
        session_id=session_id,
        state=state,
        mode=request_body.mode,
        locale=request_body.locale,
        brief_slots=brief_slots,
        gate=gate,
        assistant_message=chat_orchestrator.first_question(),
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
        assistant_message = "브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요."
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
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state=turn.state,
        brief_slots=turn.brief_slots,
        completeness=turn.gate.completeness,
    )
    history_repository.append_chat_message(
        session_id=session_id,
        role="assistant",
        content=turn.assistant_message,
    )

    return ChatMessageResponse(
        session_id=session_id,
        state=turn.state,
        assistant_message=turn.assistant_message,
        slot_updates=turn.slot_updates,
        brief_slots=turn.brief_slots,
        gate=turn.gate,
    )
