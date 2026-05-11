/**
 * W18-A13 — Playwright config for the backend-wiring fix proof.
 *
 * Required by the W18-A13 brief: a dedicated config with NO webServer
 * block, hitting the LIVE Hermes3D bridge stack at http://127.0.0.1:8765
 * via a separately started Vite preview at :5173.
 *
 * The W18-A13 e2e spec drives:
 *   - GET /api/health/services → honest-blocked banner rendering.
 *   - GET /api/mcp/locks → row-per-file rendering from the items[]/files[]
 *     envelope.
 *   - GET /api/agents/config → form populated from the new GET handler.
 *   - POST /api/approvals/{id}/defer → action accepted, transitions row.
 *   - POST /api/autopilot/next-gate → 409 → honest-blocked message
 *     surface (including the `next.message`).
 *
 * No printer-control writes are exercised — operator freeze
 * (GUI_PHYSICAL_PRINT_GREEN / GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE).
 *
 * Sources:
 *   - Playwright defineConfig docs:
 *     https://playwright.dev/docs/test-configuration
 *   - W18-A3 audit report (locked file).
 */
import { defineConfig, devices } from "@playwright/test";

const LIVE_BASE_URL =
  process.env.W18_A13_LIVE_BASE_URL ?? "http://127.0.0.1:5173";
const LIVE_BACKEND_URL =
  process.env.W18_A13_BACKEND_URL ?? "http://127.0.0.1:8765";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a13-backend-wiring\.spec\.ts$/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results/w18-a13",
  timeout: 60_000,
  use: {
    baseURL: LIVE_BASE_URL,
    viewport: { width: 1536, height: 1024 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
    // Surface the backend URL to the spec via test annotation so the
    // suite probes the live bridge directly (no fixture mocks).
    extraHTTPHeaders: {
      "X-W18-A13-Backend": LIVE_BACKEND_URL,
    },
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
  // No webServer block — the live FastAPI bridge + Vite preview are
  // started by the operator before running this config. This keeps the
  // spec honest: a stale or missing backend produces an explicit
  // banner rather than a silent skipped pass.
});
