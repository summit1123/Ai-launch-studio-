import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import {
  createChatSession,
  generateRunAsync,
  getJob,
  getChatSession,
  getRun,
  postChatMessage,
  streamChatMessage,
  uploadProductImage,
} from "../api/client";
import {
  MessageStream,
  type MessageStreamItem,
} from "../components/MessageStream";
import { LaunchResult } from "./LaunchResult";
import type {
  BriefSlots,
  ChatMessageResponse,
  ChatState,
  GateStatus,
  JobGetResponse,
  LaunchPackage,
  SlotUpdate,
  StreamEvent,
} from "../types";

function lineId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";
const ASSET_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
const LUMI_MASCOT_URL = `${ASSET_BASE_URL}/static/assets/planner_mascot.png`;

function resolveAssetUrl(path: string | null | undefined): string | null {
  if (!path) {
    return null;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${ASSET_BASE_URL}${path}`;
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
      case "product.image_url":
        next.product.image_url =
          typeof update.value === "string" ? update.value : null;
        break;
      case "product.image_context":
        next.product.image_context =
          typeof update.value === "string" ? update.value : null;
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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

type WorkspaceScene = "chat" | "meeting" | "result";

type MeetingStage = {
  title: string;
  detail: string;
};

type DeliverableState = "queued" | "active" | "done";

type MeetingDeliverable = {
  key: "report" | "poster" | "video";
  label: string;
  detail: string;
  startAt: number;
  doneAt: number;
};

const MEETING_STAGES: MeetingStage[] = [
  { title: "오케스트레이터", detail: "브리프 해석과 실행 순서를 정리 중" },
  { title: "리서치 에이전트", detail: "시장/경쟁 시그널을 수집하는 중" },
  { title: "전략 에이전트", detail: "포지셔닝과 메시지 구조를 설계 중" },
  { title: "플래너 에이전트", detail: "실행 가능한 기획 보고서를 조립 중" },
  { title: "크리에이티브 에이전트", detail: "영상/포스터 소재 초안을 확정 중" },
  {
    title: "미디어 렌더러",
    detail: "포스터·영상 파일을 실제로 생성 중 (고화질 영상은 2~3분 소요될 수 있어요)",
  },
];

const MEETING_DELIVERABLES: MeetingDeliverable[] = [
  {
    key: "report",
    label: "기획 보고서",
    detail: "시장평가·전략·실행안",
    startAt: 35,
    doneAt: 70,
  },
  {
    key: "poster",
    label: "포스터",
    detail: "제품 중심 광고 비주얼",
    startAt: 88,
    doneAt: 96,
  },
  {
    key: "video",
    label: "영상",
    detail: "숏폼 광고 컷",
    startAt: 92,
    doneAt: 99,
  },
];

const MINI_GAME_CELL_COUNT = 9;

const LUMI_SCRIPT_BY_MOOD: Record<"curious" | "focused" | "excited" | "done", string[]> = {
  curious: [
    "브리프를 읽고 핵심 포인트를 추출 중이에요.",
    "시장/타겟 시그널을 모아서 전략 재료를 만들고 있어요.",
  ],
  focused: [
    "지금은 전략을 조합해서 실행 가능한 구조로 바꾸는 중이에요.",
    "에이전트들이 같은 톤으로 기획안을 맞추고 있어요.",
  ],
  excited: [
    "좋아요! 지금 포스터와 영상을 렌더링하고 있어요.",
    "고화질 영상 생성은 보통 2~3분 정도 걸릴 수 있어요.",
    "마지막 출력물 품질을 맞추는 단계예요.",
  ],
  done: [
    "거의 끝났어요. 결과 패키지 정리 중이에요.",
    "마지막 검수 후 결과 화면으로 이동할게요.",
  ],
};

function stageIndexByProgress(progress: number, totalStages: number): number {
  if (totalStages <= 1) {
    return 0;
  }
  if (progress <= 0) {
    return 0;
  }
  const normalized = Math.min(99, Math.max(0, progress));
  return Math.min(totalStages - 1, Math.floor((normalized / 100) * totalStages));
}

function resolveLumiMood(progress: number): {
  key: "curious" | "focused" | "excited" | "done";
  text: string;
} {
  if (progress >= 96) {
    return { key: "done", text: "마무리 중! 결과를 정리하고 있어요." };
  }
  if (progress >= 78) {
    return {
      key: "excited",
      text: "지금 포스터랑 영상을 렌더링 중이에요. 고화질 영상은 2~3분 정도 걸릴 수 있어요.",
    };
  }
  if (progress >= 35) {
    return { key: "focused", text: "전략을 조립해서 실행안으로 바꾸는 중이에요." };
  }
  return { key: "curious", text: "브리프를 읽고 핵심 포인트를 모으고 있어요." };
}

function resolveDeliverableState(progress: number, item: MeetingDeliverable): DeliverableState {
  if (progress >= item.doneAt) {
    return "done";
  }
  if (progress >= item.startAt) {
    return "active";
  }
  return "queued";
}

function estimateRemainingSeconds(progress: number, elapsedSeconds: number): number | null {
  if (progress <= 8 || elapsedSeconds < 10) {
    return null;
  }
  const speed = progress / elapsedSeconds;
  if (!Number.isFinite(speed) || speed <= 0) {
    return null;
  }
  const remain = Math.round((100 - progress) / speed);
  if (!Number.isFinite(remain) || remain <= 0) {
    return null;
  }
  return Math.max(5, Math.min(remain, 3600));
}

function formatDuration(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function nextMiniGameTarget(previous: number): number {
  const next = Math.floor(Math.random() * MINI_GAME_CELL_COUNT);
  if (next === previous) {
    return (next + 1) % MINI_GAME_CELL_COUNT;
  }
  return next;
}

export function ChatWorkspace() {
  const [workspaceScene, setWorkspaceScene] = useState<WorkspaceScene>("chat");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<ChatState>("CHAT_COLLECTING");
  const [briefSlots, setBriefSlots] = useState<BriefSlots | null>(null);
  const [gate, setGate] = useState<GateStatus | null>(null);
  const [messages, setMessages] = useState<MessageStreamItem[]>([]);
  const [draft, setDraft] = useState("");
  const productImageInputRef = useRef<HTMLInputElement | null>(null);
  const [productImageFileName, setProductImageFileName] = useState<string | null>(null);
  const [localImagePreviewUrl, setLocalImagePreviewUrl] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const voiceSending = false;
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [launchPackage, setLaunchPackage] = useState<LaunchPackage | null>(null);
  const [runJobProgress, setRunJobProgress] = useState(0);
  const [meetingStageIndex, setMeetingStageIndex] = useState(0);
  const [meetingLogs, setMeetingLogs] = useState<string[]>([]);
  const [generationStartedAt, setGenerationStartedAt] = useState<number | null>(null);
  const [meetingNow, setMeetingNow] = useState<number>(Date.now());
  const [miniGameTargetIndex, setMiniGameTargetIndex] = useState<number>(() =>
    Math.floor(Math.random() * MINI_GAME_CELL_COUNT)
  );
  const [miniGameScore, setMiniGameScore] = useState(0);
  const [miniGameMisses, setMiniGameMisses] = useState(0);
  const [miniGameStreak, setMiniGameStreak] = useState(0);
  const [miniGameBestStreak, setMiniGameBestStreak] = useState(0);
  const [miniGameRounds, setMiniGameRounds] = useState(0);
  const [miniGameHint, setMiniGameHint] = useState(
    "루미가 빛나는 칸을 눌러 점수를 모아보세요."
  );
  const [miniGameOpen, setMiniGameOpen] = useState(false);
  const miniGameHitRef = useRef(false);
  const miniGameRoundsRef = useRef(0);
  const persistentImageUrl = resolveAssetUrl(briefSlots?.product.image_url);
  const imagePreviewUrl = localImagePreviewUrl ?? persistentImageUrl ?? null;
  const imageSummary = briefSlots?.product.image_context?.trim() || null;
  const streamCompact =
    messages.length <= 1 && !sending && !voiceSending && !imageUploading;
  const activeMeetingProgress = runJobProgress;
  const activeMeetingStages = MEETING_STAGES;
  const activeMeetingStep =
    activeMeetingStages[Math.min(meetingStageIndex, activeMeetingStages.length - 1)] ??
    activeMeetingStages[0];
  const normalizedMeetingProgress = Math.min(100, Math.max(8, activeMeetingProgress));
  const lumiMood = resolveLumiMood(activeMeetingProgress);
  const lumiScriptList = LUMI_SCRIPT_BY_MOOD[lumiMood.key];
  const generationElapsedSeconds = generationStartedAt
    ? Math.max(1, Math.floor((meetingNow - generationStartedAt) / 1000))
    : 0;
  const etaSeconds = estimateRemainingSeconds(activeMeetingProgress, generationElapsedSeconds);
  const stalledOnEarlyStage =
    generating && generationElapsedSeconds >= 35 && activeMeetingProgress <= 20;
  const activeLumiScript =
    lumiScriptList[Math.floor(generationElapsedSeconds / 7) % lumiScriptList.length];
  const activeMeetingStepLabel =
    activeMeetingProgress >= 96
      ? "최종 정리 중"
      : `${activeMeetingStep?.title ?? "오케스트레이터"} 작업 중`;
  const miniGameTickMs =
    activeMeetingProgress >= 78 ? 760 : activeMeetingProgress >= 35 ? 860 : 980;
  const miniGameDifficultyLabel =
    miniGameTickMs <= 760 ? "하드" : miniGameTickMs <= 860 ? "노멀" : "이지";
  const miniGameCells = Array.from({ length: MINI_GAME_CELL_COUNT }, (_, index) => index);
  const miniGameAttempts = miniGameScore + miniGameMisses;
  const miniGameAccuracy =
    miniGameAttempts > 0 ? Math.round((miniGameScore / miniGameAttempts) * 100) : null;

  const appendMeetingLog = (line: string) => {
    setMeetingLogs((previous) => {
      if (previous[previous.length - 1] === line) {
        return previous;
      }
      return [...previous, line];
    });
  };

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

  useEffect(
    () => () => {
      if (localImagePreviewUrl) {
        URL.revokeObjectURL(localImagePreviewUrl);
      }
    },
    [localImagePreviewUrl]
  );

  useEffect(() => {
    if (!generating || workspaceScene !== "meeting") {
      return;
    }
    const timerId = window.setInterval(() => {
      setMeetingNow(Date.now());
    }, 1_000);
    return () => {
      window.clearInterval(timerId);
    };
  }, [generating, workspaceScene]);

  useEffect(() => {
    if (!generating || workspaceScene !== "meeting" || !miniGameOpen) {
      miniGameHitRef.current = false;
      return;
    }

    const timerId = window.setInterval(() => {
      if (miniGameRoundsRef.current > 0 && !miniGameHitRef.current) {
        setMiniGameMisses((previous) => previous + 1);
        setMiniGameStreak(0);
      }
      miniGameHitRef.current = false;
      miniGameRoundsRef.current += 1;
      setMiniGameRounds(miniGameRoundsRef.current);
      setMiniGameTargetIndex((previous) => nextMiniGameTarget(previous));
    }, miniGameTickMs);

    return () => {
      window.clearInterval(timerId);
    };
  }, [generating, workspaceScene, miniGameTickMs, miniGameOpen]);

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
          "응답이 비어 있습니다. 다시 시도해 주세요."
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

  const openProductImagePicker = () => {
    if (loadingSession || sending || voiceSending || imageUploading) {
      return;
    }
    productImageInputRef.current?.click();
  };

  const handleProductImageChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    event.currentTarget.value = "";

    if (localImagePreviewUrl) {
      URL.revokeObjectURL(localImagePreviewUrl);
    }

    if (!file) {
      setProductImageFileName(null);
      setLocalImagePreviewUrl(null);
      return;
    }
    if (!sessionId) {
      setError("세션 준비 중입니다. 잠시 후 다시 시도해 주세요.");
      return;
    }

    setProductImageFileName(file.name);
    const previewUrl = URL.createObjectURL(file);
    setLocalImagePreviewUrl(previewUrl);
    setImageUploading(true);
    setError(null);
    appendMessage({
      id: lineId("user"),
      role: "user",
      text: `[제품 이미지 업로드] ${file.name}`,
    });

    try {
      const response = await uploadProductImage(sessionId, {
        image: file,
        locale: "ko-KR",
      });
      setState(response.state);
      setBriefSlots(response.brief_slots);
      setGate(response.gate);
      appendMessage({
        id: lineId("assistant"),
        role: "assistant",
        text: response.next_question,
      });
      URL.revokeObjectURL(previewUrl);
      setLocalImagePreviewUrl(null);
    } catch (uploadError) {
      const message =
        uploadError instanceof Error
          ? uploadError.message
          : "이미지 업로드에 실패했습니다.";
      setError(message);
      appendMessage({ id: lineId("system"), role: "system", text: message });
    } finally {
      setImageUploading(false);
    }
  };

  const handleGenerate = async () => {
    if (!sessionId || !gate?.ready || generating) {
      return;
    }

    setGenerating(true);
    setGenerationStartedAt(Date.now());
    setMeetingNow(Date.now());
    setWorkspaceScene("meeting");
    setMeetingStageIndex(0);
    setMeetingLogs([
      "루미 오케스트레이터가 원클릭 생성을 시작했습니다.",
      "기획서, 포스터, 영상을 한 번에 생성합니다.",
      "안내: 고화질 영상 생성은 약 2~3분 소요될 수 있습니다.",
    ]);
    setError(null);
    setLaunchPackage(null);
    setRunJobProgress(0);
    setMiniGameOpen(false);
    setMiniGameScore(0);
    setMiniGameMisses(0);
    setMiniGameStreak(0);
    setMiniGameBestStreak(0);
    setMiniGameRounds(0);
    setMiniGameHint("루미가 빛나는 칸을 눌러 점수를 모아보세요.");
    setMiniGameTargetIndex(Math.floor(Math.random() * MINI_GAME_CELL_COUNT));
    miniGameHitRef.current = false;
    miniGameRoundsRef.current = 0;

    try {
      const generated = await generateRunAsync(sessionId);
      appendMeetingLog("에이전트 파이프라인을 실행했습니다.");
      let currentStageIndex = 0;
      let resolvedRunId: string | null = null;
      let completionLogged = false;
      let jobFailureMessage: string | null = null;
      const applyRunJobUpdate = (job: JobGetResponse): void => {
        setRunJobProgress(job.progress);
        if (job.note) {
          appendMeetingLog(job.note);
        }

        const nextStageIndex = stageIndexByProgress(job.progress, MEETING_STAGES.length);
        if (nextStageIndex !== currentStageIndex) {
          currentStageIndex = nextStageIndex;
          setMeetingStageIndex(nextStageIndex);
          appendMeetingLog(
            `${MEETING_STAGES[nextStageIndex].title}: ${MEETING_STAGES[nextStageIndex].detail}`
          );
        }

        if (job.status === "running") {
          if (job.progress >= 78) {
            setState("GEN_CREATIVES");
          } else if (job.progress >= 35) {
            setState("GEN_STRATEGY");
          } else {
            setState("RUN_RESEARCH");
          }
          return;
        }
        if (job.status === "failed") {
          jobFailureMessage = job.error || "비동기 생성 작업이 실패했습니다.";
          return;
        }
        if (job.status === "completed") {
          resolvedRunId = job.run_id;
          setMeetingStageIndex(MEETING_STAGES.length - 1);
          if (!completionLogged) {
            appendMeetingLog("기획서/포스터/영상 생성 프로세스가 완료되었습니다.");
            completionLogged = true;
          }
        }
      };

      appendMeetingLog("연결 안정성을 위해 폴링 모드로 진행 상황을 확인합니다.");
      const POLL_INTERVAL_MS = 1_200;
      const MAX_POLLS = 900; // 18 minutes
      let terminal = false;
      for (let pollCount = 0; pollCount < MAX_POLLS; pollCount += 1) {
        const polledJob = await getJob(generated.job_id);
        applyRunJobUpdate(polledJob);
        if (jobFailureMessage) {
          throw new Error(jobFailureMessage);
        }
        if (polledJob.status === "completed") {
          terminal = true;
          break;
        }
        await sleep(POLL_INTERVAL_MS);
      }
      if (!terminal && !resolvedRunId) {
        throw new Error("생성 상태 확인 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.");
      }

      if (!resolvedRunId) {
        appendMeetingLog("스트림 종료 후 완료 상태를 재확인하고 있습니다.");
        const RECOVERY_POLL_INTERVAL_MS = 1_000;
        const RECOVERY_MAX_POLLS = 120;
        for (let recovery = 0; recovery < RECOVERY_MAX_POLLS; recovery += 1) {
          const recoveredJob = await getJob(generated.job_id);
          applyRunJobUpdate(recoveredJob);
          if (jobFailureMessage) {
            throw new Error(jobFailureMessage);
          }
          if (recoveredJob.status === "completed" && recoveredJob.run_id) {
            resolvedRunId = recoveredJob.run_id;
            break;
          }
          if (recoveredJob.status === "failed") {
            throw new Error(recoveredJob.error || "비동기 생성 작업이 실패했습니다.");
          }
          await sleep(RECOVERY_POLL_INTERVAL_MS);
        }
      }

      if (!resolvedRunId) {
        throw new Error("작업은 완료됐지만 run_id를 받지 못했습니다.");
      }

      const result = await getRun(resolvedRunId);
      setState(result.state);
      setLaunchPackage(result.package);
      const hasPoster = Boolean(result.package.marketing_assets.poster_image_url);
      const hasVideo = Boolean(result.package.marketing_assets.video_url);
      if (!hasPoster || !hasVideo) {
        appendMeetingLog(
          "일부 미디어 생성이 누락되었습니다. 영상 모델 권한/정책 또는 프롬프트 제약으로 생성되지 않을 수 있습니다."
        );
      }
      setWorkspaceScene("result");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "런 생성에 실패했습니다.";
      setError(message);
      appendMeetingLog(`실행 오류: ${message}`);
      setWorkspaceScene("chat");
    } finally {
      setGenerating(false);
      setGenerationStartedAt(null);
    }
  };

  const handleMiniGameTap = (index: number) => {
    if (!generating || workspaceScene !== "meeting") {
      return;
    }

    if (index !== miniGameTargetIndex) {
      setMiniGameHint("조금만 더! 빛나는 루미 칸을 눌러주세요.");
      setMiniGameStreak(0);
      return;
    }

    if (miniGameHitRef.current) {
      return;
    }
    miniGameHitRef.current = true;
    setMiniGameScore((previous) => previous + 1);
    setMiniGameStreak((previous) => {
      const next = previous + 1;
      setMiniGameBestStreak((best) => Math.max(best, next));
      return next;
    });
    setMiniGameHint("정확해요! 다음 루미를 잡아보세요.");
  };

  return (
    <main className="container" style={{ marginTop: "80px", paddingBottom: "120px" }}>
      <header className="hero">
        <div className="eyebrow">Chat MVP</div>
        <h1>Chat Workspace</h1>
        <p>
          대화형으로 제품 정보를 정리하고, 준비가 끝나면 기획서·포스터·영상을 한 번에
          생성합니다.
        </p>
      </header>

      {workspaceScene === "chat" && (
        <section className="glass-panel">
          <h2 className="section-title">대화</h2>

          <div className="chat-entry-toolbar">
            <button
              type="button"
              className="btn-secondary-sm"
              onClick={openProductImagePicker}
              disabled={loadingSession || sending || voiceSending || imageUploading}
            >
              {imageUploading ? "이미지 분석 중..." : "제품 이미지 올리기"}
            </button>
            <small style={{ color: "var(--muted)" }}>
              이미지를 선택하면 즉시 분석해서 대화에 반영합니다.
              {productImageFileName ? ` (최근 업로드: ${productImageFileName})` : ""}
            </small>
            <input
              ref={productImageInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={(event) => {
                void handleProductImageChange(event);
              }}
              style={{ display: "none" }}
            />
          </div>
          {imagePreviewUrl && (
            <div className="chat-image-preview-box" style={{ marginBottom: "12px" }}>
              <img src={imagePreviewUrl} alt="제품 참조 이미지" className="chat-image-preview" />
              <div>
                <strong>이미지 요약</strong>
                <p>{imageSummary ?? "이미지 분석 결과를 반영하는 중입니다."}</p>
              </div>
            </div>
          )}

          <MessageStream items={messages} compact={streamCompact} />

          <div className="chat-mode-toggle">
            <small style={{ color: "var(--muted)" }}>
              입력 방식: <strong>텍스트</strong> | 상태:{" "}
              <strong>{state === "CHAT_COLLECTING" ? "대화 진행 중" : stageLabel(state)}</strong>
            </small>
          </div>

          <form
            onSubmit={handleSubmit}
            style={{ marginTop: "10px", display: "grid", gap: "10px" }}
          >
            <textarea
              rows={3}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="자유롭게 답변해 주세요. 한 문장으로 보내도 됩니다."
              disabled={loadingSession || sending || voiceSending || imageUploading}
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
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                type="submit"
                className="btn-primary-sm"
                disabled={
                  loadingSession || sending || voiceSending || imageUploading || !sessionId
                }
              >
                {sending ? "전송 중..." : "메시지 보내기"}
              </button>
            </div>
          </form>

          {gate?.ready && !launchPackage && !generating && (
            <section className="chat-ready-cta">
              <strong>준비 완료. 원클릭으로 결과를 생성해볼까요?</strong>
              <p>기획서, 포스터, 영상을 한 번에 생성하고 완료 결과만 보여줍니다.</p>
              <button
                type="button"
                className="btn-primary"
                onClick={handleGenerate}
                disabled={!sessionId}
              >
                원클릭 생성 시작
              </button>
            </section>
          )}
        </section>
      )}

      {workspaceScene === "meeting" && (
        <section className="glass-panel meeting-room">
          <div className="meeting-room-head">
            <div>
              <h2 className="section-title">에이전트 회의실</h2>
              <p className="meeting-room-subtitle">
                리서치부터 미디어 렌더링까지 한 번에 처리하고 있습니다.
              </p>
            </div>
            <div className="meeting-badge-row">
              <span className="meeting-live-chip">LIVE</span>
              <span className="meeting-badge">
                단계 {Math.min(meetingStageIndex + 1, activeMeetingStages.length)}/
                {activeMeetingStages.length}
              </span>
              <button
                type="button"
                className="meeting-mini-toggle"
                onClick={() => setMiniGameOpen((previous) => !previous)}
              >
                {miniGameOpen ? "미니게임 닫기" : "미니게임 열기"}
              </button>
            </div>
          </div>

          <div className="meeting-progress-panel">
            <div className="meeting-progress-head">
              <strong>{activeMeetingStepLabel}</strong>
              <span>{activeMeetingProgress}%</span>
            </div>
            <div className={`meeting-lumi-status ${lumiMood.key}`}>
              <img
                src={LUMI_MASCOT_URL}
                alt="루미 상태"
                className="meeting-lumi-avatar"
              />
              <p>{lumiMood.text}</p>
            </div>
            <div className="meeting-progress-track">
              <div
                className="meeting-progress-fill"
                style={{ width: `${normalizedMeetingProgress}%` }}
              />
              <img
                src={LUMI_MASCOT_URL}
                alt="루미 진행 마커"
                className={`meeting-progress-mascot ${lumiMood.key}`}
                style={{ left: `calc(${normalizedMeetingProgress}% - 22px)` }}
              />
            </div>
          </div>

          <div className="meeting-experience">
            <section className={`meeting-lumi-stage ${lumiMood.key}`}>
              <div className="meeting-lumi-speech-row">
                <img
                  src={LUMI_MASCOT_URL}
                  alt="루미 애니메이션"
                  className="meeting-lumi-main meeting-lumi-main-inline"
                />
                <div className="meeting-lumi-bubble">
                  <strong>루미 브리핑</strong>
                  <p>{activeLumiScript}</p>
                </div>
              </div>
              <div className="meeting-lumi-meta">
                <span>경과 {formatDuration(generationElapsedSeconds)}</span>
                <span>
                  {etaSeconds === null
                    ? "예상 남은 시간 계산 중"
                    : `예상 남은 ${formatDuration(etaSeconds)}`}
                </span>
              </div>
              {stalledOnEarlyStage && (
                <small className="meeting-lumi-stall-hint">
                  초기 에이전트 호출 시간이 길어질 수 있어요. 잠시만 기다려주세요.
                </small>
              )}
            </section>

            <div className="meeting-side-stack">
              <section className="meeting-deliverables">
                {MEETING_DELIVERABLES.map((deliverable) => {
                  const status = resolveDeliverableState(activeMeetingProgress, deliverable);
                  const badge =
                    status === "done" ? "완료" : status === "active" ? "생성 중" : "대기";
                  return (
                    <article
                      key={deliverable.key}
                      className={`meeting-deliverable-card ${status}`}
                    >
                      <div>
                        <strong>{deliverable.label}</strong>
                        <p>{deliverable.detail}</p>
                      </div>
                      <span className={`meeting-deliverable-badge ${status}`}>{badge}</span>
                    </article>
                  );
                })}
              </section>
            </div>
          </div>

          <div className="meeting-layout">
            <div className="meeting-timeline">
              {activeMeetingStages.map((agent, index) => {
                const status =
                  index < meetingStageIndex
                    ? "done"
                    : index === meetingStageIndex
                      ? "active"
                      : "idle";
                const statusText =
                  status === "done" ? "완료" : status === "active" ? "진행 중" : "대기";
                return (
                  <article key={agent.title} className={`meeting-agent-card ${status}`}>
                    <div className="meeting-agent-top">
                      <div className="meeting-agent-index">{index + 1}</div>
                      <div>
                        <strong>{agent.title}</strong>
                        <p>{agent.detail}</p>
                      </div>
                    </div>
                    <span className={`meeting-agent-state ${status}`}>{statusText}</span>
                  </article>
                );
              })}
            </div>

            <div className="meeting-console">
              <div className="meeting-console-head">실시간 회의 로그</div>
              <div className="meeting-log-box">
                {meetingLogs.length === 0 ? (
                  <small style={{ color: "var(--muted)" }}>회의 로그를 준비 중입니다.</small>
                ) : (
                  meetingLogs.map((line, index) => (
                    <div key={`${line}_${index}`} className="meeting-log-line">
                      {line}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {miniGameOpen && (
            <div
              className="meeting-mini-modal-backdrop"
              onClick={() => setMiniGameOpen(false)}
              role="presentation"
            >
              <section
                className="meeting-mini-modal"
                role="dialog"
                aria-modal="true"
                aria-label="루미 별잡기 미니게임"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="meeting-mini-modal-head">
                  <div className="meeting-mini-game-head">
                    <strong>루미 별잡기</strong>
                    <span>{miniGameDifficultyLabel}</span>
                  </div>
                  <button
                    type="button"
                    className="meeting-mini-close"
                    onClick={() => setMiniGameOpen(false)}
                  >
                    닫기
                  </button>
                </div>
                <p className="meeting-mini-game-hint">{miniGameHint}</p>
                <div className="meeting-mini-game-grid">
                  {miniGameCells.map((cellIndex) => {
                    const active = cellIndex === miniGameTargetIndex;
                    return (
                      <button
                        key={cellIndex}
                        type="button"
                        className={`meeting-mini-cell ${active ? "active" : ""}`}
                        onClick={() => handleMiniGameTap(cellIndex)}
                        aria-label={active ? "루미 포착하기" : "빈 칸"}
                      >
                        {active ? (
                          <img src={LUMI_MASCOT_URL} alt="" aria-hidden="true" />
                        ) : (
                          <span className="meeting-mini-dot" />
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="meeting-mini-game-meta">
                  <span>점수 {miniGameScore}</span>
                  <span>연속 {miniGameStreak}</span>
                  <span>최고 {miniGameBestStreak}</span>
                  <span>라운드 {miniGameRounds}</span>
                  <span>
                    {miniGameAccuracy === null ? "정확도 -" : `정확도 ${miniGameAccuracy}%`}
                  </span>
                </div>
              </section>
            </div>
          )}
        </section>
      )}

      {error && (
        <section className="glass-panel" style={{ borderColor: "rgba(239, 68, 68, 0.35)" }}>
          <strong style={{ color: "#fda4af" }}>오류</strong>
          <p style={{ marginBottom: 0 }}>{error}</p>
        </section>
      )}

      {workspaceScene === "result" && launchPackage && (
        <section className="glass-panel">
          <div className="result-top-actions">
            <button
              type="button"
              className="btn-secondary-sm"
              onClick={() => setWorkspaceScene("chat")}
            >
              대화로 돌아가기
            </button>
          </div>
          <div style={{ marginTop: "14px", borderRadius: "20px", overflow: "hidden" }}>
            <LaunchResult launchPackage={launchPackage} />
          </div>
        </section>
      )}
    </main>
  );
}
