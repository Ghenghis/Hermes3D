# FEATURES — Hermes3D-OS Lite v5

> Inventory of what this kit actually does. Each row carries a tier
> annotation that matches `HONESTY_LEDGER.md`:
>
> - **runnable** — code exists, tests pass, behaviour is real
> - **scaffold** — code exists with structure and stubs documented as
>   such, intended for v5.x promotion
> - **spec** — described in contract or schema only; not yet
>   implemented
>
> The honesty ledger is the source of truth; this document mirrors it
> for readability.

---

## Fleet management

| Feature | Tier | Module |
|---------|------|--------|
| 12 verified printer profiles (6 delta, 4 cartesian, 2 CoreXY) | runnable | `core.printers.printer_profiles` |
| Bed-shape geometry (rectangular + circular delta) | runnable | `core.printers.printer_profiles.BedShape` |
| Moonraker REST client with health probe | runnable | `core.printers.moonraker_client` |
| Live fleet status aggregation | runnable | `core.farm.dashboard.collect_fleet_status` |
| Filament spool tracker with consumption ledger | runnable | `core.farm.spool_tracker` |
| Per-print cost estimator (filament + power) | runnable | `core.farm.cost_estimator` |
| Print history (JSON-backed, queried by predictor) | runnable | `core.farm.print_history` |
| Backup orchestrator for `./var/` | runnable | `core.farm.backup` |
| Per-printer calibration history view | scaffold | `core.farm.dashboard` (UI tab pending) |

## Dispatcher and decision logic

| Feature | Tier | Module |
|---------|------|--------|
| 8 dispatch strategies (auto/fastest/quality/largest_bed/smallest_fit/least_busy/delta_prefer/cartesian_prefer) | runnable | `core.agents.dispatcher` |
| Material-eligibility checks (TPU → direct drive only; ASA/PC → enclosed only; etc.) | runnable | `core.agents.materials` + `dispatcher` |
| Bed-fit checks (rectangular bbox + delta xy-circle) | runnable | `core.printers.printer_profiles.fits_bed` |
| Live state inputs (idle vs printing) | runnable | `core.printers.moonraker_client.probe_fleet` |
| Excluded-printers filter (UI integration) | runnable | `DispatchRequest.excluded_printers` |

## Truth gates and proof envelopes

| Feature | Tier | Module |
|---------|------|--------|
| 8-gate truth check (schema/geometry/bed/material/skill/spool/health/workflow) | runnable | `core.validation.truth_gate` |
| HMAC-SHA256 signed proof envelopes | runnable | `core.proof.proof_envelope` |
| Acceptance-runner produces signed envelopes per printer/variant | runnable | `04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py` |
| Batch envelope verifier | runnable | `03-PROOF-SYSTEM/conformance_runner.py` |

## Slicer integration

| Feature | Tier | Module |
|---------|------|--------|
| PrusaSlicer / OrcaSlicer CLI runner | runnable | `core.slicer.slicer_runner` |
| G-code post-process metadata extraction | runnable | `core.slicer.gcode_analyzer` |
| Per-printer/material profile derivation | runnable | `core.slicer.profile_generator` |
| G-code post-process injection (timestamps, telemetry) | runnable | `core.slicer.postproc_generator` |

## Workflow orchestration

| Feature | Tier | Module |
|---------|------|--------|
| 12-node print workflow with atomic JSON checkpointing | runnable | `core.orchestration.print_workflow` |
| Linear graph executor with PASS/FAIL/SKIP/RETRY outcomes | runnable | `core.orchestration.agent_graph` |
| LangGraph source export | runnable | `core.orchestration.langgraph_adapter` |
| LangGraph runtime adapter | spec | (depends on `langgraph` package) |
| DryRun state machine | runnable | `core.agents.orchestrator` |

## Memory and skills

| Feature | Tier | Module |
|---------|------|--------|
| Skill store (5 kinds) with confidence + scope matching | runnable | `core.memory.skill_store` |
| Skill-pack import/export bundles (hash-verified) | runnable | `core.memory.skill_pack` |
| Vector memory (TF-IDF + optional FAISS) | runnable | `core.memory.vector_memory` |
| Self-improvement loop (reinforce/weaken/propose-new) | runnable | `core.intelligence.self_improvement` |

## Multi-agent + LLM

| Feature | Tier | Module |
|---------|------|--------|
| Multi-LLM provider abstraction (5 backends) | runnable | `core.llm.providers` |
| Ollama HTTP client with graceful unavailability | runnable | `core.llm.ollama_client` |
| Critic / Optimiser / Executor agent loop | runnable | `core.agents.multi_agent` |
| Failure-pattern predictor blending skills + history | runnable | `core.intelligence.failure_predictor` |
| Quality scorer (5 dimensions, explainable) | runnable | `core.agents.quality_scorer` |

## Tools, automation, supervisor

| Feature | Tier | Module |
|---------|------|--------|
| Tool registry with decorator-based registration | runnable | `core.agents.tool_registry` |
| 11 built-in tools wired to real backends | runnable | `core.agents.tool_registrations` |
| Incident detector (9 incident types) | runnable | `core.agents.incident_detector` |
| Supervisor daemon (event listeners, auto-skill creation) | runnable | `core.supervisor.daemon` |
| Mesh repair (watertight reconstruction) | runnable | `core.agents.mesh_repair` |
| Mesh analyser (overhang, bridges, thin walls) | runnable | `core.agents.mesh_analyzer` |
| Auto-orient (Z-up + minimise overhang) | runnable | `core.agents.auto_orient` |
| Auto-recovery (resume after failure if safe) | runnable | `core.agents.auto_recovery` |
| Parallel print planner (multi-printer same job) | runnable | `core.agents.parallel_planner` |
| Equivalence checker (pre/post slicer) | runnable | `core.agents.equivalence` |
| Pre-flight checklist | runnable | `core.agents.preflight` |
| Calibration macro lookup (read-only) | runnable | `core.agents.calibration` |

## Integrations

| Feature | Tier | Module |
|---------|------|--------|
| OctoPrint client | runnable | `core.integrations.octoprint_client` |
| Obico client | runnable | `core.integrations.obico_client` |
| Telegram + Discord remote control bridge | runnable | `core.integrations.remote_control` |
| Farm auto-discovery (Moonraker/Mainsail/Fluidd/OctoPrint/Obico) | runnable | `core.integrations.farm_discovery` |

## Surface APIs

| Feature | Tier | Module |
|---------|------|--------|
| FastAPI REST server (10 endpoints) | runnable | `api.server` |
| Hand-rolled MCP stdio server (16 tools) | runnable | `api.mcp_server` |
| `hermes3d` CLI (fleet/validate/dispatch/slice/queue/spool/proof) | runnable | `cli.__main__` |

## UI

| Feature | Tier | Module |
|---------|------|--------|
| Gradio launcher with multi-tab control panel | runnable | `app.launcher` |
| Job queue viewer | runnable | `app.launcher` (tab) |
| Print farm dashboard tab | scaffold | (Tier-2 dashboards pending integration) |
| Dispatch (agentic) tab | scaffold | (relies on tool_registrations) |
| Tool registry browser tab | scaffold | (Tier-2) |
| Skill memory browser tab | scaffold | (Tier-2) |
| Incident log tab | scaffold | (Tier-2) |
| Remote control test tab | scaffold | (Tier-2) |
| LLM provider switcher | scaffold | (Tier-2) |

## Notifications

| Feature | Tier | Module |
|---------|------|--------|
| Notifier with 4 typed events | runnable | `core.notifications.notifier` |
| Telegram + Discord webhook channels | runnable | (via `remote_control` config) |

## Built-in skill packs

| Pack | Tier | Path |
|------|------|------|
| `flsun_t1_essentials` | runnable | `config/skill_packs/flsun_t1_essentials.json` |
| `tronxy_d01_quirks` | runnable | `config/skill_packs/tronxy_d01_quirks.json` |
| `asa_general_tips` | runnable | `config/skill_packs/asa_general_tips.json` |

---

## Counts (as of v5)

- Runnable modules under `src/hermes3d/core/`: ≥ 35
- Built-in tools registered: 11 (via `tool_registrations`) + 16 (via MCP server)
- Truth-gate checks: 8
- Dispatch strategies: 8
- Skill kinds: 6 (parameter_override, printer_quirk, material_quirk, scheduling_pref, user_preference, failure_pattern)
- Incident types: 9
- LLM provider backends: 5
- Acceptance test variants × printers: 48 (4 × 12), all green with signed proofs
- Tests: 264 passing in ~13 seconds

The current honesty ledger is at `00-CONTRACT/HONESTY_LEDGER.md`.
