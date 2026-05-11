# W19 Product Completion Gap Audit
**Date:** 2026-05-11  
**Audited commit:** `656c0b4` (develop)  
**Audit method:** 6 parallel read-only agents probing live API + codebase  
**Operator verdict on W18:** GUI_COMPLETE claim rejected — route-smoke and CI green ≠ product works  

---

## Why the W18 GUI_COMPLETE Claim Was Incomplete

The W18 Playwright suite (112/112 CI pass) proved that:
- Routes mount and return 200
- UI panels render with correct CSS structure
- Provider smoke pings reach MiniMax/DeepSeek
- Chat round-trip returns a reply

It did NOT prove:
- Clicking Generate in #gen3d produces a model card in the Generated Models panel
- Clicking Start Design in #design produces a downloadable STL (blocked by printer gate)
- A slice job started from the GUI produces a visible G-code download link
- 60 apps have honest proof status (1/60 is INSTALLED_PROVEN)
- MiniMax/DeepSeek can assist an actual model or slice task that appears in the GUI
- The Files tab is functional (`file_store_not_yet_configured`)

---

## What Works (confirmed by audit)

| Surface | What works | Evidence |
|---------|------------|----------|
| `POST /api/generation/run` (calibration_cube) | trimesh generates real STL, truth gate passes, artifact DB row inserted, response matches `parseGeneratedModel()` — model card WILL appear in Generated Models if correctly triggered | gen3d audit |
| `POST /api/design/intake` (desk_organizer) | trimesh+manifold3d generates STL, truth gate, proof envelope, artifact DB row — STL visible in /api/artifacts immediately | design audit |
| `POST /api/slice` | background thread → PrusaSlicer → G-code in var/slicer/ → artifact DB row → `/api/artifacts/{id}/download` works — full chain wired | slicer audit |
| `GET /api/artifacts` | 42 records returned, real STLs and G-code accessible, download endpoint working | artifact audit |
| MiniMax PASS_LIVE | `POST /api/agents/providers/smoke` + `providers/assist` both return real completions | agent audit |
| DeepSeek PASS_LIVE | Same as above | agent audit |
| `design.intake` catalog action | Wired in agents.py to real executor — can be triggered by catalog action system | agent audit |
| `generation.run` catalog action | Wired in agents.py to generation route | agent audit |
| hermes_agent proof | Only INSTALLED_PROVEN app in registry (1/60) | 60-app audit |
| Artifacts tab | Renders real STL/G-code records from /api/artifacts; download works | artifact audit |

---

## Gap 1 — Gen3D: `parents[6]` Path Bug (all providers show unavailable)

**Severity: CRITICAL — blocks the entire providers panel**

**File:** `G:/Github/Hermes3D/03_implementation/src/hermes3d/api/routes/generation.py` lines 18–28

**Bug:** Both `_LANE04_PROOF_PATH` and `_SCHEMAS_DIR` use `parents[6]` which resolves to `G:\Github` (one level too high), producing non-existent paths. The correct index is `parents[5]` (= `G:\Github\Hermes3D`).

**Cascade:**
- `gen3d_providers()`: `lane04_providers` dict is always `{}` → all 5 providers fall through to `readiness: "unavailable"` regardless of install state. Bambu Studio IS installed at `C:\Program Files\Bambu Studio\bambu-studio.exe` but shows unavailable.
- `gen3d_templates()`: `schema_present` is always `False` for all 4 provider-backed templates despite schema files existing.
- The GUI "3D GENERATION PROVIDERS" panel shows "0 available" and every provider in grey.

**Fix:** Change `parents[6]` → `parents[5]` on both path constants. One-line change, two occurrences.

---

## Gap 2 — Gen3D: No Template Routing to Providers

**Severity: HIGH — even when providers are available, backend cannot dispatch to them**

**Files:**
- `generation.py`: `GenerationRun` model has no `template_id` field; `_resolve_generation_template` only handles "calibration cube" keywords; `_execute_generation_template` has no branch for ComfyUI/TRELLIS/Hunyuan3D
- `Gen3D.tsx` line 170: POST body never includes `selectedTemplate`

**Gap:** A user selecting `comfyui_text_to_3d` template and pressing Generate gets the same calibration_cube response (if prompt matches) or HTTP 409 "local 3D Generation executor currently supports calibration-cube requests only" (if prompt doesn't match).

**Fix:** Add `template_id: str | None = None` to `GenerationRun`; update `_resolve_generation_template` to prefer explicit `template_id`; add dispatch branches per provider.

---

## Gap 3 — Design Tab: Printer Gate Blocks Intake on Fresh DB

**Severity: CRITICAL — makes #design completely non-functional on fresh install**

**File:** `G:/Github/Hermes3D/03_implementation/ui/src/tabs/Design.tsx` line 141

**Bug:** `canSubmit` requires `targetPrinterId.length > 0`. On a fresh DB with no printers configured, `/api/printers` returns an empty list, `targetPrinterId` stays `""`, and the "Start Design" button is permanently disabled. The entire design → STL → slicer workflow is unreachable.

The backend itself does NOT require `target_printer_id` (it is optional in `design.py`). The gate is frontend-only.

**Fix (two options):**
1. Remove `targetPrinterId.length > 0` from `canSubmit` (make printer selection optional)
2. Seed a "software-only / no printer" dummy entry in the printers table on fresh DB init

---

## Gap 4 — Design/Modeler: OpenSCAD + Blender Not Detected (PATH issue)

**Severity: MEDIUM — probes report not_installed for tools that ARE installed**

**File:** `design.py` `_probe_cli_provider()` uses `shutil.which()` only

**Reality:**
- OpenSCAD: `C:\Program Files\OpenSCAD\openscad.exe` — version 2021.01, executable and working
- Blender: `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` — version 5.1.1, working

**Inconsistency:** `/api/design/backends` (`_blender_backend()` in `modeling_backend.py`) correctly finds Blender via a hardcoded fallback path list and shows it as `available`. But `/api/design/providers` (`_probe_cli_provider()` in `design.py`) shows Blender as `not_installed`. Same tool, two endpoints, two different answers.

**Fix:** Add Windows fallback path list to `_probe_cli_provider()` for both `openscad` and `blender`, matching the pattern already used in `_blender_backend()`.

---

## Gap 5 — Design/Modeler: CadQuery Blocked on Python 3.14

**Severity: MEDIUM — genuinely not installable without Python version change**

`cadquery-ocp` (OpenCASCADE bindings) has no pre-built wheel for Python 3.14. The source checkout at `G:\Github\Hermes3D-OS\source-lab\sources\modelers\CadQuery\` also depends on `cadquery-ocp` via pip and cannot bypass this. CadQuery is classified as `not_installed` correctly.

**Fix options:**
1. Create a Python 3.11 virtualenv alongside Python 3.14 and run a separate CadQuery worker
2. Wait for upstream `cadquery-ocp` to publish a Python 3.14 wheel

---

## Gap 6 — Design/Modeler: Only 1 Template, No OpenSCAD Executor

**Severity: MEDIUM — modeling is desk_organizer only**

- `_TEMPLATE_REGISTRY` in `design.py` has exactly 1 entry: `desk_organizer`
- No `.scad` templates exist in the repo (the source-lab checkout only has OpenSCAD's own test files)
- Blender adapter (`src/hermes3d/adapters/blender.py`) is a detection-only skeleton — no parametric modeling
- No Blender Python script for geometry generation exists beyond the GPU thumbnail renderer

**Fix:** Add an OpenSCAD executor module + `.scad` parametric template; register in `_TEMPLATE_REGISTRY`.

---

## Gap 7 — Artifact/File Store: `/api/files` Returns `file_store_not_yet_configured`

**Severity: MEDIUM — Files tab shows amber blocked banner**

**File:** `G:/Github/Hermes3D/03_implementation/src/hermes3d/api/routes/files.py`

`list_files()` always returns `{"accepted": false, "status": "unknown", "reason": "file_store_not_yet_configured"}`. This is an intentional stub. The Files tab detects this and shows a blocked banner, then falls back to `/api/artifacts` — which does work. So the data is accessible but through the wrong tab with a confusing amber banner.

**Fix:** Implement `list_files()` to scan `var/designs/` and `var/slicer/` and return real file entries. Change `accepted: false` → `accepted: true`.

---

## Gap 8 — Artifact/File Store: Orphan Files + Thumbnails Not Registered

**Severity: LOW-MEDIUM — some artifacts exist on disk but not in GUI**

**Orphan items not in artifacts DB:**
- 6 design job directories in `var/designs/` (each with real STL + proof.json + thumbnail)
- 1 slicer job directory in `var/slicer/575b010e...` (real G-code + proof.json)
- 1 generation job directory (calibration cube STL not registered)

**Thumbnails:** `thumbnail_gpu.png` exists in every `var/designs/` subdirectory but is never inserted into the artifacts table.

**Fix:** (1) Add a startup reconciler that scans var/designs/ and var/slicer/ for orphan dirs and inserts missing DB rows. (2) In `_execute_supported_design()`, insert a thumbnail artifact row after the GPU render.

---

## Gap 9 — 60-App Registry: Honest Status Not Shown

**Severity: MEDIUM — GUI implies all installed apps are working**

| Classification | Count |
|---|---|
| INSTALLED_PROVEN | 1 (hermes_agent only) |
| INSTALLED_UNPROVEN (proof_ran=FAIL) | 2 (langchain, cadquery) |
| INSTALLED_UNPROVEN (proof_never_run) | 15 |
| NOT_INSTALLED (source only) | 4 |
| NO_PROOF_COMMAND | 38 |

- The `health` field is permanently `"unknown"` for all 60 apps — never updated by runtime probing
- `install_state=installed` is set by a git-dir filesystem check, not by running the software
- The Run Proof button is never disabled for apps with `proof_command=null`
- 28 apps claim `installed + rollback_supported=True` but have zero proof capability

**Fixes:**
1. Add a `truthful_status` derived field to API response (INSTALLED_PROVEN / INSTALLED_UNPROVEN / NOT_INSTALLED / NO_PROOF_COMMAND / CONFIG_REQUIRED)
2. Add proof commands for verifiable CLI tools (FreeCAD, meshlab, OrcaSlicer, PrusaSlicer)
3. Disable Run Proof button when `proof_command=null`
4. Run all proofs once on server start to establish a baseline

---

## Gap 10 — Agent Workflow: MiniMax/DeepSeek Cannot Create a Model

**Severity: HIGH — agent-assisted 3D workflow does not exist yet**

The two halves exist but are not connected:
- `POST /api/agents/providers/assist` → gets MiniMax text reply → stores in DB → returns to caller → **nothing downstream**
- `design.intake` catalog action → calls real executor → produces real STL → **but has no input from MiniMax**

**Missing bridge:** No endpoint, no catalog action, and no GUI surface for "ask MiniMax to suggest model parameters → parse reply → run design.intake → show resulting artifact."

The `#agents` tab is a monitoring/code-patching workbench. There is no "Agent-Assisted Design" UI panel.

**Fix (4 parts per agent audit):**
1. New `POST /api/agents/providers/model-assist` endpoint — calls MiniMax with structured JSON prompt, parses reply for OrganizerSpec parameters, calls `design_route.submit_intake()`, returns job_id + artifact_id
2. MiniMax system prompt for parameter extraction (JSON output format)
3. New `design.agent_assisted_intake` catalog action with DeepSeek review pass before intake
4. New "Agent-Assisted Design" panel in `Agents.tsx`

---

## Fix PR Order

### PR W19-1: One-line path bug fix in generation.py
**File:** `generation.py` lines 18–28  
**Change:** `parents[6]` → `parents[5]` (two occurrences)  
**Effect:** All gen3d providers show correct readiness; Bambu Studio shows `installed_not_running`; template schema_present fields correct  
**Effort:** 5 minutes

### PR W19-2: Remove printer gate from Design tab intake
**File:** `Design.tsx` line 141  
**Change:** Remove `targetPrinterId.length > 0` from `canSubmit` OR seed a dummy software-only printer  
**Effect:** "Start Design" button becomes clickable on fresh DB; entire design → STL → slicer chain becomes reachable  
**Effort:** 30 minutes

### PR W19-3: Fix PATH detection for OpenSCAD + Blender in providers probe
**File:** `design.py` `_probe_cli_provider()`  
**Change:** Add Windows fallback path list for openscad and blender, matching `_blender_backend()` pattern  
**Effect:** Providers panel shows OpenSCAD and Blender as `ready` instead of `not_installed`  
**Effort:** 1 hour

### PR W19-4: Implement `/api/files` with var/ scanner
**File:** `files.py`  
**Change:** Replace stub with real scanner of `var/designs/` and `var/slicer/`  
**Effect:** Files tab amber banner disappears; tab shows real STL/G-code files  
**Effort:** 2 hours

### PR W19-5: Register thumbnails + add startup orphan reconciler
**File:** `design.py` `_execute_supported_design()`, new startup hook  
**Change:** Insert thumbnail_gpu.png into artifacts table on generation; reconcile orphan dirs on startup  
**Effect:** Artifacts tab shows thumbnails; 7 orphan items become accessible  
**Effort:** 2 hours

### PR W19-6: Wire template_id through generation POST
**Files:** `generation.py` (add `template_id` to `GenerationRun`), `Gen3D.tsx` (include `selectedTemplate` in POST body)  
**Effect:** Template selection in the UI is honored by the backend  
**Effort:** 2 hours

### PR W19-7: 60-App honest status — `truthful_status` field + proof_commands
**Files:** `apps.py` (add derived field), `app_registry_extensions.py` (add proof_commands), `AppStatusPanel.tsx` (disable button)  
**Effect:** GUI shows honest classification; Run Proof button gated on capability  
**Effort:** 4 hours

### PR W19-8: Agent-assisted design endpoint + GUI panel
**Files:** `agents.py` (new endpoint + catalog action), `Agents.tsx` (new panel)  
**Effect:** User can ask MiniMax to generate model parameters; STL produced; visible in Artifacts  
**Effort:** 8 hours

### PR W19-9: Additional gen3d local_executor templates
**File:** `generation.py`  
**Change:** Add cylinder, sphere, torus as `local_executor` templates (trimesh.creation)  
**Effect:** Gen3D tab has multiple working templates without any provider  
**Effort:** 2 hours

### PR W19-10 (deferred): OpenSCAD parametric template
**Files:** new `openscad_executor.py` + `.scad` template file, `design.py` `_TEMPLATE_REGISTRY`  
**Effect:** Design tab has second template using OpenSCAD CLI  
**Effort:** 4 hours

---

## No-Skip Product Definition of Done

The product is complete when a user can perform this workflow entirely within the GUI, no CLI, no printer hardware:

```
1. Open #gen3d
   → Select "Calibration Cube" template
   → Click Generate
   → Model card appears in "Generated Models" with STL size and proof event
   → STL is downloadable

2. Open #design
   → Select "Desk Organizer" template
   → Fill parameters (no printer selection required)
   → Click Start Design
   → STL appears in "Produced STLs"
   → Click "Slice this STL"
   → G-code artifact appears with layer count + size
   → "Download G-code" link works

3. Open #artifacts
   → Both the STL and G-code from steps 1–2 appear in the list
   → Each has a working download link

4. Open #agents
   → Type a model description
   → Click "Ask MiniMax"
   → MiniMax returns parameters
   → Click "Create"
   → Resulting STL appears in artifacts with job_id + proof

5. Open #apps
   → hermes_agent shows PROVEN (green)
   → Apps with no proof command show NO_PROOF_COMMAND (amber)
   → Apps that failed proof show FAIL (red)
   → No app falsely claims proven status
```

No printer hardware. No mocks. No skips.

---

## Summary Table

| Gap | Severity | PR | Effort |
|-----|----------|----|--------|
| generation.py parents[6] bug → all providers unavailable | CRITICAL | W19-1 | 5 min |
| Design tab printer gate → intake permanently disabled | CRITICAL | W19-2 | 30 min |
| OpenSCAD/Blender PATH detection wrong | MEDIUM | W19-3 | 1 hr |
| /api/files stub → Files tab blocked banner | MEDIUM | W19-4 | 2 hr |
| Thumbnails unregistered, 7 orphan dirs invisible | LOW | W19-5 | 2 hr |
| template_id not routed through generation POST | HIGH | W19-6 | 2 hr |
| 60-app honest status (1/60 proven, 38 no proof cmd) | MEDIUM | W19-7 | 4 hr |
| No agent → model creation bridge | HIGH | W19-8 | 8 hr |
| Only 1 local gen3d template | LOW | W19-9 | 2 hr |
| OpenSCAD executor template | LOW | W19-10 | 4 hr |
