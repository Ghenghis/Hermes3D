import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentChatMirror } from "../../src/components/agents/AgentChatMirror";

vi.mock("../../src/api/adapters", () => ({
  adapters: {
    getAgents: vi.fn(async () => [
      {
        id: "print-safety-agent",
        role: "Print Safety Agent",
        status: "paused",
        model_provider: "not_configured",
      },
    ]),
    getVoiceAgents: vi.fn(async () => []),
    previewVoice: vi.fn(),
    uploadAgentAttachment: vi.fn(),
  },
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function streamReply(body: unknown): Response {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(body)}\n\n`));
        controller.close();
      },
    }),
    {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    },
  );
}

describe("AgentChatMirror", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("keeps an in-flight assistant reply when an older history load resolves later", async () => {
    let resolveInitialHistory: ((response: Response) => void) | null = null;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/agents/print-safety-agent/history") && method === "GET") {
        return new Promise<Response>((resolve) => {
          resolveInitialHistory = resolve;
        });
      }
      if (url.endsWith("/api/agents/print-safety-agent/chat") && method === "POST") {
        return streamReply({
          id: "reply-1",
          persona_id: "print-safety-agent",
          role: "assistant",
          message_type: "STATUS_UPDATE",
          content: "Message received. Live Hermes agent runtime is not configured yet.",
          action_id: null,
          created_at: new Date().toISOString(),
        });
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AgentChatMirror />);

    const draft = await screen.findByLabelText("Message selected Hermes agent");
    fireEvent.change(draft, { target: { value: "prove the chat path" } });
    fireEvent.click(screen.getByRole("button", { name: "Send to selected Hermes agent" }));

    expect(await screen.findByText(/Live Hermes agent runtime is not configured yet/)).toBeVisible();

    resolveInitialHistory?.(jsonResponse([]));

    await waitFor(() => {
      expect(screen.getByText(/Live Hermes agent runtime is not configured yet/)).toBeVisible();
    });
  });
});
