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

test("Approvals tab mounts and renders an honest empty queue when no approvals are pending", async ({ page }) => {
  await page.route("**/api/approvals**", (route) => fulfillJson(route, { approvals: [] }));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.approvals);
  const root = page.getByTestId(TAB_FIXTURES.approvals.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.approvals.rootTestId);
  await assertNoErrors(page);
});
