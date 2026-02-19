export type LaunchBrief = {
  product_name: string;
  product_category: string;
  target_audience: string;
  price_band: string;
  total_budget_krw: number;
  launch_date: string;
  core_kpi: string;
  region: string;
  channel_focus: string[];
  video_seconds: number;
};

export type AgentPayload = {
  summary: string;
  key_points: string[];
  risks: string[];
  artifacts: Record<string, unknown>;
};

export type AgentEnvelope = {
  agent: string;
  stage: string;
  payload: AgentPayload;
};

export type MarketingAssets = {
  video_script: string;
  poster_brief: string;
  product_copy: string;
  video_scene_plan?: string[];
  poster_headline?: string;
  product_copy_bullets?: string[];
  video_url?: string;
  poster_image_url?: string;
};

export type LaunchPackage = {
  request_id: string;
  created_at: string;
  brief: LaunchBrief;
  research_summary: AgentPayload;
  product_strategy: AgentPayload;
  technical_plan: AgentPayload;
  launch_plan: AgentPayload;
  campaign_strategy: AgentPayload;
  budget_and_kpi: AgentPayload;
  marketing_assets: MarketingAssets;
  risks_and_mitigations: string[];
  timeline: AgentEnvelope[];
};

export type LaunchRunRequest = {
  brief: LaunchBrief;
  mode: "fast" | "standard";
};

export type LaunchRunResponse = {
  package: LaunchPackage;
};

export type LaunchHistoryItem = {
  request_id: string;
  created_at: string;
  mode: "fast" | "standard";
  product_name: string;
  core_kpi: string;
};

export type LaunchHistoryListResponse = {
  items: LaunchHistoryItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  query: string;
};

export type ChatState =
  | "CHAT_COLLECTING"
  | "BRIEF_READY"
  | "RUN_RESEARCH"
  | "GEN_STRATEGY"
  | "GEN_CREATIVES"
  | "DONE"
  | "FAILED";

export type ProductSlots = {
  name: string | null;
  category: string | null;
  features: string[];
  price_band: string | null;
};

export type TargetSlots = {
  who: string | null;
  why: string | null;
};

export type ChannelSlots = {
  channels: string[];
};

export type GoalSlots = {
  weekly_goal: "reach" | "inquiry" | "purchase" | null;
  video_seconds: number | null;
};

export type BriefSlots = {
  product: ProductSlots;
  target: TargetSlots;
  channel: ChannelSlots;
  goal: GoalSlots;
};

export type SlotUpdate = {
  path: string;
  value: unknown;
  confidence: number;
};

export type GateStatus = {
  ready: boolean;
  missing_required: string[];
  completeness: number;
};

export type ChatSessionCreateRequest = {
  locale?: string;
  mode?: "fast" | "standard";
};

export type ChatSessionCreateResponse = {
  session_id: string;
  state: ChatState;
  mode: "fast" | "standard";
  locale: string;
  brief_slots: BriefSlots;
  gate: GateStatus;
  assistant_message: string;
};

export type ChatSessionGetResponse = {
  session_id: string;
  state: ChatState;
  mode: "fast" | "standard";
  locale: string;
  brief_slots: BriefSlots;
  gate: GateStatus;
  created_at: string;
  updated_at: string;
};

export type ChatMessageRequest = {
  message: string;
};

export type ChatMessageResponse = {
  session_id: string;
  state: ChatState;
  assistant_message: string;
  slot_updates: SlotUpdate[];
  brief_slots: BriefSlots;
  gate: GateStatus;
};

export type VoiceTurnResponse = {
  session_id: string;
  transcript: string;
  state: ChatState;
  next_question: string;
  slot_updates: SlotUpdate[];
  brief_slots: BriefSlots;
  gate: GateStatus;
};

export type VoiceTurnRequest = {
  audio: Blob | File;
  filename?: string;
  locale?: string;
  voice_preset?: "friendly_ko" | "calm_ko" | "neutral_ko";
};

export type AssistantVoiceRequest = {
  text: string;
  voice_preset?: "friendly_ko" | "calm_ko" | "neutral_ko";
  format?: "mp3" | "wav";
};

export type AssistantVoiceResponse = {
  audio_url: string;
  format: "mp3" | "wav";
  bytes_size: number;
};

export type RunGenerateResponse = {
  run_id: string;
  session_id: string;
  state: ChatState;
};

export type JobStatus = "queued" | "running" | "completed" | "failed";

export type RunGenerateAsyncResponse = {
  job_id: string;
  session_id: string;
  status: JobStatus;
};

export type RunGetResponse = {
  run_id: string;
  session_id: string;
  state: ChatState;
  package: LaunchPackage;
};

export type JobGetResponse = {
  job_id: string;
  type: string;
  status: JobStatus;
  progress: number;
  session_id: string;
  run_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type JobListResponse = {
  items: JobGetResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type StreamEventType =
  | "planner.delta"
  | "slot.updated"
  | "gate.ready"
  | "stage.changed"
  | "research.delta"
  | "strategy.delta"
  | "creative.delta"
  | "voice.delta"
  | "asset.ready"
  | "run.completed"
  | "error";

export type StreamEvent = {
  type: StreamEventType | string;
  data: unknown;
};
