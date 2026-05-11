/**
 * W6-6 / W8-14 / W15-A9 Playwright visual-oracle spec.
 *
 * W15-A9 implements 9 capabilities identified by W15-A5's gap analysis of
 * the W14 harness. Versus W14, every live target now runs through:
 *   1. Region crops — `target.regions[]` produces one screenshot per region.
 *   2. Per-target viewport — `target.viewport` selects a project; tests
 *      `test.use({ viewport })` so the assertion baseline matches.
 *   3. Console-error mandatory fail — strict, no allow-list.
 *   4. Network 404 fail — same-origin 4xx/5xx fail the test.
 *   5. No-fake DOM scan — innerText / data-* markers fail the test.
 *   6. Deterministic clock — `page.clock.install({ time })` + `pauseAt`.
 *   7. Theme determinism — `localStorage[h3d.theme]` stubbed via initScript.
 *   8. fonts.ready — awaited before every screenshot (full-page + regions).
 *   9. Region screenshots — `page.screenshot({ clip })` for collage refs.
 *
 * Test shape per live target:
 *   describe `visual: <target>`
 *     beforeEach:
 *       - addInitScript theme stub
 *       - install deterministic clock + pause at clock_time
 *       - attach console + 404 trackers
 *     test `matches reference within tolerance N`:
 *       - goto(route), wait for wait_test_id
 *       - waitForFontsReady, scanForFakeMarkers, drain console + 404
 *       - assert no fake markers, no console errors, no same-origin 4xx/5xx
 *       - if target.regions: loop screenshot({clip}) per region with its
 *         own toHaveScreenshot reference + tolerance
 *       - else: full-page toHaveScreenshot
 *
 * The reporter (visual-proof-reporter.ts) collects annotations emitted at
 * key milestones so the JSON summary contains region-level, network, and
 * console-error rows without needing extra Playwright wiring.
 *
 * Sources cited:
 *  1. Playwright clock.install / pauseAt:
 *     https://playwright.dev/docs/clock
 *  2. Chromatic / Percy visual-test harness recipe (regions + per-viewport
 *     projects + console-error + 404 gate + fonts.ready):
 *     https://www.chromatic.com/docs/visual-tests/
 *
 * No-fake / no-paid contract:
 *  - updateSnapshots is "none" at the config level; this spec never writes
 *    or auto-updates reference PNGs.
 *  - All gates are STRICT-by-default. There is no allow-list flag.
 *  - All network is local; no telemetry; no paid services.
 */
import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_THEME,
  DETERMINISTIC_TIME,
  attachConsoleErrorSink,
  installDeterministicClock,
  pauseClock,
  setLiveTheme,
  stubTheme,
  waitForFontsReady,
  type ConsoleErrorSink,
  type VisualRegion,
  type VisualTargetsFile,
} from "./_visual-helpers";
import { scanForFakeMarkers, summarizeFakeHits } from "./no-fake-scanner";
import {
  attachNetworkErrorTracker,
  summarizeNetworkErrors,
  type NetworkErrorTracker,
} from "./network-404-tracker";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TARGETS_PATH = path.join(HERE, "visual-targets.json");
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
// W8-14: refs are mirrored INSIDE the test root so snapshotPathTemplate
// "{arg}{ext}" resolves forward-only and Playwright accepts the path.
const REFS_LOCAL_ROOT = path.join(HERE, "__refs__");
const targetsFile = JSON.parse(fs.readFileSync(TARGETS_PATH, "utf-8")) as VisualTargetsFile;
const BASE_URL = "http://localhost:5173";

/**
 * Wait for SPA settle: domcontentloaded plus a quiet timeout. networkidle is
 * intentionally skipped — long-poll + SSE channels in the Hermes3D SPA never
 * idle within Playwright's 30s default. The wait_test_id assertion plus a
 * 500ms quiet period proves the route mounted (see W8-14 diagnosis).
 */
async function waitForStable(page: Page, quietMs = 500): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(quietMs);
}

/**
 * Build the snapshot-name array from a repo-relative reference path.
 * Returns segments relative to UI_ROOT so toHaveScreenshot resolves
 * forward-only into tests/visual/__refs__/.
 */
function snapshotPathSegments(referenceRepoRel: string): string[] {
  const subPath = referenceRepoRel.replace(/^Images-GUI[\\/]+/i, "");
  const referenceAbs = path.join(REFS_LOCAL_ROOT, subPath);
  const fromUiRoot = path.relative(UI_ROOT, referenceAbs);
  return fromUiRoot.split(/[\\/]+/);
}

/**
 * Build region snapshot segments: parent-directory + filename derived from
 * the original reference (stem) plus a `.<regionName>.png` suffix. The
 * resulting path lives next to the full-page reference inside __refs__/.
 */
function regionSnapshotSegments(referenceRepoRel: string, regionName: string): string[] {
  const subPath = referenceRepoRel.replace(/^Images-GUI[\\/]+/i, "");
  const dir = path.dirname(subPath);
  const base = path.basename(subPath, path.extname(subPath));
  const fileName = `${base}.${regionName}.png`;
  const referenceAbs = path.join(REFS_LOCAL_ROOT, dir, fileName);
  const fromUiRoot = path.relative(UI_ROOT, referenceAbs);
  return fromUiRoot.split(/[\\/]+/);
}

/**
 * Annotation helper — JSON-stringifies once and pushes onto the active test.
 * Keeping this in one place means the reporter always parses the same shape.
 */
function annotate(type: string, payload: Record<string, unknown>): void {
  test.info().annotations.push({
    type,
    description: JSON.stringify(payload),
  });
}

for (const target of targetsFile.targets) {
  const referenceAbs = path.resolve(REPO_ROOT, target.reference);

  // W18-A14 — no-skip harness contract: we MUST NOT declare a test and then
  // skip it. For `status: "future"` targets and for live targets whose
  // reference PNG has not yet been captured, continue past the
  // `test.describe(...)` declaration entirely. The visual-proof-reporter
  // injects synthesized rows for these targets in `onBegin` from the
  // manifest + on-disk reference check, so the JSON summary schema is
  // preserved without producing skipped Playwright tests.
  if (target.status === "future") {
    continue;
  }
  if (!fs.existsSync(referenceAbs)) {
    continue;
  }

  // W16-A — Effective viewport resolved per-target, falling back to the
  // manifest's top-level default when no override is declared. Computed once
  // so test.use, the annotation, and the in-body page.setViewportSize all
  // agree on the same shape (the per-target reference PNG's dimensions).
  const effectiveViewport: { width: number; height: number } =
    target.viewport &&
    Number.isFinite(target.viewport.width) &&
    Number.isFinite(target.viewport.height)
      ? { width: target.viewport.width, height: target.viewport.height }
      : {
          width: targetsFile.viewport?.width ?? 1536,
          height: targetsFile.viewport?.height ?? 1024,
        };

  test.describe(`visual: ${target.target}`, () => {
    // W15-A9 cap 2 + W16-A fix — pin EVERY test to its effective viewport.
    //
    // Previously this guard was conditional on `target.viewport` being set,
    // which meant the 2 dim-outlier targets (1672x941, 1586x992) were the
    // only ones overriding viewport. With multiple Playwright projects in
    // play (one per unique manifest viewport), every test runs in EVERY
    // project by default — so a non-override target like
    // `04_source_os_core_categories` (baseline 1536x1024) would render at
    // 1586x992 when it ran inside the `visual-chromium-1586x992` project
    // and fail with "Expected an image 1536px by 1024px, received
    // 1586px by 992px". Making `test.use({ viewport })` unconditional pins
    // the browser-context viewport to the target's declared shape
    // regardless of which project picked up the test (W15-FINAL-4 A21
    // 22-LIVE-row regression).
    //
    // `test.use({ viewport })` propagates to the underlying browser context,
    // see Playwright docs:
    //   https://playwright.dev/docs/api/class-testoptions#test-options-viewport
    test.use({ viewport: effectiveViewport });

    // W18-A14 — `status: "future"` targets and live targets whose reference
    // PNG has not yet been captured are filtered out BEFORE this describe
    // block runs (see the `continue` statements in the enclosing for-loop).
    // The visual-proof-reporter synthesizes their rows in `onBegin` so the
    // JSON summary schema stays additive. No test is declared and then
    // skipped — a skipped test is a fail under the W18-A14 no-skip harness.

    // Per-test state — kept outside the test body so beforeEach can populate
    // it and the assertion block can drain it.
    let consoleSink: ConsoleErrorSink;
    let networkTracker: NetworkErrorTracker;

    test.beforeEach(async ({ page }) => {
      // W15-A9 cap 7 — theme determinism via initScript BEFORE first paint.
      await stubTheme(page, target.theme ?? DEFAULT_THEME);
      // W15-A9 cap 6 — deterministic clock pinned at target.clock_time or
      // DETERMINISTIC_TIME. Installed BEFORE navigation so Date(), timers,
      // and requestAnimationFrame are already frozen on first paint.
      await installDeterministicClock(page, target.clock_time ?? DETERMINISTIC_TIME);
      // W15-A9 cap 3 + 4 — strict console + same-origin 4xx/5xx trackers.
      consoleSink = attachConsoleErrorSink(page);
      networkTracker = attachNetworkErrorTracker(page, { baseURL: BASE_URL });
    });

    test(`matches reference within tolerance ${target.tolerance}`, async ({ page }) => {
      annotate("visual-proof-target", {
        target: target.target,
        reference: target.reference,
        route: target.route,
        tolerance: target.tolerance,
        viewport: effectiveViewport,
        theme: target.theme ?? DEFAULT_THEME,
        clock_time: target.clock_time ?? DETERMINISTIC_TIME,
        regions: (target.regions ?? []).map((r: VisualRegion) => r.name),
      });

      // W16-A — defense-in-depth viewport pin. test.use({ viewport })
      // creates the context at the requested shape, but a stray
      // page.setViewportSize earlier in the run, or a project-level resize
      // hook, could leave the live page at a different size by the time we
      // navigate. Re-pinning RIGHT before goto guarantees the rendered DOM
      // for the screenshot matches the reference PNG's dimensions.
      // Source: https://playwright.dev/docs/api/class-page#page-set-viewport-size
      await page.setViewportSize(effectiveViewport);

      await page.goto(target.route);
      // Re-assert theme post-navigation in case the SPA cleared LS during
      // boot. Cheap and idempotent — see _visual-helpers.setLiveTheme.
      await setLiveTheme(page, target.theme ?? DEFAULT_THEME);

      if (target.wait_test_id) {
        await expect(
          page.getByTestId(target.wait_test_id),
          `${target.target} wait_test_id ${target.wait_test_id} mounts`,
        ).toBeVisible({ timeout: 15_000 });
      }
      await waitForStable(page, 500);
      // W15-A9 cap 8 — wait for fonts.ready + a single rAF tick to flush.
      await waitForFontsReady(page);

      // W15-A9 cap 5 — DOM no-fake scan. Drain hits and annotate; the
      // assertion below fails the test if any landed.
      const fakeHits = await scanForFakeMarkers(page);
      annotate("visual-proof-no-fake", {
        target: target.target,
        hits: fakeHits.length,
        summary: summarizeFakeHits(fakeHits),
      });
      expect(
        fakeHits,
        `${target.target} must not contain fake/mock DOM markers. Hits: ${summarizeFakeHits(fakeHits)}`,
      ).toHaveLength(0);

      // W15-A9 cap 4 — same-origin 4xx/5xx fail. We drain BEFORE the
      // screenshot so the actual screenshot does not itself trigger a 4xx
      // (e.g. a missing icon) AFTER our gate.
      const sameOriginErrors = networkTracker.sameOriginErrors();
      annotate("visual-proof-network", {
        target: target.target,
        same_origin_errors: sameOriginErrors.length,
        total_errors: networkTracker.errors.length,
        summary: summarizeNetworkErrors(sameOriginErrors),
      });
      expect(
        sameOriginErrors,
        `${target.target} must not produce same-origin 4xx/5xx. Errors: ${summarizeNetworkErrors(sameOriginErrors)}`,
      ).toHaveLength(0);

      // W15-A9 cap 3 — strict console-error gate. STRICT: no allow-list.
      annotate("visual-proof-console", {
        target: target.target,
        errors: consoleSink.errors.length,
        summary: consoleSink.errors.map((e) => e.text).slice(0, 5).join(" | "),
      });
      expect(
        consoleSink.errors,
        `${target.target} must not log console.errors or unhandled page errors. Errors: ${consoleSink.errors.map((e) => e.text).join(" | ")}`,
      ).toHaveLength(0);

      // W15-A9 cap 6 (phase 2) — pause the clock RIGHT before screenshot.
      // Installing in beforeEach pinned Date.now() for the page boot; pausing
      // here freezes timer-driven animations for the actual frame capture.
      await pauseClock(page, target.clock_time ?? DETERMINISTIC_TIME);

      // W15-A9 caps 1 + 9 — region screenshots. If the manifest lists
      // regions, each one produces its own toHaveScreenshot diff against
      // a per-region reference. Otherwise we fall back to full-page.
      const regions = target.regions ?? [];
      if (regions.length > 0) {
        for (const region of regions) {
          const regionReference = region.reference ?? target.reference;
          const regionTolerance = region.tolerance ?? target.tolerance;
          const segments = regionSnapshotSegments(regionReference, region.name);
          await expect(page).toHaveScreenshot(segments, {
            animations: "disabled",
            maxDiffPixelRatio: regionTolerance,
            clip: region.clip,
          });
          annotate("visual-proof-region-result", {
            target: target.target,
            region: region.name,
            status: "match",
            tolerance: regionTolerance,
            clip: region.clip,
          });
        }
      } else {
        const segments = snapshotPathSegments(target.reference);
        await expect(page).toHaveScreenshot(segments, {
          fullPage: true,
          animations: "disabled",
          maxDiffPixelRatio: target.tolerance,
        });
      }

      // Final success annotation. The reporter uses this to classify the
      // row as "match"; absence (i.e. an assertion threw earlier) yields
      // "diff" / "missing-baseline" / "error".
      annotate("visual-proof-result", {
        target: target.target,
        status: "match",
        tolerance: target.tolerance,
        regions: regions.length,
      });
    });
  });
}
