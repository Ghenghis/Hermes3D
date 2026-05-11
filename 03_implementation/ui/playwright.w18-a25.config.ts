/**
 * W18-A25 — Playwright config for the urgent #agents tab fix-it proof.
 *
 * Required by the W18-A25 brief: prove the new ActiveTasksPanel renders
 * with at least one real row when proof_events seeds are present, and
 * an honest "No recent tasks" state when the env is empty.
 *
 * No webServer block — the spec stubs ``/api/agents/tasks``,
 * ``/api/agents/action-catalog``, and ``/api/agents/actions/catalog`` with
 * real-shape JSON via ``page.route``, then loads the Vite preview at
 * :5173 (the operator starts it manually before running the suite, or
 * the test harness CI does it via a separate command).
 *
 * Operator freeze: no printer-control writes are exercised. The spec
 * only fakes the agents tasks endpoint and asserts DOM. The pinned
 * verdicts ``GUI_PHYSICAL_PRINT_GREEN`` / ``GUI_PRINTER_DRY_RUN_GREEN``
 * stay ``OUT_OF_SCOPE_BY_OPERATOR``.
 */
import { defineConfig, devices } from "@playwright/test";

const LIVE_BASE_URL =
  process.env.W18_A25_LIVE_BASE_URL ?? "http://127.0.0.1:5173";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a25-agents-tasks-visible\.spec\.ts$/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results/w18-a25",
  timeout: 60_000,
  use: {
    baseURL: LIVE_BASE_URL,
    viewport: { width: 1536, height: 1024 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
  },
  projects: [
    {
      name: "chromium-1536x1024",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1536, height: 1024 },
        deviceScaleFactor: 1,
      },
    },
  ],
  // No webServer block — the live Vite preview is started by the
  // operator before running this config. Spec stubs the backend so the
  // proof is deterministic regardless of upstream readiness.
});
