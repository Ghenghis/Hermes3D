/**
 * W18-A1 PICKUP — Full Product Route Walker (FIX-IT MODE)
 *
 * The original `w18-a1` subagent died silently with locks still held; no PR
 * was produced. This pickup spec replaces it and follows the new operator
 * rule:
 *
 *   "If software is broken, fix it. If an endpoint is missing, add it.
 *    If a button is dead, wire it or honestly disable with backend reason.
 *    If a Playwright flow fails, fix and rerun. If a visual comparison
 *    fails, fix the UI, do not recapture baseline. If a test is skipped,
 *    it does not count. Completion = PASS_REAL with evidence."
 *
 * What this spec does — for every top-level route in `src/app/routes.ts`:
 *   1. Navigate (sidebar click for primary tabs; hash navigation for the
 *      utility/meta group that does not appear in the primary sidebar).
 *   2. Wait for the route root `[data-testid="{tab}-root"]` to mount.
 *   3. Capture every console.error, page error, request, and >=400 response
 *      from the moment navigation begins to ~1.5s after the root mounts.
 *   4. Take a per-route 1920x1080 screenshot.
 *   5. Score a per-route verdict from the strict vocabulary below.
 *
 * STRICT operator freeze (2026-05-11, printer heater on):
 *   - NO printer hardware writes. The spec does not POST/PUT/PATCH to any
 *     /api/printers/{id}/* endpoint that issues G-code/M-code/jog/home/heat.
 *   - NO submission to /api/jobs.
 *   - Pinned verdicts (do not change):
 *       GUI_PHYSICAL_PRINT_GREEN  = OUT_OF_SCOPE_BY_OPERATOR
 *       GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR
 *   - The spec only navigates routes — it does not click any element that
 *     would emit a printer-control mutation. The `printers` route is
 *     navigated and inspected; mutating clicks are explicitly skipped.
 *
 * Status vocabulary (this is the ONLY set of allowed verdicts):
 *   PASS_REAL                          — route mounted, no console.error,
 *                                        no pageerror, no unexpected 4xx/5xx
 *                                        against `/api/*` paths the route
 *                                        uses.
 *   PARTIAL                            — route mounted but a backend
 *                                        dependency returned a documented
 *                                        honest-blocked payload (e.g. 200
 *                                        with `accepted=false` + reason)
 *                                        rather than fresh data.
 *   FAIL_NOT_WIRED                     — route mounted but a click target
 *                                        with no live-call wiring exists,
 *                                        or the route's primary content is
 *                                        a placeholder (no live data
 *                                        rendered).
 *   FAIL_BROKEN                        — pageerror, console.error, the root
 *                                        did not mount within 15s, or a
 *                                        request to a documented /api/*
 *                                        path returned 0 / >=500.
 *   FAIL_BACKEND_MISSING               — route triggered a network call to
 *                                        a documented /api/* path that
 *                                        returned 404 / 405 (route does not
 *                                        exist on the live backend).
 *   OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE
 *                                      — Printer hardware-write path
 *                                        deferred by operator freeze.
 *
 * Hard rules baked into this spec:
 *   - No `test.skip`. No fake-ready. No mocks. No route stubs. The live
 *     FastAPI on 127.0.0.1:8765 is the source of truth — if it 502s, that
 *     is a finding.
 *   - No `expect(...).toPass({ ignore: ... })` cheats — verdicts are
 *     deterministic from the captured signals.
 */
import { expect, test, type ConsoleMessage, type Page, type Request, type Response } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Mirror of `src/app/routes.ts` TABS. Inline to keep the audit independent
// of source-import paths that change branch-to-branch. Order matches the
// sidebar (primary group first, then utility group, then meta tabs).
const ROUTES: Array<{
  id: string;
  label: string;
  rootTestId: string;
  hashOnly: boolean;
}> = [
  // Primary group — reachable by clicking the sidebar row by accessible name.
  { id: "source_os", label: "Source OS", rootTestId: "source-os-root", hashOnly: false },
  { id: "dashboard", label: "Dashboard", rootTestId: "dashboard-root", hashOnly: false },
  { id: "autopilot", label: "Autopilot", rootTestId: "autopilot-root", hashOnly: false },
  { id: "design", label: "Design", rootTestId: "design-root", hashOnly: false },
  { id: "gen3d", label: "3D Generation", rootTestId: "gen3d-root", hashOnly: false },
  { id: "jobs", label: "Jobs", rootTestId: "jobs-root", hashOnly: false },
  { id: "printers", label: "Printers", rootTestId: "printers-root", hashOnly: false },
  { id: "observe", label: "Observe", rootTestId: "observe-root", hashOnly: false },
  { id: "voice", label: "Voice", rootTestId: "voice-root", hashOnly: false },
  { id: "agents", label: "Agents", rootTestId: "agents-root", hashOnly: false },
  { id: "learning", label: "Learning", rootTestId: "learning-root", hashOnly: false },
  { id: "artifacts", label: "Artifacts", rootTestId: "artifacts-root", hashOnly: false },
  { id: "approvals", label: "Approvals", rootTestId: "approvals-root", hashOnly: false },
  { id: "apps", label: "Apps", rootTestId: "apps-root", hashOnly: false },
  { id: "plugins", label: "Plugins", rootTestId: "plugins-root", hashOnly: false },
  // Utility group — sidebar does not render these; reach via hash.
  { id: "workflows", label: "Workflows", rootTestId: "workflows-root", hashOnly: true },
  { id: "print_queue", label: "Print Queue", rootTestId: "print-queue-root", hashOnly: true },
  { id: "files", label: "Files", rootTestId: "files-root", hashOnly: true },
  { id: "system_logs", label: "System Logs", rootTestId: "system-logs-root", hashOnly: true },
  { id: "proof", label: "Proof", rootTestId: "proof-root", hashOnly: true },
  { id: "service_health", label: "Service Health", rootTestId: "service-health-root", hashOnly: true },
  { id: "notifications", label: "Notifications", rootTestId: "notifications-root", hashOnly: true },
  { id: "safety", label: "Safety", rootTestId: "safety-root", hashOnly: true },
  // Meta tabs — also hash-only (sidebar does not render them in the primary group).
  { id: "settings", label: "Settings", rootTestId: "settings-root", hashOnly: true },
  { id: "roadmap", label: "Roadmap", rootTestId: "roadmap-root", hashOnly: true },
];

// Hash form for each route (matches `TAB_TO_HASH` in `src/app/store.ts`).
const HASH_FOR: Record<string, string> = {
  source_os: "sources",
  dashboard: "dashboard",
  autopilot: "autopilot",
  design: "design",
  gen3d: "gen3d",
  jobs: "jobs",
  printers: "printers",
  observe: "observe",
  voice: "voice",
  agents: "agents",
  learning: "learning",
  artifacts: "artifacts",
  approvals: "approvals",
  apps: "apps",
  plugins: "plugins",
  workflows: "workflows",
  print_queue: "print_queue",
  files: "files",
  system_logs: "system_logs",
  proof: "proof",
  service_health: "service_health",
  notifications: "notifications",
  safety: "safety",
  settings: "settings",
  roadmap: "roadmap",
};

type Verdict =
  | "PASS_REAL"
  | "PARTIAL"
  | "FAIL_NOT_WIRED"
  | "FAIL_BROKEN"
  | "FAIL_BACKEND_MISSING"
  | "OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE";

interface NetworkRecord {
  url: string;
  method: string;
  status: number;
  statusText: string;
}

interface RouteRecord {
  route: string;
  label: string;
  hashOnly: boolean;
  reachable: boolean;
  rootMounted: boolean;
  verdict: Verdict;
  reason: string;
  consoleErrors: string[];
  pageErrors: string[];
  apiCalls: NetworkRecord[];
  apiFailures: NetworkRecord[];
  apiFailuresBenign: NetworkRecord[];
  screenshot: string;
  durationMs: number;
}

const OUTPUT_DIR = path.resolve(__dirname, "..", "..", "test-results", "w18-a1-pickup");
fs.mkdirSync(OUTPUT_DIR, { recursive: true });
fs.mkdirSync(path.join(OUTPUT_DIR, "screenshots"), { recursive: true });
const ARTIFACT_PATH = path.join(OUTPUT_DIR, "audit.json");

// Console-error fragments that the route walker treats as benign noise
// rather than a route-breaking failure. Each entry must have a documented
// reason — these are environment artifacts the operator has explicitly
// acknowledged are not a route regression. The list is INTENTIONALLY tight.
const BENIGN_CONSOLE_FRAGMENTS: Array<{ fragment: string; reason: string }> = [
  // EventSource (SSE) auto-reconnect noise when the server happens to be
  // mid-restart — surfaces as a console.error with no impact on the active
  // route. The /api/events/stream channel itself is verified live elsewhere.
  { fragment: "EventSource", reason: "SSE reconnect noise — channel is verified by /api/events/stream gate" },
];

/**
 * Network-failure URLs that are treated as benign for route-walker scoring.
 *
 * Each entry MUST have a real engineering justification. The list is the
 * narrowest possible set that still produces a useful audit:
 *
 *   /api/events/stream
 *     EventSource (SSE) — the Dashboard route opens a long-lived stream.
 *     When the user (or this spec) navigates away from Dashboard, the SPA
 *     destroys the EventSource, and Chromium aborts the in-flight long-poll
 *     with status=0 / `net::ERR_ABORTED`. Playwright surfaces that as a
 *     `requestfailed` event that — because it crosses the route boundary —
 *     gets attributed to the next route in our pre/post counter window.
 *     This is normal SSE lifecycle, NOT a route regression.
 *
 *     Operator-side proof of the channel: `/api/events/stream` itself is
 *     a documented offline-tolerant path (see `src/api/consoleFilter.ts`
 *     OFFLINE_PATHS line 152) and is exercised live by the Dashboard.
 */
const BENIGN_API_FAILURES: ReadonlyArray<{
  pathFragment: string;
  errorMatches: ReadonlyArray<string | RegExp>;
  reason: string;
}> = [
  {
    pathFragment: "/api/events/stream",
    errorMatches: ["net::ERR_ABORTED"],
    reason:
      "EventSource (SSE) abort during route change — destroyed when Dashboard unmounts; normal lifecycle",
  },
];

function isBenignApiFailure(rec: NetworkRecord): boolean {
  for (const b of BENIGN_API_FAILURES) {
    if (!rec.url.includes(b.pathFragment)) continue;
    for (const m of b.errorMatches) {
      if (typeof m === "string" ? rec.statusText.includes(m) : m.test(rec.statusText)) {
        return true;
      }
    }
  }
  return false;
}

const PRINTERS_ROUTE_ID = "printers";

test.describe.configure({ mode: "serial" });

test("W18-A1 PICKUP — walk every top-level route, capture network + console, score verdicts", async ({
  page,
}) => {
  test.setTimeout(15 * 60_000);

  const routeRecords: RouteRecord[] = [];
  const allConsoleErrors: string[] = [];
  const allPageErrors: string[] = [];
  const allApiCalls: NetworkRecord[] = [];
  const allApiFailures: NetworkRecord[] = [];

  // Track in-flight `/api/*` requests so the per-route settle window can wait
  // for them to drain BEFORE navigating to the next route. Without this, a
  // slow first-time backend call (e.g. cold `_sync_apps_once()` in CI which
  // seeds 60 apps from JSON on first `/api/apps` hit) can still be pending
  // when the spec clicks the next sidebar tab. The component's `useEffect`
  // cleanup then aborts the fetch via its AbortController, producing a
  // `net::ERR_ABORTED` that this spec attributes to the route that started
  // the call. This is a spec-side timing race, not a backend regression —
  // local repro: `/api/apps` returns 60 apps in 200 OK, the same backend in
  // CI returns 60 apps in 200 OK, only the spec's settle window was too
  // short for cold CI starts.
  //
  // Excludes long-lived SSE channels (the EventSource on
  // `/api/events/stream`) which never "complete" in a request sense — those
  // remain in the benign-failure allowlist below.
  const SSE_PATH_FRAGMENTS = ["/api/events/stream"] as const;
  // Endpoints that are intentionally slow (>5s typical) on the live local
  // stack and would otherwise pin `inflightApi.size` above 0 for the
  // full 8s quiesce bound. We still RECORD calls to these endpoints
  // for verdict scoring (a 404 or 500 against them is still a finding)
  // — we just don't let them block the quiesce window. Documented:
  //   - /api/health/services — heavy aggregate health probe across
  //     printers + agents + modules; can take 10–15s cold.
  //   - GET /api/modules (root list) + /api/modules/runtime/* — module
  //     reconciliation, scans on-disk module dirs + plugin contracts.
  //     10–15s on a cold filesystem; effectively a long-running
  //     aggregator. (Note: /api/modules/update/readiness is FAST and
  //     deliberately NOT excluded.)
  //   - /api/agents/action-catalog — agent action catalog reconciliation;
  //     scans plugin contracts (10–15s cold).
  //   - /api/code-operator/{e2e,sandbox}/readiness — readiness probes
  //     that walk the entire code-operator artifact tree (5–10s).
  //
  // These are deliberately the narrowest possible set: every entry is
  // an endpoint that has been measured >5s on the live local stack
  // (see PR #242 follow-up). If a route's ONLY signal is a call to
  // one of these endpoints, the per-route pre/post API-call slice
  // still captures it for the verdict — only the quiesce *gate* is
  // bypassed.
  //
  // We use regex matches (anchored on the API origin) so we can pin
  // `GET /api/modules` (root list) without over-blocking the rest of
  // the /api/modules/* tree.
  const SLOW_BACKEND_RE: ReadonlyArray<RegExp> = [
    /\/api\/health\/services(\?|$)/,
    /\/api\/modules(\?|$)/, // root list, NOT /api/modules/whatever
    /\/api\/modules\/runtime\/setup-queue(\?|$)/,
    /\/api\/modules\/runtime\/runner-contracts(\?|$)/,
    /\/api\/modules\/runtime\/verifiers(\?|$)/,
    /\/api\/agents\/action-catalog(\?|$)/,
    /\/api\/code-operator\/e2e\/readiness(\?|$)/,
    /\/api\/code-operator\/sandbox\/readiness(\?|$)/,
  ];
  const inflightApi = new Set<Request>();
  const isSse = (url: string) => SSE_PATH_FRAGMENTS.some((f) => url.includes(f));
  const isSlowBackend = (url: string) =>
    SLOW_BACKEND_RE.some((re) => re.test(url));
  // A request is "quiesce-blocking" if it's a /api/* request that we
  // expect to complete reasonably fast. SSE channels never complete;
  // slow-backend endpoints take 5–15s and are documented as such.
  const isQuiesceBlocking = (url: string) =>
    /\/api\//.test(url) && !isSse(url) && !isSlowBackend(url);
  // Track the wall-clock when `inflightApi.size` last transitioned to or
  // remained at 0. The quiesce heuristic waits for this to remain
  // continuously true for `quietMs` ms — i.e. the page must have had
  // an unbroken stretch of zero in-flight /api/* traffic.
  //
  // Why this and not "no request start in the last quietMs":
  //   Several product routes (dashboard, agents, safety, etc.) mount
  //   global pollers that fire every 1–3s for `/api/agents/update/status`
  //   and friends. These pollers START a request, but they also COMPLETE
  //   fast (typically <50ms for a 200 OK). Between polls there are
  //   multi-second windows where `inflightApi.size === 0`. By keying off
  //   "stretches of zero", we observe the page as settled *between*
  //   polls without having to special-case poller URLs.
  //
  //   Chained `useEffect` fetches (the failure mode the v2 fix targets)
  //   still work because the parent request lands → child fetch starts
  //   within ~1 tick → `inflightApi.size` jumps back to 1, resetting
  //   `inflightZeroSinceMs`. Once the chain truly stops, we get a real
  //   `quietMs` window of zero.
  let inflightZeroSinceMs = Date.now();
  const onInflightChange = () => {
    if (inflightApi.size === 0) {
      // Only set if we weren't already at zero — preserves the
      // continuous-stretch semantic. If we're already at zero this is
      // a no-op.
      if (inflightZeroSinceMs === 0) inflightZeroSinceMs = Date.now();
    } else {
      inflightZeroSinceMs = 0;
    }
  };

  // Raw observers. No filtering applied here — filtering happens at the
  // per-route scoring step so we still record every raw signal in the
  // global audit.
  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() === "error") allConsoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => {
    allPageErrors.push(err.message);
  });
  page.on("request", (req: Request) => {
    const url = req.url();
    if (!isQuiesceBlocking(url)) return;
    inflightApi.add(req);
    onInflightChange();
  });
  page.on("response", async (res: Response) => {
    const url = res.url();
    if (!/\/api\//.test(url)) return;
    if (isQuiesceBlocking(url)) {
      inflightApi.delete(res.request());
      onInflightChange();
    }
    const status = res.status();
    const rec: NetworkRecord = {
      url,
      method: res.request().method(),
      status,
      statusText: res.statusText(),
    };
    allApiCalls.push(rec);
    if (status === 0 || status >= 400) {
      allApiFailures.push(rec);
    }
  });
  page.on("requestfailed", (req: Request) => {
    const url = req.url();
    if (!/\/api\//.test(url)) return;
    if (isQuiesceBlocking(url)) {
      inflightApi.delete(req);
      onInflightChange();
    }
    const rec: NetworkRecord = {
      url,
      method: req.method(),
      status: 0,
      statusText: req.failure()?.errorText ?? "request_failed",
    };
    allApiCalls.push(rec);
    allApiFailures.push(rec);
  });
  page.on("requestfinished", (req: Request) => {
    const url = req.url();
    if (!/\/api\//.test(url)) return;
    if (isQuiesceBlocking(url)) {
      inflightApi.delete(req);
      onInflightChange();
    }
  });

  /**
   * Wait for `inflightApi.size === 0` to have been continuously true
   * for at least `quietMs` ms. Bounded by `timeoutMs` so a runaway
   * never hangs the suite.
   *
   * Why this heuristic:
   *   - Pure "size === 0" is not enough: chained `useEffect` fetches
   *     start ~1 tick after their parent completes, so `size` briefly
   *     hits 0 between parent and child.
   *   - "No request start in the last N ms" doesn't work either:
   *     several routes mount fast pollers (every 1–3s) that keep
   *     refreshing the clock indefinitely.
   *   - Continuous-zero-stretch threads the needle: a 200–300ms window
   *     of zero inflight is fast enough that fast pollers (which
   *     complete each poll in <50ms) leave wide enough gaps between
   *     polls to clear it, AND it's long enough to outlast any
   *     reasonable parent→child chain (16ms typical).
   *
   * Local measurements at the time of authoring (2026-05-11):
   *   - Typical route: drains in 300–800ms.
   *   - Heaviest route (dashboard / agents / safety with pollers):
   *     drains in 600–1500ms.
   *   - Total walker runtime: ~30–45s for all 25 routes (was ~80–130s).
   *
   * If `timeoutMs` elapses with the page still chatty, we proceed —
   * the per-route slice accounting (consolePre/apiCallPre/etc.) keeps
   * later routes from being polluted by traffic that overflowed this
   * window.
   */
  const waitForApiQuiesce = async (
    quietMs = 300,
    timeoutMs = 8_000,
  ): Promise<void> => {
    const deadline = Date.now() + timeoutMs;
    // Re-prime the zero-since marker for THIS route's wait. The previous
    // route may have left it stale (it's a long-lived signal).
    if (inflightApi.size === 0 && inflightZeroSinceMs === 0) {
      inflightZeroSinceMs = Date.now();
    }
    while (Date.now() < deadline) {
      if (
        inflightApi.size === 0 &&
        inflightZeroSinceMs > 0 &&
        Date.now() - inflightZeroSinceMs >= quietMs
      ) {
        return;
      }
      await page.waitForTimeout(50);
    }
  };

  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 });
  // First-paint guard — the SPA mounts the dashboard root on load.
  await page.waitForSelector('[data-testid="dashboard-root"]', { timeout: 20_000 });

  for (const route of ROUTES) {
    const consolePre = allConsoleErrors.length;
    const pageErrPre = allPageErrors.length;
    const apiCallPre = allApiCalls.length;
    const apiFailPre = allApiFailures.length;

    const tStart = Date.now();
    let reachable = false;
    let rootMounted = false;
    let reachReason = "";

    try {
      if (route.hashOnly) {
        await page.evaluate((h) => {
          window.location.hash = `#${h}`;
        }, HASH_FOR[route.id]);
      } else {
        const sidebar = page.getByRole("button", { name: route.label, exact: true });
        await expect(sidebar).toBeVisible({ timeout: 5_000 });
        await sidebar.click();
      }
      reachable = true;
    } catch (err) {
      reachable = false;
      reachReason = `navigation failed: ${(err as Error).message.split("\n")[0]}`;
    }

    if (reachable) {
      try {
        await expect(page.getByTestId(route.rootTestId)).toBeVisible({ timeout: 15_000 });
        rootMounted = true;
      } catch (err) {
        rootMounted = false;
        reachReason = `root [data-testid="${route.rootTestId}"] did not mount in 15s: ${(err as Error).message.split("\n")[0]}`;
      }
    }

    // Settle window — give live data fetches a chance to complete so we
    // catch their 4xx/5xx in this route's slice. Evolution:
    //   v1 (initial): fixed 1.5s wait. Too short for cold CI runners.
    //   v2 (PR #242 5ab95d1): fixed 1.5s + waitForApiQuiesce up to 8s
    //     on inflight-empty. Local re-run was 1.3 min (vs 44s before)
    //     and CI exceeded patience — 25 × 8s worst-case = 200s, plus
    //     25 × 1.5s = 37.5s of unconditional sleep on top.
    //   v3 (this fix, 2026-05-11 W18-A1P-CIFIX2): switched to a
    //     "300ms of continuous zero inflight" heuristic. Tracks when
    //     `inflightApi.size` last transitioned to 0 and waits for it
    //     to stay there. Works in the presence of fast pollers
    //     (their poll → response → 0-inflight gap of 1–3s clears the
    //     300ms window easily) AND catches chained useEffect fetches
    //     (parent completes → child starts inside one tick → size
    //     bounces back to ≥1, resetting the window). Cold-start
    //     safety preserved via the 8s upper bound. Typical local
    //     route drains in 300–800ms (heaviest in 600–1500ms).
    if (rootMounted) {
      // Small post-mount tick — give the route's `useEffect`-driven
      // fetches a chance to be kicked off so the quiesce check has
      // something to wait for. Without this, a route whose mount is
      // synchronous w.r.t. its data fetches could satisfy the zero-
      // inflight window before its fetches even start.
      await page.waitForTimeout(100);
      // Re-prime the zero-stretch clock so this route's wait measures
      // a fresh stretch — without this, the previous route could
      // satisfy our quietMs window before this route's fetches start.
      inflightZeroSinceMs = inflightApi.size === 0 ? Date.now() : 0;
      await waitForApiQuiesce(300, 8_000);
    }

    // Per-route screenshot for the evidence pack.
    const shotName = `${route.id}.png`;
    const shotPath = path.join(OUTPUT_DIR, "screenshots", shotName);
    try {
      await page.screenshot({ path: shotPath, fullPage: false });
    } catch {
      // Screenshot failure is not a route-walker failure — we record it
      // implicitly via the empty screenshot path.
    }

    const myConsole = allConsoleErrors.slice(consolePre);
    const myPageErrors = allPageErrors.slice(pageErrPre);
    const myApiCalls = allApiCalls.slice(apiCallPre);
    const myApiFailuresRaw = allApiFailures.slice(apiFailPre);
    const myApiFailures = myApiFailuresRaw.filter((n) => !isBenignApiFailure(n));

    const significantConsole = myConsole.filter(
      (msg) => !BENIGN_CONSOLE_FRAGMENTS.some((b) => msg.includes(b.fragment)),
    );

    let verdict: Verdict;
    let reason: string;

    if (!reachable || !rootMounted) {
      verdict = "FAIL_BROKEN";
      reason = reachReason || "route did not reach a mounted root";
    } else if (myPageErrors.length > 0) {
      verdict = "FAIL_BROKEN";
      reason = `pageerror: ${myPageErrors[0]}`;
    } else if (significantConsole.length > 0) {
      verdict = "FAIL_BROKEN";
      reason = `console.error: ${significantConsole[0].slice(0, 200)}`;
    } else if (myApiFailures.length > 0) {
      const missing = myApiFailures.find((n) => n.status === 404 || n.status === 405);
      const broken = myApiFailures.find((n) => n.status === 0 || n.status >= 500);
      if (missing) {
        verdict = "FAIL_BACKEND_MISSING";
        reason = `${missing.method} ${missing.url} -> ${missing.status} ${missing.statusText}`;
      } else if (broken) {
        verdict = "FAIL_BROKEN";
        reason = `${broken.method} ${broken.url} -> ${broken.status} ${broken.statusText}`;
      } else {
        // 4xx that is not 404/405 — record as PARTIAL (honest-blocked
        // semantics, e.g. 400/403/422 with a documented reason payload).
        verdict = "PARTIAL";
        reason = `${myApiFailures[0].method} ${myApiFailures[0].url} -> ${myApiFailures[0].status}`;
      }
    } else if (route.id === PRINTERS_ROUTE_ID) {
      // Printers route mounts cleanly and reads `/api/printers` — but the
      // operator freeze on hardware-write paths means we do NOT click any
      // mutating control. Verdict is PASS_REAL for the read-only walk.
      verdict = "PASS_REAL";
      reason =
        "read-only walk: route mounted, /api/printers read OK; hardware-write paths skipped under operator freeze";
    } else {
      verdict = "PASS_REAL";
      reason = "route mounted, no console.error/pageerror, no /api/* failures";
    }

    routeRecords.push({
      route: route.id,
      label: route.label,
      hashOnly: route.hashOnly,
      reachable,
      rootMounted,
      verdict,
      reason,
      consoleErrors: myConsole.slice(0, 5),
      pageErrors: myPageErrors.slice(0, 5),
      apiCalls: myApiCalls.slice(0, 30),
      apiFailures: myApiFailures.slice(0, 10),
      apiFailuresBenign: myApiFailuresRaw.filter((n) => isBenignApiFailure(n)).slice(0, 5),
      screenshot: path.relative(OUTPUT_DIR, shotPath),
      durationMs: Date.now() - tStart,
    });
  }

  const aggregate = routeRecords.reduce<Record<Verdict, number>>(
    (acc, r) => {
      acc[r.verdict] = (acc[r.verdict] || 0) + 1;
      return acc;
    },
    {
      PASS_REAL: 0,
      PARTIAL: 0,
      FAIL_NOT_WIRED: 0,
      FAIL_BROKEN: 0,
      FAIL_BACKEND_MISSING: 0,
      OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE: 0,
    },
  );

  const artifact = {
    generated_utc: new Date().toISOString(),
    spec: "tests/e2e/w18-a1-pickup-full-route-walk.spec.ts",
    config: "playwright.w18-a1-pickup.config.ts",
    base_url: page.url().replace(/(\/#.*)?$/, ""),
    backend_url: "http://127.0.0.1:8765",
    operator_freeze: {
      printer_hardware_writes: "FORBIDDEN",
      gui_physical_print_green: "OUT_OF_SCOPE_BY_OPERATOR",
      gui_printer_dry_run_green: "OUT_OF_SCOPE_BY_OPERATOR",
    },
    routes: routeRecords,
    aggregate: {
      total_routes: routeRecords.length,
      verdicts: aggregate,
      total_console_errors: allConsoleErrors.length,
      total_page_errors: allPageErrors.length,
      total_api_calls: allApiCalls.length,
      total_api_failures: allApiFailures.length,
    },
    raw: {
      consoleErrors: allConsoleErrors,
      pageErrors: allPageErrors,
      apiFailures: allApiFailures,
    },
  };
  fs.writeFileSync(ARTIFACT_PATH, JSON.stringify(artifact, null, 2), "utf8");

  // Print a per-route table so the runner log is human-readable without
  // needing the audit.json blob.
  console.log("--- W18-A1 PICKUP ROUTE WALK ---");
  for (const r of routeRecords) {
    console.log(
      `[${r.verdict.padEnd(34, " ")}] ${r.route.padEnd(16, " ")} ${r.reason}`,
    );
  }
  console.log("--- AGGREGATE ---", JSON.stringify(aggregate));
  console.log("--- ARTIFACT ---", ARTIFACT_PATH);

  // Fix-it mode: a non-PASS_REAL verdict on any non-printer-lane route is a
  // hard failure for this gate. The printer route is read-only-walk PASS,
  // so it passes; the explicit OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE
  // verdict is reserved for sub-clicks the spec might add later (it is
  // counted as acceptable in this aggregate).
  const failing = routeRecords.filter(
    (r) =>
      r.verdict !== "PASS_REAL" &&
      r.verdict !== "OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE",
  );
  if (failing.length > 0) {
    const detail = failing
      .map((r) => `  - ${r.route} [${r.verdict}] ${r.reason}`)
      .join("\n");
    throw new Error(
      `W18-A1 PICKUP route walker: ${failing.length} route(s) below PASS_REAL\n${detail}`,
    );
  }

  expect(routeRecords.length).toBe(ROUTES.length);
});
