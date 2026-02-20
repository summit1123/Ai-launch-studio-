"""Product image upload + vision analysis service."""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class ProductImageAnalysis:
    image_url: str
    image_summary: str | None
    category: str | None
    features: list[str]


class ProductImageService:
    """Stores product image and optionally extracts brief hints with vision model."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self._client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None
        self._assets_dir = Path(__file__).resolve().parents[2] / "static" / "assets"
        self._assets_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def save_and_analyze(
        self,
        *,
        image_bytes: bytes,
        filename: str,
        content_type: str | None,
        locale: str = "ko-KR",
        user_note: str = "",
    ) -> ProductImageAnalysis:
        local_path = self._save_image(image_bytes=image_bytes, filename=filename)
        image_url = f"/static/assets/{local_path.name}"

        if self._client is None:
            return ProductImageAnalysis(
                image_url=image_url,
                image_summary="이미지는 저장했어요. 다음 질문에서 제품 정보를 이어서 입력해 주세요.",
                category=None,
                features=[],
            )

        try:
            parsed = await self._analyze_with_vision(
                image_bytes=image_bytes,
                content_type=content_type or "image/png",
                locale=locale,
                user_note=user_note,
            )
        except Exception:
            logger.exception("Product image analysis failed")
            parsed = None

        return ProductImageAnalysis(
            image_url=image_url,
            image_summary=parsed.get("image_summary") if parsed else None,
            category=parsed.get("category") if parsed else None,
            features=parsed.get("features", []) if parsed else [],
        )

    def _save_image(self, *, image_bytes: bytes, filename: str) -> Path:
        extension = Path(filename).suffix.lower()
        if extension not in _SUPPORTED_IMAGE_EXTENSIONS:
            extension = ".png"
        file_path = self._assets_dir / f"product_ref_{uuid4().hex}{extension}"
        file_path.write_bytes(image_bytes)
        return file_path

    async def _analyze_with_vision(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        locale: str,
        user_note: str,
    ) -> dict[str, object]:
        if self._client is None:
            return {}
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        note_block = user_note.strip() or "없음"
        prompt = (
            "너는 제품 이미지에서 온보딩 브리프 힌트를 추출하는 분석기다.\n"
            "아래 JSON 객체 하나만 출력해라. 다른 문장은 금지.\n"
            "필수 키: image_summary, category, features\n"
            "- image_summary: 한국어 1문장(40자 이내)\n"
            "- category: 한국어 카테고리 1개(추론 불가 시 null)\n"
            "- features: 한국어 핵심 특징 3~5개 배열(짧은 명사구)\n"
            "규칙:\n"
            "1) 과장 표현 금지, 보이는 근거 중심\n"
            "2) 불확실하면 null 또는 빈 배열 사용\n"
            "3) JSON 외 출력 금지\n\n"
            f"locale={locale}\n"
            f"user_note={note_block}\n"
        )

        response = await self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:{content_type};base64,{image_b64}",
                        },
                    ],
                }
            ],
            max_output_tokens=220,
            temperature=0.2,
        )
        raw = self._extract_text(response)
        payload = self._parse_json_payload(raw)
        return {
            "image_summary": self._clean_text(payload.get("image_summary")),
            "category": self._clean_text(payload.get("category")),
            "features": self._clean_features(payload.get("features")),
        }

    @staticmethod
    def _extract_text(response: object) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = getattr(response, "output", None)
        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                content = getattr(item, "content", None)
                if not isinstance(content, list):
                    continue
                for part in content:
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())
            if chunks:
                return " ".join(chunks)
        return ""

    @staticmethod
    def _parse_json_payload(raw: str) -> dict[str, object]:
        if not raw:
            return {}
        candidate = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, flags=re.DOTALL)
        if fenced:
            candidate = fenced.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        brace = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if brace:
            try:
                parsed = json.loads(brace.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _clean_text(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "unknown"}:
            return None
        return cleaned

    @staticmethod
    def _clean_features(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        features: list[str] = []
        seen: set[str] = set()
        for raw in value:
            if not isinstance(raw, str):
                continue
            item = raw.strip()
            key = item.lower()
            if len(item) < 2 or key in seen:
                continue
            seen.add(key)
            features.append(item)
            if len(features) >= 5:
                break
        return features
