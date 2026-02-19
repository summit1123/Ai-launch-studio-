"""Voice chat API."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.agents import ChatOrchestrator, VoiceAgent
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    AssistantVoiceRequest,
    AssistantVoiceResponse,
    VoiceTurnResponse,
)
from app.services import VoiceService

router = APIRouter()


@router.post("/chat/session/{session_id}/voice-turn", response_model=VoiceTurnResponse)
async def post_voice_turn(
    session_id: str,
    request: Request,
    audio: UploadFile = File(...),
    locale: str = Form(default="ko-KR"),
    voice_preset: str = Form(default="friendly_ko"),
) -> VoiceTurnResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator
    voice_agent: VoiceAgent = request.app.state.voice_agent
    voice_service: VoiceService = request.app.state.voice_service

    if not voice_service.enabled:
        raise HTTPException(status_code=503, detail="Voice service is not configured")

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

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
        return VoiceTurnResponse(
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

    if record.state != "CHAT_COLLECTING":
        gate = chat_orchestrator.evaluate_gate(record.brief_slots)
        next_question = voice_agent.format_question(
            question="브리프 수집이 완료되었습니다. 다음 생성 단계를 실행해 주세요.",
            preset=voice_preset,
        )
        history_repository.append_chat_message(
            session_id=session_id,
            role="assistant",
            content=next_question,
        )
        return VoiceTurnResponse(
            session_id=session_id,
            transcript=transcript,
            state=record.state,
            next_question=next_question,
            slot_updates=[],
            brief_slots=record.brief_slots,
            gate=gate,
        )

    turn = chat_orchestrator.process_turn(message=transcript, slots=record.brief_slots)
    formatted_question = voice_agent.format_question(
        question=turn.assistant_message,
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
    return VoiceTurnResponse(
        session_id=session_id,
        transcript=transcript,
        state=turn.state,
        next_question=formatted_question,
        slot_updates=turn.slot_updates,
        brief_slots=turn.brief_slots,
        gate=turn.gate,
    )


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
