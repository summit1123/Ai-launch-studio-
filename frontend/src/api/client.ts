import type {
  LaunchHistoryListResponse,
  LaunchRunRequest,
  LaunchRunResponse,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";

export async function runLaunch(
  payload: LaunchRunRequest,
  options?: { signal?: AbortSignal }
): Promise<LaunchRunResponse> {
  const response = await fetch(`${API_BASE_URL}/launch/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: options?.signal,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Launch API failed: ${response.status}`);
  }

  return (await response.json()) as LaunchRunResponse;
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
  const response = await fetch(`${API_BASE_URL}/launch/history?${params.toString()}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `History API failed: ${response.status}`);
  }
  return (await response.json()) as LaunchHistoryListResponse;
}

export async function getLaunchHistory(requestId: string): Promise<LaunchRunResponse> {
  const response = await fetch(`${API_BASE_URL}/launch/history/${requestId}`);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `History detail API failed: ${response.status}`);
  }
  return (await response.json()) as LaunchRunResponse;
}

export async function deleteLaunchHistory(requestId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/launch/history/${requestId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `History delete API failed: ${response.status}`);
  }
}
