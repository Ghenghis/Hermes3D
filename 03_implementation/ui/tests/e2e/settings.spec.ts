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

test("Settings tab mounts and exposes navigable settings panes", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.settings);
  const root = page.getByTestId(TAB_FIXTURES.settings.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.settings.rootTestId);
  await assertNoErrors(page);
});
