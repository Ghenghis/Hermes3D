import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A11 App Registry real-data config (AUDIT-ONLY).
 *
 * Intentionally has NO `webServer` block — this audit runs against the
 * already-live dev stack the operator is auditing:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI; LIVE_BASE_URL)
 *
 * Verdict gate this lane drives: GUI_60_APPS_GREEN.
 *
 * Hard rules (mirrors W18-A1 / A5 / A7 audit pattern):
 *   - No mocks; no route stubs; no harness-side "this is acceptable"
 *     predicates. The live FastAPI server is the source of truth.
 *   - Printer-domain side effects are forbidden by the operator freeze
 *     (printer heater on). Launch / proof / rollback buttons whose
 *     handlers dispatch to a printer or to /api/jobs are SKIPPED with
 *     a recorded backend reason — never clicked.
 *   - test.skip is forbidden; FAIL_NOT_WIRED is the honest outcome for
 *     missing surfaces. (W18-A14 no-skip harness rule.)
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a11-app-registry-real-data\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a11/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a11/html" }],
  ],
  outputDir: "test-results/w18-a11/artifacts",
  timeout: 10 * 60_000,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    extraHTTPHeaders: {
      // Identify this lane in backend access logs.
      "X-Hermes-Audit-Lane": "w18-a11",
    },
  },
  projects: [
    {
      name: "chromium-w18-a11",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
