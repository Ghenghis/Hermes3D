# Hermes3D-OS Lite — Master Contract (v5.0)

**Status:** binding for all code in this kit
**Owner:** ShadowByte (Dave)
**Last update:** 2026-04-29

This document is the single source of truth for what this kit promises,
what it refuses to do, and the technical commitments behind every claim.
If runtime code or documentation contradicts the Master Contract, the
Master Contract wins and the contradiction is a bug.

---

## §0  Scope & Vocabulary

**Hermes3D-OS Lite** is an agentic 3D-printing operating-system layer
that sits between mesh generation tooling (Blender, ComfyUI 3D, AI mesh
generators) and a fleet of physical printers running Klipper/Moonraker
or OctoPrint. It is *not* a slicer; it is *not* a printer firmware. It
is the "decision and proof" layer in between.

**The Fleet** in this contract refers to twelve physical printers:

| profile_id | Make / Model | Kinematics | Bed | Z |
|---|---|---|---|---|
| `flsun_qqs_pro` | FLSUN QQ-S Pro | delta | Ø255 mm | 360 mm |
| `flsun_t1_a` | FLSUN T1 (unit A) | delta, enclosed | Ø260 mm | 330 mm |
| `flsun_t1_b` | FLSUN T1 (unit B) | delta, enclosed | Ø260 mm | 330 mm |
| `flsun_super_racer` | FLSUN Super Racer (SR) | delta | Ø260 mm | 330 mm |
| `flsun_s1` | FLSUN S1 | delta, enclosed | Ø320 mm | 430 mm |
| `flsun_v400` | FLSUN V400 | delta | Ø300 mm | 410 mm |
| `creality_cr10s` | Creality CR-10S | cartesian | 300×300 mm | 400 mm |
| `creality_cr6_max` | Creality CR-6 Max | cartesian | 400×400 mm | 400 mm |
| `tronxy_d01_pro` | Tronxy D01 Pro Enclosed | corexy, enclosed | 220×220 mm | 220 mm |
| `tronxy_x5sa_pro` | Tronxy X5SA Pro | corexy | 330×330 mm | 400 mm |
| `prusa_mk3s` | Prusa Research MK3S+ | cartesian | 250×210 mm | 210 mm |
| `sovol_sv01` | Sovol SV01 | cartesian | 280×240 mm | 300 mm |

**Truth Gate** is the 8-check printability validation pipeline. **Proof
Envelope** is the HMAC-signed JSON document that records a Truth Gate
result + visual evidence + mesh hash.

---

## §1  Non-Negotiable Rules (Hard Contract)

The following are violations and must fail CI:

1. **No placeholders in runtime code.** `TODO`, `FIXME`, `STUB`,
   `NOT_IMPLEMENTED`, `mock data`, `sample only`, empty `except: pass`,
   UI handlers with no side effects — all forbidden in shipped code.
2. **No mock-only test strategies.** Mocks are permitted only for paid
   external APIs, nondeterministic hardware, or true isolation needs.
   Every mock-based test must have a sibling integration test that
   exercises the real code path.
3. **Zero warnings by default.** Build, lint, typecheck, and analyzer
   warnings count = 0. Time-bounded allowlists are permitted with
   explicit expiry; no permanent warning debt.
4. **Full wiring required.** GUI controls, REST endpoints, MCP tools,
   and CLI subcommands all reach real backend code.
   If a backend, tool, credential, source checkout, web account, VPS,
   or remote host is missing, the UI must render a disabled or
   unavailable state that says what is missing. It must never invent
   rows, previews, slicer output, printer telemetry, model results,
   proof bundles, or agent activity.
5. **Reproducible from clean clone.** `clone -> install -> run -> test`
   must succeed from a brand-new machine using the documented commands.
6. **Truth Gate is the only gate.** No code path slices, uploads, or
   starts a print bypassing the Truth Gate. Validation results carry
   forward via signed Proof Envelopes.
7. **All printer-side actions are typed and printer-aware.** Dispatch,
   slice profiles, calibration macros, and bed-fit math all consult
   `printer_profiles.py`. There is no "default printer."
8. **No silent mesh mutation.** Auto-repair and auto-orient produce a
   *new* file (`*.repaired.stl`, `*.oriented.stl`); the original is
   never overwritten.
9. **Hermes Agents are user delegates.** When the user grants a Hermes
   Agent a task, that agent is treated as an operator/admin delegate
   across Hermes3D-OS, the user's PC, local files, installed apps, web
   accounts/services, VPS/remote hosts, GitHub, source repositories,
   and other user-controlled systems needed to complete the task. The
   same proof, safety, lock, secret, and audit rules that bind a human
   operator bind the agent.
10. **Missing data means ask or block.** If Hermes3D does not know the
    source path, repository URL, credential location, remote host,
    printer state, model file, material, or user preference needed for
    a task, it asks the user or marks the action blocked. It never
    guesses and presents that guess as fact.
11. **Current S1 safety lock.** FLSUN S1 at `192.168.0.12` is currently
    offline/locked/no-test. Operators and Hermes Agents may edit its
    status metadata, but movement, upload, capture, and test actions
    must return a lock failure until the user explicitly clears that
    safety state.

Violations are tracked in `00_overview/contract/HONESTY_LEDGER.md` until fixed.

---

## §2–§9  Core systems (see linked specs)

| §  | System            | Authoritative spec                              |
|----|-------------------|-------------------------------------------------|
| §2 | Truth Gate        | `02_architecture/contracts/truth_gate_report.schema.json` |
| §3 | Proof Envelope    | `05_truth_proof/PROOF_PROTOCOL.md`             |
| §4 | Printer profiles  | `02_architecture/contracts/printer_profile.schema.json`  |
| §5 | Slicer adapters   | `03_implementation/src/hermes3d/core/slicer/`     |
| §6 | Moonraker client  | `03_implementation/src/hermes3d/core/printers/moonraker_client.py` |
| §7 | Renderer          | `03_implementation/src/hermes3d/core/visual/render.py` |
| §8 | Acceptance runner | `04_testing/acceptance/run_acceptance.py` |
| §9 | Truth Gate checks | `02_architecture/contracts/truth_gate_report.schema.json` |

---

## §10  Material-Aware Dispatch

The dispatcher (`core/agents/dispatcher.py`) selects a printer for a
given (mesh, material, strategy) tuple. **Hard filters run first**:

- Bed fit (kinematics-aware: rectangular vs. circular delta)
- Hotend temperature can reach `material.hotend_typical_c`
- Bed temperature can reach `material.bed_typical_c`
- `requires_enclosure` → printer must be enclosed
- `requires_direct_drive` → printer must have direct-drive extruder

**Soft scoring** then ranks the survivors. Strategies: `auto`,
`fastest`, `quality`, `largest_bed`, `smallest_fit`, `least_busy`,
`delta_prefer`, `cartesian_prefer`. The `auto` strategy is a weighted
blend tuned for the user's typical workflow (see source).

Live state (Moonraker probe) is consumed when present — the dispatcher
prefers `klippy_state == "ready"` printers.

## §11  Print Job Lifecycle

`core/agents/job_queue.py` records every print as a `Job` with the
state machine:

    QUEUED → DISPATCHED → VALIDATED → SLICED → UPLOADED → PRINTING
                                                        ↓
                                            SUCCEEDED | FAILED | CANCELLED

Transitions are validated; illegal jumps raise `ValueError`. The queue
file is JSON, atomically replaced on every save (write-tmp + rename).

## §12  G-code Pre-flight

`core/slicer/gcode_analyzer.py` parses sliced output and surfaces:

- Print time, filament length/weight, layer count, temperatures
- Risk flags: `long-print`, `heavy-spool`, `large-z`,
  `low-infill-with-support`, `high-travel-ratio`,
  `suspiciously-short`

The pre-flight checker (`core/agents/preflight.py`) combines these
flags with spool, schedule, and budget data into a final go/no-go.

## §13  Notifications

`core/notifications/notifier.py` sends Discord, Slack, and generic
webhooks. URLs come from environment variables only — no secrets in
the repo. Every notify is best-effort; failure is logged, never raised.

## §14  Scheduling & Cameras

`core/agents/scheduler.py` enforces a `SchedulerPolicy` (quiet hours,
max duration, ETA cap). `fetch_camera_snapshot()` pulls a still from
any Moonraker-attached webcam.

## §15  Filament Tracking

`core/farm/spool_tracker.py` tracks every spool — material, color,
vendor, remaining grams, currently-loaded printer. Loading a spool on
a printer auto-unloads any previous spool on that printer.

## §16  Print Farm Dashboard

`core/farm/dashboard.py` aggregates Moonraker probe + queue + spool
data into one row per fleet printer. Used by the Gradio UI and the
CLI `fleet status` command.

## §17  CLI Surface

`python -m hermes3d.cli` — see `--help` for the full command catalog.
Every subcommand produces machine-readable output via `--json`.

## §18  Mesh Auto-Repair

`core/agents/mesh_repair.py` runs a 7-stage repair pipeline (dedup
verts, drop degenerate faces, fill holes, fix normals, drop orphans,
merge close verts, trimesh process). It NEVER mutates the input mesh
in place — it returns a copy and a `RepairReport`.

## §19  Auto-Orient

`core/agents/auto_orient.py` scores 6 axis-aligned orientations on
bed-contact area, overhang area, and Z-height, and picks the best.

## §20  Print History

`core/farm/print_history.py` is an append-only JSONL log. Aggregations
yield per-printer success rates, per-material consumption totals, and
total kg/hours for the fleet.

## §21  Cost Estimation

`core/farm/cost_estimator.py` computes `filament_cost_usd +
energy_cost_usd` per job using printer-specific typical wattage.
Defaults are tunable per call.

## §22  Equivalence Pools

`core/agents/equivalence.py` exposes the `flsun_t1_pool` group (the
two T1s are interchangeable). Dispatch resolves a group_id to the
least-busy member.

## §23  Calibration

`core/agents/calibration.py` issues stock Klipper calibration macros
(`SHAPER_CALIBRATE`, `BED_MESH_CALIBRATE ADAPTIVE=1`, pressure-advance
tuning towers, flow-ratio towers) via Moonraker's gcode endpoint.

## §24  Pre-flight

`core/agents/preflight.py` runs the 6-check go/no-go against a job:
truth-gate result, printer state, spool, schedule, budget, gcode
risk flags. Returns a `PreflightReport` with WARN/PASS/FAIL per check.

## §25  Klipper Macros

`config/klipper/hermes3d_macros.cfg` provides drop-in
`START_PRINT`, `END_PRINT`, `PURGE_LINE`, `PAUSE`, `RESUME`,
`CANCEL_PRINT`, `LOAD_FILAMENT`, `UNLOAD_FILAMENT`,
`HERMES3D_HEALTHCHECK`. KAMP-aware adaptive bed mesh on every start.

## §26  REST API

`api/server.py` (FastAPI). Auth via `HERMES3D_API_TOKEN` bearer.
Endpoints: `/health`, `/fleet`, `/dispatch`, `/queue/jobs/*`,
`/spools/*`, `/proof/verify`, `/metrics`, `/metrics/prometheus`.

## §27  MCP Integration

`api/mcp_server.py` — STDIO JSON-RPC, 10 tools so an agentic IDE
(Claude Code, DaveAI-IDE, Roo Code) can drive the system directly.

Hermes Agents using MCP are first-class user delegates, not observers.
They may configure apps, edit source, run setup, use the user's PC,
web services, VPS/remote hosts, source repositories, GitHub branches,
commits, pushes, and PRs when those actions are part of the user task.
They must still obey printer safety, proof envelopes, file locks,
secret redaction, and branch/PR policy.

## §28  Auto-Recovery

`core/agents/auto_recovery.py` performs soft → firmware Klipper
restart with backoff. Refuses to act when a print is in progress.

## §29  Backup & Restore

`core/farm/backup.py` produces a `.tar.gz` of queue, spools, history,
and acceptance results, with a manifest containing every file's
SHA-256. Restore refuses to overwrite a non-empty target without an
explicit `overwrite=True`.

## §30  Orchestration Brain (LangGraph-style)

`core/orchestration/agent_graph.py` defines a `WorkflowGraph`
with checkpointed state, conditional branching, and SKIP/FAIL/RETRY
node outcomes. `print_workflow.py` composes all the agents into a
single 12-node pipeline.

## §31  Skill Memory (Hermes-style)

`core/memory/skill_store.py` persists typed skills (parameter
overrides, printer quirks, material quirks, scheduling preferences,
user preferences, failure patterns) with confidence scoring,
evidence counts, and scope-tagged lookup.

## §32  Local LLM (Ollama)

`core/llm/ollama_client.py` is a graceful Ollama HTTP wrapper. Every
LLM call is OPTIONAL — when Ollama is unreachable, the system falls
back to deterministic logic. No external services, no API keys.

## §33  Multi-Agent (Critic / Optimizer / Executor)

`core/agents/multi_agent.py` runs a 3-agent loop: Critic reviews a
dispatch decision against history+skills, Optimizer revises the
request when asked, Executor runs the workflow when approved.

## §34  OctoPrint Bridge

`core/integrations/octoprint_client.py` mirrors the Moonraker client
shape. Same dispatcher, same orchestrator — just a different transport.

## §35  Obico Failure Detection

`core/integrations/obico_client.py` polls a self-hosted Obico instance
for spaghetti-detection probability and recommends OK / HEADS_UP /
PAUSE / CANCEL based on tunable thresholds.

## §36  Failure Prediction

`core/intelligence/failure_predictor.py` blends printer-history,
material-history, and skill signals into a calibrated failure
probability + confidence label + citation list.

---

## §37  Definition of Done

A feature is DONE when:

- [ ] Code lives under `03_implementation/src/hermes3d/`
- [ ] Has a corresponding test under `04_testing/pytest/`
- [ ] All tests in the kit pass
- [ ] No `TODO`/`STUB`/`NOT_IMPLEMENTED` in shipped code
- [ ] Lint + typecheck clean (zero warnings)
- [ ] CLI surface or REST endpoint exists for it (when relevant)
- [ ] Documented in this file (a numbered §)
- [ ] Listed in `KIT_MANIFEST.json` with `status: runnable`
- [ ] Listed in `HONESTY_LEDGER.md` in the runnable column

Anything that fails the bar lives under "spec" with explicit notes
about what's missing — never under runnable.

---

## §38  What Is NOT in this Kit (Deliberately)

- A silent fork of OrcaSlicer or PrusaSlicer. Hermes3D may keep
  source-backed upstream checkouts and drive real CLIs/apps, but it
  must not present a hand-drawn or invented slicer as the real slicer.
- A G-code generator (we use the slicer)
- A Klipper firmware fork (we ship config + macros only)
- Cloud printer management (Bambu Cloud, Creality Cloud — not used)
- Telemetry to any external service
- Required network connections (everything works on a LAN)

---

## §39  Versioning & Compatibility

- Schema versions are explicit in every persistent JSON file
- Schema mismatches refuse to load (no silent migrations)
- The Truth Gate report schema is frozen at `1.0.0`; new checks add
  records, never break existing fields
- Proof Envelopes signed under one HMAC key cannot be re-verified under
  a different key — verifiers must use the same key as the writer
