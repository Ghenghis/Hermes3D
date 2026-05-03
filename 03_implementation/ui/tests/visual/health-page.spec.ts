import { expect, test } from "@playwright/test";

/**
 * Service Health page E2E.
 *
 * Drives the Phase 2 React UI in `mock` and `live` adapter modes to confirm:
 *   - Sidebar exposes a "Service Health" tab.
 *   - Mock-mode page renders cards from `MOCK_SERVICE_HEALTH`.
 *   - Live-mode page calls `GET /api/health/services` and renders the
 *     mocked-server response (status pills, latency, host:port).
 *   - "Re-probe now" button triggers a fresh request.
 *   - "Pause auto-refresh" toggles the `aria-pressed` state.
 *
 * The launcher is launched by `playwright.config.ts` (`webServer: vite`).
 * The FastAPI bridge is intentionally not booted here — we mock the route.
 */

test("mock-mode renders a Service Health tab with cards", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Service Health", exact: true }).click();

  const root = page.getByTestId("service-health-root");
  await expect(root).toBeVisible();
  await expect(page.getByTestId("service-card").first()).toBeVisible();
  // Mock data has 8 services
  await expect(page.getByTestId("service-card")).toHaveCount(8);

  // Summary pill row should be populated
  await expect(page.getByTestId("service-health-summary")).toBeVisible();
});

test("live-mode fetches /api/health/services and renders the response", async ({ page }) => {
  await page.route(/\/api\/health\/services/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results: [
          {
            name: "LM Studio",
            category: "llm",
            host: "127.0.0.1",
            port: 1234,
            status: "online",
            detail: "TCP 127.0.0.1:1234 accepted",
            latency_ms: 4.2,
            probed_at: "2026-05-03T12:00:00+00:00",
          },
          {
            name: "Ollama",
            category: "llm",
            host: "127.0.0.1",
            port: 11434,
            status: "offline",
            detail: "TCP 127.0.0.1:11434 refused (errno=10061)",
            latency_ms: 12.8,
            probed_at: "2026-05-03T12:00:00+00:00",
          },
          {
            name: "FastAPI server",
            category: "api",
            host: "127.0.0.1",
            port: 8000,
            status: "online",
            detail: "TCP 127.0.0.1:8000 accepted",
            latency_ms: 2.3,
            probed_at: "2026-05-03T12:00:00+00:00",
          },
        ],
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "Service Health", exact: true }).click();

  await expect(page.getByTestId("service-health-root")).toBeVisible();
  await expect(page.getByTestId("service-card")).toHaveCount(3);

  // Spot-check status mapping for online vs offline
  await expect(
    page.locator('[data-service-name="LM Studio"][data-service-status="online"]'),
  ).toBeVisible();
  await expect(
    page.locator('[data-service-name="Ollama"][data-service-status="offline"]'),
  ).toBeVisible();
});

test("re-probe now button triggers another fetch", async ({ page }) => {
  let calls = 0;
  await page.route(/\/api\/health\/services/, async (route) => {
    calls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        results: [
          {
            name: "LM Studio",
            category: "llm",
            host: "127.0.0.1",
            port: 1234,
            status: "online",
            detail: "TCP 127.0.0.1:1234 accepted",
            latency_ms: 4.2,
            probed_at: "2026-05-03T12:00:00+00:00",
          },
        ],
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "Service Health", exact: true }).click();

  // Wait for the initial fetch to land
  await expect(page.getByTestId("service-card")).toHaveCount(1);
  const initial = calls;

  await page.getByTestId("service-health-reprobe").click();
  await expect.poll(() => calls).toBeGreaterThan(initial);
});

test("pause auto-refresh toggles aria-pressed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Service Health", exact: true }).click();

  const pauseBtn = page.getByTestId("service-health-pause");
  await expect(pauseBtn).toHaveAttribute("aria-pressed", "false");
  await pauseBtn.click();
  await expect(pauseBtn).toHaveAttribute("aria-pressed", "true");
  await pauseBtn.click();
  await expect(pauseBtn).toHaveAttribute("aria-pressed", "false");
});
