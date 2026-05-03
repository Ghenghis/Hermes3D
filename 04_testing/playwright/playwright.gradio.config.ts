import { defineConfig } from '@playwright/test';

/**
 * Phase 5.1 — Layer-D3 Gradio smoke config.
 *
 * Scoped narrowly to `gradio_smoke.spec.ts` so it does NOT pick up the
 * existing Layer-D specs under `./specs/`. Layer-D's config is untouched.
 *
 * Booted by the same `scripts/run-e2e.sh` Layer-D uses; differentiated
 * only by which spec file Playwright runs and which report folder it
 * writes to (so artifacts don't collide in CI).
 */
export default defineConfig({
  testDir: '.',
  testMatch: 'gradio_smoke.spec.ts',
  timeout: 30_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report-gradio-smoke', open: 'never' }],
    ['junit', { outputFile: 'test-results/gradio-smoke-junit.xml' }],
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
});
