"""Main orchestrator for launch package generation."""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

PHASE_TIMEOUT_SECONDS = 180
MAX_RISKS = 10
SUPPORTED_VIDEO_SECONDS = (4, 8, 12)
VIDEO_TEXT_BUDGET: dict[int, dict[str, int]] = {
    4: {
        "max_chars": 28,
        "max_sentences": 1,
        "max_scenes": 3,
        "scene_chars": 26,
        "cta_chars": 8,
    },
    8: {
        "max_chars": 56,
        "max_sentences": 2,
        "max_scenes": 4,
        "scene_chars": 34,
        "cta_chars": 12,
    },
    12: {
        "max_chars": 84,
        "max_sentences": 3,
        "max_scenes": 5,
        "scene_chars": 42,
        "cta_chars": 14,
    },
}

from app.agents.biz_planning_agent import BizPlanningAgent
from app.agents.dev_agent import DevAgent
from app.agents.marketer_agent import MarketerAgent
from app.agents.md_agent import MDAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.poster_agent import PosterAgent
from app.agents.product_copy_agent import ProductCopyAgent
from app.agents.research_agent import ResearchAgent
from app.agents.video_producer_agent import VideoProducerAgent
from app.schemas import (
    AgentEnvelope,
    AgentPayload,
    LaunchPackage,
    LaunchRunRequest,
    MarketingAssets,
)
from app.services import AgentRuntime, MediaService


class MainOrchestrator:
    """Coordinates all studio agents and composes launch package output."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime
        self._media = MediaService()
        self._research = ResearchAgent(runtime)
        self._md = MDAgent(runtime)
        self._dev = DevAgent(runtime)
        self._planner = PlannerAgent(runtime)
        self._marketer = MarketerAgent(runtime)
        self._biz = BizPlanningAgent(runtime)
        self._video = VideoProducerAgent(runtime)
        self._poster = PosterAgent(runtime)
        self._product_copy = ProductCopyAgent(runtime)

    async def run(
        self,
        request: LaunchRunRequest,
        *,
        include_media: bool = True,
        progress_callback: Callable[[int, str], Awaitable[None] | None] | None = None,
    ) -> LaunchPackage:
        brief = request.brief
        timeline: list[AgentEnvelope] = []
        t0 = time.monotonic()
        await self._emit_progress(progress_callback, 15, "리서치/MD/기술 에이전트를 호출했습니다.")

        logger.info("[Phase 1] Starting parallel analysis for '%s'", brief.product_name)
        research, md, dev = await asyncio.wait_for(
            asyncio.gather(
                self._research.run(brief),
                self._md.run(brief),
                self._dev.run(brief),
            ),
            timeout=PHASE_TIMEOUT_SECONDS,
        )
        logger.info("[Phase 1] Completed in %.1fs", time.monotonic() - t0)
        await self._emit_progress(progress_callback, 35, "리서치 분석이 완료되어 전략 수립 단계로 이동합니다.")
        timeline.extend(
            [
                AgentEnvelope(agent="Research Agent", stage="phase1_parallel", payload=research),
                AgentEnvelope(agent="MD Agent", stage="phase1_parallel", payload=md),
                AgentEnvelope(agent="Dev Agent", stage="phase1_parallel", payload=dev),
            ]
        )

        synthesis_context = self._context_block(
            [
                ("Research", research),
                ("MD", md),
                ("Dev", dev),
            ]
        )
        t1 = time.monotonic()
        logger.info("[Phase 2] Starting synthesis")
        await self._emit_progress(progress_callback, 45, "플래너/마케터/비즈 에이전트가 전략을 종합하고 있습니다.")
        planner, marketer, biz = await asyncio.wait_for(
            asyncio.gather(
                self._planner.run(brief, synthesis_context),
                self._marketer.run(brief, synthesis_context),
                self._biz.run(brief, synthesis_context),
            ),
            timeout=PHASE_TIMEOUT_SECONDS,
        )
        logger.info("[Phase 2] Completed in %.1fs", time.monotonic() - t1)
        await self._emit_progress(progress_callback, 65, "전략 종합이 완료되었습니다. 크리에이티브 초안을 작성합니다.")
        timeline.extend(
            [
                AgentEnvelope(agent="Planner Agent", stage="phase2_synthesis", payload=planner),
                AgentEnvelope(agent="Marketer Agent", stage="phase2_synthesis", payload=marketer),
                AgentEnvelope(
                    agent="Biz Planning Agent",
                    stage="phase2_synthesis",
                    payload=biz,
                ),
            ]
        )

        marketing_context = self._context_block(
            [
                ("Marketer", marketer),
                ("Planner", planner),
            ]
        )
        md_context = self._context_block(
            [
                ("MD", md),
                ("Marketer", marketer),
            ]
        )
        t2 = time.monotonic()
        logger.info("[Phase 3] Starting asset generation")
        await self._emit_progress(progress_callback, 75, "비디오/포스터/카피 에이전트가 초안을 생성하고 있습니다.")
        video, poster, product_copy = await asyncio.wait_for(
            asyncio.gather(
                self._video.run(brief, marketing_context),
                self._poster.run(brief, marketing_context),
                self._product_copy.run(brief, md_context),
            ),
            timeout=PHASE_TIMEOUT_SECONDS,
        )
        logger.info("[Phase 3] Completed in %.1fs", time.monotonic() - t2)
        await self._emit_progress(progress_callback, 88, "에이전트 초안 정리가 완료되었습니다.")
        timeline.extend(
            [
                AgentEnvelope(agent="Video Producer Agent", stage="phase3_assets", payload=video),
                AgentEnvelope(agent="Poster Agent", stage="phase3_assets", payload=poster),
                AgentEnvelope(agent="Product Copy Agent", stage="phase3_assets", payload=product_copy),
            ]
        )
        fitted_video_script = self._fit_narration_to_duration(
            narration_script=video.narration_script or video.summary,
            cta_line=video.cta_line,
            seconds=brief.video_seconds,
        )
        fitted_scene_plan = self._fit_scene_plan(
            scene_plan=video.scene_plan,
            seconds=brief.video_seconds,
        )

        poster_image_url = None
        video_url = None
        if include_media:
            await self._emit_progress(
                progress_callback,
                93,
                "포스터/영상 생성 모델을 실행하고 있습니다. 고화질 영상은 2~3분 정도 소요될 수 있습니다.",
            )
            poster_image_url = await self._media.generate_poster(
                headline=poster.headline,
                brief=poster.subheadline or poster.summary,
                keywords=poster.key_visual_keywords,
                reference_image_url=brief.product_image_url,
                reference_notes=brief.product_image_context,
            )
            video_url = await self._media.generate_video(
                prompt=self._compose_video_generation_prompt(
                    product_name=brief.product_name,
                    narration_script=fitted_video_script,
                    seconds=brief.video_seconds,
                ),
                seconds=brief.video_seconds,
                strict_sora=True,
                reference_image_url=brief.product_image_url,
                reference_notes=brief.product_image_context,
            )
            await self._emit_progress(progress_callback, 96, "미디어 생성 결과를 패키지에 병합하고 있습니다.")

        package = LaunchPackage(
            request_id=str(uuid4()),
            brief=brief,
            research_summary=research,
            product_strategy=md,
            technical_plan=dev,
            launch_plan=planner,
            campaign_strategy=marketer,
            budget_and_kpi=biz,
            marketing_assets=MarketingAssets(
                video_script=fitted_video_script,
                poster_brief=poster.subheadline or poster.summary,
                product_copy=product_copy.body or product_copy.summary,
                video_scene_plan=fitted_scene_plan,
                poster_headline=poster.headline,
                product_copy_bullets=product_copy.bullet_points,
                poster_image_url=poster_image_url,
                video_url=video_url,
            ),
            risks_and_mitigations=self._merge_risks(
                [research, md, dev, planner, marketer, biz, video, poster, product_copy]
            ),
            timeline=timeline,
        )
        await self._emit_progress(progress_callback, 99, "최종 기획 패키지를 구성했습니다.")
        logger.info("Pipeline completed for '%s' in %.1fs", brief.product_name, time.monotonic() - t0)
        return package

    async def generate_media_assets(self, package: LaunchPackage) -> MarketingAssets:
        assets = package.marketing_assets.model_copy(deep=True)
        fitted_video_script = self._fit_narration_to_duration(
            narration_script=assets.video_script,
            cta_line="",
            seconds=package.brief.video_seconds,
        )
        fitted_scene_plan = self._fit_scene_plan(
            scene_plan=assets.video_scene_plan,
            seconds=package.brief.video_seconds,
        )
        assets.video_script = fitted_video_script
        assets.video_scene_plan = fitted_scene_plan
        assets.poster_image_url = await self._media.generate_poster(
            headline=assets.poster_headline or package.brief.product_name,
            brief=assets.poster_brief or package.campaign_strategy.summary,
            keywords=package.campaign_strategy.message_pillars[:4],
            reference_image_url=package.brief.product_image_url,
            reference_notes=package.brief.product_image_context,
        )
        assets.video_url = await self._media.generate_video(
            prompt=self._compose_video_generation_prompt(
                product_name=package.brief.product_name,
                narration_script=fitted_video_script,
                seconds=package.brief.video_seconds,
            ),
            seconds=package.brief.video_seconds,
            strict_sora=True,
            reference_image_url=package.brief.product_image_url,
            reference_notes=package.brief.product_image_context,
        )
        return assets

    @staticmethod
    def _context_block(parts: list[tuple[str, AgentPayload]]) -> str:
        lines: list[str] = []
        for label, payload in parts:
            lines.append(f"[{label}] {payload.summary}")
            for item in payload.key_points:
                lines.append(f"- {item}")
        return "\n".join(lines)

    @staticmethod
    def _merge_risks(payloads: list[AgentPayload]) -> list[str]:
        seen: set[str] = set()
        merged: list[str] = []
        for payload in payloads:
            for risk in payload.risks:
                normalized = risk.strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                merged.append(normalized)
        return merged[:MAX_RISKS]

    @staticmethod
    def _compose_video_generation_prompt(*, product_name: str, narration_script: str, seconds: int) -> str:
        budget = MainOrchestrator._video_budget(seconds)
        return (
            f"Cinematic product launch video for '{product_name}'. "
            f"Total runtime: exactly {seconds} seconds. "
            f"Narration intent: {narration_script}. "
            f"Narration density limit: <= {budget['max_chars']} Korean characters "
            f"across <= {budget['max_sentences']} short sentences. "
            "Keep pacing readable and avoid rushed voice delivery. "
            "Visual quality target: premium commercial film look, ultra-sharp details, "
            "clean highlights, physically plausible lighting, stable motion, rich textures, "
            "natural skin/material rendering, no text overlay, no watermark."
        )

    @staticmethod
    def _video_budget(seconds: int) -> dict[str, int]:
        safe_seconds = MainOrchestrator._normalize_video_seconds(seconds)
        return VIDEO_TEXT_BUDGET[safe_seconds]

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

    @staticmethod
    def _fit_narration_to_duration(
        *,
        narration_script: str,
        cta_line: str,
        seconds: int,
    ) -> str:
        safe_seconds = MainOrchestrator._normalize_video_seconds(seconds)
        budget = MainOrchestrator._video_budget(safe_seconds)
        max_chars = budget["max_chars"]
        max_sentences = budget["max_sentences"]
        cta_chars = budget["cta_chars"]
        fallback_by_seconds = {
            4: "핵심만 빠르게 전합니다.",
            8: "핵심만 짧게 전하고, 바로 행동으로 이어갑니다.",
            12: "핵심 혜택을 짧게 전달하고, 자연스럽게 행동으로 연결합니다.",
        }

        cleaned = re.sub(r"\s+", " ", narration_script or "").strip()
        if not cleaned:
            cleaned = fallback_by_seconds[safe_seconds]

        sentence_parts = [
            re.sub(r"\s+", " ", part).strip(" ,.;:")
            for part in re.split(r"(?<!\d)[.!?。！？]+|\n+", cleaned)
            if part and part.strip()
        ]

        clipped_parts: list[str] = []
        for part in sentence_parts[:max_sentences]:
            candidate = part if not clipped_parts else ". ".join([*clipped_parts, part])
            if len(candidate) <= max_chars:
                clipped_parts.append(part)
                continue
            break

        if clipped_parts:
            clipped = ". ".join(clipped_parts).strip(" .")
        else:
            source = sentence_parts[0] if sentence_parts else cleaned
            tokens = source.split()
            kept_tokens: list[str] = []
            for token in tokens:
                candidate = " ".join([*kept_tokens, token]).strip()
                if len(candidate) <= max_chars:
                    kept_tokens.append(token)
                    continue
                break
            clipped = " ".join(kept_tokens).strip(" ,.;:|-/")
            if not clipped:
                clipped = source[:max_chars].rstrip(" ,.;:|-/")
                if " " in clipped and len(clipped) > int(max_chars * 0.6):
                    clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,.;:|-/")

        short_cta = re.sub(r"\s+", " ", cta_line or "").strip()
        if short_cta:
            short_cta = short_cta[:cta_chars].strip(" .")
            if short_cta and short_cta not in clipped:
                separator = " " if re.search(r"[.!?。！？]$", clipped) else ". "
                candidate = f"{clipped}{separator}{short_cta}".strip(" .")
                if len(candidate) <= max_chars:
                    clipped = candidate

        if len(clipped) > max_chars:
            trimmed = clipped[:max_chars].rstrip(" ,.;:|-/")
            punctuation_cut = max(
                trimmed.rfind("."),
                trimmed.rfind(","),
                trimmed.rfind("!"),
                trimmed.rfind("?"),
                trimmed.rfind(";"),
                trimmed.rfind(":"),
            )
            if punctuation_cut >= int(max_chars * 0.45):
                trimmed = trimmed[:punctuation_cut]
            elif " " in trimmed and len(trimmed) > int(max_chars * 0.65):
                trimmed = trimmed.rsplit(" ", 1)[0]
            clipped = trimmed.strip(" .")

        if not clipped:
            clipped = cleaned[:max_chars].strip(" .")
        if not clipped:
            clipped = "핵심만 전달합니다"
        if cleaned != clipped:
            too_short = len(clipped) < max(6, int(max_chars * 0.35))
            natural_ending = bool(re.search(r"(요|다|죠|니다|세요|해요|합니다|입니다)$", clipped))
            sentence_ending = bool(re.search(r"[.!?。！？]$", clipped))
            tail_token = clipped.split()[-1] if clipped.split() else ""
            dangling_connector = bool(re.search(r"(그리고|및|또|또는|하지만|그러나)$", clipped))
            likely_fragment = len(tail_token) <= 1 or clipped.endswith(",") or dangling_connector
            likely_fragment_4s = likely_fragment or "," in clipped
            if safe_seconds == 4 and not natural_ending and not sentence_ending:
                if likely_fragment_4s:
                    clipped = fallback_by_seconds[safe_seconds]
                elif len(clipped) + 1 <= max_chars:
                    clipped = f"{clipped}."
            elif too_short or (not natural_ending and not sentence_ending and likely_fragment):
                clipped = fallback_by_seconds[safe_seconds]
        return clipped

    @staticmethod
    def _fit_scene_plan(*, scene_plan: list[str], seconds: int) -> list[str]:
        budget = MainOrchestrator._video_budget(seconds)
        max_scenes = budget["max_scenes"]
        max_scene_chars = budget["scene_chars"]

        cleaned_items: list[str] = []
        for raw_item in scene_plan:
            item = re.sub(r"\s+", " ", raw_item or "").strip()
            item = re.sub(r"^[\-\d\.\)\(:\s]+", "", item)
            if not item:
                continue
            if len(item) > max_scene_chars:
                item = item[:max_scene_chars].rstrip(" ,.;:|-/")
            if item:
                cleaned_items.append(item)
            if len(cleaned_items) >= max_scenes:
                break

        if cleaned_items:
            return cleaned_items

        fallback_by_seconds = {
            4: ["제품 클로즈업 훅", "핵심 효능 1컷", "짧은 CTA"],
            8: ["훅 클로즈업", "사용 장면", "핵심 효능", "마무리 CTA"],
            12: ["문제 제시 훅", "제품 제시", "사용 장면", "효능 강조", "마무리 CTA"],
        }
        return fallback_by_seconds[MainOrchestrator._normalize_video_seconds(seconds)]

    @staticmethod
    async def _emit_progress(
        callback: Callable[[int, str], Awaitable[None] | None] | None,
        progress: int,
        note: str,
    ) -> None:
        if callback is None:
            return
        try:
            maybe = callback(progress, note)
            if inspect.isawaitable(maybe):
                await maybe
        except Exception:
            logger.exception("Progress callback failed at %s%% (%s)", progress, note)
