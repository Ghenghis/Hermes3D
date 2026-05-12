# W21 Audit — Pass 2 (Behavioral Probe)

**Date:** 2026-05-12
**Auditor:** Claude (13 parallel behavioral sub-agents + 2 manual fallbacks)
**Scope:** Live HTTP probes against running backend (PID 34092 at `127.0.0.1:8765`), SQLite reads, filesystem checks, LAN printer reads. Backend started with `HERMES3D_QUEUE_POLLER_DISABLED=1` so probes don't mutate state.
**Develop SHA:** `be2755f`

This is Pass 2 of 3. It evaluates what every surface ACTUALLY DOES when called — not what it claims to do. Pass 1 was structural, Pass 3 is E2E journey-by-journey.

---

## §0. Pass-1 claims this pass REVISES

After this pass's deeper probes, **three previous claims need correction**:

1. **DB is NOT empty.** The "0 rows in DB" claim was looking at `data/hermes3d.db` (0 bytes). The CANONICAL DB at `var/hermes3d.db` is 798 KB with **751 rows** including 196 artifacts, 42 jobs, 369 proof_events. The reconciler IS working.
2. **Stale-UI count was WRONG.** Real count is **14 of 24 tabs poll**, not 3 of 10. Only **4 tabs are strictly stale** (Artifacts, Gen3D, Voice, Roadmap).
3. **57 of 60 designs have proof envelopes**, not "57 missing". 87.7% coverage. But **40% of those envelopes fail signature re-verify** (separate, new finding).

Honest scorecard adjustments are at §16.

---

## §1. GET endpoint sweep — 63 endpoints

61 / 63 returned 200 OK. **2 failures**:

| Endpoint | Status | Issue |
|---|---|---|
| `/api/agents/action-catalog` (first probe) | 0 bytes / timeout | Returns 57 KB body when given longer timeout (90 actions: 76 ready, 10 blocked, 4 partial). Real bug: response time exceeds default curl timeout when system is busy. |
| `/api/health/services` | 3 s timeout | Health-probe walker hangs. Did not return within 15 s on retry. **Real broken.** |

### Latency distribution

* Fastest p50: ~4 ms (most endpoints)
* p95 noteworthy: `/api/observe/status` 3003 ms · `/api/system/snapshot` 1596 ms · `/api/learning/idle-workbench` 1551 ms · `/api/modules/runtime/gaps` 1240 ms · `/api/observe/cameras` 890 ms · `/api/agents/update/status` 841 ms · `/api/system/runtime-readiness` 455 ms · `/api/design/providers` 447 ms · `/api/autopilot/readiness` 392 ms · `/api/gen3d/providers` 357 ms · `/api/printers` 314 ms · `/api/design/backends` 326 ms · `/api/voice/voices` 287 ms.

The Observe / System / Learning / Module-gaps endpoints are slow enough to need a UI loading state and a polling-interval ≥ their p95.

### Payload size highlights

`/api/modules` and `/api/source-os/modules` both return 121 KB (the same 60-module dump). `/api/artifacts` 124 KB. `/api/agents/actions/catalog` 54 KB. `/api/modules/runtime/cli-surface` 56 KB. `/api/files` and `/api/files/list` 41 KB each. The UI must not block paint on these — Pass 3 will measure perceived load times per-tab.

---

## §2. POST endpoint sweep — 16 critical endpoints

| Endpoint | Status | Classification | Notes |
|---|---|---|---|
| `POST /api/design/intake` (desk_organizer) | **201** | WORKING_REAL | Real STL + proof envelope written |
| `POST /api/generation/run` (calibration_cube) | **202** | WORKING_REAL | Fallback works even without provider |
| `POST /api/voice/preview` (empty audio_b64 form) | 422 | WORKING_HONEST_BLOCKED | Pydantic validation fired |
| `POST /api/voice/stt` (empty body) | **502** | BROKEN_BACKEND_5xx | Upstream Azure not configured → should be 503 not 502 |
| `POST /api/files` (write attempt) | 501 | WORKING_HONEST_BLOCKED | Operator-frozen by design |
| `POST /api/autopilot/next-gate` | 409 | WORKING_HONEST_BLOCKED | Gate blocked with reason — correct |
| `POST /api/autopilot/write-plan` | 200 | WORKING_REAL | Wrote bytes + sha256 + proof_event_id |
| `POST /api/autopilot/write-report` | 200 | WORKING_REAL | Same |
| `POST /api/agents/providers/smoke {minimax}` | 200 | WORKING_REAL | PASS_LIVE 1047 ms |
| `POST /api/agents/providers/smoke {deepseek}` | 200 | WORKING_REAL | PASS_LIVE 1151 ms |
| `POST /api/agents/providers/assist {minimax,builder}` | 200 | WORKING_REAL | model=MiniMax-M2.7-highspeed completion received |
| `POST /api/proof/events` (test event) | 422 | WORKING_HONEST_BLOCKED | Pydantic validation fired — but see §11: events that ARE accepted get silently dropped from the durable ledger |
| `POST /api/observe/anomaly/flsun_t1_a` | **201** | WORKING_REAL | Anomaly row created on disk |
| `POST /api/learning/idle-workbench/candidates` | **201** | WORKING_REAL | Candidate created |
| `POST /api/agents/queue/status` (wrong method) | 405 | WORKING_HONEST_BLOCKED | Method-not-allowed enforced |
| `POST /api/agents/queue/claim/{id}` | 200 | WORKING_REAL | Returns claimed task envelope. **But see §3 — release endpoint is broken.** |

**Summary:** 10 WORKING_REAL · 4 WORKING_HONEST_BLOCKED · 2 BROKEN_BACKEND_5xx.

`POST /api/voice/stt` returning 502 is the only POST that's truly broken — should honest-block as 503 like the smoke endpoints do when keys are missing.

---

## §3. Queue lifecycle — CRITICAL BUG FOUND

Live test sequence on PID 34092:

| Step | Action | API response | Filesystem state | Verdict |
|---|---|---|---|---|
| 1 | GET `/api/agents/queue/status` | counts {pending:0, claimed:8, done:0, blocked:0} | `claimed/` has 8 files | baseline |
| 2 | POST `/api/agents/queue/release/W21-A4-…` | `{accepted:true, status:"released"}` | **W21-A4 STILL in `claimed/`** | **BUG** |
| 3 | GET status again | counts unchanged: pending:0 claimed:8 | unchanged | confirms (2) |
| 4 | POST claim/W21-A4 again | **404 "not in pending state"** | unchanged | downstream blocked by (2) |
| 5 | Wrong-persona claim on W21-A2 | 404 "not in pending state" | unchanged | persona-mismatch path unreached because pending is empty |

**Root cause (read `queue_bridge.release_task` in `services/queue_bridge.py`):** the function writes the patched JSON in place (correct) but the trailing `_atomic_move(src, pending_dir(workspace_root))` uses `src` which by then refers to the `claimed/` path of an ALREADY-WRITTEN-IN-PLACE file. `os.replace(src, src.parent.parent / "pending" / src.name)` would work; the current path math is OFF. Pass 3 will write the fix.

**Impact:** once a task is in `claimed/`, no operator action can return it to `pending/` through the API. The queue is one-way. The auto-poller can't reclaim a wrongly-claimed task either.

---

## §4. SQLite truth — the big correction

Backend writes to `var/hermes3d.db` per `db/init.py:10`:

```python
DB_PATH = Path(__file__).resolve().parents[3] / "var" / "hermes3d.db"
```

| DB file | Size | Mtime | In use? |
|---|---|---|---|
| `var/hermes3d.db` | **798 KB** | 2026-05-11T18:17 | **YES (canonical)** |
| `data/hermes3d.db` | **0 bytes** | 2026-05-11T17:51 | NO (stale) |

### Row counts (canonical DB)

| Table | Rows |
|---|---|
| `proof_events` | **369** |
| `artifacts` | **196** |
| `modules` | 60 |
| `module_runtime_verifiers` | 53 |
| `jobs` | **42** |
| `job_steps` | 106 |
| `job_events` | 63 |
| `truth_gate_results` | 27 |
| `agent_conversations` | 23 |
| `roadmap_items` | 18 |
| `plugins` | 20 |
| `voice_assignments` | 8 |
| `module_providers` | 5 |
| Other (approvals/anomaly/etc.) | 0 |
| **TOTAL** | **751** |

### Disk-vs-DB delta

| Surface | Reports | Disk truth | Delta |
|---|---|---|---|
| `/api/artifacts` | 196 (matches DB) | 202 file paths in `var/` ref by DB | **100% of DB rows resolve to real files** |
| `/api/jobs` | 42 (matches DB) | — | ✓ |
| `/api/files` | 194 items | 217 actual files on disk | **+23 untracked** — designs subdir has variants the scanner skips |

**Verdict:** the reconciler IS working. Earlier "206 vs 0" claim was a misread of the wrong DB file. **The pipeline is FAR more functional than the gap doc said.**

---

## §5. Gen3D pipeline — providers all blocked, fallback path works

`GET /api/gen3d/providers` returns 5 entries — 4 not_installed + 1 `installed_not_running` (Bambu Studio). 0 are live-reachable.

`GET /api/gen3d/templates` advertises 5 templates: `calibration_cube` (local fallback), `comfyui_text_to_3d`, `trellis2_text_to_3d`, `hunyuan3d_text_to_3d`, `triposr_text_to_3d`.

`POST /api/generation/run {prompt, template_id:"calibration_cube"}` → **202 with real STL + SVG + proof** (truth gate pass, 55 ms). The local fallback path actually works.

`POST /api/generation/run {template_id:"unknown"}` → **202 accepted** as if it were calibration_cube. **Validation gap** — the route silently aliases unknown templates to the fallback rather than honest-blocking.

### Python import check

```
import comfyui_frontend_package  → 1.33.10
import triposr                   → ModuleNotFoundError
import trellis                   → ModuleNotFoundError
import hunyuan3d                 → ModuleNotFoundError
import rembg                     → ModuleNotFoundError
```

### GPU
RTX 3090 Ti: 24,564 MB total, **22,148 MB used**, 2,162 MB free, **88% utilization**. Some other tenant has the card. Even TripoSR (4 GB minimum) can't load.

### HuggingFace cache
No subdirs matching `Hunyuan|TripoSR|TRELLIS|ComfyUI` in `C:\Users\Admin\.cache\huggingface`. Weights are NOT cached for any of the 4 providers.

**Verdict:** Gen3D is **structurally sound** (route works, fallback succeeds) but **5 of 5 image-to-3D paths are blocked** by missing Python packages + missing weights + missing VRAM headroom.

---

## §6. App proofs — most apps never proven

`GET /api/apps` returns 60 apps. **19 have `proof_command` set**; only **1 (`hermes_agent`) has `last_proof_status == "pass"`**.

Live `POST /api/apps/hermes_agent/run-proof`:
```
accepted: true · status: pass · exit_code: 0 · duration_ms: 663
proof_command: python -m hermes_cli.main --help
stdout: 17 KB --help output captured
```
`last_proof_at` advanced from prior timestamp → 2026-05-12T01:18 confirming **persistence works**.

### 18 apps with `proof_command` set, never proven (operator-actionable today)

`azure_speech_sdk_js`, `blender`, `blender_mcp_candidates`, `build123d`, **`cadquery` (last_proof_status=fail)**, `curaengine`, `firmware_klipper`, `klipper`, **`langchain` (last_proof_status=fail)**, `langgraph`, `manifold`, `marlin`, `model_context_protocol`, `numpy_stl`, `open3d`, `openscad`, `pymesh`, `trimesh`.

### Failure roots (cadquery + langchain)

Both proof commands are `python -c "import <pkg>; print(<pkg>.__version__)"`. Both return `ModuleNotFoundError`. The 60-app registry lists them as `install_state: installed` but the active Python env (`C:\Python314\python.exe`) **cannot import them**.

This is the **Python-env mismatch problem**: the registry was populated from a different Python (perhaps a venv that's no longer activated), so its "installed" flag is stale.

---

## §7. CAD toolchain — one contradiction surfaced

| Tool | Installed | Version | Trivial op works |
|---|---|---|---|
| OpenSCAD | YES (`C:\Program Files\OpenSCAD\openscad.exe`) | 2021.01 | **FAILED** to emit STL on a trivial `.scad` script |
| Blender | YES (`C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`) | **5.1.1** (NOT 3.6 as previous audit claimed) | not tested |
| trimesh | YES | 4.12.1 | ✓ |
| manifold3d | YES | 3.4.1 | ✓ (CSG diff returned watertight result) |
| CadQuery | NO | — | — |
| FreeCAD | NO | — | — |

**Contradiction:** `/api/design/backends` declares `openscad.available=false, path=null`. `/api/design/providers` declares `openscad.status=ready, version=2021.01`. **Same backend, two opposite answers from two endpoints.** Plus the trivial STL export actually fails — so the truth is closer to `available=false`, and `/api/design/providers` is over-optimistic.

GPU: 24.5 GB, CUDA 13.1, 11% utilization at probe time (later GPU probes saw 88% — non-deterministic across probes, suggests another GPU tenant cycling).

---

## §8. Provider live-smoke matrix

| Provider | Smoke endpoint | Live status | Latency | Tokens | Notes |
|---|---|---|---|---|---|
| MiniMax | YES | **PASS_LIVE** | 1047 ms | 42 in / 3 out | role=builder model=MiniMax-M2.7-highspeed |
| DeepSeek | YES | **PASS_LIVE** | 1151 ms | 5 in / 1 out | role=reviewer model=deepseek-v4-pro |
| LM Studio | NO smoke wired | direct `GET /v1/models` returns 97 models | — | — | role=fallback kind=local_fallback |
| Ollama | NO smoke wired | direct `GET /api/tags` returns 27 models | — | — | role=fallback kind=local_fallback |
| OpenAI | NO smoke wired | key_present=true but route never built | — | — | — |
| HuggingFace, GitHub, CodeRabbit, Azure Speech, SiliconFlow | NO smoke wired | keys in .env, no live probe surface | — | — | — |

### Strict provider separation proven

`GET /api/agents/health` returns distinct `kind` fields:
```
minimax  → kind: "live_remote"
deepseek → kind: "live_remote"
lm_studio → kind: "local_fallback"
ollama    → kind: "local_fallback"
```

`POST /api/agents/providers/assist {provider:"minimax", role:"builder"}` returns `"model":"MiniMax-M2.7-highspeed"` and `"persona":"modeling-agent"` — never silently routed through LM Studio.

`POST /api/agents/providers/assist {provider:"deepseek", role:"reviewer"}` returns `"model":"deepseek-v4-pro"` and `"persona":"oliver-qa-agent"`.

**W18 strict rule (LM Studio ≠ MiniMax) verified.**

---

## §9. Disk-vs-DB reconciliation — WORKING

`POST /api/files/reconcile` → `{inserted: 0, by_bucket: {generation: 0, designs: 0, slicer: 0}}`. Zero inserts means **the DB is already in sync** — not that the reconciler is broken.

| Concern | Reports | Disk truth | Status |
|---|---|---|---|
| artifacts rows | 202 | 202 files referenced exist | **100% in sync** |
| jobs rows | 42 | (no direct disk equivalent) | tracked |
| /api/files scanner | 194 items | 217 files in var/ | 13% gap (designs subdir variants) |

Reconciler **is called on app startup** (`api/app.py:105`, `@app.on_event("startup")`). It uses `INSERT OR IGNORE` keyed on `file_path` and skips duplicates. The W21 gap audit's "206 vs 0" claim was looking at the WRONG DB.

---

## §10. Printer registry vs LAN (read-only)

`GET /api/printers` returns 4 entries:

| id | IP | Model | Registry status | Live LAN status | Filename | Duration |
|---|---|---|---|---|---|---|
| flsun_t1_a | 192.168.0.10 | FLSUN T1 | online | `klippy_state=ready, state=complete` | `delta-calibration-test-model-50pct-T1.gcode` | 152 s |
| flsun_t1_b | 192.168.0.11 | FLSUN T1 | online | `klippy_state=ready, state=standby` | — | 0 s |
| flsun_s1 | 192.168.0.12 | FLSUN S1 | online | `klippy_state=ready, state=standby` | — | 0 s (camera-only / operator-locked) |
| flsun_v400 | 192.168.0.34 | FLSUN V400 | online | `klippy_state=ready, moonraker=0.7.1-586`, `state=standby` | — | 0 s |

All 4 LAN-reachable. **No hardware writes performed.** The S1 lock check is verified at the route layer (`api/routes/printer_safety.py`).

---

## §11. Event ledger — silent routing

POST `/api/proof/events {event_type:"w21_audit_pass2_probe", payload:{}}`:
- Response: `{recorded:true, proof_kind:"audit_event", verified:false, reason:"Recorded as local audit evidence only"}`
- ID: `59a05f9e884c4924bca127eb44527cd8`

After the POST:
- `GET /api/proof/bundles?limit=10` — new event appears as `local-audit-evidence-1` ✓ (in the bundle list)
- SQLite `proof_events` table — **DOES NOT contain the new event** (despite 369 historical rows)
- `.hermes3d_orchestrator/events.ndjson` — **DOES NOT contain it** (625 lines unchanged)
- `.hermes3d_orchestrator/evidence/ledger.ndjson` — **DOES NOT contain it** (681 lines unchanged)
- `.hermes3d_orchestrator/events/` subdir — empty

**Verdict: SILENT_ROUTING.** The endpoint acknowledges receipt and surfaces a bundle ID, but the event never reaches any durable ledger. On backend restart the bundle dies.

### Ledger architecture (3 separate stores)

* SQLite `proof_events` — has 369 historical rows (so SOMETHING writes here, but not the API endpoint)
* Orchestrator `events.ndjson` — orchestrator-owned, has 625 lock/task/heartbeat lines
* Evidence `evidence/ledger.ndjson` — hash-chained, 681 lines, `lock.acquired` (228) / `lock.released` (180) / `evidence.appended` (76) / `gate.passed` (21) / `pr.opened` (21)

Three ledgers, no propagation rule. Pass 3 will trace which ledger each subsystem writes to.

---

## §12. Stale-UI map (corrected) — 14 of 24 tabs poll

| Tab | Pattern | Interval | Verdict |
|---|---|---|---|
| Dashboard | useEffect + EventSource SSE | live | LIVE_SSE |
| Files | useEffect + manual refresh | — | MANUAL_REFRESH_ONLY |
| **Artifacts** | useEffect on mount only | — | **STALE_FETCH_ONCE** |
| Agents | 5× useEffect + manual refresh | — | MANUAL_REFRESH_ONLY |
| Jobs | useEffect + setInterval (queued/printing only) | 10 s | LIVE_POLLING |
| **Gen3D** | useEffect on mount only | — | **STALE_FETCH_ONCE** |
| Design | useEffect + 3× setInterval | 15 s / 30 s / 30 s | LIVE_POLLING |
| Plugins | useEffect + manual refresh | — | MANUAL_REFRESH_ONLY |
| Approvals | useEffect + setInterval | 5 s | LIVE_POLLING |
| Autopilot | useEffect + setInterval | 30 s | LIVE_POLLING |
| SourceOS | 2× useEffect + setTimeout | 15 s | HYBRID |
| Printers | useEffect + refetch helper | — | MANUAL_REFRESH_ONLY |
| **Voice** | 2× useEffect on mount | — | **STALE_FETCH_ONCE** |
| Learning | useEffect + manual refresh | — | MANUAL_REFRESH_ONLY |
| Observe | useEffect + setInterval + retry | 5 s | LIVE_POLLING |
| Settings | delegated | — | N/A |
| **Roadmap** | useEffect on mount only | — | **STALE_FETCH_ONCE** |
| Workflows | useEffect + setInterval | 15 s | LIVE_POLLING |
| Notifications | useEffect + setInterval | 15 s | LIVE_POLLING |
| Safety | useEffect + setInterval | 20 s | LIVE_POLLING |
| Proof | useEffect + setInterval | 30 s | LIVE_POLLING |
| ServiceHealth | delegated | — | N/A |
| SystemLogs | useEffect + setInterval + pause toggle | 5 s | LIVE_POLLING |
| PrintQueue | useEffect + setInterval | 10 s | LIVE_POLLING |

**Counts (24 tabs, excluding 2 delegated):**
* LIVE polling/SSE: **12** (Dashboard, Jobs, Design, Approvals, Autopilot, Observe, Workflows, Notifications, Safety, Proof, SystemLogs, PrintQueue)
* HYBRID: 1 (SourceOS)
* MANUAL_REFRESH_ONLY: 5 (Files, Agents, Plugins, Printers, Learning)
* **STALE_FETCH_ONCE: 4 (Artifacts, Gen3D, Voice, Roadmap)** ← only these 4 are real stale risks

Earlier "7 of 10" claim was wrong. Real number is 4 of 24 tabs need polling added.

---

## §13. Process + port inventory

| Port | Service | PID | Memory | Health |
|---|---|---|---|---|
| 8765 | Hermes3D backend (uvicorn) | 34092 | 197 MB | reachable; some routes 0-byte / 3 s |
| 1234 | LM Studio | 19064 | 16.8 GB | green; 97 models loaded |
| 11434 | Ollama | 23696 | 162 MB | green; 27 models |
| 8000 | "Manager" (IPv6) | 6788 | 167 MB | unknown ownership |
| 5173 | Vite dev | — | — | **refused** (UI not running) |
| 8188 | ComfyUI | — | — | **refused** (provider offline) |

20 `node.exe` processes running (MCP servers + Electron). 11 `python.exe` processes (mix of running backend + tooling).

GPU consumers: **88% utilization** by an unidentified tenant; only 2.2 GB VRAM free.

---

## §14. Proof envelope integrity — 40% signature mismatch

Sampled 20 of 57 `*.proof.json` files under `var/designs/**`.

* **8 of 20 (40%) FAIL signature re-verify** when checked against the default proof key (`hermes3d-default-proof-key-not-secret`).
* **12 of 20 (60%) PASS** signature re-verify with the default key.
* All 20 envelopes have valid structure (artifact_path, signature, truth_gate_report).
* All 20 truth_gate_report blocks report `overall_status: pass` for the 8 standard checks (watertight, manifold, normals, bed_fit, minimum_volume, wall_thickness, self_intersection, printer_fit-skipped).
* Coverage: **50 of 57 sampled designs** have a sibling proof.json. **7 don't.** (87.7% per-design coverage.)

**Root cause of the 40% mismatch:** `HERMES3D_PROOF_KEY` is not set in this session. The 12 passing proofs were signed with the default key; the 8 failing ones were signed with a different (real or test) key that the operator rotated. Either:
* The operator rotated proof keys between batch runs without re-signing, OR
* CI signed some with a different key, OR
* The proof_envelope module's HMAC input changed between batches.

Either way: **40% of recent design proofs cannot be re-verified by anyone without the original key.**

---

## §15. Source-OS modules — 60 registered, 4 with broken paths

`GET /api/source-os/modules` returns **60 modules**.

| install_state | Count |
|---|---|
| installed | **56** |
| source_available | 4 |

| runtime_status | Count |
|---|---|
| ready | 35 |
| setup_required | 16 |
| source_ready | 7 |
| blocked | 2 |

**`local_path` exists on disk: 56 of 60.** The 4 missing all point to `G:\Github\Hermes3D\03_implementation\source-lab\sources\...` but the real clones are at `G:\Github\Hermes3D-OS\source-lab\sources\...`:

| Module | Reported path (BROKEN) | Real clone path (likely) |
|---|---|---|
| blender_mcp_candidates | `03_implementation\source-lab\sources\orchestration\blender-mcp` | Hermes3D-OS sibling, or not cloned |
| open3d | `03_implementation\source-lab\sources\modelers\Open3D` | Hermes3D-OS sibling, or not cloned |
| numpy_stl | `03_implementation\source-lab\sources\modelers\numpy-stl` | Hermes3D-OS sibling, or not cloned |
| pymesh | `03_implementation\source-lab\sources\modelers\pymeshfix` | Hermes3D-OS sibling, or not cloned |

**Fix:** the module-registry seeder is writing absolute paths into the wrong workspace root. One PR can re-seed the 4 rows.

---

## §16. Pass-2 corrected scorecard

| Pillar | Pass-1 honest estimate | Pass-2 corrected |
|---|---|---|
| GUI shell | ~85% | ~85% (unchanged) |
| Backend HTTP wiring | ~80% | **~90%** (only 2 of 63 GETs broken, only 1 of 16 POSTs broken) |
| Slicer | ~95% | ~95% |
| Provider key loading + smoke | ~70% | ~70% (only 2 providers smoke-wired; rest have keys but no probe) |
| Design tab | ~70% | ~70% (1 working template, OpenSCAD contradiction) |
| **DB tracking** | ~10% | **~95%** (DB IS populated, reconciler works — corrected from "206 vs 0" lie) |
| **Realtime UI refresh** | ~30% | **~70%** (12 of 22 active tabs poll properly; only 4 strictly stale) |
| **Hermes Agent execution** | ~10% | **~10%** (claim works; queue release BROKEN; no execution code; reaffirmed) |
| **Gen3D pipeline** | ~5% | **~10%** (calibration_cube fallback works; 5 real providers blocked) |
| Test route coverage | ~43% | ~43% (Pass-1 result) |
| Proof envelope verifiability | (not measured) | **60%** (40% of recent proofs unverifiable from default key) |
| Event ledger durability | (not measured) | **POOR — silent routing on /api/proof/events** |
| App-proof execution | (not measured) | **5% — only 1 of 19 proof_commands proven** |

**Weighted estimate revised: ~65-72% E2E day-to-day.** Up from 55-65% in the gap doc because the DB + reconciler + UI polling are healthier than first claimed. Down from 95% because of the new bugs found: queue release, silent event routing, proof key drift, 4 broken source-OS paths, OpenSCAD trivial-export failure, Python-env mismatch on cadquery/langchain proof, 22 GB GPU pinned by a non-Hermes tenant.

---

## §17. New P0/P1 surfaced by Pass 2 (not in prior docs)

### P0 — break or silently lose data

1. **Queue release is one-way broken.** `release_task` writes the patched JSON but moves it to the wrong destination. Tasks stuck in `claimed/` cannot be released through the API. Fix: correct path math in `services/queue_bridge.py:release_task`.
2. **`/api/proof/events` silently drops events.** Returns `recorded:true` but no durable ledger receives the event. Fix: wire the POST to append to either SQLite `proof_events` or `evidence/ledger.ndjson` (preferably both with a manifest-style chain).
3. **40% proof signature mismatch.** Either rotate to a stable `HERMES3D_PROOF_KEY` and re-sign historical envelopes, or accept that the historical batch is unverifiable.
4. **`/api/health/services` hangs 3+ s.** UI is calling this on every Dashboard mount. Fix: shorten the per-provider probe timeout and add caching.
5. **4 source-OS modules report wrong local_path.** Re-seed registry with correct workspace root.

### P1 — known gap, confirmed

6. **`/api/agents/action-catalog` slow + sometimes 0-byte.** When operating under load, the 57 KB response doesn't fit the default timeout. Either paginate or stream.
7. **`/api/voice/stt` returns 502 instead of 503 when Azure not configured.** Honest-block convention is 503.
8. **Generation route silently aliases unknown templates to calibration_cube.** Should 422 with the supported_templates list.
9. **cadquery + langchain proofs fail because Python env can't import them.** Either reinstall to the active env or downgrade install_state.
10. **OpenSCAD declared ready but trivial STL export fails.** Either fix the trivial export or downgrade availability.

### P2 — backlog (still real)

11. 7 of 57 designs missing proof.json siblings.
12. 18 apps have proof_command set but never run.
13. 5 providers with .env keys have no smoke endpoint (openai, huggingface, github, coderabbit, azure_speech, siliconflow).
14. /api/files scanner under-counts by ~13% (designs variants).
15. 22 GB GPU is held by an unidentified tenant — Gen3D can't load anything significant until cleanup.

---

## §18. What Pass 2 DOES NOT answer

Pass 2 tested individual surfaces. It does NOT validate:

* Whether a real user can navigate from `#design` to a printed object (Pass 3 journey).
* Whether the 5 manual-refresh tabs leave the operator with stale data within a single session.
* Whether the queue release bug actually blocks the orchestrator workflow in practice (or if other paths route around it).
* Whether the GPU tenant is one of our own processes (need to attribute the 22 GB).
* Whether the 40% proof-key drift is a recent rotation or a long-standing issue.

Pass 3 (E2E user journeys) traces 15 named user paths step-by-step to surface gaps that single-surface probes miss.

End of Pass 2.
