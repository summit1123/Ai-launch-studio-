export type MessageStreamItem = {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
};

type MessageStreamProps = {
  items: MessageStreamItem[];
};

export function MessageStream({ items }: MessageStreamProps) {
  return (
    <div
      style={{
        display: "grid",
        gap: "10px",
        maxHeight: "380px",
        overflowY: "auto",
        padding: "6px",
      }}
    >
      {items.map((line) => (
        <div
          key={line.id}
          style={{
            justifySelf: line.role === "user" ? "end" : "start",
            maxWidth: "88%",
            padding: "10px 14px",
            borderRadius: "12px",
            border:
              line.role === "system"
                ? "1px solid rgba(239, 68, 68, 0.35)"
                : "1px solid rgba(255, 255, 255, 0.12)",
            background:
              line.role === "user"
                ? "rgba(56, 189, 248, 0.18)"
                : line.role === "system"
                  ? "rgba(239, 68, 68, 0.12)"
                  : "rgba(15, 23, 42, 0.7)",
            whiteSpace: "pre-wrap",
          }}
        >
          {line.text}
        </div>
      ))}
    </div>
  );
}
