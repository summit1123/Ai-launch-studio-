"""Product copy agent under MD."""

from app.agents.base import BaseStudioAgent
from app.schemas import ProductCopyOutput


class ProductCopyAgent(BaseStudioAgent[ProductCopyOutput]):
    agent_name = "Product Copy Agent"
    stage = "phase3_assets"
    output_model = ProductCopyOutput
    instructions = (
        "당신은 전문 카피라이터입니다. 제품의 이점, 사용 상황, 입증 자료를 포함한 제품 설명을 한국어로 작성하십시오. "
        "모든 내용은 MD 전략과 일관성을 유지해야 하며, 반드시 한국어만 사용하십시오."
    )
    output_requirements = (
        "5) title: 상품 제목\n"
        "6) body: 본문 설명 3~6문장\n"
        "7) bullet_points: 핵심 포인트 3~5개"
    )
