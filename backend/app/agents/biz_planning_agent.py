"""Business planning agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import BizPlanningOutput


class BizPlanningAgent(BaseStudioAgent[BizPlanningOutput]):
    agent_name = "Biz Planning Agent"
    stage = "phase2_synthesis"
    output_model = BizPlanningOutput
    instructions = (
        "당신은 비즈니스 기획 리드입니다. 예산 배분, 매출 가설, KPI 목표를 한국어로 수립하십시오. "
        "측정 가능한 가정과 리스크가 조정된 전망을 반드시 한국어로 제시하십시오."
    )
    output_requirements = (
        "5) budget_split_krw: 카테고리별 예산 map\n"
        "6) kpi_targets: KPI 목표 2~5개\n"
        "7) roi_assumptions: ROI 가정 1~3개"
    )
