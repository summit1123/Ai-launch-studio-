import { FormEvent, useEffect, useMemo, useState } from "react";

import type { LaunchBrief } from "../types";
import { BRIEF_TEMPLATES, cloneBrief, getDefaultBrief, DEFAULT_TEMPLATE_INDEX } from "../data/briefTemplates";

type LaunchFormProps = {
  loading: boolean;
  onSubmit: (brief: LaunchBrief) => Promise<void>;
  initialBrief?: LaunchBrief | null;
};

const CUSTOM_TEMPLATE_ID = "custom";

export function LaunchForm({ loading, onSubmit, initialBrief = null }: LaunchFormProps) {
  const [form, setForm] = useState<LaunchBrief>(() =>
    cloneBrief(initialBrief ?? getDefaultBrief())
  );
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>(
    initialBrief ? CUSTOM_TEMPLATE_ID : BRIEF_TEMPLATES[DEFAULT_TEMPLATE_INDEX].id
  );
  const channelText = useMemo(() => form.channel_focus.join(", "), [form]);

  useEffect(() => {
    if (initialBrief) {
      setForm(cloneBrief(initialBrief));
      setSelectedTemplateId(CUSTOM_TEMPLATE_ID);
      return;
    }
    setForm(getDefaultBrief());
    setSelectedTemplateId(BRIEF_TEMPLATES[DEFAULT_TEMPLATE_INDEX].id);
  }, [initialBrief]);

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplateId(templateId);
    if (templateId === CUSTOM_TEMPLATE_ID) {
      return;
    }
    const selected = BRIEF_TEMPLATES.find((item) => item.id === templateId);
    if (!selected) {
      return;
    }
    setForm(cloneBrief(selected.brief));
  };

  const updateForm = (next: LaunchBrief) => {
    setForm(next);
    if (selectedTemplateId !== CUSTOM_TEMPLATE_ID) {
      setSelectedTemplateId(CUSTOM_TEMPLATE_ID);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(form);
  };

  return (
    <section className="glass-panel" style={{ marginBottom: 0 }}>
      <form className="launchForm" onSubmit={handleSubmit}>
        <label>
          <span>샘플 브리프</span>
          <select
            value={selectedTemplateId}
            onChange={(e) => handleTemplateChange(e.target.value)}
          >
            <option value={CUSTOM_TEMPLATE_ID}>직접 입력</option>
            {BRIEF_TEMPLATES.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>제품 명칭</span>
          <input
            placeholder="예: 글로우 세럼 X"
            value={form.product_name}
            onChange={(e) => updateForm({ ...form, product_name: e.target.value })}
            required
          />
        </label>
        <label>
          <span>카테고리</span>
          <input
            placeholder="예: 프리미엄 스킨케어"
            value={form.product_category}
            onChange={(e) => updateForm({ ...form, product_category: e.target.value })}
            required
          />
        </label>
        <label>
          <span>타깃 오디언스</span>
          <input
            placeholder="예: 2034 여성, 자기관리 매니아"
            value={form.target_audience}
            onChange={(e) => updateForm({ ...form, target_audience: e.target.value })}
            required
          />
        </label>
        <label>
          <span>가격대</span>
          <input
            placeholder="예: $45 - Mid-Premium"
            value={form.price_band}
            onChange={(e) => updateForm({ ...form, price_band: e.target.value })}
            required
          />
        </label>
        <label>
          <span>총 예산 (KRW)</span>
          <input
            type="number"
            placeholder="예: 50,000,000"
            value={form.total_budget_krw}
            min={0}
            onChange={(e) =>
              updateForm({ ...form, total_budget_krw: Number(e.target.value) || 0 })
            }
            required
          />
        </label>
        <label>
          <span>출시 예정일</span>
          <input
            type="date"
            value={form.launch_date}
            onChange={(e) => updateForm({ ...form, launch_date: e.target.value })}
            required
          />
        </label>
        <label>
          <span>핵심 KPI</span>
          <input
            placeholder="예: 출시 한 달 내 점유율 10%"
            value={form.core_kpi}
            onChange={(e) => updateForm({ ...form, core_kpi: e.target.value })}
            required
          />
        </label>
        <label>
          <span>광고 영상 길이 (초)</span>
          <select
            value={form.video_seconds}
            onChange={(e) =>
              updateForm({ ...form, video_seconds: Number(e.target.value) || 10 })
            }
          >
            <option value={5}>5초 (초단기 티저)</option>
            <option value={10}>10초 (숏폼 기본)</option>
            <option value={15}>15초 (메시지 확장)</option>
            <option value={20}>20초 (브랜드 확장)</option>
          </select>
        </label>
        <label>
          <span>채널 (콤마 구분)</span>
          <input
            placeholder="예: Instagram, YouTube"
            value={channelText}
            onChange={(e) =>
              updateForm({
                ...form,
                channel_focus: e.target.value
                  .split(",")
                  .map((channel) => channel.trim())
                  .filter(Boolean),
              })
            }
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "AI 에이전트 군단이 협업 중입니다..." : "전략 수립 및 에셋 생성 시작"}
        </button>
      </form>
    </section>
  );
}
