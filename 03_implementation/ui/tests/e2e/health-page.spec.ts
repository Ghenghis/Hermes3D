/**
 * W11-2 — ServiceHealthPage Playwright E2E spec.
 *
 * Closes the W10-A9 PROOF_PARTIAL finding for closed-unmerged PR #37
 * (ServiceHealthPage scope, replaced by PR #42). PR #42 landed
 * `core.health.probe` + the FastAPI endpoint + ServiceCard/StatusPill
 * subcomponents (31 backend tests pass) but no UI-side Playwright spec
 * existed at HEAD. This spec proves the page mounts, renders one
 * ServiceCard per probed service, applies the correct StatusPill tone
 * per status, and emits no console errors.
 *
 * The page is exercised via the `#health` hash gate added in
 * `main.tsx` alongside the existing `#apps` gate (parallel pattern; the
 * AppShell-side wiring is owned by a downstream lane and out of scope).
 *
 * Sources:
 *  - Playwright assertions / `toHaveAttribute`, `getByTestId`, route stubs:
 *      https://playwright.dev/docs/test-assertions
 *  - Existing project pattern (hash gate + route stub + screenshot):
 *      03_implementation/ui/tests/e2e/app-status.spec.ts
 *
 * No-fake / no-paid contract:
 *  - The mocked payload uses production wire shape from
 *    `src/types/serviceHealth.ts` and matches `parseServiceHealthArray`
 *    in `src/api/adapters.live.ts`. No invented fields.
 *  - W8-15 viewport (1536x1024) for the screenshot, matching the
 *    Images-GUI/ reference pack convention.
 */
import { expect, test } from "@playwright/test";
import { assertNoErrors, attachErrorCapture, fulfillJson } from "./_helpers";

const PROBED_AT = "2026-05-10T09:00:00Z";

const HEALTH_RESPONSE = {
  results: [
    {
      name: "hermes_agent",
      category: "api" as const,
      host: "127.0.0.1",
      port: 8765,
      status: "online" as const,
      detail: "ok",
      latency_ms: 12,
      probed_at: PROBED_AT,
    },
    {
      name: "opencode",
      category: "mcp" as const,
      host: "127.0.0.1",
      port: 9101,
      status: "unreachable" as const,
      detail: "timeout after 2s",
      latency_ms: 0,
      probed_at: PROBED_AT,
    },
    {
      name: "openhands",
      category: "mcp" as const,
      host: "127.0.0.1",
      port: 9102,
      status: "offline" as const,
      detail: "ECONNREFUSED",
      latency_ms: 0,
      probed_at: PROBED_AT,
    },
  ],
};

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
  await page.route("**/api/health/services", (route) => fulfillJson(route, HEALTH_RESPONSE));
});

test("Service Health page renders 3 ServiceCards with correct StatusPill tones", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1024 });
  await page.goto("/#health");

  await expect(page.getByTestId("service-health-root")).toBeVisible({ timeout: 15_000 });

  const cards = page.getByTestId("service-card");
  await expect(cards).toHaveCount(3);

  const hermesAgent = page.locator('[data-service-name="hermes_agent"]');
  await expect(hermesAgent).toBeVisible();
  await expect(hermesAgent.locator("[data-status-pill]")).toHaveAttribute("data-status", "online");

  const opencode = page.locator('[data-service-name="opencode"]');
  await expect(opencode).toBeVisible();
  await expect(opencode.locator("[data-status-pill]")).toHaveAttribute("data-status", "unreachable");

  const openhands = page.locator('[data-service-name="openhands"]');
  await expect(openhands).toBeVisible();
  await expect(openhands.locator("[data-status-pill]")).toHaveAttribute("data-status", "offline");

  await expect(page.getByTestId("service-health-summary")).toBeVisible();

  await page.screenshot({
    path: "test-results/w11-2-health-page-1536x1024.png",
    fullPage: true,
    animations: "disabled",
  });

  await assertNoErrors(page);
});
