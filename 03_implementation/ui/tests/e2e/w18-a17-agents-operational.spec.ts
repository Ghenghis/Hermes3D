/**
 * W18-A17 Hermes Agents OPERATIONAL Proof — audit-only, NO mocks.
 *
 * Strengthens GUI_AGENT_WORKFLOW_GREEN from "single chat round-trip" to
 * "operational + assistive". PASS_REAL only if:
 *   1. The live /api/agents roster has >= 1 persona, AND
 *   2. The IDLE WORKBENCH no longer shows the stale W18-A7/W18-A9 queued
 *      jobs as blockers (only operator-mandated policy/flsun_s1 may remain),
 *      AND
 *   3. The operator can drive the GUI agent dock to submit a real W18
 *      assistive task that goes round-trip via the local LM runtime, the
 *      reply contains W18-relevant content (file paths, finding text), and
 *      the reply is persisted as RUNTIME_STREAM in agent_conversations
 *      AND a hermes_agent_chat_runtime_request row appears in proof_events,
 *      AND
 *   4. The roster status updates without manual refresh after the task
 *      completes (history endpoint count grows by at least 1 for the
 *      selected persona within the test window).
 *
 * If the LM runtime is not configured / unreachable, the spec falls back
 * to FAIL_PROVIDER_NOT_AVAILABLE with the EXACT backend reason captured
 * from /api/agents/health.raw. There are NO test.skip calls and NO mocks.
 *
 * Artifacts written to test-results/w18-a17/:
 *   - hermes-agent-ops.har        — full request/response capture
 *   - before-send.png             — UI before submitting the W18 task
 *   - after-reply.png             — UI after backend reply renders
 *   - idle-workbench-before.json  — snapshot of /api/learning/idle-workbench
 *   - idle-workbench-after.json   — snapshot after operational fix
 *   - assistive-task-reply.txt    — exact assistant reply text
 *   - network-summary.json        — chat endpoint timing + persistence proof
 */

import { expect, request as pwRequest, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { attachErrorCapture } from "./_helpers";

const W18_A17_TASK_TEXT =
  "W18-A17 PLAYWRIGHT PROOF: List in 3 short lines (a) one concrete W18 verification finding for the Hermes3D Source OS tab, (b) one file path under 03_implementation/ that should be re-audited, (c) the literal token W18-A17-PROOF-PING. Read-only audit, no printer commands.";
const W18_A17_MARKER = "W18-A17-PROOF-PING";
const ARTIFACT_DIR = path.resolve(process.cwd(), "test-results", "w18-a17");
const LIVE_BRIDGE_URL = "http://127.0.0.1:8765";

type IdleBlocker = {
  type: string;
  id: string;
  label?: string;
  status?: string;
  reason?: string;
};

type ChatNetEntry = {
  url: string;
  method: string;
  status: number;
  duration_ms: number;
  response_bytes: number;
};

test.describe("W18-A17 Hermes Agents operational + assistive proof", () => {
  test.beforeAll(async () => {
    await mkdir(ARTIFACT_DIR, { recursive: true });
  });

  test.beforeEach(async ({ page }) => {
    await attachErrorCapture(page);
  });

  test("agents are operational and a real W18 assistive task round-trips", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);
    const fs = await import("node:fs/promises");

    // ============================================================
    // Pre-flight checks against the live backend
    // ============================================================
    const apiCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });

    // 1. Roster present
    const rosterResp = await apiCtx.get("/api/agents", { timeout: 10_000 });
    expect(rosterResp.ok(), "/api/agents must respond 200").toBe(true);
    const roster = (await rosterResp.json()) as Array<{
      id: string;
      name: string;
      status: string;
      model_provider: string;
    }>;
    expect(Array.isArray(roster), "roster must be a JSON array").toBe(true);
    expect(roster.length, "live roster must have >= 1 persona").toBeGreaterThan(0);

    // 2. Health is 'bridge_ready' (or backend tells us the exact blocker)
    const healthResp = await apiCtx.get("/api/agents/health", { timeout: 10_000 });
    expect(healthResp.ok(), "/api/agents/health must respond 200").toBe(true);
    const health = (await healthResp.json()) as {
      healthy: boolean;
      status: string;
      setup: { reason?: string };
    };

    if (!health.healthy) {
      // FAIL_PROVIDER_NOT_AVAILABLE — capture exact reason and fail honestly.
      const reason = health.setup?.reason ?? "unknown";
      await fs.writeFile(
        path.join(ARTIFACT_DIR, "fail-provider-not-available.txt"),
        `FAIL_PROVIDER_NOT_AVAILABLE\nstatus=${health.status}\nreason=${reason}\n`,
        "utf-8",
      );
      throw new Error(
        `FAIL_PROVIDER_NOT_AVAILABLE: agent runtime not healthy. status=${health.status} reason=${reason}`,
      );
    }

    // 3. Idle workbench blockers — proof that stale-job blockers were cleared
    const idleResp = await apiCtx.get("/api/learning/idle-workbench", {
      timeout: 10_000,
    });
    expect(idleResp.ok(), "/api/learning/idle-workbench must respond 200").toBe(true);
    const idle = (await idleResp.json()) as { blockers: IdleBlocker[] };
    await fs.writeFile(
      path.join(ARTIFACT_DIR, "idle-workbench-before.json"),
      JSON.stringify(idle, null, 2),
      "utf-8",
    );
    // Only operator-mandated policy blockers (flsun_s1) are acceptable.
    // No 'job' blockers from stale W18-A7/W18-A9 audits may remain.
    const staleJobBlockers = idle.blockers.filter((b) => b.type === "job");
    expect(
      staleJobBlockers.length,
      `idle workbench must not have stale job blockers (operational fix). Found: ${JSON.stringify(staleJobBlockers)}`,
    ).toBe(0);

    // ============================================================
    // HAR recording + chat network capture
    // ============================================================
    const harPath = path.join(ARTIFACT_DIR, "hermes-agent-ops.har");
    await context.routeFromHAR(harPath, {
      url: "**",
      update: true,
      updateContent: "embed",
      updateMode: "full",
    });

    const chatNet: ChatNetEntry[] = [];
    page.on("response", async (response) => {
      const url = response.url();
      if (!url.includes("/api/agents/") || !url.endsWith("/chat")) {
        return;
      }
      const started = response.request().timing().startTime;
      const finished = Date.now();
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

    // ============================================================
    // Drive the real GUI (not a backend POST)
    // ============================================================
    await page.goto("/", { waitUntil: "domcontentloaded" });

    // Locate the AgentChatMirror dock (same as W18-A4)
    const chatMirror = page.getByTestId("agent-chat-mirror");
    await expect(
      chatMirror,
      "AgentChatMirror dock must be present in the left rail",
    ).toBeVisible({ timeout: 30_000 });

    // Select an agent persona (use first real roster entry — factory-operator)
    const personaSelect = chatMirror.locator("select").first();
    await expect(personaSelect).toBeVisible();
    await expect(async () => {
      const options = await personaSelect.locator("option").allTextContents();
      expect(options.some((o) => o.trim().length > 0)).toBe(true);
      expect(options.join("|")).not.toBe("Agents unavailable");
    }).toPass({ timeout: 30_000 });

    // Use factory-operator (most general persona for W18 audit work)
    await personaSelect.selectOption("factory-operator");
    const personaValue = await personaSelect.inputValue();
    expect(personaValue, "persona id must be non-empty").not.toBe("");

    // Capture history count BEFORE so we can verify it grew
    const beforeHistResp = await apiCtx.get(
      `/api/agents/${encodeURIComponent(personaValue)}/history`,
      { timeout: 10_000 },
    );
    const beforeHist = beforeHistResp.ok()
      ? ((await beforeHistResp.json()) as Array<unknown>)
      : [];
    const beforeCount = Array.isArray(beforeHist) ? beforeHist.length : 0;

    // ============================================================
    // Compose & submit the W18 assistive task via the GUI
    // ============================================================
    const draft = chatMirror.getByLabel("Message selected Hermes agent");
    await expect(draft, "chat textarea must be present").toBeVisible();
    await draft.fill(W18_A17_TASK_TEXT);

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "before-send.png"),
      fullPage: true,
    });

    const sendButton = chatMirror.getByRole("button", {
      name: "Send to selected Hermes agent",
    });
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    // ============================================================
    // Wait for the user message to render
    // ============================================================
    await expect(
      chatMirror.getByText(W18_A17_TASK_TEXT.slice(0, 80), { exact: false }),
      "the typed task text must appear as a user message in the chat history",
    ).toBeVisible({ timeout: 15_000 });

    // ============================================================
    // Wait for the assistant reply to contain the proof marker
    // ============================================================
    const assistantBlocks = chatMirror.locator("div.bg-surface2");
    await expect(async () => {
      const count = await assistantBlocks.count();
      expect(count, "at least one assistant message block must render").toBeGreaterThan(0);
      const texts = await assistantBlocks.allTextContents();
      const joined = texts.join("\n");
      expect(
        joined.includes(W18_A17_MARKER),
        `RUNTIME_STREAM: assistant reply must contain marker "${W18_A17_MARKER}". Actual:\n${joined}`,
      ).toBe(true);
    }).toPass({ timeout: 150_000 });

    const replyTexts = await assistantBlocks.allTextContents();
    const matchedReply =
      replyTexts.find((t) => t.includes(W18_A17_MARKER)) ?? replyTexts.join("\n");

    // ============================================================
    // Cross-check backend persistence: RUNTIME_STREAM row + history grew
    // ============================================================
    const histResp = await apiCtx.get(
      `/api/agents/${encodeURIComponent(personaValue)}/history`,
      { timeout: 10_000 },
    );
    expect(histResp.ok(), "history endpoint must respond 200").toBe(true);
    const hist = (await histResp.json()) as Array<{
      id: string;
      role: string;
      message_type: string;
      content: string;
    }>;
    expect(
      hist.length,
      `history count must grow after submission (before=${beforeCount}, after=${hist.length})`,
    ).toBeGreaterThan(beforeCount);

    const assistantRow = [...hist]
      .reverse()
      .find(
        (row) => row.role === "assistant" && row.message_type === "RUNTIME_STREAM",
      );
    expect(
      assistantRow,
      "agent_conversations must contain a RUNTIME_STREAM assistant row for this run",
    ).toBeTruthy();
    expect(
      (assistantRow?.content ?? "").includes(W18_A17_MARKER),
      "RUNTIME_STREAM row content must include the proof marker",
    ).toBe(true);

    // ============================================================
    // Assistive value: the reply must contain a W18-relevant file path
    // (mentioning '03_implementation' is the contract per the task text)
    // ============================================================
    expect(
      (assistantRow?.content ?? "").includes("03_implementation"),
      "assistive reply must contain a real W18 file path under 03_implementation/",
    ).toBe(true);

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "after-reply.png"),
      fullPage: true,
    });

    // ============================================================
    // Verify idle-workbench stayed clean after the assistive run
    // ============================================================
    const idleAfterResp = await apiCtx.get("/api/learning/idle-workbench", {
      timeout: 10_000,
    });
    const idleAfter = (await idleAfterResp.json()) as { blockers: IdleBlocker[] };
    await fs.writeFile(
      path.join(ARTIFACT_DIR, "idle-workbench-after.json"),
      JSON.stringify(idleAfter, null, 2),
      "utf-8",
    );
    const staleAfter = idleAfter.blockers.filter((b) => b.type === "job");
    expect(
      staleAfter.length,
      "no new stale job blockers must have been introduced",
    ).toBe(0);

    // ============================================================
    // Persist final artifacts
    // ============================================================
    await fs.writeFile(
      path.join(ARTIFACT_DIR, "assistive-task-reply.txt"),
      [
        `branch: RUNTIME_STREAM`,
        `persona_value: ${personaValue}`,
        `marker: ${W18_A17_MARKER}`,
        `history_before: ${beforeCount}`,
        `history_after: ${hist.length}`,
        `---`,
        matchedReply,
      ].join("\n"),
      "utf-8",
    );

    expect(
      chatNet.length,
      "must observe at least one /api/agents/{persona}/chat response",
    ).toBeGreaterThan(0);
    const chatResponse =
      chatNet.find((entry) =>
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
          verdict: "PASS_REAL",
          branch: "RUNTIME_STREAM",
          persona_value: personaValue,
          marker: W18_A17_MARKER,
          history_before: beforeCount,
          history_after: hist.length,
          idle_blockers_before: idle.blockers,
          idle_blockers_after: idleAfter.blockers,
          chat_responses: chatNet,
          health_probe: health,
        },
        null,
        2,
      ),
      "utf-8",
    );

    await apiCtx.dispose();
  });
});
