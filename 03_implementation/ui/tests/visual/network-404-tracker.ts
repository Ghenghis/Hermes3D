/**
 * W15-A9 cap 4 — same-origin 404 network tracker.
 *
 * Subscribes to Playwright's `response` event for the page and records
 * every same-origin 4xx/5xx response. The visual-proof spec inspects this
 * after each screenshot and fails the test if any same-origin 404 (or
 * other 4xx/5xx) was seen — a missing JS chunk, a missing icon, or a
 * broken API endpoint will all surface here regardless of whether the
 * page swallowed the error.
 *
 * Cross-origin failures are recorded but NOT failed by default; many UIs
 * legitimately fan out to third-party assets (fonts.googleapis, CDN sprites)
 * that we cannot guarantee. Callers that want strict cross-origin failure
 * pass `{ crossOriginIsStrict: true }`.
 *
 * No-fake / no-paid contract:
 *  - Tracker is in-process; no telemetry; no remote sink.
 *  - Only the URL, status, and method are recorded. No headers, no bodies.
 *
 * Sources cited:
 *  1. Playwright Page.on('response') reference:
 *     https://playwright.dev/docs/api/class-page#page-event-response
 *  2. Chromatic visual-test pattern — same-origin 404 is a mandatory gate
 *     in the "visual oracle" recipe:
 *     https://www.chromatic.com/docs/visual-tests/
 */
import type { Page } from "@playwright/test";

export interface NetworkErrorEvent {
  /** Full URL (no querystring trimming). */
  url: string;
  /** HTTP status code (always 400+). */
  status: number;
  /** HTTP method. */
  method: string;
  /** Whether the URL was same-origin as the page's baseURL. */
  same_origin: boolean;
}

export interface NetworkErrorTracker {
  /** Every recorded 4xx/5xx, regardless of origin. */
  errors: NetworkErrorEvent[];
  /** Convenience filter for the strict gate. */
  sameOriginErrors(): NetworkErrorEvent[];
}

export interface NetworkTrackerOptions {
  /** Page's baseURL, used to classify same-origin vs cross-origin. */
  baseURL?: string;
  /**
   * If true, cross-origin 4xx/5xx are ALSO recorded as same-origin so the
   * spec gate treats them as failures. Default false.
   */
  crossOriginIsStrict?: boolean;
}

/**
 * Compare two URLs by origin (scheme + host + port). Returns false on any
 * parse failure so opaque URLs do not accidentally trip the strict gate.
 */
function isSameOrigin(target: string, baseURL: string | undefined): boolean {
  if (!baseURL) return false;
  try {
    const a = new URL(target);
    const b = new URL(baseURL);
    return a.origin === b.origin;
  } catch {
    return false;
  }
}

/**
 * Attach a 4xx/5xx response listener to a Page. Returns the tracker; the
 * caller is responsible for draining `errors` after each test.
 */
export function attachNetworkErrorTracker(
  page: Page,
  opts: NetworkTrackerOptions = {},
): NetworkErrorTracker {
  const baseURL = opts.baseURL ?? "";
  const strictCrossOrigin = Boolean(opts.crossOriginIsStrict);
  const tracker: NetworkErrorTracker = {
    errors: [],
    sameOriginErrors(): NetworkErrorEvent[] {
      return tracker.errors.filter((e) => e.same_origin);
    },
  };

  page.on("response", (response) => {
    const status = response.status();
    if (status < 400) return;
    const url = response.url();
    const method = response.request().method();
    // Skip data: URLs and blob: URLs — these are in-page constructs, not
    // server responses. Same-origin classification would be meaningless.
    if (/^(data|blob):/i.test(url)) return;
    const sameOrigin = isSameOrigin(url, baseURL);
    tracker.errors.push({
      url,
      status,
      method,
      same_origin: sameOrigin || strictCrossOrigin,
    });
  });

  return tracker;
}

/**
 * Render a stable, deduped summary string for an annotation payload.
 * Errors are sorted by (status, url) and capped at 20.
 */
export function summarizeNetworkErrors(errors: NetworkErrorEvent[]): string {
  if (errors.length === 0) return "";
  const sorted = errors
    .slice()
    .sort((a, b) => (a.status === b.status ? a.url.localeCompare(b.url) : a.status - b.status))
    .slice(0, 20);
  return sorted.map((e) => `${e.status} ${e.method} ${e.url}`).join(" | ");
}
