/**
 * Minimal Playwright config for the W15-A17 palette preview spec.
 *
 * Standalone so it doesn't require the e2e webServer (the spec is
 * self-contained via `page.setContent`). Run via:
 *   npx playwright test --config tests/visual/palettes.playwright.config.ts
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "palettes-preview.spec.ts",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  outputDir: "../../test-results/palettes-preview",
  use: {
    headless: true,
    screenshot: "off",
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
