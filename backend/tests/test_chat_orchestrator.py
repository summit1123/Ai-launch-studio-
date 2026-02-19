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


def test_process_turn_normalizes_video_seconds_and_returns_notice() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    turn = orchestrator.process_turn(
        message="영상 길이는 8초로 해줘. 제품명은 테스트",
        slots=slots,
    )

    assert turn.brief_slots.goal.video_seconds == 10
    assert "8초" in turn.assistant_message
    assert "10초" in turn.assistant_message


def test_process_turn_maps_plain_answer_to_expected_product_name_slot() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()

    turn = orchestrator.process_turn(
        message="아이폰",
        slots=slots,
    )

    assert turn.brief_slots.product.name == "아이폰"
    assert turn.gate.ready is False
    assert "아이폰" in turn.assistant_message
    assert "제품 카테고리는 무엇인가요?" in turn.assistant_message


def test_process_turn_accepts_plain_feature_list_when_feature_slot_is_expected() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "테스트 세럼"
    slots.product.category = "스킨케어"
    slots.product.price_band = "mid"
    slots.target.who = "20대 직장인"
    slots.target.why = "피부 진정"
    slots.channel.channels = ["Instagram"]
    slots.goal.weekly_goal = "inquiry"

    turn = orchestrator.process_turn(
        message="저자극, 빠른 흡수, 비건 포뮬러",
        slots=slots,
    )

    assert turn.state == "BRIEF_READY"
    assert turn.gate.ready is True
    assert len(turn.brief_slots.product.features) >= 3
    assert "저자극" in turn.brief_slots.product.features


def test_process_turn_does_not_treat_plain_sentence_as_feature_list() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "테스트 세럼"
    slots.product.category = "스킨케어"
    slots.product.price_band = "mid"
    slots.target.who = "20대 직장인"
    slots.target.why = "피부 진정"
    slots.channel.channels = ["Instagram"]
    slots.goal.weekly_goal = "inquiry"

    turn = orchestrator.process_turn(
        message="카테고리는 스킨케어",
        slots=slots,
    )

    assert turn.state == "CHAT_COLLECTING"
    assert turn.brief_slots.product.features == []
    assert "핵심 특징 3가지를 알려주세요" in turn.assistant_message
