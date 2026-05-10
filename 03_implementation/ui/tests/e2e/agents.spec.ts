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

test("Agents tab mounts and shows Hermes Agent operator surface", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.agents);
  const root = page.getByTestId(TAB_FIXTURES.agents.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.agents.rootTestId);
  await assertNoErrors(page);
});
