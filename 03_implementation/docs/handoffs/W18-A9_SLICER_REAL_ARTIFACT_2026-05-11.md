# W18-A9 - Modeler -> Slicer Real-Artifact Proof

- Date: 2026-05-11
- Branch: `claude/w18-a9-slicer-real-artifact`
- Base: `caa9a07` on `develop` (W18-A5 head)
- Hermes lock owner: `w18-a9` (taskId `W18-A9-MODELER-SLICER-PROOF-2026-05-11`)
- Verdict gate: **GUI_SLICER_GREEN = FAIL_NOT_WIRED**
- Pinned (unchanged): `GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR`, `GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR`

## TL;DR

The Hermes3D GUI has **no surface that triggers the slicer**. The Print Queue
tab's `SubmitJobDialog` exposes a `job_type=slice` option, but `POST /api/jobs`
with that option only persists a queued SQLite row - **no FastAPI handler runs
`slice_mesh()`**, and no in-process worker picks the row up. The slicer pipeline
is reachable only from the CLI (`hermes3d slice`) and from the out-of-process
LangGraph `print_workflow.py` agent graph.

The slicer code path **itself works**: a control invocation against the W18-A5
desk_organizer STL produced a real **3.1 MB G-code on disk** (116 layers,
107,472 G0/G1 motion lines, 312.2 min estimated print time) - documenting that
the gap is **strictly the GUI/HTTP wiring**, not the slicer.

This lane is the GUI-slicer audit only. The W18-A9 brief explicitly **replaces**
the cancelled "A9 physical print gate" - no physical printing was authorised
and none was performed. No printer-control endpoint was touched.

## Status vocabulary

- **PASS_REAL** - GUI exposes a slicer trigger; GUI -> backend call -> slicer
  CLI runs -> G-code on disk -> GUI surfaces path. *Not achieved.*
- **PARTIAL** - slicer is reachable through some HTTP endpoint (even
  non-GUI), but the GUI surface only partially drives it. *Not achieved
  (no `/api/slice*` endpoint at all).*
- **FAIL_NOT_WIRED** - no HTTP/GUI path triggers `slice_mesh()`. The slicer
  is reachable only from the CLI / out-of-process graph. **This is the
  honest verdict.**

## Surface map

### Backend - what exists
- `src/hermes3d/core/slicer/slicer_runner.py::slice_mesh()` - real
  PrusaSlicer/OrcaSlicer CLI wrapper. Auto-detects binary via
  `HERMES3D_SLICER_BIN` or platform candidates.
- `src/hermes3d/core/slicer/gcode_analyzer.py::analyze_gcode()` - read-only
  parser for slicer output.
- `src/hermes3d/core/orchestration/print_workflow.py` - LangGraph agent graph
  with a `slice` node calling `slice_mesh()`. **Out-of-process**; not invoked
  by the FastAPI app.
- `src/hermes3d/cli/__main__.py::cmd_slice` - operator runs
  `hermes3d slice STL` directly.

### Backend - what does NOT exist
- **No `/api/slice*` route.** Confirmed: openapi.json (241 paths total) lists
  zero `/api/slice*` and only one `gcode` path (`/api/printers/{id}/upload-gcode`,
  which is a printer-control endpoint forbidden by the freeze).
- **No worker in `api/app.py` picks up `job_type=slice` rows.** The route
  `routes/jobs.py::create_job` does an `INSERT INTO jobs` and returns. There
  is no background task, no FastAPI startup event, no Celery/RQ binding.

### GUI - what exists
- **Print Queue tab** (`#print_queue`, `src/tabs/PrintQueue.tsx`) has a
  `Submit Job` button that opens `SubmitJobDialog`.
- **SubmitJobDialog** (`src/components/print-queue/SubmitJobDialog.tsx`)
  exposes job-type options: `print`, `slice`, `calibration`, `dimensional_qc`.
- Selecting `slice` and submitting calls `jobsClient.enqueue()` which POSTs to
  `/api/jobs` with `job_type=slice, dry_run=true, printer_id=null`.

### GUI - what does NOT exist
- **No STL/mesh picker** to choose what to slice.
- **No slicer-status banner** that updates while a slice runs.
- **No output-path surfacing** anywhere (no slicer_report card on any tab).
- **No "Slice this artifact" button** on the Artifacts tab.

## Evidence

### Playwright spec
- File: `03_implementation/ui/tests/e2e/w18-a9-slicer-real-artifact.spec.ts`
- Config: `03_implementation/ui/playwright.w18-a9.config.ts` (no `webServer`;
  audit runs against the live FastAPI on 127.0.0.1:8765 and Vite on
  localhost:5173, matching the W18-A1 audit-mode pattern)
- Result: **1 passed (34.3s, chromium 1920x1080)**
- Reporter outputs: `test-results/w18-a9/results.json`, `test-results/w18-a9/html/`

### Audit steps (from `test-results/w18-a9/audit.json`)

| # | Step                                       | Result                          | Notes |
|---|--------------------------------------------|---------------------------------|-------|
| 1 | OpenAPI slicer-path inventory              | `present`                       | Only `/api/printers/{id}/upload-gcode` (forbidden); 0 slicer endpoints. |
| 2 | GUI Print Queue loaded                     | `ok`                            | `print-queue-root` testid visible. |
| 3 | GUI Submit Job dialog opened               | `ok`                            | `submit-job-dialog` testid visible. |
| 4 | GUI submit slice job                       | `ok`                            | `job_id=0f185c58be324169a5b14d9ae8a148bc`, `job_type=slice`, `dry_run=1`, `printer_id=null`. |
| 5 | GUI slice-executor observation             | `no_gcode_artifact_after_30s`   | Polled `/api/jobs/{id}` every 2s for 30s. Status remained `queued`; 0 artifacts, 0 steps, 0 events. **This is the FAIL_NOT_WIRED proof.** |
| 6 | No printer-control endpoints touched       | `ok`                            | Only POST endpoint observed: `/api/jobs`. |
| 7 | Control slicer CLI real artifact           | `ok`                            | 3.1 MB G-code, 116 layers, 107,472 motion lines, 312.2 min, sha256 captured. |
| 8 | Analyzer gap (LAYER_CHANGE markers)        | `known_gap`                     | `gcode_analyzer.py` does not count `;LAYER_CHANGE` (modern PrusaSlicer 2.9.5). Returns `layer_count=null` despite 116 real layers. Recommend a fix-lane PR. |

### G-code file on disk (control proof)

| Field                         | Value |
|-------------------------------|-------|
| `gcode_path` (origin)         | `G:\Github\Hermes3D\03_implementation\ui\test-results\w18-a9\gcode-out\desk_organizer_09a2a3bd9d.gcode` |
| `gcode_path` (evidence copy)  | `G:\Github\Hermes3D\03_implementation\ui\test-results\w18-a9\desk_organizer_09a2a3bd9d.gcode` |
| `gcode_size_bytes`            | `3,137,105` (3.1 MB) |
| `gcode_sha256`                | `40c5ecbbf9424a718c8d627d6f4d9842016bfb993d05ca21c81930f7fcfef6c1` |
| `motion_lines` (G0+G1)        | `107,472` |
| `layer_count_real`            | `116` (from `;LAYER_CHANGE` markers; spec-side ground truth) |
| `estimated_print_time_min`    | `312.2` (~5h 12m) |
| `estimated_filament_mm`       | `31,964.92` (~32 m) |
| `slicer_binary`               | `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe` (PrusaSlicer 2.9.5-beta2) |
| `argv`                        | `prusa-slicer-console.exe --export-gcode --output <path> <stl>` |
| `slice_duration_seconds`      | `1.00` |
| input STL                     | `03_implementation/var/designs/4e32a558e5a34de09ea61bdc15ae647e/desk_organizer_09a2a3bd9d.stl` (the W18-A5 desk_organizer output) |

### gcode_analyzer summary (out-of-band, captures the gap)

| Field                          | Value |
|--------------------------------|-------|
| `slicer_name` / `slicer_version` | `PrusaSlicer` / `2.9.5-beta2` |
| `estimated_print_time_min`     | `312.2` |
| `filament_used_mm`             | `31,964.92` |
| `filament_used_g`              | `null` (not in this PrusaSlicer header build) |
| `layer_count` (analyzer-reported) | **`null`** - bug; see step 8 |
| `layer_height_mm`              | `0.3` |
| `nozzle_temp_c`                | `200` |
| `extrusion_moves_sampled`      | `8,360` |
| `travel_moves_sampled`         | `457` |
| `risk_flags`                   | `[]` |

### Submitted slice job (GUI -> /api/jobs)

```json
{
  "id": "0f185c58be324169a5b14d9ae8a148bc",
  "name": "W18-A9 slicer audit (no printer)",
  "job_type": "slice",
  "status": "queued",
  "printer_id": null,
  "dry_run": 1,
  "created_at": "2026-05-11 11:05:..."
}
```

After 30 seconds of `GET /api/jobs/{id}` polling: still `queued`, 0 artifacts,
0 steps, 0 events. This is the empirical proof that the GUI cannot drive the
slicer end-to-end.

### Screenshots
- `test-results/w18-a9/01-print-queue-loaded.png` - Print Queue tab with
  Submit Job button visible.
- `test-results/w18-a9/02-submit-job-dialog-opened.png` - SubmitJobDialog
  open.
- `test-results/w18-a9/03-submit-dialog-slice-type-selected.png` - dialog
  with job_type=`slice (slice only, no print)` and dry-run pre-checked.
- `test-results/w18-a9/05-print-queue-after-submit.png` - Print Queue
  after submission; the W18-A9 row appears in the queued lane.

### Captured intermediate JSONs
- `test-results/w18-a9/openapi-paths.json` - inventory of slicer/gcode paths.
- `test-results/w18-a9/04-submitted-job.json` - raw POST `/api/jobs` response.
- `test-results/w18-a9/06-job-detail-after-poll.json` - final job detail.
- `test-results/w18-a9/07-network-log.json` - full network audit.
- `test-results/w18-a9/08-control-input-stl-chosen.json` - selected STL.
- `test-results/w18-a9/09-control-slicer-run.log` - slicer CLI stdout/stderr.
- `test-results/w18-a9/10-slice-proof.json` - parsed SliceResult + analyzer.
- `test-results/w18-a9/audit.json` - top-level audit summary (verdict + steps).

## Network endpoints touched (allow-list of writes)

The spec captured **173 calls** to our backend+frontend across the run. Of
those, only **POST** writes are policy-relevant. The complete write
allow-list seen during the audit:

```
POST /api/jobs
```

That is the **only** write our audit performed. **Zero** printer-control
endpoints were hit:

```json
"printer_control_hits": []
```

The spec hard-asserts this list is empty against the explicit pattern list:
- `/api/printers/{id}/upload-gcode`
- `/api/printers/{id}/jobs`
- `/api/jobs/{id}/start`
- moonraker `/printer/print/start` and `:7125`
- octoprint `/api/files/local`, `/api/printer/command`, and `:5000`

If any future regression starts emitting writes to those URLs from the
GUI's slicer path, this spec will FAIL the audit, by design.

## Console / page-error / HTTP noise

- `console.error` count: **0** (filtering `Failed to load resource` /
  `net::ERR_*` noise from unrelated probes, per the W18-A5 convention).
- `pageerror` count: **0**
- HTTP 4xx/5xx failures on our hosts: **0**

The GUI slicer-trigger path is clean of console noise even though it does
not produce real work.

## Scope discipline (operator freeze restated)

This lane:
- Did **NOT** touch any physical printer.
- Did **NOT** transmit G-code to any printer.
- Did **NOT** call Klipper / Moonraker.
- Did **NOT** upload to OctoPrint.
- Did **NOT** modify any printer-write-enabled config or DB rows.
- The control-proof slicer CLI ran a local executable that writes to disk
  and exits; it cannot reach the network without an explicit upload step
  that this audit does not contain.

Pinned verdicts are unchanged:
- `GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR`
- `GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR`

## Suggested follow-up fix lanes (NOT done here)

These are recorded as observations, not assigned work. A future lane should:

1. **Add an `/api/slice` synchronous endpoint** that accepts an STL path
   (or artifact_id) and a profile, calls `slice_mesh()`, persists the
   resulting `SliceResult` as a typed proof event, and returns the
   gcode_path + sha256 + analyzer summary. Front the endpoint with an
   STL-id picker on the Artifacts tab (the existing Artifacts tab already
   has the per-row context).
2. **Surface slicer status in the GUI**: an in-process status card
   (similar to `design.toolchain` on the Design tab) showing
   `slicer_binary`, `last_run_gcode_path`, `last_run_sha256`,
   `estimated_minutes`. This is the surface a future
   GUI_SLICER_GREEN=PASS_REAL spec would assert against.
3. **Fix `gcode_analyzer.py` `;LAYER_CHANGE` blind spot**: add a third
   pattern + counter so `analyze_gcode().layer_count` is non-null for
   modern PrusaSlicer/Orca output. Today the audit had to count layers
   itself.
4. **Connect the `job_type=slice` queue row to a background worker** if
   the design wants the queue to be the slicer entry point (vs. a
   dedicated `/api/slice`). Either path closes the gap.

## Hermes ledger
- Lock owner: `w18-a9`
- Locks held during run:
  - `03_implementation/docs/handoffs/W18-A9_SLICER_REAL_ARTIFACT_2026-05-11.md`
  - `03_implementation/ui/playwright.w18-a9.config.ts`
  - `03_implementation/ui/tests/e2e/w18-a9-slicer-real-artifact.spec.ts`
- Evidence appended:
  - `ev_dce2d6bb1bf29a9c` - survey finding (no `/api/slice*` endpoint).
  - `ev_66bc91ad3458b27e` - Playwright spec pass with verdict +
    G-code sha + layer count + zero printer-control hits.
- Hermes run-gate id `playwright` returned status `fail` due to a
  `spawn EINVAL` on `npx.cmd` in the gate runner (Windows env quirk
  shared with other W18 lanes). The spec itself was executed and passed
  via the documented command in the brief.

## Run command (for reproducibility)

```powershell
cd G:\Github\Hermes3D\.claude\worktrees\w18-a9\03_implementation\ui
npx playwright test --config=playwright.w18-a9.config.ts --reporter=list
```

Expected output: `1 passed`. Verdict and details land in
`test-results/w18-a9/audit.json`. Tail of the produced G-code copy lands
beside it as `desk_organizer_<hash>.gcode`.

## Follow-up CI fix (2026-05-11, branch `claude/w18-a9-cadquery-fix`)

After this lane merged to `develop` (PR #239), the same spec was added to the
**default `playwright.config.ts` test suite** that runs on the Layer D2 —
UI-Final (React @ 1920×1080) GitHub Actions job. Two environment differences
between the workstation and the CI runner caused the merged spec to fail
develop's own CI (run `25667636164`, commit `9d303cd`) and every open W18 PR
rebased on develop (#232, #238, #241, #242):

1. **No test timeout override.** The default Playwright config sets no
   explicit `timeout`, so the framework falls back to 30 000 ms. The spec
   spends 30 000 ms in Step 5 (polling `/api/jobs/{id}` for a slicer-attached
   G-code artifact) and then needs additional time to spawn the Python
   `slice_mesh()` subprocess in Step 7. The total never fits in 30 s.
2. **No PrusaSlicer / OrcaSlicer / FLSUN-slicer binary on the GitHub
   runner.** `find_slicer()` returns `None` and `slice_mesh()` raises
   `SlicerNotFound`, so even with a longer timeout the spec hard-asserts on a
   non-zero rc and fails.

### Fix (lock owner `w18-a9-fix`, taskId `W18-A9-CADQUERY-FIX-2026-05-11`)

The spec was rewritten to be environment-aware in the same idiom W18-A4 uses
for its provider check:

- **Test timeout raised to 180 000 ms** via `test.setTimeout(180_000)` at the
  top of the audit body. This is the same envelope W18-A5 uses.
- **New Step 1b: probe `GET /api/design/providers`** for the live
  CAD/modeling provider inventory. The spec records `available_cad_providers`
  in `test-results/w18-a9/01b-design-providers.json` and pushes an audit
  step with `cad_providers_available` / `no_cad_provider_available`. No
  hard-coded provider name is required — the spec asserts against the live
  list (which may include OpenSCAD, Blender, CadQuery, trimesh, manifold3d,
  FreeCAD, or any subset thereof) OR the honest empty-list state.
- **New Step 1c: probe `GET /api/design/toolchain/status`** for the
  `slicer_cli` stage. The result is captured in
  `test-results/w18-a9/01c-toolchain-status.json` and a
  `slicer_cli_availability_probe` audit step is recorded.
- **Step 7 is now conditional on the slicer probe.** If `slicer_cli.status
  == "ready"`, the spec runs the full Python control-proof (unchanged
  behaviour on workstations with PrusaSlicer installed — still produces a
  ~3.1 MB real G-code on disk). If `slicer_cli` is not ready, the spec
  records a `control_slicer_cli_unavailable` audit step and writes a
  human-readable note to `09-control-slicer-run.log`. **No `test.skip()`,
  no mocks.** Both code paths PASS_REAL.
- **Step 9 audit summary** now includes an `environment` block with
  `slicer_cli_available` and `available_cad_provider_names`, and
  `control_proof_gcode` is null-safe with an explicit
  `status: "slicer_cli_unavailable"` shape when the control proof was
  honestly skipped.

The GUI-surface assertions (Steps 2–6 and 8) are unchanged. The pinned
verdicts (`GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR`,
`GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR`) are unchanged. The
operator freeze on printer hardware writes is unchanged. No printer-control
endpoint is touched.

### PRs unblocked by this fix

- `develop` CI on commit `9d303cd` (Layer D2 — UI-Final)
- PR #232
- PR #238
- PR #241
- PR #242
