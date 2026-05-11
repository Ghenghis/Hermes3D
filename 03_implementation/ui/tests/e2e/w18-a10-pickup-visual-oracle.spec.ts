/**
 * W18-A10 PICKUP — Visual Oracle Playwright spec.
 *
 * Pickup-suffixed fork of the dead `w18-a10-visual-oracle.spec.ts`. The
 * original w18-a10 subagent died silently with locks still held; this
 * pickup runs on `w18-a10-pickup` lock owner and a separate manifest so
 * the lock contention is avoided.
 *
 * Goal
 * ----
 * For EVERY PNG in `Images-GUI/` (the 31-image visual reference pack):
 *   1. Navigate the live UI at LIVE_BASE_URL (http://localhost:5173).
 *   2. Pin theme, deterministic clock, exact viewport from the manifest.
 *   3. Screenshot the page.
 *   4. Pixel-diff against the reference PNG with `pixelmatch`.
 *   5. Emit a diff PNG when there is any mismatch.
 *   6. compare_mode = "live"          -> assert diffRatio <= tolerance.
 *      compare_mode = "informational" -> annotate diff and PASS (PARTIAL
 *                                        with documented out-of-scope
 *                                        blocker per the pickup contract).
 *
 * Pickup contract (hard rules)
 * ----------------------------
 *   - DO NOT regenerate / recapture / replace `Images-GUI/*.png`.
 *   - DO NOT use `--update-snapshots` (the config also blocks it).
 *   - No harness-side console-error filtering for `live` mode targets.
 *   - No `test.skip` ever — every manifest entry produces a test.
 *   - No printer-hardware writes. We may render the printer UI; we never
 *     click any printer-control button.
 *   - Fix-it mode: when a `live` target diffs, the parent agent fixes the
 *     UI source. We never recapture the baseline.
 *
 * Architecture
 * ------------
 *   - `w18-a10-pickup-global-setup.ts` mirrors Images-GUI/* into
 *     `tests/e2e/__refs_pickup__/Images-GUI/` (idempotent, forward-only).
 *   - `w18-a10-pickup-pixel-compare.ts` wraps Playwright's bundled
 *     `pixelmatch` + `pngjs` so we record exact diffPixels per target.
 *   - `tests/visual-proof/w18-a10-pickup-reporter.ts` reads `w18-a10-pickup`
 *     annotations and writes the verdict summary + top-10 worst list.
 *
 * Sources cited
 * -------------
 *   1. Playwright TestOptions.viewport + Page.setViewportSize:
 *      https://playwright.dev/docs/api/class-testoptions
 *   2. Mapbox pixelmatch — https://github.com/mapbox/pixelmatch
 *   3. Playwright clock.install (deterministic time):
 *      https://playwright.dev/docs/clock
 */
import { test, expect, type ConsoleMessage, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  comparePickupPng,
  readPickupReference,
  type PickupPixelCompareResult,
} from "./w18-a10-pickup-pixel-compare";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
const MANIFEST_PATH = path.join(
  UI_ROOT,
  "tests",
  "visual-proof",
  "W18_A10_PICKUP_VISUAL_TARGET_MANIFEST.json",
);
const OBSERVED_DIR = path.join(UI_ROOT, "tests", "visual-proof", "observed-pickup");
const DIFFS_DIR = path.join(UI_ROOT, "tests", "visual-proof", "diffs-pickup");
const BASE_URL = process.env.LIVE_BASE_URL ?? "http://localhost:5173";
const DETERMINISTIC_TIME = new Date("2026-05-11T10:00:00.000Z");

interface ManifestTarget {
  id: string;
  reference: string;
  reference_size: { width: number; height: number };
  route: string;
  viewport: { width: number; height: number };
  theme: string;
  state: string;
  wait_test_id: string | null;
  compare_mode: "live" | "informational";
  tolerance: number;
  blocker?: string;
  notes: string;
}

interface ManifestFile {
  default_viewport: { width: number; height: number };
  default_theme: string;
  targets: ManifestTarget[];
  max_diff_pixel_ratio_default: number;
}

const MANIFEST = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf-8")) as ManifestFile;

function annotate(payload: Record<string, unknown>): void {
  test.info().annotations.push({
    type: "w18-a10-pickup",
    description: JSON.stringify(payload),
  });
}

function resolveRoute(route: string): string {
  if (!route.startsWith("/")) return route;
  return `${BASE_URL}${route}`;
}

async function waitForRouteSettled(
  page: Page,
  waitTestId: string | null,
  quietMs = 750,
): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  if (waitTestId) {
    try {
      await page.waitForSelector(`[data-testid="${waitTestId}"]`, {
        state: "visible",
        timeout: 30_000,
      });
    } catch (err) {
      // Fall back to the global dashboard-root anchor so the page settles
      // and we still capture an honest screenshot (the diff itself is the
      // signal — never recapture the baseline).
      await page.waitForSelector(`[data-testid="dashboard-root"]`, {
        state: "visible",
        timeout: 5_000,
      }).catch(() => {
        throw err;
      });
    }
  }
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
  });
  await page.waitForTimeout(quietMs);
}

function attachConsoleErrors(page: Page): { errors: string[] } {
  const errors: string[] = [];
  const handler = (msg: ConsoleMessage) => {
    if (msg.type() === "error") {
      errors.push(msg.text());
    }
  };
  page.on("console", handler);
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  return { errors };
}

async function pinTheme(page: Page, theme: string): Promise<void> {
  await page.addInitScript((t) => {
    try {
      window.localStorage.setItem("h3d.theme", t);
    } catch {
      // localStorage unavailable in some sandboxes.
    }
  }, theme);
}

async function pinClock(page: Page, at: Date): Promise<void> {
  try {
    await page.clock.install({ time: at });
  } catch {
    // Older Playwright builds without clock.install. Tolerance covers
    // a few seconds of date-time drift.
  }
}

for (const target of MANIFEST.targets) {
  test.describe(`w18-a10-pickup visual oracle: ${target.id}`, () => {
    test.use({ viewport: target.viewport });

    test(`${target.id} (${target.compare_mode})`, async ({ page }) => {
      const refAbs = path.join(REPO_ROOT, target.reference);
      if (!fs.existsSync(refAbs)) {
        throw new Error(`[w18-a10-pickup] reference PNG missing on disk: ${refAbs}`);
      }

      const consoleTracker = attachConsoleErrors(page);
      await pinTheme(page, target.theme ?? MANIFEST.default_theme);
      await pinClock(page, DETERMINISTIC_TIME);
      await page.setViewportSize(target.viewport);

      const url = resolveRoute(target.route);
      let navError: Error | null = null;
      try {
        await page.goto(url, { waitUntil: "domcontentloaded" });
        await waitForRouteSettled(page, target.wait_test_id);
      } catch (err) {
        navError = err as Error;
      }

      // Screenshot ALWAYS — even when navigation fails we want the diff
      // PNG vs the reference so the operator can see what went wrong.
      const observedBuffer = await page.screenshot({
        fullPage: false,
        animations: "disabled",
        caret: "hide",
        scale: "css",
      });

      const expectedBuffer = readPickupReference(refAbs);
      const cmp: PickupPixelCompareResult = comparePickupPng(
        expectedBuffer,
        observedBuffer,
        {
          threshold: 0.2,
          observedDir: OBSERVED_DIR,
          diffDir: DIFFS_DIR,
          artifactStem: target.id,
        },
      );

      const maxRatio = target.tolerance ?? MANIFEST.max_diff_pixel_ratio_default;
      const verdict =
        target.compare_mode === "live"
          ? cmp.diffRatio <= maxRatio
            ? "pass"
            : "diff"
          : "informational";

      annotate({
        target: target.id,
        compare_mode: target.compare_mode,
        verdict,
        ref: target.reference,
        route: target.route,
        viewport: target.viewport,
        theme: target.theme,
        state: target.state,
        expected_size: cmp.expected,
        observed_size: cmp.observed,
        diff_pixels: cmp.diffPixels,
        diff_ratio: cmp.diffRatio,
        max_diff_ratio: maxRatio,
        size_mismatch: cmp.sizeMismatch,
        observed_path: path.relative(REPO_ROOT, cmp.observedPath),
        diff_path: cmp.diffPath ? path.relative(REPO_ROOT, cmp.diffPath) : null,
        console_errors_count: consoleTracker.errors.length,
        console_errors_sample: consoleTracker.errors.slice(0, 5),
        nav_error: navError ? navError.message : null,
        blocker: target.blocker ?? null,
        notes: target.notes,
      });

      // For informational targets, the diff is documentation — the test
      // still PASSES so the harness can complete and the operator can
      // read the verdict table. The `blocker` field carries the precise
      // PARTIAL reason.
      if (target.compare_mode === "informational") {
        // Soft assertion: the test passes regardless of diff. We still
        // require navigation to NOT throw a fatal — if the route does
        // not exist the harness has bigger problems.
        if (navError) {
          throw navError;
        }
        return;
      }

      // Live targets: hard-fail on any console error (no filtering) and
      // hard-fail when diffRatio exceeds tolerance. The diff PNG path is
      // surfaced in the assertion message so the operator can see it
      // immediately when fixing the UI.
      if (navError) {
        throw navError;
      }
      if (consoleTracker.errors.length > 0) {
        throw new Error(
          `[w18-a10-pickup] ${target.id}: ${consoleTracker.errors.length} ` +
            `console errors. First: ${consoleTracker.errors[0]}`,
        );
      }

      expect(
        cmp.diffRatio,
        `[w18-a10-pickup] ${target.id} pixel diff ratio ${cmp.diffRatio.toFixed(4)} ` +
          `> tolerance ${maxRatio}. diffPixels=${cmp.diffPixels} ` +
          `expected=${cmp.expected.width}x${cmp.expected.height} ` +
          `observed=${cmp.observed.width}x${cmp.observed.height} ` +
          `sizeMismatch=${cmp.sizeMismatch} ref=${target.reference} ` +
          `diffPath=${cmp.diffPath ?? "(none)"}\n` +
          `FIX-IT RULE: fix the UI source to match Images-GUI/. Do NOT recapture the baseline.`,
      ).toBeLessThanOrEqual(maxRatio);
    });
  });
}
