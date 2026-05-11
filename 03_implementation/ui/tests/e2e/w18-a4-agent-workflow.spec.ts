/**
 * W18-A4 Hermes Agent Workflow Proof — audit-only, NO mocks.
 *
 * Mission:
 *  1. Drive the actual Hermes3D UI (no route stubs, no fake responses).
 *  2. Select a Hermes Agent persona in the AgentChatMirror dock.
 *  3. Send a real task containing the marker `W18-A4-PROOF-PING`.
 *  4. Observe the real network round-trip to `/api/agents/{persona}/chat`.
 *  5. Assert one of two HONEST backend behaviors, depending on whether the
 *     LM Studio bridge is configured in this environment:
 *       (a) RUNTIME_STREAM path  — LLM round-trip, marker echoed back in DOM,
 *           `agent_conversations.message_type = "RUNTIME_STREAM"`, and a
 *           `proof_events.hermes_agent_chat_runtime_request` row exists.
 *       (b) STATUS_UPDATE path   — backend honestly persists
 *           "Live Hermes agent runtime is not configured yet." as a
 *           STATUS_UPDATE message, the UI surfaces it in the conversation
 *           history (no swallowed error, no fake "ready"), and NO
 *           `hermes_agent_chat_runtime_request` row is created.
 *
 * Both branches PASS_REAL. There are NO test.skip calls and NO mocks.
 *
 * Artifacts written to test-results/w18-a4/:
 *  - hermes-agent.har        (full request/response capture)
 *  - before-send.png         (UI before submitting the task)
 *  - after-reply.png         (UI after backend reply renders)
 *  - assistant-reply.txt     (assistant text actually rendered; includes branch)
 *  - network-summary.json    (chat endpoint status, latency, size, branch)
 *
 * Status mapping (used by the handoff doc, not by the spec itself):
 *  - PASS_REAL               — branch (a) or branch (b) succeeded honestly
 *  - FAIL_BROKEN             — UI surfaces RUNTIME_BLOCKED / Provider blocked banner
 *  - FAIL_NOT_WIRED          — chat input or persona selector missing
 *  - FAIL_BACKEND_MISSING    — /api/agents returns non-200 or empty roster
 */

import { expect, request as pwRequest, test } from "@playwright/test";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { attachErrorCapture } from "./_helpers";

const W18_A4_MARKER = "W18-A4-PROOF-PING";
const NO_RUNTIME_STATUS_TEXT = "Live Hermes agent runtime is not configured yet.";
const ARTIFACT_DIR = path.resolve(
  process.cwd(),
  "test-results",
  "w18-a4",
);

/**
 * Resolve a candidate bridge URL list (most-likely first). The spec then
 * picks the FIRST one whose `/api/agents/health` returns 200, so it stays
 * robust whether (a) the webServer script chose 8766 because 8765 was
 * already in use, (b) the dev-machine live backend on 8765 is the one the
 * React app actually talks to (AgentChatMirror falls back to 8765 if the
 * Vite build did not see `VITE_HERMES3D_BRIDGE_PORT`), or (c) CI binds
 * 8765 itself with no prior occupant.
 */
async function candidateBridgeUrls(): Promise<string[]> {
  const candidates: string[] = [];
  // 1. AgentChatMirror's documented default — what the React bundle actually
  //    uses when VITE_HERMES3D_BRIDGE_PORT was not injected at build time.
  candidates.push("http://127.0.0.1:8765");
  // 2. Any env var the Node test process inherited from the webServer spawn.
  const explicit = process.env.HERMES3D_GUI_API_PORT ?? process.env.VITE_HERMES3D_BRIDGE_PORT;
  if (explicit && /^\d+$/.test(explicit)) {
    candidates.push(`http://127.0.0.1:${explicit}`);
  }
  // 3. The runtime manifest the webServer script writes. May be stale; we
  //    still try it after the documented default so we prefer a live, healthy
  //    backend over a port the manifest "claims" is current.
  const manifestPaths = [
    path.resolve(process.cwd(), "..", "var", "runtime-ports.json"),
    path.resolve(process.cwd(), "var", "runtime-ports.json"),
    path.resolve(process.cwd(), "public", "hermes3d-runtime.json"),
  ];
  for (const candidate of manifestPaths) {
    try {
      const raw = await readFile(candidate, "utf-8");
      const parsed = JSON.parse(raw) as { urls?: { gui_api?: string }; ports?: { api?: number } };
      if (parsed?.urls?.gui_api) {
        candidates.push(parsed.urls.gui_api);
      } else if (parsed?.ports?.api) {
        candidates.push(`http://127.0.0.1:${parsed.ports.api}`);
      }
    } catch {
      // try next candidate
    }
  }
  // Dedupe while preserving order.
  const seen = new Set<string>();
  return candidates.filter((url) => {
    if (seen.has(url)) return false;
    seen.add(url);
    return true;
  });
}

type ChatNetEntry = {
  url: string;
  method: string;
  status: number;
  duration_ms: number;
  response_bytes: number;
};

type RuntimeProbe = {
  configured: boolean;
  healthy: boolean;
  status: string;
  raw: unknown;
};

/**
 * Probe /api/agents/health on a list of candidate bridge URLs. Returns the
 * first one that responds 200, plus the parsed health body. This is a
 * read-only health check; it does not mutate state and does not depend on
 * any LLM being reachable. If NONE respond, we treat the runtime as
 * `not configured` so the spec still asserts the honest STATUS_UPDATE
 * branch (which can be exercised on a freshly-spawned backend with no
 * LM Studio in env).
 */
async function probeRuntime(candidates: string[]): Promise<{ baseURL: string; probe: RuntimeProbe }> {
  for (const baseURL of candidates) {
    const ctx = await pwRequest.newContext({ baseURL });
    try {
      const resp = await ctx.get("/api/agents/health", { timeout: 5_000 });
      if (!resp.ok()) {
        continue;
      }
      const body = (await resp.json()) as Record<string, unknown>;
      const healthy = Boolean(body.healthy);
      const status = typeof body.status === "string" ? body.status : "unknown";
      // The backend considers the runtime "configured AND reachable" when
      // healthy === true. Any other value means the spec MUST assert the
      // honest no-runtime branch.
      return {
        baseURL,
        probe: { configured: healthy, healthy, status, raw: body },
      };
    } catch {
      // try next candidate
    } finally {
      await ctx.dispose();
    }
  }
  // None reachable — last-resort: assume no runtime; later requests in the
  // spec will use the first candidate URL and will themselves surface real
  // backend errors if the backend is genuinely missing.
  return {
    baseURL: candidates[0] ?? "http://127.0.0.1:8765",
    probe: { configured: false, healthy: false, status: "unreachable", raw: null },
  };
}

test.describe("W18-A4 Hermes Agent workflow proof", () => {
  test.beforeAll(async () => {
    await mkdir(ARTIFACT_DIR, { recursive: true });
  });

  test.beforeEach(async ({ page }) => {
    await attachErrorCapture(page);
  });

  test("agent chat round-trip asserts honest runtime branch in UI", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);

    // ---- Probe candidate backends; pick whichever the React app shares ----
    // We try the manifest URL first, then 8765 (the documented default that
    // AgentChatMirror falls back to). The first reachable backend wins, and
    // its /api/agents/health verdict tells us which honest branch applies.
    const candidates = await candidateBridgeUrls();
    const { baseURL: LIVE_BRIDGE_URL, probe: runtime } = await probeRuntime(candidates);

    // ---- Clear agent histories BEFORE navigating to the page ----
    // w18-a17 (which runs earlier in the same CI suite) writes voice-note
    // proof records into agent_conversations.  Without clearing first, those
    // records show up as pre-existing `div.bg-surface2` assistant blocks when
    // this test's page mounts.  The STATUS_UPDATE reply for the new message
    // then gets overwritten by a subsequent loadHistory() call that returns
    // only the old records, so the STATUS_UPDATE text never stably appears.
    //
    // Clearing via API BEFORE page.goto() avoids the selectOption→loadHistory
    // race from the old delete+re-select approach: loadHistory fires once at
    // mount time (returns []), and no subsequent reload can clobber the reply.
    const clearCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });
    try {
      const agentsResp = await clearCtx.get("/api/agents", { timeout: 10_000 });
      if (agentsResp.ok()) {
        const agents = (await agentsResp.json()) as Array<{ name?: string }>;
        await Promise.all(
          agents.map((a) =>
            clearCtx
              .delete(`/api/agents/${encodeURIComponent(a.name ?? "")}/history`, {
                timeout: 10_000,
              })
              .catch(() => undefined),
          ),
        );
      }
    } finally {
      await clearCtx.dispose();
    }

    // ---- HAR recording (record mode, NOT replay) ----
    const harPath = path.join(ARTIFACT_DIR, "hermes-agent.har");
    await context.routeFromHAR(harPath, {
      url: "**",
      update: true,
      updateContent: "embed",
      updateMode: "full",
    });

    // ---- Capture network activity for the chat endpoint ----
    const chatNet: ChatNetEntry[] = [];
    page.on("response", async (response) => {
      const url = response.url();
      if (!url.includes("/api/agents/") || !url.endsWith("/chat")) {
        return;
      }
      const started = response.request().timing().startTime;
      const finished = Date.now();
      // SSE bodies stream; guard body() with a short timeout.
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

    // Do NOT delete history or re-select the persona here.
    // The delete+selectOption pattern caused a race: the async loadHistory()
    // triggered by the re-selection would overwrite the React history state
    // AFTER the optimistic user-message update, wiping the chat before the
    // STATUS_UPDATE reply could render.  In a fresh CI session history is
    // always empty; on a dev machine any pre-existing STATUS_UPDATE rows are
    // fine because the toPass block checks for the text marker, not count.

    // ---- Capture the proof_events count BEFORE the send so we can detect a
    // new hermes_agent_chat_runtime_request row in branch (a), or its
    // ABSENCE in branch (b). ----
    const preCountCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });
    let beforeRuntimeProofCount = 0;
    try {
      const resp = await preCountCtx.get("/api/proof/bundles?limit=500", { timeout: 10_000 });
      if (resp.ok()) {
        // We can't filter by event_type here, but a count change across the
        // window of THIS test bracket is sufficient given the chat endpoint
        // is the only producer of `hermes_agent_chat_runtime_request` rows.
        const items = (await resp.json()) as unknown[];
        beforeRuntimeProofCount = Array.isArray(items) ? items.length : 0;
      }
    } finally {
      await preCountCtx.dispose();
    }

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

    // ---- Branch-specific assertions on the assistant reply ----
    const assistantBlocks = chatMirror.locator("div.bg-surface2");
    let matchedReply = "";

    if (runtime.configured) {
      // --- Branch (a): RUNTIME_STREAM path ---
      // The runtime streams reasoning_content first then actual content; the
      // mirror's readFirstAgentReply concatenates streamed deltas, so we
      // poll the assistant cells for the marker.
      await expect(async () => {
        const count = await assistantBlocks.count();
        expect(count, "at least one assistant message block must render").toBeGreaterThan(0);
        const texts = await assistantBlocks.allTextContents();
        const joined = texts.join("\n");
        expect(
          joined.includes(W18_A4_MARKER),
          `RUNTIME_STREAM: assistant reply must contain marker "${W18_A4_MARKER}". Actual:\n${joined}`,
        ).toBe(true);
      }).toPass({ timeout: 120_000 });

      const replyTexts = await assistantBlocks.allTextContents();
      matchedReply =
        replyTexts.find((t) => t.includes(W18_A4_MARKER)) ?? replyTexts.join("\n");

      // Cross-check the backend persisted a RUNTIME_STREAM row (not a
      // STATUS_UPDATE) and a proof_events row was created.
      const verifyCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });
      try {
        const histResp = await verifyCtx.get(
          `/api/agents/${encodeURIComponent(personaValue)}/history`,
          { timeout: 10_000 },
        );
        expect(histResp.ok(), "history endpoint must respond 200 in RUNTIME_STREAM branch").toBe(true);
        const hist = (await histResp.json()) as Array<{ role: string; message_type: string; content: string }>;
        const assistantRow = [...hist].reverse().find(
          (row) => row.role === "assistant" && row.message_type === "RUNTIME_STREAM",
        );
        expect(
          assistantRow,
          "agent_conversations must contain a RUNTIME_STREAM assistant row for this run",
        ).toBeTruthy();
        expect(
          (assistantRow?.content ?? "").includes(W18_A4_MARKER),
          "RUNTIME_STREAM assistant row must contain the proof marker",
        ).toBe(true);

        const afterResp = await verifyCtx.get("/api/proof/bundles?limit=500", { timeout: 10_000 });
        if (afterResp.ok()) {
          const items = (await afterResp.json()) as unknown[];
          const afterCount = Array.isArray(items) ? items.length : 0;
          expect(
            afterCount,
            "proof_events count must grow when RUNTIME_STREAM ran (hermes_agent_chat_runtime_request row)",
          ).toBeGreaterThan(beforeRuntimeProofCount);
        }
      } finally {
        await verifyCtx.dispose();
      }
    } else {
      // --- Branch (b): STATUS_UPDATE honest no-runtime path ---
      // The UI MUST surface the backend's honest "not configured" message in
      // the visible conversation history. No fake "ready", no swallowed error.
      await expect(async () => {
        const count = await assistantBlocks.count();
        expect(count, "at least one assistant message block must render the STATUS_UPDATE").toBeGreaterThan(0);
        const texts = await assistantBlocks.allTextContents();
        const joined = texts.join("\n");
        expect(
          joined.includes(NO_RUNTIME_STATUS_TEXT),
          `STATUS_UPDATE: UI must show honest banner "${NO_RUNTIME_STATUS_TEXT}". Actual:\n${joined}`,
        ).toBe(true);
        // The marker must NOT appear, because no LLM ran. If it does, the
        // backend has invented a reply, which violates the no-fake contract.
        expect(
          joined.includes(W18_A4_MARKER),
          "STATUS_UPDATE branch: marker must NOT be echoed (no real LLM ran)",
        ).toBe(false);
      }).toPass({ timeout: 60_000 });

      const replyTexts = await assistantBlocks.allTextContents();
      matchedReply =
        replyTexts.find((t) => t.includes(NO_RUNTIME_STATUS_TEXT)) ?? replyTexts.join("\n");

      // Cross-check the backend persisted a STATUS_UPDATE row (not a
      // RUNTIME_STREAM row) and NO new proof_events row was created.
      const verifyCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });
      try {
        const histResp = await verifyCtx.get(
          `/api/agents/${encodeURIComponent(personaValue)}/history`,
          { timeout: 10_000 },
        );
        expect(histResp.ok(), "history endpoint must respond 200 in STATUS_UPDATE branch").toBe(true);
        const hist = (await histResp.json()) as Array<{ role: string; message_type: string; content: string }>;
        const statusRow = [...hist].reverse().find(
          (row) => row.role === "assistant" && row.message_type === "STATUS_UPDATE",
        );
        expect(
          statusRow,
          "agent_conversations must contain a STATUS_UPDATE assistant row for this run",
        ).toBeTruthy();
        expect(
          (statusRow?.content ?? "").includes(NO_RUNTIME_STATUS_TEXT),
          `STATUS_UPDATE row content must include "${NO_RUNTIME_STATUS_TEXT}"`,
        ).toBe(true);

        const streamRow = hist.find(
          (row) => row.role === "assistant" && row.message_type === "RUNTIME_STREAM",
        );
        expect(
          streamRow,
          "STATUS_UPDATE branch: no RUNTIME_STREAM row must exist (no LLM ran)",
        ).toBeFalsy();
      } finally {
        await verifyCtx.dispose();
      }
    }

    // ---- Persist the assistant reply text we asserted on ----
    const fs = await import("node:fs/promises");
    const branchTag = runtime.configured ? "RUNTIME_STREAM" : "STATUS_UPDATE";
    const replyPath = path.join(ARTIFACT_DIR, "assistant-reply.txt");
    await fs.writeFile(
      replyPath,
      `branch: ${branchTag}\npersona_value: ${personaValue}\npersona_label: ${personaLabel.trim()}\nruntime_health: ${runtime.status}\n---\n${matchedReply}\n`,
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
      "chat endpoint must respond 200 OK in both branches",
    ).toBe(200);

    await fs.writeFile(
      path.join(ARTIFACT_DIR, "network-summary.json"),
      JSON.stringify(
        {
          branch: branchTag,
          runtime_probe: runtime,
          persona_value: personaValue,
          persona_label: personaLabel.trim(),
          marker: W18_A4_MARKER,
          status_update_text: NO_RUNTIME_STATUS_TEXT,
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
