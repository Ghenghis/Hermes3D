import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/**
 * W18-A10 PICKUP visual-oracle Playwright config.
 *
 * NO `webServer` block — the spec runs against the already-live dev stack:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI)
 * Override via `LIVE_BASE_URL` (frontend). The spec reads that env var.
 *
 * No-recapture contract: `updateSnapshots: "none"` forbids
 * `--update-snapshots` from rewriting any baseline.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a10-pickup-visual-oracle\.spec\.ts/,
  globalSetup: path.join(HERE, "tests", "e2e", "w18-a10-pickup-global-setup.ts"),
  fullyParallel: false,
  retries: 0,
  workers: 1,
  // Allow the harness to complete even with live diffs; the spec marks live
  // diffs as failed assertions, the reporter aggregates the verdict.
  forbidOnly: false,
  updateSnapshots: "none",
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a10-pickup/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a10-pickup/html" }],
    ["./tests/visual-proof/w18-a10-pickup-reporter.ts"],
  ],
  outputDir: "test-results/w18-a10-pickup/artifacts",
  timeout: 90_000,
  use: {
    baseURL: process.env.LIVE_BASE_URL ?? "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-w18-a10-pickup",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
