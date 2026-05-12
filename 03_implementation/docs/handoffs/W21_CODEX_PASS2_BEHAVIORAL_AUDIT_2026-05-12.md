# W21 Codex Pass 2 - Behavioral Probe Audit

Date: 2026-05-12
Auditor: Codex with 6 capped sub-agents
Repo: `G:\Github\Hermes3D`
Backend: `http://127.0.0.1:8765`
Mode: safe behavior probes only. No printer hardware actions.

## Method

Pass 2 probes live behavior and local runtime state. It intentionally avoids printer writes, camera probes, Moonraker mutations, update-center write paths, generation installs, and large GPU jobs.

The backend was checked live. The queue poller was disabled for the probe run where needed so audit calls did not mutate queue state.

## Live API Baseline

| Probe | Result |
|---|---|
| `GET /health` | 200, runtime ready |
| `GET /openapi.json` | 200, 265 paths, 280 operations |
| `GET /api/agents/health` | 200, bridge ready |
| `GET /api/agents/queue/status` | 200, accepted |
| `GET /api/gen3d/providers` | 200 |
| `GET /api/design/providers` | 200 |

The OpenAPI operation count matches the source route count from Pass 1.

## Safe Endpoint Sweep

Agent behavioral sweep:

| Category | Result |
|---|---:|
| Selected non-printer GETs | 68 |
| GETs returning 200 within 12s | 65 |
| GETs timing out at 12s but passing with longer timeout | 3 |
| Safe/read-only POSTs returning 200 | 3 |
| Safe/read-only POSTs returning 501 | 1 |

Slow endpoints:

| Endpoint | Longer retry result |
|---|---|
| `/api/code-operator/cli-runners` | 200 in about 17.8s |
| `/api/code-operator/e2e/readiness` | 200 in about 18.2s |
| `/api/code-operator/sandbox/readiness` | 200 in about 17.5s |

Behavioral interpretation: these endpoints are present, but normal UI/e2e timing can misclassify them as broken. W21 tests need lag-protected waits around code-operator readiness.

Safe POST results:

| Endpoint | Result |
|---|---|
| `POST /api/code-operator/repo/search` | 200, `status=ready`, count 3 |
| `POST /api/code-operator/files/read` | 200, read `README.md` lines 1-5 |
| `POST /api/code-operator/history/list` | 200, `status=ready`, count 0 |
| `POST /api/files` | 501, honest blocked `write_not_implemented` |

## Agents Behavior

Live `/api/agents/health` shows:

| Item | Behavior |
|---|---|
| Runtime bridge | ready |
| Local fallback | LM Studio/Ollama available |
| MiniMax key | present after env loader |
| DeepSeek key | present after env loader |
| Personas | still idle |

Live `/api/agents/queue/status` showed:

| Queue bucket | Count |
|---|---:|
| pending | 0 |
| claimed | 8 |
| done | 0 |
| blocked | 0 |

This is the central W21 truth: the queue bridge can claim tasks, but there is no evidence that personas execute the tasks or produce the expected handoff files. Claimed is not done.

Behavioral classification:

`CLAIM_WORKS_EXECUTION_MISSING`

Required fix:

Implement MVP-3 so a claimed task either produces a handoff/result artifact or is marked `blocked` with a reason. A task cannot stay in claimed forever while the UI presents agent activity as productive.

## Gen3D Behavior

Live provider behavior:

| Provider | Live state |
|---|---|
| ComfyUI | `not_installed` / not reachable as service |
| TRELLIS.2 | `not_installed` |
| Hunyuan3D | `not_installed` |
| TripoSR | `not_installed` |
| BambuStudio bridge | installed but not running |

Local machine evidence:

| Area | Behavior |
|---|---|
| RTX 3090 Ti CUDA | available |
| Free VRAM | too low during audit, about 2.1-2.4 GB free |
| ComfyUI repo | present and very large |
| Hunyuan3D shape weight | present under ComfyUI model folders |
| rembg | missing in backend/Comfy environment |
| TripoSR | repo/docs found, not a usable installed provider |
| TRELLIS | repo found, no ready weights/service |

Backend `/api/generation/run` behavior is local-template generation, not real provider execution. Provider cards being visible does not mean provider-backed generation works.

Behavioral classification:

`GEN3D_PROVIDER_PIPELINE_NOT_WORKING_REAL`

Required fixes:

1. Install/repair the provider environment.
2. Start/register at least one service.
3. Wire `/api/generation/run` to the provider path when a provider template is selected.
4. Send and read reference images for image-to-3D.
5. Install/remediate background removal for non-transparent logo input.

## Design Behavior

Design intake behavior:

| Path | Behavior |
|---|---|
| `POST /api/design/intake` with desk-organizer-style prompt | creates real STL and proof |
| Freeform custom modeling prompt | blocked/rejected unless resolved to supported template |
| Hermes logo/image modeling | not implemented as real image-to-CAD/image-to-3D |

Provider/toolchain behavior:

| Tool | Live behavior |
|---|---|
| OpenSCAD | ready |
| Blender | ready |
| trimesh | ready |
| manifold3d | ready |
| CadQuery | not installed |
| FreeCAD | not installed |

Behavioral classification:

`DESIGN_WORKING_NARROW_TEMPLATE_ONLY`

Required fixes:

1. Land the stashed template work for `calibration_cube` and `simple_box`.
2. Add proof generation for every template, not just desk organizer.
3. Add honest UI wording: freeform prompt is not arbitrary CAD yet.
4. Wire image/logo intake to the Gen3D/background-removal path or mark it blocked.

## Slicer Behavior

Slicer behavior is one of the strongest areas.

Evidence:

| Item | Behavior |
|---|---|
| Slicer route | real `POST /api/slice` and job status route |
| Core execution | shells out to PrusaSlicer/OrcaSlicer |
| G-code artifacts | present under `var/slicer` |
| Proof artifacts | present |
| G-code analyzer | parses output metrics |

Behavioral classification:

`SLICER_WORKING_REAL`

Remaining UX issue:

Model-to-slice handoff is fragmented. If the user creates a model and refreshes or switches context, the UI may lose the in-memory action path even though files exist on disk.

## Files, Artifacts, and DB Behavior

Runtime DB correction:

`G:\Github\Hermes3D\03_implementation\var\hermes3d.db` is the live DB.

Observed runtime DB behavior from the files/artifacts agent:

| Table/thing | Observed |
|---|---:|
| jobs | 44 |
| artifacts | 202 |
| proof events | 394 |
| truth-gate rows | 29 |
| artifact paths missing on disk | 0 |

This corrects a previous bad conclusion based on the wrong zero-byte DB path under `data`.

Remaining behavioral gaps:

| Gap | Effect |
|---|---|
| One scanner-relevant G-code not in DB | file visible on disk but not reconciled |
| 102 artifacts with null `job_id` | lineage is weak |
| Slicer files classified under modeling stage | UI/proof semantics are misleading |
| Files UI still falls back to artifacts copy | user sees stale "not shipped" assumptions |

Behavioral classification:

`ARTIFACTS_REAL_BUT_LINEAGE_AND_UI_STALE`

## Apps and Source OS Behavior

App registry behavior remains mixed:

| Bucket | Count |
|---|---:|
| Total app entries | 60 |
| Apps with proof command | 19 |
| Apps proven success | 1 |
| Apps failed proof | 2 |
| Apps never proofed | 56 |
| Apps missing/not installed/source-only | 4 |

The app registry is not a pure stub. But most apps are not proven day-to-day usable.

Behavioral classification:

`REGISTRY_REAL_PROOFS_MOSTLY_NOT_RUN`

Required fixes:

1. Run the 18 remaining proof-capable app commands.
2. Persist proof status and last-run timestamp.
3. Fix or honestly mark failed apps.
4. Install missing app packages only if they are in the desired day-to-day scope.

## UI Behavior Findings

Known action problems:

| UI area | Behavior |
|---|---|
| Source OS detail actions | buttons disabled or lacking backend endpoints |
| Dashboard Action Window | route/mount mismatch |
| Freeze/Thaw controls | UI describes missing backend route |
| Generic panel overflow menu | disabled |
| Files tab | stale fallback behavior despite backend being real |
| Apps route | double-wired app registry path |

Realtime behavior:

| Tab | Behavioral state |
|---|---|
| Design | polling/live |
| Approvals | polling/live |
| Autopilot | polling/live |
| Dashboard | stale risk |
| Files | stale risk |
| Artifacts | stale confirmed/risk |
| Agents | stale risk |
| Gen3D | stale risk |
| Plugins | stale risk |
| Jobs | partial |

Behavioral classification:

`UI_SHELL_REAL_REALTIME_INCOMPLETE`

## Pass 2 Verdict

The backend is much more real than the user feared in some areas: OpenAPI matches source, env keys load, slicer is real, DB artifacts exist, and design can create a real desk-organizer STL.

The product still feels 55-65 percent E2E because the high-value user paths stop at the exact places the user keeps noticing:

1. Agents claim but do not execute.
2. Gen3D providers are not usable.
3. Image-to-3D does not move the uploaded image through a provider/background-removal pipeline.
4. Design is one-template narrow.
5. Most app proofs have never run.
6. Several tabs do not update in realtime.
7. Some controls are visible but disabled, stale, slow, or backed by missing endpoints.

This pass confirms that "green CI" is not equivalent to "day-to-day complete."
