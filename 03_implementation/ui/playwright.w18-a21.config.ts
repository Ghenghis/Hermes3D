/**
 * W18-A21 — /api/providers/health smoke evidence + #agents GUI team-tasks
 * Playwright runner config.
 *
 * Hits a LIVE FastAPI bridge (no webServer, no Vite spawn). The spec is
 * env-aware (REAL_MINIMAX vs HONEST_BLOCKED) per the W18-A4 / W18-A17
 * pattern: it probes /api/code-operator/teams/readiness for
 * minimax-builders.live_status and chooses the honest branch.
 *
 * Defaults to LIVE_BASE_URL=http://127.0.0.1:8765 to match the local
 * Hermes3D bridge port. Overridable via the W18_A21_LIVE_BASE_URL env var
 * so this config can run against a remote staging bridge without code
 * changes.
 *
 * Sources:
 *   - Playwright defineConfig docs:
 *     https://playwright.dev/docs/test-configuration
 *   - W18-A17 pattern: tests/e2e/w18-a17-agents-operational.spec.ts
 *   - W18-A19 pattern: tests/e2e/w18-a19-provider-smoke.spec.ts
 */
import { defineConfig, devices } from "@playwright/test";

// baseURL is the React app origin (Vite dev or production preview).
// The FastAPI bridge URL is passed separately via W18_A21_API_BASE so this
// config works whether the dev stack runs both on 8765 or splits them
// (e.g. Vite on 5180 + FastAPI on 8030 during local development).
const LIVE_BASE_URL = process.env.W18_A21_LIVE_BASE_URL ?? "http://127.0.0.1:8765";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a21-minimax-task-in-gui\.spec\.ts$/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results/w18-a21",
  timeout: 240_000,
  use: {
    baseURL: LIVE_BASE_URL,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
    video: "off",
  },
  projects: [
    {
      name: "chromium-w18-a21",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
