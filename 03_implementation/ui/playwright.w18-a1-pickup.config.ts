import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A1 PICKUP route walker config.
 *
 * Pickup lane (original w18-a1 subagent died silently). Intentionally has
 * NO `webServer` block — this config runs against an already-live local
 * dev stack started outside the test runner:
 *   - Frontend SPA: http://127.0.0.1:5173  (Vite — `baseURL` here)
 *   - Backend API : http://127.0.0.1:8765  (FastAPI — referenced from spec)
 *
 * Why no webServer:
 *   The brief mandates "no webServer, LIVE_BASE_URL". Spinning up a second
 *   backend in a temp port would diverge from the truth the operator is
 *   auditing. Operator pre-starts the stack via
 *     `node scripts/start-e2e-stack.mjs`
 *   or pre-existing dev sessions.
 *
 * Strict freeze respected by the spec (NOT enforced here — this file is
 * just the harness):
 *   - GUI_PHYSICAL_PRINT_GREEN     = OUT_OF_SCOPE_BY_OPERATOR
 *   - GUI_PRINTER_DRY_RUN_GREEN    = OUT_OF_SCOPE_BY_OPERATOR
 *   - No POST/PUT/PATCH to /api/printers/{id}/* that emits G-code/M-code.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a1-pickup-full-route-walk\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a1-pickup/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a1-pickup/html" }],
  ],
  outputDir: "test-results/w18-a1-pickup/artifacts",
  timeout: 30 * 60_000,
  use: {
    baseURL: process.env.LIVE_BASE_URL ?? "http://127.0.0.1:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-w18-a1-pickup",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
