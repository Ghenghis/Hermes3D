import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  attachErrorCapture,
  openTab,
} from "./_helpers";

/**
 * E2E coverage for the W6-3 Dashboard mode switcher.
 *
 * Each test:
 *   1. Loads the GUI at a deep-link hash for one of the three modes.
 *   2. Asserts that the dashboard root mounts with the expected
 *      `data-dashboard-mode` attribute.
 *   3. Captures a screenshot for the artifact archive (this is what the W6-3
 *      handoff document references).
 *   4. Asserts no JS console errors during render.
 */

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

test("Dashboard advanced mode renders with the action-window button", async ({ page }) => {
  await page.goto("/#dashboard:advanced");
  const root = page.getByTestId(TAB_FIXTURES.dashboard.rootTestId);
  await expect(root).toBeVisible({ timeout: 15_000 });
  // The advanced shell is the parent — match by the inner Dashboard.tsx root.
  await expect(page.getByTestId("dashboard-advanced-action-window-btn")).toBeVisible();
  await page.screenshot({ path: "test-results/e2e/artifacts/dashboard-advanced.png", fullPage: true });
  await assertNoErrors(page);
});

test("Dashboard simple mode shows minimal KPI tiles only", async ({ page }) => {
  await page.goto("/#dashboard:simple");
  const root = page.getByTestId(TAB_FIXTURES.dashboard.rootTestId);
  await expect(root).toBeVisible({ timeout: 15_000 });
  await expect(root).toHaveAttribute("data-dashboard-mode", "simple");
  await expect(page.getByTestId("dashboard-simple-kpi-total-printers")).toBeVisible();
  await expect(page.getByTestId("dashboard-simple-hero")).toBeVisible();
  // Advanced + custom widgets must NOT be present in simple.
  await expect(page.getByTestId("dashboard-advanced-action-window-btn")).toHaveCount(0);
  await expect(page.getByTestId("dashboard-custom-grid")).toHaveCount(0);
  await page.screenshot({ path: "test-results/e2e/artifacts/dashboard-simple.png", fullPage: true });
  await assertNoErrors(page);
});

test("Dashboard custom mode renders the configurable grid", async ({ page }) => {
  await page.goto("/#dashboard:custom");
  const root = page.getByTestId(TAB_FIXTURES.dashboard.rootTestId);
  await expect(root).toBeVisible({ timeout: 15_000 });
  await expect(root).toHaveAttribute("data-dashboard-mode", "custom");
  await expect(page.getByTestId("dashboard-custom-grid")).toBeVisible();
  await expect(page.getByTestId("dashboard-custom-edit-btn")).toBeVisible();
  await page.screenshot({ path: "test-results/e2e/artifacts/dashboard-custom.png", fullPage: true });
  await assertNoErrors(page);
});

test("Mode switcher cycles between all three modes via the top-right toggle", async ({ page }) => {
  await page.goto("/#dashboard:advanced");
  await openTab(page, TAB_FIXTURES.dashboard);

  const switcher = page.getByTestId("dashboard-mode-switcher");
  await expect(switcher).toBeVisible();

  // Switch to simple.
  await page.getByTestId("dashboard-mode-btn-simple").click();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("data-dashboard-mode", "simple", { timeout: 5_000 });
  expect(await page.evaluate(() => window.location.hash)).toBe("#dashboard:simple");

  // Switch to custom.
  await page.getByTestId("dashboard-mode-btn-custom").click();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("data-dashboard-mode", "custom", { timeout: 5_000 });
  expect(await page.evaluate(() => window.location.hash)).toBe("#dashboard:custom");

  // Switch back to advanced.
  await page.getByTestId("dashboard-mode-btn-advanced").click();
  // Advanced uses a different root (the legacy Dashboard) so we look for the
  // action-window chip instead of the data-dashboard-mode attribute.
  await expect(page.getByTestId("dashboard-advanced-action-window-btn")).toBeVisible();
  expect(await page.evaluate(() => window.location.hash)).toBe("#dashboard:advanced");

  await assertNoErrors(page);
});

test("Query string ?mode= overrides the persisted mode at load", async ({ page }) => {
  // Pre-seed localStorage with "simple" but ask the loader for "custom" — the
  // query string should win.
  await page.addInitScript(() => {
    window.localStorage.setItem("h3d.dashboard.mode", "simple");
  });
  await page.goto("/?mode=custom#dashboard");
  const root = page.getByTestId("dashboard-root");
  await expect(root).toBeVisible({ timeout: 15_000 });
  await expect(root).toHaveAttribute("data-dashboard-mode", "custom", { timeout: 5_000 });
  await assertNoErrors(page);
});
