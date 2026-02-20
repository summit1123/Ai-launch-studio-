"""Voice chat API."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.agents import ChatOrchestrator, VoiceAgent
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    AssistantVoiceRequest,
    AssistantVoiceResponse,
    VoiceTurnResponse,
)
from app.services import VoiceService

router = APIRouter()
COLLECTABLE_STATES = {"CHAT_COLLECTING", "BRIEF_READY"}


def _sse_event(event_type: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _process_voice_turn(
    session_id: str,
    request: Request,
    audio: UploadFile,
    locale: str,
    voice_preset: str,
) -> tuple[str, VoiceTurnResponse]:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator
    voice_agent: VoiceAgent = request.app.state.voice_agent
    voice_service: VoiceService = request.app.state.voice_service

    if not voice_service.enabled:
        raise HTTPException(status_code=503, detail="Voice service is not configured")

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    previous_state = record.state
    audio_bytes = await audio.read()
    transcript = await voice_service.transcribe(
        audio_bytes=audio_bytes,
        filename=audio.filename or "voice.wav",
        locale=locale,
    )
    if not transcript:
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        fallback_question = voice_agent.format_question(
            question="음성 인식이 어려워요. 이번 답변은 텍스트로 입력해 주세요.",
            preset=voice_preset,
        )
        return previous_state, VoiceTurnResponse(
            session_id=session_id,
            transcript="",
            state=record.state,
            next_question=fallback_question,
            slot_updates=[],
            brief_slots=record.brief_slots,
            gate=gate,
        )

    history_repository.append_chat_message(
        session_id=session_id,
        role="user",
        content=transcript,
    )

    if record.state not in COLLECTABLE_STATES:
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        dialogue_service = getattr(request.app.state, "onboarding_dialogue_service", None)
        assistant_message = "브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요."
        if dialogue_service is not None:
            assistant_message = await dialogue_service.compose_reply(
                fallback_message=assistant_message,
                state=record.state,
                gate=gate,
                brief_slots=record.brief_slots,
                user_message=transcript,
                locale=locale,
            )
        next_question = voice_agent.format_question(
            question=assistant_message,
            preset=voice_preset,
        )
        history_repository.append_chat_message(
            session_id=session_id,
            role="assistant",
            content=next_question,
        )
        return previous_state, VoiceTurnResponse(
            session_id=session_id,
            transcript=transcript,
            state=record.state,
            next_question=next_question,
            slot_updates=[],
            brief_slots=record.brief_slots,
            gate=gate,
        )

    turn = chat_orchestrator.process_turn(message=transcript, slots=record.brief_slots)
    dialogue_service = getattr(request.app.state, "onboarding_dialogue_service", None)
    assistant_message = turn.assistant_message
    if dialogue_service is not None:
        assistant_message = await dialogue_service.compose_reply(
            fallback_message=assistant_message,
            state=turn.state,
            gate=turn.gate,
            brief_slots=turn.brief_slots,
            user_message=transcript,
            locale=locale,
        )
    formatted_question = voice_agent.format_question(
        question=assistant_message,
        preset=voice_preset,
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
        content=formatted_question,
    )
    return previous_state, VoiceTurnResponse(
        session_id=session_id,
        transcript=transcript,
        state=turn.state,
        next_question=formatted_question,
        slot_updates=turn.slot_updates,
        brief_slots=turn.brief_slots,
        gate=turn.gate,
    )


@router.post("/chat/session/{session_id}/voice-turn", response_model=VoiceTurnResponse)
async def post_voice_turn(
    session_id: str,
    request: Request,
    audio: UploadFile = File(...),
    locale: str = Form(default="ko-KR"),
    voice_preset: str = Form(default="cute_ko"),
) -> VoiceTurnResponse:
    _, response = await _process_voice_turn(
        session_id=session_id,
        request=request,
        audio=audio,
        locale=locale,
        voice_preset=voice_preset,
    )
    return response


@router.post("/chat/session/{session_id}/voice-turn/stream")
async def post_voice_turn_stream(
    session_id: str,
    request: Request,
    audio: UploadFile = File(...),
    locale: str = Form(default="ko-KR"),
    voice_preset: str = Form(default="cute_ko"),
) -> StreamingResponse:
    previous_state, response = await _process_voice_turn(
        session_id=session_id,
        request=request,
        audio=audio,
        locale=locale,
        voice_preset=voice_preset,
    )

    async def _event_stream() -> AsyncIterator[str]:
        yield _sse_event(
            "voice.delta",
            {"transcript": response.transcript, "state": response.state},
        )
        if response.slot_updates:
            yield _sse_event(
                "slot.updated",
                {"slot_updates": [slot.model_dump() for slot in response.slot_updates]},
            )
        if response.state != previous_state:
            yield _sse_event(
                "stage.changed",
                {"from": previous_state, "to": response.state},
            )
        yield _sse_event("planner.delta", {"text": response.next_question})
        if response.gate.ready:
            yield _sse_event("gate.ready", response.gate.model_dump())

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.post("/chat/session/{session_id}/assistant-voice", response_model=AssistantVoiceResponse)
async def create_assistant_voice(
    session_id: str,
    request_body: AssistantVoiceRequest,
    request: Request,
) -> AssistantVoiceResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    voice_agent: VoiceAgent = request.app.state.voice_agent
    voice_service: VoiceService = request.app.state.voice_service

    if not voice_service.enabled:
        raise HTTPException(status_code=503, detail="Voice service is not configured")

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    text = voice_agent.format_question(
        question=request_body.text,
        preset=request_body.voice_preset,
    )
    audio_url, bytes_size = await voice_service.synthesize_to_file(
        text=text,
        voice_preset=request_body.voice_preset,
        audio_format=request_body.format,
    )
    return AssistantVoiceResponse(
        audio_url=audio_url,
        format=request_body.format,
        bytes_size=bytes_size,
    )
