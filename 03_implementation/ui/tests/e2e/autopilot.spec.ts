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

test("Autopilot tab mounts and surfaces honest readiness rows", async ({ page }) => {
  await page.route("**/api/autopilot/readiness", (route) =>
    fulfillJson(route, [
      { id: "printer_connectivity", name: "Printer Connectivity", ready: true, message: "" },
      {
        id: "api_token_set",
        name: "API Token Set",
        ready: false,
        message: "Token missing from runtime env.",
        fix_target: "settings",
      },
    ]),
  );
  await page.route("**/api/autopilot/guardrails", (route) => fulfillJson(route, []));
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.autopilot);
  const root = page.getByTestId(TAB_FIXTURES.autopilot.rootTestId);
  await expect(root).toBeVisible();
  // Truthful empty-state for guardrails plus a readiness row should appear.
  await assertNoFakeVisibleText(page, TAB_FIXTURES.autopilot.rootTestId);
  await assertNoErrors(page);
});
