import { expect, test } from "@playwright/test";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

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
const TABS = [
  "Dashboard",
  "Agents",
  "Workflows",
  "3D Generation",
  "Blender MCP",
  "Slicing",
  "Printer Fleet",
  "Print Queue",
  "Printer Control",
  "Docked Apps",
  "Proof & Reports",
  "System Logs",
  "Service Health",
  "Settings",
] as const;

const FORBIDDEN_SOURCE_PATTERNS = [
  { label: "BrowserWindow", pattern: /\bBrowserWindow\b/ },
  { label: "webview element", pattern: /<webview\b|\bWebView\b/i },
  { label: "window.open", pattern: /\bwindow\s*\.\s*open\s*\(/ },
  { label: "openExternal", pattern: /\bopenExternal\s*\(/ },
  { label: "child_process", pattern: /\bchild_process\b/ },
  { label: "spawn", pattern: /\bspawn\s*\(/ },
  { label: "exec", pattern: /\bexec\s*\(/ },
  { label: "shell API", pattern: /\bshell\s*\./ },
  { label: "process API", pattern: /\bprocess\s*\./ },
] as const;

function collectSourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      return collectSourceFiles(fullPath);
    }
    return /\.(ts|tsx)$/.test(entry.name) ? [fullPath] : [];
  });
}

test.describe("Panel dock state machine @ 1920×1080", () => {
  test("every tab panel exposes required Phase 2 chrome", async ({ page }) => {
    await page.goto("/");
    const sidebar = page.locator('aside[aria-label="Primary navigation"]');

    for (const tab of TABS) {
      await sidebar.getByRole("button", { name: tab, exact: true }).click();

      const panels = page.locator("[data-panel-id]");
      await expect.poll(async () => panels.count(), `${tab} panels`).toBeGreaterThan(0);
      const panelCount = await panels.count();

      for (let index = 0; index < panelCount; index += 1) {
        const panel = panels.nth(index);
        await expect(panel).toHaveAttribute("aria-label", /.+/);
        await expect(panel.locator("[data-panel-header-status]")).toHaveCount(1);
        await expect(panel.locator('[role="group"][aria-label^="Dock mode controls for"]')).toHaveCount(1);
        await expect(panel.locator('button[data-dock-mode="docked"]')).toHaveCount(1);
        await expect(panel.locator('button[data-dock-mode="undocked"]')).toHaveCount(1);
        await expect(panel.locator('button[data-dock-mode="fullscreen"]')).toHaveCount(1);
        await expect(panel.locator('button[data-action="collapse"]')).toHaveCount(1);
        await expect(panel.locator('button[data-action="more"]')).toHaveCount(1);
      }
    }
  });

  test("dock toggle: switches state via store", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");

    await fleet.locator('button[data-dock-mode="undocked"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "undocked");

    await fleet.locator('button[data-dock-mode="fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "fullscreen");

    await fleet.locator('button[data-dock-mode="docked"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");
  });

  test("fullscreen overlay renders fixed-position CSS (no native window)", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);

    await fleet.locator('button[data-dock-mode="fullscreen"]').click();
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

    await fleet.locator('button[data-dock-mode="fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "fullscreen");

    // Second click on the same active mode → toggles back to docked.
    await fleet.locator('button[data-dock-mode="fullscreen"]').click();
    await expect(fleet).toHaveAttribute("data-dock-state", "docked");
  });

  test("collapse: hides panel body and flips chevron aria-label", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);
    const body = fleet.locator("[data-panel-body]");

    await expect(body).toBeVisible();
    await expect(fleet).toHaveAttribute("data-collapsed", "false");

    await fleet.locator('button[data-action="collapse"]').click();
    await expect(fleet).toHaveAttribute("data-collapsed", "true");
    await expect(body).toBeHidden();

    // Re-expand.
    await fleet.locator('button[data-action="collapse"]').click();
    await expect(fleet).toHaveAttribute("data-collapsed", "false");
    await expect(body).toBeVisible();
  });

  test("no external window or network calls during dock interactions", async ({ page }) => {
    const requests: string[] = [];
    let popups = 0;
    page.on("request", (req) => requests.push(req.url()));
    page.on("popup", () => {
      popups += 1;
    });
    await page.addInitScript(() => {
      Object.defineProperty(window, "__externalLaunchAttempts", {
        value: [],
        writable: true,
      });
      Object.defineProperty(window, "open", {
        configurable: true,
        writable: true,
        value: (...args: unknown[]) => {
          (window as Window & { __externalLaunchAttempts: string[][] }).__externalLaunchAttempts.push(
            args.map(String),
          );
          return null;
        },
      });
    });

    await page.goto("/");
    const fleet = page.locator(FLEET);

    // Exercise every dock + collapse path.
    await fleet.locator('button[data-dock-mode="undocked"]').click();
    await fleet.locator('button[data-dock-mode="fullscreen"]').click();
    await fleet.locator('button[data-dock-mode="docked"]').click();
    await fleet.locator('button[data-action="collapse"]').click();
    await fleet.locator('button[data-action="collapse"]').click();

    const launchAttempts = await page.evaluate(
      () => (window as Window & { __externalLaunchAttempts?: string[][] }).__externalLaunchAttempts ?? [],
    );
    expect(launchAttempts).toEqual([]);
    expect(popups).toBe(0);

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

  test("source has no external window/process launch path", () => {
    const sourceRoot = join(process.cwd(), "src");
    const violations = collectSourceFiles(sourceRoot).flatMap((file) => {
      const source = readFileSync(file, "utf8");
      return FORBIDDEN_SOURCE_PATTERNS.flatMap(({ label, pattern }) =>
        pattern.test(source) ? [`${file}: ${label}`] : [],
      );
    });

    expect(violations).toEqual([]);
  });

  test("aria contract: every dock-toggle button has label + title", async ({ page }) => {
    await page.goto("/");
    const fleet = page.locator(FLEET);

    for (const mode of ["docked", "undocked", "fullscreen"]) {
      const btn = fleet.locator(`button[data-dock-mode="${mode}"]`);
      await expect(btn).toBeVisible();
      await expect(btn).toHaveAttribute("aria-label", /PRINTER FLEET/);
      await expect(btn).toHaveAttribute("title", /./);
    }

    const collapse = fleet.locator('button[data-action="collapse"]');
    await expect(collapse).toBeVisible();
    await expect(collapse).toHaveAttribute("aria-expanded", "true");
  });
});
