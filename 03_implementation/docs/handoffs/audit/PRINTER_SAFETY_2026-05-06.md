# Printer/Camera/Physical Safety Audit
**Date**: 2026-05-06
**Agent**: claude-polish-printer-safety-04
**Task ID**: H3D-CLAUDE-POLISH-PRINTER-SAFETY-2026-05-06
**Branch**: claude/polish-safety-audit

---

## S1 Camera-Only Lock Verification

### Backend — printers.py

| Code Path | S1 Blocked Before Network? | Status |
|-----------|---------------------------|--------|
| `GET /api/printers/probe` (probe_printer_by_ip) | YES — line 103: `if str(address) in CAMERA_ONLY_IPS or is_s1_target(str(address))` raises 403 before any network call | PASS |
| `GET /api/printers/{printer_id}/test` (test_printer) | YES — line 343: `check_s1_lock(printer_id)` raises 423 before Moonraker probe | PASS |
| `POST /api/printers/{printer_id}/move` (move_printer) | YES — line 361: `check_s1_lock(printer_id)` raises 423 before any action | PASS |
| `POST /api/printers/{printer_id}/upload` (upload_to_printer) | YES — line 367: `check_s1_lock(printer_id)` raises 423 before any action | PASS |
| `POST /api/printers/{printer_id}/upload-gcode` (upload_gcode_to_printer) | YES — line 373: `check_s1_lock(printer_id)` raises 423 before write logic | PASS |
| `POST /api/printers/onboard` — URL validation | YES — line 515: `_validate_onboard_moonraker_url` checks CAMERA_ONLY_IPS, raises 403 | PASS |
| `POST /api/printers/onboard` — printer ID validation | YES — line 557: `_validated_onboard_printer_id` calls `is_s1_target`, raises 423 | PASS |
| `POST /api/printers/onboard` — model validation | YES — line 574: `_validated_onboard_model` raises 423 for "FLSUN S1" | PASS |

**CAMERA_ONLY_IPS constant present**: YES — line 40:
`CAMERA_ONLY_IPS: frozenset[str] = frozenset({"192.168.0.12"})`

**Safety module** (`hermes3d/api/safety.py`):
- `S1_ALT_IDS = {"flsun-s1", "flsun_s1", "s1", "192.168.0.12"}` — covers all S1 aliases including raw IP
- `check_s1_lock()` raises HTTP 423 (LOCKED)
- `is_s1_target()` delegates to `is_s1_printer()` from local_state for DB-level check

### Backend — jobs.py

| Code Path | S1 Blocked Before Network? | Status |
|-----------|---------------------------|--------|
| `_check_printer_policy()` Gate 1 | YES — line 39: `check_s1_lock(printer_id)` is the first gate, before write-allowed or idle checks | PASS |
| `POST /api/jobs/{id}/repair/propose` | YES — line 186: `check_s1_lock(job.get("printer_id"))` before any planning | PASS |
| `POST /api/jobs/{id}/repair/apply` | YES — line 234: `_check_printer_policy()` called, which invokes check_s1_lock first | PASS |
| `POST /api/jobs/{id}/retry` | YES — line 279: `_check_printer_policy()` called | PASS |
| `POST /api/jobs/{id}/rollback` | YES — line 322: `_check_printer_policy()` called | PASS |

**`_check_printer_policy()` gate order** (lines 25–96):
1. Gate 1: S1 hard lock (`check_s1_lock`)
2. Gate 2: Write-allowed list + DB `write_enabled` / `safety_policy`
3. Gate 3: PRINTER_IDLE check (`live_state.lower() not in PRINTER_IDLE_STATES`)

All three gates in correct order. PASS.

### Backend — observe.py

| Code Path | S1 Read-Only Enforced? | Status |
|-----------|------------------------|--------|
| `GET /api/observe/status` — per camera | YES — line 79: `"read_only": is_s1_target(printer_id)` flags S1 | PASS |
| `GET /api/observe/cameras` — per camera list | YES — line 100: `"printer_locked": is_s1_target(printer["id"])` | PASS |
| `GET /api/observe/cameras/{id}/health` | YES — line 212: `"read_only": is_s1_target(str(camera["printer_id"]))` | PASS |
| Camera stream/snapshot | READ-ONLY — HTTP redirect to camera URL, no printer command | PASS |
| `POST capture-evidence` | READ-ONLY — HTTP GET to snapshot URL, stores JPEG artifact | PASS |
| Camera probe `_probe_camera_timed()` | READ-ONLY — HTTP GET to MJPEG endpoint, no write commands | PASS |
| `PUT /api/observe/cameras/{id}/view` | READ-ONLY — stores CSS display preferences in DB only; no hardware commands | PASS |

**All 4 cameras present**: Verified via `_camera_kind()` (lines 255–263):
- `flsun_s1` — integrated (camera-only, read_only=True)
- `flsun_t1_a` — integrated (T1 #1)
- `flsun_t1_b` — integrated (T1 #2)
- `flsun_v400` — usb_webcam

### Frontend — Printers.tsx

| Check | Result | Status |
|-------|--------|--------|
| `CAMERA_ONLY_IPS = new Set(["192.168.0.12"])` present | YES — line 17 | PASS |
| S1 blocked in wizard before probe | YES — lines 71–75: `if (CAMERA_ONLY_IPS.has(ipTrimmed))` sets `isCameraOnly=true`, blocks probe call | PASS |
| S1 "cannot add" message displayed | YES — lines 234–239: "Camera only — cannot add as print target." | PASS |
| Upload/Start buttons disabled for S1 | YES — lines 597–605: `uploadDisabledReason` set to lock message when `locked=true` (isS1) | PASS |
| Test button disabled for S1 | YES — lines 611–614: `testDisabledReason` set for locked printers | PASS |
| G-code path input disabled for S1 | YES — line 697: `disabled={locked}` on input | PASS |
| Model selector excludes FLSUN S1 | YES — lines 281–286: only Generic, FLSUN T1, FLSUN V400 in wizard model dropdown | PASS |

### Frontend — Observe.tsx

| Check | Result | Status |
|-------|--------|--------|
| Camera hardware pan/tilt commands | NONE FOUND | PASS |
| Camera hardware zoom (PTZ) commands | NONE FOUND | PASS |
| GCode/print commands | NONE FOUND | PASS |
| Movement commands | NONE FOUND | PASS |
| CameraControls = CSS display transforms only | YES — rotate_deg, mirror_x/y, zoom, brightness, contrast are CSS filter/transform | PASS |
| `onViewChange` calls PUT to `/api/observe/cameras/{id}/view` | YES — stores display prefs in DB only; backend `set_camera_view_settings` confirmed DB-only | PASS |
| Probe button calls GET `/api/observe/cameras/{id}/health` | YES — read-only health check | PASS |

---

## GCode Keyword Scan (must be ZERO in probe/read routes)

Searched `printers.py` for: `gcode|G28|G29|M104|M109|M140|M190|start_print|upload`

Results in **read routes** (GET /api/printers/probe, GET /api/printers/{id}/status):
- **ZERO** GCode keywords in probe/read routes

GCode references found ONLY in write routes:
- `upload_gcode_to_printer` (POST) — guarded by `check_s1_lock` on line 373
- `_require_print_start_gates` — only called from write route with job_id gate
- `GcodeUploadRequest` — Pydantic model for upload endpoint only
- Import `check_gcode_file`, `resolve_bounds` — only used in upload route

**Probe endpoint analysis** (`GET /api/printers/probe`, lines 91–169):
- Calls `client.server_info()` — GET /server/info (read-only)
- Calls `client.printer_state(...)` — GET /printer/objects/query (read-only)
- Calls `get_profile(...)` — in-memory static data, no network call
- Returns JSON data only
- Zero GCode transmission

---

## Policy Test Results

| Test Suite | Pass | Fail | Notes |
|------------|------|------|-------|
| `04_testing/pytest/unit/test_printer_policy.py` | 16 | 0 | All 16 passed |
| `04_testing/pytest/unit/test_jobs_policy.py` | 37 | 0 | All 37 passed |
| **Total** | **53** | **0** | |

---

## Bypass Path Check

Searched all three route files for: `admin`, `override`, `skip`, `force`, `bypass`

Results:
- `printers.py`: **ZERO** matches — no bypass paths found
- `jobs.py`: **ZERO** matches — no bypass paths found
- `observe.py`: **ZERO** matches — no bypass paths found
- `safety.py`: **ZERO** matches — no bypass paths found

---

## Minor Observation (Non-blocking)

**`_probe_optional_http` in printers.py (line 688)**: Uses HTTP GET (not HEAD) for camera URL verification during printer onboarding. This is different from `validate_camera_url` which uses HEAD. The GET approach is acceptable because:
1. Many MJPEG streams do not support HEAD requests
2. This is a one-time onboarding probe, not a production polling call
3. It reads stream data only — no write, no command
4. `required: False` means a failed camera probe does not block onboarding

**Classification**: Non-blocking observation only. No safety violation.

---

## BLOCKERS (safety violations)

**NONE.**

---

## PASS (safety verified)

1. S1 (192.168.0.12) is blocked BEFORE any network call in ALL write routes (printers.py: test, move, upload, upload-gcode; jobs.py: repair, retry, rollback via `_check_printer_policy`)
2. S1 IP in `CAMERA_ONLY_IPS` frozenset — cannot be onboarded via moonraker URL, printer ID, or model name (three independent checks)
3. `_check_printer_policy()` enforces gates in strict order: S1 lock → write-allowed list → idle check
4. Probe endpoint (`GET /api/printers/probe`) is fully read-only: GET Moonraker queries only, zero GCode keywords
5. Camera validation uses HEAD-only in `validate_camera_url`; GET in `_probe_optional_http` is acceptable (MJPEG compatibility)
6. `observe.py` camera controls are display-only CSS transforms stored in DB; no hardware PTZ/pan/tilt/zoom commands issued anywhere
7. `observe.py` marks S1 `read_only: true` in all camera list endpoints
8. All 4 cameras (S1/T1-A/T1-B/V400) are present in `_camera_kind()`
9. Frontend blocks S1 in wizard, upload inputs, test button with `CAMERA_ONLY_IPS` + `isS1()` guards
10. Observe.tsx contains zero hardware control commands (pan/tilt/gcode/move/PTZ absent)
11. 53/53 policy tests passed (16 printer + 37 jobs)

**Overall verdict: SAFETY VERIFIED — no violations found.**
