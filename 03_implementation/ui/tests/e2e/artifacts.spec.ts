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

test("Artifacts tab mounts and renders empty-state when no artifacts exist", async ({ page }) => {
  await page.route("**/api/artifacts**", (route) => fulfillJson(route, { artifacts: [] }));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.artifacts);
  const root = page.getByTestId(TAB_FIXTURES.artifacts.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.artifacts.rootTestId);
  await assertNoErrors(page);
});
