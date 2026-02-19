"""Request/response schemas for launch orchestration."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class LaunchBrief(BaseModel):
    product_name: str = Field(min_length=2, description="Product or line name")
    product_category: str = Field(min_length=2, description="Category")
    target_audience: str = Field(min_length=2, description="Primary audience")
    price_band: str = Field(min_length=1, description="Price positioning")
    total_budget_krw: int = Field(ge=0, description="Total launch budget in KRW")
    launch_date: date
    core_kpi: str = Field(min_length=2, description="North-star KPI")
    region: str = Field(default="KR", min_length=2, description="Target market")
    channel_focus: list[str] = Field(default_factory=list)
    video_seconds: int = Field(
        default=8,
        ge=4,
        le=30,
        description="Target ad video length in seconds (Sora-supported values are normalized)",
    )


class AgentPayload(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class AgentEnvelope(BaseModel):
    agent: str
    stage: str
    payload: AgentPayload


class Milestone(BaseModel):
    name: str
    due: str
    owner: str
    success_criteria: str


class ResearchOutput(AgentPayload):
    market_signals: list[str] = Field(default_factory=list)
    competitor_insights: list[str] = Field(default_factory=list)
    audience_insights: list[str] = Field(default_factory=list)


class MDOutput(AgentPayload):
    usp: list[str] = Field(default_factory=list)
    hero_product_angle: str = ""
    assortment_notes: list[str] = Field(default_factory=list)


class DevOutput(AgentPayload):
    implementation_scope: list[str] = Field(default_factory=list)
    technical_constraints: list[str] = Field(default_factory=list)
    demo_readiness_checks: list[str] = Field(default_factory=list)


class PlannerOutput(AgentPayload):
    milestones: list[Milestone] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class MarketerOutput(AgentPayload):
    message_pillars: list[str] = Field(default_factory=list)
    channel_tactics: dict[str, Any] = Field(default_factory=dict)
    conversion_hooks: list[str] = Field(default_factory=list)


class BizPlanningOutput(AgentPayload):
    budget_split_krw: dict[str, int] = Field(default_factory=dict)
    kpi_targets: list[str] = Field(default_factory=list)
    roi_assumptions: list[str] = Field(default_factory=list)


class VideoScriptOutput(AgentPayload):
    scene_plan: list[str] = Field(default_factory=list)
    narration_script: str = ""
    cta_line: str = ""


class PosterBriefOutput(AgentPayload):
    headline: str = ""
    subheadline: str = ""
    layout_directions: list[str] = Field(default_factory=list)
    key_visual_keywords: list[str] = Field(default_factory=list)


class ProductCopyOutput(AgentPayload):
    title: str = ""
    body: str = ""
    bullet_points: list[str] = Field(default_factory=list)


class MarketingAssets(BaseModel):
    video_script: str
    poster_brief: str
    product_copy: str
    video_scene_plan: list[str] = Field(default_factory=list)
    poster_headline: str = ""
    product_copy_bullets: list[str] = Field(default_factory=list)
    video_url: str | None = None
    poster_image_url: str | None = None


class LaunchPackage(BaseModel):
    request_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    brief: LaunchBrief

    research_summary: ResearchOutput
    product_strategy: MDOutput
    technical_plan: DevOutput
    launch_plan: PlannerOutput
    campaign_strategy: MarketerOutput
    budget_and_kpi: BizPlanningOutput

    marketing_assets: MarketingAssets
    risks_and_mitigations: list[str] = Field(default_factory=list)
    timeline: list[AgentEnvelope] = Field(default_factory=list)


class LaunchRunRequest(BaseModel):
    brief: LaunchBrief
    mode: Literal["fast", "standard"] = "standard"


class LaunchRunResponse(BaseModel):
    package: LaunchPackage


class LaunchHistoryItem(BaseModel):
    request_id: str
    created_at: datetime
    mode: Literal["fast", "standard"] = "standard"
    product_name: str
    core_kpi: str


class LaunchHistoryListResponse(BaseModel):
    items: list[LaunchHistoryItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
    has_more: bool
    query: str


class LaunchDeleteResponse(BaseModel):
    deleted: bool
