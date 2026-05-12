# Hermes3D — Complete Project Handover to Codex
**Date:** 2026-05-12  
**Author:** Claude (outgoing)  
**Recipient:** Codex (incoming, full ownership)  
**Status at handover:** W21-MVP-5 merged (PR #266). Branch `claude/w21-mvp6-gen3d-bgremove` checked out, no commits yet — that branch is the **next** work item.

---

## 1. Project Identity and Mission

**Official name:** Hermes Proof-Gated Agentic Workbench  
**Failure recovery subsystem:** Hermes Agent Recovery Controller  
**Project named after:** NousResearch/hermes-agent (confirmed by operator)  

The project is a **local-first, proof-gated 3D printing agentic workbench**. It orchestrates:
- AI-assisted 3D design (OpenSCAD/Blender templates)
- Slicing (PrusaSlicer/OrcaSlicer subprocess)
- Print-farm management (Moonraker/Klipper printer fleet)
- Hermes Agent task queue (MiniMax = builder, DeepSeek = reviewer)
- Source-OS module registry (60 apps)
- Proof-gate evidence chain (every meaningful action emits a proof event)

**Honest current completion:** ~55–65% E2E. The shell is large and real. Several high-value user journeys stop before producing a user-visible result.

---

## 2. Repository Layout

```
G:\Github\Hermes3D\
├── 03_implementation\
│   ├── src\hermes3d\
│   │   ├── api\
│   │   │   ├── app.py                  ← FastAPI app entry, route mounts
│   │   │   └── routes\                 ← 39 route modules (280 operations total)
│   │   ├── core\
│   │   │   └── orchestration\          ← agent_graph.py, task queue
│   │   ├── services\
│   │   │   ├── queue_bridge.py         ← Hermes orchestrator bridge
│   │   │   ├── queue_poller.py         ← auto-poller (claims tasks)
│   │   │   ├── agent_runtime.py        ← persona executor (MVP-3 land)
│   │   │   ├── agent_checkout.py
│   │   │   └── ...
│   │   └── ...
│   ├── ui\
│   │   ├── src\
│   │   │   ├── tabs\                   ← 25 React tab components
│   │   │   ├── hooks\
│   │   │   │   └── _useQuery.ts        ← usePollingEffect, PANEL_POLL_MS=15000
│   │   │   ├── api\
│   │   │   │   └── adapters.ts         ← all frontend→backend calls
│   │   │   └── types\                  ← TypeScript type definitions
│   │   └── tests\
│   │       ├── unit\                   ← Vitest unit tests
│   │       └── e2e\                    ← Playwright E2E specs
│   ├── tests\                          ← 162 Python test files, 1392 test functions
│   ├── var\hermes3d.db                 ← LIVE RUNTIME DB (44 jobs, 202 artifacts, 394 proof events)
│   ├── data\hermes3d.db               ← ZERO-BYTE — ignore this path entirely
│   └── docs\handoffs\                  ← all audit/handoff docs
├── docs\handoffs\                      ← top-level handoffs (less used)
└── .hermes3d_orchestrator\            ← MCP lock/task queue directory
```

**CRITICAL DB CORRECTION:** The real runtime database is at:
```
G:\Github\Hermes3D\03_implementation\var\hermes3d.db
```
`03_implementation\data\hermes3d.db` is zero-byte / untracked and was a source of false "empty DB" conclusions in prior audits. Always use `var\hermes3d.db`.

---

## 3. Environment and Secrets

**All secrets live OUTSIDE every repo at:**
```
G:\private\.env
```
Never commit secrets. Never move them into the repo. This is a strict operator rule after a 2026-05-03 incident.

Key env vars present in `G:\private\.env`:
- `MINIMAX_API_KEY` — MiniMax M2 builder provider
- `DEEPSEEK_API_KEY` — DeepSeek reviewer provider  
- `VITE_HERMES3D_BRIDGE_PORT` — UI bridge port (default 8765)
- `HERMES3D_WORKSPACE_ROOT` — set by orchestrator MCP when running

Provider routing rule (STRICT from memory):
- **MiniMax** = builder tasks
- **DeepSeek** = reviewer tasks
- LM Studio / Ollama = dev-only fallback, NOT for production proof

---

## 4. Backend Service

- **Framework:** FastAPI + Uvicorn
- **Default port:** `http://127.0.0.1:8765`
- **Entry point:** `03_implementation/src/hermes3d/api/app.py`
- **OpenAPI:** `http://127.0.0.1:8765/openapi.json` (265 paths, 280 operations)
- **Health:** `GET /health` → 200 when runtime ready

To start backend:
```powershell
cd G:\Github\Hermes3D\03_implementation
# activate venv first, then:
uvicorn hermes3d.api.app:app --port 8765 --reload
```

Known slow endpoints (need lag-protected waits in tests):
- `GET /api/code-operator/cli-runners` → ~17.8s
- `GET /api/code-operator/e2e/readiness` → ~18.2s  
- `GET /api/code-operator/sandbox/readiness` → ~17.5s

---

## 5. Frontend (UI)

- **Framework:** React + TypeScript + Vite + Tailwind CSS
- **Location:** `03_implementation\ui\`
- **Dev server:** `npm run dev` (port 5173 by default)
- **Test runner:** Vitest (unit) + Playwright (E2E)

Key files:
```
ui/src/hooks/_useQuery.ts           ← usePollingEffect hook (lag-protected, 15s poll)
ui/src/api/adapters.ts              ← all API calls — single source of truth
ui/src/tabs/                        ← 25 tab components
ui/tests/unit/usePollingEffect.test.tsx   ← 7 behavioural tests for the polling hook
ui/tests/e2e/_helpers.ts            ← shared Playwright helpers, TAB_FIXTURES
ui/tests/e2e/w21-mvp5-stale-ui-refresh.spec.ts  ← polling E2E proof (Files, Artifacts, Agents)
```

`PANEL_POLL_MS = 15_000` is the standard polling interval. Imported from `_useQuery.ts` by all 5 newly-polled tabs.

UI test commands:
```powershell
cd G:\Github\Hermes3D\03_implementation\ui
npm run test              # Vitest unit
npx playwright test       # Playwright E2E
npx playwright test --ui  # Interactive mode
```

---

## 6. Git State at Handover

**Active branch:** `claude/w21-mvp6-gen3d-bgremove` (no commits ahead of develop yet — this is the NEXT work item)

**Latest merged commit (HEAD of develop):**
```
62e8703 feat(W21-MVP-5): realtime polling for Files / Artifacts / Agents / Gen3D / Plugins (#266)
```

**Recent merged PRs (chronological):**
```
#266  W21-MVP-5: realtime polling (Files/Artifacts/Agents/Gen3D/Plugins)
#265  W21-MVP-4: /api/artifacts/{id}/lineage — parent/child traversal
#264  W21-MVP-3: sanitizer + quality gate + preserve-existing for persona executor
#263  W21-MVP-3: Hermes Agent persona executor — claimed tasks produce deliverables
#262  W21-P0-C: cache /api/health/services (Dashboard cold-start fix)
#261  W21: 3-pass deep audit docs
#260  W21: brutally honest reality-gap audit
#259  W21-A4 fix: swallow CancelledError on poller shutdown
#258  W21-A4: MVP-2 orchestrator queue bridge + auto-poller
#257  W21-A4: MVP-1 env-file loader + activation audit doc
```

**Important stash:**
```
stash@{0}: On claude/w21-p1-design-templates: W21-P1 in-progress design templates 
           (lag-protection added) — held until agents activated
```
This stash contains `calibration_cube` and `simple_box` templates that were implemented but held. Now that MVP-3 persona executor is merged, this stash should be popped and the branch PRed.

---

## 7. Operator-Imposed Constraints (STRICT — Never Violate)

1. **No printer hardware writes** — W18+ freeze. Never touch print queue writes, Moonraker mutations, firmware flashes. A8/A9 are software-only.
2. **No fake data / mock passes** — FORBIDDEN_VISIBLE_TERMS: `TODO`, `FIXME`, `lorem ipsum`, `placeholder text`, `sample data`, `mock data`, `dummy data`, `fake data`. Zero-tolerance.
3. **No route-only green** — A route returning 200 does not mean the feature is complete.
4. **No paid services** — free/open-source only. Sigstore + GitHub Attestations + GitHub Packages, never Azure Artifact Signing.
5. **Standing merge authorization** — Auto-merge all green PRs ASAP.
6. **Recovery loop is mandatory** — failure → classify → freeze → snapshot → MiniMax fix → DeepSeek review → apply → re-run → resume. Never stop at first blocker.
7. **Weakness-correction is strict** — every audit finding must be fixed in a PR, not noted-and-skipped.
8. **No AI slop** — no vague hand-wavy conclusions. Every claim must be backed by evidence.
9. **Lag-protected waits in Playwright** — never use instant assertions after async backend operations. Use `toContainText(..., { timeout: 25_000 })` and drain microtasks with `await Promise.resolve()`.
10. **Max 6 agents per sweep** — user explicitly capped at 4–6 sub-agents. Do NOT run a 20-agent sweep again.
11. **Printer hardware freeze** — `GUI_PHYSICAL_PRINT_GREEN` and `GUI_PRINTER_DRY_RUN_GREEN` are both `OUT_OF_SCOPE_BY_OPERATOR`.

---

## 8. Proof-Gate System

Proof events are emitted via `adapters.emitProofEvent(event_name, payload)` in the frontend, or `POST /api/proof/events` from backend. The `var/hermes3d.db` stores:
- `artifacts` table — 202 rows (design STLs, G-code, reports, meshes)
- `proof_events` table — 394 rows
- `truth_gates` table — 29 rows
- `jobs` table — 44 rows

Every meaningful feature completion requires:
1. Backend endpoint returning real data (not placeholder)
2. UI reflecting the result (with polling or SSE)
3. Proof event emitted and stored in DB
4. Playwright spec proving it E2E with real backend

---

## 9. Hermes Agent System (Critical Context)

### Architecture
The Hermes Agent system uses a task queue stored in:
```
G:\Github\Hermes3D\.hermes3d_orchestrator\
```

Queue bridge code: `03_implementation/src/hermes3d/services/queue_bridge.py`
Queue poller: `03_implementation/src/hermes3d/services/queue_poller.py`
Persona executor (W21-MVP-3, now merged): `03_implementation/src/hermes3d/services/agent_runtime.py`

### Current Queue State (as of audit 2026-05-12)
```
pending: 0
claimed: 8
done:    0
blocked: 0
```
**PROBLEM:** 8 tasks stuck in `claimed` state. MVP-3 persona executor was merged (#263/#264) but may not have cleared these. Codex must verify whether the 8 claimed tasks can be run to completion or released.

### API Routes
```
GET  /api/agents                     — agent roster
GET  /api/agents/health              — provider health (MiniMax/DeepSeek keys)
GET  /api/agents/queue/status        — pending/claimed/done/blocked counts
POST /api/agents/queue/claim/{id}    — operator-triggered claim
POST /api/agents/queue/complete/{id} — operator-triggered completion
POST /api/agents/queue/block/{id}    — mark blocked with reason
POST /api/agents/queue/release/{id}  — release back to pending
POST /api/agents/assist              — direct MiniMax/DeepSeek assist call
GET  /api/agents/tasks               — task list with action catalog
```

### Persona Executor (MVP-3)
Located in `03_implementation/src/hermes3d/services/agent_runtime.py` (merged in #263/#264). The executor:
- Reads claimed tasks
- Routes to MiniMax (builder) or DeepSeek (reviewer) based on task type
- Produces a handoff markdown file at `task.handoff_path`
- Transitions task to `done` or `blocked` with reason

**Next step for agents:** Verify 8 claimed tasks are now processable or release them. Confirm the executor actually runs when the poller picks up tasks.

---

## 10. Gen3D — Current State and Next Work

**Active branch for this work:** `claude/w21-mvp6-gen3d-bgremove`

### What Exists
- Provider registry in DB: `comfyui`, `trellis2`, `hunyuan3d`, `triposr`, `bambustudio_bridge`
- ComfyUI repo at `G:\Github\ComfyUI` (very large)
- Hunyuan3D shape weight present under ComfyUI model folders
- RTX 3090 Ti CUDA available (but only 2.1–2.4 GB VRAM free during audit — need to free VRAM)
- `GET /api/gen3d/providers` — 200, shows providers but all `not_installed`
- `POST /api/generation/run` — works but generates a **local template mesh**, NOT a real provider-backed model

### What's Missing (The MVP-6 Work)
1. **`rembg` not installed** — background removal for non-transparent PNG inputs is blocked
2. **Provider services not started** — none of the 5 providers register as `ready`
3. **Real provider dispatch** — `/api/generation/run` does not call ComfyUI/Hunyuan/TripoSR yet
4. **Image → provider pipeline** — UI does not pass `reference_artifact_id` through to backend for image-to-3D
5. **Logo workflow** — Hermes logo PNG needs: upload → `rembg` background removal → provider dispatch → STL → artifact

### Recommended Minimal Path
1. Free VRAM (kill any GPU-heavy processes)
2. Install `rembg` in backend venv
3. Start ComfyUI server (Hunyuan3D wrapper weights already present)
4. Make `/api/gen3d/providers` show ComfyUI as `ready`
5. Wire `/api/generation/run` to dispatch to ComfyUI when provider template selected
6. Pass `reference_image` bytes through UI → backend → rembg → provider
7. Write output mesh as artifact in `var/hermes3d.db`
8. Playwright proof: upload logo PNG, get STL artifact, no white-background geometry

---

## 11. Design Templates — Stash Ready to Pop

Stash `stash@{0}` on branch `claude/w21-p1-design-templates` contains:
- `calibration_cube` template — tested, lag-protection added
- `simple_box` template — tested, lag-protection added

These templates were implemented and lag-tested but held until agent activation was confirmed (MVP-3). **MVP-3 is now merged.** Pop the stash, run tests, open PR.

Current design state:
- `desk_organizer` — on develop, real STL + proof ✓
- `calibration_cube` — in stash, needs PR
- `simple_box` — in stash, needs PR

Design routes:
```
POST /api/design/intake          — create STL from prompt/template
GET  /api/design/templates       — list available templates
GET  /api/design/specs           — design specifications
GET  /api/design/providers       — design providers (OpenSCAD=ready, Blender=ready)
GET  /api/design/backends        — backend tool status
GET  /api/design/toolchain/status — toolchain health
```

Available CAD tools: `OpenSCAD` (installed), `Blender` (installed), `trimesh` (installed), `manifold3d` (installed).
Missing: `CadQuery`, `FreeCAD` (not required for current templates).

---

## 12. Artifact / File Lineage — Known Gaps

Runtime DB at `var/hermes3d.db`:
- 202 artifacts — 102 have `null job_id` (weak lineage)
- Slicer files are incorrectly classified as `stage=MODELING` (should be `SLICING`)
- One scanner-relevant G-code file exists on disk but is not reconciled into DB
- No unique index on `file_path` — idempotence is app-side only

Reconcile endpoint: `POST /api/files/reconcile`  
Files scanner: `GET /api/files` (real, works)  
Artifacts DB route: `GET /api/artifacts` (real, works)

Fix required:
1. Normalize `stage`/`gate` labels for slicer artifacts
2. Link slicer artifacts to their job_id
3. Reconcile the missing G-code into DB
4. Add unique index on `file_path` or enforce idempotence at DB level

---

## 13. Realtime UI Polling — What's Done and What's Still Missing

**DONE (W21-MVP-5, PR #266):**
- Files tab — `usePollingEffect(refresh, PANEL_POLL_MS)` ✓
- Artifacts tab — list + proof manifest poll ✓
- Agents tab — roster + notifications + idle workbench poll ✓
- Gen3D tab — provider health + providers + templates poll ✓
- Plugins tab — plugin list polls ✓

**STILL STALE:**
- Dashboard — partial SSE, some panels not refreshed
- Jobs — partial polling
- Source OS — no polling (by design — rare changes)

**Hook contract (pinned by unit tests):**
```typescript
// In ui/src/hooks/_useQuery.ts
export function usePollingEffect(
  effect: () => void | Promise<void>,
  intervalMs: number,
  deps: DependencyList,
): void
```
- Calls effect immediately on mount (no waiting for first tick)
- Re-fires on `intervalMs` interval
- Lag-protected: skips tick if previous is still in-flight
- Cleanup on unmount: clears interval, respects `cancelled` flag
- Uses `effectRef` pattern: always calls latest closure

**E2E proof spec:** `ui/tests/e2e/w21-mvp5-stale-ui-refresh.spec.ts` covers Files, Artifacts, Agents.

---

## 14. App Registry — 60 Apps State

```
Total registered:  60
With proof cmd:    19
Proven success:     1
Failed proof:       2
Never proofed:     56  ← this is the gap
Not installed:      4
```

App registry route: `GET /api/apps` (returns all 60)  
Proof command run: via Source OS runner infrastructure  

Action required: run the 18 remaining proof-capable apps (not the 2 already failed, not the 1 success), persist `last_proof_status` + timestamp, fix or honestly mark failures.

---

## 15. Known UI Problems (Disabled/Broken Controls)

| UI area | Problem |
|---------|---------|
| Source OS detail actions | Buttons exist but backend endpoints missing |
| Dashboard Action Window | Route/mount mismatch — `ActionWindowMount` exists but not clearly wired |
| Freeze/Thaw controls (Autopilot) | UI references backend route that doesn't exist yet |
| Generic panel overflow menu | Disabled |
| Files tab | Still contains stale fallback copy from before `/api/files` was real |
| Apps route | Double-wired: both `#apps` intercept AND `App.tsx` `apps` mapping |

Each of these must either get a real backend route or be converted to an honest-disabled state with a visible reason. No silent no-ops.

---

## 16. Test Coverage Gaps

**Backend (Python):**
- 162 test files, 1392 test functions
- 34 skipped tests across 17 files
- 188 of 280 API operations have NO direct endpoint-literal test evidence
- Route modules needing direct smoke tests: `artifacts`, `autonomous`, `autopilot`, `design`, `desktop_updates`, `events`, `jobs`, `learning`, `notifications`, `observe`, `plugins`, `ports`, `settings`, `source_os`, `update_center`, `voice`

**Frontend (Playwright/Vitest):**
- 39 E2E specs (Playwright)
- Unit tests for `usePollingEffect` (7 tests, all passing)

Test commands:
```powershell
# Backend Python
cd G:\Github\Hermes3D\03_implementation
pytest tests/ -x -v

# UI unit
cd ui && npm run test

# UI E2E
cd ui && npx playwright test

# Backend test specific module
pytest tests/test_agents.py -v
```

---

## 17. MCP Locks Orchestrator

**Repo:** `G:\Github\hermes3d-mcp-lock-orchestrator`  
**MCP server:** `hermes3d-locks` (tools prefixed `mcp__hermes3d-locks__*`)

This is the A2A task coordination layer. The orchestrator:
- Assigns tasks to agents via `hermes_enqueue_task` / `hermes_claim_task`
- Tracks evidence via `hermes_append_evidence`
- Manages proof gates via `hermes_run_gate` / `hermes_verify_evidence`
- Lock management via `hermes_lock_files` / `hermes_release_files`

**STRICT rule:** All changes to orchestrator + subagents must be made while `hermes3d-locks` is reachable. Use ALL 20 agents, never skip a lane.

**STRICT rule:** Pre-check `hermes_list_locks` before each lane dispatch to avoid lock collisions (H3D 20-agent lock collision issue from 2026-05-06).

Queue state check:
```powershell
# Check task queue via API
curl http://127.0.0.1:8765/api/agents/queue/status
```

---

## 18. Completion Backlog — Priority Order

### P0 — Must Fix Before Claiming Product E2E

**1. Hermes Agent task execution (8 stuck claimed tasks)**
- Verify MVP-3 executor (#263/#264) actually processes claimed tasks end-to-end
- 8 tasks in claimed state must become done or blocked with reason
- UI must show the transition

**2. Gen3D minimum viable provider path (branch: `claude/w21-mvp6-gen3d-bgremove`)**
- Install `rembg` (background removal)
- Free GPU VRAM (2.4 GB free is not enough for Hunyuan3D)
- Start ComfyUI or TripoSR as a service
- Wire `/api/generation/run` to dispatch to real provider
- End-to-end: PNG → rembg → provider → STL → artifact

**3. Hermes logo image-to-3D pipeline**
- Part of P0 #2 above, but specifically for the Hermes logo PNG
- The operator needs this specific use case proven

**4. Artifact lineage reconciliation**
- Fix `stage` labels (slicer files wrongly labeled as MODELING)
- Link 102 null-`job_id` artifacts to their job where possible
- Reconcile the one missing G-code into DB
- Playwright proof: correct lineage displayed in UI

**5. Design template stash → PR**
- Pop `stash@{0}` on `claude/w21-p1-design-templates`
- `calibration_cube` and `simple_box` were implemented and lag-tested
- Run tests, open PR, merge

### P1 — High Value

**6. Source OS detail actions**
- Implement backend endpoints for proof/log/settings/bridge detail actions
- OR make UI show honest-disabled with visible reason (no silent no-ops)

**7. 60-app proof run**
- Run 18 remaining proof-capable apps
- Persist status + timestamp
- Fix or mark failures

**8. Freeze/Thaw backend route**
- Either implement Autopilot freeze/thaw endpoints
- Or change UI to honest-disabled with reason

**9. Dashboard Action Window mount**
- Fix the route/mount mismatch for the Action Window entry
- Test that clicking it navigates to the correct surface

**10. Apps route double-wire fix**
- Remove one of the two wiring paths for the Apps registry

**11. Code-operator readiness latency**
- Cache or parallelize the 17–18s endpoints
- Add UI progress indicator (don't look frozen)

### P2 — Coverage and Hygiene

**12. Direct route smoke tests for 16 uncovered route modules**
- Add TestClient smoke tests (no hardware)
- Mock adapters for camera/printer routes

**13. Resolve 34 skipped tests**
- Unskip where possible
- Add reason + backlog link for permanent skips

**14. Connectors and skills registries**
- `/api/connectors` and `/api/skills` return `honest_blocked` envelopes
- Implement registry source or keep honest-blocked with clear plan

---

## 19. Coding Conventions

- **Python:** FastAPI routes return `{"accepted": bool, "status": str, "reason": str | None}` honest-blocked envelopes for not-yet-implemented paths
- **TypeScript:** No `any` casts without `eslint-disable`. Use proper types from `src/types/`
- **No mock data in production routes** — honest blocked envelope or real data, never fake rows
- **Polling:** Always use `usePollingEffect` from `_useQuery.ts`, not raw `setInterval`
- **Proof events:** Always emit via `adapters.emitProofEvent()` for meaningful actions
- **Lag-protected Playwright tests:** Use `{ timeout: 25_000 }` on `toContainText` after backend state changes
- **Printer writes forbidden** — any file that touches Moonraker or print queue writes must be reviewed

---

## 20. What Claude Was Working on at Handover

Claude was on branch `claude/w21-mvp6-gen3d-bgremove` with **no commits** — the branch was freshly created as the next work item after MVP-5 merged. The branch name describes the intended work: Gen3D background removal pipeline.

Claude had also completed W21-MVP-5 (PR #266) which closed the stale-tab polling gap for Files, Artifacts, Agents, Gen3D, and Plugins.

The conversation ran out of context window before any code was written on the Gen3D branch.

---

## 21. Recommended First Steps for Codex

1. **Read these audit files (in this order):**
   - `03_implementation/docs/handoffs/W21_CODEX_PASS1_STRUCTURAL_AUDIT_2026-05-12.md`
   - `03_implementation/docs/handoffs/W21_CODEX_PASS2_BEHAVIORAL_AUDIT_2026-05-12.md`
   - `03_implementation/docs/handoffs/W21_CODEX_PASS3_E2E_JOURNEY_AUDIT_2026-05-12.md`
   - `03_implementation/docs/handoffs/W21_CODEX_COMPLETION_BACKLOG_2026-05-12.md`
   - This document

2. **Check agent queue state:**
   ```
   GET http://127.0.0.1:8765/api/agents/queue/status
   ```
   The 8 claimed tasks need to either be executed by MVP-3 or released.

3. **Check current branch:**
   ```powershell
   cd G:\Github\Hermes3D
   git status
   git log --oneline develop..HEAD
   ```
   Should be `claude/w21-mvp6-gen3d-bgremove` with no commits yet.

4. **Pop the design template stash (quickest win):**
   ```powershell
   git checkout claude/w21-p1-design-templates
   git stash pop stash@{0}
   # run tests, open PR
   ```

5. **Then tackle Gen3D (the branch you're on):**
   - Check VRAM availability: `nvidia-smi`
   - Check if `rembg` is installed in the backend venv
   - Check ComfyUI status

6. **Do NOT:**
   - Run another 20-agent sweep
   - Touch printer hardware
   - Claim any feature complete without Playwright proof
   - Use mock/fake data
   - Skip test failures

---

## 22. Quick Reference

| Thing | Location |
|-------|----------|
| Backend entry | `03_implementation/src/hermes3d/api/app.py` |
| Runtime DB | `03_implementation/var/hermes3d.db` |
| Secrets | `G:\private\.env` |
| Frontend adapters | `03_implementation/ui/src/api/adapters.ts` |
| Polling hook | `03_implementation/ui/src/hooks/_useQuery.ts` |
| Tab components | `03_implementation/ui/src/tabs/` |
| Agent queue routes | `03_implementation/src/hermes3d/api/routes/agent_queue.py` |
| Queue bridge service | `03_implementation/src/hermes3d/services/queue_bridge.py` |
| Persona executor | `03_implementation/src/hermes3d/services/agent_runtime.py` |
| Gen3D routes | `03_implementation/src/hermes3d/api/routes/generation.py` |
| Design routes | `03_implementation/src/hermes3d/api/routes/design.py` |
| Slicer routes | `03_implementation/src/hermes3d/api/routes/slicer.py` |
| Artifacts routes | `03_implementation/src/hermes3d/api/routes/artifacts.py` |
| MCP orchestrator | `G:\Github\hermes3d-mcp-lock-orchestrator\` |
| Audit docs | `03_implementation/docs/handoffs/` |
| Visual reference PNGs | `Images-GUI/` (31 PNGs, PR #128) |

---

## 23. Final Honest Assessment

Hermes3D is **not one bugfix from complete**. It has:
- A large, real backend (280 real operations)
- A real slicer (PrusaSlicer/OrcaSlicer subprocess)
- Real artifacts DB (202 artifacts on disk)
- Real design template (desk_organizer → STL)
- Real agent queue (claim path works)
- Real polling UI (5 tabs now polled)
- Real MiniMax/DeepSeek integration (keys load, smoke works)

But the high-value product loops that would make an operator say "this works" are:
1. Agents that **finish tasks** (not just claim them)
2. Gen3D that **produces a real mesh** from an image
3. All 60 apps that have been **proven** (not just registered)
4. Files/Artifacts with **correct lineage** and correct labels
5. UI that **stays current** without manual reload

That is the day-to-day completion path. No audits needed — only implementation and proof.

---

*Handover complete. Claude signing off.*
