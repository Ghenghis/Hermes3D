/**
 * W18-A4 Hermes Agent Workflow Proof — audit-only, NO mocks.
 *
 * Mission:
 *  1. Drive the actual Hermes3D UI (no route stubs, no fake responses).
 *  2. Select a Hermes Agent persona in the AgentChatMirror dock.
 *  3. Send a real task containing the marker `W18-A4-PROOF-PING`.
 *  4. Observe the real SSE round-trip to `/api/agents/{persona}/chat`.
 *  5. Assert the marker is echoed back in the visible chat history.
 *
 * Artifacts written to test-results/w18-a4/:
 *  - hermes-agent.har        (full request/response capture)
 *  - before-send.png         (UI before submitting the task)
 *  - after-reply.png         (UI after assistant message renders)
 *  - assistant-reply.txt     (the assistant text actually rendered)
 *  - network-summary.json    (chat endpoint status, latency, size)
 *
 * Status mapping (used by the handoff doc, not by the spec itself):
 *  - PASS_REAL          — assistant message in DOM contains the marker
 *  - FAIL_BROKEN        — UI surfaces RUNTIME_BLOCKED / Provider blocked banner
 *  - FAIL_NOT_WIRED     — chat input or persona selector missing
 *  - FAIL_BACKEND_MISSING — /api/agents returns non-200 or empty roster
 */

import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { attachErrorCapture } from "./_helpers";

const W18_A4_MARKER = "W18-A4-PROOF-PING";
const ARTIFACT_DIR = path.resolve(
  process.cwd(),
  "test-results",
  "w18-a4",
);

test.describe("W18-A4 Hermes Agent workflow proof", () => {
  test.beforeAll(async () => {
    await mkdir(ARTIFACT_DIR, { recursive: true });
  });

  test.beforeEach(async ({ page }) => {
    await attachErrorCapture(page);
  });

  test("real persona chat round-trip echoes proof marker in UI", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);

    // ---- HAR recording (record mode, NOT replay) ----
    const harPath = path.join(ARTIFACT_DIR, "hermes-agent.har");
    await context.routeFromHAR(harPath, {
      url: "**",
      update: true,
      updateContent: "embed",
      updateMode: "full",
    });

    // ---- Capture network activity for the chat endpoint ----
    type ChatNetEntry = {
      url: string;
      method: string;
      status: number;
      duration_ms: number;
      response_bytes: number;
    };
    const chatNet: ChatNetEntry[] = [];
    page.on("response", async (response) => {
      const url = response.url();
      if (!url.includes("/api/agents/") || !url.endsWith("/chat")) {
        return;
      }
      const started = response.request().timing().startTime;
      const finished = Date.now();
      // SSE response bodies are streamed; reading body() can hang on
      // never-closing streams, so guard it.
      let body = Buffer.alloc(0);
      try {
        body = await Promise.race([
          response.body(),
          new Promise<Buffer>((resolve) =>
            setTimeout(() => resolve(Buffer.alloc(0)), 1_000),
          ),
        ]);
      } catch {
        body = Buffer.alloc(0);
      }
      chatNet.push({
        url,
        method: response.request().method(),
        status: response.status(),
        duration_ms: Math.max(0, finished - started),
        response_bytes: body.byteLength,
      });
    });

    // ---- Mount the app ----
    await page.goto("/", { waitUntil: "domcontentloaded" });

    // ---- Locate the AgentChatMirror dock ----
    const chatMirror = page.getByTestId("agent-chat-mirror");
    await expect(
      chatMirror,
      "AgentChatMirror dock must be present in the left rail",
    ).toBeVisible({ timeout: 30_000 });

    // ---- Select a Hermes Agent persona ----
    const personaSelect = chatMirror.locator("select").first();
    await expect(
      personaSelect,
      "persona selector must be present (FAIL_NOT_WIRED if missing)",
    ).toBeVisible();

    // Wait for the live /api/agents roster to populate the select.
    await expect(async () => {
      const options = await personaSelect.locator("option").allTextContents();
      // The placeholder option `Agents unavailable` means the backend
      // returned an empty roster, which is FAIL_BACKEND_MISSING.
      expect(options.some((o) => o.trim().length > 0)).toBe(true);
      expect(options.join("|")).not.toBe("Agents unavailable");
    }).toPass({ timeout: 30_000 });

    // Pick the first real persona, capture its visible label.
    const personaValue = await personaSelect.inputValue();
    const personaLabel = (await personaSelect
      .locator(`option[value="${personaValue}"]`)
      .textContent()) ?? personaValue;
    expect(personaValue, "persona id must be non-empty").not.toBe("");

    // ---- Compose and submit the proof task ----
    const draft = chatMirror.getByLabel("Message selected Hermes agent");
    await expect(
      draft,
      "chat textarea must be present (FAIL_NOT_WIRED if missing)",
    ).toBeVisible();
    const taskText = `Echo back the string '${W18_A4_MARKER}' verbatim and then stop.`;
    await draft.fill(taskText);

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "before-send.png"),
      fullPage: true,
    });

    const sendButton = chatMirror.getByRole("button", {
      name: "Send to selected Hermes agent",
    });
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    // ---- Wait for the user message to appear in history ----
    await expect(
      chatMirror.getByText(taskText, { exact: false }),
      "the typed task text must appear as a user message in the chat history",
    ).toBeVisible({ timeout: 15_000 });

    // ---- Wait for an assistant reply that contains the marker ----
    // The runtime streams reasoning_content first then actual content; the
    // mirror's readFirstAgentReply concatenates streamed deltas, so we
    // poll the assistant cells for the marker.
    const assistantBlocks = chatMirror.locator("div.bg-surface2");
    await expect(async () => {
      const count = await assistantBlocks.count();
      expect(count, "at least one assistant message block must render").toBeGreaterThan(0);
      const texts = await assistantBlocks.allTextContents();
      const joined = texts.join("\n");
      expect(
        joined.includes(W18_A4_MARKER),
        `assistant reply must contain marker "${W18_A4_MARKER}". Actual:\n${joined}`,
      ).toBe(true);
    }).toPass({ timeout: 120_000 });

    // ---- Capture the assistant reply text we asserted on ----
    const replyTexts = await assistantBlocks.allTextContents();
    const matchedReply =
      replyTexts.find((t) => t.includes(W18_A4_MARKER)) ?? replyTexts.join("\n");
    const replyPath = path.join(ARTIFACT_DIR, "assistant-reply.txt");
    await page.context().request.fetch("data:text/plain,").catch(() => {});
    const fs = await import("node:fs/promises");
    await fs.writeFile(
      replyPath,
      `persona_value: ${personaValue}\npersona_label: ${personaLabel.trim()}\n---\n${matchedReply}\n`,
      "utf-8",
    );

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "after-reply.png"),
      fullPage: true,
    });

    // ---- Network summary: prove a real /chat response was observed ----
    expect(
      chatNet.length,
      "must observe at least one /api/agents/{persona}/chat response",
    ).toBeGreaterThan(0);
    const chatResponse = chatNet.find((entry) =>
      entry.url.endsWith(`/api/agents/${personaValue}/chat`),
    ) ?? chatNet[0];
    expect(
      chatResponse.status,
      "chat endpoint must respond 200 OK",
    ).toBe(200);

    await fs.writeFile(
      path.join(ARTIFACT_DIR, "network-summary.json"),
      JSON.stringify(
        {
          persona_value: personaValue,
          persona_label: personaLabel.trim(),
          marker: W18_A4_MARKER,
          chat_responses: chatNet,
        },
        null,
        2,
      ),
      "utf-8",
    );

    // ---- HAR is finalized in afterEach by closing the context ----
  });
});
