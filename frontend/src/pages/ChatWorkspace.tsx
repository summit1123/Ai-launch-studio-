import { useEffect, useState, type FormEvent } from "react";

import {
  createChatSession,
  generateRunAssetsAsync,
  generateRunAsync,
  getJob,
  getRunAssets,
  getChatSession,
  getRun,
  postChatMessage,
  postVoiceTurn,
  streamChatMessage,
  streamVoiceTurn,
} from "../api/client";
import {
  BriefSlotCard,
} from "../components/BriefSlotCard";
import {
  MessageStream,
  type MessageStreamItem,
} from "../components/MessageStream";
import { VoiceInputButton } from "../components/VoiceInputButton";
import { VoicePlaybackToggle } from "../components/VoicePlaybackToggle";
import { LaunchResult } from "./LaunchResult";
import type {
  BriefSlots,
  ChatMessageResponse,
  ChatState,
  GateStatus,
  JobStatus,
  LaunchPackage,
  SlotUpdate,
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

function parseSlotUpdates(value: unknown): SlotUpdate[] {
  const record = asRecord(value);
  if (!record || !Array.isArray(record.slot_updates)) {
    return [];
  }

  const updates: SlotUpdate[] = [];
  for (const raw of record.slot_updates) {
    const item = asRecord(raw);
    if (!item || typeof item.path !== "string") {
      continue;
    }
    updates.push({
      path: item.path,
      value: item.value,
      confidence: typeof item.confidence === "number" ? item.confidence : 0,
    });
  }
  return updates;
}

function applySlotUpdates(
  current: BriefSlots | null,
  updates: SlotUpdate[]
): BriefSlots | null {
  if (!current || updates.length === 0) {
    return current;
  }

  const next: BriefSlots = {
    product: {
      ...current.product,
      features: [...current.product.features],
    },
    target: { ...current.target },
    channel: {
      ...current.channel,
      channels: [...current.channel.channels],
    },
    goal: { ...current.goal },
  };

  for (const update of updates) {
    switch (update.path) {
      case "product.name":
        next.product.name = typeof update.value === "string" ? update.value : null;
        break;
      case "product.category":
        next.product.category = typeof update.value === "string" ? update.value : null;
        break;
      case "product.features":
        next.product.features = Array.isArray(update.value)
          ? update.value
              .map((item) => (typeof item === "string" ? item.trim() : ""))
              .filter(Boolean)
          : [];
        break;
      case "product.price_band":
        next.product.price_band = typeof update.value === "string" ? update.value : null;
        break;
      case "target.who":
        next.target.who = typeof update.value === "string" ? update.value : null;
        break;
      case "target.why":
        next.target.why = typeof update.value === "string" ? update.value : null;
        break;
      case "channel.channels":
        next.channel.channels = Array.isArray(update.value)
          ? update.value
              .map((item) => (typeof item === "string" ? item.trim() : ""))
              .filter(Boolean)
          : [];
        break;
      case "goal.weekly_goal":
        if (
          update.value === "reach" ||
          update.value === "inquiry" ||
          update.value === "purchase"
        ) {
          next.goal.weekly_goal = update.value;
        }
        break;
      case "goal.video_seconds": {
        const parsed = Number(update.value);
        next.goal.video_seconds =
          Number.isFinite(parsed) && parsed > 0 ? parsed : null;
        break;
      }
      default:
        break;
    }
  }

  return next;
}

async function getRunSessionSnapshot(sessionId: string) {
  return getChatSession(sessionId);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function quickRepliesByMissingPath(path: string | undefined): string[] {
  switch (path) {
    case "product.name":
      return ["아이폰 17", "글로우세럼X", "루트 밸런스 토닉"];
    case "product.category":
      return ["스마트폰", "스킨케어", "헬스케어"];
    case "product.features":
      return ["저자극, 빠른 흡수, 비건 포뮬러", "초경량, 내구성, 생활방수"];
    case "product.price_band":
      return ["중가", "프리미엄", "39,000원"];
    case "target.who":
      return ["20대 직장인", "30대 남성", "민감성 피부 사용자"];
    case "target.why":
      return ["휴대성이 필요해서", "트러블 진정을 원해서", "시간 절약이 필요해서"];
    case "channel.channels":
      return ["인스타, 네이버", "유튜브, 틱톡"];
    case "goal.weekly_goal":
      return ["조회", "문의", "구매"];
    default:
      return [];
  }
}

function hasGeneratedAssets(launchPackage: LaunchPackage | null): boolean {
  if (!launchPackage) {
    return false;
  }
  return Boolean(
    launchPackage.marketing_assets.poster_image_url ||
      launchPackage.marketing_assets.video_url
  );
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
  const [assetsReady, setAssetsReady] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [runJobId, setRunJobId] = useState<string | null>(null);
  const [runJobStatus, setRunJobStatus] = useState<JobStatus | null>(null);
  const [runJobProgress, setRunJobProgress] = useState(0);
  const [assetGenerating, setAssetGenerating] = useState(false);
  const [assetJobId, setAssetJobId] = useState<string | null>(null);
  const [assetJobStatus, setAssetJobStatus] = useState<JobStatus | null>(null);
  const [assetJobProgress, setAssetJobProgress] = useState(0);
  const nextMissingPath = gate?.missing_required?.[0];
  const quickReplies = quickRepliesByMissingPath(nextMissingPath);
  const latestAssistantText =
    [...messages]
      .reverse()
      .find((line) => line.role === "assistant" && line.text.trim().length > 0)
      ?.text ?? "";

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
    setMessages((previous) => {
      const last = previous[previous.length - 1];
      if (
        last &&
        last.role === line.role &&
        last.text.trim() &&
        last.text.trim() === line.text.trim()
      ) {
        return previous;
      }
      return [...previous, line];
    });
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
    let streamError: unknown = null;

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

        if (event.type === "slot.updated") {
          const updates = parseSlotUpdates(event.data);
          if (updates.length > 0) {
            setBriefSlots((previous) => applySlotUpdates(previous, updates));
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
    } catch (err) {
      streamError = err;
    }

    if (streamError === null) {
      try {
        const latestSession = await getRunSessionSnapshot(sessionId);
        setState(latestSession.state);
        setBriefSlots(latestSession.brief_slots);
        setGate(latestSession.gate);
      } catch (err) {
        const messageText =
          err instanceof Error
            ? err.message
            : "세션 동기화에 실패했습니다. 다음 턴에서 자동 재동기화됩니다.";
        setError(messageText);
      }

      if (!assistantBuffer.trim()) {
        updateMessageText(
          assistantLineId,
          "응답이 비어 있습니다. 다시 시도하거나 음성 입력을 사용해 주세요."
        );
      }
    } else {
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
          streamError instanceof Error
            ? streamError.message
            : "메시지 전송에 실패했습니다.";
        setError(messageText);
        appendMessage({ id: lineId("system"), role: "system", text: messageText });
      }
    }
    setSending(false);
  };

  const handleGenerate = async () => {
    if (!sessionId || !gate?.ready || generating || assetGenerating) {
      return;
    }
    const POLL_INTERVAL_MS = 1_500;
    const MAX_POLLS = 240;

    setGenerating(true);
    setError(null);
    setLaunchPackage(null);
    setAssetsReady(false);
    setRunId(null);
    setRunJobId(null);
    setRunJobStatus(null);
    setRunJobProgress(0);
    setAssetJobId(null);
    setAssetJobStatus(null);
    setAssetJobProgress(0);

    try {
      const generated = await generateRunAsync(sessionId);
      setRunJobId(generated.job_id);
      setRunJobStatus(generated.status);
      appendMessage({
        id: lineId("system"),
        role: "system",
        text: "기획 보고서 생성을 시작했습니다. 분석 결과를 수집하는 중입니다.",
      });

      for (let pollCount = 0; pollCount < MAX_POLLS; pollCount += 1) {
        const job = await getJob(generated.job_id);
        setRunJobStatus(job.status);
        setRunJobProgress(job.progress);

        if (job.status === "failed") {
          throw new Error(job.error || "비동기 생성 작업이 실패했습니다.");
        }
        if (job.status === "completed" && job.run_id) {
          setRunId(job.run_id);
          const result = await getRun(job.run_id);
          setState(result.state);
          setLaunchPackage(result.package);
          setAssetsReady(hasGeneratedAssets(result.package));
          appendMessage({
            id: lineId("system"),
            role: "system",
            text: "기획 보고서 생성 완료. 내용을 검토한 뒤 이벤트(포스터/영상) 생성을 진행하세요.",
          });
          return;
        }

        if (job.status === "running") {
          setState("RUN_RESEARCH");
        }
        await delay(POLL_INTERVAL_MS);
      }

      throw new Error(
        "생성 시간이 길어지고 있습니다. 잠시 후 작업 상태를 다시 확인해 주세요."
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "런 생성에 실패했습니다.";
      setError(message);
      appendMessage({
        id: lineId("system"),
        role: "system",
        text: message,
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateAssets = async () => {
    if (!runId || !launchPackage || assetGenerating || generating) {
      return;
    }
    const POLL_INTERVAL_MS = 1_500;
    const MAX_POLLS = 240;

    setAssetGenerating(true);
    setError(null);
    setAssetJobId(null);
    setAssetJobStatus(null);
    setAssetJobProgress(0);

    try {
      const generated = await generateRunAssetsAsync(runId);
      setAssetJobId(generated.job_id);
      setAssetJobStatus(generated.status);
      appendMessage({
        id: lineId("system"),
        role: "system",
        text: "이벤트 생성 시작: 포스터/영상 소재를 생성 중입니다.",
      });

      for (let pollCount = 0; pollCount < MAX_POLLS; pollCount += 1) {
        const job = await getJob(generated.job_id);
        setAssetJobStatus(job.status);
        setAssetJobProgress(job.progress);

        if (job.status === "failed") {
          throw new Error(job.error || "이벤트 생성 작업이 실패했습니다.");
        }
        if (job.status === "completed") {
          const assets = await getRunAssets(runId);
          setLaunchPackage((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              marketing_assets: {
                ...previous.marketing_assets,
                poster_image_url: assets.poster_image_url ?? undefined,
                video_url: assets.video_url ?? undefined,
              },
            };
          });
          const hasAssets =
            Boolean(assets.poster_image_url) || Boolean(assets.video_url);
          setAssetsReady(hasAssets);
          appendMessage({
            id: lineId("system"),
            role: "system",
            text: hasAssets
              ? "이벤트 생성 완료: 보고서 아래에 포스터/영상이 업데이트되었습니다."
              : "이벤트 생성이 완료됐지만 생성된 파일이 없습니다. 프롬프트를 조정해 다시 시도해 주세요.",
          });
          return;
        }
        if (job.status === "running") {
          setState("GEN_CREATIVES");
        }
        await delay(POLL_INTERVAL_MS);
      }

      throw new Error(
        "이벤트 생성 시간이 길어지고 있습니다. 잠시 후 작업 상태를 다시 확인해 주세요."
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "이벤트 생성에 실패했습니다.";
      setError(message);
      appendMessage({
        id: lineId("system"),
        role: "system",
        text: message,
      });
    } finally {
      setAssetGenerating(false);
    }
  };

  const handleVoiceSubmit = async (payload: VoiceTurnRequest) => {
    if (!sessionId || voiceSending) {
      return;
    }
    setVoiceSending(true);
    setError(null);
    const userLineId = lineId("user");
    const assistantLineId = lineId("assistant");
    let assistantBuffer = "";
    let transcriptBuffer = "";
    let streamError: unknown = null;

    appendMessage({ id: userLineId, role: "user", text: "" });
    appendMessage({ id: assistantLineId, role: "assistant", text: "" });

    try {
      await streamVoiceTurn(sessionId, payload, (event: StreamEvent) => {
        const payloadRecord = asRecord(event.data);

        if (event.type === "voice.delta") {
          const transcript = payloadRecord?.transcript;
          if (typeof transcript === "string") {
            transcriptBuffer = transcript;
            updateMessageText(userLineId, transcriptBuffer);
          }
          const nextState = asChatState(payloadRecord?.state);
          if (nextState) {
            setState(nextState);
          }
          return;
        }

        if (event.type === "slot.updated") {
          const updates = parseSlotUpdates(event.data);
          if (updates.length > 0) {
            setBriefSlots((previous) => applySlotUpdates(previous, updates));
          }
          return;
        }

        if (event.type === "planner.delta") {
          const text = payloadRecord?.text;
          if (typeof text === "string") {
            assistantBuffer += text;
            updateMessageText(assistantLineId, assistantBuffer);
          }
          return;
        }

        if (event.type === "stage.changed") {
          const nextState = asChatState(payloadRecord?.to ?? payloadRecord?.state);
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

        if (event.type === "error") {
          const message =
            typeof payloadRecord?.message === "string"
              ? payloadRecord.message
              : "음성 스트림 처리 중 오류가 발생했습니다.";
          setError(message);
        }
      });
    } catch (err) {
      streamError = err;
    }

    if (streamError === null) {
      if (!transcriptBuffer.trim()) {
        setMessages((previous) =>
          previous.filter((line) => line.id !== userLineId)
        );
      }
      try {
        const latestSession = await getRunSessionSnapshot(sessionId);
        setState(latestSession.state);
        setBriefSlots(latestSession.brief_slots);
        setGate(latestSession.gate);
      } catch (err) {
        const messageText =
          err instanceof Error
            ? err.message
            : "음성 턴 동기화에 실패했습니다. 다음 턴에서 자동 재동기화됩니다.";
        setError(messageText);
      }
      if (!assistantBuffer.trim()) {
        updateMessageText(
          assistantLineId,
          "응답이 비어 있습니다. 다시 시도하거나 텍스트 입력을 사용해 주세요."
        );
      }
    } else {
      setMessages((previous) =>
        previous.filter(
          (line) => line.id !== assistantLineId && line.id !== userLineId
        )
      );
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
      } catch {
        const message =
          streamError instanceof Error
            ? streamError.message
            : "음성 전송에 실패했습니다.";
        setError(message);
        appendMessage({
          id: lineId("system"),
          role: "system",
          text: message,
        });
      }
    }
    setVoiceSending(false);
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
              background:
                "linear-gradient(160deg, rgba(11, 27, 55, 0.82) 0%, rgba(7, 18, 38, 0.8) 100%)",
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
        {quickReplies.length > 0 && (
          <div style={{ marginTop: "10px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {quickReplies.map((reply) => (
              <button
                key={reply}
                type="button"
                className="btn-secondary-sm"
                onClick={() => setDraft(reply)}
                disabled={loadingSession || sending || voiceSending}
              >
                {reply}
              </button>
            ))}
          </div>
        )}

        <div style={{ marginTop: "12px" }}>
          <VoiceInputButton
            disabled={loadingSession || sending}
            loading={voiceSending}
            onSubmit={handleVoiceSubmit}
          />
        </div>
        <div style={{ marginTop: "8px" }}>
          <VoicePlaybackToggle
            sessionId={sessionId}
            text={latestAssistantText}
            disabled={loadingSession || sending || voiceSending}
          />
        </div>
      </section>

      <section className="glass-panel">
        <h2 className="section-title">실행 단계</h2>
        <BriefSlotCard slots={briefSlots} gate={gate} />

        <div
          style={{
            marginTop: "14px",
            display: "flex",
            gap: "10px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!sessionId || !gate?.ready || generating || assetGenerating}
          >
            {generating ? `기획 생성 중...(${runJobProgress}%)` : "1) 기획 보고서 생성"}
          </button>
          {launchPackage && runId && (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleGenerateAssets}
              disabled={assetGenerating || generating}
            >
              {assetGenerating
                ? `이벤트 생성 중...(${assetJobProgress}%)`
                : "2) 이벤트(포스터/영상) 추가 생성"}
            </button>
          )}
          {runId && <small style={{ color: "var(--muted)" }}>run_id: {runId}</small>}
        </div>
        {runJobId && (
          <small style={{ color: "var(--muted)" }}>
            job_id: {runJobId} · 상태: {runJobStatus ?? "queued"} · 진행률: {runJobProgress}%
          </small>
        )}
        {assetJobId && (
          <small style={{ color: "var(--muted)", display: "block", marginTop: "4px" }}>
            asset_job_id: {assetJobId} · 상태: {assetJobStatus ?? "queued"} · 진행률:{" "}
            {assetJobProgress}%
          </small>
        )}
      </section>

      {error && (
        <section className="glass-panel" style={{ borderColor: "rgba(239, 68, 68, 0.35)" }}>
          <strong style={{ color: "#fda4af" }}>오류</strong>
          <p style={{ marginBottom: 0 }}>{error}</p>
        </section>
      )}

      {launchPackage && (
        <section className="glass-panel" style={{ padding: 0, overflow: "hidden" }}>
          <LaunchResult launchPackage={launchPackage} showAssets={assetsReady} />
        </section>
      )}
    </main>
  );
}
