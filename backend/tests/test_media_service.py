"""Tests for media service video generation behavior."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.media_service import MediaService, VIDEO_MODEL_CANDIDATES, VIDEO_SIZE_CANDIDATES


class _FakeVideo:
    def __init__(self, video_id: str, status: str = "completed") -> None:
        self.id = video_id
        self.status = status


class _FakeBinaryContent:
    def __init__(self, content: bytes) -> None:
        self.content = content


class MediaServiceVideoTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_video_normalizes_seconds_and_downloads_content(self) -> None:
        service = MediaService()
        service._api_key = "test-key"

        create_and_poll = AsyncMock(return_value=_FakeVideo("video_test_job", "completed"))
        download_content = AsyncMock(return_value=_FakeBinaryContent(b"fake-mp4"))

        with (
            patch.object(service._client.videos, "create_and_poll", create_and_poll),
            patch.object(service._client.videos, "download_content", download_content),
            patch.object(service, "_save_bytes_locally", return_value=Path("video_raw.mp4")),
            patch.object(service, "_enhance_video_file", AsyncMock(return_value=Path("video.mp4"))),
        ):
            result = await service.generate_video(prompt="test prompt", seconds=6)

        self.assertEqual("/static/assets/video.mp4", result)
        create_and_poll.assert_awaited_once()
        kwargs = create_and_poll.await_args.kwargs
        self.assertEqual("4", kwargs["seconds"])
        self.assertEqual(VIDEO_SIZE_CANDIDATES[0], kwargs["size"])
        download_content.assert_awaited_once_with("video_test_job", variant="video")

    async def test_generate_video_passes_input_reference_when_available(self) -> None:
        service = MediaService()
        service._api_key = "test-key"

        create_and_poll = AsyncMock(return_value=_FakeVideo("video_test_job", "completed"))
        download_content = AsyncMock(return_value=_FakeBinaryContent(b"fake-mp4"))
        reference_path = Path("product_ref.png")
        prepared_reference_path = Path("product_ref_1280x720.png")

        with (
            patch.object(service, "_resolve_local_reference_image", return_value=reference_path),
            patch.object(
                service,
                "_prepare_video_reference_image",
                AsyncMock(return_value=prepared_reference_path),
            ) as prepare_reference,
            patch.object(service._client.videos, "create_and_poll", create_and_poll),
            patch.object(service._client.videos, "download_content", download_content),
            patch.object(service, "_save_bytes_locally", return_value=Path("video_raw.mp4")),
            patch.object(service, "_enhance_video_file", AsyncMock(return_value=Path("video.mp4"))),
        ):
            result = await service.generate_video(
                prompt="test prompt",
                seconds=8,
                reference_image_url="/static/assets/product_ref.png",
            )

        self.assertEqual("/static/assets/video.mp4", result)
        kwargs = create_and_poll.await_args.kwargs
        self.assertEqual(prepared_reference_path, kwargs["input_reference"])
        prepare_reference.assert_awaited_once_with(source_path=reference_path, target_size=VIDEO_SIZE_CANDIDATES[0])

    async def test_generate_video_uses_image_fallback_when_video_models_fail(self) -> None:
        service = MediaService()
        service._api_key = "test-key"

        create_and_poll = AsyncMock(side_effect=Exception("all-models-failed"))
        fallback = AsyncMock(return_value="/static/assets/video_fallback.mp4")

        with (
            patch.object(service._client.videos, "create_and_poll", create_and_poll),
            patch.object(service, "_generate_video_via_image_fallback", fallback),
        ):
            result = await service.generate_video(prompt="test prompt", seconds=8)

        self.assertEqual("/static/assets/video_fallback.mp4", result)
        self.assertEqual(
            create_and_poll.await_count,
            len(VIDEO_MODEL_CANDIDATES) * len(VIDEO_SIZE_CANDIDATES),
        )
        fallback.assert_awaited_once_with(prompt="test prompt", seconds=8)

    async def test_generate_video_forwards_reference_to_fallback(self) -> None:
        service = MediaService()
        service._api_key = "test-key"

        create_and_poll = AsyncMock(side_effect=Exception("all-models-failed"))
        fallback = AsyncMock(return_value="/static/assets/video_fallback.mp4")

        with (
            patch.object(service._client.videos, "create_and_poll", create_and_poll),
            patch.object(service, "_generate_video_via_image_fallback", fallback),
        ):
            result = await service.generate_video(
                prompt="test prompt",
                seconds=8,
                reference_image_url="/static/assets/product_ref.png",
                reference_notes="mint packaging",
            )

        self.assertEqual("/static/assets/video_fallback.mp4", result)
        kwargs = fallback.await_args.kwargs
        self.assertEqual("/static/assets/product_ref.png", kwargs["reference_image_url"])
        self.assertEqual("mint packaging", kwargs["reference_notes"])
        self.assertIn("Reference visual notes: mint packaging", kwargs["prompt"])
        self.assertIn("Preserve exact product identity", kwargs["prompt"])

    async def test_generate_video_returns_none_when_all_paths_fail(self) -> None:
        service = MediaService()
        service._api_key = "test-key"

        create_and_poll = AsyncMock(side_effect=Exception("all-models-failed"))
        fallback = AsyncMock(return_value=None)

        with (
            patch.object(service._client.videos, "create_and_poll", create_and_poll),
            patch.object(service, "_generate_video_via_image_fallback", fallback),
        ):
            result = await service.generate_video(prompt="test prompt", seconds=12)

        self.assertIsNone(result)
        self.assertEqual(
            create_and_poll.await_count,
            len(VIDEO_MODEL_CANDIDATES) * len(VIDEO_SIZE_CANDIDATES),
        )
        fallback.assert_awaited_once_with(prompt="test prompt", seconds=12)
