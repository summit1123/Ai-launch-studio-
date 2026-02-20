"""Tests for supported video duration normalization."""

from __future__ import annotations

from app.services.media_service import MediaService


def test_normalize_video_seconds_to_supported_values() -> None:
    assert MediaService._normalize_video_seconds(4) == 4
    assert MediaService._normalize_video_seconds(8) == 8
    assert MediaService._normalize_video_seconds(12) == 12


def test_normalize_video_seconds_rounds_to_nearest_supported_value() -> None:
    assert MediaService._normalize_video_seconds(5) == 4
    assert MediaService._normalize_video_seconds(6) == 4
    assert MediaService._normalize_video_seconds(7) == 8
    assert MediaService._normalize_video_seconds(10) == 8
    assert MediaService._normalize_video_seconds(11) == 12
    assert MediaService._normalize_video_seconds(13) == 12


def test_normalize_video_seconds_handles_invalid_input() -> None:
    assert MediaService._normalize_video_seconds(0) == 4
    assert MediaService._normalize_video_seconds(-10) == 4
    assert MediaService._normalize_video_seconds("abc") == 4  # type: ignore[arg-type]
