"""Tests for supported video duration normalization."""

from __future__ import annotations

from app.services.media_service import MediaService


def test_normalize_video_seconds_to_supported_values() -> None:
    assert MediaService._normalize_video_seconds(5) == 5
    assert MediaService._normalize_video_seconds(10) == 10
    assert MediaService._normalize_video_seconds(15) == 15
    assert MediaService._normalize_video_seconds(20) == 20


def test_normalize_video_seconds_rounds_to_nearest_supported_value() -> None:
    assert MediaService._normalize_video_seconds(6) == 5
    assert MediaService._normalize_video_seconds(8) == 10
    assert MediaService._normalize_video_seconds(12) == 10
    assert MediaService._normalize_video_seconds(13) == 15
    assert MediaService._normalize_video_seconds(19) == 20


def test_normalize_video_seconds_handles_invalid_input() -> None:
    assert MediaService._normalize_video_seconds(0) == 5
    assert MediaService._normalize_video_seconds(-10) == 5
    assert MediaService._normalize_video_seconds("abc") == 5  # type: ignore[arg-type]
