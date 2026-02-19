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
