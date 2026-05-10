/**
 * Wave 15 / Agent 16 — Primary Tabs C screenshot capture.
 *
 * Captures 1536x1024 evidence for the four tabs in this lane:
 *   - Artifacts
 *   - Approvals
 *   - Plugins
 *   - Roadmap
 *
 * Output: 03_implementation/proof/screenshots/w15-a16/*.png
 *
 * Notes:
 *   - Uses URL-hash routing (e.g. `#approvals`) registered in the AppShell
 *     store. Roadmap is not in PRIMARY_TABS (filtered out of the sidebar)
 *     but is registered as a tab in the store's TAB_IDS, so it renders via
 *     hash route.
 *   - Each tab renders honest-blocked empty states when the backend is not
 *     available, matching the "no fake data" contract. The screenshots
 *     therefore capture the live UI shell with intentional empty/blocked
 *     copy when run standalone against vite-only.
 *   - This spec is screenshot-only (no pixel diff vs baseline) so it can
 *     run as proof-of-render in isolation.
 *
 * Sources:
 *   - Playwright Screenshot API:
 *     https://playwright.dev/docs/screenshots
 *   - Playwright page.goto with fragment:
 *     https://playwright.dev/docs/api/class-page#page-goto
 */
import { test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SCREENSHOT_DIR = path.resolve(
  __dirname,
  "../../../proof/screenshots/w15-a16",
);

test.beforeAll(() => {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
});

const TABS = [
  { id: "artifacts", hash: "artifacts", testId: "artifacts-root" },
  { id: "approvals", hash: "approvals", testId: "approvals-root" },
  { id: "plugins", hash: "plugins", testId: "plugins-root" },
  { id: "roadmap", hash: "roadmap", testId: "roadmap-root" },
];

test.describe("W15-A16 Primary Tabs C @ 1536x1024", () => {
  test.use({ viewport: { width: 1536, height: 1024 } });

  const consoleErrors = new Map<string, string[]>();

  for (const tab of TABS) {
    test(`captures ${tab.id} tab`, async ({ page }) => {
      const errors: string[] = [];
      consoleErrors.set(tab.id, errors);
      page.on("console", (msg) => {
        if (msg.type() === "error") {
          errors.push(msg.text());
        }
      });
      page.on("pageerror", (err) => {
        errors.push(`pageerror: ${err.message}`);
      });

      await page.goto(`/#${tab.hash}`);
      await page.waitForSelector(`[data-testid="${tab.testId}"]`, { timeout: 15_000 });
      await page.waitForLoadState("domcontentloaded");
      // Give recharts/SVG/recharts one paint frame to settle.
      await page.evaluate(
        () => new Promise((r) => requestAnimationFrame(() => r(null))),
      );
      const out = path.join(SCREENSHOT_DIR, `${tab.id}-1536x1024.png`);
      await page.screenshot({
        path: out,
        fullPage: false,
        animations: "disabled",
      });

      // Write the console-error count alongside the PNG for the audit.
      fs.writeFileSync(
        path.join(SCREENSHOT_DIR, `${tab.id}-console-errors.json`),
        JSON.stringify({ tab: tab.id, errors }, null, 2),
      );
    });
  }
});
