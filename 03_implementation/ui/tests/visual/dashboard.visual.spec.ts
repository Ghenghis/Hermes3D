import { expect, test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Phase 2 Dashboard visual gate.
 *
 *  1. Boot the app at 1920×1080 (configured in playwright.config.ts).
 *  2. Wait for the Dashboard root to render — `data-testid="dashboard-root"`.
 *  3. Export the current screenshot to `artifacts/dashboard-current-1920x1080.png`
 *     (always, for human review, even when the diff fails).
 *  4. Run the strict pixel diff via `toHaveScreenshot` (3% tolerance).
 *     - On first run (no baseline) Playwright creates the snapshot under
 *       `tests/visual/__screenshots__/` and the test fails by design — commit
 *       the snapshot, then subsequent runs enforce the diff.
 *
 * Phase 2 safety boundary (see ../../../README.md §"Phase 2 safety boundary"):
 *   This test is forbidden from launching external applications. It must NOT
 *   call `page.click()` on download/file links, navigate to `file://` URLs,
 *   trigger filechooser dialogs, or call any process-spawn API. Pure
 *   navigation + screenshot only.
 */

const ARTIFACT_DIR = path.resolve(__dirname, "../../artifacts");
const ARTIFACT_PATH = path.join(ARTIFACT_DIR, "dashboard-current-1920x1080.png");

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
});

test.describe("Dashboard @ 1920×1080", () => {
  test("renders all panels and matches visual baseline", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 15_000 });
    // Give recharts and the SVG previews one paint frame to settle.
    await page.waitForLoadState("networkidle");
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r(null))));

    // Always export the current screenshot artifact for human review.
    await page.screenshot({
      path: ARTIFACT_PATH,
      fullPage: false,
      animations: "disabled",
    });

    // Strict pixel diff (3% tolerance). First run creates the baseline.
    await expect(page).toHaveScreenshot("dashboard-1920x1080.png", {
      maxDiffPixelRatio: 0.03,
      animations: "disabled",
      fullPage: false,
    });
  });
});
