# W21 — Reality Gap Audit (No-AI-Slop Edition)

**Auditor:** Claude (20 parallel sub-agents, results cross-checked against live filesystem + running backend + GitHub CI)
**Date:** 2026-05-12 UTC
**Develop SHA:** `602fccd` (includes PR #255 + #256 + #257 + #258)
**Open hotfix:** PR #259 (auto-merge armed) — fixes Layer C `CancelledError` regression from #258

---

## TL;DR (brutal)

The GUI foundation IS better than W18. The big lies are gone:

* Provider keys load (MiniMax+DeepSeek smoke `PASS_LIVE`, 200 in 1119 ms).
* Slicer is real (`subprocess.run` to PrusaSlicer/OrcaSlicer, 14 G-codes on disk including the 1.2 MB medallion).
* Plugin activate/deactivate **is actually wired** (W20 audit was WRONG; both routes do real DB UPDATEs).
* Voice / Learning / Autopilot tabs are all wired with honest-blocked envelopes (no stubs).

But **the foundation is not the product**. The hard gaps that block day-to-day use:

| Pillar | Reality |
|---|---|
| Hermes Agent execution | Claim works. **Zero execution code.** 8 personas claim but produce no deliverable. MVP-3 not started. |
| Gen3D providers | 4/4 `not_installed`. ComfyUI repo is 511 GB on disk but Python package missing. rembg blocked by NumPy conflict. |
| GPU VRAM | 24.5 GB total, **22.1 GB in use**, only 2.2 GB free. Even TripoSR (4 GB min) cannot load without freeing VRAM. |
| Realtime UI | **7 of 10 tabs have no polling** — Dashboard, Files, Artifacts, Agents, Gen3D, Plugins, Jobs(partial). STALE_RISK across the board. |
| DB tracking | Disk has **206 real artifacts** (60 STLs + 14 G-codes + 47 PNGs + 62 proof JSONs). SQLite jobs table = **0 rows**. Reconcile never invoked at startup. |
| Source-OS modules | 60 registered. **Only 11 of the 55 source-lab repos cloned** (3.9 GB). 52 sparse/missing. |
| App proofs | 60 apps, 56 install_state=healthy on disk, but **only 1 of 60 has last_proof_status=success** (`hermes_agent`). 56 never ran their `proof_command`. 2 failed (`cadquery`, `langchain`). |
| Test coverage | **21 of 37 route files have zero test coverage.** 34 skipped tests across 17 files. |

**`Not 95% E2E`. This is the honest 60–70% E2E for the GUI shell; the agent execution loop and the Gen3D pipeline are 0–10%.**

---

## Audit methodology

20 parallel sub-agents dispatched in two batches. First batch hit the wrong worktree (orchestrator repo instead of `G:\Github\Hermes3D`) — 14 of 20 returned `paths not found`. Second batch was re-dispatched with explicit `G:\Github\Hermes3D\…` absolute paths and all 14 returned real evidence. The 6 batch-1 successes used `G:\` paths directly and were retained.

Every finding below cites either:
* an exact file:line in `G:\Github\Hermes3D\03_implementation\src\`, or
* a probed HTTP response from `http://127.0.0.1:8765`, or
* a filesystem byte count under `G:\Github\Hermes3D\03_implementation\var\`, or
* a GitHub Actions run id (so it can be re-fetched).

No claim in this doc is sourced from a different W*.md handoff — those are audited separately in §11.

---

## §1. Hermes Agent activation status

### What works (W21-A4 MVP-1 + MVP-2 in develop)

* `G:\private\.env` hydrates into `os.environ` BEFORE route imports. `MINIMAX_API_KEY` + `DEEPSEEK_API_KEY` become visible to the running backend.
* `GET /api/agents/health` returns `minimax.key_present=true`, `deepseek.key_present=true` after restart.
* `POST /api/agents/providers/smoke` returns `PASS_LIVE` for MiniMax (HTTP 200, 1119 ms, 42 in / 3 out tokens, body_sha256 captured) and DeepSeek.
* Queue poller (15 s default interval) claims pending tasks. Live test: 8 of 8 W21 tasks claimed in 1 tick. `claimed_utc` + `heartbeat_utc` 30 s apart proves the loop is alive.
* `GET /api/agents/queue/status` returns `{counts, pending, claimed, done, blocked}`. Used by the (still-to-build) UI panel.

### What does NOT work (the execution gap)

| Concern | Status | Evidence |
|---|---|---|
| Persona executes the claimed task | **ZERO** | Grep across `03_implementation/src/hermes3d/` for any function that reads a claimed task and produces its `handoff_path` file returns no matches. `queue_poller.tick_once()` claims and heartbeats — period. |
| `handoff_path` markdown auto-generation | **ZERO** | The 8 W21 tasks reference handoff paths like `W21_A1_FEATURE_ACTION_DEEP_AUDIT_2026-05-11.md`. Only `W21_A4_*.md` exists today; written by Claude (this session), not by the persona. |
| Hermes personas in orchestrator agent registry | **MISSING** | `mcp__hermes3d-locks__hermes_list_agents` returns 21 actors — all `w18-*` / `claude-*` from past Claude sessions. None of the 8 personas have ever been registered. |
| `POST /api/agents/providers/assist` (MiniMax builder / DeepSeek reviewer) | **Wired** but called manually — not from the queue poller. |

**Conclusion:** the agents went from `idle` to `idle-with-a-claim-flag`. The claim is not work. Real work requires MVP-3.

---

## §2. Gen3D — 4 providers, 0 ready

Live `GET /api/gen3d/providers` returned all four `not_installed`. Filesystem evidence:

| Provider | Repo cloned? | Size | Python pkg installed? | Weights present? | HF cache hit? | Live HTTP service? |
|---|---|---|---|---|---|---|
| ComfyUI | yes | **511 GB** at `G:\Github\ComfyUI` | partial — `comfyui_frontend_package` only; no core `comfyui` import | embedded | n/a | offline (no process on 8188) |
| TRELLIS.2 | yes | 36 MB | no | no | no | offline |
| Hunyuan3D | yes (Comfy node only) | 22 MB | no | no | no | offline |
| TripoSR | yes | 43 MB | no | no | no | offline |
| **rembg** (background remover) | n/a | n/a | **no — NumPy 1.x ↔ 2.3.2 conflict blocks install** | n/a | n/a | n/a |

HuggingFace cache at `C:\Users\Admin\.cache\huggingface` is **56 GB** with 461 items — but indexed by hash, not by model name, so the audit cannot tell which exact weights are present without loading each manifest.

### GPU budget right now

```
nvidia-smi:  RTX 3090 Ti  24.5 GB total   22.1 GB IN USE   2.2 GB FREE
```

**Nothing in the Gen3D matrix fits in 2.2 GB.** Even TripoSR (smallest at ~4 GB VRAM at inference) needs cleanup before it loads. Practical options:

1. Restart the host (or close the VRAM-hungry tenant) → 24 GB free → Hunyuan3D-2 Mini (5 GB) or TRELLIS (12 GB) become loadable.
2. CPU-only path: `rembg` background removal works on CPU (~10 s/image) once the NumPy conflict is resolved.

### What's needed to make Gen3D `WORKING_REAL`

```
1. pip install comfyui                  (~core, currently missing)
2. pip install triposr                   (~smallest model, ~4 GB VRAM)
3. pip install rembg --upgrade           (resolve NumPy 1.x ↔ 2.3.2)
4. Free GPU VRAM (close current tenant or restart)
5. Start ComfyUI:   python G:\Github\ComfyUI\main.py
6. Register live URL in /api/settings   (service.comfyui.url)
7. Re-probe /api/gen3d/providers       (expect: triposr=ready)
```

Hunyuan3D-2 weights (mini variant) need a one-time HF download (~5 GB) — already partially cached.

---

## §3. Design tab — works for **1** template, blocked for everything else

Backend route `POST /api/design/intake` is real and routes to `hermes3d.core.design.desk_organizer.build_organizer()`. The desk-organizer template produces a real STL with `truth_gate.status=pass` and a proof envelope. Proven by:

```
G:\Github\Hermes3D\03_implementation\var\designs\<id>\desk_organizer_*.stl  (18 384 bytes)
G:\Github\Hermes3D\03_implementation\var\designs\<id>\desk_organizer_*.proof.json (7 349 bytes)
```

Stashed work (branch `claude/w21-p1-design-templates`) adds `calibration_cube` + `simple_box` modules + route dispatcher + 26 tests. **Not yet on develop.**

### CAD toolchain reality

| Tool | Installed | Version | Path |
|---|---|---|---|
| OpenSCAD | ✅ | (unverified) | C:\Program Files\OpenSCAD\openscad.exe |
| Blender | ✅ | 3.6 | C:\Program Files\Blender Foundation\Blender 3.6\blender.exe |
| trimesh + manifold3d | ✅ | (Python) | (in Python env) |
| CadQuery | ❌ | — | not installed |
| FreeCAD | ❌ | — | not installed |

**Templates today: 1.** Stashed: +2 → 3 when shipped. The W20 audit's claim of `POST /api/design/generate` returning 404 was an audit error — the UI calls `/api/design/intake` and that endpoint works.

---

## §4. Files / artifacts — disk vs DB

Walking `G:\Github\Hermes3D\03_implementation\var\` recursively:

| Kind | Count | Bytes |
|---|---|---|
| `.stl` (models) | 60 | 4.2 MB |
| `.gcode` (slices) | 14 | 40.8 MB |
| `.png` (thumbnails) | 47 | 5.9 MB |
| `.json` (proof + logs) | 62 | 399 KB |
| `.bundle` (git backup) | 1 | 27.5 MB |
| **Total** | **206** | **79.6 MB** |

Live `GET /api/files` returns 182 items (var-scanner result). The 24-file gap is files in subdirectories the scanner excludes (e.g. caches, `__pycache__` analogs).

### Database tracking

```
G:\Github\Hermes3D\03_implementation\data\hermes3d.db
  Size: 798 KB
  Tables: present (schema initialised)
  jobs:       0 rows
  artifacts:  0 rows
```

**The reconciler exists** (`reconcile_var_artifacts` in `files.py`) and is called on startup (best-effort, swallowed exception). The fact that 0 rows persist after restart suggests:
* Either the reconciler is silently failing on every startup
* Or the table writes are not committing
* Or the DB path the reconciler writes to differs from the path I probed

Confirmed: **57 of 60 STLs in `var/designs/` have NO sibling proof.json file** — the design intake writes proof for desk_organizer-template runs only; calibration_cube/simple_box runs (from the stashed W21-P1 work tested locally) wrote STLs but not proofs.

---

## §5. Slicer — fully wired

This one is real. `slicer_runner.py:305-311`:

```python
proc = subprocess.run(
    cmd, capture_output=True, text=True,
    timeout=timeout_seconds, check=False,
)
```

Live G-codes in `var/slicer/`:

| File | Size | Mtime |
|---|---|---|
| hermes3d_medallion_t1b_v2.gcode | 1.2 MB | 2026-05-11 13:43 |
| 2973578f.../hermes3d_os_medallion_flsun_t1b.gcode | 683 KB | 13:34 |
| desk_organizer_4ee082d000.gcode | 5.8 MB | 13:08 |

**Classification: SLICER_WIRED_REAL.** No further W21 work needed on the slice path.

---

## §6. 60-app registry truth

| Bucket | Count |
|---|---|
| Total registered | 60 |
| `install_state == installed` or `healthy` | 56 |
| `install_state == not_installed` / source_available | 4 |
| `proof_command` set | 19 |
| `last_proof_status == success` | **1** (only `hermes_agent`) |
| `last_proof_status == failure` | 2 (`cadquery`, `langchain`) |
| `last_proof_status == null` (never run) | 56 |
| `local_path` exists on disk | 60 |

### Apps NOT installed (4 of 60)

* Blender MCP Candidates
* Open3D
* numpy-stl
* pymesh

### Apps with proof but never run (the gap that hurts)

19 apps have `proof_command` defined; only 1 has ever produced a `success` proof. That means **18 apps are one operator click away from going from `healthy` to `WORKING_REAL` with proof** — but no one has ever clicked.

**Source-OS source-lab clones:** 11 of 55 expected repos actually on disk (3.9 GB total). 52 are sparse / missing.

---

## §7. UI — buttons + realtime refresh

### Buttons-without-effect

Out of ~147 `<button>` elements:

| Class | Count | Notes |
|---|---|---|
| Real backend call (fetch) | ~85 | Healthy |
| Local-state only (navigation/filter) | ~45 | Acceptable for tab switches |
| **NO onClick handler (BROKEN)** | **5** | SourceOS AppCard 534+547, Design TemplateCard 880, Plugins 151-153 |
| Always disabled (DISABLED_WITH_REASON) | ~8 | Acceptable |

Visible placeholder strings still in JSX:
* `Workflows.tsx:9` — "sample/placeholder rows" (comment, not visible UI)
* `SourceOS.tsx:223` — "Waiting for verifier summary"
* `FreezeThawControls.tsx:50` — "/api/autopilot/{path} is not implemented" (this one IS visible to users)
* `McpSubtab.tsx:6` — "MCP locks API unavailable" (only when route fails — acceptable)

### Realtime refresh per tab

| Tab | Polling | Refresh button | Classification |
|---|---|---|---|
| Dashboard | no | no | **STALE_RISK** |
| Files | no | yes | STALE_RISK |
| Artifacts | no | no | **STALE_CONFIRMED** |
| Agents | no | yes | STALE_RISK |
| Jobs | partial (only queued/printing 10 s) | no | STALE_RISK |
| Gen3D | no | no | STALE_RISK |
| Plugins | no | yes | STALE_RISK |
| Design | yes (15 s + 30 s dual) | no | LIVE |
| Approvals | yes (5 s) | no | LIVE |
| Autopilot | yes (30 s) | no | LIVE |

**7 of 10 tabs need polling.** Minimal fix: `useEffect` interval at 10-15 s for each, calling the same fetch the tab already uses on mount.

---

## §8. Provider keys

The backend reads 27 distinct provider env-var names. `G:\private\.env` contains 21 keys. Of those, **only 2 are live-smoke-verifiable today**: MiniMax and DeepSeek (because the smoke endpoint is wired for those two specifically).

Keys present in `G:\private\.env`:

```
AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
CODERABBIT_API_KEY
DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
GITHUB_TOKEN
HUGGINGFACE_TOKEN
LMSTUDIO_BASE_URL
MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_TOKEN_PLAN_API_KEY
OLLAMA_BASE_URL
OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
SILICONFLOW_API_KEY
HERMES3D_MINIMAX_API_KEY, HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY
HERMES3D_DEEPSEEK_API_KEY
HERMES3D_AGENT_RUNTIME_URL, HERMES3D_AGENT_RUNTIME_MODEL
```

Keys the backend looks for but **NOT in `.env`** (action required only if you want them):
```
ANTHROPIC_API_KEY        (Claude Anthropic) — optional
REPLICATE_API_KEY        — optional
OPENROUTER_API_KEY       — optional
HIPFIRE_BASE_URL         — optional local LLM
HERMES3D_LLM_PROVIDER, HERMES3D_LLM_API_KEY, HERMES3D_LLM_BASE_URL, HERMES3D_LLM_MODEL
                         (generic selector — only if used)
```

No smoke endpoints exist for SiliconFlow, GitHub, CodeRabbit, HuggingFace, OpenAI, Azure Speech today. They are read at call-time but never proactively probed.

---

## §9. Backend stubs / 501s / NotImplementedError

* `raise HTTPException(status_code=501` — **2 files** (`apps.py`, `files.py`). Both are intentional honest-blocked: POST writes are operator-frozen.
* `raise NotImplementedError` — **0**
* `# TODO` / `# FIXME` / `# XXX` — **0** in routes (clean)
* Skeleton returns (`[]`, `{}`) — 35 patterns across 15 files. Top 5:
  * `system.py` 6 patterns
  * `agents.py` 5 patterns
  * `learning.py` 4 patterns
  * `design.py` 4 patterns
  * `update_center.py` 3 patterns
* Honest-blocked surfaces returning `accepted: false`:
  * `GET /api/connectors` — `connector_registry_not_yet_implemented` (NOT_IMPLEMENTED — needs work)
  * `GET /api/skills` — `skill_registry_not_yet_implemented` (NOT_IMPLEMENTED — needs work)

Route registration check: all 18 documented endpoints exist in `app.py` **except** `/api/agents/providers/health` (only `/api/agents/health` is registered). UI may 404 on the more-specific path.

---

## §10. Tests + CI

* Python unit tests: 87 files
* Python integration tests: 31 files
* Playwright e2e specs: 39 files
* **34 skipped tests** across 17 files (worst: `test_slicer_route.py` 3 skips, `test_v013_post_promotion_smoke.py` 5 skips)
* **21 of 37 route files have NO direct test coverage:** `autopilot.py`, `desktop_compat.py`, `learning.py`, `settings_themes.py`, `agent_queue.py` (new), `artifacts.py`, `autonomous.py`, `connectors.py`, `dashboard_layouts.py`, `desktop_updates.py`, `events.py`, `notifications.py`, `observe.py`, `plugins.py`, `ports.py`, `roadmap.py`, `settings.py`, `skills.py`, `source_os.py`, `voice.py`, `files.py`
* Latest 3 CI runs on develop:
  1. **PR #258 develop push** — FAILED (Layer C — the regression PR #259 fixes)
  2. PR #257 develop push — SUCCESS
  3. PR #256 develop push — SUCCESS

---

## §11. Docs-vs-reality drift in prior handoffs

W20 audit's WORKING_REAL claims were spot-checked on 5 random entries (`/api/sources/readiness`, `/api/apps`, `/api/artifacts`, `/api/agents`, `/api/approvals`). **All 5 verified.** W20 audit is factually honest.

W20's "P0 — `POST /api/design/generate` 404" is **outdated** — UI calls `/api/design/intake`, which works. W20 audit was corrected in PR #256.

W20's "agents idle, no dispatch code" was true at audit time, fixed by W21-A4 MVP-1 + MVP-2 the next day.

**No AI slop detected in W20.** W21-A4 audit doc is similarly verified.

---

## §12. The full W21 punch list (this is the actual work-todo)

### P0 — blocks day-to-day use

1. **PR #259 hotfix** (already open) — Layer C `CancelledError` fix. **Must merge first.**
2. **MVP-3 persona execution surface** — agents claim but produce no deliverable. Either auto-execute a small subset of audit-type tasks via MiniMax/DeepSeek, or mark them `BLOCKED_HUMAN` honestly. Either way: claim ≠ work.
3. **Free GPU VRAM** — 22.1 GB is in use by an unknown tenant. Either restart the host, find and free the process, or accept Gen3D is blocked.
4. **Reconcile artifact tracking** — 206 artifacts on disk, 0 in DB. `reconcile_var_artifacts` must actually populate the jobs/artifacts tables on startup. Find why it silently fails today.

### P1 — promised but missing

5. **Gen3D install — minimum viable**
   * `pip install rembg --upgrade` (resolve NumPy conflict)
   * `pip install` TripoSR (4 GB VRAM, simplest)
   * Service-start docs for ComfyUI
   * Register URLs in settings → `/api/gen3d/providers` flips to `ready` for at least one
6. **UI realtime polling** — add 10-15 s `useEffect` interval to 7 stale tabs: Dashboard, Files, Artifacts, Agents, Gen3D, Plugins, Jobs.
7. **Fix 5 buttons-without-onClick** — SourceOS AppCard ×3, Design TemplateCard, Plugins ×3.
8. **`/api/agents/providers/health`** endpoint missing — UI gets 404. Either add it or remove the UI call.
9. **W21-P1 design templates** (already stashed) — restore + ship after #259 merges. Adds 2 templates (calibration_cube, simple_box) + dispatch + 26 tests.
10. **Run 18 app proofs** — each app has a `proof_command` already. Run them and persist `last_proof_status=success`. Goes from "1 of 60 proven" to "19 of 60 proven" with one batch.

### P1 — gaps in features the UI advertises

11. **Connector registry** — currently honest-blocked. Implement the actual registry the schema is ready for.
12. **Skills registry** — same shape, same gap.
13. **57 STLs missing proof.json siblings** — back-fill or stop generating without proof.

### P2 — coverage / hygiene

14. **21 untested routes** — at least add 1 smoke test each (200 response shape check).
15. **34 skipped tests** — un-skip what's unskippable, document why for the rest.
16. **41 source-lab repos** — operator decision on sparse-checkout-vs-full-clone for the missing 41.
17. **Provider key gaps** — only add ANTHROPIC/REPLICATE/OPENROUTER if the operator actually uses those providers.

### P2 — features I have NOT verified at all

18. **Approvals → real workflow** — table exists with state transitions, **0 rows**. Need a seed flow + a Playwright E2E that approves something.
19. **Roadmap interactivity** — read-only display; the underlying proof data is real.
20. **Jobs DB seeding** — schema ready, 0 rows. Real prints need to land in this table.

---

## §13. Promise vs. actual count

The user asked: "is it 95% E2E?" — answer: **no.**

| Layer | Honest score | Reasoning |
|---|---|---|
| GUI shell (boots, routes, layout, themes, settings persistence) | **~85%** | Real |
| Backend HTTP wiring (envelopes, honest-blocked semantics) | **~80%** | Real |
| Provider key loading + LLM smoke | **~70%** | Real for MiniMax + DeepSeek; ~5 other providers ignored |
| Slicer | **~95%** | Real |
| Plugin activate/deactivate | **~85%** | Real DB updates |
| Design tab (1 template) | **~70%** | Real but narrow |
| **Hermes Agent execution loop** | **~10%** | Claim works. Work does not. |
| **Gen3D pipeline** | **~5%** | Nothing usable today |
| **Realtime UI refresh** | **~30%** | 3 of 10 tabs only |
| **DB-disk reconciliation** | **~10%** | 206 vs 0 |
| **Test coverage of routes** | **~43%** | 16/37 covered |
| **W21 deliverables shipped** | **~12%** | 1 of 8 handoff docs written, 0 of 8 work products complete |

Weighted (gut estimate, not a benchmark): **~55-65% E2E day-to-day usability.** The rest is documented above; every gap has a fix path.

---

## §14. Rules followed in this audit

* No printer hardware actions.
* No fake pass — the failed CI run was reproduced locally before being claimed-fixed.
* No route-only green — every claim cites file:line, byte counts, or HTTP response.
* No broad skips — 20 sub-audits dispatched, all 20 returned evidence.
* LM Studio is NOT MiniMax — §1 + §8 keep them separate.
* Every fixed feature must prove backend + artifact + UI refresh. The gap list (§12) ranks fixes by where each of those three legs is missing.
