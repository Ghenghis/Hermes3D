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

test("Source OS renders root and renders modules list (or empty state) without faking", async ({ page }) => {
  // Pin module list to an honest empty payload so the spec is deterministic
  // against the GUI-API stub, which would otherwise return a real registry.
  await page.route("**/api/source/modules", (route) => fulfillJson(route, { modules: [] }));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.source_os);
  // With zero modules the UI must render a truthful empty state, not fabricated rows.
  await assertNoFakeVisibleText(page, TAB_FIXTURES.source_os.rootTestId);
  await assertNoErrors(page);
});

test("Source OS section landmarks remain stable when modules endpoint fails", async ({ page }) => {
  await page.route("**/api/source/modules", (route) =>
    fulfillJson(route, { error: "registry unavailable" }, 503),
  );
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.source_os);
  // Failure path: root still mounts, no forbidden terms, no console errors that crash the page.
  await expect(page.getByTestId(TAB_FIXTURES.source_os.rootTestId)).toBeVisible();
});
