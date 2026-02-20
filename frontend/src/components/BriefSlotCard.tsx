import type { BriefSlots, GateStatus } from "../types";

type BriefSlotCardProps = {
  slots: BriefSlots | null;
  gate: GateStatus | null;
};

type SlotCard = {
  title: string;
  ready: boolean;
  items: Array<{ label: string; value: string }>;
};

const REQUIRED_SLOT_LABELS: Record<string, string> = {
  "product.name": "제품명",
  "product.category": "카테고리",
  "product.features": "핵심 특징 3개",
  "product.price_band": "가격대",
  "target.who": "타겟 고객",
  "target.why": "구매 이유",
  "channel.channels": "집중 채널",
  "goal.weekly_goal": "주간 목표",
};

function missingLabels(paths: string[]): string {
  return paths.map((path) => REQUIRED_SLOT_LABELS[path] ?? path).join(", ");
}

function textValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "-";
}

function listValue(values: string[] | undefined): string {
  if (!values || values.length === 0) {
    return "-";
  }
  return values.join(", ");
}

function videoSecondsValue(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value) || value <= 0) {
    return "-";
  }
  return `${value}초`;
}

function buildCards(slots: BriefSlots | null): SlotCard[] {
  if (!slots) {
    return [
      { title: "제품", ready: false, items: [] },
      { title: "타겟", ready: false, items: [] },
      { title: "채널", ready: false, items: [] },
      { title: "목표", ready: false, items: [] },
    ];
  }

  const productReady =
    Boolean(slots.product.name) &&
    Boolean(slots.product.category) &&
    slots.product.features.length >= 3 &&
    Boolean(slots.product.price_band);
  const targetReady = Boolean(slots.target.who) && Boolean(slots.target.why);
  const channelReady =
    slots.channel.channels.length >= 1 && slots.channel.channels.length <= 2;
  const goalReady = Boolean(slots.goal.weekly_goal);

  return [
    {
      title: "제품",
      ready: productReady,
      items: [
        { label: "제품명", value: textValue(slots.product.name) },
        { label: "카테고리", value: textValue(slots.product.category) },
        { label: "특징", value: listValue(slots.product.features) },
        { label: "가격대", value: textValue(slots.product.price_band) },
      ],
    },
    {
      title: "타겟",
      ready: targetReady,
      items: [
        { label: "누가", value: textValue(slots.target.who) },
        { label: "왜", value: textValue(slots.target.why) },
      ],
    },
    {
      title: "채널",
      ready: channelReady,
      items: [{ label: "채널", value: listValue(slots.channel.channels) }],
    },
    {
      title: "목표",
      ready: goalReady,
      items: [
        { label: "주간 목표", value: textValue(slots.goal.weekly_goal) },
        { label: "영상 길이", value: videoSecondsValue(slots.goal.video_seconds) },
      ],
    },
  ];
}

export function BriefSlotCard({ slots, gate }: BriefSlotCardProps) {
  const cards = buildCards(slots);
  const progress = gate ? Math.round(gate.completeness * 100) : 0;

  return (
    <div style={{ display: "grid", gap: "12px" }}>
      <div
        style={{
          height: "8px",
          borderRadius: "999px",
          background: "rgba(255, 255, 255, 0.08)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: "100%",
            background: "linear-gradient(90deg, #38bdf8, #0ea5e9)",
            transition: "width 0.2s ease",
          }}
        />
      </div>
      <small style={{ color: "var(--muted)" }}>
        게이트 진행률: {progress}% {gate?.ready ? "· 준비 완료" : "· 정보 수집 필요"}
      </small>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "10px",
        }}
      >
        {cards.map((card) => (
          <article
            key={card.title}
            style={{
              border: "1px solid var(--surface-border)",
              borderRadius: "12px",
              background: "rgba(15, 23, 42, 0.7)",
              padding: "12px",
              display: "grid",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
              <strong>{card.title}</strong>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: card.ready ? "#22c55e" : "var(--muted)",
                }}
              >
                {card.ready ? "완료" : "수집중"}
              </span>
            </div>
            {card.items.map((item) => (
              <div key={item.label} style={{ display: "grid", gap: "2px" }}>
                <small style={{ color: "var(--muted)" }}>{item.label}</small>
                <span style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{item.value}</span>
              </div>
            ))}
          </article>
        ))}
      </div>

      {!gate?.ready && gate && (
        <small style={{ color: "var(--muted)" }}>
          누락 슬롯: {missingLabels(gate.missing_required)}
        </small>
      )}
    </div>
  );
}
