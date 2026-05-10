/**
 * Vite-only Playwright config for the W8-2 GUI breadth-page spec.
 *
 * The default `playwright.e2e.config.ts` boots the full Hermes3D stack
 * (FastAPI + Vite + desktop compat shim). The breadth spec stubs every
 * backend route, so it can run against a plain Vite dev server — that
 * keeps the spec executable in CI lanes that don't have the Python
 * runtime, and avoids cross-spec port contention.
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /gui-breadth-pages\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/e2e-breadth/results.json" }],
  ],
  outputDir: "test-results/e2e-breadth/artifacts",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-breadth",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
  // The breadth spec stubs every backend route, so it runs against a
  // production build served by `vite preview`. Production mode disables
  // React Fast Refresh and avoids the `$RefreshReg$ is not defined`
  // pitfall that bites Vite 8 + plugin-react 6 when a non-component module
  // returns a function expression (see `src/app/routes.tsx`).
  webServer: {
    command:
      "npx vite build --outDir dist-breadth && npx vite preview --outDir dist-breadth --host 127.0.0.1 --port 5174 --strictPort",
    url: "http://127.0.0.1:5174",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
