"""Tests for media service video generation behavior."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.media_service import MediaService


class _FakeResponse:
    def __init__(self, *, json_data: dict | None = None, content: bytes = b"") -> None:
        self._json_data = json_data or {}
        self.content = content

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClientSuccess:
    instances: list["_FakeAsyncClientSuccess"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.post_files = None
        self.status_get_count = 0
        _FakeAsyncClientSuccess.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, headers=None, files=None):
        self.post_files = files
        return _FakeResponse(json_data={"id": "video_test_job"})

    async def get(self, url: str, headers=None):
        if url.endswith("/content"):
            return _FakeResponse(content=b"fake-mp4")
        self.status_get_count += 1
        return _FakeResponse(json_data={"status": "completed"})


class _FakeAsyncClientQueued:
    instances: list["_FakeAsyncClientQueued"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.status_get_count = 0
        _FakeAsyncClientQueued.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, headers=None, files=None):
        return _FakeResponse(json_data={"id": "video_test_job"})

    async def get(self, url: str, headers=None):
        self.status_get_count += 1
        return _FakeResponse(json_data={"status": "queued"})


class MediaServiceVideoTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_video_normalizes_seconds_to_supported_value(self) -> None:
        """Sora supports only specific durations, so 6s should be normalized."""
        _FakeAsyncClientSuccess.instances.clear()
        service = MediaService()
        service._api_key = "test-key"

        with (
            patch("app.services.media_service.httpx.AsyncClient", _FakeAsyncClientSuccess),
            patch.object(service, "_save_bytes_locally", return_value=Path("video.mp4")),
        ):
            result = await service.generate_video(prompt="test prompt", seconds=6)

        self.assertEqual("/static/assets/video.mp4", result)
        sent_seconds = _FakeAsyncClientSuccess.instances[0].post_files["seconds"][1]
        self.assertEqual("5", sent_seconds)

    async def test_generate_video_polls_beyond_20_attempts_before_timeout(self) -> None:
        """Video jobs can exceed 100 seconds, so polling should exceed 20 attempts."""
        _FakeAsyncClientQueued.instances.clear()
        service = MediaService()
        service._api_key = "test-key"

        with (
            patch("app.services.media_service.httpx.AsyncClient", _FakeAsyncClientQueued),
            patch("app.services.media_service.asyncio.sleep", AsyncMock()),
        ):
            result = await service.generate_video(prompt="test prompt", seconds=8)

        self.assertIsNone(result)
        self.assertGreater(_FakeAsyncClientQueued.instances[0].status_get_count, 20)

