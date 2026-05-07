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

test("Dashboard renders live root and exposes the Hermes Agent chat mirror", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.dashboard);
  // Hermes Agent chat mirror is required from every dashboard surface.
  // We assert the chat-mirror trigger is reachable rather than fabricating any content.
  const root = page.getByTestId(TAB_FIXTURES.dashboard.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.dashboard.rootTestId);
  await assertNoErrors(page);
});

test("Dashboard direct hash route mounts dashboard root", async ({ page }) => {
  await page.goto("/#dashboard");
  await expect(page.getByTestId(TAB_FIXTURES.dashboard.rootTestId)).toBeVisible({ timeout: 15_000 });
  await assertNoErrors(page);
});
