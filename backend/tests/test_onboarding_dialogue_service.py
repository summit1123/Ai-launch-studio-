"""Tests for onboarding dialogue service utilities."""

from app.services.onboarding_dialogue_service import OnboardingDialogueService


def test_parse_slot_updates_from_json_object() -> None:
    raw = (
        '{"updates":[{"path":"product.name","value":"루미 세럼","confidence":0.93},'
        '{"path":"goal.video_seconds","value":12,"confidence":0.88}]}'
    )

    updates = OnboardingDialogueService._parse_slot_updates(raw)

    assert len(updates) == 2
    assert updates[0].path == "product.name"
    assert updates[0].value == "루미 세럼"
    assert updates[1].path == "goal.video_seconds"
    assert updates[1].value == 12


def test_parse_slot_updates_from_code_fence() -> None:
    raw = """```json
    {"updates":[{"path":"product.price_band","value":"mid","confidence":0.9}]}
    ```"""

    updates = OnboardingDialogueService._parse_slot_updates(raw)

    assert len(updates) == 1
    assert updates[0].path == "product.price_band"
    assert updates[0].value == "mid"
