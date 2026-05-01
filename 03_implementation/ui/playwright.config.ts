import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the Phase 2 visual screenshot gate.
 *
 * The test boots a fresh `vite` dev server, navigates to the Dashboard at
 * 1920×1080, disables animations, takes a screenshot, and (if a baseline is
 * present) diffs it against the committed baseline with `maxDiffPixelRatio:
 * 0.03`. The artifact is also exported to `artifacts/` for human review.
 *
 * Pixel-perfect comparison only works when the same browser, viewport,
 * deviceScaleFactor, fonts, and deterministic data are used — see
 * Dashboard.tsx + TopBar.tsx for our deterministic mock-data sources.
 */
export default defineConfig({
  testDir: "./tests/visual",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results",
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.03,
      animations: "disabled",
    },
  },
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
  },
  projects: [
    {
      name: "chromium-1920x1080",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
