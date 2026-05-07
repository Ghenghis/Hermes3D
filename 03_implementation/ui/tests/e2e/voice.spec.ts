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

test("Voice tab mounts and respects STT runtime gating", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.voice);
  const root = page.getByTestId(TAB_FIXTURES.voice.rootTestId);
  await expect(root).toBeVisible();
  // Voice must never claim STT works when runtime is missing - assert no fake/placeholder phrases.
  await assertNoFakeVisibleText(page, TAB_FIXTURES.voice.rootTestId);
  await assertNoErrors(page);
});
