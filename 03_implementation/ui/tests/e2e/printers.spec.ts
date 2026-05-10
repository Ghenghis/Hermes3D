import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  fulfillJson,
  openTab,
} from "./_helpers";

const FORBIDDEN_LIVE_PRINTER_IPS = ["192.168.0.10", "192.168.0.11", "192.168.0.12", "192.168.0.34"];

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
  // Hard-fail any direct request to the live operator printer fleet so this
  // spec never reaches S1/T1#1/T1#2/V400 on the user's network.
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (FORBIDDEN_LIVE_PRINTER_IPS.some((ip) => url.includes(ip))) {
      await route.abort();
      return;
    }
    await route.fallback();
  });
});

test("Printers tab mounts and never reaches live operator IPs from the browser", async ({ page }) => {
  // Stub printer list at the GUI-API boundary instead of the printer hardware.
  await page.route("**/api/printers", (route) =>
    fulfillJson(route, { printers: [] }),
  );
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.printers);
  const root = page.getByTestId(TAB_FIXTURES.printers.rootTestId);
  await expect(root).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.printers.rootTestId);
  await assertNoErrors(page);
});
