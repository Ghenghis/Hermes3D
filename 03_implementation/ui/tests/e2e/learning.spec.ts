import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  openTab,
} from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

test("Learning tab mounts and exposes the idle workbench surface", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.learning);
  const root = page.getByTestId(TAB_FIXTURES.learning.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.learning.rootTestId);
  await assertNoErrors(page);
});
