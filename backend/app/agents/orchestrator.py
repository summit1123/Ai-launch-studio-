"""Main orchestrator for launch package generation."""

from __future__ import annotations

import asyncio
import logging
import time
from uuid import uuid4

logger = logging.getLogger(__name__)

PHASE_TIMEOUT_SECONDS = 60
MAX_RISKS = 10

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

    async def run(self, request: LaunchRunRequest) -> LaunchPackage:
        brief = request.brief
        timeline: list[AgentEnvelope] = []
        t0 = time.monotonic()

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
        planner, marketer, biz = await asyncio.wait_for(
            asyncio.gather(
                self._planner.run(brief, synthesis_context),
                self._marketer.run(brief, synthesis_context),
                self._biz.run(brief, synthesis_context),
            ),
            timeout=PHASE_TIMEOUT_SECONDS,
        )
        logger.info("[Phase 2] Completed in %.1fs", time.monotonic() - t1)
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
        video, poster, product_copy = await asyncio.wait_for(
            asyncio.gather(
                self._video.run(brief, marketing_context),
                self._poster.run(brief, marketing_context),
                self._product_copy.run(brief, md_context),
            ),
            timeout=PHASE_TIMEOUT_SECONDS,
        )
        logger.info("[Phase 3] Completed in %.1fs", time.monotonic() - t2)
        timeline.extend(
            [
                AgentEnvelope(agent="Video Producer Agent", stage="phase3_assets", payload=video),
                AgentEnvelope(agent="Poster Agent", stage="phase3_assets", payload=poster),
                AgentEnvelope(agent="Product Copy Agent", stage="phase3_assets", payload=product_copy),
            ]
        )

        # Phase 4: Media Generation (Optional/Post-processing)
        poster_image_url = None
        video_url = None
        
        if not brief.product_name.startswith("[MOCK"):
            # Image Generation (DALL-E 3)
            poster_image_url = await self._media.generate_poster(
                headline=poster.headline,
                brief=poster.subheadline or poster.summary,
                keywords=poster.key_visual_keywords
            )
            
            # Video Generation (Sora) - This might be slow
            video_url = await self._media.generate_video(
                prompt=f"Cinematic product launch video for '{brief.product_name}'. {video.narration_script}",
                seconds=brief.video_seconds,
            )

        return LaunchPackage(
            request_id=str(uuid4()),
            brief=brief,
            research_summary=research,
            product_strategy=md,
            technical_plan=dev,
            launch_plan=planner,
            campaign_strategy=marketer,
            budget_and_kpi=biz,
            marketing_assets=MarketingAssets(
                video_script=video.narration_script or video.summary,
                poster_brief=poster.subheadline or poster.summary,
                product_copy=product_copy.body or product_copy.summary,
                video_scene_plan=video.scene_plan,
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
        logger.info("Pipeline completed for '%s' in %.1fs", brief.product_name, time.monotonic() - t0)

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
