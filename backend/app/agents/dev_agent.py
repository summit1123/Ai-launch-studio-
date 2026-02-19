"""Dev feasibility agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import DevOutput


class DevAgent(BaseStudioAgent[DevOutput]):
    agent_name = "Dev Agent"
    stage = "phase1_parallel"
    output_model = DevOutput
    instructions = (
        "당신은 제품 엔지니어링 리드입니다. 구현 범위, 기술적 리스크, 데모 준비 상태를 한국어로 분석하십시오. "
        "짧은 일정 내의 현실적인 범위를 반드시 한국어로 우선순위화하십시오."
    )
    output_requirements = (
        "5) implementation_scope: 구현 범위 3~6개\n"
        "6) technical_constraints: 기술 제약 1~3개\n"
        "7) demo_readiness_checks: 데모 체크포인트 2~5개"
    )
