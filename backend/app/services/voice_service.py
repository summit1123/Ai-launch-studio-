"""Voice service for STT/TTS."""

from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path
from uuid import uuid4

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VoiceService:
    """Handles speech-to-text and text-to-speech with OpenAI audio APIs."""

    VOICE_MAP = {
        "friendly_ko": "alloy",
        "calm_ko": "ash",
        "neutral_ko": "verse",
    }

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._stt_model = settings.openai_stt_model
        self._tts_model = settings.openai_tts_model
        self._client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self._assets_dir = Path(__file__).resolve().parents[2] / "static" / "assets"
        self._assets_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        locale: str = "ko-KR",
    ) -> str:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is missing")
        if not audio_bytes:
            return ""

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        language = "ko" if locale.lower().startswith("ko") else None
        try:
            response = await self._client.audio.transcriptions.create(
                model=self._stt_model,
                file=audio_file,
                language=language,
            )
            text = getattr(response, "text", "") or ""
            return str(text).strip()
        except Exception:
            logger.exception("Voice transcription failed")
            return ""

    async def synthesize_to_file(
        self,
        *,
        text: str,
        voice_preset: str = "friendly_ko",
        audio_format: str = "mp3",
    ) -> tuple[str, int]:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is missing")

        voice = self.VOICE_MAP.get(voice_preset, "alloy")
        response = await self._client.audio.speech.create(
            model=self._tts_model,
            voice=voice,
            input=text,
            format=audio_format,
        )
        content = await self._read_binary_response(response)
        file_path = self._save_bytes_locally(content=content, extension=f".{audio_format}")
        return f"/static/assets/{file_path.name}", len(content)

    async def _read_binary_response(self, response: object) -> bytes:
        read = getattr(response, "read", None)
        if callable(read):
            raw = read()
            if asyncio.iscoroutine(raw):
                raw = await raw
            if isinstance(raw, bytes):
                return raw

        content = getattr(response, "content", None)
        if isinstance(content, bytes):
            return content

        if isinstance(response, bytes):
            return response

        return b""

    def _save_bytes_locally(self, *, content: bytes, extension: str) -> Path:
        file_name = f"tts_{uuid4().hex}{extension}"
        file_path = self._assets_dir / file_name
        file_path.write_bytes(content)
        return file_path
