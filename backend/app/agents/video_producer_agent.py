"""Video script agent under marketing."""

from app.agents.base import BaseStudioAgent
from app.schemas import VideoScriptOutput


class VideoProducerAgent(BaseStudioAgent[VideoScriptOutput]):
    agent_name = "Video Producer Agent"
    stage = "phase3_assets"
    output_model = VideoScriptOutput
    instructions = (
        "당신은 홍보 영상 프로듀서입니다. 장면 흐름, 나레이션 가이드, CTA를 포함한 30-60초 분량의 제품 출시 영상 스크립트를 한국어로 작성하십시오. "
        "반드시 한국어만 사용하십시오."
    )
    output_requirements = (
        "5) scene_plan: 장면 흐름 4~7개\n"
        "6) narration_script: 나레이션 원고\n"
        "7) cta_line: 마지막 행동 유도 문구"
    )
