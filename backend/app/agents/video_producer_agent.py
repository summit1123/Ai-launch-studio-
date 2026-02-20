"""Video script agent under marketing."""

from app.agents.base import BaseStudioAgent
from app.schemas import VideoScriptOutput


class VideoProducerAgent(BaseStudioAgent[VideoScriptOutput]):
    agent_name = "Video Producer Agent"
    stage = "phase3_assets"
    output_model = VideoScriptOutput
    instructions = (
        "당신은 숏폼 홍보 영상 프로듀서입니다. "
        "브리프에 포함된 영상 길이(초)에 정확히 맞춰 장면 흐름, 나레이션 가이드, CTA를 한국어로 작성하십시오. "
        "나레이션은 해당 길이 안에서 끊김 없이 자연스럽게 완독 가능한 분량으로만 작성하십시오. "
        "영상 길이별 엄수 규칙: 4초=1문장(약 28자 이내), 8초=2문장(약 56자 이내), 12초=3문장(약 84자 이내). "
        "문장을 길게 늘이지 말고, 접속사 나열을 피하고, 한 문장에 메시지 1개만 담으십시오. "
        "CTA는 매우 짧게(8~14자 내외) 작성하십시오. "
        "한 장면당 메시지는 1개만 두고, 과도한 컷 전환보다 선명한 제품 클로즈업과 안정적 카메라 무빙을 우선하십시오. "
        "반드시 한국어만 사용하십시오."
    )
    output_requirements = (
        "5) scene_plan: 길이별 장면 수 제한 준수 (4초=최대3, 8초=최대4, 12초=최대5)\n"
        "6) narration_script: 길이에 맞춰 자연스럽게 읽히는 짧은 나레이션 원고\n"
        "7) cta_line: 8~14자 내외의 짧은 행동 유도 문구"
    )
