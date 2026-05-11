/**
 * W18-A25 — Playwright e2e proof for the urgent #agents tab fix-it.
 *
 * The brief required:
 *   - Navigate to #agents.
 *   - Assert the new "Active Tasks" panel renders ≥1 task when the
 *     backend provides one (we stub the call so the test is deterministic
 *     regardless of operator-local proof_events state).
 *   - Assert the task shows provider_id (`minimax` or `deepseek`).
 *   - Screenshot.
 *   - Env-aware: when the backend honestly returns zero tasks, assert
 *     the panel renders the explicit "No recent tasks" message rather
 *     than a fake row.
 *
 * Operator freeze: no printer-control writes. The stubbed backend
 * returns only the agents-tasks / action-catalog payloads needed for
 * the panel; no /api/printers/* call is touched.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { attachErrorCapture, fulfillJson, readErrors } from "./_helpers";

const STUB_AGENT_TASKS_WITH_MINIMAX = {
  schema_version: "agent-tasks-v1",
  tasks: [
    {
      task_id: "H3D-W18A25-MM-1",
      team_id: "minimax-builders",
      provider_id: "minimax",
      title: "MiniMax demo coding pass",
      kind: "code_team",
      action_id: "code.teams.assign_task",
      status: "assigned",
      event_type: "hermes_agent.action.executed",
      created_utc: "2026-05-11 14:00:00",
      evidence_id: "ev_w18a25_minimax_stub",
      source_agent: "hermes-agent",
    },
    {
      task_id: "H3D-W18A25-DS-1",
      team_id: "deepseek-reviewers",
      provider_id: "deepseek",
      title: "DeepSeek review pass",
      kind: "code_team",
      action_id: "code.teams.run_review_pass",
      status: "review_recorded",
      event_type: "hermes_agent.action.executed",
      created_utc: "2026-05-11 13:55:00",
      evidence_id: "ev_w18a25_deepseek_stub",
      source_agent: "hermes-agent",
    },
  ],
  active_count: 2,
  total_count: 2,
  limit: 50,
  window_days: 7,
  provider_smoke_latest: [
    {
      provider_id: "minimax",
      status: "ready",
      task_id: "H3D-W18A25-SMOKE-MM",
      created_utc: "2026-05-11 13:30:00",
      evidence_id: "ev_w18a25_smoke_minimax",
    },
    {
      provider_id: "deepseek",
      status: "ready",
      task_id: "H3D-W18A25-SMOKE-DS",
      created_utc: "2026-05-11 13:32:00",
      evidence_id: "ev_w18a25_smoke_deepseek",
    },
  ],
};

const STUB_AGENT_TASKS_EMPTY = {
  schema_version: "agent-tasks-v1",
  tasks: [],
  active_count: 0,
  total_count: 0,
  limit: 50,
  window_days: 7,
  provider_smoke_latest: [],
};

// Minimal stubs for endpoints the #agents tab fetches on mount; without
// these the tab may render an "API unavailable" state and the test
// would be unable to reach the ActiveTasksPanel.
const STUB_AGENTS_ROSTER: ReadonlyArray<Record<string, unknown>> = [
  {
    id: "factory-operator",
    role: "Factory Operator",
    status: "idle",
    task_count: 0,
    last_activity_utc: "2026-05-11T14:00:00Z",
    model_provider: "ollama/llama3.1:8b",
  },
];

const STUB_ACTION_CATALOG = {
  status: "ready",
  summary: "Hermes Agents catalog (w18-a25 stub).",
  contract_version: "agent-operator-contract-v1",
  counts: { ready: 4 },
  total: 4,
  ready_now: [],
  blocked_or_partial: [],
  contracts: [],
};

const STUB_EMPTY_OBJECT = { status: "ready" };

// Realistic-shape stubs for the agents-tab aux endpoints so the
// AgentsTab itself doesn't throw on undefined-array reads (e.g.
// ``e2eReadiness.blocked_reasons.length`` at Agents.tsx:434).
const STUB_E2E_READINESS = {
  status: "blocked",
  ready: false,
  summary: "Stubbed for W18-A25 test.",
  blocked_reasons: [],
  programming: {
    status: "blocked",
    ready: false,
    provider_lanes: [],
    blocked_reasons: [],
  },
  folder_index: {
    status: "blocked",
    loaded: [],
    missing: [],
    target_roots: [],
    provider_context_files: [],
    required: [],
  },
  cli_runners: {
    status: "blocked",
    count: 0,
    detected: 0,
    runners: [],
    sandbox: {
      status: "blocked",
      ready: false,
      mode: "docker",
      docker_executable: null,
      docker_version: null,
      image_configured: false,
      image: null,
      network_mode: "none",
      workspace_mount: "",
      denied_paths: [],
      blocked_reasons: [],
    },
    policy: { write_runs_allowed: false, reason: "stub", allowed_now: [] },
  },
  next_required_steps: [],
};

const STUB_CLI_RUNNERS = {
  status: "blocked",
  count: 0,
  detected: 0,
  runners: [],
  sandbox: STUB_E2E_READINESS.cli_runners.sandbox,
  policy: { write_runs_allowed: false, reason: "stub", allowed_now: [] },
};

const STUB_SANDBOX = STUB_E2E_READINESS.cli_runners.sandbox;

const STUB_RUNTIME_IDENTITY = {
  bridge_port: 8765,
  hermes_agent_version: "stub",
  hermes_agent_revision: "stub",
};

async function stubBackend(page: Page, tasksPayload: unknown): Promise<void> {
  // Tasks endpoint — the panel's main fetch.
  await page.route("**/api/agents/tasks**", (route: Route) => fulfillJson(route, tasksPayload));
  // Aux endpoints the AgentsTab itself fetches; we don't care about
  // their values, only that they don't 404 and gate the tab.
  await page.route("**/api/agents", (route: Route) => fulfillJson(route, STUB_AGENTS_ROSTER));
  await page.route("**/api/agents/action-catalog", (route: Route) =>
    fulfillJson(route, STUB_ACTION_CATALOG),
  );
  await page.route("**/api/agents/actions/catalog", (route: Route) =>
    fulfillJson(route, STUB_ACTION_CATALOG),
  );
  await page.route("**/api/notifications", (route: Route) =>
    fulfillJson(route, { notifications: [] }),
  );
  // Minimum stubs to keep the workbench panels honest-blocked silently
  // rather than throwing, so the screenshot is clean.
  await page.route("**/api/code-operator/e2e/readiness", (route: Route) =>
    fulfillJson(route, STUB_E2E_READINESS),
  );
  await page.route("**/api/code-operator/cli-runners", (route: Route) =>
    fulfillJson(route, STUB_CLI_RUNNERS),
  );
  await page.route("**/api/code-operator/sandbox/readiness", (route: Route) =>
    fulfillJson(route, STUB_SANDBOX),
  );
  await page.route("**/api/system/runtime-identity", (route: Route) =>
    fulfillJson(route, STUB_RUNTIME_IDENTITY),
  );
  // Catch-all for any other agent surface so a stray fetch doesn't 404.
  await page.route("**/api/agents/health", (route: Route) =>
    fulfillJson(route, { healthy: false, status: "stub", agents: {}, setup: {} }),
  );
  await page.route("**/api/agents/config", (route: Route) =>
    fulfillJson(route, { accepted: true, status: "ready", config: {}, api_key_configured: false, redacted: [] }),
  );
  await page.route("**/api/agents/update-status", (route: Route) =>
    fulfillJson(route, STUB_EMPTY_OBJECT),
  );
  await page.route("**/api/learning/idle-workbench", (route: Route) =>
    fulfillJson(route, {
      status: "loading",
      review_policy: "stub",
      blockers: [],
      candidates: [],
      daily_prompt: { question: "?", last_candidate_at: null, suggested_kinds: [] },
    }),
  );
}

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
  page.on("pageerror", (err) => {
    // eslint-disable-next-line no-console
    console.log("[pageerror]", err.message, err.stack?.split("\n")[1] ?? "");
  });
});

async function assertNoUnexpectedErrors(page: Page): Promise<void> {
  const errors = await readErrors(page);
  // Filter the noise from optional probes (any 4xx we didn't stub).
  const remaining = errors.filter(
    (line) => !line.includes("Failed to load resource"),
  );
  expect(remaining, remaining.join("\n")).toEqual([]);
}

test("W18-A25: #agents Active Tasks panel renders provider rows from /api/agents/tasks", async ({ page }) => {
  await stubBackend(page, STUB_AGENT_TASKS_WITH_MINIMAX);
  await page.goto("/#agents");

  const panel = page.getByTestId("agents-active-tasks-panel");
  await expect(panel).toBeVisible({ timeout: 15_000 });

  // The provider smoke strip must show minimax + deepseek when stubs are present.
  await expect(page.getByTestId("agents-active-tasks-smoke-minimax")).toBeVisible();
  await expect(page.getByTestId("agents-active-tasks-smoke-deepseek")).toBeVisible();

  // The task list must have at least one row, and at least one row must
  // expose provider_id = "minimax" or "deepseek".
  const rows = page.getByTestId("agents-active-tasks-row");
  await expect(rows.first()).toBeVisible();
  const rowCount = await rows.count();
  expect(rowCount).toBeGreaterThanOrEqual(1);

  let providerSeen: string | null = null;
  for (let index = 0; index < rowCount; index += 1) {
    const provider = await rows.nth(index).getAttribute("data-task-provider-id");
    if (provider === "minimax" || provider === "deepseek") {
      providerSeen = provider;
      break;
    }
  }
  expect(
    providerSeen,
    `expected at least one row with provider_id minimax or deepseek; rows checked=${rowCount}`,
  ).not.toBeNull();

  // The visible row text must show the provider id so the operator can
  // see at a glance which provider just did work.
  await expect(page.getByTestId("agents-active-tasks-row-provider").first()).toBeVisible();

  await page.screenshot({
    path: "test-results/w18-a25/agents-active-tasks-with-rows.png",
    fullPage: true,
    animations: "disabled",
  });

  await assertNoUnexpectedErrors(page);
});

test("W18-A25: #agents Active Tasks panel honestly says 'No recent tasks' when feed is empty", async ({ page }) => {
  await stubBackend(page, STUB_AGENT_TASKS_EMPTY);
  await page.goto("/#agents");

  const panel = page.getByTestId("agents-active-tasks-panel");
  await expect(panel).toBeVisible({ timeout: 15_000 });

  // Empty-state element renders honestly — no fake "1 active task" UI.
  const empty = page.getByTestId("agents-active-tasks-empty");
  await expect(empty).toBeVisible();
  await expect(empty).toContainText(/No recent Hermes Agent code-team tasks/);

  // No row elements should exist.
  await expect(page.getByTestId("agents-active-tasks-row")).toHaveCount(0);

  // No provider smoke strip when there are no smokes.
  await expect(page.getByTestId("agents-active-tasks-smokes")).toHaveCount(0);

  await page.screenshot({
    path: "test-results/w18-a25/agents-active-tasks-empty.png",
    fullPage: true,
    animations: "disabled",
  });

  await assertNoUnexpectedErrors(page);
});

test("W18-A25: #agents Active Tasks panel surfaces failure state when /api/agents/tasks 500s", async ({ page }) => {
  // Stub the aux endpoints first with realistic shapes so the parent
  // AgentsTab itself renders cleanly, then override the tasks endpoint
  // with a 500. The order of route handlers matters because Playwright
  // matches by first-registered-wins for overlapping patterns.
  await stubBackend(page, STUB_AGENT_TASKS_EMPTY);
  await page.unroute("**/api/agents/tasks**");
  await page.route("**/api/agents/tasks**", (route: Route) =>
    route.fulfill({ status: 500, contentType: "text/plain", body: "Internal Server Error" }),
  );

  await page.goto("/#agents");

  const panel = page.getByTestId("agents-active-tasks-panel");
  await expect(panel).toBeVisible({ timeout: 15_000 });

  // The adapter's fetchJsonWithTimeout swallows the 500 into the
  // fallback envelope with schema_version "agent-tasks-unavailable",
  // which the panel renders as the explicit "unavailable" state.
  // No fake "1 active task" UI, no silently-empty list.
  const unavailable = page.getByTestId("agents-active-tasks-unavailable");
  await expect(unavailable).toBeVisible({ timeout: 10_000 });
  await expect(unavailable).toContainText(/Active Tasks API unavailable/);

  await page.screenshot({
    path: "test-results/w18-a25/agents-active-tasks-500.png",
    fullPage: true,
    animations: "disabled",
  });
});
