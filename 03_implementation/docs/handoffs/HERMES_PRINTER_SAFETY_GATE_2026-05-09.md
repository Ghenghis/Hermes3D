# Hermes3D Printer Safety Gate (W6-9, 2026-05-09)

**Owner agent:** `claude-w6-9-printer-safety` (lane 5 of 5-lane finish order)
**Branch:** `claude/w6-9-printer-safety-e2e`
**Subsystem name:** Hermes3D Printer Safety Gate (BLK-016 successor)

## 1. Threat model

A consumer FDM printer can ignite a plate full of ABS or PETG residue if the
nozzle reaches ~210 C while the bed is obstructed by a previous print, by
debris, or by a person leaning over it. Two failure modes were tracked
separately as BLK-016:

* **Heat-without-vision** — a remote API caller asks
  `start_print` / `heat_extruder` / `heat_bed` while NO operator can see the
  printer (camera dead/unconfigured). The printer obeys and a smouldering
  obstruction can ignite over hours. Class: ICS actuator commanded without
  pre-condition (NIST SP 800-82r3 calls this a violation of "default-deny").
* **Heat-onto-obstruction** — a vision system exists but reports the plate is
  obstructed (or "unknown"); the gate is meant to refuse heat anyway, but
  was previously absent so the command was accepted on the printer's say-so.

The gate is the **bouncer at the door**: if either gate has not seen recent
proof, every heat/start command is refused. Posture is **default-deny**.

## 2. Three explicit gates

| Gate | Source of truth | Freshness window | Pass condition |
| ---- | ---- | ---- | ---- |
| Camera-only | The latest live frame for the printer's camera | `CAMERA_FRAME_FRESHNESS_SEC` (5 s default) | A frame ts_unix within the window |
| Plate clear | The latest vision-classifier verdict | `PLATE_CLEAR_FRESHNESS_SEC` (30 s default) | classification == "clear" AND confidence >= `PLATE_CLEAR_MIN_CONFIDENCE` (0.85 default) |
| No heat/start | Combination of the two | derived | Both gates must pass concurrently |

Failure modes (each maps to a string in `is_safe_to_start`'s `reasons` list):

* `no camera bound to printer`
* `no camera frame ever`
* `no plate classification ever`
* `camera stale: last frame Xs ago`
* `plate classification stale: Xs ago`
* `plate not clear: classifier says 'obstructed'`
* `plate not clear: classifier says 'unknown'`
* `plate-clear confidence too low`

## 3. Files in this lane

| File | Purpose |
| ---- | ---- |
| `03_implementation/src/hermes3d/services/printer_safety_gate.py` | `PrinterSafetyGate` service (in-memory, asyncio-locked) |
| `03_implementation/src/hermes3d/api/routes/printer_safety.py` | 7 routes: 3 gated commands + 1 read-only state + 3 ingestion |
| `04_testing/pytest/integration/test_printer_safety_gate.py` | 10 integration tests (all passing) |
| `03_implementation/docs/handoffs/HERMES_PRINTER_SAFETY_GATE_2026-05-09.md` | This handoff |

### Wire-in note (open task)

`03_implementation/src/hermes3d/api/app.py` is held by `claude-w6-7-app-registry`
during this lane. The W6-9 router is therefore not yet imported by the FastAPI
app factory. Whoever lands W6-7 (or whoever picks up after W6-7 releases the
lock) must add **two lines** to `app.py`:

```python
from hermes3d.api.routes import (
    ...,
    printer_safety,   # <-- add
    ...,
)

# ... in create_gui_app(), inside the include_router loop ...
for route_module in [
    ...,
    printer_safety,   # <-- add
    ...,
]:
    app.include_router(route_module.router)
```

The 10 integration tests construct a fresh `FastAPI()` and `include_router`
the safety router directly, so they do not depend on this wire-in.

## 4. Public API

### Service surface

```python
from hermes3d.services.printer_safety_gate import PrinterSafetyGate, get_default_gate

gate = get_default_gate()
await gate.bind_camera(printer_id="flsun_t1_a", camera_id="cam_t1_a")
await gate.record_camera_frame(camera_id="cam_t1_a", ts_unix=time.time())
await gate.record_plate_classification(
    camera_id="cam_t1_a", classification="clear", confidence=0.92, ts_unix=time.time(),
)

allow, reasons = await gate.is_safe_to_start("flsun_t1_a")
if not allow:
    raise PreflightBlocked(reasons=reasons)
```

### Route surface

| Method | Path | Behaviour |
| ---- | ---- | ---- |
| POST | `/api/printers/{id}/start-print` | 403 with `blocked_by` if not safe; 200 if safe |
| POST | `/api/printers/{id}/heat-extruder` | same |
| POST | `/api/printers/{id}/heat-bed` | same |
| GET | `/api/printers/{id}/safety-state` | `{allow, camera_fresh, plate_classification, plate_confidence, blocked_by, thresholds, ...}` |
| POST | `/api/printers/{id}/safety-events/bind-camera` | bind printer to a camera_id |
| POST | `/api/printers/{id}/safety-events/camera-frame` | record a live frame (called by future camera feeder) |
| POST | `/api/printers/{id}/safety-events/plate-classification` | record a vision verdict (called by future classifier) |

## 5. How to extend

The gate's only state is camera frames and classifications. Three reasonable
future extensions DO NOT require changing the public surface:

1. **Door interlock** — register a fourth gate (`record_door_state`) and add
   a fourth row to the failure-reason mux in `is_safe_to_start`.
2. **Weight sensor** — add a `record_bed_weight(printer_id, grams, ts)` and
   refuse to start if `grams > 50` (any non-trivial residue).
3. **Persistence** — replace the in-memory `_printers` dict with a write to
   the `proof_events` ledger. The `asyncio.Lock` already serialises writes,
   so the swap is one method body.

Tests should accompany every new gate; the existing 10 tests remain the
baseline contract.

## 6. Why not just lean on the existing `core.safety` package?

`core.safety` (thermal runaway, emergency-stop timing, gcode bounds, material
window, bed adhesion) is a **G-code-time** pre-flight: it inspects the file
about to be sent. It cannot know whether the bed is physically clear or
whether the camera is alive. The W6-9 gate is **runtime-time**: it answers
"is the world safe RIGHT NOW for an actuator to fire?", which is a complementary
question to "is this g-code internally consistent?" Both gates run; both must
pass. No work is duplicated.

## 7. Sources cited

* **NIST SP 800-82 Rev. 3, "Guide to Operational Technology (OT) Security",
  2023-09.** Section 5.4.2 (default-deny posture for actuator commands) and
  Section 6.3.5 (sensor-driven pre-conditions for ICS actuators).
  https://csrc.nist.gov/publications/detail/sp/800-82/rev-3/final
* **OctoPrint safety best practices.** "Don't enable heating without
  operator confirmation" + thermal runaway rationale.
  https://docs.octoprint.org/en/master/features/safety.html

## 8. Test results (run on 2026-05-09)

```
$ python -m pytest 04_testing/pytest/integration/test_printer_safety_gate.py -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-8.4.2
collected 10 items

test_default_state_is_blocked_with_full_reasons         PASSED
test_camera_frame_alone_still_blocked                   PASSED
test_obstructed_plate_is_blocked                        PASSED
test_clear_with_low_confidence_is_blocked               PASSED
test_clear_high_confidence_allows                       PASSED
test_camera_stale_blocks                                PASSED
test_plate_classification_stale_blocks                  PASSED
test_state_is_isolated_per_printer                      PASSED
test_routes_403_when_blocked_and_200_when_allowed       PASSED
test_concurrent_calls_have_no_race                      PASSED

============================= 10 passed in 1.43s ==============================
```

10/10 pass. No skipped or xfail tests.

## 9. STATUS UPDATE — wired-in 2026-05-09 (W8-10)

**Owner agent:** `claude-w8-10-app-wire-in`
**Branch:** `claude/w8-10-printer-safety-app-wire-in` (from
`feat/hermes3d-7-complete-gui-repo-wiring` HEAD `d1334ed`)
**Predecessor lock release:** W6-7 released `app.py` after PR #179 opened, so the
two-line wire-in deferred at the bottom of section 3 is now safe to land.

### Patch applied to `03_implementation/src/hermes3d/api/app.py`

Two lines added — alphabetised in the `from hermes3d.api.routes import (...)`
block, and inserted adjacent to `printers` in the `route_module` list inside
`create_gui_app()`:

```diff
 from hermes3d.api.routes import (
     ...,
     ports,
+    printer_safety,
     printers,
     roadmap,
     ...
 )

 # ... inside create_gui_app() ...
 for route_module in [
     ...,
     generation,
     printers,
+    printer_safety,
     settings,
     ...,
 ]:
     app.include_router(route_module.router)
```

No other route or service in `app.py` was touched. Diff is 2 added lines and
0 deleted.

### Verification (run on 2026-05-09 against the patched app)

```text
$ PYTHONPATH=src python -c "from hermes3d.api.app import app; \
    print(sorted([r.path for r in app.routes if 'safety' in r.path \
    or r.path.endswith('/start-print') \
    or r.path.endswith('/heat-extruder') \
    or r.path.endswith('/heat-bed')]))"
[
  '/api/printers/{printer_id}/heat-bed',
  '/api/printers/{printer_id}/heat-extruder',
  '/api/printers/{printer_id}/safety-events/bind-camera',
  '/api/printers/{printer_id}/safety-events/camera-frame',
  '/api/printers/{printer_id}/safety-events/plate-classification',
  '/api/printers/{printer_id}/safety-state',
  '/api/printers/{printer_id}/start-print',
]
```

All 7 W6-9 routes are now mounted on the canonical `app` (244 total app routes).

### Smoke tests (run on 2026-05-09 against the patched app)

```text
$ python -m pytest 04_testing/pytest/integration/test_printer_safety_gate.py -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-8.4.2
collected 10 items

test_default_state_is_blocked_with_full_reasons         PASSED
test_camera_frame_alone_still_blocked                   PASSED
test_obstructed_plate_is_blocked                        PASSED
test_clear_with_low_confidence_is_blocked               PASSED
test_clear_high_confidence_allows                       PASSED
test_camera_stale_blocks                                PASSED
test_plate_classification_stale_blocks                  PASSED
test_state_is_isolated_per_printer                      PASSED
test_routes_403_when_blocked_and_200_when_allowed       PASSED
test_concurrent_calls_have_no_race                      PASSED

============================= 10 passed in 2.22s ==============================
```

10/10 still pass post-wire-in. (Suite uses a freshly-constructed `FastAPI()`
plus `include_router` so it does not exercise `app.py` directly — the
verification command above confirms `app.py` itself now mounts the router.)

`04_testing/pytest/unit/test_app_factory.py` and `test_app_routes.py` were
checked via Glob and do **not** exist in this repo, so no other unit harness
needs to run for this wire-in.

### Sources

1. **FastAPI `include_router` reference** —
   <https://fastapi.tiangolo.com/tutorial/bigger-applications/#include-the-apirouter>
   confirms the `app.include_router(module.router)` pattern this repo uses.
2. **Existing route wiring in `03_implementation/src/hermes3d/api/app.py`
   (HEAD `d1334ed`)** — the alphabetised import block plus iterative
   `for route_module in [...]: app.include_router(route_module.router)` loop
   is the team's canonical pattern; this patch follows it without exception.

### Lock release

`hermes_release_files` called for `claude-w8-10-app-wire-in` on:
- `03_implementation/src/hermes3d/api/app.py`
- `03_implementation/docs/handoffs/HERMES_PRINTER_SAFETY_GATE_2026-05-09.md`

after PR was opened.
