"""Marketing strategy agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import MarketerOutput


class MarketerAgent(BaseStudioAgent[MarketerOutput]):
    agent_name = "Marketer Agent"
    stage = "phase2_synthesis"
    output_model = MarketerOutput
    instructions = (
        "당신은 GTM 마케터입니다. 출시 메시지, 채널 믹스, 캠페인 접근 방식을 한국어로 구축하십시오. "
        "인지도와 전환의 균형을 최적화하여 반드시 한국어로 전략을 수립하십시오."
    )
    output_requirements = (
        "5) message_pillars: 핵심 메시지 2~4개\n"
        "6) channel_tactics: 채널별 실행전략 map\n"
        "7) conversion_hooks: 전환 유도 장치 2~4개"
    )
