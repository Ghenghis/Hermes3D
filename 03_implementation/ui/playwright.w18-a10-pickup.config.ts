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
 *
 * W18-A10P-CIFIX project split (2026-05-11)
 * -----------------------------------------
 * The spec generates ONE test per manifest target, named
 * `<target.id> (<compare_mode>)`. Two Playwright projects consume the
 * same spec with non-overlapping `grep` filters:
 *
 *   - `live-targets`           — grep = /\(live\)$/
 *       Runs the 8 deterministic-renderable live targets. These remain
 *       HARD assertions: a pixel-diff or console error FAILS the test
 *       and gates GUI_PIXEL_E2E_GREEN.
 *
 *   - `informational-variants` — grep = /\(informational\)$/
 *       Runs the 23 composite/concept/named-theme PARTIAL targets. The
 *       spec wraps each in try/catch so a closed-page / nav crash
 *       (the PR-#241 failure mode for
 *        08_workflow_printqueue_files_logs and
 *        08_proof_health_notifications_safety) records a PARTIAL row
 *       with `crash_during_capture=true` instead of failing Playwright.
 *
 * Together: both projects RUN every manifest target exactly once (no
 * `test.skip`); only the `live-targets` project gates Layer D2.
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
      name: "live-targets",
      // The 8 deterministic-renderable live targets. HARD assertions.
      grep: /\(live\)$/,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
    {
      name: "informational-variants",
      // The 23 composite / concept / named-theme PARTIAL targets. The
      // spec wraps these in try/catch so a screenshot crash records a
      // PARTIAL row instead of failing Layer D2.
      grep: /\(informational\)$/,
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
