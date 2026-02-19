"""Planning agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import PlannerOutput


class PlannerAgent(BaseStudioAgent[PlannerOutput]):
    agent_name = "Planner Agent"
    stage = "phase2_synthesis"
    output_model = PlannerOutput
    instructions = (
        "당신은 출시 PM 플래너입니다. 마일스톤 계획, 의존성, 실행 체크리스트를 한국어로 구축하십시오. "
        "핵심 경로와 출시일 주요 결정 사항을 반드시 한국어로 명시하십시오."
    )
    output_requirements = (
        "5) milestones: [{name,due,owner,success_criteria}] 2~5개\n"
        "6) critical_path: 핵심 경로 2~4개\n"
        "7) dependencies: 선행 의존성 2~5개"
    )
