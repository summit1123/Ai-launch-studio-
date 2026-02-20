import type { LaunchBrief } from "../types";

export type BriefTemplate = {
  id: string;
  name: string;
  summary: string;
  brief: LaunchBrief;
};

export const BRIEF_TEMPLATES: BriefTemplate[] = [
  {
    id: "glow-serum-x",
    name: "Glow Serum X",
    summary: "기존 스킨케어 런칭 샘플",
    brief: {
      product_name: "Glow Serum X",
      product_category: "Skincare",
      target_audience: "20-34 뷰티 얼리어답터",
      price_band: "mid-premium",
      total_budget_krw: 120000000,
      launch_date: "2026-04-01",
      core_kpi: "런칭 후 4주 내 재구매율 25%",
      region: "KR",
      channel_focus: ["Instagram", "YouTube", "Naver SmartStore"],
      video_seconds: 8,
    },
  },
  {
    id: "uv-calm-serum",
    name: "UV Calm Serum SPF50+",
    summary: "민감성 타깃 선세럼 런칭",
    brief: {
      product_name: "UV Calm Serum SPF50+",
      product_category: "Skincare",
      target_audience: "25-39 민감성 피부 직장인",
      price_band: "mid-premium",
      total_budget_krw: 90000000,
      launch_date: "2026-05-20",
      core_kpi: "런칭 후 4주 내 신규 고객 전환율 3.5%",
      region: "KR",
      channel_focus: ["Instagram", "YouTube", "Olive Young"],
      video_seconds: 8,
    },
  },
  {
    id: "root-balance-tonic",
    name: "Root Balance Scalp Tonic",
    summary: "프리미엄 두피 토닉 퍼포먼스 런칭",
    brief: {
      product_name: "Root Balance Scalp Tonic",
      product_category: "Haircare",
      target_audience: "30-45 탈모 고민 남녀",
      price_band: "premium",
      total_budget_krw: 150000000,
      launch_date: "2026-06-10",
      core_kpi: "런칭 6주 내 재구매율 20%",
      region: "KR",
      channel_focus: ["YouTube", "Naver SmartStore", "Kakao"],
      video_seconds: 12,
    },
  },
  {
    id: "urban-fit-gel",
    name: "Urban Fit All-in-One Gel",
    summary: "남성 그루밍 숏폼 퍼널 집중",
    brief: {
      product_name: "Urban Fit All-in-One Gel",
      product_category: "Men Grooming",
      target_audience: "20-34 남성, 간편 루틴 선호층",
      price_band: "mid",
      total_budget_krw: 70000000,
      launch_date: "2026-04-28",
      core_kpi: "런칭 후 30일 내 CAC 18,000원 이하",
      region: "KR",
      channel_focus: ["Instagram", "TikTok", "Coupang"],
      video_seconds: 12,
    },
  },
];

export function cloneBrief(brief: LaunchBrief): LaunchBrief {
  return {
    ...brief,
    channel_focus: [...brief.channel_focus],
  };
}

export const DEFAULT_TEMPLATE_INDEX = 3; // Urban Fit All-in-One Gel

export function getDefaultBrief(): LaunchBrief {
  return cloneBrief(BRIEF_TEMPLATES[DEFAULT_TEMPLATE_INDEX].brief);
}
