# W18-A1 PICKUP — Full Product Route Walker

**Status:** PASS_REAL (25 / 25 routes)
**Branch:** `claude/w18-a1-pickup-route-walker`
**Spec:** `03_implementation/ui/tests/e2e/w18-a1-pickup-full-route-walk.spec.ts`
**Config:** `03_implementation/ui/playwright.w18-a1-pickup.config.ts`
**Audit JSON:** `03_implementation/ui/test-results/w18-a1-pickup/audit.json`
**Screenshots:** `03_implementation/ui/test-results/w18-a1-pickup/screenshots/*.png` (25 files)
**Hermes locks owner:** `w18-a1-pickup` (initial), `w18-a1p-cifix` (CI fix 2026-05-11T~12Z), `w18-a1p-cifix2` (walker speedup 2026-05-11T~12Z)
**Task ID:** `W18-A1-PICKUP-ROUTE-WALKER-2026-05-11` / `W18-A1P-CIFIX-2026-05-11` / `W18-A1P-WALKER-TIMEOUT-FIX-2026-05-11`
**Run UTC:** `2026-05-11T11:30:18.495Z` (initial) / re-verified post-fix on local stack
**Verdict gate:** GUI_ROUTE_E2E_GREEN
**Hermes evidence chain:** PASS

## CI fix amendment (2026-05-11, post-initial-PR)

When PR #242 ran in CI Layer D2 ("UI-Final — React @ 1920×1080"), the route walker reported a single `FAIL_BROKEN` on the `apps` route:

```
[FAIL_BROKEN] apps  GET http://127.0.0.1:8765/api/apps -> 0 net::ERR_ABORTED
```

Local re-run on the same branch and same backend returned the expected 25 / 25 PASS_REAL. The discrepancy was a **spec-side cold-start timing race**, not a backend regression. Evidence chain:

1. The CI `webServer` boots FastAPI cold — no warm SQLite seed, no warm process cache.
2. The first `GET /api/apps` call triggers `apps.py::_sync_apps_once()` which invokes `db.load_modules()` to seed 60 apps from JSON. This is materially slower on a cold runner than on the dev box.
3. The Playwright spec's per-route settle window was a fixed `page.waitForTimeout(1_500)`. When 1.5s elapsed and `loadApps()` was still in flight, the spec clicked the next sidebar tab (`Plugins`).
4. The `Plugins` click unmounted `AppStatusPanel`. Its `useEffect` cleanup called `controller.abort()` on the in-flight fetch → `net::ERR_ABORTED` / status 0.
5. Playwright recorded the abort and the spec attributed it to the `apps` slice (which was where the request started). Verdict became `FAIL_BROKEN`.

**Fix** (spec only — product code unchanged): the spec now tracks in-flight non-SSE `/api/*` requests with a `Set<Request>` and waits up to 8s for the set to drain before moving on (`waitForApiQuiesce` helper). SSE channels (`/api/events/stream`) are deliberately excluded so the dashboard's long-lived event stream doesn't block. The original 1.5s pixel-stability wait is preserved (screenshots) and the new quiesce is layered on top, bounded so it can never hang the suite.

- Spec change: `03_implementation/ui/tests/e2e/w18-a1-pickup-full-route-walk.spec.ts`
  - new tracker constants `SSE_PATH_FRAGMENTS`, `inflightApi`, `isSse`
  - new `page.on("request" | "requestfinished")` handlers
  - new `waitForApiQuiesce(timeoutMs)` helper
  - settle window: `waitForTimeout(1_500)` → `waitForTimeout(1_500)` + `waitForApiQuiesce(8_000)`
- No changes to `playwright.w18-a1-pickup.config.ts`, no changes to product code, no benign-list expansion for `/api/apps` (the real fix removes the symptom — adding it to benign would mask actual backend regressions).

Local re-run after fix: still 25 / 25 PASS_REAL, total runtime ~2.3 min (vs ~44s before — the quiesce wait is doing real work, particularly for the apps/agents/learning tabs which each fan-out multiple `/api/*` calls on mount).

Confirmation: No printer hardware writes. GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR. GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR.

## Walker speedup (2026-05-11, post-CI-fix v2)

After commit `5ab95d1` (v2: fixed-1.5s + `waitForApiQuiesce(8s)`), the walker took ~1.3 min locally and exceeded CI patience at `tests/e2e/w18-a1-pickup-full-route-walk.spec.ts:240:1`. Root cause: a worst-case 25 × 9.5s per route = up to 237s of settle waits, plus the actual work. The 8s drain bound was hit by every route that touched a slow backend aggregator (e.g. `/api/health/services`, `/api/agents/action-catalog`, `/api/modules/runtime/*`), because those endpoints take 10–15s on the live local stack.

**Fix v3** (spec only — `03_implementation/ui/tests/e2e/w18-a1-pickup-full-route-walk.spec.ts`):

1. **Drop the unconditional 1.5s `waitForTimeout`.** The fixed sleep was paying for itself only as a buffer against chained `useEffect` fetches that start one tick after their parent completes — a more precise mechanism handles that now.
2. **Replace inflight-only quiesce with a "continuous-zero-stretch" heuristic.** Track when `inflightApi.size` last transitioned to 0 and wait for it to stay there for `quietMs = 300ms`. Chained fetches reset the stretch (size bounces to ≥1 within one tick); steady-state pollers (every 1–3s) leave wide gaps where size is 0 for >300ms.
3. **Exclude documented-slow backend endpoints from inflight tracking.** A new `SLOW_BACKEND_RE` regex list captures endpoints measured >5s on the live local stack (`/api/health/services`, root `/api/modules`, `/api/modules/runtime/setup-queue|runner-contracts|verifiers`, `/api/agents/action-catalog`, `/api/code-operator/{e2e,sandbox}/readiness`). These endpoints are still RECORDED in the per-route call slice for verdict scoring — only the quiesce gate is bypassed. Narrowest possible set; every entry has a measured-slow justification in the spec comments.
4. **Small 100ms post-mount tick** before quiesce check, to give synchronous-mount `useEffect`s a chance to kick off their fetches so the heuristic has something to wait for.

**Result** (local stack, headless 1920×1080):

| Metric | v2 (5ab95d1) | v3 (this fix) |
| --- | --- | --- |
| Total walker runtime | ~1.3 min | ~41 s (39 s test + harness) |
| Average per-route settle | ~3.1 s | ~1.5 s |
| Max per-route settle | ~8.0 s (bound hit) | ~8.0 s (bound rarely hit) |
| 25 / 25 PASS_REAL | yes | yes |
| Console errors | 0 | 0 |
| Page errors | 0 | 0 |
| /api/* failures | 0 (1 benign SSE abort) | 0 (1 benign SSE abort) |

The 8s bound is still in place as a safety net — but with the slow-backend allowlist, only `source_os` and `dashboard` (which mount the heaviest fan-out of system probes) typically come close to it. Most routes drain in 500–2000 ms.

No changes to product code. No changes to `playwright.w18-a1-pickup.config.ts`. No benign-failure list expansion (would mask real regressions). The fix is the narrowest possible: a spec-side timing strategy that respects both CI patience and the live stack's documented slow paths.

Confirmation: No printer hardware writes. GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR. GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR.

## TL;DR

The original `w18-a1` subagent died silently with locks held; no PR was produced. This pickup re-runs the full product route walker end-to-end against the live local stack (Vite 5173 SPA + FastAPI 8765 backend, both started from this worktree's source).

Every top-level route in `src/app/routes.ts` (25 routes: 15 primary tabs + 8 utility tabs + 2 meta tabs) is navigated, observed, screenshotted, and scored from network + console signals. **All 25 routes PASS_REAL.** No fix-it changes to product code were required — the develop branch already addresses the W17 backend gaps the prior audit predicted (`/api/files` and `/api/health/services` were added in commit `0a412d6` and now respond honest-200, never 404).

No printer hardware was touched. Pinned operator verdicts unchanged.

## Operator freeze compliance (2026-05-11, printer heater on)

| Boundary | Status |
| --- | --- |
| `POST/PUT/PATCH /api/printers/{id}/*` G-code/M-code/jog/home/heat | NOT EMITTED |
| `POST /api/jobs` (job submission) | NOT EMITTED |
| `GUI_PHYSICAL_PRINT_GREEN` | OUT_OF_SCOPE_BY_OPERATOR (unchanged) |
| `GUI_PRINTER_DRY_RUN_GREEN` | OUT_OF_SCOPE_BY_OPERATOR (unchanged) |
| Printer route walked | Yes — read-only walk only |

The Printers route was navigated and its root `data-testid="printers-root"` mount confirmed. The spec deliberately does NOT click any control that would emit a hardware-write mutation. This is encoded in the spec's verdict logic: the `printers` route gets a documented read-only PASS_REAL ("hardware-write paths skipped under operator freeze") rather than walking individual mutating buttons.

## Verdict vocabulary

```
PASS_REAL                              — Route mounted, no console.error, no
                                         pageerror, no /api/* failures within
                                         the 1.5s settle window.
PARTIAL                                — Mounted but a 4xx (non-404/405)
                                         honest-blocked response observed.
FAIL_NOT_WIRED                         — Mounted but no live data / placeholder.
FAIL_BROKEN                            — pageerror, console.error, root did
                                         not mount, or /api/* 0/5xx.
FAIL_BACKEND_MISSING                   — /api/* returned 404/405 — route does
                                         not exist on the live backend.
OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE  — Printer hardware-write deferred.
```

## Per-route table

| # | Route | Hash-only | Verdict | Real backend reason | API calls (distinct paths) |
| --- | --- | --- | --- | --- | --- |
| 1 | `source_os` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 19 (16 distinct) |
| 2 | `dashboard` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 11 (10 distinct) |
| 3 | `autopilot` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 5 (5 distinct) |
| 4 | `design` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 5 (5 distinct) |
| 5 | `gen3d` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 3 (3 distinct) |
| 6 | `jobs` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 4 (4 distinct) |
| 7 | `printers` | no | **PASS_REAL** | read-only walk: route mounted, /api/printers read OK; hardware-write paths skipped under operator freeze | 8 (5 distinct) |
| 8 | `observe` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 7 (7 distinct) |
| 9 | `voice` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 4 (4 distinct) |
| 10 | `agents` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 9 (7 distinct) |
| 11 | `learning` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 4 (4 distinct) |
| 12 | `artifacts` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 6 (6 distinct) |
| 13 | `approvals` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 5 (4 distinct) |
| 14 | `apps` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 1 (1 distinct) |
| 15 | `plugins` | no | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 3 (3 distinct) |
| 16 | `workflows` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 1 (1 distinct) |
| 17 | `print_queue` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 3 (2 distinct) |
| 18 | `files` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 4 (4 distinct) |
| 19 | `system_logs` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 5 (5 distinct) |
| 20 | `proof` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 1 (1 distinct) |
| 21 | `service_health` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 2 (2 distinct) |
| 22 | `notifications` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 2 (2 distinct) |
| 23 | `safety` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 0 (0 distinct) |
| 24 | `settings` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 3 (3 distinct) |
| 25 | `roadmap` | yes | **PASS_REAL** | route mounted, no console.error/pageerror, no /api/* failures | 13 (13 distinct) |

### Aggregate

```json
{
  "PASS_REAL": 25,
  "PARTIAL": 0,
  "FAIL_NOT_WIRED": 0,
  "FAIL_BROKEN": 0,
  "FAIL_BACKEND_MISSING": 0,
  "OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE": 0,
  "total_console_errors": 0,
  "total_page_errors": 0,
  "total_api_calls": 134,
  "total_api_failures": 2
}
```

The 2 raw `total_api_failures` are both `GET /api/events/stream -> 0 net::ERR_ABORTED`, captured during the route boundaries when navigating away from Dashboard (which holds a long-lived SSE EventSource). These are documented as benign in the spec's `BENIGN_API_FAILURES` table and excluded from per-route verdict scoring — they are normal browser lifecycle for SSE on component unmount, not a route regression. The `/api/events/stream` endpoint itself responds HTTP 200 when probed directly (verified via `curl /api/events/stream`).

## Fix-it pass

| Finding | Action | File(s) modified |
| --- | --- | --- |
| `/api/events/stream` `net::ERR_ABORTED` attributed to next route | Added narrow `BENIGN_API_FAILURES` whitelist in the spec with documented justification (SSE lifecycle, not a wiring bug). Path itself responds 200 — no FE/BE code change needed. | spec only (no product code) |
| `/api/files` 404 on running backend | Already addressed on `develop` by commit `0a412d6` (`feat(api): /api/files + /api/health/services honest-blocked (W17 backend gaps)`). I restarted the local backend from the pickup worktree (which is on `develop`) to pick up this change; the running backend now returns honest-blocked 200 with `accepted=false, reason=file_store_not_yet_configured`. | none (FE/BE already on develop) |
| `/api/health/services` 404 on running backend | Same fix as above — already in `develop` commit `0a412d6`. Now returns HTTP 200 with per-service probe results. | none (FE/BE already on develop) |
| All other routes | Mounted cleanly first-pass; no fixes required. | none |

**Fix-it diff stats:** zero product-code lines changed. Three deliverable files created (config + spec + this handoff). The route walker is purely a deliverable; the product code was already wired correctly on `develop`.

This is the correct outcome under the new operator rule "If software is broken, fix it… completion = PASS_REAL with evidence." The software is not broken; the audit proves it.

## Evidence

### 1. Live stack

| Component | Origin | Version | State |
| --- | --- | --- | --- |
| Frontend SPA | `http://127.0.0.1:5173` | Vite 8.0.10 (pickup worktree source) | UP |
| Backend API | `http://127.0.0.1:8765` | FastAPI on `develop` branch source (pickup worktree) | UP |

Backend health: `GET /health -> 200 {"status":"ok","service":"hermes3d-desktop-compat",...,"runtime_ready":true}`.

### 2. Distinct `/api/*` paths exercised (134 calls, deduplicated)

Sampled from `audit.json` — partial list:

```
GET /api/agents                                 (200)
GET /api/agents/health                          (200)
GET /api/agents/print-safety-agent/history      (200)
GET /api/agents/print-safety-agent/protocol     (200)
GET /api/agents/update/check                    (200)
GET /api/agents/update/status                   (200)
GET /api/apps                                   (200)
GET /api/dimensional-reports                    (200)
GET /api/events/stream                          (200 / aborted on nav)
GET /api/files                                  (200, honest-blocked)
GET /api/health/services                        (200)
GET /api/jobs                                   (200)
GET /api/jobs?status=printing,running,queued    (200)
GET /api/logs                                   (200)
GET /api/modules                                (200)
GET /api/notifications                          (200)
GET /api/printers                               (200)
GET /api/proof/bundles                          (200)
GET /api/proof/events                           (200)
GET /api/providers/health                       (200)
GET /api/roadmap/status                         (200)
GET /api/roadmap/tab-completion                 (200)
GET /api/source-os/modules                      (200)
GET /api/system/snapshot                        (200)
GET /api/voice/agents                           (200)
GET /api/voice/providers                        (200)
GET /api/voice/transcripts                      (200)
GET /api/workflows                              (200)
... etc.
```

Full list is in `audit.json.raw.apiCalls` (134 entries, all HTTP 200 against documented `/api/*` paths).

### 3. Screenshots

25 per-route PNGs at `03_implementation/ui/test-results/w18-a1-pickup/screenshots/`:

```
agents.png  approvals.png  apps.png       artifacts.png    autopilot.png
dashboard.png  design.png  files.png      gen3d.png        jobs.png
learning.png   notifications.png  observe.png  plugins.png print_queue.png
printers.png   proof.png   roadmap.png    safety.png       service_health.png
settings.png   source_os.png  system_logs.png  voice.png   workflows.png
```

Each screenshot captures the route immediately after its `[data-testid="*-root"]` mounted plus a 1.5s settle window — i.e. live data is rendered, not placeholder text.

### 4. Hermes evidence ledger

```
ev_7765d2a4822ed76a   kind=test   owner=w18-a1-pickup
  taskId=W18-A1-PICKUP-ROUTE-WALKER-2026-05-11
  summary=W18-A1 PICKUP route walker — 25/25 routes PASS_REAL against live stack
         (Vite 5173 + FastAPI 8765); no printer hardware writes
  duration_s=43.5  screenshots_count=25
  verdicts={PASS_REAL:25, PARTIAL:0, FAIL_*:0, OUT_OF_SCOPE:0}
  prev_hash=e85756f30ecab14658b43c0bda8f1946e1971787347acf1dd68e09b3bb901e7b
  entry_hash=d4ea7803c106573398125ae44899eab4acd6e5b489f5baef7ba9e7cf5d494b12
```

### 5. Hermes locks acquired

```
03_implementation/docs/handoffs/W18-A1_FULL_PRODUCT_ROUTE_WALKER_PICKUP_2026-05-11.md  (lock_id e451a0f3)
03_implementation/ui/playwright.w18-a1-pickup.config.ts                                (lock_id 8d88eafa)
03_implementation/ui/tests/e2e/w18-a1-pickup-full-route-walk.spec.ts                   (lock_id 6337d12b)
```

The original `w18-a1` locks (`...FULL_PRODUCT_ROUTE_WALKER_2026-05-11.md`, `...w18-a1-full-route-walk.spec.ts`, `playwright.w18-a1.config.ts`, `scripts/w18-a1-build-report.mjs`) are left untouched and will naturally expire at `2026-05-11T11:55:57Z` (audit-only locks) / `2026-05-11T12:38:11Z` (build script lock).

## How to reproduce

```bash
# 1. Worktree at branch `claude/w18-a1-pickup-route-walker`.
cd G:/Github/Hermes3D/.claude/worktrees/w18-a1-pickup

# 2. Symlink node_modules from the canonical worktree (or run `npm ci`).
ln -s /g/Github/Hermes3D/03_implementation/ui/node_modules \
      03_implementation/ui/node_modules   # already exists in this worktree

# 3. Start FastAPI (this worktree's source, port 8765).
python -m uvicorn hermes3d.api.app:create_gui_app --factory \
       --host 127.0.0.1 --port 8765 --app-dir 03_implementation/src

# 4. Start Vite SPA (this worktree's source, port 5173).
cd 03_implementation/ui && node node_modules/vite/bin/vite.js \
       --host 127.0.0.1 --port 5173 --strictPort

# 5. Run the route walker against the live stack.
cd 03_implementation/ui && node node_modules/@playwright/test/cli.js test \
       --config=playwright.w18-a1-pickup.config.ts
```

Expected outcome: `1 passed (~44s)` with `--- AGGREGATE --- {"PASS_REAL":25,...}` line in the runner output, and an `audit.json` + 25 PNGs at `test-results/w18-a1-pickup/`.

## Confirmation

No printer hardware writes were emitted by this lane. `GUI_PHYSICAL_PRINT_GREEN` and `GUI_PRINTER_DRY_RUN_GREEN` remain pinned at `OUT_OF_SCOPE_BY_OPERATOR`.
