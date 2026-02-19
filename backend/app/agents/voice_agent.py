"""Voice interaction preset agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


VoicePreset = Literal["friendly_ko", "calm_ko", "neutral_ko"]


@dataclass(frozen=True)
class VoicePresetConfig:
    label: str
    pace: str
    prefix: str


class VoiceAgent:
    """Builds assistant question text with preset-specific tone."""

    PRESETS: dict[VoicePreset, VoicePresetConfig] = {
        "friendly_ko": VoicePresetConfig(
            label="친근형",
            pace="medium",
            prefix="좋아요.",
        ),
        "calm_ko": VoicePresetConfig(
            label="차분형",
            pace="slow",
            prefix="천천히 정리해볼게요.",
        ),
        "neutral_ko": VoicePresetConfig(
            label="중립형",
            pace="medium",
            prefix="다음 정보를 확인하겠습니다.",
        ),
    }

    def resolve_preset(self, preset: str | None) -> VoicePreset:
        if preset in self.PRESETS:
            return preset
        return "friendly_ko"

    def format_question(self, *, question: str, preset: str | None) -> str:
        normalized = self.resolve_preset(preset)
        config = self.PRESETS[normalized]
        stripped = question.strip()
        if not stripped:
            return config.prefix
        if stripped.startswith(config.prefix):
            return stripped
        return f"{config.prefix} {stripped}"

    def tts_profile(self, preset: str | None) -> dict[str, str]:
        normalized = self.resolve_preset(preset)
        config = self.PRESETS[normalized]
        return {
            "preset": normalized,
            "label": config.label,
            "pace": config.pace,
        }
