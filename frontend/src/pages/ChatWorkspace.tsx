import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createChatSession,
  generateRun,
  getRun,
  postChatMessage,
} from "../api/client";
import { LaunchResult } from "./LaunchResult";
import type {
  BriefSlots,
  ChatMessageResponse,
  ChatState,
  GateStatus,
  LaunchPackage,
} from "../types";

type ChatLine = {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
};

function lineId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function stageLabel(state: ChatState): string {
  switch (state) {
    case "CHAT_COLLECTING":
      return "브리프 수집 중";
    case "BRIEF_READY":
      return "브리프 준비 완료";
    case "RUN_RESEARCH":
      return "시장 리서치 실행 중";
    case "GEN_STRATEGY":
      return "전략 생성 중";
    case "GEN_CREATIVES":
      return "소재 생성 중";
    case "DONE":
      return "완료";
    case "FAILED":
      return "실패";
    default:
      return state;
  }
}

function summarizeSlots(slots: BriefSlots | null): string {
  if (!slots) {
    return "세션을 생성하는 중입니다.";
  }

  const features =
    slots.product.features.length > 0 ? slots.product.features.join(", ") : "-";
  const channels =
    slots.channel.channels.length > 0 ? slots.channel.channels.join(", ") : "-";

  return [
    `제품명: ${slots.product.name ?? "-"}`,
    `카테고리: ${slots.product.category ?? "-"}`,
    `특징: ${features}`,
    `가격대: ${slots.product.price_band ?? "-"}`,
    `타겟: ${slots.target.who ?? "-"}`,
    `구매 이유: ${slots.target.why ?? "-"}`,
    `채널: ${channels}`,
    `주간 목표: ${slots.goal.weekly_goal ?? "-"}`,
  ].join("\n");
}

export function ChatWorkspace() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<ChatState>("CHAT_COLLECTING");
  const [briefSlots, setBriefSlots] = useState<BriefSlots | null>(null);
  const [gate, setGate] = useState<GateStatus | null>(null);
  const [messages, setMessages] = useState<ChatLine[]>([]);
  const [draft, setDraft] = useState("");
  const [loadingSession, setLoadingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [launchPackage, setLaunchPackage] = useState<LaunchPackage | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

  const completeness = useMemo(() => {
    return gate ? Math.round(gate.completeness * 100) : 0;
  }, [gate]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoadingSession(true);
      setError(null);
      try {
        const response = await createChatSession({
          locale: "ko-KR",
          mode: "standard",
        });
        if (cancelled) {
          return;
        }
        setSessionId(response.session_id);
        setState(response.state);
        setBriefSlots(response.brief_slots);
        setGate(response.gate);
        setMessages([
          {
            id: lineId("assistant"),
            role: "assistant",
            text: response.assistant_message,
          },
        ]);
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message =
          err instanceof Error ? err.message : "대화 세션 생성에 실패했습니다.";
        setError(message);
      } finally {
        if (!cancelled) {
          setLoadingSession(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const applyTurnResponse = (response: ChatMessageResponse) => {
    setState(response.state);
    setBriefSlots(response.brief_slots);
    setGate(response.gate);
    setMessages((previous) => [
      ...previous,
      {
        id: lineId("assistant"),
        role: "assistant",
        text: response.assistant_message,
      },
    ]);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionId) {
      return;
    }

    const message = draft.trim();
    if (!message || sending) {
      return;
    }

    setDraft("");
    setError(null);
    setSending(true);
    setMessages((previous) => [
      ...previous,
      { id: lineId("user"), role: "user", text: message },
    ]);

    try {
      const response = await postChatMessage(sessionId, { message });
      applyTurnResponse(response);
    } catch (err) {
      const messageText =
        err instanceof Error ? err.message : "메시지 전송에 실패했습니다.";
      setError(messageText);
      setMessages((previous) => [
        ...previous,
        { id: lineId("system"), role: "system", text: messageText },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleGenerate = async () => {
    if (!sessionId || !gate?.ready || generating) {
      return;
    }
    setGenerating(true);
    setError(null);
    setLaunchPackage(null);

    try {
      const generated = await generateRun(sessionId);
      setRunId(generated.run_id);
      setState(generated.state);

      const result = await getRun(generated.run_id);
      setState(result.state);
      setLaunchPackage(result.package);
      setMessages((previous) => [
        ...previous,
        {
          id: lineId("system"),
          role: "system",
          text: "생성 완료: 시장/전략/소재 패키지를 확인하세요.",
        },
      ]);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "런 생성에 실패했습니다.";
      setError(message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <main className="container" style={{ marginTop: "80px", paddingBottom: "120px" }}>
      <header className="hero">
        <div className="eyebrow">Chat + Voice MVP</div>
        <h1>Chat Workspace</h1>
        <p>
          텍스트 또는 음성 턴으로 브리프를 채운 뒤, 게이트 통과 시 리서치와 실행형
          런칭 패키지를 생성합니다.
        </p>
      </header>

      <section className="glass-panel">
        <h2 className="section-title">대화</h2>
        <div
          style={{
            display: "grid",
            gap: "10px",
            maxHeight: "380px",
            overflowY: "auto",
            padding: "6px",
          }}
        >
          {messages.map((line) => (
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
              }}
            >
              {line.text}
            </div>
          ))}
        </div>

        <form
          onSubmit={handleSubmit}
          style={{ marginTop: "16px", display: "grid", gap: "10px" }}
        >
          <textarea
            rows={3}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="제품명, 카테고리, 특징, 가격대, 타겟, 채널, 목표를 자유롭게 입력하세요."
            disabled={loadingSession || sending}
            style={{
              width: "100%",
              borderRadius: "12px",
              border: "1px solid var(--surface-border)",
              background: "rgba(15, 23, 42, 0.7)",
              color: "var(--ink)",
              padding: "12px 14px",
              resize: "vertical",
            }}
          />
          <div style={{ display: "flex", gap: "10px", justifyContent: "space-between" }}>
            <small style={{ color: "var(--muted)" }}>
              상태: <strong>{stageLabel(state)}</strong>
            </small>
            <button
              type="submit"
              className="btn-primary-sm"
              disabled={loadingSession || sending || !sessionId}
            >
              {sending ? "전송 중..." : "메시지 보내기"}
            </button>
          </div>
        </form>
      </section>

      <section className="glass-panel">
        <h2 className="section-title">브리프 게이트</h2>
        <p style={{ margin: "0 0 10px", color: "var(--muted)" }}>
          완성도 {completeness}%{gate?.ready ? " · 준비 완료" : " · 정보 수집 필요"}
        </p>
        {!gate?.ready && gate && (
          <p style={{ marginTop: 0, color: "var(--muted)" }}>
            누락 슬롯: {gate.missing_required.join(", ")}
          </p>
        )}

        <pre
          style={{
            margin: 0,
            borderRadius: "12px",
            border: "1px solid var(--surface-border)",
            background: "rgba(15, 23, 42, 0.7)",
            padding: "14px",
            whiteSpace: "pre-wrap",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: "0.82rem",
            color: "var(--ink)",
          }}
        >
          {summarizeSlots(briefSlots)}
        </pre>

        <div style={{ marginTop: "14px", display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!sessionId || !gate?.ready || generating}
          >
            {generating ? "생성 중..." : "런 패키지 생성"}
          </button>
          {runId && <small style={{ color: "var(--muted)" }}>run_id: {runId}</small>}
        </div>
      </section>

      {error && (
        <section className="glass-panel" style={{ borderColor: "rgba(239, 68, 68, 0.35)" }}>
          <strong style={{ color: "#fda4af" }}>오류</strong>
          <p style={{ marginBottom: 0 }}>{error}</p>
        </section>
      )}

      {launchPackage && (
        <section className="glass-panel" style={{ padding: 0, overflow: "hidden" }}>
          <LaunchResult launchPackage={launchPackage} />
        </section>
      )}
    </main>
  );
}
