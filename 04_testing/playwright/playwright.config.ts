import { defineConfig, devices } from '@playwright/test';

/**
 * Hermes3D-OS Playwright config.
 *
 * Cross-browser is intentionally NOT configured. The kit targets a single
 * Gradio launcher rendered in Chromium for QA gating; expanding to Firefox /
 * WebKit would multiply CI time without catching kit-relevant regressions
 * (the Gradio UI does not ship browser-specific JS). Firefox/WebKit can be
 * re-enabled later by appending entries to `projects` below.
 *
 * `webServer` is intentionally OMITTED: Gradio + FastAPI lifecycle is owned
 * by `scripts/run-e2e.sh` so that import-time errors in the launcher fail
 * the whole run fast (instead of getting wrapped in Playwright's generic
 * "server failed to start" message).
 */
export default defineConfig({
  testDir: './specs',
  timeout: 30_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.HERMES3D_UI_URL ?? 'http://127.0.0.1:7860',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      animations: 'disabled',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  outputDir: 'test-results/',
  snapshotDir: '__snapshots__',
});
