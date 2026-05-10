import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  fulfillJson,
  openTab,
} from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

test("Plugins tab mounts and respects backend-not-configured gating", async ({ page }) => {
  // Stub plugins endpoint with a single plugin whose backend is honestly missing,
  // so the tab must show a blocked state rather than fabricate readiness.
  await page.route("**/api/plugins", (route) =>
    fulfillJson(route, {
      plugins: [
        {
          id: "test_plugin",
          name: "Test Plugin",
          enabled: false,
          status: "blocked",
          reason: "backend not configured",
          backend_configured: false,
        },
      ],
    }),
  );
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.plugins);
  const root = page.getByTestId(TAB_FIXTURES.plugins.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.plugins.rootTestId);
  await assertNoErrors(page);
});
