"""Service for generating marketing media assets using AI."""

from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
SUPPORTED_VIDEO_SECONDS = (4, 8, 12)
VIDEO_POLL_INTERVAL_SECONDS = 5
VIDEO_MAX_POLLS = 72

class MediaService:
    """Service to handle image and video generation."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._client = AsyncOpenAI(api_key=self._api_key)
        # Keep generated assets aligned with FastAPI static mount: backend/static
        self._assets_dir = Path(__file__).resolve().parents[2] / "static" / "assets"
        self._assets_dir.mkdir(parents=True, exist_ok=True)

    async def generate_poster(self, headline: str, brief: str, keywords: list[str]) -> str | None:
        """Generate a poster image using gpt-image-1.5."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is missing; poster generation skipped")
            return None

        prompt = f"""
        Professional marketing poster for a product launch.
        Headline: {headline}
        Brief: {brief}
        Visual Style Keywords: {', '.join(keywords)}
        Clean, modern, high-quality, product-focused, commercial photography style.
        No text in the image except for the overall vibe and aesthetic.
        """.strip()

        try:
            logger.info("Generating poster image with gpt-image-1.5...")
            response = await self._client.images.generate(
                model="gpt-image-1.5",
                prompt=prompt,
                size="1024x1024",
                quality="auto",
                n=1,
            )
            image_item = response.data[0]
            image_url = getattr(image_item, "url", None)
            image_b64 = getattr(image_item, "b64_json", None)

            if image_url:
                local_path = await self._save_locally(image_url, "poster")
                return f"/static/assets/{local_path.name}"

            if image_b64:
                local_path = self._save_b64_locally(image_b64, "poster", extension=".png")
                return f"/static/assets/{local_path.name}"

            logger.warning("Image response did not include url or b64_json")
            return None
        except Exception:
            logger.exception("Failed to generate poster image")
            return None

    async def generate_video(self, prompt: str, seconds: int = 15) -> str | None:
        """Generate a short video using OpenAI Sora (sora-2) with polling."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is missing; video generation skipped")
            return None

        try:
            safe_seconds = self._normalize_video_seconds(seconds)
            logger.info("Generating video with OpenAI Sora (sora-2), seconds=%s...", safe_seconds)
            async with httpx.AsyncClient(timeout=180) as client:
                headers = {
                    "Authorization": f"Bearer {self._api_key}"
                }
                # Sora API uses multipart/form-data
                files = {
                    "model": (None, "sora-2"),
                    "prompt": (None, prompt),
                    "seconds": (None, str(safe_seconds)),
                    "size": (None, "1280x720")
                }
                response = await client.post(
                    "https://api.openai.com/v1/videos",
                    headers=headers,
                    files=files
                )
                response.raise_for_status()
                job_data = response.json()
                video_id = job_data.get("id")
                
                if not video_id:
                    return None

                # Polling loop
                logger.info(f"Video job submitted: {video_id}. Polling for completion...")
                for _ in range(VIDEO_MAX_POLLS):
                    await asyncio.sleep(VIDEO_POLL_INTERVAL_SECONDS)
                    status_resp = await client.get(
                        f"https://api.openai.com/v1/videos/{video_id}",
                        headers=headers
                    )
                    status_resp.raise_for_status()
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    
                    if status == "completed":
                        content_resp = await client.get(
                            f"https://api.openai.com/v1/videos/{video_id}/content",
                            headers=headers,
                        )
                        content_resp.raise_for_status()
                        local_path = self._save_bytes_locally(
                            content_resp.content,
                            "video",
                            extension=".mp4",
                        )
                        return f"/static/assets/{local_path.name}"
                    elif status == "failed":
                        logger.error(f"Video generation failed for job {video_id}")
                        return None

                logger.warning(
                    "Video generation polling timed out for job %s after %s seconds",
                    video_id,
                    VIDEO_MAX_POLLS * VIDEO_POLL_INTERVAL_SECONDS,
                )
                return None
        except Exception:
            logger.exception("Failed to generate video with Sora")
            return None

    async def _save_locally(self, url: str, prefix: str, extension: str = ".png") -> Path:
        """Download remote asset and save to local static directory."""
        filename = f"{prefix}_{uuid4().hex}{extension}"
        file_path = self._assets_dir / filename
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_path.write_bytes(resp.content)
            
        logger.info("Saved asset to %s", file_path)
        return file_path

    def _save_bytes_locally(self, data: bytes, prefix: str, extension: str = ".png") -> Path:
        filename = f"{prefix}_{uuid4().hex}{extension}"
        file_path = self._assets_dir / filename
        file_path.write_bytes(data)
        logger.info("Saved asset to %s", file_path)
        return file_path

    def _save_b64_locally(self, b64_data: str, prefix: str, extension: str = ".png") -> Path:
        raw = base64.b64decode(b64_data)
        return self._save_bytes_locally(raw, prefix=prefix, extension=extension)

    @staticmethod
    def _normalize_video_seconds(seconds: int) -> int:
        try:
            requested = int(seconds)
        except (TypeError, ValueError):
            requested = SUPPORTED_VIDEO_SECONDS[0]
        return min(
            SUPPORTED_VIDEO_SECONDS,
            key=lambda allowed: (abs(allowed - requested), -allowed),
        )
