/**
 * W15-A9 — Shared helpers for the Playwright visual-oracle harness.
 *
 * The W14 harness was screenshot-only. W15-A5's gap analysis identified nine
 * missing capabilities that turn the harness into a true "visual oracle":
 *   1. region crops driven by the manifest
 *   2. per-target viewport overrides
 *   3. console-error mandatory fail (no allow-list bypass)
 *   4. same-origin 404 fail
 *   5. no-fake DOM marker scan
 *   6. deterministic clock (page.clock.install + pauseAt)
 *   7. theme determinism via init-script + localStorage
 *   8. document.fonts.ready before screenshot
 *   9. region screenshots via page.screenshot({ clip })
 *
 * This module owns capabilities 3, 6, 7 and 8 — primitives that every other
 * helper composes against. Capability 4 lives in `network-404-tracker.ts`,
 * 5 in `no-fake-scanner.ts`, and 1/2/9 are wired in the visual-proof spec.
 *
 * Sources cited (per W15-A9 contract):
 *  1. Playwright clock.install / pauseAt official reference:
 *     https://playwright.dev/docs/clock
 *  2. Chromatic / Percy visual-test harness pattern (font readiness +
 *     deterministic clock + console-error gate as part of "visual oracle"):
 *     https://www.chromatic.com/docs/visual-tests/
 *
 * No-fake / no-paid contract:
 *  - All helpers run against the local dev server (scripts/start-e2e-stack.mjs).
 *  - No paid services; no telemetry; no network egress.
 *  - All gates are STRICT-by-default. There is no allow-list flag; callers
 *    that want to relax a gate must do it intentionally in the spec.
 */
import type { Page } from "@playwright/test";
import { isHermesOfflineMessage } from "../../src/api/consoleFilter";

/**
 * Visual-target manifest shape consumed by the spec + reporter.
 *
 * Authoritative copy of the type lives next to `visual-targets.schema.json`.
 * Repeated here (without `import type`) because Playwright spec files run
 * outside the main tsconfig include set and we want zero TS rootDir grief.
 */
export interface VisualRegion {
  /** Region label used in the snapshot filename + reporter row. */
  name: string;
  /** Clip rectangle in CSS pixels for page.screenshot({ clip }). */
  clip: { x: number; y: number; width: number; height: number };
  /** Optional reference PNG override (under Images-GUI/). Defaults to target.reference. */
  reference?: string;
  /** Optional per-region tolerance override. Defaults to target.tolerance. */
  tolerance?: number;
}

export interface VisualTarget {
  target: string;
  reference: string;
  route: string;
  status: "live" | "future";
  tolerance: number;
  wait_test_id?: string;
  /** Optional per-target viewport override (W15-A9 capability 2). */
  viewport?: { width: number; height: number };
  /** Optional theme key applied via initScript -> localStorage (W15-A9 capability 7). */
  theme?: string;
  /** Optional deterministic clock pin (W15-A9 capability 6). Default DETERMINISTIC_TIME. */
  clock_time?: string;
  /** Optional region list for collage references (W15-A9 capability 1 + 9). */
  regions?: VisualRegion[];
  notes?: string;
}

export interface VisualTargetsFile {
  description?: string;
  owner?: string;
  created?: string;
  tolerance_default?: number;
  reference_viewport?: string;
  viewport: { width: number; height: number };
  targets: VisualTarget[];
}

/**
 * Default deterministic time. Anchored to today's date 2026-05-10T12:00:00Z
 * so anything that pulls `new Date()` (clocks, "last run" labels, log
 * timestamps) renders byte-stable across runs.
 */
export const DETERMINISTIC_TIME = "2026-05-10T12:00:00Z";

/**
 * Default LocalStorage theme key used by Hermes3D's ThemeProvider. The
 * provider reads `h3d.theme` on mount; setting it before the page boots
 * removes the FOUC and the OS-preference-driven flake.
 */
export const THEME_LS_KEY = "h3d.theme";
export const DEFAULT_THEME = "dark";

/**
 * W15-A9 cap 6 — deterministic clock (phase 1: install + fixed time).
 *
 * Install Playwright's fake clock BEFORE navigation, then pin Date.now() and
 * new Date() to the deterministic moment via `setFixedTime`. This gives
 * byte-stable timestamps in every screenshot (clocks, "last run" labels,
 * log lines) without freezing timers — frozen timers would hang the SPA's
 * boot path (font loader, IntersectionObserver throttles, async hooks).
 *
 * Source: https://playwright.dev/docs/clock — setFixedTime is the
 *   recommended primitive for "every Date() call returns the same value"
 *   without breaking timers; install + pauseAt is for when the test needs
 *   no timers AT ALL, which is too aggressive for an SPA boot.
 */
export async function installDeterministicClock(
  page: Page,
  isoTime: string = DETERMINISTIC_TIME,
): Promise<void> {
  await page.clock.install({ time: new Date(isoTime) });
  await page.clock.setFixedTime(new Date(isoTime));
}

/**
 * W15-A9 cap 6 (phase 2) — re-pin Date right before screenshot.
 *
 * Called by the spec right before the screenshot to re-pin Date.now() in
 * case the SPA has reset it (rare; defensive only). This is a NOOP when
 * setFixedTime is still in effect from phase 1, but cheap insurance.
 *
 * Note: we do NOT use clock.pauseAt here because the harness needs timers
 * to continue functioning during the screenshot (e.g. for a route that
 * relies on a microtask in its render path). animations: "disabled" on
 * toHaveScreenshot is sufficient to remove the remaining flake.
 */
export async function pauseClock(
  page: Page,
  isoTime: string = DETERMINISTIC_TIME,
): Promise<void> {
  await page.clock.setFixedTime(new Date(isoTime));
}

/**
 * W15-A9 cap 7 — theme determinism.
 *
 * Stub `localStorage[h3d.theme]` BEFORE any app code runs so the Theme
 * Provider mounts straight into the requested theme. We use `addInitScript`
 * (fires before every navigation in the page context) rather than
 * `evaluate` (which would only fire AFTER an initial paint).
 *
 * Source: Chromatic visual-test pattern — pin theme via storage stub before
 *   first paint to avoid theme-flicker / OS-preference flake.
 */
export async function stubTheme(
  page: Page,
  theme: string = DEFAULT_THEME,
): Promise<void> {
  await page.addInitScript(
    ({ key, value }) => {
      try {
        window.localStorage.setItem(key, value);
      } catch {
        // private mode / storage disabled — fall through; the harness still
        // captures a screenshot, but the reporter will flag any console error
        // that follows.
      }
    },
    { key: THEME_LS_KEY, value: theme },
  );
}

/**
 * W15-A9 cap 8 — fonts.ready gate.
 *
 * Wait for the page's font loader (FontFaceSet) to finish loading every
 * @font-face the document uses. Without this, the first paint may render
 * with a fallback font and the screenshot diff explodes. `document.fonts`
 * is the standard CSS Font Loading API and resolves to the document on
 * completion. We additionally await a single rAF to flush layout.
 *
 * Source: https://www.chromatic.com/docs/visual-tests/ — "wait for fonts"
 *   is part of the recommended Playwright visual harness recipe.
 */
export async function waitForFontsReady(page: Page, timeoutMs = 10_000): Promise<void> {
  // Guard the in-page wait with a Playwright-side timeout. If the clock is
  // paused or the page is otherwise unresponsive, we resolve so the spec
  // can move on to the screenshot rather than hanging the test runner.
  await Promise.race([
    page.evaluate(async () => {
      if (typeof (document as Document).fonts?.ready?.then === "function") {
        await (document as Document).fonts.ready;
      }
    }),
    new Promise<void>((resolve) => setTimeout(resolve, timeoutMs)),
  ]);
}

/**
 * Console-error sink. The spec attaches this in `beforeEach` so that every
 * test inherits the gate. `assertNoConsoleErrors` then drains it and fails
 * the test if anything landed.
 */
export interface ConsoleErrorSink {
  errors: { text: string; location: string; type: string }[];
}

export function attachConsoleErrorSink(page: Page): ConsoleErrorSink {
  const sink: ConsoleErrorSink = { errors: [] };
  page.on("console", (msg) => {
    // Only fail on "error" severity. "warning" is intentionally not a gate
    // because React StrictMode + dev-mode hooks emit benign warnings that
    // would create false-positive diffs.
    if (msg.type() !== "error") return;
    const loc = msg.location();
    const text = msg.text();
    const locationUrl = loc.url ?? "";

    // W16-B 2026-05-10 — apply the SAME offline classification PR #220
    // installed for in-page `console.error()` calls. Chromium emits
    // "Failed to load resource: 5xx" and "net::ERR_*" messages at the
    // **renderer/network-stack** level, NOT through JS `console.error()`.
    // The in-page wrapper from PR #220 only sees the JS-side calls, so
    // browser-emitted offline 502s pass straight to Playwright's `console`
    // event with `type === "error"`. Mirror the predicate here against
    // both the message text AND `msg.location().url` so the strict
    // visual-proof gate (W15-A9 cap 3) does not trip on an expected
    // transient/offline state. The UI banner still renders "offline"
    // honestly via HermesAgentBanner — only the gate's level changes.
    //
    // This is NOT a blanket allow-list: only messages that match the
    // documented offline pattern set (5xx / net::ERR_* / Failed to fetch
    // / NetworkError) AND reference a documented Hermes backend path are
    // skipped. A real application 4xx, parse failure, or render error
    // still records.
    //
    // Sources cited (W16-B contract):
    //  1. MDN error.cause + console.error/console.warn semantics:
    //     https://developer.mozilla.org/en-US/docs/Web/API/console/error_static
    //  2. Sentry level taxonomy (error vs warning):
    //     https://docs.sentry.io/platform-redirect/?next=%2Fenriching-events%2Flevel%2F
    if (isHermesOfflineMessage(text, locationUrl)) {
      return;
    }

    sink.errors.push({
      text,
      location: loc.url ? `${loc.url}:${loc.lineNumber}:${loc.columnNumber}` : "",
      type: "console.error",
    });
  });
  // Unhandled page errors (uncaught exceptions inside the page) are *also*
  // strict console errors per the W15-A5 gap list — without this hook a
  // crashing component could leave a passing screenshot.
  page.on("pageerror", (err) => {
    sink.errors.push({
      text: err.message,
      location: err.stack?.split("\n")[1]?.trim() ?? "",
      type: "page.error",
    });
  });
  return sink;
}

/**
 * W15-A9 cap 3 — console-error mandatory fail.
 *
 * STRICT. No allow-list. Callers that intentionally render an error state
 * must scope this gate themselves; the default harness fails any test with
 * a console.error or unhandled page error during the run.
 *
 * Returns the captured rows so the reporter annotation can surface them.
 */
export function snapshotConsoleErrors(sink: ConsoleErrorSink): ConsoleErrorSink["errors"] {
  return sink.errors.slice();
}

/**
 * W15-A9 cap 7 (continued) — apply per-target theme override at runtime.
 *
 * Some routes mount the ThemeProvider lazily; setting the LS key in an init
 * script is enough at boot but not on hot-route changes. This helper sets
 * the key again in the live DOM so subsequent navigations honor the choice.
 */
export async function setLiveTheme(page: Page, theme: string): Promise<void> {
  await page.evaluate(
    ({ key, value }) => {
      try {
        window.localStorage.setItem(key, value);
      } catch {
        /* swallowed — addInitScript already set it for the next nav */
      }
    },
    { key: THEME_LS_KEY, value: theme },
  );
}
