/**
 * W18-A17 Hermes Agents OPERATIONAL Proof — audit-only, NO mocks.
 *
 * Strengthens GUI_AGENT_WORKFLOW_GREEN from "single chat round-trip" to
 * "operational + assistive". This spec is ENV-AWARE following the
 * W18-A4 PR #232 pattern (commit ca682b9):
 *
 *   (a) RUNTIME_STREAM branch — LM runtime reachable (CI with
 *       HERMES3D_AGENT_RUNTIME_URL set, or operator workstation with LM
 *       Studio running). Asserts the strengthened operational+assistive
 *       contract: roster present, no stale job blockers, real LLM
 *       round-trip, reply contains the marker AND a 03_implementation
 *       file path, persisted as RUNTIME_STREAM in agent_conversations,
 *       proof_events row hermes_agent_chat_runtime_request created,
 *       history grew.
 *
 *   (b) STATUS_UPDATE branch — LM runtime NOT reachable (typical CI
 *       runner without HERMES3D_AGENT_RUNTIME_URL). Asserts the honest
 *       backend behavior: roster present, no stale job blockers, the UI
 *       surfaces the literal banner
 *       "Live Hermes agent runtime is not configured yet.", persisted
 *       as STATUS_UPDATE in agent_conversations, NO RUNTIME_STREAM row
 *       exists for this run, NO proof_events.hermes_agent_chat_runtime_request
 *       row was created, and (because no LLM ran) the marker is NOT
 *       echoed AND no 03_implementation path requirement applies.
 *
 * Both branches MUST PASS_REAL. There are NO test.skip calls and NO
 * mocks. The choice between branches is driven by a real probe of
 * /api/agents/health on the live bridge — not by an env flag the test
 * sets itself.
 *
 * If /api/agents itself is missing or returns an empty roster, that is
 * FAIL_BACKEND_MISSING (a real bug, not an environment fact) and the
 * spec fails honestly.
 *
 * Artifacts written to test-results/w18-a17/:
 *   - hermes-agent-ops.har        — full request/response capture
 *   - before-send.png             — UI before submitting the W18 task
 *   - after-reply.png             — UI after backend reply renders
 *   - idle-workbench-before.json  — snapshot of /api/learning/idle-workbench
 *   - idle-workbench-after.json   — snapshot after operational fix
 *   - assistive-task-reply.txt    — exact assistant reply text + branch
 *   - network-summary.json        — chat endpoint timing + persistence proof + branch
 */

import { expect, request as pwRequest, test } from "@playwright/test";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { attachErrorCapture } from "./_helpers";

const W18_A17_TASK_TEXT =
  "W18-A17 PLAYWRIGHT PROOF: List in 3 short lines (a) one concrete W18 verification finding for the Hermes3D Source OS tab, (b) one file path under 03_implementation/ that should be re-audited, (c) the literal token W18-A17-PROOF-PING. Read-only audit, no printer commands.";
const W18_A17_MARKER = "W18-A17-PROOF-PING";
const NO_RUNTIME_STATUS_TEXT = "Live Hermes agent runtime is not configured yet.";
const ARTIFACT_DIR = path.resolve(process.cwd(), "test-results", "w18-a17");

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

type RuntimeProbe = {
  configured: boolean;
  healthy: boolean;
  status: string;
  reason: string;
  raw: unknown;
};

/**
 * Resolve a candidate bridge URL list (most-likely first). Mirrors the
 * W18-A4 spec so this spec works whether CI binds 127.0.0.1:8765 itself,
 * the operator dev box has the live FastAPI on 8765, or the webServer
 * spawn manifest writes a different port.
 */
async function candidateBridgeUrls(): Promise<string[]> {
  const candidates: string[] = [];
  // 1. AgentChatMirror's documented default — what the React bundle actually
  //    uses when VITE_HERMES3D_BRIDGE_PORT was not injected at build time.
  candidates.push("http://127.0.0.1:8765");
  // 2. Any env var the Node test process inherited from the webServer spawn.
  const explicit =
    process.env.HERMES3D_GUI_API_PORT ?? process.env.VITE_HERMES3D_BRIDGE_PORT;
  if (explicit && /^\d+$/.test(explicit)) {
    candidates.push(`http://127.0.0.1:${explicit}`);
  }
  // 3. The runtime manifest the webServer script writes.
  const manifestPaths = [
    path.resolve(process.cwd(), "..", "var", "runtime-ports.json"),
    path.resolve(process.cwd(), "var", "runtime-ports.json"),
    path.resolve(process.cwd(), "public", "hermes3d-runtime.json"),
  ];
  for (const candidate of manifestPaths) {
    try {
      const raw = await readFile(candidate, "utf-8");
      const parsed = JSON.parse(raw) as {
        urls?: { gui_api?: string };
        ports?: { api?: number };
      };
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

/**
 * Probe /api/agents/health on a list of candidate bridge URLs. Returns the
 * first one that responds 200, plus the parsed health body. This is a
 * read-only health check; it does not mutate state and does not depend on
 * any LLM being reachable.
 *
 * The runtime is considered "configured AND reachable" iff
 *   body.healthy === true AND body.setup.reason contains "responded HTTP 200".
 *
 * Any other value (healthy=false, or healthy=true with a different reason
 * such as "no runtime configured") means the spec MUST assert the honest
 * STATUS_UPDATE branch.
 */
async function probeRuntime(
  candidates: string[],
): Promise<{ baseURL: string; probe: RuntimeProbe }> {
  for (const baseURL of candidates) {
    const ctx = await pwRequest.newContext({ baseURL });
    try {
      const resp = await ctx.get("/api/agents/health", { timeout: 5_000 });
      if (!resp.ok()) {
        continue;
      }
      const body = (await resp.json()) as Record<string, unknown>;
      const healthy = Boolean(body.healthy);
      const status =
        typeof body.status === "string" ? body.status : "unknown";
      const setup =
        typeof body.setup === "object" && body.setup !== null
          ? (body.setup as Record<string, unknown>)
          : {};
      const reason =
        typeof setup.reason === "string" ? setup.reason : "unknown";
      const configured = healthy && reason.includes("responded HTTP 200");
      return {
        baseURL,
        probe: { configured, healthy, status, reason, raw: body },
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
    probe: {
      configured: false,
      healthy: false,
      status: "unreachable",
      reason: "no /api/agents/health responded 200 across candidates",
      raw: null,
    },
  };
}

test.describe("W18-A17 Hermes Agents operational + assistive proof", () => {
  test.beforeAll(async () => {
    await mkdir(ARTIFACT_DIR, { recursive: true });
  });

  test.beforeEach(async ({ page }) => {
    await attachErrorCapture(page);
  });

  test("agents are operational and a real W18 assistive task round-trips (env-aware)", async ({
    page,
    context,
  }) => {
    test.setTimeout(180_000);
    const fs = await import("node:fs/promises");

    // ============================================================
    // Probe candidate backends; pick whichever the React app shares
    // and decide which honest branch applies. NO env flag, NO mock.
    // ============================================================
    const candidates = await candidateBridgeUrls();
    const { baseURL: LIVE_BRIDGE_URL, probe: runtime } =
      await probeRuntime(candidates);

    const apiCtx = await pwRequest.newContext({ baseURL: LIVE_BRIDGE_URL });

    // ============================================================
    // Pre-flight checks against the live backend (both branches)
    // ============================================================

    // 1. Roster present — applies to both branches. If missing, that is a
    //    real backend bug (FAIL_BACKEND_MISSING), not an env fact.
    const rosterResp = await apiCtx.get("/api/agents", { timeout: 10_000 });
    expect(rosterResp.ok(), "/api/agents must respond 200").toBe(true);
    const roster = (await rosterResp.json()) as Array<{
      id: string;
      name: string;
      status: string;
      model_provider: string;
    }>;
    expect(Array.isArray(roster), "roster must be a JSON array").toBe(true);
    expect(
      roster.length,
      "live roster must have >= 1 persona",
    ).toBeGreaterThan(0);

    // 2. Idle workbench blockers — proof that stale-job blockers were cleared.
    //    This is the operational fix and applies to BOTH branches because the
    //    blocker-clear work is independent of the LLM runtime.
    const idleResp = await apiCtx.get("/api/learning/idle-workbench", {
      timeout: 10_000,
    });
    expect(
      idleResp.ok(),
      "/api/learning/idle-workbench must respond 200",
    ).toBe(true);
    const idle = (await idleResp.json()) as { blockers: IdleBlocker[] };
    await fs.writeFile(
      path.join(ARTIFACT_DIR, "idle-workbench-before.json"),
      JSON.stringify(idle, null, 2),
      "utf-8",
    );
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

    const chatMirror = page.getByTestId("agent-chat-mirror");
    await expect(
      chatMirror,
      "AgentChatMirror dock must be present in the left rail",
    ).toBeVisible({ timeout: 30_000 });

    const personaSelect = chatMirror.locator("select").first();
    await expect(personaSelect).toBeVisible();
    await expect(async () => {
      const options = await personaSelect.locator("option").allTextContents();
      expect(options.some((o) => o.trim().length > 0)).toBe(true);
      expect(options.join("|")).not.toBe("Agents unavailable");
    }).toPass({ timeout: 30_000 });

    // factory-operator is the most general persona for W18 audit work.
    // In CI it may or may not be in the roster; fall back to the first
    // available persona if missing so both branches stay deterministic.
    const personaOptions = await personaSelect
      .locator("option")
      .evaluateAll((els) =>
        els
          .map((el) => (el as HTMLOptionElement).value)
          .filter((v) => v && v.trim().length > 0),
      );
    const chosenPersona = personaOptions.includes("factory-operator")
      ? "factory-operator"
      : personaOptions[0];
    expect(
      chosenPersona,
      "at least one selectable persona id must be available",
    ).toBeTruthy();
    await personaSelect.selectOption(chosenPersona);
    const personaValue = await personaSelect.inputValue();
    expect(personaValue, "persona id must be non-empty").not.toBe("");

    // Capture history count BEFORE so we can verify it grew (RUNTIME_STREAM
    // branch) or that exactly one STATUS_UPDATE row was added (STATUS_UPDATE
    // branch).
    const beforeHistResp = await apiCtx.get(
      `/api/agents/${encodeURIComponent(personaValue)}/history`,
      { timeout: 10_000 },
    );
    const beforeHist = beforeHistResp.ok()
      ? ((await beforeHistResp.json()) as Array<unknown>)
      : [];
    const beforeCount = Array.isArray(beforeHist) ? beforeHist.length : 0;

    // Capture proof_events count BEFORE so we can verify in the
    // RUNTIME_STREAM branch that a hermes_agent_chat_runtime_request row
    // was added. /api/proof/bundles does not expose event_type, so this
    // count is used only as a coarse signal in the RUNTIME_STREAM branch
    // where the LLM round-trip dominates. For the STATUS_UPDATE branch
    // we rely on a kind-specific check (count of RUNTIME_STREAM rows in
    // this persona's history) which is 1:1 with the proof_events row
    // hermes_agent_chat_runtime_request — the backend only emits that
    // proof_event from _runtime_chat_stream, which is the same path that
    // inserts the RUNTIME_STREAM agent_conversations row.
    let beforeRuntimeProofCount = 0;
    {
      const resp = await apiCtx.get("/api/proof/bundles?limit=500", {
        timeout: 10_000,
      });
      if (resp.ok()) {
        const items = (await resp.json()) as unknown[];
        beforeRuntimeProofCount = Array.isArray(items) ? items.length : 0;
      }
    }

    // Kind-specific snapshot: count of RUNTIME_STREAM assistant rows for
    // THIS persona before chat. In STATUS_UPDATE branch (no LLM runtime),
    // this count MUST NOT grow. This is resilient to unrelated proof_events
    // (heartbeats, lock acquisitions, recovery events) growing in CI.
    let beforeRuntimeStreamRows = 0;
    {
      const resp = await apiCtx.get(
        `/api/agents/${encodeURIComponent(personaValue)}/history`,
        { timeout: 10_000 },
      );
      if (resp.ok()) {
        const rows = (await resp.json()) as Array<{
          role: string;
          message_type: string;
        }>;
        beforeRuntimeStreamRows = Array.isArray(rows)
          ? rows.filter(
              (row) =>
                row.role === "assistant" &&
                row.message_type === "RUNTIME_STREAM",
            ).length
          : 0;
      }
    }

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

    await expect(
      chatMirror.getByText(W18_A17_TASK_TEXT.slice(0, 80), { exact: false }),
      "the typed task text must appear as a user message in the chat history",
    ).toBeVisible({ timeout: 15_000 });

    // ============================================================
    // Branch-specific assertions on the assistant reply
    // ============================================================
    const assistantBlocks = chatMirror.locator("div.bg-surface2");
    const branchTag = runtime.configured ? "RUNTIME_STREAM" : "STATUS_UPDATE";
    let matchedReply = "";

    if (runtime.configured) {
      // --- Branch (a): RUNTIME_STREAM path ---
      // Real LLM runs. The reply MUST contain the proof marker AND a
      // 03_implementation path, persist as RUNTIME_STREAM in
      // agent_conversations, and create a proof_events row.
      await expect(async () => {
        const count = await assistantBlocks.count();
        expect(
          count,
          "at least one assistant message block must render",
        ).toBeGreaterThan(0);
        const texts = await assistantBlocks.allTextContents();
        const joined = texts.join("\n");
        expect(
          joined.includes(W18_A17_MARKER),
          `RUNTIME_STREAM: assistant reply must contain marker "${W18_A17_MARKER}". Actual:\n${joined}`,
        ).toBe(true);
      }).toPass({ timeout: 150_000 });

      const replyTexts = await assistantBlocks.allTextContents();
      matchedReply =
        replyTexts.find((t) => t.includes(W18_A17_MARKER)) ??
        replyTexts.join("\n");

      // Cross-check backend persistence: RUNTIME_STREAM row + history grew
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
        `RUNTIME_STREAM: history count must grow after submission (before=${beforeCount}, after=${hist.length})`,
      ).toBeGreaterThan(beforeCount);

      const assistantRow = [...hist]
        .reverse()
        .find(
          (row) =>
            row.role === "assistant" && row.message_type === "RUNTIME_STREAM",
        );
      expect(
        assistantRow,
        "agent_conversations must contain a RUNTIME_STREAM assistant row for this run",
      ).toBeTruthy();
      expect(
        (assistantRow?.content ?? "").includes(W18_A17_MARKER),
        "RUNTIME_STREAM row content must include the proof marker",
      ).toBe(true);

      // The assistive value contract: the LLM was instructed to include a
      // 03_implementation path. This requirement applies ONLY when an LLM
      // actually ran (RUNTIME_STREAM branch), not to the honest no-runtime
      // STATUS_UPDATE banner.
      expect(
        (assistantRow?.content ?? "").includes("03_implementation"),
        "RUNTIME_STREAM: assistive reply must contain a real W18 file path under 03_implementation/",
      ).toBe(true);

      // Verify proof_events grew (hermes_agent_chat_runtime_request row).
      const afterProof = await apiCtx.get("/api/proof/bundles?limit=500", {
        timeout: 10_000,
      });
      if (afterProof.ok()) {
        const items = (await afterProof.json()) as unknown[];
        const afterCount = Array.isArray(items) ? items.length : 0;
        expect(
          afterCount,
          "RUNTIME_STREAM: proof_events count must grow when LLM ran (hermes_agent_chat_runtime_request row)",
        ).toBeGreaterThan(beforeRuntimeProofCount);
      }
    } else {
      // --- Branch (b): STATUS_UPDATE honest no-runtime path ---
      // The UI MUST surface the backend's honest "not configured" banner.
      // No fake "ready", no swallowed error. NO marker echoed (no LLM ran).
      // NO 03_implementation path requirement (no LLM, no path to invent).
      // NO new hermes_agent_chat_runtime_request proof_events row.
      await expect(async () => {
        const count = await assistantBlocks.count();
        expect(
          count,
          "at least one assistant message block must render the STATUS_UPDATE",
        ).toBeGreaterThan(0);
        const texts = await assistantBlocks.allTextContents();
        const joined = texts.join("\n");
        expect(
          joined.includes(NO_RUNTIME_STATUS_TEXT),
          `STATUS_UPDATE: UI must show honest banner "${NO_RUNTIME_STATUS_TEXT}". Actual:\n${joined}`,
        ).toBe(true);
        expect(
          joined.includes(W18_A17_MARKER),
          "STATUS_UPDATE: marker must NOT be echoed (no real LLM ran). Backend must not fabricate a reply.",
        ).toBe(false);
      }).toPass({ timeout: 60_000 });

      const replyTexts = await assistantBlocks.allTextContents();
      matchedReply =
        replyTexts.find((t) => t.includes(NO_RUNTIME_STATUS_TEXT)) ??
        replyTexts.join("\n");

      // Cross-check backend persisted a STATUS_UPDATE row (not RUNTIME_STREAM).
      const histResp = await apiCtx.get(
        `/api/agents/${encodeURIComponent(personaValue)}/history`,
        { timeout: 10_000 },
      );
      expect(
        histResp.ok(),
        "history endpoint must respond 200 in STATUS_UPDATE branch",
      ).toBe(true);
      const hist = (await histResp.json()) as Array<{
        id: string;
        role: string;
        message_type: string;
        content: string;
      }>;
      expect(
        hist.length,
        `STATUS_UPDATE: history count must grow after submission (before=${beforeCount}, after=${hist.length})`,
      ).toBeGreaterThan(beforeCount);

      const statusRow = [...hist]
        .reverse()
        .find(
          (row) =>
            row.role === "assistant" && row.message_type === "STATUS_UPDATE",
        );
      expect(
        statusRow,
        "STATUS_UPDATE: agent_conversations must contain a STATUS_UPDATE assistant row for this run",
      ).toBeTruthy();
      expect(
        (statusRow?.content ?? "").includes(NO_RUNTIME_STATUS_TEXT),
        `STATUS_UPDATE: row content must include "${NO_RUNTIME_STATUS_TEXT}"`,
      ).toBe(true);

      // No RUNTIME_STREAM row may exist among the NEW rows (rows added by
      // this run). We can't safely require zero RUNTIME_STREAM rows across
      // all history because the persona is shared with prior test runs;
      // but the LAST assistant row for this run must be STATUS_UPDATE.
      const lastAssistant = [...hist]
        .reverse()
        .find((row) => row.role === "assistant");
      expect(
        lastAssistant?.message_type,
        "STATUS_UPDATE: most recent assistant row must be STATUS_UPDATE (no LLM ran)",
      ).toBe("STATUS_UPDATE");

      // Kind-specific check: no NEW RUNTIME_STREAM assistant row for this
      // persona must have been inserted by this run. This is the spec
      // equivalent of "no proof_events row with kind=hermes_agent_chat_runtime_request
      // was created" because the backend only emits that proof_event from
      // the same _runtime_chat_stream code path that writes the
      // RUNTIME_STREAM agent_conversations row. The total proof_events
      // count is intentionally NOT checked here — unrelated proof kinds
      // (heartbeats, lock acquisitions, recovery controller events) may
      // legitimately grow during the run and must not fail this branch.
      const afterRuntimeStreamRows = hist.filter(
        (row) =>
          row.role === "assistant" && row.message_type === "RUNTIME_STREAM",
      ).length;
      expect(
        afterRuntimeStreamRows - beforeRuntimeStreamRows,
        `STATUS_UPDATE: zero NEW RUNTIME_STREAM rows must exist for this persona (no LLM ran). before=${beforeRuntimeStreamRows} after=${afterRuntimeStreamRows} — equivalent to delta==0 for proof_events kind="hermes_agent_chat_runtime_request"`,
      ).toBe(0);
    }

    await page.screenshot({
      path: path.join(ARTIFACT_DIR, "after-reply.png"),
      fullPage: true,
    });

    // ============================================================
    // Verify idle-workbench stayed clean after the assistive run
    // (operational invariant — applies to BOTH branches)
    // ============================================================
    const idleAfterResp = await apiCtx.get("/api/learning/idle-workbench", {
      timeout: 10_000,
    });
    const idleAfter = (await idleAfterResp.json()) as {
      blockers: IdleBlocker[];
    };
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
    const histFinalResp = await apiCtx.get(
      `/api/agents/${encodeURIComponent(personaValue)}/history`,
      { timeout: 10_000 },
    );
    const histFinal = histFinalResp.ok()
      ? ((await histFinalResp.json()) as Array<unknown>)
      : [];
    const histFinalCount = Array.isArray(histFinal) ? histFinal.length : 0;

    await fs.writeFile(
      path.join(ARTIFACT_DIR, "assistive-task-reply.txt"),
      [
        `branch: ${branchTag}`,
        `runtime_healthy: ${runtime.healthy}`,
        `runtime_status: ${runtime.status}`,
        `runtime_reason: ${runtime.reason}`,
        `persona_value: ${personaValue}`,
        `marker: ${W18_A17_MARKER}`,
        `history_before: ${beforeCount}`,
        `history_after: ${histFinalCount}`,
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
      "chat endpoint must respond 200 OK in both branches",
    ).toBe(200);

    await fs.writeFile(
      path.join(ARTIFACT_DIR, "network-summary.json"),
      JSON.stringify(
        {
          verdict: "PASS_REAL",
          branch: branchTag,
          runtime_probe: runtime,
          persona_value: personaValue,
          marker: W18_A17_MARKER,
          status_update_text: NO_RUNTIME_STATUS_TEXT,
          history_before: beforeCount,
          history_after: histFinalCount,
          idle_blockers_before: idle.blockers,
          idle_blockers_after: idleAfter.blockers,
          chat_responses: chatNet,
        },
        null,
        2,
      ),
      "utf-8",
    );

    await apiCtx.dispose();
  });
});
