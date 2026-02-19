"""MD agent."""

from app.agents.base import BaseStudioAgent
from app.schemas import MDOutput


class MDAgent(BaseStudioAgent[MDOutput]):
    agent_name = "MD Agent"
    stage = "phase1_parallel"
    output_model = MDOutput
    instructions = (
        "당신은 머천다이징 전략가입니다. 제품 포지셔닝, USP, 상품 구성을 정의하여 한국어로 작성하십시오. "
        "출시 시 즉시 실행 가능한 권장 사항을 반드시 한국어로 제안하십시오."
    )
    output_requirements = (
        "5) usp: 제품 USP 2~4개\n"
        "6) hero_product_angle: 핵심 포지셔닝 1문장\n"
        "7) assortment_notes: SKU 구성 노트 1~3개"
    )
