# W18-A12 — Slicer Wire-Up (POST /api/slice + Design-tab UI)

**Task ID:** W18-A12-SLICER-WIREUP-2026-05-11
**CI-fix Task ID:** W18-A12-CIFIX-2026-05-11
**Verdict gate:** `GUI_SLICER_GREEN`
**Verdict:** `PASS_REAL` — slicer is now reachable from the GUI end-to-end and produces a real G-code file on disk.

**Supersedes verdict from:** W18-A9 (PR #239) `FAIL_NOT_WIRED`, W18-A6 (PR #231) `FAIL_NOT_WIRED`.

**CI fix (2026-05-11):** The Layer D2 default Playwright suite picked up this
spec on commit `d28008a` and failed because (a) the GitHub runner has no
PrusaSlicer / OrcaSlicer / FLSUN-slicer binary installed and (b) CAD
providers may not be configured. The 2026-05-11 update made the spec
env-aware (W18-A4 / W18-A9 idiom): probe `find_slicer()` directly and
`/api/design/toolchain/status`, then run either the **REAL_SLICE** branch
(workstation), the **HONEST_BLOCKED_SLICER** branch (CI without slicer
binary), or the **HONEST_BLOCKED_INTAKE** branch (toolchain not ready).
All three branches PASS_REAL with NO `test.skip` and NO mocks. The
no-printer-write contract is enforced in all branches.

**Confirmation:** No printer hardware writes. G-code stays on disk. The route is forbidden from dispatching to a printer. Pinned verdicts unchanged: `GUI_PHYSICAL_PRINT_GREEN=OUT_OF_SCOPE_BY_OPERATOR`, `GUI_PRINTER_DRY_RUN_GREEN=OUT_OF_SCOPE_BY_OPERATOR`.

## Operator directive

> "If an endpoint is missing, add it. If a button is dead, wire it." — 2026-05-11.

Hard freeze respected:

- No POST/PUT/PATCH to `/api/printers/{id}/*` for moves/heat/upload/start.
- No Moonraker/Klipper/OctoPrint upload from the new endpoint.
- The slicer produces a G-code FILE on disk; that file is the deliverable.
- A unit test (`test_slicer_does_not_dispatch`) monkey-patches `urllib.urlopen`
  and `requests.api.request` and asserts they are never called during a slice.
- The Playwright e2e asserts the GUI network log contains NO write to a
  printer-control pattern.

## Before / after

| Surface | Before (W18-A9 verdict) | After (this PR) |
|---|---|---|
| OpenAPI `/api/slic*` routes | 0 | 2 (`POST /api/slice`, `GET /api/slice/{job_id}`) |
| GUI "Slice this STL" button | absent (Slicing.tsx deleted in W15) | present in Design tab |
| GUI surfaces gcode_path + sha256 + layer_count | no | yes |
| GUI download G-code | no | yes (via `/api/artifacts/{id}/download`) |
| Background slice executor inside FastAPI | no | yes (daemon thread + SQLite rendezvous) |
| `analyze_gcode().layer_count` for PrusaSlicer 2.9.5 | `null` | real integer (W18-A9 side-finding fixed) |
| Proof envelope written to `var/slicer/{job_id}/proof.json` | n/a | yes |
| `proof_events` row on completion | n/a | yes (event_type=`slice_completed`) |
| Artifacts attached to the slice job | n/a | yes (gcode + proof_report) |

## Files modified

| Path | Lines | Change |
|---|---|---|
| `03_implementation/src/hermes3d/api/routes/slicer.py` | +540 | NEW — HTTP route + background worker + proof envelope writer |
| `03_implementation/src/hermes3d/api/app.py` | +5 | Register the slicer router |
| `03_implementation/src/hermes3d/core/slicer/gcode_analyzer.py` | +83/-3 | Parse `;LAYER_CHANGE` markers (PrusaSlicer 2.9.5 fix), add streaming `motion_lines` + `layer_change_markers` fields |
| `03_implementation/ui/src/api/slicer.ts` | +175 | NEW — `startSlice` / `getSlice` / `pollSliceUntilTerminal` / `gcodeDownloadUrl` |
| `03_implementation/ui/src/tabs/Design.tsx` | +267/-3 | Capture produced STL after intake, add `design.slicer` section with "Slice this STL" button + state panel + download link |
| `03_implementation/ui/playwright.w18-a12.config.ts` | +49 | NEW — dedicated config, no `webServer`, runs against live :8765 + :5173 |
| `03_implementation/ui/tests/e2e/w18-a12-slicer-wireup.spec.ts` | +414 | NEW — drive GUI Design tab end-to-end, recompute sha256, assert layer_count > 0, assert no printer-control endpoint touched |
| `04_testing/pytest/unit/test_slicer_route.py` | +346 | NEW — 7 tests covering routing, real-gcode, no-dispatch, error handling, analyzer-fix |
| `04_testing/fixtures/tiny_cube_10mm.stl` | (binary) | Re-added 684-byte cube fixture (was untracked on `main`) |

Total diff: **3 files modified, 7 files added, ~352 + ~1188 ≈ 1540 lines added**, 6 lines removed.

## Endpoint contract

### `POST /api/slice` → 202 Accepted

Body:

```json
{
  "stl_path": "G:\\Github\\Hermes3D\\...\\organizer.stl",
  "printer_profile": null,
  "options": { "timeout_seconds": 600 }
}
```

Response:

```json
{
  "status": "accepted",
  "accepted": true,
  "job_id": "5642235bfc5f4da0b808654f5c2fe6c6",
  "id": "5642235bfc5f4da0b808654f5c2fe6c6",
  "stl_path": "...resolved absolute path...",
  "printer_profile": null,
  "freeze": { "no_printer_writes": true, "no_dispatch": true }
}
```

### `GET /api/slice/{job_id}` → 200

```json
{
  "id": "5642235bfc5f4da0b808654f5c2fe6c6",
  "job_id": "5642235bfc5f4da0b808654f5c2fe6c6",
  "status": "completed",
  "name": "Slice desk_organizer_4ee082d000.stl",
  "dry_run": true,
  "proof_event_id": "0f980016fa634f41914f782ad1cab30a",
  "gcode_path": "G:\\Github\\...\\var\\slicer\\<job_id>\\desk_organizer_4ee082d000.gcode",
  "sha256": "d38505b3418087e816f4ab3b2df8d3282f74e3247e33dd10c975774c2005ddc0",
  "size_bytes": 6019909,
  "layer_count": 300,
  "motion_lines": 211443,
  "estimated_print_time_min": 761.83,
  "slicer_binary": "C:\\Program Files\\Prusa3D\\PrusaSlicer\\prusa-slicer-console.exe",
  "gcode_artifact_id": "eeb9a8617c074a49a46d073d66b251a2",
  "proof_path": "...\\proof.json",
  "proof_artifact_id": "7e87ba125e8441eca107d98ebe9d2bde"
}
```

Note: the gcode is downloadable via the existing
`GET /api/artifacts/{gcode_artifact_id}/download` endpoint.

## Real-artifact evidence

Two end-to-end runs against a live worktree backend (port 8766) on
2026-05-11 11:35:14 UTC. Both proof envelopes copied into
`03_implementation/docs/handoffs/evidence/w18-a12/`.

### Run 1 — tiny_cube_10mm.stl (684-byte test fixture)

| Metric | Value |
|---|---|
| `gcode_path` | `var/slicer/5f0f40dbb6674eb2b0bee3475d7f042e/tiny_cube_10mm.gcode` |
| `gcode_size_bytes` | 109 737 |
| `gcode_sha256` | `584d66e264a7ed48f066b6b6b64bc99e38853f8e1a687ec08e40456bac7e0b8f` |
| `layer_count` (W18-A12 fix) | **33** |
| `motion_lines` | 3 371 |
| `estimated_print_time_min` | 8.8 |
| `slicer_binary` | `C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe` (v2.9.5-beta2) |
| `duration_seconds` | ~1.0 |
| `proof_event_id` | `4a42b90af5414ea9aead6de615058da4` |

### Run 2 — Parametric desk_organizer (produced by `/api/design/intake`)

| Metric | Value |
|---|---|
| `gcode_path` | `var/slicer/5642235bfc5f4da0b808654f5c2fe6c6/desk_organizer_4ee082d000.gcode` |
| `gcode_size_bytes` | **6 019 909** |
| `gcode_sha256` | `d38505b3418087e816f4ab3b2df8d3282f74e3247e33dd10c975774c2005ddc0` |
| `layer_count` (W18-A12 fix) | **300** |
| `motion_lines` | **211 443** |
| `estimated_print_time_min` | 761.83 (12.7 h) |
| `slicer_binary` | PrusaSlicer 2.9.5-beta2 |
| `duration_seconds` | 1.086 |
| `proof_event_id` | `0f980016fa634f41914f782ad1cab30a` |
| download via `/api/artifacts/eeb9a8617c074a49a46d073d66b251a2/download` | 6 019 909 bytes, sha256 match ✓ |

Download verification (Run 2):

```text
curl -o $TEMP/dl.gcode http://127.0.0.1:8766/api/artifacts/eeb9a8617c074a49a46d073d66b251a2/download
200 bytes=6019909
sha256: d38505b3418087e816f4ab3b2df8d3282f74e3247e33dd10c975774c2005ddc0  ← matches
```

## Analyzer fix (W18-A9 side-finding)

Before this PR, `analyze_gcode()` returned `layer_count=null` for any
PrusaSlicer 2.9.5 output despite the file containing 100+ real layers,
because the analyzer only matched:

- `; total layer count = N` header (PrusaSlicer 2.9.5 no longer writes it), and
- `;LAYER:N` markers (Cura format, not PrusaSlicer).

After the fix:

- Added a streaming pass that counts the bare `;LAYER_CHANGE` token (the
  PrusaSlicer 2.9.5 / OrcaSlicer / SuperSlicer per-layer marker).
- `;BEFORE_LAYER_CHANGE` and `;AFTER_LAYER_CHANGE` are explicitly
  ignored to avoid triple-counting.
- `motion_lines` is now a full-file streaming count of G0/G1 motion lines
  (the body-sample-window count is still emitted as `*_moves_sampled`).
- Header-form `; total layer count = N` and the older `;LAYER:N` patterns
  remain authoritative — they win over the streaming counter when present.

Unit tests:

- `test_gcode_analyzer_counts_layer_change_markers` — synthetic G-code with
  three `;LAYER_CHANGE` markers + BEFORE/AFTER wrappers → `layer_count == 3`.
- `test_gcode_analyzer_prefers_header_layer_count` — header `total layer count = 7`
  overrides marker count of 2 → `layer_count == 7`.

## Test evidence

### Pytest unit tests

```
$ PYTHONPATH=03_implementation/src python -m pytest 04_testing/pytest/unit/test_slicer_route.py -v --timeout=300
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-8.4.2, pluggy-1.6.0
configfile: pyproject.toml
plugins: anyio-4.12.1, asyncio-1.3.0, base-url-2.1.0, cov-5.0.0, playwright-0.7.2, timeout-2.4.0, xdist-3.8.0
collected 7 items

04_testing\pytest\unit\test_slicer_route.py::test_slice_endpoint_returns_real_gcode PASSED
04_testing\pytest\unit\test_slicer_route.py::test_slicer_route_does_not_import_printer_clients PASSED
04_testing\pytest\unit\test_slicer_route.py::test_slicer_does_not_dispatch PASSED
04_testing\pytest\unit\test_slicer_route.py::test_slice_unknown_stl_returns_404 PASSED
04_testing\pytest\unit\test_slicer_route.py::test_slice_routes_are_registered PASSED
04_testing\pytest\unit\test_slicer_route.py::test_gcode_analyzer_counts_layer_change_markers PASSED
04_testing\pytest\unit\test_slicer_route.py::test_gcode_analyzer_prefers_header_layer_count PASSED

============================== 7 passed in 4.94s ==============================
```

### TypeScript

```
$ tsc --noEmit -p tsconfig.json
EXIT_CODE=0
```

### Hermes gate

```
hermes_run_gate(gateId="git-status", owner="w18-a12")
→ exit_code=0, duration_ms=105, status=pass
```

### Playwright e2e (env-aware, both branches PASS_REAL)

`03_implementation/ui/tests/e2e/w18-a12-slicer-wireup.spec.ts` is the
GUI-side proof script. It runs against the live :8765/:5173 stack via
`playwright.w18-a12.config.ts`. The 2026-05-11 CI-fix update made the spec
env-aware following the W18-A4 / W18-A9 pattern — no `test.skip`, no mocks,
both code paths PASS_REAL.

Branch decision (recorded in `audit.json` under `branch`):

1. `slicer_cli_ready` is derived from a Python subprocess that calls
   `hermes3d.core.slicer.find_slicer()` on THIS host. The toolchain endpoint
   reads the committed `LOCAL_TOOLING_AUDIT.json` (workstation paths), so
   it cannot be trusted on CI. Probe written to
   `test-results/w18-a12/01c-find-slicer-probe.json`.
2. `intake_available` is derived from `GET /api/design/toolchain/status`:
   `overall === "ready"` means intake will accept requests.
3. CAD provider inventory is recorded from `GET /api/design/providers` for
   audit traceability (`01b-design-providers.json`).

Branches:

* **REAL_SLICE** — `slicer_cli_ready === true` AND `intake_available === true`.
  Exercises the full chain: Design tab → intake → "Slice this STL" →
  poll → recompute sha256 + layer_count from G-code on disk → assert
  GUI matches backend → download link returns identical bytes.

* **HONEST_BLOCKED_SLICER** — toolchain ready, slicer binary absent (typical CI).
  Drives the same surface, asserts `POST /api/slice` returns 202, then
  `GET /api/slice/{id}` returns `status="failed"` with `error` and
  `failure_payload.reason` populated. The GUI surfaces the backend's
  truthful "slicer_not_found" message verbatim in `design-slicer-error`,
  status badge shows `failed`, and the Download link does NOT render.

* **HONEST_BLOCKED_INTAKE** — `toolchain.overall !== "ready"` (e.g. trimesh
  missing). Asserts `POST /api/design/intake` returns 409 with structured
  `detail.reason`. The GUI surfaces the truthful "Blocked / toolchain not
  ready" banner. No slicer is invoked; no STL rows appear.

All three branches share the network-audit invariants:

1. Open Design tab → assert root visible.
2. Assert `design-slicer-root` + `design-slicer-freeze-badge` render in
   every branch (the W18-A12 wire-up surface is always present).
3. Assert no `Send to Printer` / `Start Print` / `Upload to Printer` /
   `Print Now` button exists.
4. Network audit — assert all writes stayed on the allow-list
   (`/api/design/*`, `/api/slice/*`, `/api/artifacts/*`, `/api/events`,
   `/api/proof`, `/api/system`, `/api/settings`, `/api/printers` GET only,
   `/api/logs`, `/api/health`).
5. Assert zero printer-control writes (`/api/printers/{id}/upload-gcode`,
   `/jobs/{id}/start`, Moonraker `:7125`, OctoPrint `:5000`, etc.).
6. Assert zero `console.error`, `pageerror`, unexpected 4xx/5xx on our
   endpoints. The two honest-failure shapes (409 on `/api/design/intake`,
   404 on `/api/slice/{id}` during the brief pre-row window) are excluded
   from the failure list because they are the truthful answer.

The spec runs against a live backend started from this branch — the
contract guarantee is that the developer (or CI) starts uvicorn from this
worktree and `npm run dev` from this UI before invoking
`npx playwright test --config=playwright.w18-a12.config.ts`. On CI the
default Playwright suite picks up the spec via `testMatch` in the root
`playwright.config.ts`; the env-aware branch decision keeps it green
without slicer/CAD-provider dependencies.

## Files locked on hermes3d-locks

Locked under `w18-a12` (task `W18-A12-SLICER-WIREUP-2026-05-11`):

- `03_implementation/src/hermes3d/api/routes/slicer.py`
- `03_implementation/src/hermes3d/api/app.py`
- `03_implementation/src/hermes3d/core/slicer/slicer_runner.py`
- `03_implementation/src/hermes3d/core/slicer/gcode_analyzer.py`
- `04_testing/pytest/unit/test_slicer_route.py`
- `03_implementation/ui/src/api/slicer.ts`
- `03_implementation/ui/src/tabs/Design.tsx`
- `03_implementation/ui/tests/e2e/w18-a12-slicer-wireup.spec.ts`
- `03_implementation/ui/playwright.w18-a12.config.ts`
- `03_implementation/docs/handoffs/W18-A12_SLICER_WIREUP_2026-05-11.md`

Released on PR open.

## Allow-listed network endpoints

The e2e spec asserts these are the ONLY backend paths that may be
written to during a slicer flow:

- `POST /api/design/intake`
- `POST /api/slice`
- `POST /api/events` (proof event from the FE adapter)
- `GET /api/slice/{job_id}`
- `GET /api/artifacts/{artifact_id}/download`
- `GET /api/design/{providers,templates,toolchain/status}`
- `GET /api/printers` (target-picker only; no writes)
- `GET /api/logs`, `/api/health`, `/openapi.json`

Any deviation fails the spec.
