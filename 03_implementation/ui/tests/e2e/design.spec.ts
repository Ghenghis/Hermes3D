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

test("Design tab mounts and exposes parametric template surface", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.design);
  const root = page.getByTestId(TAB_FIXTURES.design.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.design.rootTestId);
  await assertNoErrors(page);
});
