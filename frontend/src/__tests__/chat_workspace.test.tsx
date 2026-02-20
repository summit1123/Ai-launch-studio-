import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  streamJobStatus: vi.fn(),
  uploadProductImage: vi.fn(),
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
const getChatSession = vi.mocked(client.getChatSession);
const postChatMessage = vi.mocked(client.postChatMessage);
const streamChatMessage = vi.mocked(client.streamChatMessage);

describe("ChatWorkspace text flow", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();

    createChatSession.mockResolvedValue({
      session_id: "sess_test_1",
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

    getChatSession.mockResolvedValue({
      session_id: "sess_test_1",
      state: "CHAT_COLLECTING",
      mode: "standard",
      locale: "ko-KR",
      brief_slots: {
        ...blankSlots,
        product: {
          ...blankSlots.product,
          name: "테스트 세럼",
        },
      },
      gate: {
        ready: false,
        missing_required: ["product.category"],
        completeness: 0.125,
      },
      created_at: "2026-02-19T00:00:00Z",
      updated_at: "2026-02-19T00:00:01Z",
    });

    streamChatMessage.mockImplementation(
      async (
        _sessionId: string,
        _payload: { message: string },
        onEvent: (event: { type: string; data: unknown }) => void
      ) => {
        onEvent({
          type: "planner.delta",
          data: { text: "좋아요. 카테고리도 알려주세요." },
        });
        onEvent({
          type: "run.completed",
          data: {
            state: "CHAT_COLLECTING",
            gate: {
              ready: false,
              missing_required: ["product.category"],
              completeness: 0.125,
            },
          },
        });
      }
    );
  });

  it("세션 생성 후 스트림 응답을 메시지에 반영한다", async () => {
    render(<ChatWorkspace />);

    await screen.findByText("제품명(상품명)을 알려주세요.");

    const textarea = screen.getByPlaceholderText(
      "자유롭게 답변해 주세요. 한 문장으로 보내도 됩니다."
    );
    fireEvent.change(textarea, { target: { value: "제품명은 테스트 세럼입니다." } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 보내기" }));

    await waitFor(() => {
      expect(streamChatMessage).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(getChatSession).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("좋아요. 카테고리도 알려주세요.")).toBeTruthy();
    expect(screen.queryByText(/게이트 진행률:/)).toBeNull();
  });

  it("스트림 slot.updated를 즉시 반영하고 스냅샷 실패 시 재전송하지 않는다", async () => {
    getChatSession.mockRejectedValueOnce(new Error("snapshot sync failed"));
    streamChatMessage.mockImplementationOnce(
      async (
        _sessionId: string,
        _payload: { message: string },
        onEvent: (event: { type: string; data: unknown }) => void
      ) => {
        onEvent({
          type: "slot.updated",
          data: {
            slot_updates: [
              {
                path: "product.name",
                value: "즉시 반영 세럼",
                confidence: 0.94,
              },
            ],
          },
        });
        onEvent({
          type: "planner.delta",
          data: { text: "카테고리도 알려주세요." },
        });
        onEvent({
          type: "run.completed",
          data: {
            state: "CHAT_COLLECTING",
            gate: {
              ready: false,
              missing_required: ["product.category"],
              completeness: 0.125,
            },
          },
        });
      }
    );

    render(<ChatWorkspace />);
    await screen.findByText("제품명(상품명)을 알려주세요.");

    const textarea = screen.getByPlaceholderText(
      "자유롭게 답변해 주세요. 한 문장으로 보내도 됩니다."
    );
    fireEvent.change(textarea, { target: { value: "제품명은 즉시 반영 세럼입니다." } });
    fireEvent.click(screen.getByRole("button", { name: "메시지 보내기" }));

    await waitFor(() => {
      expect(streamChatMessage).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.getByText("제품명은 즉시 반영 세럼입니다.")).toBeTruthy();
    });
    expect(postChatMessage).not.toHaveBeenCalled();
  });
});
