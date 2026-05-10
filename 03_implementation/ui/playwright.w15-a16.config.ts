/**
 * Wave 15 / Agent 16 — Primary Tabs C screenshot capture config.
 *
 * Vite-only (no Python backend). Captures the UI shell at 1536x1024
 * for the four tabs in scope. Tabs degrade to honest-blocked empty
 * states when the live backend is absent, which is exactly the state
 * the audit needs to record.
 *
 * Sources:
 *   - Playwright defineConfig docs:
 *     https://playwright.dev/docs/test-configuration
 *   - vite preview / dev server:
 *     https://vite.dev/guide/cli.html
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual",
  testMatch: /w15-a16-tabs-c\.visual\.spec\.ts$/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "test-results/w15-a16",
  use: {
    baseURL: "http://localhost:5173",
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
  webServer: {
    // Vite dev server only — backend optional; tabs degrade honestly.
    command: "npx vite --host 127.0.0.1 --port 5173 --strictPort",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
