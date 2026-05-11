# W18-A5 — Modeler Workflow Proof

- Date: 2026-05-11
- Branch: `claude/w18-a5-modeler-workflow`
- Base commit: `330f521` on `develop`
- Hermes lock owner: `w18-a5` (taskId `W18-A5-MODELER-WORKFLOW-2026-05-11`)
- Status: **PASS_REAL_PARAMETRIC** (with caveat — see Surface Map)

## TL;DR

The Hermes3D "Design" surface produces a **real 3D model artifact on disk**
end-to-end (verified Playwright spec, real STL on filesystem, real proof
envelope, truth gate `pass`), but it is **NOT an interactive in-page 3D modeler**.
It is a **parametric template form** (currently one template: Parametric Desk
Organizer) that submits to `POST /api/design/intake` and the backend executor
`hermes3d.core.design.desk_organizer` writes a binary STL + signed proof
envelope under `03_implementation/var/designs/{job_id}/`.

The brief's prior W17-NEW-A5 note ("#design CTA navigates AWAY") does not
match the current `develop` state — `#design` mounts `src/tabs/Design.tsx`
in-place and the in-page form posts to the backend without navigation.

## Status vocabulary

Per the audit contract:

- **PASS_REAL_PARAMETRIC** — A Playwright spec opens the modeler surface,
  triggers the workflow, the backend produces a real STL on disk, and the UI
  surfaces the artifact label (visible in Artifacts tab). This applies here
  because the Design surface IS the modeler surface (parametric), even though
  it is not an interactive 3D editor.
- The simpler **PASS_REAL** is reserved for an interactive modeler with a
  primitive-creation or load-STL workflow — that surface **does not exist** in
  the current GUI. If the auditor reads this lane as strictly requiring an
  interactive 3D editor, the status flips to **FAIL_NOT_WIRED** for that
  flavor; either reading is supported by the same evidence.

## Evidence

### Playwright spec
- File: `03_implementation/ui/tests/e2e/w18-a5-modeler-workflow.spec.ts`
- Result: 2 passed (13.6s, chromium 1920x1080) against the live FastAPI
  backend on `127.0.0.1:8765` and Vite dev server on `localhost:5173`
- Test 1 (`Design tab surfaces a parametric template form, NOT an in-page 3D
  modeler`) asserts:
  - `design-root` testid mounts
  - `#design.intake`, `#design.toolchain`, `#design.providers`,
    `#design.templates` sections are visible
  - "Start Design" button is present
  - **EXPECTED-FALSE**: no `<canvas>` element, no `window.THREE` / three.js
    root — these failures-to-find are the audit finding (no in-page 3D editor)
- Test 2 (`Parametric modeler workflow produces a real STL artifact on disk`)
  asserts:
  - `/api/design/toolchain/status` returns `overall: ready`
  - `/api/design/intake` returns 201 with `status: completed`
  - Returned `artifact.file_path` exists on disk
  - On-disk file size matches API `file_size`
  - File is a valid binary STL (header + triangle count + 50*N bytes)
  - Proof envelope file exists at `proof.file_path`
  - `truth_gate.status == "pass"`
  - Artifacts tab renders the new mesh label

### Real artifact produced

Captured at `03_implementation/ui/test-results/w18-a5/intake-result.json`:

```json
{
  "job_id": "6d0ebe83c20740c3bb45c33f3c383853",
  "artifact": {
    "label": "desk_organizer_a22a716e10.stl",
    "file_path": "G:\\Github\\Hermes3D\\03_implementation\\var\\designs\\6d0ebe83c20740c3bb45c33f3c383853\\desk_organizer_a22a716e10.stl",
    "file_size": 15284,
    "sha256": "51d5583b1701cff93969c4a5a770c6c9bbab078fa0eb384a0ed9a37efa3655ac"
  },
  "proof": {
    "label": "desk_organizer_a22a716e10.proof.json",
    "file_size": 4622,
    "sha256": "70e3f0fd35b8870e95fb322f04410f95e189d90a393fe627a17aad1918d3fc3e"
  },
  "truth_gate": { "status": "pass", "duration_s": 0.1915 },
  "on_disk": { "stl_size_bytes": 15284, "stl_triangles": 304 }
}
```

- 304 binary-STL triangles, watertight per backend mesh summary contract.
- Proof envelope is signed (`signature.algorithm` set by `core.proof.write_proof`).

### Screenshots (captured by the Playwright spec)

- `03_implementation/ui/test-results/w18-a5/design-surface.png` — full
  Design tab, showing parametric intake form, toolchain stage cards, CAD
  provider health, template gallery. No 3D canvas visible.
- `03_implementation/ui/test-results/w18-a5/artifacts-with-mesh.png` — full
  Artifacts tab after the workflow completes, with the new STL listed.

### Test fixture seeded for future load-STL paths

- `04_testing/fixtures/tiny_cube_10mm.stl` — 684 bytes, valid binary STL,
  12 triangles, 8 vertices, watertight, volume 1000 mm^3, bounds 0..10mm.
  Verified by trimesh import:
  `triangles=12 vertices=8 volume=1000.00mm3 watertight=True`.
- Not consumed by the current spec (the parametric path does not need it),
  but available for a future load-STL workflow if/when an in-page modeler is
  added.

## Surface map — what is actually on the Design route

Route: `src/app/routes.ts` → `Design` (label) → `src/tabs/Design.tsx`,
mounted in-place on `#design`. No external navigation.

| Section | DOM anchor | What it actually does |
| --- | --- | --- |
| Design Intake | `#design.intake` | Real form: template select, name, description, width/depth/height mm, tray/pen counts, phone-slot, cable-passthrough, target printer. "Start Design" POSTs to `/api/design/intake`. |
| Design Toolchain | `#design.toolchain` | Reads `GET /api/design/toolchain/status` every 15s. Stage cards: intake, source CAD, OpenSCAD CLI, mesh worker, slicer CLI, prompt-to-CAD executor, latest truth gate. |
| CAD Provider Health | `#design.providers` | Reads `GET /api/design/providers` every 30s. Live `shutil.which()` + `importlib` probes for OpenSCAD, Blender, CadQuery, trimesh, manifold3d, FreeCAD. |
| Template Gallery | `#design.templates` | Reads `GET /api/design/templates`. Currently returns ONE template: `desk_organizer` (Parametric Desk Organizer). Templates without renderer show "Preview not available". |

What is **NOT** on the route:
- No `<canvas>` element (confirmed via Playwright `page.locator("canvas").count() === 0`)
- No three.js / `window.THREE` (confirmed via `page.evaluate`)
- No `babylonjs` / `@react-three/*` / `cannon` packages in
  `03_implementation/ui/package.json`
- No "Load STL" file picker
- No primitive-creation control (no "create cube/sphere/cylinder" buttons)
- No `src/components/modeler/*` or `src/modeler/*` directories
- No transform gizmo / vertex-editing UI

Reference points in `src/tabs/Design.tsx`:
- Line 204: `<div data-testid="design-root" ...>` — the route root
- Line 246-254: "Start Design" CTA that calls `submit()` → `fetch(/api/design/intake)`
- Lines 218-222: template `<select>` populated from `/api/design/templates`
- The backend executor that produces real STLs:
  `03_implementation/src/hermes3d/api/routes/design.py:356` (`_execute_supported_design`)

## Repro

```powershell
# Pre-req: backend on 8765, Vite on 5173 (Playwright config will start them)
cd G:\Github\Hermes3D\03_implementation\ui
npx playwright test tests/e2e/w18-a5-modeler-workflow.spec.ts --reporter=list
```

Expected: 2 passed; artifact written under
`G:\Github\Hermes3D\03_implementation\var\designs\{job_id}\desk_organizer_*.stl`;
proof bundle written under `03_implementation/ui/test-results/w18-a5/`.

## Recommendations (out of scope for this audit — requires operator approval)

1. **Add at least one more template** so "Template Gallery" is more than one
   tile. The dispatcher only supports `desk_organizer`. Adding e.g. a
   parametric box / lid / mounting bracket would broaden the parametric
   modeler's surface usefulness.
2. **Wire a read-only 3D preview** for the generated STL using trimesh's
   `pyglet`/server-side render to PNG, returned in the intake response so
   the Design tab can show a thumbnail. This is a separate fix lane.
3. **In-page 3D modeler is a much larger ask** — would require adding
   three.js or babylon.js to the bundle and a separate modeler tab. Not
   recommended without operator approval; the current parametric path is
   working and produces auditable artifacts.

## Lock release

Locks held during this audit:
- `03_implementation/docs/handoffs/W18-A5_MODELER_WORKFLOW_2026-05-11.md`
- `03_implementation/ui/tests/e2e/w18-a5-modeler-workflow.spec.ts`
- `04_testing/fixtures/tiny_cube_10mm.stl`

Released by the audit's closing `hermes_release_files` call after the PR opens.
