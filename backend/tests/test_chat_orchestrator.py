"""Tests for chat brief collection orchestrator."""

from app.agents.chat_orchestrator import ChatOrchestrator
from app.schemas import BriefSlots


def test_gate_is_not_ready_with_empty_slots() -> None:
    orchestrator = ChatOrchestrator()
    gate = orchestrator.evaluate_gate(BriefSlots())

    assert gate.ready is False
    assert gate.completeness == 0.0
    assert "product.name" in gate.missing_required
    assert "goal.weekly_goal" in gate.missing_required


def test_process_turn_sets_brief_ready_when_required_fields_are_present() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    turn = orchestrator.process_turn(
        message=(
            "제품명은 글로우세럼X, 카테고리는 스킨케어, 특징은 저자극, 빠른흡수, 비건포뮬라, "
            "가격은 39000원, 타겟은 20대 직장인, 이유는 민감 피부 진정 필요, "
            "채널은 인스타와 네이버, 목표는 문의"
        ),
        slots=slots,
    )

    assert turn.state == "BRIEF_READY"
    assert turn.gate.ready is True
    assert turn.brief_slots.product.name == "글로우세럼X"
    assert turn.brief_slots.product.category == "스킨케어"
    assert len(turn.brief_slots.product.features) >= 3
    assert turn.brief_slots.product.price_band == "mid"
    assert turn.brief_slots.target.who == "20대 직장인"
    assert turn.brief_slots.target.why == "민감 피부 진정 필요"
    assert set(turn.brief_slots.channel.channels) == {"Instagram", "Naver"}
    assert turn.brief_slots.goal.weekly_goal == "inquiry"
