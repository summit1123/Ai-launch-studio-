"""LLM-driven onboarding dialogue service."""

from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas import BriefSlots, ChatState, GateStatus

logger = logging.getLogger(__name__)


class OnboardingDialogueService:
    """Generates conversational onboarding replies with OpenAI as best-effort."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def compose_reply(
        self,
        *,
        fallback_message: str,
        state: ChatState,
        gate: GateStatus,
        brief_slots: BriefSlots,
        user_message: str,
        locale: str = "ko-KR",
    ) -> str:
        if self._client is None:
            return fallback_message

        try:
            response = await asyncio.wait_for(
                self._client.responses.create(
                    model=self._model,
                    input=self._build_prompt(
                        fallback_message=fallback_message,
                        state=state,
                        gate=gate,
                        brief_slots=brief_slots,
                        user_message=user_message,
                        locale=locale,
                    ),
                    temperature=0.4,
                    max_output_tokens=160,
                ),
                timeout=8,
            )
        except Exception:
            logger.exception("Onboarding dialogue generation failed")
            return fallback_message

        text = self._extract_text(response)
        if not text:
            return fallback_message
        return text

    def _build_prompt(
        self,
        *,
        fallback_message: str,
        state: ChatState,
        gate: GateStatus,
        brief_slots: BriefSlots,
        user_message: str,
        locale: str,
    ) -> str:
        return (
            "너는 한국어 온보딩 챗봇이다.\n"
            "목표: 사용자의 제품 홍보 브리프를 대화형으로 수집한다.\n"
            "규칙:\n"
            "1) 응답은 1~2문장으로 짧고 자연스럽게.\n"
            "2) CHAT_COLLECTING 상태이면 정확히 하나의 다음 질문을 포함.\n"
            "3) 이미 받은 정보는 짧게 확인하고, 반복 질문을 피한다.\n"
            "4) 과장된 친절 문구 없이 간결하게.\n"
            "5) 한국어로 답한다.\n"
            "6) 마크다운 문법(*,**,#,`,-,[])과 이모지를 쓰지 말고 평문으로만 쓴다.\n\n"
            f"locale: {locale}\n"
            f"state: {state}\n"
            f"gate_ready: {gate.ready}\n"
            f"missing_required: {gate.missing_required}\n"
            f"completeness: {gate.completeness}\n"
            f"user_message: {user_message}\n"
            f"brief_slots: {brief_slots.model_dump_json(ensure_ascii=False)}\n"
            f"fallback_message: {fallback_message}\n\n"
            "fallback_message의 의도를 유지해 자연스럽게 다시 써서 출력해라."
        )

    @staticmethod
    def _extract_text(response: object) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = getattr(response, "output", None)
        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                content = getattr(item, "content", None)
                if not isinstance(content, list):
                    continue
                for part in content:
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())
            if chunks:
                return " ".join(chunks)
        return ""
