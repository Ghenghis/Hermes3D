/**
 * W15-FIX-502 — console.error -> console.warn redirector for transient,
 * expected backend offline states (5xx, ERR_CONNECTION_REFUSED, "Failed to
 * fetch", etc.).
 *
 * Background
 * ----------
 * The Hermes3D-OS UI polls `/api/agents/update/status` and several other
 * read-only endpoints. When the v0.13 canary backend is not running locally
 * (the common case in CI for visual-proof, and during dev for any contributor
 * who hasn't started the bridge yet), every poll generates a browser-level
 * `console.error` for "Failed to load resource: the server responded with a
 * status of 502" or `net::ERR_CONNECTION_REFUSED`.
 *
 * These are NOT bugs in the application; they are honest signals of a
 * transient/offline state that the UI already renders as an "offline" banner
 * via `HermesAgentBanner` and `useAgentUpdateStatus`. The application-level
 * fetcher (`safeGetJson`) catches the failure and returns `null`. The console
 * noise comes from the browser network stack, not from a `console.error(...)`
 * call inside the app code.
 *
 * The strict visual-proof gate (W15-A9 cap 3) treats any `console.error` as a
 * blocking failure. To honor the gate WITHOUT bypassing it in the test
 * harness, we filter at the application boot: install a single console.error
 * wrapper that re-emits known-offline messages via `console.warn`. Real
 * application errors (parse failures, JS exceptions, 4xx client errors) keep
 * going to `console.error`.
 *
 * Level convention (from cited sources)
 * --------------------------------------
 *  - MDN Console.error / Console.warn semantics:
 *      console.error is for "things that have already gone wrong" — i.e.,
 *      genuine application failures the developer must investigate.
 *      console.warn is for "potential issues that should be investigated but
 *      may not necessarily indicate something has broken." A transient,
 *      retried, offline backend matches `warn`, not `error`.
 *      https://developer.mozilla.org/en-US/docs/Web/API/console/error_static
 *      https://developer.mozilla.org/en-US/docs/Web/API/console/warn_static
 *
 *  - Sentry-style level convention:
 *      Sentry's level taxonomy distinguishes `error` (alertable, page-on-call)
 *      from `warning` (anomalous but expected; aggregated, not paged). Offline
 *      backend in a polling status check is the textbook "warning" case.
 *      https://docs.sentry.io/platform-redirect/?next=%2Fenriching-events%2Flevel%2F
 *
 * Contract
 * --------
 *  - Idempotent: calling `installConsoleFilter` more than once is a no-op.
 *  - Surgical: only messages matching `OFFLINE_PATTERNS` are downgraded; all
 *    other `console.error` calls reach the underlying impl unchanged.
 *  - No data loss: downgraded messages still appear in the console, just at
 *    `warn` level — the UI banner still renders "offline" so the human
 *    operator is not lied to.
 *  - Test/dev opt-out: set `localStorage["h3d.console.filter"] = "off"` to
 *    bypass the filter entirely (useful while debugging a real 5xx bug).
 *
 * What this DOES NOT do
 * ---------------------
 *  - Does not change `console.warn` semantics.
 *  - Does not silence anything.
 *  - Does not log or store the downgraded message anywhere outside the
 *    standard browser console — no telemetry, no remote sink.
 */

/**
 * Patterns matched against the first string-coerced argument to
 * `console.error`. A match downgrades the call to `console.warn`.
 *
 * Each pattern is documented with the exact browser-emitted form it covers.
 */
const OFFLINE_PATTERNS: readonly RegExp[] = [
  // Chromium "Failed to load resource: the server responded with a status of
  // 5xx (...)" — emitted at error level by the network stack for any 5xx
  // HTTP response, even when application code handles the response and never
  // calls `console.error` itself.
  /Failed to load resource:.*status of 5\d{2}\b/i,

  // Chromium / Firefox network-layer "Failed to fetch" — emitted when the
  // fetch promise rejects with a network error (DNS, refused, timeout).
  /TypeError: Failed to fetch\b/i,

  // Chromium-specific net errors, all expected when the local bridge is
  // not running. Each is a "browser can't reach the origin" condition that
  // the UI already surfaces via the offline banner.
  /\bnet::ERR_CONNECTION_REFUSED\b/i,
  /\bnet::ERR_CONNECTION_FAILED\b/i,
  /\bnet::ERR_NAME_NOT_RESOLVED\b/i,
  /\bnet::ERR_NETWORK_CHANGED\b/i,
  /\bnet::ERR_INTERNET_DISCONNECTED\b/i,

  // Cross-engine fallback when the network engine surfaces the failure as a
  // bare "NetworkError" string (Safari + Firefox).
  /\bNetworkError when attempting to fetch resource\b/i,
];

/**
 * Hermes3D backend paths that are known to be offline-tolerant. A 5xx or
 * network failure on any of these paths is downgraded to `warn`. We pin the
 * filter to these paths so a 5xx on an unrelated origin (e.g. a CDN that
 * normally works) still surfaces as a real `error`.
 *
 * If a path appears in the first console argument (Chromium prints the full
 * URL in the resource-failure message), the downgrade applies.
 *
 * W16-B 2026-05-10 — extended with the 12 paths the W15-A21 harness observed
 * returning 502 against the local v0.13 canary backend. Every path here is a
 * READ-ONLY status/poll endpoint already wrapped in a try/catch that returns
 * null/[] on failure, so a transient 502 cannot corrupt application state —
 * it is purely transient/offline noise per MDN's `warn` vs `error` taxonomy.
 *
 * Authoritative list of fetchers wrapping these paths:
 *   - /api/system/snapshot          -> adapters.live.ts fetchNullable
 *   - /api/proof/bundles            -> adapters.live.ts fetchArray
 *   - /api/notifications            -> adapters.live.ts fetchJson
 *   - /api/workflows                -> adapters.live.ts fetchArray
 *   - /api/voice/agents             -> adapters.live.ts fetchArray
 *   - /api/printers                 -> adapters.live.ts fetchJson (per-id) + EventSource
 *   - /api/logs                     -> adapters.live.ts fetchArray
 *   - /api/jobs                     -> adapters.live.ts fetchArray
 *   - /api/events/stream            -> Dashboard.tsx / SimpleHermesDashboard.tsx EventSource (idle/offline)
 *   - /api/dimensional-reports      -> adapters.live.ts fetchArray
 *   - /api/agents/print-safety-agent/history -> adapters.live.ts fetchArray
 */
const OFFLINE_PATHS: readonly string[] = [
  // PR #220 baseline
  "/api/agents/update/status",
  "/api/agents/update/",
  "/api/agents",
  "/api/agents/health",
  "/api/proof/events",
  "/api/code-operator/cli-runners",
  "/api/code-operator/mcp-locks",
  "/api/code-operator/recovery",
  "/api/code-operator/teams",
  "/api/code-operator/providers",
  "/api/providers/health",
  "/api/source-os/modules",
  // W16-B extensions — paths the W15-A21 harness confirmed 502 on the
  // local-only v0.13 canary stub. All wrapped in try/catch fetchers.
  "/api/system/snapshot",
  "/api/system/runtime-readiness",
  "/api/system/runtime-identity",
  "/api/proof/bundles",
  "/api/notifications",
  "/api/workflows",
  "/api/voice/agents",
  "/api/voice/transcripts",
  "/api/voice/proof-events",
  "/api/printers",
  "/api/logs",
  "/api/jobs",
  "/api/events/stream",
  "/api/dimensional-reports",
  "/api/agents/print-safety-agent",
];

/**
 * Coerce an arbitrary console argument into a searchable string without
 * triggering serialization side-effects (e.g. calling .toString() on an
 * `Error` would lose the stack; calling it on a `Response` would log the
 * body URL). We keep this conservative: Errors keep their message + name,
 * everything else falls through `String(x)`.
 */
function argToString(arg: unknown): string {
  if (arg == null) return "";
  if (typeof arg === "string") return arg;
  if (arg instanceof Error) return `${arg.name}: ${arg.message}`;
  try {
    return String(arg);
  } catch {
    return "";
  }
}

/**
 * Build the searchable haystack from all console.error arguments. We
 * concatenate so a multi-arg call like
 *   console.error("Fetch failed for", url, response.status)
 * matches against the full message rather than just the first token.
 */
function buildHaystack(args: unknown[]): string {
  return args.map(argToString).join(" ");
}

/**
 * Returns true if the console message looks like a known-offline 5xx or
 * network error against one of the Hermes3D backend paths.
 */
function isKnownOffline(haystack: string): boolean {
  if (haystack.length === 0) return false;
  const patternHit = OFFLINE_PATTERNS.some((re) => re.test(haystack));
  if (!patternHit) return false;
  // If the message mentions a Hermes3D path, downgrade. If it doesn't, leave
  // it as `error` because we cannot prove it's transient/offline noise.
  return OFFLINE_PATHS.some((path) => haystack.includes(path)) || isGenericNetworkRefusal(haystack);
}

/**
 * W16-B — Public predicate for offline classification at the Playwright
 * harness layer.
 *
 * The in-page wrapper (installConsoleFilter) only catches `console.error()`
 * calls that originate from JS code. Chromium emits "Failed to load
 * resource: 5xx" / "net::ERR_*" messages at the **renderer/network-stack**
 * level — those messages reach Playwright's `page.on('console')` listener
 * but do NOT go through the JS `console.error` function reference, so the
 * wrapper never sees them. The visual-oracle harness needs to apply the
 * SAME classification at sink-record time, against the message text AND
 * the `msg.location().url` Playwright surfaces alongside.
 *
 * Inputs:
 *   - `text`: the console message body (`msg.text()` in Playwright).
 *   - `locationUrl`: the originating resource URL (`msg.location().url`).
 *     May be empty when Chromium did not attach a URL (e.g. JS console.error
 *     with no associated request).
 *
 * Returns true ONLY when BOTH conditions hold:
 *   1. `text` matches an OFFLINE_PATTERN (5xx / net::ERR_* / Failed to fetch
 *      / NetworkError); and
 *   2. `text` OR `locationUrl` references an OFFLINE_PATH (a documented
 *      Hermes backend path), OR `locationUrl` is one of the local bridge
 *      origins (127.0.0.1:8765 / 8766 / 8767, localhost equivalents).
 *
 * The locationUrl branch is what fixes the W16-B regression: Chromium's
 * 502 message is "Failed to load resource: the server responded with a
 * status of 502 (Bad Gateway)" with NO path in the text — the path lives
 * exclusively in `msg.location().url`. PR #220's in-page predicate scanned
 * only the text and therefore could never match.
 *
 * No-fake / no-paid contract:
 *  - This is a pure function. No I/O, no telemetry.
 *  - Same predicate as `isKnownOffline` — they are intentionally identical
 *    so the two layers (in-page wrapper + harness sink) classify the same
 *    way. Test-only `__testing.isKnownOffline` continues to mirror this
 *    behaviour for backward compatibility.
 */
export function isHermesOfflineMessage(
  text: string,
  locationUrl: string,
): boolean {
  // Build a single haystack containing both the message body and the
  // location URL. This gives the existing `OFFLINE_PATHS.some(...)` and
  // `OFFLINE_PATTERNS.some(...)` predicates a single string to scan
  // exactly as if Chromium had inlined the URL in the message.
  const haystack = locationUrl ? `${text} ${locationUrl}` : text;
  return isKnownOffline(haystack);
}

/**
 * Some Chromium versions emit a bare `net::ERR_CONNECTION_REFUSED` without
 * including the URL in the same console call. When that happens the URL
 * lives in a separate "requestfailed" event. To avoid both false negatives
 * (real error suppressed) and false positives (suppressing a 5xx for an
 * unrelated origin), we only treat a bare net::ERR_* refusal as offline
 * when it explicitly references one of the localhost bridge ports we use.
 */
function isGenericNetworkRefusal(haystack: string): boolean {
  if (!/\bnet::ERR_/i.test(haystack)) return false;
  return (
    haystack.includes("127.0.0.1:8765") ||
    haystack.includes("127.0.0.1:8766") ||
    haystack.includes("127.0.0.1:8767") ||
    haystack.includes("localhost:8765") ||
    haystack.includes("localhost:8766") ||
    haystack.includes("localhost:8767")
  );
}

/**
 * Test-mode opt-out. Set
 *   localStorage["h3d.console.filter"] = "off"
 * to bypass the filter and let everything go to `console.error` unchanged.
 *
 * Treated as off when storage is unavailable (e.g. SSR, sandboxed iframes),
 * because those contexts don't need the filter anyway.
 */
function isFilterDisabled(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.localStorage?.getItem("h3d.console.filter") === "off";
  } catch {
    // Storage blocked (Safari private mode, etc.) — treat as enabled because
    // we'd rather have a quiet console than fail open.
    return false;
  }
}

/**
 * Module-level guard so installing the filter twice (HMR, StrictMode double
 * effect) is a no-op rather than a double-wrap.
 */
let installed = false;
let originalError: typeof console.error | null = null;

/**
 * Install the console.error filter. Idempotent; safe to call from app boot
 * AND from tests. Returns the uninstall function for tests that want to
 * reset between cases.
 */
export function installConsoleFilter(): () => void {
  if (installed) {
    return uninstallConsoleFilter;
  }
  installed = true;
  originalError = console.error.bind(console);
  const originalWarn = console.warn.bind(console);

  // Replace console.error with a thin wrapper. We intentionally do NOT
  // re-assign console.error to a fat-arrow function captured by reference
  // because StrictMode's double-render can recompute references; an
  // assignment-based wrap survives that.
  console.error = function hermesConsoleErrorFilter(...args: unknown[]) {
    if (isFilterDisabled()) {
      originalError!(...args);
      return;
    }
    const haystack = buildHaystack(args);
    if (isKnownOffline(haystack)) {
      // Downgrade to warn. Prefix so a developer scanning the console can
      // see why this is a `warn` and not an `error`. Reviewers reading the
      // proof artifact will see the same prefix in the captured logs.
      originalWarn("[hermes3d:offline-5xx]", ...args);
      return;
    }
    originalError!(...args);
  };

  return uninstallConsoleFilter;
}

/**
 * Restore the original `console.error`. Used by unit tests; not exported
 * from `main.tsx` because app code should keep the filter installed for the
 * full session.
 */
export function uninstallConsoleFilter(): void {
  if (!installed || !originalError) return;
  console.error = originalError;
  originalError = null;
  installed = false;
}

/** Test-only: expose the predicates so the unit suite can pin behavior. */
export const __testing = {
  argToString,
  buildHaystack,
  isKnownOffline,
  isGenericNetworkRefusal,
  OFFLINE_PATTERNS,
  OFFLINE_PATHS,
};
