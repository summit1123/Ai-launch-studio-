import { useEffect, useRef } from "react";

export type MessageStreamItem = {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
};

type MessageStreamProps = {
  items: MessageStreamItem[];
  compact?: boolean;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";
const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
const PLANNER_AVATAR_URL = `${BACKEND_BASE_URL}/static/assets/planner_mascot.png`;
const PLANNER_NAME = "루미";

export function MessageStream({ items, compact = false }: MessageStreamProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [items]);

  return (
    <div
      ref={containerRef}
      style={{
        display: "grid",
        gap: "12px",
        maxHeight: "460px",
        minHeight: compact ? "120px" : "280px",
        overflowY: "auto",
        padding: "14px",
        borderRadius: "14px",
        border: "1px solid var(--surface-border)",
        background:
          "linear-gradient(180deg, rgba(11, 28, 56, 0.74) 0%, rgba(7, 20, 42, 0.72) 100%)",
      }}
    >
      {items.map((line) => (
        <div
          key={line.id}
          style={{
            justifySelf: line.role === "user" ? "end" : "start",
            maxWidth: line.role === "user" ? "72%" : "88%",
            minWidth: line.role === "assistant" ? "240px" : undefined,
            width: "fit-content",
            padding: "10px 12px",
            borderRadius: "14px",
            border:
              line.role === "system"
                ? "1px solid rgba(239, 68, 68, 0.35)"
                : "1px solid var(--surface-border)",
            background:
              line.role === "user"
                ? "linear-gradient(145deg, rgba(34, 211, 238, 0.3), rgba(245, 158, 11, 0.2))"
                : line.role === "system"
                  ? "rgba(239, 68, 68, 0.12)"
                  : "var(--surface-strong)",
            whiteSpace: "pre-wrap",
            boxShadow: "0 8px 24px rgba(2, 6, 23, 0.25)",
          }}
        >
          <div
            style={{
              fontSize: "0.78rem",
              color: "var(--muted)",
              marginBottom: "4px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontWeight: 700,
            }}
          >
            {line.role === "assistant" && (
              <img
                src={PLANNER_AVATAR_URL}
                alt={`${PLANNER_NAME} 프로필`}
                style={{
                  width: "42px",
                  height: "42px",
                  borderRadius: "999px",
                  border: "2px solid rgba(143, 201, 255, 0.5)",
                  objectFit: "cover",
                  boxShadow: "0 4px 14px rgba(34, 211, 238, 0.24)",
                }}
              />
            )}
            {line.role === "assistant" ? PLANNER_NAME : line.role === "user" ? "나" : "시스템"}
          </div>
          {line.text}
        </div>
      ))}
    </div>
  );
}
