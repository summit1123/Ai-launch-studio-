import { render, screen } from "@testing-library/react";
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

describe("ChatWorkspace voice mode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createChatSession.mockResolvedValue({
      session_id: "sess_text_only_1",
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
  });

  it("MVP에서는 음성 모드 버튼을 노출하지 않는다", async () => {
    const { container } = render(<ChatWorkspace />);
    await screen.findByText("제품명(상품명)을 알려주세요.");

    expect(screen.queryByRole("button", { name: "음성 모드" })).toBeNull();
    expect(container.querySelector('input[type="file"][accept="audio/*"]')).toBeNull();
  });
});
