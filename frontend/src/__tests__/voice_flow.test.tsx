import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import { ChatWorkspace } from "../pages/ChatWorkspace";

const blankSlots = {
  product: {
    name: null,
    category: null,
    features: [],
    price_band: null,
  },
  target: {
    who: null,
    why: null,
  },
  channel: {
    channels: [],
  },
  goal: {
    weekly_goal: null,
    video_seconds: null,
  },
};

vi.mock("../api/client", () => ({
  createChatSession: vi.fn(),
  getChatSession: vi.fn(),
  postChatMessage: vi.fn(),
  streamChatMessage: vi.fn(),
  streamVoiceTurn: vi.fn(),
  generateRunAssetsAsync: vi.fn(),
  generateRunAsync: vi.fn(),
  getJob: vi.fn(),
  getRunAssets: vi.fn(),
  generateRun: vi.fn(),
  getRun: vi.fn(),
  postVoiceTurn: vi.fn(),
  createAssistantVoice: vi.fn(),
}));

const createChatSession = vi.mocked(client.createChatSession);
const postVoiceTurn = vi.mocked(client.postVoiceTurn);
const streamVoiceTurn = vi.mocked(client.streamVoiceTurn);
const getChatSession = vi.mocked(client.getChatSession);

describe("ChatWorkspace voice flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    createChatSession.mockResolvedValue({
      session_id: "sess_voice_1",
      state: "CHAT_COLLECTING",
      mode: "standard",
      locale: "ko-KR",
      brief_slots: blankSlots,
      gate: {
        ready: false,
        missing_required: ["product.name"],
        completeness: 0.0,
      },
      assistant_message: "제품명(상품명)을 알려주세요.",
    });

    streamVoiceTurn.mockImplementation(
      async (
        _sessionId: string,
        _payload: unknown,
        onEvent: (event: { type: string; data: unknown }) => void
      ) => {
        onEvent({
          type: "voice.delta",
          data: { transcript: "제품명은 음성 세럼입니다.", state: "CHAT_COLLECTING" },
        });
        onEvent({
          type: "slot.updated",
          data: {
            slot_updates: [
              { path: "product.name", value: "음성 세럼", confidence: 0.9 },
            ],
          },
        });
        onEvent({
          type: "planner.delta",
          data: { text: "좋아요. 브리프 수집이 완료됐어요." },
        });
        onEvent({
          type: "gate.ready",
          data: { ready: true, missing_required: [], completeness: 1 },
        });
        onEvent({
          type: "stage.changed",
          data: { from: "CHAT_COLLECTING", to: "BRIEF_READY" },
        });
      }
    );

    getChatSession.mockResolvedValue({
      session_id: "sess_voice_1",
      state: "BRIEF_READY",
      mode: "standard",
      locale: "ko-KR",
      brief_slots: {
        product: {
          name: "음성 세럼",
          category: "스킨케어",
          features: ["저자극", "빠른흡수", "비건"],
          price_band: "mid",
        },
        target: { who: "20대 여성", why: "트러블 진정" },
        channel: { channels: ["Instagram"] },
        goal: { weekly_goal: "purchase", video_seconds: 10 },
      },
      gate: {
        ready: true,
        missing_required: [],
        completeness: 1.0,
      },
      created_at: "2026-02-19T00:00:00Z",
      updated_at: "2026-02-19T00:00:01Z",
    });
  });

  it("음성 파일 업로드 후 transcript와 다음 질문을 표시한다", async () => {
    const { container } = render(<ChatWorkspace />);
    await screen.findByText("제품명(상품명)을 알려주세요.");

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement | null;
    expect(fileInput).toBeTruthy();

    const file = new File(["voice"], "voice.wav", { type: "audio/wav" });
    fireEvent.change(fileInput as HTMLInputElement, {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(streamVoiceTurn).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("제품명은 음성 세럼입니다.")).toBeTruthy();
    expect(screen.getByText("좋아요. 브리프 수집이 완료됐어요.")).toBeTruthy();
    expect(screen.getByText("게이트 진행률: 100% · 준비 완료")).toBeTruthy();
    expect(postVoiceTurn).not.toHaveBeenCalled();
  });
});
