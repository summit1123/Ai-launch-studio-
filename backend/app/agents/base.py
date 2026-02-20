"""Base agent utilities."""

from __future__ import annotations

import logging
import time
from typing import Generic, TypeVar

from app.schemas import AgentPayload, LaunchBrief
from app.services import AgentRuntime

logger = logging.getLogger(__name__)

OutputT = TypeVar("OutputT", bound=AgentPayload)


class BaseStudioAgent(Generic[OutputT]):
    """Shared run flow for all agents."""

    agent_name: str = "Studio Agent"
    stage: str = "generic"
    instructions: str = "간결하고 실행 가능한 지침을 제공하십시오."
    output_requirements: str = ""
    output_model: type[OutputT]

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    def _build_prompt(self, brief: LaunchBrief, context: str = "") -> str:
        channels = ", ".join(brief.channel_focus) if brief.channel_focus else "미지정"
        image_ref = brief.product_image_url or "없음"
        image_context = brief.product_image_context or "없음"
        return f"""
당신은 AI Launch Studio의 실행형 에이전트입니다.
목표는 "아이디어 설명"이 아니라 "즉시 실행 가능한 결과"를 주는 것입니다.

[브리프]
- 제품명: {brief.product_name}
- 카테고리: {brief.product_category}
- 타깃: {brief.target_audience}
- 가격대: {brief.price_band}
- 총예산(KRW): {brief.total_budget_krw}
- 출시일: {brief.launch_date}
- KPI: {brief.core_kpi}
- 지역: {brief.region}
- 채널: {channels}
- 영상 길이(초): {brief.video_seconds}
- 제품 레퍼런스 이미지 URL: {image_ref}
- 제품 레퍼런스 이미지 요약: {image_context}

[공유 컨텍스트]
{context or "없음"}

[출력 규칙]
1) 모든 출력은 한국어
2) 가짜/샘플/데모라고 표시된 문구 금지
3) 근거가 약한 항목은 단정하지 말고 `risks`에 불확실성을 명시
4) 실행 단위는 모호한 표현 대신 이번 주 실행 가능한 수준으로 작성

[필수 출력]
1) summary: 핵심 결론 1문단
2) key_points: 실행 포인트 3~5개
3) risks: 주요 리스크 1~3개
4) artifacts: 필요한 구조화 데이터
{self.output_requirements}

중요: 출력 스키마 키 누락 없이 반환하세요.
""".strip()

    def _resolve_output_model(self) -> type[OutputT]:
        model = getattr(self, "output_model", None)
        if model is None:
            raise ValueError(f"{self.agent_name} is missing output_model")
        return model

    async def run(self, brief: LaunchBrief, context: str = "") -> OutputT:
        logger.info("Agent '%s' starting", self.agent_name)
        t0 = time.monotonic()
        prompt = self._build_prompt(brief=brief, context=context)
        result = await self._runtime.run(
            agent_name=self.agent_name,
            instructions=self.instructions,
            prompt=prompt,
            brief=brief,
            output_type=self._resolve_output_model(),
        )
        elapsed = time.monotonic() - t0
        logger.info("Agent '%s' completed in %.2fs", self.agent_name, elapsed)
        return result
