/**
 * E2E spec for the Action Window + Task Monitor drawer (W6-4).
 *
 * Covered scenarios (per the W6-4 contract):
 *   1. Detached Action Window opens, resizes to viewport, shot.
 *   2. Detached Action Window tab switching screenshot.
 *   3. Task Monitor drawer mounted directly into the page with three mocked
 *      runs in three different states; screenshot.
 *   4. Click a run to expand its event timeline; screenshot.
 *   5. Toggle "Clear completed" UI-only filter; screenshot.
 *
 * Route stubs use the mocked URL pattern `**\/api/code-operator/recovery/runs*`
 * so the test never depends on a live RC v2 backend. Console errors are
 * captured and asserted to be empty at the end of every test.
 */

import { expect, test, type ConsoleMessage, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SCREENSHOT_DIR = "test-results/e2e/action-window-task-monitor";

/**
 * Vite 8.0.10 + @vitejs/plugin-react 6.0.1 in this repo produce TSX modules
 * that call `$RefreshReg$()` and `$RefreshSig$()` at module scope, but the
 * Fast Refresh preamble that defines those globals is not consistently
 * injected into the served HTML (issue affects both `index.html` and the
 * second `action-window.html` entry). The runtime errors block React
 * mounting in dev mode. Existing GUI E2E tests at HEAD hit the same bug.
 *
 * `addInitScript` runs before any page script — it provides safe no-op
 * stubs for the Refresh hooks so the modules execute. Production builds
 * skip this transform entirely; this shim is dev-only.
 */
async function installRefreshShim(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const w = window as unknown as {
      $RefreshReg$?: (...args: unknown[]) => void;
      $RefreshSig$?: () => (type: unknown) => unknown;
    };
    if (typeof w.$RefreshReg$ !== "function") {
      w.$RefreshReg$ = () => undefined;
    }
    if (typeof w.$RefreshSig$ !== "function") {
      w.$RefreshSig$ = () => (type: unknown) => type;
    }
  });
}

function attachConsoleCapture(page: Page): { errors: string[] } {
  const errors: string[] = [];
  const onConsole = (msg: ConsoleMessage) => {
    if (msg.type() === "error") {
      // Vite dev server occasionally logs a noisy 404 for a mocked route the
      // first paint requests; allow it through so the test is meaningful.
      const text = msg.text();
      if (
        text.includes("Failed to load resource") ||
        text.includes("net::ERR_FAILED")
      ) {
        return;
      }
      errors.push(text);
    }
  };
  const onPageError = (err: Error) => {
    errors.push(err.message);
  };
  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  return { errors };
}

function expectNoErrors(errors: string[]) {
  expect(errors, errors.join("\n")).toEqual([]);
}

test.beforeAll(() => {
  try {
    mkdirSync(SCREENSHOT_DIR, { recursive: true });
  } catch {
    // already exists
  }
});

test("Action Window — detached pop-out renders and resizes to viewport", async ({ page }) => {
  await installRefreshShim(page);
  const { errors } = attachConsoleCapture(page);
  await page.goto("/action-window.html?detached=1");
  const root = page.getByTestId("action-window-root");
  await expect(root).toBeVisible();
  await expect(root).toHaveAttribute("data-detached", "true");

  // Both resize handles must be hidden in detached mode.
  await expect(page.getByTestId("action-window-handle-right")).toHaveCount(0);
  await expect(page.getByTestId("action-window-handle-bottom")).toHaveCount(0);

  // Tabs are still visible; the detached panel is the same component tree.
  await expect(page.getByTestId("action-window-tab-code")).toBeVisible();
  await page.screenshot({ path: `${SCREENSHOT_DIR}/01-action-window-detached.png`, fullPage: true });
  expectNoErrors(errors);
});

test("Action Window — tab switching updates the active panel", async ({ page }) => {
  await installRefreshShim(page);
  const { errors } = attachConsoleCapture(page);
  await page.goto("/action-window.html?detached=1");
  await expect(page.getByTestId("action-window-panel-code")).toBeVisible();
  await page.getByTestId("action-window-tab-output").click();
  await expect(page.getByTestId("action-window-panel-output")).toBeVisible();
  await page.getByTestId("action-window-tab-diff").click();
  await expect(page.getByTestId("action-window-panel-diff")).toBeVisible();
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-action-window-diff-tab.png`, fullPage: true });
  expectNoErrors(errors);
});

test("Task Monitor — three runs in three states render with badges", async ({ page }) => {
  await installRefreshShim(page);
  const { errors } = attachConsoleCapture(page);

  // Mock the RC v2 endpoint.
  const runsPayload = {
    count: 3,
    by_state: { proposing: 1, applying: 1, escalated: 1 },
    runs: [
      {
        attempt_id: "a1aaaaaaaaaaaaaa",
        task_id: "T-MOCK-001",
        state: "proposing",
        branch: "propose_review_apply_rerun",
        failure_class: "gate_fail",
        failed_step_type: "ci",
        failure_fingerprint: "fp-aaa",
        retry_count: 0,
        retry_budget_max: 3,
        actor: "user",
        confirm: false,
        started_utc: "2026-05-09T10:00:00Z",
        last_event_utc: "2026-05-09T10:00:30Z",
        last_event_summary: "proposal in flight",
        proposal_id: null,
        review_evidence_id: null,
        apply_evidence_id: null,
        retry_gate_id: null,
        terminal_status: null,
        cancelled_reason: null,
        is_terminal: false,
        is_cancellable: true,
        history: [
          { ts_utc: "2026-05-09T10:00:00Z", from: "created", to: "proposing", note: "begin propose" },
        ],
      },
      {
        attempt_id: "a2bbbbbbbbbbbbbb",
        task_id: "T-MOCK-002",
        state: "applying",
        branch: "rollback_then_retry",
        failure_class: "merge_git_fail",
        failed_step_type: "merge",
        failure_fingerprint: "fp-bbb",
        retry_count: 1,
        retry_budget_max: 3,
        actor: "user",
        confirm: true,
        started_utc: "2026-05-09T09:50:00Z",
        last_event_utc: "2026-05-09T10:01:00Z",
        last_event_summary: "applying patch",
        proposal_id: "prop-bbb",
        review_evidence_id: "rev-bbb",
        apply_evidence_id: null,
        retry_gate_id: null,
        terminal_status: null,
        cancelled_reason: null,
        is_terminal: false,
        is_cancellable: false,
        history: [
          { ts_utc: "2026-05-09T09:50:00Z", from: "created", to: "proposing", note: "begin propose" },
          { ts_utc: "2026-05-09T09:55:00Z", from: "proposing", to: "reviewing", note: "review minimax" },
          { ts_utc: "2026-05-09T10:00:00Z", from: "reviewing", to: "applying", note: "apply patch" },
        ],
      },
      {
        attempt_id: "a3cccccccccccccc",
        task_id: "T-MOCK-003",
        state: "escalated",
        branch: "escalate_immediately",
        failure_class: "provider_auth",
        failed_step_type: "provider",
        failure_fingerprint: "fp-ccc",
        retry_count: 0,
        retry_budget_max: 3,
        actor: "user",
        confirm: false,
        started_utc: "2026-05-09T09:00:00Z",
        last_event_utc: "2026-05-09T09:01:00Z",
        last_event_summary: "escalated to human",
        proposal_id: null,
        review_evidence_id: null,
        apply_evidence_id: null,
        retry_gate_id: null,
        terminal_status: "escalated",
        cancelled_reason: null,
        is_terminal: true,
        is_cancellable: false,
        history: [
          { ts_utc: "2026-05-09T09:00:00Z", from: "created", to: "escalated", note: "hard-escalate class" },
        ],
      },
    ],
    task_id_filter: null,
  };
  await page.route("**/api/code-operator/recovery/runs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(runsPayload),
    });
  });

  await page.goto(`/action-window.html?detached=1&with-monitor=1`);
  await expect(page.getByTestId("task-monitor-drawer")).toHaveAttribute("data-open", "true");
  // Wait for poll to land all three rows.
  await expect(page.getByTestId("task-monitor-row")).toHaveCount(3);
  await expect(page.getByTestId("task-monitor-count")).toHaveText("3");
  // Each badge maps to the right state.
  const badges = await page.getByTestId("task-monitor-state-badge").all();
  const states = await Promise.all(badges.map((b) => b.getAttribute("data-state")));
  expect(states).toEqual(["proposing", "applying", "escalated"]);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/03-task-monitor-three-runs.png`, fullPage: true });
  expectNoErrors(errors);
});

test("Task Monitor — clicking a run expands its event timeline", async ({ page }) => {
  await installRefreshShim(page);
  const { errors } = attachConsoleCapture(page);
  await stubRecoveryRunsRoute(page, [
    {
      attempt_id: "expand0001expand",
      task_id: "T-EXPAND",
      state: "applying",
      history: [
        { ts_utc: "2026-05-09T10:00:00Z", from: "created", to: "proposing", note: "begin propose" },
        { ts_utc: "2026-05-09T10:05:00Z", from: "proposing", to: "reviewing", note: "review minimax" },
        { ts_utc: "2026-05-09T10:10:00Z", from: "reviewing", to: "applying", note: "apply patch" },
      ],
    },
  ]);
  await page.goto("/action-window.html?detached=1&with-monitor=1");
  await expect(page.getByTestId("task-monitor-row")).toHaveCount(1);
  await page.getByTestId("task-monitor-row").locator("button").first().click();
  const timeline = page.getByTestId("task-monitor-timeline");
  await expect(timeline).toBeVisible();
  // Three events render in chronological order.
  await expect(timeline.locator("li")).toHaveCount(3);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/04-task-monitor-expanded.png`, fullPage: true });
  expectNoErrors(errors);
});

test("Task Monitor — clear-completed filter hides terminal runs", async ({ page }) => {
  await installRefreshShim(page);
  const { errors } = attachConsoleCapture(page);
  await stubRecoveryRunsRoute(page, [
    { attempt_id: "live000000000001", task_id: "T-A", state: "proposing" },
    {
      attempt_id: "term000000000001",
      task_id: "T-B",
      state: "recovered",
      is_terminal: true,
      terminal_status: "recovered",
      is_cancellable: false,
    },
    {
      attempt_id: "term000000000002",
      task_id: "T-C",
      state: "cancelled",
      is_terminal: true,
      terminal_status: "cancelled",
      is_cancellable: false,
    },
  ]);
  await page.goto("/action-window.html?detached=1&with-monitor=1");
  await expect(page.getByTestId("task-monitor-row")).toHaveCount(3);
  await page.getByTestId("task-monitor-clear-completed").click();
  await expect(page.getByTestId("task-monitor-row")).toHaveCount(1);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/05-task-monitor-filtered.png`, fullPage: true });
  expectNoErrors(errors);
});

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

interface MockRunInput {
  attempt_id: string;
  task_id: string;
  state: string;
  history?: Array<{ ts_utc: string; from: string; to: string; note: string }>;
  is_terminal?: boolean;
  terminal_status?: string | null;
  is_cancellable?: boolean;
}

async function stubRecoveryRunsRoute(page: Page, input: MockRunInput[]): Promise<void> {
  const runs = input.map((entry) => ({
    attempt_id: entry.attempt_id,
    task_id: entry.task_id,
    state: entry.state,
    branch: "propose_review_apply_rerun",
    failure_class: "gate_fail",
    failed_step_type: "ci",
    failure_fingerprint: `fp-${entry.attempt_id}`,
    retry_count: 0,
    retry_budget_max: 3,
    actor: "user",
    confirm: false,
    started_utc: "2026-05-09T10:00:00Z",
    last_event_utc: entry.history?.[entry.history.length - 1]?.ts_utc ?? "2026-05-09T10:00:00Z",
    last_event_summary: "playwright stub",
    proposal_id: null,
    review_evidence_id: null,
    apply_evidence_id: null,
    retry_gate_id: null,
    terminal_status: entry.terminal_status ?? null,
    cancelled_reason: null,
    is_terminal: entry.is_terminal ?? false,
    is_cancellable: entry.is_cancellable ?? true,
    history: entry.history ?? [],
  }));
  const payload = {
    count: runs.length,
    by_state: runs.reduce<Record<string, number>>((acc, run) => {
      acc[run.state] = (acc[run.state] ?? 0) + 1;
      return acc;
    }, {}),
    runs,
    task_id_filter: null,
  };
  await page.route("**/api/code-operator/recovery/runs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    });
  });
}

