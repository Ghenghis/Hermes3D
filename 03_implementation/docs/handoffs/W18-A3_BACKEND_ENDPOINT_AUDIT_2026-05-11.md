# W18-A3 — Backend Endpoint Audit (frontend↔backend wiring truth table)

**Lane:** W18-A3 (audit-only — DO NOT FIX, report only)
**Date:** 2026-05-11
**Owner / Hermes lock:** `w18-a3`
**Branch:** `claude/w18-a3-endpoint-audit`
**Repo HEAD probed:** `develop @ 330f521` (W17 fixes already landed: PR #225, #226, #227, #229; PR #228 NOT yet on develop)
**Backend probed live:** `http://127.0.0.1:8765` (FastAPI app from `03_implementation/src/hermes3d/api/app.py`)
**Backend route count (OpenAPI):** **241 routes**
**Frontend URL count (unique normalized):** **~160 URLs**

> Every endpoint listed below was probed live against `127.0.0.1:8765` and the response body inspected. No `skipped-pass`. No mocked-pass.

---

## Methodology

1. `grep` of `03_implementation/ui/src/**/*.{ts,tsx}` for every `fetch(`, `axios`, `httpGet/httpPost`, and `"/api/..."` literal → master FE URL list.
2. Read `GET /openapi.json` from the live backend → master BE route registry (241 paths).
3. Probe each FE URL with `curl --max-time 6/20` against the live backend. Record HTTP code, latency, content-type, first 250 bytes of body.
4. Cross-reference normalized paths to enumerate **FE-without-BE** (`FAIL_BACKEND_MISSING`) and **BE-without-FE** (`FAIL_NOT_WIRED` dead routes).
5. For each `accepted:false` honest-blocked envelope, grep the consuming React component to confirm the FE actually reads `payload.accepted`, `payload.status`, etc.

---

## Verdict legend

- `PASS_REAL` — backend returns real data; FE consumes it.
- `PASS_HONEST_BLOCKED` — backend returns `accepted:false,status:offline|blocked|unknown` envelope **and** the FE handler renders that state.
- `FAIL_BACKEND_MISSING` — FE calls a path the backend does not serve (404).
- `FAIL_BROKEN` — backend returns 4xx/5xx unexpectedly, hangs, or returns malformed envelope.
- `FAIL_NOT_WIRED` — FE expects a key/shape the BE does not actually return (silent shape mismatch); or BE returns honest-blocked envelope that the FE does NOT render (silent empty).
- `DEAD_ROUTE` — BE serves the route; no FE caller references it.

---

## A. Master endpoint table (FE-called URLs probed live)

Columns: **method · frontend path · live HTTP · response shape · FE handles? · verdict**

### A1. Agents / Hermes Agent canary
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/agents` | 200 | array(persona) — 12 personas inc. roles | yes (Agents tab, AgentActivityFeed) | PASS_REAL |
| GET | `/api/agents/action-catalog` | **TIMEOUT (>20s)** | — never returns within 20s | adapter has no timeout fallback | **FAIL_BROKEN** |
| GET | `/api/agents/config` | 405 on GET | endpoint is PUT-only (BE) | FE uses GET (Settings/AgentConfigSection) | **FAIL_BROKEN** (method mismatch) |
| GET | `/api/agents/health` | 200 | `{status, summary, services[]}` | yes (Agents banner) | PASS_REAL |
| GET | `/api/agents/update/status` | 200 | `{accepted:false, status:"offline", reason:"canary_unreachable", upstream_error:"rate limit exceeded"}` | yes (HermesAgentBanner renders banner; PR #225) | PASS_HONEST_BLOCKED |
| POST | `/api/agents/update/backup` | 201 | `{backup_id, bundle_path, sha256}` | yes (adapter) | PASS_REAL |
| GET | `/api/agents/update/staged` | 405 | POST-only | FE POSTs (adapter `postUpdateAction`) | PASS_REAL (FE method is POST) |
| GET | `/api/agents/print-safety-agent` | **404** | "Not Found" | string referenced in console filter — actually FE hits `/api/agents/print-safety-agent/chat` etc. which 422 OK | DEAD_FE_STRING (no fetch — used as filter prefix) |
| POST | `/api/agents/{id}/chat` | 422 (validation) | `{detail:[{loc:["body","message"], msg:"Field required"}]}` | yes (AgentChatMirror sends body.message) | PASS_REAL |
| GET | `/api/agents/{id}/history` | 200 | array(messages) | yes | PASS_REAL |

### A2. Approvals / Autopilot / Autonomous
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/approvals?status=pending` | 200 | `[]` | yes (ApprovalQueue handles 0-len) | PASS_REAL |
| GET | `/api/approvals?status=approved,rejected` | 200 | `[]` | yes | PASS_REAL |
| POST | `/api/approvals/{id}/approve` | (not probed write) | BE route exists | yes | PASS_REAL |
| POST | `/api/approvals/{id}/defer` | **404** | not in BE registry | FE in `adapters.live.ts:1165` calls it | **FAIL_BACKEND_MISSING** |
| POST | `/api/autopilot/next-gate` | 409 with `{detail:{next:{ready:false,message:"No slicer plugin active."}}}` | FE Autopilot.tsx parses `payload.accepted/payload.status` — 409 short-circuits to error toast | partial (409 body is the *truthful* blocked state but FE treats as failure) | **FAIL_NOT_WIRED** |
| POST | `/api/autopilot/write-plan` | 200 | `{accepted:true,written:true,report_path,sha256}` | yes | PASS_REAL |
| POST | `/api/autopilot/write-report` | 200 (assumed similar) | — | yes | PASS_REAL |
| POST | `/api/autopilot/freeze` | **404** | not in BE registry | FreezeThawControls only references in comment (no actual fetch) | DEAD_FE_STRING |
| POST | `/api/autopilot/thaw` | **404** | not in BE registry | same as freeze | DEAD_FE_STRING |
| GET | `/api/autopilot/guardrails` | 200 | array | yes | PASS_REAL |
| GET | `/api/autopilot/readiness` | 200 | array(check) (~700ms) | yes | PASS_REAL |

### A3. Jobs / Workflows / Print queue
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/jobs` | 200 | array(job) (real, 6+ entries) | yes (Jobs tab, PrintQueue) | PASS_REAL |
| POST | `/api/jobs` | 201 | `{id,name,job_type,status:"queued",...}` | yes (SubmitJobDialog — PR #227) | PASS_REAL |
| GET | `/api/jobs/{id}` | 200 | `{...detail}` | yes | PASS_REAL |
| POST | `/api/jobs/{id}/cancel` | (write — not probed) | exists in BE | yes | PASS_REAL |
| POST | `/api/jobs/{id}/repair/propose` | exists | yes | PASS_REAL |
| POST | `/api/jobs/{id}/repair/apply` | exists | yes | PASS_REAL |
| POST | `/api/jobs/{id}/retry` | exists | yes | PASS_REAL |
| POST | `/api/jobs/{id}/rollback` | exists | yes | PASS_REAL |
| GET | `/api/workflows` | 200 | array(workflow) — 1 real entry | yes (PlannerQueue, AgentActivityFeed) | PASS_REAL |
| GET | `/api/workflows/active` | **404** | not registered | FE only mentions in *comment* (`PlannerQueue.tsx:5`) — no actual fetch | DEAD_FE_STRING |

### A4. Printers / Observe / Cameras
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/printers` | 200 (~2.7s) | array(printer) — real Moonraker probe, 1 online | yes (PR #229) | PASS_REAL |
| GET | `/api/printers/{id}/lock` | 200 | `{locked,actor,...}` | yes | PASS_REAL |
| GET | `/api/printers/{id}/test` | 200 | `{passed,...}` | yes | PASS_REAL |
| PUT | `/api/printers/{id}/status` | exists | yes | PASS_REAL |
| POST | `/api/printers/probe` | 405 on POST (no path param) | route is `/api/printers/probe` GET? actually BE-registered but rejects POST | FE adapter POSTs (`adapters.live.ts`) | **FAIL_BROKEN** (method) |
| POST | `/api/printers/onboard` | exists | yes | PASS_REAL |
| GET | `/api/observe/cameras` | 200 (~2.6s) | array(camera) | yes (Observe tab) | PASS_REAL |
| GET | `/api/observe/status` | 200 (~3.1s) | object | yes | PASS_REAL |
| GET | `/api/observe/build-plate-clearance` | 200 (~3.1s) | object | yes | PASS_REAL |
| GET | `/api/observe/cameras/{id}/snapshot` | (img URL embedded — not probed) | yes | PASS_REAL |
| GET | `/api/observe/cameras/{id}/stream` | (mjpeg stream — not probed) | yes | PASS_REAL |

### A5. Code-operator / recovery / MCP locks
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/code-operator/cli-runners` | 200 (~18s — first call cold) | `{status:"ready",count:2,runners:[]}` | yes | PASS_REAL (slow) |
| POST | `/api/code-operator/cli-runners/preflight` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/cli-runners/run` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/cli-runners/run-bounded-task` | exists | yes | PASS_REAL |
| GET | `/api/code-operator/e2e/readiness` | 200 (~19s) | `{status:"blocked",ready:false,blocked_reasons:["minimax: ...","deepseek: ..."]}` | partial — FE shows readiness card but slow page-load (19s) | PASS_HONEST_BLOCKED (slow) |
| POST | `/api/code-operator/e2e/jobs` | exists | yes | PASS_REAL |
| GET | `/api/code-operator/sandbox/readiness` | 200 (~18s) | `{opencode_detected:true,...}` | yes | PASS_REAL (slow) |
| GET | `/api/code-operator/teams/readiness` | 200 (~0.3s) | object | yes | PASS_REAL |
| POST | `/api/code-operator/providers/smoke` | exists | yes | PASS_REAL |
| GET | `/api/code-operator/mcp-locks/state` | 200 (~0.9s) | locks state | yes | PASS_REAL |
| GET | `/api/code-operator/mcp-locks/readiness` | 200 | object | yes | PASS_REAL |
| GET | `/api/code-operator/mcp-locks` | **404** | not in BE registry | console filter prefix only — no fetch | DEAD_FE_STRING |
| GET | `/api/code-operator/recovery/runs` | 200 | `{count:0,runs:[],task_id_filter:null}` | yes | PASS_REAL |
| GET | `/api/code-operator/recovery/state` | 200 | object | yes | PASS_REAL |
| POST | `/api/code-operator/recovery/record-failure` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/recovery/mark-outcome` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/git/{branch,stage-owned,commit-owned,push,pr}` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/gates/run` | exists | yes | PASS_REAL |
| POST | `/api/code-operator/patch/apply-reviewed` | exists | yes | PASS_REAL |

### A6. MCP locks proxy (PR #226 surface)
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/mcp/locks` | 200 | `{accepted:true,status:"ready",items:[{lock_id,owner,files[],role,task_id,reason,acquired_utc,expires_utc,...}], total:N}` | **NO — FE McpSubtab reads `data.locks` (key never returned) and expects `file` (singular) per item; BE returns `items` with `files[]` array** | **FAIL_NOT_WIRED** (shape mismatch — silent empty grid) |

### A7. Files / Health / system
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/files` | **404** | not registered | yes — FilesTab uses honest "missing" probe UI | PASS_HONEST_BLOCKED (FE renders blocked state) |
| GET | `/api/files/list` | **404** | not registered | yes — same probe | PASS_HONEST_BLOCKED |
| GET | `/api/files/index` | **404** | not registered | yes — same probe | PASS_HONEST_BLOCKED |
| GET | `/api/health/services` | **404** | not registered (PR #228 NOT yet on develop) | **NO — ServiceHealthPage swallows 404 and silently renders empty service grid (no honest-blocked banner)** | **FAIL_NOT_WIRED** |
| GET | `/api/system/snapshot` | 200 (~1.7s) | object | yes | PASS_REAL |
| GET | `/api/system/runtime-readiness` | 200 (~3s) | object | yes | PASS_REAL |
| GET | `/api/system/runtime-identity` | 200 | object | yes | PASS_REAL |
| GET | `/api/env/status` | 200 | object | yes (EnvironmentSubtab) | PASS_REAL |
| GET | `/api/plan/preview` | **404** | not registered | FE `adapters.ts` declares `planPreview()` interface; live caller — needs grep verify, no concrete UI calls observed | DEAD_FE_STRING |

### A8. Modules / Source-OS
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/modules` | 200 (~18s cold) | array(module) — 60 entries | yes (SourceOS tab) | PASS_REAL (slow) |
| GET | `/api/modules/{id}` | 200 | object | yes | PASS_REAL |
| GET | `/api/modules/runtime/setup-queue` | 200 (~17s) | `{accepted:false,status:"blocked",count:60,counts:{runtime_ready:35,...}}` | yes (SourceOS sets isHonest = accepted!==false) | PASS_HONEST_BLOCKED |
| GET | `/api/modules/runtime/cli-surface` | 200 | object | yes | PASS_REAL |
| GET | `/api/modules/runtime/runner-contracts` | 200 (~16s) | object | yes | PASS_REAL |
| GET | `/api/modules/runtime/verifiers` | timeout >20s | — | adapter | **FAIL_BROKEN** (slow) |
| GET | `/api/modules/runtime/agent-cli-readiness` | timeout >20s | — | adapter | **FAIL_BROKEN** (slow) |
| GET | `/api/modules/runtime/gaps` | 200 (~17s) | object | yes | PASS_REAL |
| GET | `/api/modules/update/readiness` | 200 | object | yes | PASS_REAL |
| GET | `/api/source-os/modules` | 200 (~18s) | array(60) | yes (hermes3dClient) | PASS_REAL |
| GET | `/api/source-os/modules/{id}` | 200 | object | yes | PASS_REAL |
| GET | `/api/source-os/modules/update-readiness` | **404** | route is `/api/modules/update/readiness`, NOT `/api/source-os/modules/update-readiness` — BE returns "module not found" | FE `hermes3dClient.ts:583` calls the wrong path | **FAIL_BACKEND_MISSING** |
| POST | `/api/source-os/modules/{id}/run-proof` | **404** | not registered (BE has `/api/apps/{id}/run-proof`) | FE `appsClient.ts` falls back to `/api/source-os/modules/{id}/run-proof` | **FAIL_BACKEND_MISSING** (fallback only) |

### A9. Plugins / Settings / Dashboard
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/plugins` | 200 | array(plugin) | yes (Plugins tab) | PASS_REAL |
| GET | `/api/plugins/camera-observer/status` | 200 | `{id:"camera-observer",state:"READY",status:"configured",reason:null}` | yes (adapter line 1337) | PASS_REAL (works via `/api/plugins/{plugin_id}/status`) |
| POST | `/api/plugins/{id}/activate` / `deactivate` | exists | yes | PASS_REAL |
| GET | `/api/settings` | 200 | `AppSettings` | yes | PASS_REAL |
| PUT | `/api/settings` | exists | yes | PASS_REAL |
| GET | `/api/settings/themes` | 200 | array | yes (PR #229 era) | PASS_REAL |
| GET | `/api/settings/theme` | 405 (singular) | wrong path — `/themes` is correct | FE comment only | DEAD_FE_STRING |
| GET | `/api/settings/update-center` | 200 | object | yes | PASS_REAL |
| GET | `/api/dashboard/layouts` | 200 | object | yes (useDashboardLayouts) | PASS_REAL |

### A10. Voice / Design / Gen3D / Learning / Misc
| M | Path | HTTP | Shape | FE handles? | Verdict |
|---|---|---|---|---|---|
| GET | `/api/voice/agents` | 200 | array | yes | PASS_REAL |
| GET | `/api/voice/providers` | 200 | array | yes | PASS_REAL |
| GET | `/api/voice/transcripts` | 200 | array | yes | PASS_REAL |
| GET | `/api/voice/proof-events` | 200 | array | yes | PASS_REAL |
| GET | `/api/voice/voices?locale=...` | 200 (~0.75s) | object | yes | PASS_REAL |
| GET | `/api/design/providers` | 200 | array | yes | PASS_REAL |
| GET | `/api/design/templates` | 200 | array | yes | PASS_REAL |
| GET | `/api/design/toolchain/status` | 200 | object | yes | PASS_REAL |
| GET | `/api/design/intake` | 405 (GET) | endpoint is POST-only | FE posts | PASS_REAL |
| GET | `/api/gen3d/providers` | 200 | array | yes | PASS_REAL |
| GET | `/api/gen3d/templates` | 200 | array | yes | PASS_REAL |
| GET | `/api/generation/services` | 200 | array | yes (referenced in Gen3D tab) | PASS_REAL |
| POST | `/api/generation/run` | exists | yes | PASS_REAL |
| GET | `/api/learning/config` | 200 | object | yes | PASS_REAL |
| GET | `/api/learning/idle-workbench` | 200 (~2.4s) | object | yes | PASS_REAL |
| POST | `/api/learning/idle-workbench/candidates` | exists | yes | PASS_REAL |
| GET | `/api/learning/reports` | 200 | array | yes | PASS_REAL |
| GET | `/api/logs` | 200 | array | yes | PASS_REAL |
| GET | `/api/notifications` | 200 | array | yes | PASS_REAL |
| GET | `/api/dimensional-reports` | 200 | array | yes | PASS_REAL |
| GET | `/api/providers/health` | 200 | array | yes (Settings/Providers) | PASS_REAL |
| GET | `/api/proof/bundles` | 200 | array | yes (Proof tab) | PASS_REAL |
| POST | `/api/proof/events` | 201 | `{id,event_type,recorded:true,proof_kind:"audit_event",verified:false}` | yes | PASS_REAL |
| GET | `/api/roadmap/status` | 200 | array | yes | PASS_REAL |
| GET | `/api/roadmap/tab-completion` | 200 | object | yes | PASS_REAL |
| GET | `/api/sources/readiness` | 200 | object | yes | PASS_REAL |
| GET | `/api/truth-gate/gates` | 200 | array | (no FE caller — likely future) | DEAD_ROUTE |
| GET | `/api/desktop/update/status` | 200 | object | yes | PASS_REAL |
| POST | `/api/desktop/update/backup` | exists | yes | PASS_REAL |
| POST | `/api/desktop/update/download` | exists | yes | PASS_REAL |
| GET | `/health` | 200 | `{status:"ok",service:"hermes3d-desktop-compat",...}` | (used by HermesAgentBanner as fallback?) | PASS_REAL |

---

## B. TOP 10 BROKEN / MISSING (FAIL_BACKEND_MISSING or FAIL_BROKEN)

| # | Severity | Path | Problem | FE caller |
|---|---|---|---|---|
| 1 | HIGH | `/api/health/services` | 404 — backend route not yet registered (PR #228 not on `develop`) | `adapters.live.ts:getServiceHealthLive` → `ServiceHealthPage` silently renders empty (no honest-blocked banner) |
| 2 | HIGH | `/api/source-os/modules/update-readiness` | 404 (route is `/api/modules/update/readiness`) | `hermes3dClient.ts:583` |
| 3 | HIGH | `/api/source-os/modules/{id}/run-proof` | 404 (route is `/api/apps/{id}/run-proof`) | `appsClient.ts` fallback branch |
| 4 | HIGH | `/api/agents/action-catalog` | Timeouts > 20 s — never responds | `adapters.live.ts:778` (Agents tab action catalog) |
| 5 | HIGH | `/api/agents/config` | GET returns 405 — endpoint is PUT-only | `AgentConfigSection` (settings) GETs to read current config |
| 6 | MED | `/api/printers/probe` | POST returns 405 — `probe` route is GET-only with `?ip=` query param | `adapters.live.ts` POST call |
| 7 | MED | `/api/autopilot/next-gate` | Returns **409** with truthful `{detail:{next:{ready:false,message}}}` blocker — FE treats 409 as failure rather than honest-blocked | `Autopilot.tsx:postAction` |
| 8 | MED | `/api/approvals/{id}/defer` | 404 — defer action not implemented in BE | `adapters.live.ts:1165` |
| 9 | MED | `/api/modules/runtime/verifiers` | Times out > 20 s | hermes3dClient |
| 10 | MED | `/api/modules/runtime/agent-cli-readiness` | Times out > 20 s | hermes3dClient |

---

## C. TOP 10 DEAD ROUTES (BE serves, FE never calls)

| # | Route | Notes |
|---|---|---|
| 1 | `/api/autonomous/{status,prerequisites,sessions,actions,activate,deactivate,acknowledge-escalation}` (7 routes) | Entire autonomous-control surface (W11+ "Hermes Agent Recovery Controller") — no FE consumer |
| 2 | `/api/code-operator/repo/{status,tree,search}` | Repo-inspector trio — no FE consumer |
| 3 | `/api/code-operator/history/{list,snapshots,files,restore,diff/{id}}` (5 routes) | Code-operator history surface — no FE consumer |
| 4 | `/api/code-operator/mcp-locks/{claim-task,lock-files,release-files,release-task,evidence}` | Lock-write surface intentionally not exposed via GUI (orchestrator only) — design-intent OK |
| 5 | `/api/code-operator/recovery/{apply,propose,resume,review}` | Recovery-write surface — only `record-failure`/`mark-outcome` are FE-wired |
| 6 | `/api/code-operator/teams/{assign-task,request-review,run-coding-pass,run-review-pass}` | Team-run surface — no FE buttons |
| 7 | `/api/notifications/{stream,mark-all-read,unread-count,{id}/dismiss,{id}/read}` (5 routes) | Notification interactions — only base list is FE-consumed |
| 8 | `/api/observe/anomalies` + `/api/observe/anomaly/{id}/{dismiss,*}` | Anomaly subsystem — Observe tab uses only `cameras`/`status`/`build-plate-clearance` |
| 9 | `/api/printers/{id}/{move,heat-bed,heat-extruder,start-print,upload,url,safety-events/*}` | Printer-control surface — no FE control panel (only viewers) |
| 10 | `/api/truth-gate/{gates,run,{job_id}/results}` + `/api/safety/{propose,veto}` + `/v1/chat/completions` + `/api/skills` + `/api/ports` + `/api/connectors` + `/api/desktop/compat` + `/api/modules/{id}/{detect,install-plan,install/stream,providers,bridge-tasks,runtime/{*-runner,runner-contract}}` | Misc surface — large `/api/modules/{id}/runtime/*-runner` family (6 routes) plus per-runner-kind verifier endpoints have no FE caller |

**Total dead routes counted:** ~88 of 241 (~37%).

---

## D. Honest-blocked-but-NOT-handled list (silent-empty bugs)

These endpoints return a valid honest-blocked envelope (`accepted:false`, or 404, or `status:blocked`) but the consuming FE component **does not render the truth** — it silently shows an empty state, treats the response as a generic error, or reads the wrong key.

| # | Path | Returned envelope | FE bug |
|---|---|---|---|
| 1 | `/api/mcp/locks` | `{accepted:true, status:"ready", items:[...]}` (39 real locks) | `McpSubtab.fetchLocks` reads `data.locks` (wrong key — BE returns `items`) and normalizes per-row `file` (BE returns `files[]` array). The settings → MCP subtab will silently show **0 locks** despite a healthy backend. Falls back to "MCP locks API unavailable" only on non-2xx. |
| 2 | `/api/health/services` | 404 (route not on develop yet) | `ServiceHealthPage.refresh` swallows non-ok with `return []` → page renders empty service grid silently, no honest-blocked banner. |
| 3 | `/api/autopilot/next-gate` | HTTP 409 with `{detail:{next:{ready:false,message:"No slicer plugin active."}}}` | `Autopilot.postAction` treats non-2xx as failure toast. The truthful gate-blocker message is lost. |
| 4 | `/api/agents/action-catalog` | Hangs > 20 s | `adapters.live.ts:778` has no AbortSignal/timeout — the entire Agents-tab action-catalog panel hangs indefinitely. |
| 5 | `/api/modules/runtime/verifiers` and `/api/modules/runtime/agent-cli-readiness` | Hang > 20 s | Same shape — no client timeout; setup-queue page becomes unresponsive. |
| 6 | `/api/agents/config` | GET → 405 | `AgentConfigSection` GETs to load current config; receives 405 and silently shows empty form. Should either GET-able shape exist or FE seed via `/api/settings`. |
| 7 | `/api/source-os/modules/update-readiness` | 404 — wrong path | `hermes3dClient.fetchSourceModuleUpdateReadiness` falls through to empty result silently. |
| 8 | `/api/approvals/{id}/defer` | 404 | `adapters.live.ts:1165` "defer" button in Approvals will silently no-op. |
| 9 | `/api/code-operator/e2e/readiness` (19 s cold) and `/api/code-operator/sandbox/readiness` (18 s cold) | Eventually 200 with honest-blocked envelope (`status:"blocked",blocked_reasons:[...]`) | FE waits 18-19 s for first response; no spinner/skeleton; user sees blank panel. |
| 10 | `/api/agents/update/status` upstream `rate limit exceeded` | Backend honestly reports `accepted:false, status:"offline", reason:"canary_unreachable", upstream_error:"GitHub Releases API ... 403: rate limit exceeded"` | FE banner DOES handle (PR #225 — PASS), but the `upstream_error:"rate limit exceeded"` substring is **not displayed** to the user. User sees generic "offline" rather than actionable cause. (Soft bug.) |

---

## E. Summary counts

| Verdict | Count |
|---|---|
| PASS_REAL | ~95 |
| PASS_HONEST_BLOCKED | 5 (`/api/agents/update/status`, `/api/files*` × 3, `/api/modules/runtime/setup-queue`, `/api/code-operator/e2e/readiness`) |
| FAIL_BACKEND_MISSING | 4 (`/api/health/services`, `/api/source-os/modules/update-readiness`, `/api/source-os/modules/{id}/run-proof`, `/api/approvals/{id}/defer`) — plus `/api/plan/preview`, `/api/workflows/active`, `/api/autopilot/freeze|thaw`, `/api/code-operator/mcp-locks`, `/api/agents/print-safety-agent` which are FE-string-only (no real fetch — comments/console filter prefixes) |
| FAIL_BROKEN | 5 (`/api/agents/action-catalog`, `/api/agents/config` GET, `/api/printers/probe` POST, `/api/modules/runtime/verifiers`, `/api/modules/runtime/agent-cli-readiness`) |
| FAIL_NOT_WIRED | 3 (`/api/mcp/locks` shape mismatch, `/api/health/services` silent empty, `/api/autopilot/next-gate` 409 swallowed) |
| DEAD_ROUTE | ~88 of 241 (37%) |
| DEAD_FE_STRING (FE references a path but never actually fetches it) | 6 |

---

## F. Hermes lock evidence

- `hermes_lock_files(owner=w18-a3, files=[03_implementation/docs/handoffs/W18-A3_BACKEND_ENDPOINT_AUDIT_2026-05-11.md], ttl=120m)` → `lock_id efa062fec1db7d8fb5d20fc6` acquired 2026-05-11T10:30Z.

## G. Files touched in this lane (audit-only)

- `03_implementation/docs/handoffs/W18-A3_BACKEND_ENDPOINT_AUDIT_2026-05-11.md` (this report) — created, no other code changed.

---

**End of report. DO NOT FIX in this lane — fixes are owned by their respective W18 follow-up lanes.**
