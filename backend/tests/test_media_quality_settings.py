"""Tests for media quality target-size selection helpers."""

from __future__ import annotations

from app.services.media_service import MediaService


def test_derive_enhancement_target_size_keeps_landscape_native() -> None:
    assert MediaService._derive_enhancement_target_size(1280, 720) == "1280x720"


def test_derive_enhancement_target_size_keeps_portrait_native() -> None:
    assert MediaService._derive_enhancement_target_size(720, 1280) == "720x1280"


def test_derive_enhancement_target_size_makes_even_and_caps_long_edge() -> None:
    size = MediaService._derive_enhancement_target_size(3841, 2161)
    width_text, _, height_text = size.partition("x")
    width = int(width_text)
    height = int(height_text)
    assert width % 2 == 0
    assert height % 2 == 0
    assert max(width, height) <= 1920
