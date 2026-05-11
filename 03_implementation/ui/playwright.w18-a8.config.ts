import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A8 artifact / file / proof audit config.
 *
 * Intentionally has NO `webServer` block — the lane spec runs against the
 * already-live dev stack at:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI — hermes3d.api.routes.artifacts +
 *                                       hermes3d.api.routes.system)
 *
 * This config exists so the audit hits the live :8765 stack without
 * accidentally spawning a second backend on a different port.
 *
 * LIVE_BASE_URL is read from env so an operator can point the spec at a
 * non-default port if needed (default: http://127.0.0.1:8765).
 *
 * Hard rule (operator freeze 2026-05-11): this spec must NOT touch any
 * printer-control endpoint. It only exercises /api/artifacts/* and
 * /api/proof/*.
 */
const LIVE_BASE_URL = process.env.LIVE_BASE_URL ?? "http://127.0.0.1:8765";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a8-artifact-file-proof\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a8/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a8/html" }],
  ],
  outputDir: "test-results/w18-a8/artifacts",
  timeout: 15 * 60_000,
  use: {
    // Frontend; the spec drives the live SPA at :5173.
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    extraHTTPHeaders: {
      "x-w18-a8-audit": "1",
    },
  },
  projects: [
    {
      name: "chromium-w18-a8",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
        // Expose the backend URL to the spec via process.env.
      },
    },
  ],
  metadata: {
    lane: "W18-A8",
    backend: LIVE_BASE_URL,
    pinned_verdicts: {
      GUI_PHYSICAL_PRINT_GREEN: "OUT_OF_SCOPE_BY_OPERATOR",
      GUI_PRINTER_DRY_RUN_GREEN: "OUT_OF_SCOPE_BY_OPERATOR",
    },
  },
});
