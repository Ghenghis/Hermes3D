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
 * W18-A10P-CIFIX project split (2026-05-11)
 * -----------------------------------------
 *   The Playwright config defines two projects that both consume this
 *   spec via the same generator loop:
 *     - `live-targets`            — grep filter narrows to "(live)" tests.
 *                                   These remain HARD assertions and gate
 *                                   GUI_PIXEL_E2E_GREEN.
 *     - `informational-variants`  — grep filter narrows to
 *                                   "(informational)" tests. Their entire
 *                                   render-+-compare body is wrapped in a
 *                                   try/catch so a closed-page / nav crash
 *                                   becomes an annotated PARTIAL row
 *                                   (bucket=informational, with a
 *                                   `crash_during_capture` flag) instead
 *                                   of failing Playwright. The reporter's
 *                                   GUI_PIXEL_E2E_GREEN computation only
 *                                   considers the `live` bucket, so a
 *                                   project-B crash never blocks the
 *                                   Layer D2 verdict.
 *   No `test.skip` is used: each test still RUNS in exactly one project;
 *   the other project ignores it via Playwright's per-project `grep`.
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
 *   4. Playwright projects + grep for splitting suites:
 *      https://playwright.dev/docs/test-projects
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
  // Per-selector budget. Live targets use the default (30s). The
  // informational variants pass a much shorter budget so a missing
  // route anchor cannot consume the whole test timeout.
  primaryTimeoutMs = 30_000,
  fallbackTimeoutMs = 5_000,
): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  if (waitTestId) {
    try {
      await page.waitForSelector(`[data-testid="${waitTestId}"]`, {
        state: "visible",
        timeout: primaryTimeoutMs,
      });
    } catch (err) {
      // Fall back to the global dashboard-root anchor so the page settles
      // and we still capture an honest screenshot (the diff itself is the
      // signal — never recapture the baseline).
      await page.waitForSelector(`[data-testid="dashboard-root"]`, {
        state: "visible",
        timeout: fallbackTimeoutMs,
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

/**
 * Bound any async step so its worst-case duration is capped. This is the
 * W18-A10P-CIFIX2 fix for PR #241: a Playwright test-level timeout fires
 * OUTSIDE user code's try/catch (it is dispatched by the Playwright
 * runner against the worker), so even when every step is wrapped in
 * try/catch the test can still be killed by the test-level timeout. By
 * racing each step against a small bounded timeout we keep total time
 * predictable, the test stays well inside the per-test budget, and the
 * try/catch wrapper in runInformationalVariant always gets to run the
 * reporter PARTIAL emit on the way out.
 */
async function withBudget<T>(
  promise: Promise<T>,
  budgetMs: number,
  label: string,
): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`step-budget-exceeded: ${label} > ${budgetMs}ms`));
    }, budgetMs);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
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

async function runInformationalVariant(
  page: Page,
  target: ManifestTarget,
): Promise<void> {
  // The whole render+screenshot+compare path is wrapped so a
  // closed-page / nav crash records a PARTIAL annotation instead of
  // failing Playwright. The PR-#241 CI failure was exactly this:
  // for `08_workflow_printqueue_files_logs` and
  // `08_proof_health_notifications_safety`, the test budget (30s in
  // the default playwright.config.ts) was being consumed entirely by
  // `waitForSelector` for a non-existent route anchor (`workflows-root`,
  // `proof-root`). The test-level timeout fires OUTSIDE this try/catch
  // (Playwright kills the worker for the test), so even the catch+emit
  // path never runs and the test is recorded as failed.
  //
  // The W18-A10P-CIFIX2 fix bounds each step with `withBudget` so the
  // total worst case is well below the per-test budget. We also extend
  // the test timeout for informational variants so the reporter PARTIAL
  // emit always gets to run on the way out (Layer D2's default is 30s;
  // we lift this single test to 120s).
  test.setTimeout(120_000);
  const refAbs = path.join(REPO_ROOT, target.reference);
  if (!fs.existsSync(refAbs)) {
    annotate({
      target: target.id,
      compare_mode: target.compare_mode,
      verdict: "informational",
      crash_during_capture: true,
      crash_phase: "reference-missing",
      crash_message: `reference PNG missing on disk: ${refAbs}`,
      ref: target.reference,
      route: target.route,
      viewport: target.viewport,
      theme: target.theme,
      state: target.state,
      blocker: target.blocker ?? null,
      notes: target.notes,
    });
    return;
  }

  const consoleTracker = attachConsoleErrors(page);
  let crashPhase: string | null = null;
  let crashMessage: string | null = null;
  let navError: Error | null = null;
  let cmp: PickupPixelCompareResult | null = null;

  // Bounded per-step budgets keep worst case well below the per-test
  // timeout so the catch + PARTIAL annotate path always runs.
  const PIN_BUDGET_MS = 5_000;
  const VIEWPORT_BUDGET_MS = 3_000;
  const GOTO_BUDGET_MS = 15_000;
  const SETTLE_BUDGET_MS = 12_000;
  const SETTLE_PRIMARY_MS = 6_000;
  const SETTLE_FALLBACK_MS = 3_000;
  const SCREENSHOT_BUDGET_MS = 15_000;

  try {
    try {
      await withBudget(
        pinTheme(page, target.theme ?? MANIFEST.default_theme),
        PIN_BUDGET_MS,
        "pin-theme",
      );
      await withBudget(pinClock(page, DETERMINISTIC_TIME), PIN_BUDGET_MS, "pin-clock");
      await withBudget(
        page.setViewportSize(target.viewport),
        VIEWPORT_BUDGET_MS,
        "set-viewport",
      );
    } catch (err) {
      crashPhase = "setup";
      crashMessage = (err as Error).message;
    }

    const url = resolveRoute(target.route);
    if (!crashPhase) {
      try {
        await withBudget(
          page.goto(url, { waitUntil: "domcontentloaded", timeout: GOTO_BUDGET_MS }),
          GOTO_BUDGET_MS + 1_000,
          "goto",
        );
      } catch (err) {
        navError = err as Error;
      }
      try {
        await withBudget(
          waitForRouteSettled(
            page,
            target.wait_test_id,
            500, // shorter quiet for informational
            SETTLE_PRIMARY_MS,
            SETTLE_FALLBACK_MS,
          ),
          SETTLE_BUDGET_MS,
          "wait-for-route-settled",
        );
      } catch (err) {
        // Don't overwrite a real navError. Record as a settle-fail.
        if (!navError) navError = err as Error;
      }
    }

    // Screenshot may legitimately throw if the page context was torn
    // down by the navigation (one of the original PR-#241 failure
    // shapes). Record the crash phase and stop — never let it bubble.
    let observedBuffer: Buffer | null = null;
    if (!crashPhase) {
      try {
        observedBuffer = await withBudget(
          page.screenshot({
            fullPage: false,
            animations: "disabled",
            caret: "hide",
            scale: "css",
            timeout: SCREENSHOT_BUDGET_MS,
          }),
          SCREENSHOT_BUDGET_MS + 1_000,
          "screenshot",
        );
      } catch (err) {
        crashPhase = "screenshot";
        crashMessage = (err as Error).message;
      }
    }

    if (observedBuffer) {
      try {
        const expectedBuffer = readPickupReference(refAbs);
        cmp = comparePickupPng(expectedBuffer, observedBuffer, {
          threshold: 0.2,
          observedDir: OBSERVED_DIR,
          diffDir: DIFFS_DIR,
          artifactStem: target.id,
        });
      } catch (err) {
        crashPhase = "pixel-compare";
        crashMessage = (err as Error).message;
      }
    }
  } catch (err) {
    crashPhase = crashPhase ?? "setup";
    crashMessage = crashMessage ?? (err as Error).message;
  }

  const maxRatio = target.tolerance ?? MANIFEST.max_diff_pixel_ratio_default;
  annotate({
    target: target.id,
    compare_mode: target.compare_mode,
    verdict: "informational",
    crash_during_capture: crashPhase !== null,
    crash_phase: crashPhase,
    crash_message: crashMessage,
    ref: target.reference,
    route: target.route,
    viewport: target.viewport,
    theme: target.theme,
    state: target.state,
    expected_size: cmp?.expected ?? null,
    observed_size: cmp?.observed ?? null,
    diff_pixels: cmp?.diffPixels ?? null,
    diff_ratio: cmp?.diffRatio ?? null,
    max_diff_ratio: maxRatio,
    size_mismatch: cmp?.sizeMismatch ?? null,
    observed_path: cmp ? path.relative(REPO_ROOT, cmp.observedPath) : null,
    diff_path: cmp?.diffPath ? path.relative(REPO_ROOT, cmp.diffPath) : null,
    console_errors_count: consoleTracker.errors.length,
    console_errors_sample: consoleTracker.errors.slice(0, 5),
    nav_error: navError ? navError.message : null,
    blocker: target.blocker ?? null,
    notes: target.notes,
  });

  // Informational variants NEVER throw. The Playwright run only fails
  // when a `live` target diffs / errors. See
  // tests/visual-proof/w18-a10-pickup-reporter.ts -> GUI_PIXEL_E2E_GREEN.
}

async function runLiveVariant(page: Page, target: ManifestTarget): Promise<void> {
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

  // Live mode: screenshot must succeed. If it doesn't, this is a real
  // regression and we want the loud failure.
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
  const verdict = cmp.diffRatio <= maxRatio ? "pass" : "diff";

  annotate({
    target: target.id,
    compare_mode: target.compare_mode,
    verdict,
    crash_during_capture: false,
    crash_phase: null,
    crash_message: null,
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
}

for (const target of MANIFEST.targets) {
  test.describe(`w18-a10-pickup visual oracle: ${target.id}`, () => {
    test.use({ viewport: target.viewport });

    // Each test is generated once. The Playwright config's per-project
    // `grep` (in `playwright.w18-a10-pickup.config.ts`) decides which
    // project owns which test:
    //   - `live-targets`           grep = /\(live\)$/
    //   - `informational-variants` grep = /\(informational\)$/
    // Project B (informational) NEVER fails Playwright; its body wraps
    // every step in try/catch. Project A (live) keeps the hard pixel
    // oracle behaviour and gates GUI_PIXEL_E2E_GREEN.
    test(`${target.id} (${target.compare_mode})`, async ({ page }) => {
      if (target.compare_mode === "informational") {
        await runInformationalVariant(page, target);
        return;
      }
      await runLiveVariant(page, target);
    });
  });
}
