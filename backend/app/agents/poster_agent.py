"""Poster planning agent under marketing."""

from app.agents.base import BaseStudioAgent
from app.schemas import PosterBriefOutput


class PosterAgent(BaseStudioAgent[PosterBriefOutput]):
    agent_name = "Poster Agent"
    stage = "phase3_assets"
    output_model = PosterBriefOutput
    instructions = (
        "당신은 비주얼 캠페인 디자이너입니다. 헤드라인, 바디 카피, 레이아웃 가이드, 비주얼 계층 구조 힌트를 포함한 포스터 기획안을 한국어로 작성하십시오. "
        "반드시 한국어만 사용하십시오."
    )
    output_requirements = (
        "5) headline: 메인 헤드라인\n"
        "6) subheadline: 보조 문구\n"
        "7) layout_directions: 레이아웃 지시 2~4개\n"
        "8) key_visual_keywords: 비주얼 키워드 3~6개"
    )
