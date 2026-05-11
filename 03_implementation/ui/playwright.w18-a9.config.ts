import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A9 modeler→slicer real-artifact audit config.
 *
 * Intentionally has NO `webServer` block — the lane spec runs against the
 * already-live dev stack at:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI; openapi.json on the same)
 *
 * Mirrors W18-A1's audit-mode pattern so the audit does not spin up a
 * second backend on 8766/8642 (which would diverge from the truth the
 * operator is auditing).
 *
 * Strict operator freeze applies: no printer hardware writes, no
 * Klipper/Moonraker dispatch, no OctoPrint upload. The spec hard-asserts
 * that NO printer-control endpoint was hit during the run.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a9-slicer-real-artifact\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a9/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a9/html" }],
  ],
  outputDir: "test-results/w18-a9/artifacts",
  timeout: 10 * 60_000,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-w18-a9",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
