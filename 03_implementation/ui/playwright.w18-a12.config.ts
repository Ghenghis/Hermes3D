import { defineConfig, devices } from "@playwright/test";

/**
 * W18-A12 slicer wire-up config.
 *
 * NO webServer block — the lane spec runs against the already-live dev
 * stack at:
 *   - Frontend: http://localhost:5173 (Vite)
 *   - Backend:  http://127.0.0.1:8765 (FastAPI)
 *
 * This is a real-artifact proof: the spec drives the Design tab, calls
 * /api/design/intake, then /api/slice, polls for a real G-code file on
 * disk, asserts sha256 + layer_count, and asserts NO printer-control
 * endpoint was touched.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a12-slicer-wireup\.spec\.ts/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a12/results.json" }],
    ["html", { open: "never", outputFolder: "test-results/w18-a12/html" }],
  ],
  outputDir: "test-results/w18-a12/artifacts",
  // Slicing a tiny cube is fast (~5 s) but a desk_organizer can take longer.
  // Give the whole spec 25 minutes worst-case.
  timeout: 25 * 60_000,
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
      name: "chromium-w18-a12",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
});
