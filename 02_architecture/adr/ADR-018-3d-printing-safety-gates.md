# ADR-018 — 3D-printing safety gates (P1 batch)

**Status:** Accepted.
**Date:** 2026-05-03.
**Related:** [ADR-009 orchestration skeleton](ADR-009-orchestration-skeleton.md), [ADR-013 kit hardening v5.1](ADR-013-kit-hardening-v5_1.md), `03_implementation/src/hermes3d/core/agents/preflight.py`.
**Tracking:** `H3D-V5.3-3DPRINT-SAFETY`.

## Context

Hermes3D drives a 12-printer fleet end-to-end: vision → mesh → repair →
truth-gate → slice → **print**. Up to v5.2 the only "safety" surface
was `core.agents.preflight.PreflightReport`, which checks scheduler /
spool / budget concerns. None of those checks defend against
**physical safety hazards** that could damage a printer, ruin a print,
or in the worst case start a fire:

- A thermistor disconnect or stuck-on heater (thermal runaway).
- An `M112` that the firmware never acknowledges (silent halt failure).
- A G-code program that targets coordinates outside the printable
  volume (head-into-frame collision).
- A profile whose `nozzle_temp` / `bed_temp` is outside the loaded
  material's safe window (clogs, fumes, fire).

These four hazards are P1 because they each cause unrecoverable
hardware damage on the first occurrence and the firmware's own
defenses are known-weak: Klipper's `verify_heater` has long-standing
edge cases on bed-thermistor noise, Marlin's `MAXTEMP` cutoff fires
*after* the heater has already been driven for the duration of the
runaway, and neither firmware enforces XY bounds against an arbitrary
G-code program.

The existing `Preflight` module is the right shape (data-only,
`PASS|WARN|FAIL`, no I/O) but its concerns are operational
(scheduling, cost, spool tracking), not physical. We need a
companion package whose mandate is *only* physical safety.

## Decision

Add `hermes3d.core.safety` — a side-effect-free package containing
four independent safety gates, each shipping its own data shapes,
parser/check logic, and pytest harness. The gates are wired into the
orchestrator's pre-flight phase (before `submit_print_job`) and into
the existing `hermes_run_gate` registry under the IDs:

- `safety.thermal_runaway_detection`
- `safety.emergency_stop_timing`
- `safety.gcode_bounds_precondition`
- `safety.material_temperature_window`

Failures emit `safety.violation` events to the evidence ledger via the
event-manager bridge in `hermes3d.core.agents.orchestrator`. The
package itself never imports the orchestrator or event manager — it
returns plain dataclasses, and the orchestrator owns all side effects.

### Module layout

```
hermes3d/core/safety/
├── __init__.py              # Public API + run_all_safety_gates()
├── thermal_runaway.py       # Detector state machine + replay harness
├── emergency_stop.py        # M112 timing harness + KlipperMockSimulator
├── gcode_bounds.py          # G-code parser + bounds checker
├── material_window.py       # Material DB loader + window check
└── material_db.yaml         # Default windows (PLA, PETG, ABS, TPU, PC, Nylon)
```

### Gate-by-gate design

#### `safety.thermal_runaway_detection`

Pure state machine over `TemperatureSample` ticks. Two trip
conditions:

1. **Persistent over-target.** `temp > target + 15°C` for `> 5 s`.
   The detector accumulates excursion duration; any sample dropping
   back below threshold resets the excursion. This avoids false
   positives on PID overshoot at the start of a heat-up.
2. **Thermistor error.** Any sample carrying a non-empty
   `thermistor_error` code (`MINTEMP`, `MAXTEMP`, Klipper's
   `shutdown:temperature_sensor`) trips immediately.

The brief specifies a 2-second detection budget. With a 1 Hz
monitoring cadence, the trip lands on the first sample after the 5 s
window — i.e. ≤ 1 s after the window crosses. That's well under the 2 s
budget. The test harness drives the detector at both 1 Hz and 50 ms
cadences to confirm both end up within budget.

#### `safety.emergency_stop_timing`

Round-trip timer for `M112 → motors_disabled` evidence. Defines a
`Protocol` (`EmergencyStopTransport`) so the same code path serves
the production Moonraker client and the in-process
`KlipperMockSimulator` used by tests. The mock is deterministic — its
`response_delay_s` knob exactly defines the round-trip time, which
makes the budget assertion (`elapsed_ms ≤ 200 ms`) trivially testable.

The 200 ms budget is the brief's number; it matches Klipper's
documented worst case for a `restart` command on a normally-loaded
moonraker process.

#### `safety.gcode_bounds_precondition`

Stream parser that tokenises one line at a time, simulates head
position, and checks every commanded target against a `PrinterBounds`
record. Supported codes:

- `G0`/`G1` — straight moves (G90 absolute, G91 relative).
- `G2`/`G3` — arcs. We do not rasterise; we check start, end, and
  any cardinal-tangent points the arc passes through. Slicer output
  is well-served by this; pathological hand-written arcs that span
  > 180° still get the four cardinal extrema checked.
- `G28` (homing), `G29` (bed mesh) — recorded as warnings, not blocked.
- `G90` / `G91` / `G92` — mode + position-set semantics.
- `M`-codes / `T`-codes / unknown G-codes — non-motion, skipped or
  warned.

Bounds source order: explicit `override_bounds` argument, then
`fleet_lookup(printer_id)` → `PrinterProfile`, then
`PRUSA_MK3S_DEFAULT_BOUNDS` (250×210×210 mm) with a warning. The
fallback is deliberately conservative — we'd rather refuse a borderline
move on an unconfigured printer than off-bed it.

#### `safety.material_temperature_window`

YAML-backed material database at `material_db.yaml` (PLA, PETG, ABS,
TPU, PC, Nylon) with a sibling `material_db.user.yaml` override file
(merged on top, never committed). Each entry carries
`nozzle_min_c / nozzle_max_c / bed_min_c / bed_max_c`. The gate
rejects any profile whose temperatures fall outside the window for the
named material; unknown materials are rejected by default.

Escape hatch: `HERMES3D_OVERRIDE_MATERIAL_WINDOW=1` flips the gate
into "log loudly, allow the print" mode. Used for paid-thermistor
experimental materials and developer test prints. The override is
logged at WARNING and reflected as `overridden=true` in the result so
the audit trail is honest about why an out-of-window print was allowed.

### Pre-flight integration

`run_all_safety_gates(...)` runs all four gates as a batch. Missing
inputs cause that gate to be **skipped** (not failed), so partial
runs (dry-run, validate-only) still produce a meaningful bundle.
Successes go to `passed_gates`; failures go to `violations` (a list of
`safety.violation` payloads ready for the event ledger).

The orchestrator wires the bundle into the pre-flight node of
`print_workflow`:

```python
bundle = run_all_safety_gates(...)
if not bundle.passed:
    for v in bundle.violations:
        event_manager.emit("safety.violation", v)
    raise PreflightBlocked(bundle)
```

The bundle is also persisted alongside the existing
`PreflightReport` so the audit trail captures both the operational
and the physical pre-flight in one place.

## Rationale & Consequences

- **Why a new package, not extend `agents/preflight.py`?** Different
  failure mode (physical hazard vs. operational concern), different
  inputs (telemetry traces vs. job metadata), and different test
  harnesses (replay traces vs. pytest fixtures). Co-locating them
  would couple two surfaces that should be evolving on independent
  cadences.
- **Why pure stdlib + PyYAML?** The brief's constraint, and the
  right call: safety code with surprise transitive deps is asking for
  a supply-chain hazard. PyYAML is already pulled transitively via
  pydantic / fastapi.
- **Why a Protocol for `EmergencyStopTransport`?** Lets us hold the
  timing budget as a property of the harness rather than the wire
  protocol. The mock simulator and the production Moonraker client are
  swap-in interchangeable.
- **What this does NOT solve.** Per-printer firmware-level safety
  (Klipper's `verify_heater`, Marlin's `MAXTEMP`) is the *first* line
  of defense — Hermes3D's gates are the *second*. We do not propose
  to replace firmware safety, only to backstop it at the orchestrator
  layer.

### Trade-offs

- The arc-bounds check is approximate for arcs spanning > 180°
  with extrema that fall between cardinal tangents. We accept this:
  slicer output never produces such arcs; hand-written G-code that
  does is rare and the warning-log path is sufficient.
- The material override env var is footgun-shaped. We mitigate by
  logging at WARNING (loud), reflecting the override in the result
  (`overridden=true`), and emitting the violation payload anyway so
  the evidence ledger records the override.
- The thermal-runaway detector trusts the firmware's reported
  `target_c` field. If a malicious firmware lies about target, the
  gate is fooled. This is a known limitation that no orchestrator-level
  detector can fully solve; the mitigation path is firmware
  attestation, out of scope here.

## Status

**Accepted** for the v5.3 release. Implementation lives at
`03_implementation/src/hermes3d/core/safety/`; tests at
`04_testing/pytest/test_safety_*.py`. PR:
`feat/cp-h3d-3dprint-safety-gates`.
