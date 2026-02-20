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
        default=12,
        ge=4,
        le=12,
        description="Target ad video length in seconds (normalized to 4/8/12)",
    )
    product_image_url: str | None = Field(
        default=None,
        description="Uploaded product image URL used as visual reference",
    )
    product_image_context: str | None = Field(
        default=None,
        description="Vision summary extracted from uploaded product image",
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


ChatState = Literal[
    "CHAT_COLLECTING",
    "BRIEF_READY",
    "RUN_RESEARCH",
    "GEN_STRATEGY",
    "GEN_CREATIVES",
    "DONE",
    "FAILED",
]

JobStatus = Literal["queued", "running", "completed", "failed"]


class ProductSlots(BaseModel):
    name: str | None = None
    category: str | None = None
    features: list[str] = Field(default_factory=list)
    price_band: str | None = None
    image_url: str | None = None
    image_context: str | None = None


class TargetSlots(BaseModel):
    who: str | None = None
    why: str | None = None


class ChannelSlots(BaseModel):
    channels: list[str] = Field(default_factory=list)


class GoalSlots(BaseModel):
    weekly_goal: Literal["reach", "inquiry", "purchase"] | None = None
    video_seconds: int | None = Field(
        default=None,
        ge=4,
        le=12,
        description="Preferred video length in seconds (4/8/12)",
    )


class BriefSlots(BaseModel):
    product: ProductSlots = Field(default_factory=ProductSlots)
    target: TargetSlots = Field(default_factory=TargetSlots)
    channel: ChannelSlots = Field(default_factory=ChannelSlots)
    goal: GoalSlots = Field(default_factory=GoalSlots)


class SlotUpdate(BaseModel):
    path: str
    value: Any
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class GateStatus(BaseModel):
    ready: bool
    missing_required: list[str] = Field(default_factory=list)
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)


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


class ChatSessionCreateRequest(BaseModel):
    locale: str = "ko-KR"
    mode: Literal["fast", "standard"] = "standard"


class ChatSessionCreateResponse(BaseModel):
    session_id: str
    state: ChatState
    mode: Literal["fast", "standard"]
    locale: str
    brief_slots: BriefSlots
    gate: GateStatus
    assistant_message: str


class ChatSessionGetResponse(BaseModel):
    session_id: str
    state: ChatState
    mode: Literal["fast", "standard"]
    locale: str
    brief_slots: BriefSlots
    gate: GateStatus
    created_at: datetime
    updated_at: datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)


class ChatMessageResponse(BaseModel):
    session_id: str
    state: ChatState
    assistant_message: str
    slot_updates: list[SlotUpdate] = Field(default_factory=list)
    brief_slots: BriefSlots
    gate: GateStatus


class ProductImageUploadResponse(BaseModel):
    session_id: str
    state: ChatState
    image_url: str
    image_summary: str | None = None
    next_question: str
    slot_updates: list[SlotUpdate] = Field(default_factory=list)
    brief_slots: BriefSlots
    gate: GateStatus


class VoiceTurnResponse(BaseModel):
    session_id: str
    transcript: str
    state: ChatState
    next_question: str
    slot_updates: list[SlotUpdate] = Field(default_factory=list)
    brief_slots: BriefSlots
    gate: GateStatus


class AssistantVoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    voice_preset: Literal["cute_ko", "friendly_ko", "calm_ko", "neutral_ko"] = "cute_ko"
    format: Literal["mp3", "wav"] = "mp3"


class AssistantVoiceResponse(BaseModel):
    audio_url: str
    format: Literal["mp3", "wav"]
    bytes_size: int


class RunGenerateResponse(BaseModel):
    run_id: str
    session_id: str
    state: ChatState


class RunGenerateAsyncResponse(BaseModel):
    job_id: str
    session_id: str
    status: JobStatus


class RunGetResponse(BaseModel):
    run_id: str
    session_id: str
    state: ChatState
    package: LaunchPackage


class MediaAssetItem(BaseModel):
    asset_id: str
    run_id: str
    asset_type: str
    local_path: str | None = None
    remote_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RunAssetsGetResponse(BaseModel):
    run_id: str
    poster_image_url: str | None = None
    video_url: str | None = None
    items: list[MediaAssetItem] = Field(default_factory=list)


class RunAssetsGenerateAsyncResponse(BaseModel):
    job_id: str
    run_id: str
    session_id: str
    status: JobStatus


class JobGetResponse(BaseModel):
    job_id: str
    type: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    note: str | None = None
    session_id: str
    run_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobGetResponse] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


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
