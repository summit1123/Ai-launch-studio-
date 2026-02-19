"""Wrapper around OpenAI Agents SDK with safe local fallback."""

from __future__ import annotations

import logging
import os
from typing import TypeVar

logger = logging.getLogger(__name__)

from pydantic import ValidationError

from app.schemas import AgentPayload, LaunchBrief

try:
    from agents import Agent, AgentOutputSchema, Runner

    HAS_AGENT_SDK = True
except Exception:
    Agent = None  # type: ignore[assignment]
    AgentOutputSchema = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]
    HAS_AGENT_SDK = False

OutputT = TypeVar("OutputT", bound=AgentPayload)


class AgentRuntime:
    """Execute agent prompts via SDK or deterministic mock."""

    def __init__(self, model: str, api_key: str | None, use_agent_sdk: bool = True) -> None:
        self._model = model
        if api_key and "OPENAI_API_KEY" not in os.environ:
            os.environ["OPENAI_API_KEY"] = api_key

        self._sdk_enabled = use_agent_sdk and HAS_AGENT_SDK and bool(
            os.getenv("OPENAI_API_KEY")
        )

    @property
    def using_live_sdk(self) -> bool:
        return self._sdk_enabled

    async def run(
        self,
        *,
        agent_name: str,
        instructions: str,
        prompt: str,
        brief: LaunchBrief,
        output_type: type[OutputT],
    ) -> OutputT:
        if self._sdk_enabled:
            output = await self._run_with_sdk(
                agent_name=agent_name,
                instructions=instructions,
                prompt=prompt,
                output_type=output_type,
            )
            if output is not None:
                return output
            logger.warning(
                "SDK call failed for '%s', falling back to mock", agent_name
            )

        return self._mock_payload(agent_name=agent_name, brief=brief, output_type=output_type)

    async def _run_with_sdk(
        self,
        *,
        agent_name: str,
        instructions: str,
        prompt: str,
        output_type: type[OutputT],
    ) -> OutputT | None:
        if not HAS_AGENT_SDK:
            return None

        if Agent is None or Runner is None:
            return None

        kwargs: dict[str, object] = {
            "name": agent_name,
            "instructions": instructions,
        }
        wrapped_output_type: object = output_type
        if AgentOutputSchema is not None:
            try:
                wrapped_output_type = AgentOutputSchema(output_type, strict_json_schema=False)
            except Exception:
                wrapped_output_type = output_type
        kwargs["output_type"] = wrapped_output_type

        try:
            kwargs["model"] = self._model
            live_agent = Agent(**kwargs)
        except TypeError:
            kwargs.pop("model", None)
            live_agent = Agent(**kwargs)

        try:
            result = await Runner.run(starting_agent=live_agent, input=prompt)
            final_output = result.final_output
        except Exception:
            logger.exception("Agent SDK Runner.run failed for '%s'", agent_name)
            return None

        return self._coerce_output(final_output=final_output, output_type=output_type)

    def _coerce_output(self, *, final_output: object, output_type: type[OutputT]) -> OutputT | None:
        try:
            if isinstance(final_output, output_type):
                return final_output

            if isinstance(final_output, str):
                return output_type.model_validate(
                    {
                        "summary": final_output,
                        "key_points": [],
                        "risks": [],
                        "artifacts": {"source": "sdk-string"},
                    }
                )

            if isinstance(final_output, dict):
                return output_type.model_validate(final_output)

            if hasattr(final_output, "model_dump"):
                model_dump = getattr(final_output, "model_dump")
                if callable(model_dump):
                    return output_type.model_validate(model_dump())
        except ValidationError:
            logger.warning("Output validation failed for %s", output_type.__name__)
            return None

        try:
            return output_type.model_validate(
                {
                    "summary": str(final_output),
                    "key_points": [],
                    "risks": [],
                    "artifacts": {"source": "sdk-fallback-stringified"},
                }
            )
        except ValidationError:
            return None

    def _mock_payload(
        self,
        *,
        agent_name: str,
        brief: LaunchBrief,
        output_type: type[OutputT],
    ) -> OutputT:
        base: dict[str, object] = {
            "summary": (
                f"[MOCK:{agent_name}] {brief.product_name}({brief.product_category}) 런칭 "
                f"초안 생성 완료. 목표 KPI는 '{brief.core_kpi}' 기준으로 정렬했습니다."
            ),
            "key_points": [
                f"타깃: {brief.target_audience}",
                f"가격대: {brief.price_band}",
                f"예산: {brief.total_budget_krw:,} KRW",
            ],
            "risks": [
                "메시지 일관성 검토 필요",
                "출시 일정 버퍼(최소 1주) 확보 필요",
            ],
            "artifacts": {"source": "mock", "agent": agent_name},
        }
        self._inject_mock_details(payload=base, brief=brief, output_type=output_type)
        return output_type.model_validate(base)

    @staticmethod
    def _inject_mock_details(
        *,
        payload: dict[str, object],
        brief: LaunchBrief,
        output_type: type[OutputT],
    ) -> None:
        fields = output_type.model_fields

        if "market_signals" in fields:
            payload["market_signals"] = [
                f"{brief.product_category} 검색량 상승 시그널",
                f"{brief.target_audience} 세그먼트 관심도 증가",
            ]
            payload["competitor_insights"] = ["상위 경쟁사 2곳이 유사 라인 예고"]
            payload["audience_insights"] = ["가성비+기능성 메시지 반응 우세"]

        if "usp" in fields:
            payload["usp"] = ["핵심 성분 차별화", "짧은 사용 후 체감 포인트 강조"]
            payload["hero_product_angle"] = f"{brief.product_name}의 첫구매 진입장벽 최소화"
            payload["assortment_notes"] = ["히어로 SKU 1개 + 보조 SKU 2개 권장"]

        if "implementation_scope" in fields:
            payload["implementation_scope"] = [
                "브리프 입력 폼",
                "오케스트레이터 실행 API",
                "결과 타임라인 대시보드",
            ]
            payload["technical_constraints"] = ["API 타임아웃 관리", "출력 스키마 검증 필요"]
            payload["demo_readiness_checks"] = ["3회 연속 데모 실행", "오류 메시지 fallback 확인"]

        if "milestones" in fields:
            payload["milestones"] = [
                {
                    "name": "브리프 확정",
                    "due": "D-7",
                    "owner": "기획팀",
                    "success_criteria": "입력 파라미터 승인 완료",
                },
                {
                    "name": "콘텐츠 초안 확정",
                    "due": "D-4",
                    "owner": "마케팅팀",
                    "success_criteria": "영상/포스터/카피 1차본 완료",
                },
                {
                    "name": "최종 리허설",
                    "due": "D-1",
                    "owner": "전체팀",
                    "success_criteria": "데모 오류 0건",
                },
            ]
            payload["critical_path"] = ["브리프 확정", "에이전트 산출물 통합", "리허설"]
            payload["dependencies"] = ["시장조사 결과", "예산 승인", "데모 환경 준비"]

        if "message_pillars" in fields:
            payload["message_pillars"] = ["문제 해결", "즉시 체감", "신뢰 근거"]
            payload["channel_tactics"] = {
                "Instagram": "숏폼 리치 + 후기 유도",
                "YouTube": "문제-해결형 브랜디드 영상",
                "Naver SmartStore": "상세페이지 전환 최적화",
            }
            payload["conversion_hooks"] = ["런칭 한정 혜택", "리뷰 리워드"]

        if "budget_split_krw" in fields:
            budget = max(brief.total_budget_krw, 0)
            payload["budget_split_krw"] = {
                "콘텐츠 제작": int(budget * 0.35),
                "퍼포먼스 광고": int(budget * 0.40),
                "인플루언서/협업": int(budget * 0.15),
                "예비비": int(budget * 0.10),
            }
            payload["kpi_targets"] = [brief.core_kpi, "CTR 1.8%+", "CAC 목표치 내 유지"]
            payload["roi_assumptions"] = ["런칭 4주 내 손익분기 60%", "재구매율 기반 LTV 상승"]

        if "scene_plan" in fields:
            payload["scene_plan"] = [
                "문제 제시: 기존 제품 한계",
                f"해결 제시: {brief.product_name} 핵심 기능",
                "사용 장면: 타깃 일상 시나리오",
                "사회적 증거: 리뷰/지표",
                "CTA: 구매 유도",
            ]
            payload["narration_script"] = (
                f"{brief.target_audience}를 위한 {brief.product_name} 런칭 메시지 나레이션 초안"
            )
            payload["cta_line"] = "지금 런칭 혜택으로 첫 구매를 시작하세요."

        if "headline" in fields:
            payload["headline"] = f"{brief.product_name}, 출시 즉시 체감되는 변화"
            payload["subheadline"] = f"{brief.target_audience}를 위한 맞춤 런칭 제안"
            payload["layout_directions"] = ["상단 훅 카피", "중앙 제품 비주얼", "하단 CTA 배치"]
            payload["key_visual_keywords"] = ["clean", "premium", "evidence-driven"]

        if "title" in fields:
            payload["title"] = f"{brief.product_name} 제품 소개"
            payload["body"] = (
                f"{brief.product_name}은(는) {brief.target_audience}를 위해 설계된 "
                "신규 런칭 제품으로, 사용 즉시 핵심 효용을 전달하도록 기획되었습니다."
            )
            payload["bullet_points"] = [
                "핵심 효용 1: 사용 직후 체감",
                "핵심 효용 2: 루틴 친화적 사용감",
                "핵심 효용 3: 명확한 구매 이유 제시",
            ]
