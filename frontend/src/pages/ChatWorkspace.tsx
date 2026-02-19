import { useEffect, useState, type FormEvent } from "react";

import {
  createChatSession,
  generateRun,
  getChatSession,
  getRun,
  postChatMessage,
  postVoiceTurn,
  streamChatMessage,
} from "../api/client";
import {
  BriefSlotCard,
} from "../components/BriefSlotCard";
import {
  MessageStream,
  type MessageStreamItem,
} from "../components/MessageStream";
import { VoiceInputButton } from "../components/VoiceInputButton";
import { LaunchResult } from "./LaunchResult";
import type {
  BriefSlots,
  ChatMessageResponse,
  ChatState,
  GateStatus,
  LaunchPackage,
  StreamEvent,
  VoiceTurnRequest,
} from "../types";

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

const CHAT_STATES: ChatState[] = [
  "CHAT_COLLECTING",
  "BRIEF_READY",
  "RUN_RESEARCH",
  "GEN_STRATEGY",
  "GEN_CREATIVES",
  "DONE",
  "FAILED",
];

function asChatState(value: unknown): ChatState | null {
  if (typeof value !== "string") {
    return null;
  }
  return CHAT_STATES.includes(value as ChatState) ? (value as ChatState) : null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function parseGateStatus(value: unknown): GateStatus | null {
  const record = asRecord(value);
  if (!record) {
    return null;
  }
  if (
    typeof record.ready !== "boolean" ||
    typeof record.completeness !== "number" ||
    !Array.isArray(record.missing_required)
  ) {
    return null;
  }
  if (!record.missing_required.every((item) => typeof item === "string")) {
    return null;
  }
  return {
    ready: record.ready,
    completeness: record.completeness,
    missing_required: record.missing_required as string[],
  };
}

async function getRunSessionSnapshot(sessionId: string) {
  return getChatSession(sessionId);
}

export function ChatWorkspace() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<ChatState>("CHAT_COLLECTING");
  const [briefSlots, setBriefSlots] = useState<BriefSlots | null>(null);
  const [gate, setGate] = useState<GateStatus | null>(null);
  const [messages, setMessages] = useState<MessageStreamItem[]>([]);
  const [draft, setDraft] = useState("");
  const [loadingSession, setLoadingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const [voiceSending, setVoiceSending] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [launchPackage, setLaunchPackage] = useState<LaunchPackage | null>(null);
  const [runId, setRunId] = useState<string | null>(null);

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

  const appendMessage = (line: MessageStreamItem) => {
    setMessages((previous) => [...previous, line]);
  };

  const updateMessageText = (id: string, text: string) => {
    setMessages((previous) =>
      previous.map((line) => (line.id === id ? { ...line, text } : line))
    );
  };

  const applyTurnResponse = (response: ChatMessageResponse) => {
    setState(response.state);
    setBriefSlots(response.brief_slots);
    setGate(response.gate);
    appendMessage({
      id: lineId("assistant"),
      role: "assistant",
      text: response.assistant_message,
    });
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
    appendMessage({ id: lineId("user"), role: "user", text: message });

    const assistantLineId = lineId("assistant");
    appendMessage({ id: assistantLineId, role: "assistant", text: "" });
    let assistantBuffer = "";

    try {
      await streamChatMessage(sessionId, { message }, (event: StreamEvent) => {
        const payload = asRecord(event.data);

        if (event.type === "planner.delta") {
          const text = payload?.text;
          if (typeof text === "string") {
            assistantBuffer += text;
            updateMessageText(assistantLineId, assistantBuffer);
          }
          return;
        }

        if (event.type === "stage.changed") {
          const nextState = asChatState(payload?.to ?? payload?.state);
          if (nextState) {
            setState(nextState);
          }
          return;
        }

        if (event.type === "gate.ready") {
          const parsedGate = parseGateStatus(event.data);
          if (parsedGate) {
            setGate(parsedGate);
          }
          return;
        }

        if (event.type === "run.completed") {
          const nextState = asChatState(payload?.state);
          if (nextState) {
            setState(nextState);
          }
          const parsedGate = parseGateStatus(payload?.gate);
          if (parsedGate) {
            setGate(parsedGate);
          }
          return;
        }

        if (event.type === "error") {
          const message =
            typeof payload?.message === "string"
              ? payload.message
              : "스트림 처리 중 오류가 발생했습니다.";
          setError(message);
        }
      });

      const latestSession = await getRunSessionSnapshot(sessionId);
      setState(latestSession.state);
      setBriefSlots(latestSession.brief_slots);
      setGate(latestSession.gate);

      if (!assistantBuffer.trim()) {
        updateMessageText(
          assistantLineId,
          "응답이 비어 있습니다. 다시 시도하거나 음성 입력을 사용해 주세요."
        );
      }
    } catch (err) {
      try {
        const response: ChatMessageResponse = await postChatMessage(sessionId, {
          message,
        });
        setMessages((previous) =>
          previous.filter((line) => line.id !== assistantLineId)
        );
        applyTurnResponse(response);
      } catch {
        const messageText =
          err instanceof Error ? err.message : "메시지 전송에 실패했습니다.";
        setError(messageText);
        appendMessage({ id: lineId("system"), role: "system", text: messageText });
      }
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

  const handleVoiceSubmit = async (payload: VoiceTurnRequest) => {
    if (!sessionId || voiceSending) {
      return;
    }
    setVoiceSending(true);
    setError(null);

    try {
      const response = await postVoiceTurn(sessionId, payload);
      if (response.transcript.trim()) {
        appendMessage({
          id: lineId("user"),
          role: "user",
          text: response.transcript,
        });
      }
      setState(response.state);
      setBriefSlots(response.brief_slots);
      setGate(response.gate);
      appendMessage({
        id: lineId("assistant"),
        role: "assistant",
        text: response.next_question,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "음성 전송에 실패했습니다.";
      setError(message);
      appendMessage({
        id: lineId("system"),
        role: "system",
        text: message,
      });
    } finally {
      setVoiceSending(false);
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
        <MessageStream items={messages} />

        <form
          onSubmit={handleSubmit}
          style={{ marginTop: "16px", display: "grid", gap: "10px" }}
        >
          <textarea
            rows={3}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="제품명, 카테고리, 특징, 가격대, 타겟, 채널, 목표를 자유롭게 입력하세요."
            disabled={loadingSession || sending || voiceSending}
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
              disabled={loadingSession || sending || voiceSending || !sessionId}
            >
              {sending ? "전송 중..." : "메시지 보내기"}
            </button>
          </div>
        </form>

        <div style={{ marginTop: "12px" }}>
          <VoiceInputButton
            disabled={loadingSession || sending}
            loading={voiceSending}
            onSubmit={handleVoiceSubmit}
          />
        </div>
      </section>

      <section className="glass-panel">
        <h2 className="section-title">브리프 게이트</h2>
        <BriefSlotCard slots={briefSlots} gate={gate} />

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
