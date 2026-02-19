"""Research agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import ResearchOutput


class ResearchAgent(BaseStudioAgent[ResearchOutput]):
    agent_name = "Research Agent"
    stage = "phase1_parallel"
    output_model = ResearchOutput
    instructions = (
        "당신은 시장 조사 전문가입니다. 트렌드, 경쟁사, 수요 시그널을 분석하여 한국어로 작성하십시오. "
        "출시 시사점에 대한 근거 중심의 분석을 반드시 한국어로 제공하십시오."
    )
    output_requirements = (
        "5) market_signals: 시장 변화 시그널 2~4개\n"
        "6) competitor_insights: 경쟁 동향 1~3개\n"
        "7) audience_insights: 타깃 인사이트 1~3개"
    )
