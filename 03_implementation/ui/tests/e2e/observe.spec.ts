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

test("Observe tab mounts and renders the camera surface root", async ({ page }) => {
  // Stub printers so Observe never tries to reach the real S1/T1/V400 fleet.
  await page.route("**/api/printers", (route) => fulfillJson(route, { printers: [] }));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.observe);
  const root = page.getByTestId(TAB_FIXTURES.observe.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.observe.rootTestId);
  await assertNoErrors(page);
});
