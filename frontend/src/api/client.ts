import type {
  AssistantVoiceRequest,
  AssistantVoiceResponse,
  ChatMessageRequest,
  ChatMessageResponse,
  ProductImageUploadResponse,
  ChatSessionCreateRequest,
  ChatSessionCreateResponse,
  ChatSessionGetResponse,
  JobGetResponse,
  JobListResponse,
  RunAssetsGenerateAsyncResponse,
  RunAssetsGetResponse,
  RunGenerateResponse,
  RunGenerateAsyncResponse,
  RunGetResponse,
  StreamEvent,
  StreamEventType,
  LaunchHistoryListResponse,
  LaunchRunRequest,
  LaunchRunResponse,
  VoiceTurnRequest,
  VoiceTurnResponse,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";

type RequestOptions = {
  signal?: AbortSignal;
};

type StreamOptions = {
  signal?: AbortSignal;
};

function resolveApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  const fallback = `API failed: ${response.status}`;
  const body = await response.text();
  if (!body.trim()) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(body) as {
      detail?: unknown;
      error?: { message?: string };
    };
    if (parsed.error?.message) {
      return parsed.error.message;
    }
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (parsed.detail !== undefined) {
      return JSON.stringify(parsed.detail);
    }
  } catch {
    // keep plain text fallback
  }

  return body || fallback;
}

async function requestJson<T>(
  path: string,
  init: RequestInit,
  errorPrefix: string
): Promise<T> {
  const response = await fetch(resolveApiUrl(path), init);
  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message || `${errorPrefix}: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function runLaunch(
  payload: LaunchRunRequest,
  options?: RequestOptions
): Promise<LaunchRunResponse> {
  return requestJson<LaunchRunResponse>(
    "/launch/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: options?.signal,
    },
    "Launch API failed"
  );
}

export async function listLaunchHistory(
  limit = 20,
  offset = 0,
  query = ""
): Promise<LaunchHistoryListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    q: query,
  });
  return requestJson<LaunchHistoryListResponse>(
    `/launch/history?${params.toString()}`,
    { method: "GET" },
    "History API failed"
  );
}

export async function getLaunchHistory(requestId: string): Promise<LaunchRunResponse> {
  return requestJson<LaunchRunResponse>(
    `/launch/history/${requestId}`,
    { method: "GET" },
    "History detail API failed"
  );
}

export async function deleteLaunchHistory(requestId: string): Promise<void> {
  const response = await fetch(resolveApiUrl(`/launch/history/${requestId}`), {
    method: "DELETE",
  });
  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message || `History delete API failed: ${response.status}`);
  }
}

export async function createChatSession(
  payload: ChatSessionCreateRequest = {}
): Promise<ChatSessionCreateResponse> {
  return requestJson<ChatSessionCreateResponse>(
    "/chat/session",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        locale: payload.locale ?? "ko-KR",
        mode: payload.mode ?? "standard",
      }),
    },
    "Create chat session API failed"
  );
}

export async function getChatSession(sessionId: string): Promise<ChatSessionGetResponse> {
  return requestJson<ChatSessionGetResponse>(
    `/chat/session/${sessionId}`,
    { method: "GET" },
    "Get chat session API failed"
  );
}

export async function postChatMessage(
  sessionId: string,
  payload: ChatMessageRequest,
  options?: RequestOptions
): Promise<ChatMessageResponse> {
  return requestJson<ChatMessageResponse>(
    `/chat/session/${sessionId}/message`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: options?.signal,
    },
    "Chat message API failed"
  );
}

function parseSseBlock(block: string): StreamEvent | null {
  if (!block.trim()) {
    return null;
  }

  let eventType = "message";
  const dataLines: string[] = [];
  for (const rawLine of block.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const rawData = dataLines.join("\n").trim();
  let data: unknown = rawData;
  try {
    data = JSON.parse(rawData);
  } catch {
    // keep text payload as-is
  }

  return {
    type: eventType as StreamEventType,
    data,
  };
}

async function streamPost(
  path: string,
  init: RequestInit,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(resolveApiUrl(path), init);
  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message || `Stream API failed: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Stream response body is missing");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    while (true) {
      const boundary = buffer.indexOf("\n\n");
      if (boundary < 0) {
        break;
      }
      const rawBlock = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const event = parseSseBlock(rawBlock);
      if (event) {
        onEvent(event);
      }
    }
  }

  buffer += decoder.decode().replace(/\r\n/g, "\n");
  const tailEvent = parseSseBlock(buffer);
  if (tailEvent) {
    onEvent(tailEvent);
  }
}

async function streamGet(
  path: string,
  onEvent: (event: StreamEvent) => void,
  options?: StreamOptions
): Promise<void> {
  // Cloudflare Tunnel may drop long-lived SSE connections.
  const MAX_RETRIES = 20;
  const RETRY_DELAY_MS = 1_000;
  const TERMINAL_TYPES = new Set<string>([
    "job.completed",
    "job.failed",
    "run.completed",
  ]);

  const sleep = (ms: number): Promise<void> =>
    new Promise((resolve) => {
      setTimeout(resolve, ms);
    });

  let lastStreamError: unknown = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
    if (options?.signal?.aborted) {
      return;
    }

    let response: Response;
    try {
      response = await fetch(resolveApiUrl(path), {
        method: "GET",
        headers: { Accept: "text/event-stream" },
        signal: options?.signal,
      });
    } catch (fetchError) {
      lastStreamError = fetchError;
      if (attempt < MAX_RETRIES && !options?.signal?.aborted) {
        await sleep(RETRY_DELAY_MS);
        continue;
      }
      throw fetchError;
    }

    if (!response.ok) {
      const message = await readErrorMessage(response);
      throw new Error(message || `Stream API failed: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("Stream response body is missing");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let terminalReached = false;
    let droppedMidstream = false;

    try {
      while (true) {
        let chunk: ReadableStreamReadResult<Uint8Array>;
        try {
          chunk = await reader.read();
        } catch (readError) {
          lastStreamError = readError;
          droppedMidstream = true;
          break;
        }

        const { value, done } = chunk;
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        while (true) {
          const boundary = buffer.indexOf("\n\n");
          if (boundary < 0) {
            break;
          }
          const rawBlock = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const event = parseSseBlock(rawBlock);
          if (!event) {
            continue;
          }
          onEvent(event);
          if (TERMINAL_TYPES.has(event.type)) {
            terminalReached = true;
            return;
          }
        }
      }
    } finally {
      reader.cancel().catch(() => {});
    }

    buffer += decoder.decode().replace(/\r\n/g, "\n");
    const tailEvent = parseSseBlock(buffer);
    if (tailEvent) {
      onEvent(tailEvent);
      if (TERMINAL_TYPES.has(tailEvent.type)) {
        return;
      }
    }

    if (terminalReached) {
      return;
    }

    if (attempt < MAX_RETRIES && !options?.signal?.aborted) {
      if (!droppedMidstream) {
        lastStreamError = new Error("SSE stream ended before terminal event");
      }
      await sleep(RETRY_DELAY_MS);
      continue;
    }

    if (lastStreamError instanceof Error) {
      throw lastStreamError;
    }
    throw new Error("SSE stream ended before terminal event");
  }
}

export async function streamChatMessage(
  sessionId: string,
  payload: ChatMessageRequest,
  onEvent: (event: StreamEvent) => void,
  options?: RequestOptions
): Promise<void> {
  return streamPost(
    `/chat/session/${sessionId}/message/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: options?.signal,
    },
    onEvent
  );
}

function buildVoiceTurnFormData(payload: VoiceTurnRequest): FormData {
  const formData = new FormData();
  const filename =
    payload.filename ?? (payload.audio instanceof File ? payload.audio.name : "voice.wav");

  formData.append("audio", payload.audio, filename);
  formData.append("locale", payload.locale ?? "ko-KR");
  formData.append("voice_preset", payload.voice_preset ?? "cute_ko");
  return formData;
}

function buildProductImageFormData(payload: {
  image: File;
  note?: string;
  locale?: string;
}): FormData {
  const formData = new FormData();
  formData.append("image", payload.image, payload.image.name || "product.png");
  formData.append("note", payload.note ?? "");
  formData.append("locale", payload.locale ?? "ko-KR");
  return formData;
}

export async function postVoiceTurn(
  sessionId: string,
  payload: VoiceTurnRequest,
  options?: RequestOptions
): Promise<VoiceTurnResponse> {
  return requestJson<VoiceTurnResponse>(
    `/chat/session/${sessionId}/voice-turn`,
    {
      method: "POST",
      body: buildVoiceTurnFormData(payload),
      signal: options?.signal,
    },
    "Voice turn API failed"
  );
}

export async function uploadProductImage(
  sessionId: string,
  payload: {
    image: File;
    note?: string;
    locale?: string;
  },
  options?: RequestOptions
): Promise<ProductImageUploadResponse> {
  return requestJson<ProductImageUploadResponse>(
    `/chat/session/${sessionId}/product-image`,
    {
      method: "POST",
      body: buildProductImageFormData(payload),
      signal: options?.signal,
    },
    "Product image upload API failed"
  );
}

export async function streamVoiceTurn(
  sessionId: string,
  payload: VoiceTurnRequest,
  onEvent: (event: StreamEvent) => void,
  options?: RequestOptions
): Promise<void> {
  return streamPost(
    `/chat/session/${sessionId}/voice-turn/stream`,
    {
      method: "POST",
      body: buildVoiceTurnFormData(payload),
      signal: options?.signal,
    },
    onEvent
  );
}

export async function createAssistantVoice(
  sessionId: string,
  payload: AssistantVoiceRequest,
  options?: RequestOptions
): Promise<AssistantVoiceResponse> {
  return requestJson<AssistantVoiceResponse>(
    `/chat/session/${sessionId}/assistant-voice`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: payload.text,
        voice_preset: payload.voice_preset ?? "cute_ko",
        format: payload.format ?? "mp3",
      }),
      signal: options?.signal,
    },
    "Assistant voice API failed"
  );
}

export async function generateRun(
  sessionId: string,
  options?: RequestOptions
): Promise<RunGenerateResponse> {
  return requestJson<RunGenerateResponse>(
    `/runs/${sessionId}/generate`,
    {
      method: "POST",
      signal: options?.signal,
    },
    "Run generate API failed"
  );
}

export async function generateRunAsync(
  sessionId: string,
  options?: RequestOptions
): Promise<RunGenerateAsyncResponse> {
  return requestJson<RunGenerateAsyncResponse>(
    `/runs/${sessionId}/generate/async`,
    {
      method: "POST",
      signal: options?.signal,
    },
    "Run async generate API failed"
  );
}

export async function getRun(runId: string): Promise<RunGetResponse> {
  return requestJson<RunGetResponse>(
    `/runs/${runId}`,
    { method: "GET" },
    "Run get API failed"
  );
}

export async function generateRunAssetsAsync(
  runId: string,
  options?: RequestOptions
): Promise<RunAssetsGenerateAsyncResponse> {
  return requestJson<RunAssetsGenerateAsyncResponse>(
    `/runs/${runId}/assets/generate/async`,
    {
      method: "POST",
      signal: options?.signal,
    },
    "Run assets async generate API failed"
  );
}

export async function getRunAssets(runId: string): Promise<RunAssetsGetResponse> {
  return requestJson<RunAssetsGetResponse>(
    `/runs/${runId}/assets`,
    { method: "GET" },
    "Run assets get API failed"
  );
}

export async function getJob(jobId: string): Promise<JobGetResponse> {
  return requestJson<JobGetResponse>(
    `/jobs/${jobId}`,
    { method: "GET" },
    "Job get API failed"
  );
}

export async function streamJobStatus(
  jobId: string,
  onEvent: (event: StreamEvent) => void,
  options?: {
    pollMs?: number;
    timeoutSeconds?: number;
    signal?: AbortSignal;
  }
): Promise<void> {
  const query = new URLSearchParams();
  if (options?.pollMs !== undefined) {
    query.set("poll_ms", String(options.pollMs));
  }
  if (options?.timeoutSeconds !== undefined) {
    query.set("timeout_seconds", String(options.timeoutSeconds));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return streamGet(`/jobs/${jobId}/stream${suffix}`, onEvent, {
    signal: options?.signal,
  });
}

export async function listJobs(params?: {
  runId?: string;
  sessionId?: string;
  limit?: number;
  offset?: number;
}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params?.runId) {
    query.set("run_id", params.runId);
  }
  if (params?.sessionId) {
    query.set("session_id", params.sessionId);
  }
  if (params?.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    query.set("offset", String(params.offset));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestJson<JobListResponse>(
    `/jobs${suffix}`,
    { method: "GET" },
    "Job list API failed"
  );
}
