# W21 Codex Pass 1 - Structural Inventory Audit

Date: 2026-05-12
Auditor: Codex with 6 capped sub-agents
Repo: `G:\Github\Hermes3D`
Scope: structure only. This pass inventories what exists and how it is registered. It does not call something "working" unless later passes probe behavior.

## Method

The user explicitly capped the audit at 4-6 agents. Codex used 6 agents, each with a separate ownership slice:

1. Backend route and test coverage
2. UI tabs, controls, and static action wiring
3. Live endpoint map and safe probe readiness
4. Gen3D/provider/model inventory
5. Design/modeler/template/STL inventory
6. Slicer/files/artifacts/DB inventory

No printer hardware actions were taken.

## Backend API Surface

The live GUI API is mounted from:

`G:\Github\Hermes3D\03_implementation\src\hermes3d\api\app.py`

Route modules live under:

`G:\Github\Hermes3D\03_implementation\src\hermes3d\api\routes`

Structural count from source and live OpenAPI:

| Item | Count |
|---|---:|
| Route modules | 37 |
| Unique OpenAPI paths | 265 |
| Total operations | 280 |
| GET | 134 |
| POST | 130 |
| PUT | 12 |
| PATCH | 3 |
| DELETE | 1 |

Largest route groups:

| Module | Operations |
|---|---:|
| `code_operator.py` | 55 |
| `modules.py` | 39 |
| `agents.py` | 19 |
| `printers.py` | 12 |
| `observe.py` | 12 |
| `jobs.py` | 10 |
| `system.py` | 10 |
| `autonomous.py` | 9 |
| `learning.py` | 9 |
| `voice.py` | 9 |
| `generation.py` | 8 |
| `notifications.py` | 7 |
| `plugins.py` | 7 |
| `printer_safety.py` | 7 |

Structural conclusion: the API surface is large and registered. Registration is not the same as product readiness.

## UI Route Surface

Registered React tab components were found under:

`G:\Github\Hermes3D\03_implementation\ui\src\tabs`

The route table exposes 25 route keys, including primary visible tabs and hidden utility tabs. The visible sidebar exposes only the primary tabs. Utility surfaces exist but are harder to discover.

Primary visible tabs include:

`source-os`, `dashboard`, `autopilot`, `design`, `gen3d`, `jobs`, `printers`, `observe`, `voice`, `agents`, `learning`, `artifacts`, `approvals`, `apps`, `plugins`, `settings`

Hidden or utility route surfaces include:

`files`, `mcp`, `safety`, `roadmap`, `dispatch-gate`, `action-window`, and several supporting diagnostic or workflow panels.

Structural mismatches found:

| Area | Structural issue |
|---|---|
| Apps | `#apps` is double-wired: root intercepts standalone app registry while `App.tsx` also maps `apps`. |
| Dashboard | "Action Window" navigation routes toward `autopilot`; an `ActionWindowMount` exists but is not clearly mounted as the visible destination. |
| Files | `Files.tsx` still contains fallback language around `/api/files` despite the backend now existing. |
| Source OS detail | Several detail actions are disabled because no detail backend exists yet. |
| Generic panels | Overflow menu buttons exist but are disabled. |

## Test Structure

Detected test inventory:

| Test type | Count |
|---|---:|
| Python test files | 162 |
| Python `test_*` functions | 1392 |
| Playwright/e2e specs | 39 |

Endpoint-literal evidence in tests covers only a minority of the API surface:

| Coverage slice | Count |
|---|---:|
| Operations with direct literal or path-pattern evidence | 92 of 280 |
| Route modules with direct endpoint evidence | 21 of 37 |
| Route modules with no direct endpoint-literal evidence | 16 of 37 |

Modules needing direct smoke or contract tests:

`artifacts`, `autonomous`, `autopilot`, `design`, `desktop_updates`, `events`, `jobs`, `learning`, `notifications`, `observe`, `plugins`, `ports`, `settings`, `source_os`, `update_center`, `voice`

This does not mean those modules are broken. It means CI can miss regressions there.

## Hermes Agent Structure

What exists structurally:

| Piece | Exists |
|---|---|
| Agent provider health endpoint | yes |
| Agent queue status endpoint | yes |
| Queue poller and claim path | yes |
| Provider assist endpoint | yes |
| MiniMax/DeepSeek env loader | yes |

What is structurally missing:

| Piece | Missing |
|---|---|
| Persona task execution loop | no code found |
| Handoff markdown auto-generation from claimed task | no code found |
| Persona registration into Hermes locks registry | not observed |
| UI evidence that claimed tasks become done/blocked | not observed |

Structural verdict: W21-A4 MVP-1 and MVP-2 made keys load and tasks claimable. They did not make Hermes personas do work.

## Gen3D Structure

Provider registry exists for:

`comfyui`, `trellis2`, `hunyuan3d`, `triposr`, `bambustudio_bridge`

Local filesystem inventory:

| Provider/source | Structural state |
|---|---|
| ComfyUI | Repo present at `G:\Github\ComfyUI`; very large install tree; server not structurally configured as Hermes service. |
| Hunyuan3D wrapper | ComfyUI custom node present; shape weight file present under ComfyUI models. |
| TRELLIS.2 | Repo present; no confirmed weight cache. |
| TripoSR | Repo/docs present; no confirmed package/weights/service. |
| rembg | Not installed in active backend environment. |

Backend generation structure:

| Path | Reality |
|---|---|
| `/api/gen3d/providers` | provider discovery/readiness |
| `/api/generation/run` | local template executor; currently calibration-cube style local mesh path |
| Provider execution | not structurally implemented as real provider dispatch |
| Reference image payload | model field exists, but UI/backend do not complete a real image-to-3D pipeline |

## Design/Modeler Structure

Design routes exist:

`/api/design/intake`, `/api/design/specs`, `/api/design/templates`, `/api/design/providers`, `/api/design/toolchain/status`, `/api/design/backends`

Design template structure:

| Template | Develop state |
|---|---|
| `desk_organizer` | real template on develop |
| `calibration_cube` | worked in stashed W21-P1 branch, not develop |
| `simple_box` | worked in stashed W21-P1 branch, not develop |
| arbitrary prompt/logo modeling | no real executor found |

CAD toolchain structural state:

| Tool | State |
|---|---|
| OpenSCAD | installed path found |
| Blender | installed path found |
| `trimesh` | installed |
| `manifold3d` | installed |
| CadQuery | missing |
| FreeCAD | missing |

## Files, Artifacts, Slicer, and DB Structure

Important correction: the runtime DB path is:

`G:\Github\Hermes3D\03_implementation\var\hermes3d.db`

The zero-byte or untracked path:

`G:\Github\Hermes3D\03_implementation\data\hermes3d.db`

is not the live runtime DB.

Slicer structure:

| Piece | Exists |
|---|---|
| `POST /api/slice` | yes |
| `GET /api/slice/{job_id}` | yes |
| PrusaSlicer/OrcaSlicer subprocess path | yes |
| G-code analyzer | yes |
| Slice proof artifacts | yes |

Files/artifacts structure:

| Piece | Exists |
|---|---|
| `/api/files` scanner | yes |
| `/api/files/reconcile` | yes |
| `/api/artifacts` DB-backed route | yes |
| Startup reconcile hook | yes, best-effort |

Structural issues:

| Area | Issue |
|---|---|
| Artifacts DB | no unique index found for `file_path`; idempotence appears app-side. |
| Reconciled job links | many artifacts can have null `job_id`. |
| Stage labels | reconcile labels slicer files as modeling-stage evidence. |
| Files UI | does not fully trust/use the now-real `/api/files` surface. |

## 60-App Registry Structure

The app registry contains 60 app entries. Prior W21 evidence and endpoint probes indicate:

| Bucket | Count |
|---|---:|
| Registered apps | 60 |
| Apps with a proof command | 19 |
| Apps already proven success | 1 |
| Apps with proof failure | 2 |
| Apps never proofed | 56 |
| Apps marked not installed/source-only | 4 |

This is structurally better than a placeholder registry, but still not day-to-day proven.

## Pass 1 Verdict

Hermes3D has a large and real shell: routes, tabs, DB schema, provider registries, slicer routes, design routes, app registry, and agent queue routes exist.

The structural gaps that explain the user's experience are:

1. Agent queue claiming exists, but no task execution surface exists.
2. Gen3D provider registration exists, but real provider dispatch is not complete.
3. Design exists, but only one develop template is real.
4. UI route count is high, but several controls are hidden, disabled, double-wired, stale, or wired to missing backend routes.
5. Test coverage does not match the API surface: 188 of 280 operations lack direct endpoint-literal evidence.
6. Runtime DB is real under `var`, but several docs/audits previously checked the wrong DB path.

This pass supports the user's 55-65 percent E2E feeling. The structure exists, but many high-value pathways stop before a user-visible result.
