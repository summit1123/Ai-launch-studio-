"""LLM-driven onboarding dialogue service."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas import BriefSlots, ChatState, GateStatus, SlotUpdate

logger = logging.getLogger(__name__)


class OnboardingDialogueService:
    """Generates conversational onboarding replies with OpenAI as best-effort."""

    _PATH_LABELS = {
        "product.name": "제품명",
        "product.category": "카테고리",
        "product.features": "핵심 특징 3개",
        "product.price_band": "가격대",
        "target.who": "타겟 고객",
        "target.why": "구매 이유",
        "channel.channels": "집중 채널 1~2개",
        "goal.weekly_goal": "이번 주 목표",
    }
    _REPLY_TIMEOUT_SECONDS = 15
    _SLOT_TIMEOUT_SECONDS = 12
    _REPLY_HISTORY_TURNS = 16
    _SLOT_HISTORY_TURNS = 16

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
        chat_history: list[dict[str, str]] | None = None,
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
                        chat_history=chat_history or [],
                        locale=locale,
                    ),
                    temperature=0.6,
                ),
                timeout=self._REPLY_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("Onboarding dialogue generation failed")
            return fallback_message

        text = self._extract_text(response)
        if not text:
            return fallback_message
        return text

    async def propose_slot_updates(
        self,
        *,
        state: ChatState,
        gate: GateStatus,
        brief_slots: BriefSlots,
        user_message: str,
        chat_history: list[dict[str, str]] | None = None,
        locale: str = "ko-KR",
    ) -> list[SlotUpdate]:
        if self._client is None:
            return []

        try:
            response = await asyncio.wait_for(
                self._client.responses.create(
                    model=self._model,
                    input=self._build_slot_extraction_prompt(
                        state=state,
                        gate=gate,
                        brief_slots=brief_slots,
                        user_message=user_message,
                        chat_history=chat_history or [],
                        locale=locale,
                    ),
                    temperature=0.1,
                ),
                timeout=self._SLOT_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("Onboarding slot extraction failed")
            return []

        text = self._extract_text(response)
        if not text:
            return []
        return self._parse_slot_updates(text)

    def _build_slot_extraction_prompt(
        self,
        *,
        state: ChatState,
        gate: GateStatus,
        brief_slots: BriefSlots,
        user_message: str,
        chat_history: list[dict[str, str]],
        locale: str,
    ) -> str:
        allowed_paths = [
            "product.name",
            "product.category",
            "product.features",
            "product.price_band",
            "target.who",
            "target.why",
            "channel.channels",
            "goal.weekly_goal",
            "goal.video_seconds",
        ]
        history_payload = [
            {
                "role": item.get("role", ""),
                "content": item.get("content", ""),
            }
            for item in chat_history[-self._SLOT_HISTORY_TURNS :]
        ]
        missing_labels = [self._PATH_LABELS.get(path, path) for path in gate.missing_required]

        return (
            "너는 대화형 온보딩 슬롯 추출기다.\n"
            "사용자 발화와 대화 맥락을 보고 이번 턴에 확정 가능한 정보만 추출한다.\n"
            "추측 금지: 사용자가 직접 말하지 않은 값은 절대 채우지 마라.\n"
            "누락/불확실 값은 생략한다.\n"
            "입력 정보가 상충되면(예: 초특가 표현 + 매우 높은 가격) 해당 슬롯 업데이트를 생략한다.\n"
            "반드시 JSON 객체만 출력한다. 설명 문장, 마크다운, 코드펜스 금지.\n\n"
            "출력 스키마:\n"
            "{\n"
            '  "updates": [\n'
            '    {"path": "product.name", "value": "...", "confidence": 0.0}\n'
            "  ]\n"
            "}\n\n"
            "경로 규칙:\n"
            "- path는 아래 목록에서만 선택\n"
            f"- allowed_paths: {allowed_paths}\n"
            "- product.features, channel.channels는 배열\n"
            "- product.price_band는 low/mid/premium 중 하나\n"
            "- goal.weekly_goal는 reach/inquiry/purchase 중 하나\n"
            "- goal.video_seconds는 정수(4/8/12)\n"
            "- confidence는 0~1 실수\n\n"
            f"locale: {locale}\n"
            f"state: {state}\n"
            f"gate_ready: {gate.ready}\n"
            f"missing_required_labels: {missing_labels}\n"
            f"current_slots: {brief_slots.model_dump_json(ensure_ascii=False)}\n"
            f"chat_history: {json.dumps(history_payload, ensure_ascii=False)}\n"
            f"user_message: {user_message}\n"
        )

    @staticmethod
    def _parse_slot_updates(raw_text: str) -> list[SlotUpdate]:
        candidate = raw_text.strip()
        if not candidate:
            return []

        text_variants = [candidate]
        fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*```", candidate)
        if fenced_match:
            text_variants.append(fenced_match.group(1).strip())
        object_match = re.search(r"(\{[\s\S]*\})", candidate)
        if object_match:
            text_variants.append(object_match.group(1).strip())
        array_match = re.search(r"(\[[\s\S]*\])", candidate)
        if array_match:
            text_variants.append(array_match.group(1).strip())

        payload: object | None = None
        for variant in text_variants:
            try:
                payload = json.loads(variant)
                break
            except json.JSONDecodeError:
                continue
        if payload is None:
            return []

        raw_updates: object
        if isinstance(payload, list):
            raw_updates = payload
        elif isinstance(payload, dict):
            raw_updates = payload.get("updates", [])
        else:
            return []

        if not isinstance(raw_updates, list):
            return []

        updates: list[SlotUpdate] = []
        for item in raw_updates:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if not isinstance(path, str) or not path.strip():
                continue
            value = item.get("value")
            confidence = item.get("confidence", 0.72)
            try:
                confidence_float = float(confidence)
            except (TypeError, ValueError):
                confidence_float = 0.72
            confidence_float = max(0.0, min(1.0, confidence_float))
            updates.append(
                SlotUpdate(
                    path=path.strip(),
                    value=value,
                    confidence=confidence_float,
                )
            )
        return updates

    def _build_prompt(
        self,
        *,
        fallback_message: str,
        state: ChatState,
        gate: GateStatus,
        brief_slots: BriefSlots,
        user_message: str,
        chat_history: list[dict[str, str]],
        locale: str,
    ) -> str:
        missing_labels = [self._PATH_LABELS.get(path, path) for path in gate.missing_required]
        history_payload = [
            {
                "role": item.get("role", ""),
                "content": item.get("content", ""),
            }
            for item in chat_history[-self._REPLY_HISTORY_TURNS :]
        ]
        return (
            "너는 제품 홍보 기획을 돕는 한국어 챗봇이다.\n"
            "사용자는 자유롭게 말한다. 템플릿 문답처럼 보이지 않게 자연스럽게 대화하라.\n"
            "규칙:\n"
            "1) 사용자의 명시적 질문/요청에 먼저 답한다. 질문을 무시하고 바로 되묻지 않는다.\n"
            "2) 기획 관련 질문에는 실행 가능한 답을 준다(메시지, 채널, 크리에이티브, KPI/테스트).\n"
            "3) 응답 길이는 의도에 맞게 유연하게 작성하되, 불필요한 반복은 피한다.\n"
            "4) CHAT_COLLECTING 상태에서는 필요한 경우에만 후속 질문 1개를 끝에 붙인다.\n"
            "5) 같은 질문을 반복하지 말고, 이미 받은 정보는 확인 후 다음 단계로 진행한다.\n"
            "6) 사용자가 이미지를 업로드했다면 image_context를 근거로 제안을 구체화한다.\n"
            "7) 이미지 기반 추정은 단정하지 말고 '보이는 정보 기준 추정'임을 짧게 밝힌다.\n"
            "8) 입력이 상충되거나 비현실적으로 보이면 확정하지 말고 짧게 검증 질문을 한다.\n"
            "9) 내부 키(슬롯 경로)나 시스템 용어(gate, slot, required)는 절대 노출하지 않는다.\n"
            "10) 출력에 '확인:', '필요한 정보:', '질문:' 같은 라벨/머리말을 쓰지 않는다.\n"
            "11) 한국어 평문으로 답하고, 마크다운/이모지는 사용하지 않는다.\n\n"
            f"locale: {locale}\n"
            f"state: {state}\n"
            f"gate_ready: {gate.ready}\n"
            f"missing_required: {gate.missing_required}\n"
            f"missing_required_labels: {missing_labels}\n"
            f"completeness: {gate.completeness}\n"
            f"chat_history: {json.dumps(history_payload, ensure_ascii=False)}\n"
            f"user_message: {user_message}\n"
            f"brief_slots: {brief_slots.model_dump_json(ensure_ascii=False)}\n"
            f"fallback_message: {fallback_message}\n\n"
            "user_message의 의도를 우선 반영하고, fallback_message 및 missing_required_labels를 참고해 자연스러운 한 턴 답변을 작성해라."
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
