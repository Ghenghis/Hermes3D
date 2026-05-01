import { expect, test } from "@playwright/test";

/**
 * Phase 2 Tasks 39-42 — dock/undock/fullscreen + collapse state machine.
 *
 * Tests are pure DOM/state assertions (no screenshot diff), so they can
 * change without bumping the dashboard visual baseline. Each test gets a
 * fresh browser context, so dock-state mutations don't leak across tests.
 *
 * Phase 2 safety boundary: this spec MUST NOT click any LockedAction or
 * trigger a download/file:// navigation. Pure store-mutation testing only.
 *
 * The fleet panel on the Dashboard is the canonical target — it has a
 * stable `data-panel-id="dashboard.fleet"` and is rendered in the default
 * tab so no extra navigation is required.
 */

const FLEET = '[data-panel-id="dashboard.fleet"]';

test.describe("Panel dock state machine @ 1920×1080", () => {
  test("dock toggle: switches state via store", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");

    await fleet.locator('button[aria-label="Undocked"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "undocked");

    await fleet.locator('button[aria-label="Fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "fullscreen");

    await fleet.locator('button[aria-label="Docked"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");
  });

  test("fullscreen overlay renders fixed-position CSS (no native window)", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);

    await fleet.locator('button[aria-label="Fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "fullscreen");

    // CSS-only fullscreen: `fixed inset-4 z-40 shadow-glow`. Bounding box
    // covers near-full viewport (allowing for the inset-4 = 16px gutters).
    const box = await fleet.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      // Viewport is 1920×1080 with inset-4 (16px). Allow ±2px tolerance.
      expect(box.width).toBeGreaterThan(1880); // 1920 − 32 = 1888
      expect(box.height).toBeGreaterThan(1040); // 1080 − 32 = 1048
    }
  });

  test("clicking the active dock mode returns to 'docked'", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);

    await fleet.locator('button[aria-label="Fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "fullscreen");

    // Second click on the same active mode → toggles back to docked.
    await fleet.locator('button[aria-label="Fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");
  });

  test("collapse: hides panel body and flips chevron aria-label", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);
    const body = fleet.locator("[data-panel-body]");

    await expect(body).toBeVisible();
    await expect(fleet).toHaveAttribute("data-collapsed", "false");

    await fleet.locator('button[aria-label="Collapse panel"]').click();
    await expect(fleet).toHaveAttribute("data-collapsed", "true");
    await expect(body).toBeHidden();

    // Re-expand.
    await fleet.locator('button[aria-label="Expand panel"]').click();
    await expect(fleet).toHaveAttribute("data-collapsed", "false");
    await expect(body).toBeVisible();
  });

  test("no external network calls during dock interactions", async ({ page }) => {
    const requests: string[] = [];
    page.on("request", (req) => requests.push(req.url()));

    await page.goto("/");
    const fleet = page.locator(FLEET);

    // Exercise every dock + collapse path.
    await fleet.locator('button[aria-label="Undocked"]').click();
    await fleet.locator('button[aria-label="Fullscreen"]').click();
    await fleet.locator('button[aria-label="Docked"]').click();
    await fleet.locator('button[aria-label="Collapse panel"]').click();
    await fleet.locator('button[aria-label="Expand panel"]').click();

    // Filter for cross-origin requests. Vite serves /node_modules/.vite/* over
    // localhost:5173 — those are expected. Anything else (file:// , external
    // domain) would be a Phase-2 violation.
    const external = requests.filter(
      (u) =>
        !u.startsWith("http://localhost:") &&
        !u.startsWith("ws://localhost:") &&
        !u.startsWith("data:") &&
        !u.startsWith("blob:") &&
        !u.startsWith("about:"),
    );
    expect(external, `unexpected external requests: ${external.join(", ")}`).toEqual([]);
  });

  test("aria contract: every dock-toggle button has label + title", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);

    for (const label of ["Docked", "Undocked", "Fullscreen"]) {
      const btn = fleet.locator(`button[aria-label="${label}"]`);
      await expect(btn).toBeVisible();
      await expect(btn).toHaveAttribute("title", new RegExp(label));
    }

    const collapse = fleet.locator('button[aria-label="Collapse panel"]');
    await expect(collapse).toBeVisible();
    await expect(collapse).toHaveAttribute("aria-expanded", "true");
  });
});
