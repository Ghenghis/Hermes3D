import { defineConfig, devices } from "@playwright/test";

const apiPort = Number(process.env.HERMES3D_GUI_API_PORT ?? 18765);
const uiPort = Number(process.env.HERMES3D_UI_PORT ?? 15173);
const baseURL = process.env.HERMES3D_W18_A20_BASE_URL ?? `http://127.0.0.1:${uiPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /w18-a20-modeling-backend\.spec\.ts$/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/w18-a20/results.json" }],
  ],
  outputDir: "test-results/w18-a20/artifacts",
  use: {
    baseURL,
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-w18-a20",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: {
    command: "node scripts/start-e2e-stack.mjs",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 180_000,
    env: {
      HERMES3D_GUI_API_PORT: String(apiPort),
      HERMES3D_UI_PORT: String(uiPort),
      HERMES3D_START_DESKTOP_COMPAT: "0",
      VITE_HERMES3D_BRIDGE_PORT: String(apiPort),
      HERMES3D_STRICT_PORTS: "1",
    },
  },
});
