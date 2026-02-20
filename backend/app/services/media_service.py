"""Service for generating marketing media assets using AI."""

from __future__ import annotations

import asyncio
import base64
import logging
from asyncio.subprocess import PIPE
from pathlib import Path
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
SUPPORTED_VIDEO_SECONDS = (4, 8, 12)
# Keep video generation quality consistent by pinning to the highest-quality model.
VIDEO_MODEL_CANDIDATES = ("sora-2-pro",)
VIDEO_SIZE_CANDIDATES = ("1280x720", "720x1280", "1792x1024", "1024x1792")
VIDEO_POLL_INTERVAL_MS = 4_000
VIDEO_POLL_TIMEOUT_SECONDS = 600
DEFAULT_ENHANCE_SIZE = "1280x720"

class MediaService:
    """Service to handle image and video generation."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._image_model = settings.openai_image_model
        self._client = AsyncOpenAI(api_key=self._api_key)
        # Keep generated assets aligned with FastAPI static mount: backend/static
        self._assets_dir = Path(__file__).resolve().parents[2] / "static" / "assets"
        self._assets_dir.mkdir(parents=True, exist_ok=True)

    async def generate_poster(
        self,
        headline: str,
        brief: str,
        keywords: list[str],
        *,
        reference_image_url: str | None = None,
        reference_notes: str | None = None,
    ) -> str | None:
        """Generate a poster image using gpt-image-1.5."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is missing; poster generation skipped")
            return None

        keyword_text = ", ".join(keywords) if keywords else "미니멀, 상업적, 제품 중심"
        reference_hint_lines: list[str] = []
        if reference_notes:
            reference_hint_lines.append(f"Reference Visual Notes: {reference_notes}")
        if reference_image_url:
            reference_hint_lines.append(
                "If a reference product image is provided, preserve core product identity "
                "(shape, packaging tone, logo placement cues, and category feel)."
            )
        reference_hints = "\n".join(reference_hint_lines)

        prompt = f"""
        Professional marketing poster for a product launch.
        Headline: {headline}
        Brief: {brief}
        Visual Style Keywords: {keyword_text}
        {reference_hints}
        Clean, modern, high-quality, product-focused, commercial photography style.
        No text in the image except for the overall vibe and aesthetic.
        """.strip()

        try:
            logger.info("Generating poster image with %s...", self._image_model)
            response = None
            reference_path = self._resolve_local_reference_image(reference_image_url)
            if reference_path is not None:
                logger.info("Using product reference image for poster generation: %s", reference_path)
                try:
                    with reference_path.open("rb") as image_file:
                        response = await self._client.images.edit(
                            model=self._image_model,
                            image=image_file,
                            prompt=prompt,
                            size="1024x1024",
                            quality="auto",
                            n=1,
                        )
                except Exception:
                    logger.exception(
                        "images.edit failed; fallback to text-only poster generation"
                    )

            if response is None:
                response = await self._client.images.generate(
                    model=self._image_model,
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

    def _resolve_local_reference_image(self, reference_image_url: str | None) -> Path | None:
        if not reference_image_url:
            return None
        if not reference_image_url.startswith("/static/assets/"):
            return None
        safe_name = Path(reference_image_url).name
        if not safe_name:
            return None
        candidate = self._assets_dir / safe_name
        if candidate.exists() and candidate.is_file():
            return candidate
        return None

    async def generate_video(
        self,
        prompt: str,
        seconds: int = 15,
        *,
        strict_sora: bool = False,
        reference_image_url: str | None = None,
        reference_notes: str | None = None,
    ) -> str | None:
        """Generate a short video using OpenAI Video API."""
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is missing; video generation skipped")
            return None

        safe_seconds = self._normalize_video_seconds(seconds)
        video_prompt = self._build_video_prompt(
            prompt=prompt,
            reference_image_url=reference_image_url,
            reference_notes=reference_notes,
        )
        reference_path = self._resolve_local_reference_image(reference_image_url)
        if reference_path is not None:
            logger.info("Using product reference image for video generation: %s", reference_path)
        prepared_reference_by_size: dict[str, Path | None] = {}
        last_error: str | None = None
        for model_name in VIDEO_MODEL_CANDIDATES:
            for size in VIDEO_SIZE_CANDIDATES:
                try:
                    logger.info(
                        "Generating video with OpenAI Video API model=%s, seconds=%s, size=%s",
                        model_name,
                        safe_seconds,
                        size,
                    )
                    request_kwargs: dict[str, object] = {
                        "model": model_name,
                        "prompt": video_prompt,
                        "seconds": str(safe_seconds),
                        "size": size,
                        "poll_interval_ms": VIDEO_POLL_INTERVAL_MS,
                    }
                    if reference_path is not None:
                        if size not in prepared_reference_by_size:
                            prepared_reference_by_size[size] = await self._prepare_video_reference_image(
                                source_path=reference_path,
                                target_size=size,
                            )
                        prepared_reference = prepared_reference_by_size[size]
                        if prepared_reference is None:
                            logger.warning(
                                "Skipping video request because reference preparation failed (model=%s, size=%s)",
                                model_name,
                                size,
                            )
                            continue
                        request_kwargs["input_reference"] = prepared_reference

                    video = await asyncio.wait_for(
                        self._client.videos.create_and_poll(**request_kwargs),
                        timeout=VIDEO_POLL_TIMEOUT_SECONDS,
                    )
                    status = getattr(video, "status", None)
                    if status != "completed":
                        failure_reason = getattr(video, "failure_reason", None)
                        logger.warning(
                            "Video generation did not complete (model=%s, size=%s, status=%s, reason=%s)",
                            model_name,
                            size,
                            status,
                            failure_reason,
                        )
                        continue

                    content = await self._client.videos.download_content(video.id, variant="video")
                    video_bytes = content.content
                    if not video_bytes:
                        logger.warning(
                            "Video content is empty for id=%s (model=%s, size=%s)",
                            video.id,
                            model_name,
                            size,
                        )
                        continue

                    raw_path = self._save_bytes_locally(
                        video_bytes,
                        "video_raw",
                        extension=".mp4",
                    )
                    target_size = await self._select_enhancement_target_size(raw_path)
                    enhanced_path = await self._enhance_video_file(
                        source_path=raw_path,
                        target_size=target_size,
                    )
                    if enhanced_path is not None:
                        return f"/static/assets/{enhanced_path.name}"
                    return f"/static/assets/{raw_path.name}"
                except Exception as exc:
                    last_error = str(exc)
                    logger.exception(
                        "Failed to generate video with model=%s, size=%s",
                        model_name,
                        size,
                    )

        if strict_sora:
            if last_error:
                logger.warning(
                    "Video API models failed in strict_sora mode. Last error: %s",
                    last_error,
                )
            else:
                logger.warning("Video API models failed in strict_sora mode.")
            return None

        logger.warning("Video API models failed. Falling back to image-to-video composition.")
        fallback_kwargs: dict[str, object] = {
            "prompt": video_prompt,
            "seconds": safe_seconds,
        }
        if reference_image_url:
            fallback_kwargs["reference_image_url"] = reference_image_url
        if reference_notes:
            fallback_kwargs["reference_notes"] = reference_notes
        fallback_video_url = await self._generate_video_via_image_fallback(**fallback_kwargs)
        if fallback_video_url:
            return fallback_video_url

        if last_error:
            logger.warning("Video generation failed for all models. Last error: %s", last_error)
        return None

    async def _prepare_video_reference_image(self, *, source_path: Path, target_size: str) -> Path | None:
        """Prepare reference image to exactly match Sora requested dimensions."""
        width, height = self._parse_size(target_size)
        prepared_path = self._assets_dir / f"video_ref_{width}x{height}_{uuid4().hex}.png"
        filter_chain = (
            f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            "format=rgb24"
        )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vf",
            filter_chain,
            "-frames:v",
            "1",
            str(prepared_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.warning(
                "Failed to prepare reference image for Sora (size=%s): %s",
                target_size,
                stderr.decode("utf-8", errors="ignore"),
            )
            return None
        return prepared_path

    def _build_video_prompt(
        self,
        *,
        prompt: str,
        reference_image_url: str | None,
        reference_notes: str | None,
    ) -> str:
        reference_lines: list[str] = []
        if reference_image_url:
            reference_lines.append(
                "Preserve exact product identity from the provided product reference image "
                "(shape, packaging tone, material cues, and logo placement cues)."
            )
        if reference_notes:
            reference_lines.append(f"Reference visual notes: {reference_notes}")
        if not reference_lines:
            return prompt
        return f"{prompt}\n" + "\n".join(reference_lines)

    async def _generate_video_via_image_fallback(
        self,
        *,
        prompt: str,
        seconds: int,
        reference_image_url: str | None = None,
        reference_notes: str | None = None,
    ) -> str | None:
        """Fallback: generate an AI keyframe image and render it into mp4 with ffmpeg."""
        frame_prompt_parts = [
            "Create a cinematic commercial keyframe for a product launch video.",
            "No text overlay, no watermark, clean product focus.",
            f"Scene direction: {prompt}",
        ]
        if reference_notes:
            frame_prompt_parts.append(f"Reference visual notes: {reference_notes}")
        frame_prompt = " ".join(frame_prompt_parts)

        reference_path = self._resolve_local_reference_image(reference_image_url)
        image_response = None
        try:
            if reference_path is not None:
                logger.info("Using product reference image for fallback keyframe: %s", reference_path)
                try:
                    with reference_path.open("rb") as image_file:
                        image_response = await self._client.images.edit(
                            model=self._image_model,
                            image=image_file,
                            prompt=frame_prompt,
                            size="1536x1024",
                            quality="auto",
                            n=1,
                        )
                except Exception:
                    logger.exception("Fallback images.edit failed; retry with text-only keyframe prompt")

            if image_response is None:
                image_response = await self._client.images.generate(
                    model=self._image_model,
                    prompt=frame_prompt,
                    size="1536x1024",
                    quality="auto",
                    n=1,
                )
        except Exception:
            logger.exception("Fallback keyframe generation failed")
            return None

        image_item = image_response.data[0]
        image_url = getattr(image_item, "url", None)
        image_b64 = getattr(image_item, "b64_json", None)

        frame_path: Path | None = None
        if image_url:
            try:
                frame_path = await self._save_locally(image_url, "video_frame")
            except Exception:
                logger.exception("Failed to download fallback keyframe image")
                return None
        elif image_b64:
            frame_path = self._save_b64_locally(image_b64, "video_frame", extension=".png")
        else:
            logger.warning("Fallback keyframe image response did not include url or b64_json")
            return None

        output_path = self._assets_dir / f"video_{uuid4().hex}.mp4"
        duration = max(4, min(12, int(seconds)))
        fade_out_start = max(0.0, duration - 0.7)
        video_filter = (
            "scale=2048:1152:flags=lanczos:force_original_aspect_ratio=increase,"
            "crop=1920:1080:"
            "x=(in_w-out_w)/2+sin(t*0.7)*28:"
            "y=(in_h-out_h)/2+cos(t*0.5)*14,"
            "eq=contrast=1.03:saturation=1.05,"
            "unsharp=5:5:0.55:5:5:0.0,"
            "fade=t=in:st=0:d=0.5,"
            f"fade=t=out:st={fade_out_start}:d=0.6,"
            "format=yuv420p"
        )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(frame_path),
            "-t",
            str(duration),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-maxrate",
            "14M",
            "-bufsize",
            "28M",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(
                "ffmpeg fallback video render failed (exit=%s): %s",
                process.returncode,
                stderr.decode("utf-8", errors="ignore"),
            )
            return None

        logger.info("Fallback image-to-video render completed: %s", output_path)
        return f"/static/assets/{output_path.name}"

    async def _enhance_video_file(
        self,
        *,
        source_path: Path,
        target_size: str,
    ) -> Path | None:
        """Re-encode generated videos for a sharper and more stable delivery quality."""
        width, height = self._parse_size(target_size)
        output_path = self._assets_dir / f"video_{uuid4().hex}.mp4"
        video_filter = (
            f"scale={width}:{height}:flags=lanczos:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            "eq=contrast=1.02:saturation=1.04,"
            "unsharp=5:5:0.5:5:5:0.0,"
            "format=yuv420p"
        )

        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-maxrate",
            "14M",
            "-bufsize",
            "28M",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            logger.warning(
                "Video post-processing failed for %s: %s",
                source_path,
                stderr.decode("utf-8", errors="ignore"),
            )
            return None

        logger.info("Video post-processing completed: %s", output_path)
        return output_path

    async def _select_enhancement_target_size(self, source_path: Path) -> str:
        """Prefer source-native resolution to avoid artificial upscaling blur."""
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(source_path),
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.warning(
                "ffprobe failed for %s, using default enhance size (%s): %s",
                source_path,
                DEFAULT_ENHANCE_SIZE,
                stderr.decode("utf-8", errors="ignore"),
            )
            return DEFAULT_ENHANCE_SIZE

        text = stdout.decode("utf-8", errors="ignore").strip()
        width_text, _, height_text = text.partition("x")
        try:
            width = int(width_text.strip())
            height = int(height_text.strip())
        except ValueError:
            logger.warning(
                "Could not parse ffprobe size output '%s' for %s, using default (%s)",
                text,
                source_path,
                DEFAULT_ENHANCE_SIZE,
            )
            return DEFAULT_ENHANCE_SIZE
        return self._derive_enhancement_target_size(width, height)

    @staticmethod
    def _derive_enhancement_target_size(width: int, height: int) -> str:
        safe_width = max(2, int(width))
        safe_height = max(2, int(height))

        if safe_width % 2 != 0:
            safe_width -= 1
        if safe_height % 2 != 0:
            safe_height -= 1

        long_edge = max(safe_width, safe_height)
        if long_edge > 1920:
            scale = 1920 / long_edge
            safe_width = max(2, int(round(safe_width * scale)))
            safe_height = max(2, int(round(safe_height * scale)))
            if safe_width % 2 != 0:
                safe_width -= 1
            if safe_height % 2 != 0:
                safe_height -= 1

        return f"{safe_width}x{safe_height}"

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
    def _parse_size(value: str) -> tuple[int, int]:
        width_text, _, height_text = value.partition("x")
        width = int(width_text.strip())
        height = int(height_text.strip())
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid size value: {value}")
        return width, height

    @staticmethod
    def _normalize_video_seconds(seconds: int) -> int:
        try:
            requested = int(seconds)
        except (TypeError, ValueError):
            requested = SUPPORTED_VIDEO_SECONDS[0]
        return min(
            SUPPORTED_VIDEO_SECONDS,
            key=lambda allowed: (abs(allowed - requested), allowed),
        )
