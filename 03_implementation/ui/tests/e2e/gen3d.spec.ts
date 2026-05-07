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

test("3D Generation tab mounts and exposes the generation entry surface", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.gen3d);
  const root = page.getByTestId(TAB_FIXTURES.gen3d.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.gen3d.rootTestId);
  await assertNoErrors(page);
});
