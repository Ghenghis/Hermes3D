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

test("Jobs tab mounts and renders an honest empty queue when backend reports none", async ({ page }) => {
  await page.route("**/api/jobs", (route) => fulfillJson(route, { jobs: [] }));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.jobs);
  const root = page.getByTestId(TAB_FIXTURES.jobs.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.jobs.rootTestId);
  await assertNoErrors(page);
});
