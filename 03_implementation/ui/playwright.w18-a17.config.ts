import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A17 Hermes Agents OPERATIONAL config (AUDIT-ONLY).
 *
 * Intentionally has NO `webServer` block — this audit runs against the
 * already-live dev stack:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI; LIVE_BASE_URL)
 *
 * Verdict gate this lane drives: STRENGTHENED GUI_AGENT_WORKFLOW_GREEN.
 *
 * Strengthened verdict: PASS_REAL only if at least one real Hermes Agent
 * task completes via the live LM runtime, the result is persisted to
 * agent_conversations.message_type='RUNTIME_STREAM' AND proof_events row
 * 'hermes_agent_chat_runtime_request', the GUI displays the task message
 * and assistant reply, and the assistive task helped W18 completion (file
 * paths or concrete findings present in the reply text).
 *
 * Hard rules:
 *   - No mocks; no route stubs; no harness-side "this is acceptable" predicates.
 *   - NO printer hardware writes from the submitted agent task.
 *   - test.skip is forbidden; FAIL_NOT_WIRED / FAIL_PROVIDER_NOT_AVAILABLE
 *     is the honest outcome.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a17-agents-operational\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a17/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a17/html" }],
  ],
  outputDir: "test-results/w18-a17/artifacts",
  timeout: 10 * 60_000,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    extraHTTPHeaders: {
      "X-Hermes-Audit-Lane": "w18-a17",
    },
  },
  projects: [
    {
      name: "chromium-w18-a17",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
