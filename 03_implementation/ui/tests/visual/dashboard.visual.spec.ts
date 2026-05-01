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
 *  4. Run the strict pixel diff via `toHaveScreenshot` (3% tolerance) — only
 *     on the platform whose baseline is committed.
 *
 * Baseline scoping:
 *   Playwright auto-keys baselines as
 *     `<name>-<projectName>-<process.platform>.png`.
 *   The committed baseline is `…-chromium-1920x1080-win32.png`. On other
 *   platforms (Linux CI runners) the test still navigates + exports the
 *   artifact for human review, but skips the strict pixel diff because
 *   sub-pixel font rendering and antialiasing diverge across platforms.
 *   Linux/macOS baselines can be added under their own `…-linux.png` /
 *   `…-darwin.png` filenames when those CI lanes need to gate on visuals.
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

    // Always export the current screenshot artifact for human review,
    // regardless of platform.
    await page.screenshot({
      path: ARTIFACT_PATH,
      fullPage: false,
      animations: "disabled",
    });

    // Strict pixel diff is only enforced where a platform-specific baseline
    // is committed. Phase 2 ships only the win32 baseline (the developer
    // host); Linux CI uploads the artifact instead.
    test.skip(
      process.platform !== "win32",
      `dashboard visual baseline is win32-only in Phase 2 (current platform: ${process.platform}); ` +
        `artifact exported to artifacts/dashboard-current-1920x1080.png for review`,
    );

    await expect(page).toHaveScreenshot("dashboard-1920x1080.png", {
      maxDiffPixelRatio: 0.03,
      animations: "disabled",
      fullPage: false,
    });
  });
});
