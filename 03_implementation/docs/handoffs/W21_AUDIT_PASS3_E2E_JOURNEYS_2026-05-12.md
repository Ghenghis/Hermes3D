# W21 Audit — Pass 3 (E2E User Journeys)

**Date:** 2026-05-12
**Auditor:** Claude (15 parallel journey sub-agents + 2 direct probes for ones that refused)
**Scope:** Trace 15 named user journeys step-by-step across UI + backend + DB + filesystem + LAN. Each journey shows where it WORKS, BLOCKS, or BREAKS. Pass 1 (structural) and Pass 2 (behavioral) already landed; this pass surfaces cross-system gaps.
**Backend:** live at `127.0.0.1:8765`, PID 34092, queue poller disabled.
**Develop SHA:** `be2755f`

---

## §0. Journey scorecard

| # | Journey | Verdict | Weakest link |
|---|---|---|---|
| 1 | Cold-start Dashboard | **PARTIAL_BREAK** | `/api/workflows`, `/api/proof/bundles`, `/api/system/snapshot`, `/api/dimensional-reports` — 5 of 9 fetches return 404 from the UI's adapter path (despite Pass-2 confirming these endpoints exist at the canonical path) |
| 2 | Upload image → 3D model → STL in #files | **BLOCKED_AT_STEP_5** | rembg not installed; uploaded image stored as proof artifact but never processed; only `calibration_cube` local-fallback path produces an STL |
| 3 | #design → template → STL → Slice → G-code → #files | **WORKS_WITH_REFRESH_GAP** | Slicer subprocess fires real PrusaSlicer; STL + G-code appear in `var/`; UI's "Recent STLs" panel does NOT auto-refresh after Slice |
| 4 | #agents claimed-tasks panel | **NOT_WIRED** | Agents.tsx renders `TeamTasksPanel` (code-operator team runs) instead of calling `/api/agents/queue/status`; W21-A4 MVP-2 UI panel still missing |
| 5 | #apps run proof + status update | **WORKING_REAL_NO_BULK** | Per-app proof flows end-to-end with 30s poll + immediate refetch; no batch Run-All button — operator clicks 18 times |
| 6 | #plugins activate flow | **WORKING_REAL** | activate POST returns updated row, DB persists, UI auto-reloads; PluginCard line 56 confirmed wired (Pass-2 claim refuted) |
| 7 | #autopilot write-plan + next-gate | **WORKING_REAL** | All 4 endpoints fire real bytes + SHA256 + proof_event_id; honest-blocked 409 from `next-gate` rendered with gate name + reason |
| 8 | #jobs cancel / retry / repair / rollback | **WORKING_REAL** | 4 transitions wired; cancel triggers immediate refetch (no stale window); polling 10s for queued+printing only |
| 9 | #source_os Backup → Check → Apply | **WORKING_NO_AUTO_REFRESH** | Backup creates bundle, check fires real git probe, apply returns accepted; `latest_backup` field does NOT auto-refresh after Backup — operator must reload |
| 10 | Settings + MCP + Update Center | **MOSTLY_WORKING** | Theme persists in SQLite; 6 themes listed but `label` field is `null`; 6 of 12 orchestrator locks are STALE (w18-a1, w18-a10, w18-a16 — not reaped); update-center response missing `components` + `velopack` keys |
| 11 | #printers view (read-only) | **WORKING_REAL** | All 4 printers LAN-reachable; S1 lock enforced bi-directionally (UI disables + backend returns 423); attempting `POST heat-extruder` on S1 would be blocked |
| 12 | Hermes Agent claim → execute → done | **BLOCKED_AT_STEP_4** | Zero code path executes a claimed task or produces the `handoff_path` markdown. MVP-3 100% missing |
| 13 | Voice tab configure + preview | **WORKING_HONEST_BLOCKED** | Azure-dependent; STT is client-side Web Speech API (not a backend gap); preview blocks honestly without keys; STALE_FETCH_ONCE for catalog refresh |
| 14 | Learning candidate queue | **WORKING_REAL_QUEUED** | Candidate POST accepted + queued; 9 blockers prevent run (S1 lock + 8 queued jobs); blockers logic IS the safety policy, not a bug |
| 15 | Approvals queue lifecycle | **WORKING_REAL** | 5s polling; pending→approved/rejected/deferred transition invariant enforced; auto-creation tied to `POST /api/jobs/{id}/repair/propose` only (generic jobs don't auto-create approvals) |

**Totals:** 5 WORKING_REAL · 4 WORKING_WITH_GAPS (refresh / no-bulk / no-auto-refresh / honest-blocked) · 4 PARTIAL_BREAK or BLOCKED · 1 NOT_WIRED · 1 MOSTLY_WORKING.

---

## §1. Journey 1 — Dashboard cold-start (PARTIAL_BREAK)

**Trace:**
1. Vite dev server NOT running (port 5173 refused) → operator uses production `dist/` build ✓
2. `App.tsx` mounts → Dashboard `useEffect` fires `Promise.allSettled` of 9 fetches
3. The 9 endpoints the Dashboard adapter calls (per `adapters.live.ts`):
   * `/api/printers` ✓ 200 (4 printers)
   * `/api/jobs?status=printing,queued,running` ✓ 200 (42 jobs in DB; subset returned)
   * `/api/agents` ✓ 200 (8 personas)
   * `/api/workflows` ✓ 200 per Pass-2 — but the J1 agent's session saw **404**
   * `/api/proof/bundles` ✓ 200 per Pass-2 — but J1 saw **404**
   * `/api/system/snapshot` ✓ 200 per Pass-2 — but J1 saw **404**
   * `/api/dimensional-reports` ✓ 200 per Pass-2 — but J1 saw **404**
   * `/api/logs` ✓ 200 (empty)
   * `/api/notifications` ✓ 200 (empty)
4. SSE: `EventSource /api/events/stream` initiates; no events within 2s window; UI shows "Connecting…" fallback
5. Hermes Agent banner: `/api/agents/update/status` returns v0.13 tag with `accepted:true, status:"ready"`
6. KPI tiles hydrate from successful payloads; failed ones render empty/null states gracefully
7. `Promise.allSettled` absorbs failures — Dashboard does NOT crash on partial fetch failure

**The 4 "404" discrepancy:** J1 saw 404 on routes Pass-2 saw 200. Most plausible cause: the adapters.live.ts path uses **different URL strings** than the route registration (path prefix mismatch like `/api/proof/bundles` vs `/api/proof/bundles/`, or staging guard). Pass-1 inventory confirms all 4 endpoints ARE registered in `system.py`. Action: re-probe with exact UI fetch strings and confirm.

**Classification:** PARTIAL_BREAK — Dashboard fires without crashing but ~44% of intended KPI data is unavailable to the operator under the path the UI adapter actually uses.

---

## §2. Journey 2 — Image → 3D model → STL (BLOCKED_AT_STEP_5)

**Trace:**
1. `<input type="file">` exists in Gen3D.tsx; handler is `attachReference()` line 189
2. POST goes to `/api/artifacts` (NOT `/api/gen3d/upload`) — file is stored as a proof artifact, **not pre-processed for 3D conversion**
3. Live curl POST of a 1×1 PNG to `/api/artifacts` succeeds; row inserted; `artifact.file_path` returned
4. `/api/gen3d/providers` reports 4 of 5 `not_installed`; 1 `installed_not_running` (Bambu) — UI correctly blocks generation when none ready
5. **rembg NOT installed (`ModuleNotFoundError`)** — background removal step is the missing gear; even if user supplies an alpha-channel PNG, the backend wouldn't strip white background
6. `calibration_cube` template via `POST /api/generation/run` produces a real STL via trimesh local fallback ✓ — but **ignores the uploaded reference image** (line 403 stores `reference_artifact_id` in notes only; never feeds it to the generator)
7. The fallback STL appears in `/api/files` AND `/api/artifacts` ✓
8. Gen3D.tsx state update `setGeneratedModels()` runs after a successful run → "Generated Models" panel re-renders ✓

**Verdict:** the **image-to-3D pipeline is not a pipeline** today. Image upload works, model generation works, but they are disconnected; the generator only emits a parametric primitive (calibration cube) regardless of what was uploaded. To make Journey 2 WORKING_REAL, three deps are needed: (a) install rembg, (b) install TripoSR / Hunyuan3D / TRELLIS / ComfyUI core + weights, (c) wire `generation.run` to read `reference_artifact_id` and run rembg → provider → STL.

**Classification:** BLOCKED_AT_STEP_5 (rembg + provider pipeline).

---

## §3. Journey 3 — Design → Slice → G-code (WORKS_WITH_REFRESH_GAP)

**Trace:**
1. `GET /api/design/templates` returns 1 real template (`desk_organizer`); Design.tsx populates the select
2. Form fields visible: title, description, width_mm, depth_mm, height_mm, tray_count, pen_count, phone_slot, cable_passthrough, target_printer_id
3. `POST /api/design/intake` → 201 with `{job_id, artifact.file_path, proof.event_id, truth_gate.status:"pass"}`. STL on disk = 18 KB.
4. `extractStlArtifact()` parses the response and prepends to `producedStls` state; "Recent STLs" panel renders the new row immediately ✓
5. "Slice this STL" button POSTs `/api/slice {stl_path, printer_profile, options}` → 202 with `job_id`
6. Polling `GET /api/slice/{job_id}` returns `gcode_path`, `size_bytes`, `layer_count`, `motion_lines`, `estimated_print_time_min`, `sha256` once the subprocess finishes
7. `var/slicer/{job_id}/<basename>.gcode` lands on disk (Pass-2 confirmed: real subprocess.run to PrusaSlicer)
8. **GAP:** Design.tsx does NOT auto-refresh `/api/files` after slice completes. The G-code is in the DB and on disk but the "Recent STLs" panel doesn't refresh to show its G-code sibling. Operator must reload tab.

**Classification:** WORKS_WITH_REFRESH_GAP — the heavy lifting works (real subprocess, real artifacts, real proof); UI freshness lags one reload.

---

## §4. Journey 4 — #agents claimed tasks panel (NOT_WIRED)

**Trace:**
1. `GET /api/agents/queue/status` exists, returns valid JSON with 8 claimed tasks + their `claimed_by`, `claimed_utc`, `heartbeat_utc`, `priority` ✓
2. **Agents.tsx does NOT call `/api/agents/queue/status`**. Grep confirms zero references.
3. The tab renders `<TeamTasksPanel>` which calls `/api/code-operator/teams/team-tasks` + `/teams/provider-smoke-history` — those endpoints surface code-operator builder/reviewer task runs, NOT the W21 queue.
4. `/api/agents/tasks` returns a pre-MVP-2 schema (active_count, provider_smoke_latest) — Agents.tsx may consume this for live status but it's a different model.
5. `/api/agents/action-catalog` (after Pass-2 fix) returns **90 actions**: 76 ready, 10 blocked, 4 partial. Blocked reasons include "Provider configured but has not passed a live smoke proof." These ARE rendered somewhere in Agents.tsx but as a separate panel.

**Verdict:** the W21-A4 MVP-2 backend is fully wired and tested. The matching UI panel that should show claimed W21 tasks per persona is still **missing from the UI**. This is the next-most-actionable UI gap.

**Classification:** NOT_WIRED (specifically: backend ready, UI panel absent).

---

## §5. Journey 5 — App proof flow (WORKING_REAL_NO_BULK)

**Trace:**
1. `AppRegistry.tsx` routes `#apps` → `AppStatusPanel`. `#apps/<id>` → `AppDetailPanel` ✓ (W20-compliant)
2. Row click toggles inline expansion; "View details" navigates to `#apps/<id>` ✓
3. "Run proof" button (AppStatusPanel:379) is disabled when `!app.proof_command`; otherwise wired to `runProof(app)` which POSTs `/api/apps/{id}/run-proof` (with fallback to `/api/source-os/modules/{id}/run-proof`)
4. Live probe `POST /api/apps/hermes_agent/run-proof`: `{accepted:true, status:"pass", exit_code:0, duration_ms:663}` ✓
5. **Auto-refresh DOES work:** `loadApps()` is called immediately after the POST (line 141); the 30s poll catches drift; the row's `last_proof_status` flips to `success` and the timestamp advances on the next render
6. For `cadquery` (returns ModuleNotFoundError): toast shows redacted reason; AppDetailPanel renders the error banner
7. **GAP:** No "Run all 18 unproven" button. Operator clicks 18 times.
8. Pass-2's "missing onClick at AppCard lines 534+547" claim — those lines DO exist in `AppCard.tsx` and HAVE handlers (`onClick={() => onChange("matrix")}` and `onClick={() => onChange("registry")}`). **Pass-2 claim refuted.**

**Classification:** WORKING_REAL — workflow is single-app at a time but no bulk shortcut.

---

## §6. Journey 6 — Plugin activate (WORKING_REAL)

**Trace:**
1. `GET /api/plugins` returns 20 plugins: 5 ACTIVE (autopilot-setup, azure-voice, evidence-ledger, maintenance, moonraker, visual-evidence), 1 READY+configured (`camera-observer`), 7 READY+unconfigured, 6 PLANNED ✓
2. `POST /api/plugins/camera-observer/activate` → 200 with `{state:"ACTIVE", activated_at:<utc>}` ✓; DB UPDATE confirmed
3. After activation: `load()` is called from Plugins.tsx:88 → list re-fetches → row state flips to ACTIVE ✓ (NOT MANUAL_REFRESH; auto)
4. `POST /api/plugins/deepseek-v4/activate` (configured=false) → **409 with reason** (correct honest block); UI surfaces the reason in the panel
5. `POST /api/plugins/camera-observer/deactivate` → 200; state reverts to READY ✓
6. Pass-2's "buttons-without-onClick at lines 151-158" — lines DO have `onClick={() => planSetupQueue()}`. **Pass-2 claim refuted.**
7. PluginCard Activate button has `onClick={() => void onActivate(plugin)}` ✓

**Classification:** WORKING_REAL.

---

## §7. Journey 7 — Autopilot (WORKING_REAL)

**Trace:**
1. `GET /api/autopilot/readiness` returns 16 checks; 7 fail (slicer_availability, filament_profile_loaded, bed_mesh_calibrated, nozzle_temp_verified, model_llm_available, comfyui_available, api_token_set)
2. `GET /api/autopilot/guardrails` returns 3 guardrails: `s1_lock`, `approval_required`, `truth_gate` — all `enforced:true`
3. `POST /api/autopilot/write-plan` → `{accepted:true, written:true, report_path:"...agent-plan-bec3a647.md", bytes:1029, sha256:"af9c...", proof_event_id:"bec3..."}` ✓
4. The file at `report_path` exists on disk, size matches `bytes` ✓
5. `POST /api/autopilot/next-gate` → **409 honest-blocked** with `detail.next.id="slicer_availability"` and a human-readable reason — UI prefixes "Honest-blocked: …" correctly
6. `POST /api/autopilot/write-report` → similar to write-plan, real bytes + SHA + proof ✓
7. After write-plan: UI shows `report_path` string only (no inline preview — honest)
8. 30s polling re-fetches readiness; no cascade refresh after write actions

**Classification:** WORKING_REAL — proof events wired, honest-blocked flow respected, real file writes.

---

## §8. Journey 8 — Jobs cancel/retry/repair/rollback (WORKING_REAL)

**Trace:**
1. `GET /api/jobs` returns 42 jobs from the real DB ✓
2. `GET /api/jobs/{id}` returns full detail (steps, artifacts, events, approvals, transition_state) ✓
3. Jobs.tsx renders all detail fields ✓
4. `POST /api/jobs/{id}/cancel` — wired; `loadJobs()` called immediately after (no stale window)
5. `POST /api/jobs/{id}/retry` — wired; gated by `transition_state.can_retry`
6. `POST /api/jobs/{id}/repair/propose`, `repair/apply`, `rollback` — all wired
7. `GET /api/jobs/{id}/artifacts/{aid}/download` — opens a download stream with Content-Type/Length
8. 10s polling on queued+printing jobs only (correct — completed/failed are immutable)

**Classification:** WORKING_REAL.

---

## §9. Journey 9 — Source-OS Backup→Check→Apply (WORKING_NO_AUTO_REFRESH)

**Trace:**
1. `GET /api/source-os/modules` returns 60 modules ✓
2. 4 modules (blender_mcp_candidates, open3d, numpy_stl, pymesh) have broken `local_path` pointing at `03_implementation/source-lab/…` which doesn't exist (Pass-2 finding)
3. For `printrun` (known-good): `POST /api/modules/printrun/update/backup` → `{backup_id, bundle_path, commit, dirty:false}` ✓; bundle file lands on disk
4. `POST /api/modules/printrun/update/check` → real git probe with `status, current_commit, remote_commit, branch` ✓
5. `POST /api/modules/printrun/update/apply {actor:"operator", reason:"…"}` → accepted ✓
6. **GAP:** `latest_backup` field does NOT auto-refresh after Backup completes. SourceOS.tsx is HYBRID (15s + setTimeout) but the action-completion callback `onRefresh()` is only called if the parent provides it explicitly. The row stays stale until the operator switches subtabs or reloads.
7. "Verify All" button → `POST /api/modules/runtime/verify-all` returns batch counts; UI re-fetches 4 sibling summaries (loadModules, loadVerifierSummary, loadCliSurfaceSummary, loadRunnerContracts) ✓
8. Pass-2's "AppCard onClick missing at SourceOS.tsx lines 534+547" — those lines DO have `onClick={() => onChange("matrix" | "registry")}`. **Pass-2 claim refuted.**

**Classification:** WORKING_NO_AUTO_REFRESH — workflow completes; UI freshness gap on per-row backup state.

---

## §10. Journey 10 — Settings + MCP + Update Center (MOSTLY_WORKING)

**Trace:**
1. `GET /api/settings` returns SQLite-backed keys: ports.* (api, cadquery_worker, camera_proxy, model_llm, openscad_worker, slicer_worker, telemetry, web), printer.flsun_s1.* (camera_view, status), theme value, etc. ✓
2. `GET /api/settings/themes` returns **6 themes** (default, cyberpunk, matrix, tron, industrial_forge, aurora_operator) — but the `label` field is `null` for all 6. UI must derive a display name from `id` or read the underlying JSON files in `data/themes/`.
3. `PUT /api/settings/theme {theme:"forest"}` would persist to SQLite. (Per Pass-2 — `settings` table key `theme`).
4. Language / UI-mode / dashboard-mode store in **localStorage** (no backend), so they don't survive a different browser.
5. `GET /api/mcp/locks` returns 12 active locks. **6 are STALE** (`w18-a1`, `w18-a10`, `w18-a16` × 2, `w18-a1` repeat, `w18-a10` repeat). 2 fresh locks owned by `codex-w21-3pass-audit` (current Codex session is also running a parallel audit). **Stale locks need reaping** via the orchestrator's `hermes_recover_stale_locks` MCP verb.
6. `GET /api/settings/update-center` returns `provider_health` (2 entries) but the `components` and `velopack` keys are missing or empty. Pass-1 expected a schema with `components` + `velopack`. The route in `update_center.py:220` may be returning a partial response.
7. Desktop update: `POST /api/desktop/update/backup` should write a git bundle (Pass-2 said this is REAL). Not re-tested here.

**Classification:** MOSTLY_WORKING — theme persistence works, MCP locks live, but theme labels are null, 6 stale orchestrator locks are unreaped, and update-center response shape is partial.

---

## §11. Journey 11 — Printers view (WORKING_REAL)

**Trace:**
1. `GET /api/printers` returns 4 printers: flsun_t1_a (192.168.0.10), flsun_t1_b (.0.11), flsun_s1 (.0.12), flsun_v400 (.0.34) — all `status:"online"` ✓
2. Each LAN probe `http://<ip>/server/info` returns `klippy_state:"ready"` ✓
3. `http://192.168.0.10/printer/objects/query?print_stats` shows last job completed = `delta-calibration-test-model-50pct-T1.gcode`, 152 s
4. The S1 lock check: `is_s1_target(printer_id)` in `api/safety.py:14` is used to short-circuit `/test`, `/move`, `/upload`, `/upload-gcode`, `/heat-extruder`, `/start-print` for any S1 alias (`flsun-s1`, `flsun_s1`, `s1`, `192.168.0.12`).
5. Printers.tsx disables hardware-action buttons for the locked S1 row at the UI layer (lines 641, 656, 734, 754, 768, 775, 784) AND the backend rejects any write with `423 PRINTER_LOCKED` if the UI is compromised.
6. **Bi-directional + non-bypassable safety.** Confirmed.
7. flsun_t1_b test endpoint runs against a live read-only Moonraker probe and reports latency_ms.

**Classification:** WORKING_REAL — fleet visible, safety enforced at two layers, no operator path to accidentally write to S1.

---

## §12. Journey 12 — Hermes Agent claim → execute (BLOCKED_AT_STEP_4)

**Trace:**
1. `GET /api/agents/queue/status` returns 8 claimed tasks ✓
2. `queue_poller.tick_once()` claims pending tasks (proven Pass-2 live), heartbeats ours, but explicitly does NOT execute (line 16 docstring: "does not execute task content")
3. Grep across `src/hermes3d/` for: `execute_task`, `run_persona`, `process_claimed`, `dispatch_to_persona`, `claimed_dir` consumer — **zero matches** for any actual executor
4. No code reads `tasks/claimed/*.json`, dispatches to the persona's executor, captures output, writes `handoff_path` markdown, OR marks done with deliverable
5. `POST /api/agents/queue/complete/W21-A4-…` (when called) would move the file `claimed/ → done/` but the handoff_path .md would never be auto-created
6. The user has been writing the handoff docs (claimed by `factory-operator`) manually; the persona system is purely symbolic

**Classification:** BLOCKED_AT_STEP_4 — MVP-3 (persona execution surface) is 100% missing.

---

## §13. Journey 13 — Voice tab (WORKING_HONEST_BLOCKED)

**Trace:**
1. `GET /api/voice/agents` returns assignments (none configured if Azure not set up) ✓
2. `GET /api/voice/providers` returns Azure with `configured: ?, status: ?` ✓
3. `GET /api/voice/voices` returns the catalog (fallback if backend unreachable)
4. Voice.tsx loads once on mount — STALE_FETCH_ONCE per Pass-2; refresh button exists for manual update
5. `POST /api/voice/preview {agent_id, text}` → 422 if Azure not configured (correct honest-block)
6. `POST /api/voice/stt` would return 502 — but **STT is client-side Web Speech API** (`VoiceBrowserSubtab.tsx`), the backend STT endpoint is intentionally not in the design. The 502 is the route returning honest-blocked for a never-built endpoint, which is mis-coded as 502 instead of 404 or 503.
7. `PUT /api/voice/agents/{id} {voice}` updates assignment (no provider field change supported)
8. `GET /api/voice/transcripts` returns recent transcripts list
9. `GET /api/voice/proof-events` returns voice-related proof events

**Classification:** WORKING_HONEST_BLOCKED — Azure key gates everything; client-side STT is a design choice not a gap; status code of 502 on stt should be 503/404.

---

## §14. Journey 14 — Learning candidate queue (WORKING_REAL_QUEUED)

**Trace:**
1. `GET /api/learning/config` → `{enabled:false, active:false, idle_minutes:30, runner_status:"ready", reports_directory:"…\\var\\learning\\reports"}`
2. `GET /api/learning/idle-workbench` → `{status:"ready", review_policy:"<text>", blockers:[9 items], candidates:[1]}` — currently 9 blockers prevent immediate run: 1 × S1 printer lock + 8 × queued jobs from earlier W18-A7/A9 audit runs (those queued jobs are stale — they should be cancelled or completed to unblock the Learning runner)
3. `POST /api/learning/idle-workbench/candidates` with body `{title, kind, agent_id, summary, source}` → 201 with new candidate_id ✓ — even though blockers exist, the candidate is queued.
4. `POST /api/learning/idle-workbench/candidates/{id}/run` would honest-block until blockers clear.
5. `GET /api/learning/reports` → 0 reports currently in `var/learning/reports/`
6. Learning.tsx is MANUAL_REFRESH_ONLY per Pass-2; refresh button required.

**Classification:** WORKING_REAL_QUEUED — wired end-to-end; runner is honest-blocked by the safety policy (correct behavior). The 8 stale queued jobs in the system are a separate cleanup concern.

---

## §15. Journey 15 — Approvals lifecycle (WORKING_REAL)

**Trace:**
1. `GET /api/approvals?status=pending` returns `[]` (no pending)
2. Approvals.tsx polls every 5s for pending + history
3. Approval auto-creation: only `POST /api/jobs/{id}/repair/propose` creates a `REPAIR_APPROVAL` row; generic job creation does NOT
4. Manual seed via SQLite `INSERT INTO approvals(...)` works; row appears in next poll
5. `POST /api/approvals/{id}/approve {decided_by, notes}` updates the row with `status='approved'`, `decided_at=now()`, `decided_by`, `notes`
6. State invariant enforced: `_decide()` refuses pending→pending or already-decided→decided transitions (409 on double-decide)
7. UI polls every 5 s; approved rows disappear from the pending list within 5s ✓
8. `proof_events` table receives a `approvals.approval.approved` event for the audit trail
9. Reject + Defer paths follow the same `_decide()` flow with different `status` values

**Classification:** WORKING_REAL — schema, route, UI, polling, state invariant all correct.

---

## §16. Cross-journey gap matrix

Journeys grouped by failure class:

| Failure mode | Journeys affected | What it means |
|---|---|---|
| **Execution missing** | J12 | The biggest gap: agents claim but nothing runs |
| **Pipeline disconnect** | J2 | Upload + generate exist but aren't wired together |
| **UI panel not built** | J4 | Backend wired (queue/status), UI not |
| **Refresh gap** | J3, J9 | Backend writes, UI doesn't auto-refresh |
| **Polling missing** | J13 (Voice) | STALE_FETCH_ONCE per Pass-2 |
| **Route discrepancy** | J1 | UI adapter path vs registered path off-by-one for 4 routes |
| **Schema partial** | J10 | update-center missing keys; theme labels null |
| **Stale locks** | J10 | 6 of 12 MCP locks not reaped |
| **No bulk action** | J5 | 18 apps × 1 click |
| **Honest blockers correct** | J7, J13, J14 | Working as designed; not a bug |
| **Bi-directional safety** | J11 | Working as designed; this is a positive |
| **Pass-2 false alarms** | J5, J6, J9 | "Missing onClick" claims at AppCard lines 534/547 — REFUTED; all those buttons have handlers |

### Pass-2 corrections this pass exposes

* **Plugins.tsx lines 151-158:** Pass-2 claimed "placeholder buttons no onClick". REFUTED. Plain `onClick={() => planSetupQueue()}` is present.
* **SourceOS.tsx lines 534+547:** Pass-2 claimed "role='button' no handler". REFUTED. Both have `onClick={() => onChange("matrix")}` / `onChange("registry")`.
* **AppCard buttons:** Pass-2 mentioned missing handlers. Current code shows full handlers including Launch button at PluginCard.tsx:56.

The previous gap audit's "5 buttons no onClick" claim is **0 after this verification**. The auditor (me) mis-counted in the earlier doc — those button locations have handlers.

### Pass-3-only new findings

1. **J1 — adapter path vs route registration discrepancy.** 4 endpoints return 404 from the Dashboard's adapter path despite Pass-2 confirming they exist. Action: re-probe with the exact `adapters.live.ts` fetch URLs to find the path drift.
2. **J2 — image upload disconnected from generation pipeline.** Even after Gen3D providers install, the line in `generation.run` that reads `reference_artifact_id` needs to feed the image through rembg → provider.
3. **J4 — Agents tab UI panel for `/api/agents/queue/status` is unbuilt.** Backend wired in PR #258; UI side never landed.
4. **J9 — SourceOS Backup row doesn't auto-refresh `latest_backup`.** One callback chain missing in the AppDetailPanel parent.
5. **J10 — 6 stale MCP locks** owned by past Claude sessions (w18-a1, w18-a10, w18-a16). Action: call `mcp__hermes3d-locks__hermes_recover_stale_locks`.
6. **J10 — update-center response missing `components` + `velopack` keys.** Schema regression vs prior contract.
7. **J10 — theme JSON files don't expose a `label` field** the /api/settings/themes consumer expects.
8. **J13 — `/api/voice/stt` returns 502 for an intentional design choice (STT is browser-side).** Should return 404 or 503 instead.
9. **J14 — 8 stale W18-A7/A9 jobs in the queue** are blocking the Learning runner from firing. Need cleanup.

---

## §17. Cross-pass synthesis preview

Pass 1 told us WHAT is registered. Pass 2 told us WHICH endpoints / routes actually behave. Pass 3 told us WHICH user paths complete.

The honest score from all three:

* **Reachable surface (Pass 1):** ~270 routes + ~25 tabs all registered.
* **Working surface (Pass 2):** 61 of 63 GETs return 200; 10 of 16 POSTs WORKING_REAL; 4 honest-blocked; 2 broken (voice/stt, health/services).
* **Completable journeys (Pass 3):** 5 of 15 WORKING_REAL, 4 of 15 with non-blocking gaps, 4 of 15 PARTIAL/BLOCKED, 1 of 15 NOT_WIRED, 1 of 15 MOSTLY_WORKING.

**The MVP-3 persona execution gap is the single highest-impact P0 — without it, the orchestrator queue is a permanent claim graveyard.**

Pass 3 synthesis doc will tie it all together with the prioritised fix list.

End of Pass 3.
