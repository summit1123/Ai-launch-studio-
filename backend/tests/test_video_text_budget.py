"""Tests for video narration/scene text budgeting."""

from __future__ import annotations

from app.agents.orchestrator import MainOrchestrator


def test_fit_narration_to_duration_caps_length_for_12s() -> None:
    raw = (
        "지금 소개할 제품은 매일 사용하는 동안 빠르게 흡수되고 피부 밸런스를 안정적으로 잡아주며 "
        "아침과 저녁 모두 부담 없이 사용할 수 있도록 설계되었습니다. "
        "오늘부터 바로 시작해보세요."
    )
    fitted = MainOrchestrator._fit_narration_to_duration(
        narration_script=raw,
        cta_line="지금 시작해보세요",
        seconds=12,
    )
    budget = MainOrchestrator._video_budget(12)
    assert len(fitted) <= budget["max_chars"]
    assert fitted.strip()


def test_fit_narration_to_duration_falls_back_when_empty() -> None:
    fitted = MainOrchestrator._fit_narration_to_duration(
        narration_script="",
        cta_line="",
        seconds=4,
    )
    budget = MainOrchestrator._video_budget(4)
    assert fitted
    assert len(fitted) <= budget["max_chars"]


def test_fit_scene_plan_caps_item_count_and_length() -> None:
    scene_plan = [
        "1) 0-2초: 제품 패키지 디테일을 아주 길고 자세하게 설명하는 훅 장면",
        "2) 2-4초: 사용 장면에서 텍스처와 흡수 과정을 상세하게 보여주는 장면",
        "3) 4-6초: 전후 대비를 길게 말하는 장면",
        "4) 6-8초: 핵심 효능을 강조하는 장면",
        "5) 8-10초: 신뢰 요소를 제시하는 장면",
        "6) 10-12초: CTA 마무리",
    ]

    fitted = MainOrchestrator._fit_scene_plan(scene_plan=scene_plan, seconds=8)
    budget = MainOrchestrator._video_budget(8)
    assert 1 <= len(fitted) <= budget["max_scenes"]
    assert all(0 < len(item) <= budget["scene_chars"] for item in fitted)
