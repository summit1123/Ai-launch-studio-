"""Tests for chat brief collection orchestrator."""

from app.agents.chat_orchestrator import ChatOrchestrator
from app.schemas import BriefSlots, SlotUpdate


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

    assert turn.brief_slots.goal.video_seconds == 8
    assert "8초" in turn.assistant_message


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

    assert turn.state == "BRIEF_READY"
    assert turn.brief_slots.product.features == []
    assert "핵심 정보가 충분히 모였어요" in turn.assistant_message


def test_process_turn_accepts_plain_numeric_price_when_price_slot_is_expected() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "루미 세럼"
    slots.product.category = "스킨케어"

    turn = orchestrator.process_turn(
        message="39000",
        slots=slots,
    )

    assert turn.brief_slots.product.price_band == "mid"
    assert any(update.path == "product.price_band" for update in turn.slot_updates)


def test_process_turn_applies_external_updates_before_rule_updates() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()

    turn = orchestrator.process_turn(
        message="스킨케어",
        slots=slots,
        external_updates=[
            SlotUpdate(path="product.name", value="루미 세럼", confidence=0.94),
        ],
    )

    assert turn.brief_slots.product.name == "루미 세럼"
    assert turn.brief_slots.product.category == "스킨케어"
    assert any(update.path == "product.name" for update in turn.slot_updates)


def test_process_turn_questions_conflicting_discount_and_high_price() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "피자헛"
    slots.product.category = "푸드"

    turn = orchestrator.process_turn(
        message="150000원 초특가 세일",
        slots=slots,
    )

    assert turn.brief_slots.product.price_band is None
    assert "금액이 맞나요" in turn.assistant_message


def test_process_turn_does_not_fill_slots_when_user_asks_why_question() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "루미 세럼"
    slots.product.category = "스킨케어"
    slots.product.price_band = "mid"

    turn = orchestrator.process_turn(
        message="왜 타겟 고객이 필요해?",
        slots=slots,
    )

    assert not turn.brief_slots.target.who
    assert not turn.brief_slots.target.why
    assert "타겟이 선명해야" in turn.assistant_message


def test_process_turn_answers_price_input_format_question_first() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "루미 세럼"
    slots.product.category = "스킨케어"

    turn = orchestrator.process_turn(
        message="가격은 숫자만 써도 돼?",
        slots=slots,
    )

    assert turn.brief_slots.product.price_band is None
    assert "가격은 숫자만 입력해도 인식돼요" in turn.assistant_message


def test_process_turn_keeps_short_single_token_with_question_mark_as_name() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()

    turn = orchestrator.process_turn(
        message="아이폰?",
        slots=slots,
    )

    assert turn.brief_slots.product.name == "아이폰"


def test_process_turn_autofills_channel_when_user_delegates_choice() -> None:
    orchestrator = ChatOrchestrator()
    slots = BriefSlots()
    slots.product.name = "피자헛"
    slots.product.category = "푸드"
    slots.product.price_band = "mid"
    slots.target.who = "20대 직장인"
    slots.target.why = "가성비 외식"
    slots.goal.weekly_goal = "purchase"
    slots.product.features = ["빠른 배달", "다양한 메뉴", "할인 프로모션"]

    turn = orchestrator.process_turn(
        message="니가 알아서 해",
        slots=slots,
    )

    assert turn.brief_slots.channel.channels == ["Instagram", "YouTube"]
    assert any(update.path == "channel.channels" for update in turn.slot_updates)
