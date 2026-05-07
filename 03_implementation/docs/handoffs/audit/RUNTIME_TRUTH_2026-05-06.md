# Runtime Truth Audit
**Agent**: claude-polish-runtime-03
**Task ID**: H3D-CLAUDE-POLISH-SOURCE-RUNTIME-2026-05-06
**Date**: 2026-05-06
**Hermes evidence chain: PASS**

---

## Proof File Verification

| File | Real? | Honest not_found entries? | Issues |
|------|-------|--------------------------|--------|
| SLICERS_VERIFY_2026-05-06.json | YES | YES — 2 of 7 not_found (SuperSlicer, Slic3r) | None |
| MODELERS_VERIFY_2026-05-06.json | YES | YES — 3 of 6 not_found (FreeCAD, CadQuery, build123d) | None |
| PRINTFARM_VERIFY_2026-05-06.json | YES | YES — all 6 localhost services unreachable, S1 camera skipped per policy | None |
| GEN3D_VERIFY_2026-05-06.json | YES | YES — 4 of 5 not_installed (ComfyUI, TRELLIS, Hunyuan3D, TripoSR) | None |
| FIRMWARE_VERIFY_2026-05-06.json | YES | YES — both toolchains (avr_gcc, arm_none_eabi_gcc) absent | None |
| PROOF_MANIFEST_2026-05-06.json | YES | N/A (file listing, not install probe) | None |

### Proof File Quality Assessment

**SLICERS**: Real timestamps (`2026-05-06T23:29:36.844112+00:00`), real output_head captured from actual CLI invocations (PrusaSlicer help text, CuraEngine version line, FLSUN version line), honest `not_found` with notes explaining absence. BambuStudio marked `found` via filesystem metadata only with explicit note — correct behaviour for a GUI-only launcher.

**MODELERS**: Real subprocess output captured (`Blender 5.1.1`, `build date: 2026-04-14`), real pip show results with package locations (`C:\\Python314\\Lib\\site-packages`), honest pip `return_code: 1` for missing packages. Policy section correctly documents `pip: show only (no install)`.

**PRINTFARM**: Real network probe: 3 printers reachable on LAN (elapsed_ms 98–211 ms, real IPs), 6 localhost services honestly unreachable with `[WinError 10061]` errors recorded verbatim. S1 camera skipped per policy with note.

**GEN3D**: Real `git ls-remote` probes with actual commit SHAs and ref counts (ComfyUI: 200 refs, BambuStudio: 15 refs). Real pip show checks with `return_code: 1` for missing packages. Honest `weights_present: false` for all providers. BambuStudio detected as installed via executable path.

**FIRMWARE**: Real `git ls-remote --heads` output with real commit SHAs and branch counts (Klipper: 6 heads, Marlin: 25 heads, RepRap: 40 heads, Prusa: 31 heads). Both toolchains honestly missing with `not_installed` reason. Forbidden flash token list is comprehensive.

**PROOF_MANIFEST**: Real file sizes (zip is 2.9 MB, total 3.47 MB) with real filesystem modification timestamps. File listing consistent with actual proof directory contents.

---

## Verifier Script Verification

| Script | Real probe calls? | Handles missing tools? | Issues |
|--------|-------------------|----------------------|--------|
| verify_slicers.py | YES — `subprocess.run`, `shutil.which`, `Path.is_file` | YES — returns `status: not_found` with note | None |
| verify_modelers.py | YES — `subprocess.run` for CLI, `subprocess.run pip show` for Python | YES — returns `installed: false`, `status: not_found` | None |
| verify_printfarm.py | YES — `urllib.request.urlopen` HTTP GET, `shutil.which` for binaries | YES — records unreachable with error string | None |
| verify_firmware.py | YES — `subprocess.run git ls-remote`, `shutil.which` for toolchains | YES — records `not_installed` reason, exits 0 | None |

### Script Quality Assessment

All 4 scripts pass `python -m py_compile` syntax check: **PASS**

**verify_slicers.py**: Uses `shutil.which` for PATH resolution, `Path.is_file()` for absolute paths, `subprocess.run` with `capture_output=True` and real `timeout_s` per slicer. Handles `TimeoutExpired`, `OSError`. The `is_ok` determination is correct: requires return_code==0 OR version extracted OR >10 chars of output. No hardcoded return values. BambuStudio uses `metadata_only=True` flag to avoid launching GUI — correct.

**verify_modelers.py**: Uses `shutil.which` and `Path.is_absolute()` for executable resolution. CLI probes via `subprocess.run` with version regex extraction. Python probes via `pip show` subprocess and `python -c` smoke tests. Handles `TimeoutExpired`, `OSError`. Policy enforces `pip: show only (no install)`. No hardcoded return values.

**verify_printfarm.py**: Uses `urllib.request` (stdlib only, no third-party HTTP). Skips S1 camera by policy. Probes Moonraker `/server/info` via HTTP GET with real timeout. Handles `HTTPError`, `URLError`, `TimeoutError`, `OSError`. Records real error messages verbatim. No hardcoded return values.

**verify_firmware.py**: Uses `shutil.which("git")` before any git probe. Uses `subprocess.run(["git", "ls-remote", "--heads", url])` — read-only, no clone. Toolchain probe uses `<cmd> --version`. `_is_flash_invocation()` guard prevents forbidden commands. Exits 0 even for missing tools. No hardcoded return values.

---

## Route Implementation Verification

| Route | Real implementation? | Hardcoded? | Issues |
|-------|---------------------|-----------|--------|
| GET /api/sources/readiness (source_os.py) | YES — reads real proof JSON files from disk | NO | None |
| GET /api/artifacts/list (artifacts.py) | YES — `os.walk` filesystem scan | NO | None |
| GET /api/design/templates (design.py) | YES — `importlib.util.find_spec` live module check | NO | None |
| GET /api/design/providers (design.py) | YES — `shutil.which` + `subprocess.run` live probes | NO | None |
| GET /api/gen3d/providers (generation.py) | YES — reads Lane 04 proof JSON + `port_reachable` live probe | NO | None |
| GET /api/gen3d/templates (generation.py) | YES — filesystem schema discovery + hard local template | NO | None |
| GET /api/observe/status (observe.py) | YES — `urllib.request.urlopen` live camera probes | NO | None |

### Route Quality Assessment

**source_os.py** (`GET /api/sources/readiness`): Reads three real proof JSON files (`CLI_READINESS_PATH`, `CLI_SURFACE_PATH`, `LOCAL_TOOLING_PATH`) from disk. Returns honest status counts from proof data. Falls back to unavailable with a descriptive `next_action` message when a tool is absent. No subprocess calls needed — correct for a readiness aggregation endpoint.

**artifacts.py** (`GET /api/artifacts/list`): Uses `os.walk(_PROOF_DIR)` to scan the real proof directory. Reports actual `stat().st_size` and `stat().st_mtime`. Path traversal protection via `relative_to()`. No fake metadata.

**design.py** (`GET /api/design/templates`): `_discover_templates()` calls `importlib.util.find_spec(module_name)` then `importlib.import_module(module_name)` — live Python runtime check. Reports `executor_available: False` with error message if import fails. Checks `missing_deps` via `find_spec` for each required module. Not hardcoded.

**design.py** (`GET /api/design/providers`): `_probe_providers()` calls `shutil.which()` for CLI tools and `importlib.util.find_spec()` for Python packages. For found executables, runs `subprocess.run([detected_path, *version_args], timeout=5)` to get real version strings. All probed at call time (`probed_at: utc_now()`). No stubs.

**generation.py** (`GET /api/gen3d/providers`): Reads real Lane 04 GEN3D proof file from disk and merges with live `port_reachable()` check for providers with HTTP endpoints. Honest readiness states: `available` only when live port probe succeeds; `not_installed` when proof shows pip not present; `unavailable` when repo also unreachable.

**generation.py** (`GET /api/gen3d/templates`): Local `calibration_cube` template is real (produced by `trimesh.creation.box`). Provider-backed templates discovered by checking `_SCHEMAS_DIR / schema_file` filesystem path; `schema_present` flag is honest.

**observe.py** (`GET /api/observe/status`): `_probe_camera_timed()` makes a real HTTP request via `urllib.request.urlopen` with 1.5 s timeout. Records real `elapsed_ms`, `http_status`, and calculates `estimated_fps` from response time. S1 camera flagged `read_only: True` via `is_s1_target()`. No hardcoded status values.

### Grep Red Flag Analysis

The `return []` occurrences in `design.py` (lines 534, 612, 616, 618) are guard clauses in helper functions that return empty lists when input is not a dict/list — this is correct defensive programming, not hardcoded fake data.

Line 146 contains the word "hardcoded" in a docstring explicitly saying templates are NOT derived from hardcoded fake metadata — a false positive from the grep.

No genuine hardcoded return value red flags found.

---

## Test Quality Check

| Test File | Tests real behaviour? | Quality | Issues |
|-----------|----------------------|---------|--------|
| test_slicers.py | YES — live probes against real executables | HIGH | None |
| test_modelers.py | YES — validates proof JSON against schema contract | HIGH | None |

**test_slicers.py**: Contains both unit tests (logic without filesystem) and integration tests. Unit tests verify:
- `_resolve_exe` returns None for non-existent paths (real filesystem check)
- `probe_slicer` returns correct schema for not-found entry (real behaviour test)
- `run_all_probes` returns correct totals and all required keys

Live integration tests use `@pytest.mark.parametrize` from actual proof file — only runs if the executable is confirmed installed and `Path(exe_path).is_file()` is True. G-code safety guard checks that probe output does not contain G-code markers (`;LAYER:`, `G28 `, `M104 `).

No vacuous tests that always pass regardless of code. The `assert result["status"] in ("found", "not_found")` in `test_run_all_probes_status_values` is paired with the actual logic under test — it would fail if the script returned an invalid status string.

**test_modelers.py**: Validates proof JSON schema contract including:
- `status == "found"` must correlate with `installed == True` (cross-field consistency check)
- CLI modelers with `installed=True` must have `version_probe.found == True`
- pip_probes must list all companion packages (numpy-stl, open3d alongside trimesh)
- Summary counts must match actual modeler list

These are meaningful semantic checks, not vacuous schema checks.

---

## BLOCKERS

None. All proof files contain real probe output. All verifier scripts implement genuine runtime checks. All API routes use real filesystem/subprocess/network operations. Tests exercise real behaviour.

---

## PASS

All runtime truth checks pass:
- 6/6 proof files verified as genuine
- 4/4 verifier scripts pass syntax check and implement real probes
- 7/7 API routes verified as real implementations with no hardcoded returns
- 2/2 test files verified as exercising real behaviour
