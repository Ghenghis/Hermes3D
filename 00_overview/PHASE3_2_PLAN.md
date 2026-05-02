Phase 3.2 — Planner Agent + 3D Generation Read-Only Slice
Status: design only · no code · no commits.
Architecture references: 02_architecture/adr/ADR-008-adapter-lifecycle-and-dock-undock.md, 02_architecture/adr/ADR-009-orchestration-skeleton.md.
Branch: feat/phase-3-2-planner-readonly (forks from develop after Phase 3.1 merge).

1. Objective
Add a Planner agent that converts a user prompt into a typed task DAG, and ship a 3D Generation read-only / simulated executor that consumes the first DAG node end-to-end. Prove the Planner→DAG→Executor seam with proof + ledger evidence, without granting any write capability. Smaller than Phase 3.1 (no new live adapter/provider surface; CP3.2-D adds localhost-only preview/read routes — just one agent + one simulated executor + DAG primitives).

The slice ends with a UI affordance on the 3D Generation tab that submits a prompt, the Planner emits a DAG, the simulated executor "produces" a deterministic stub model, and the result flows back through the existing AdapterAPI swap point. No external provider is contacted; no slicer or Blender or printer is invoked.

2. Strict out-of-scope
The following are explicitly NOT in Phase 3.2. Each requires its own ADR + checkpoint:

Real 3D-generation provider calls (TRELLIS / Hunyuan3D / TripoSR / MiniMax) — simulated stub only.
Blender MCP execution — no bridge tools invoked, no .3mf exported.
Slicer execution (PrusaSlicer / OrcaSlicer / FLSUN / Cura) — no subprocess.
Printer adapters of any kind — Fleet read-only stays as Phase 3.1 ships it.
Mesh QA / Slicer QA agents — placeholders in DAG only, never dispatched.
Repair agent — failures bubble up as Err and surface in the UI; no auto-repair.
Releaser / Auditor — proof bundle is assembled by the existing CP3.1-style pipeline; no agent involvement.
Native windows / BrowserWindow / WebView / iframes — none.
LLM gateway with cost cap — Planner is a deterministic stub in Phase 3.2 (uses a fixture template). The real LLM call ships in Phase 3.3.
Write capability of any kind — Phase-4 boundary unchanged.
Cancellation propagation across nodes — supervisor accepts a single Cancel (already in CP3.1 contract); per-node cancellation semantics ship later.
3. Files / modules to create or modify
Python (orchestration + agents)
Path	Status	Purpose
00_overview/PHASE3_2_PLAN.md	new	this plan
02_architecture/adr/ADR-010-planner-and-dag.md	new	DAG schema, Planner contract, simulated-executor boundary, capability-token shape extension
03_implementation/src/hermes3d/orchestration/dag.py	new	TaskNode, TaskDAG, topological walker; pure data + algorithm, no I/O
03_implementation/src/hermes3d/orchestration/types.py	modify (additive)	new DTOs: PlanRequest, PlanResult, Gen3DRequest, Gen3DResult, SimulatedModelArtifact (deterministic content-addressable stub)
03_implementation/src/hermes3d/orchestration/supervisor.py	modify (additive)	dispatch_plan(req, token) + dispatch_gen3d(req, token); per-DAG-run mutex; tokens scoped to planner.plan and gen3d.generate only
03_implementation/src/hermes3d/agents/planner.py	new	Planner agent: takes PlanRequest, returns PlanResult{ dag: TaskDAG }. Phase 3.2 is deterministic-template-based, not LLM-driven
03_implementation/src/hermes3d/agents/gen3d_executor.py	new	Simulated 3D executor; produces a SimulatedModelArtifact whose sha256 is derived from the request, written under var/orchestration/artifacts/<sha>.json
03_implementation/src/hermes3d/orchestration/bridge.py	modify (additive)	new route POST /api/plan/preview (accepts {prompt}, returns the DAG only — does NOT dispatch); new route GET /api/runs/<run_id> (returns ledger-derived run summary). Both routes still localhost-bound. No execution route in Phase 3.2.
03_implementation/src/hermes3d/adapters/_capabilities.py	modify (additive)	add capability flags plan_dag, gen3d_simulate; both flagged phase=3 and dangerous=False
UI (mock-only surfaces; one new live read)
Path	Status	Purpose
03_implementation/ui/src/api/adapters.ts	modify	add planPreview(prompt: string): Promise<TaskDAG> to AdapterAPI; resolver picks mock vs live
03_implementation/ui/src/api/adapters.live.ts	modify	add live planPreview → POST 127.0.0.1:<port>/api/plan/preview with response shape validation
03_implementation/ui/src/types/dag.ts	new	TS mirror of dag.py types (TaskNode, TaskDAG)
03_implementation/ui/src/data/mock/dag.ts	new	deterministic fixture DAG used in mock mode
03_implementation/ui/src/tabs/Gen3D.tsx	modify	add a "Preview plan" button that calls planPreview(prompt) and renders the returned DAG inside the existing pipeline visualization (which already exists). The "Generate" button stays LockedAction — Phase 3.2 does not execute the DAG from the UI
Tests / fixtures
Path	Status	Purpose
04_testing/pytest/unit/orchestration/test_dag.py	new	DAG construction, topological walk, cycle rejection, max-depth cap
04_testing/pytest/unit/orchestration/test_supervisor_plan_dispatch.py	new	dispatch_plan enforces tokens, ledger writes, cycle rejection
04_testing/pytest/unit/agents/test_planner.py	new	deterministic DAG output for fixture prompts; refusal to plan unsafe nodes
04_testing/pytest/unit/agents/test_gen3d_simulated.py	new	sha-determinism, refuses any non-gen3d.generate tool
04_testing/pytest/integration/test_plan_preview_roundtrip.py	new	bridge POST /api/plan/preview + GET /api/runs/<id>; assert no execution side effect
04_testing/playwright_ui/tests/visual/gen3d.plan_preview.spec.ts	new	UI live-mode test: type prompt → click Preview plan → DAG renders; no other side effects
04_testing/fixtures/planner/prompts.json	new	deterministic prompt → DAG fixtures used by both Python and Playwright tests
CI
Path	Status	Purpose
.github/workflows/ui-ci.yml	modify	extend layer_d2_live_smoke path filter to include agents/planner.py, agents/gen3d_executor.py, orchestration/dag.py, the new test files. No new job. Existing live-smoke job runs the new gen3d.plan_preview spec
4. Checkpoint breakdown
CP3.2-A → CP3.2-B → CP3.2-C → CP3.2-D → CP3.2-E. Strict serial. Architect review at A, C, D, E.

CP3.2-A — Plan + ADR-010
Commit PHASE3_2_PLAN.md (this document).
Commit ADR-010-planner-and-dag.md defining: DAG schema (typed nodes, edges, retry budget, gate set), Planner deterministic-template contract, simulated executor boundary, capability-token extension (no new fields, just new tools values), refusal rule R6 (Planner cannot emit a node whose tool is not in the registered tool set).
CP3.2-B — DAG + types (offline)
orchestration/dag.py + new DTOs in types.py.
Unit tests for DAG construction, topological walk, cycle rejection, max-depth ≤ 12 (matches DTE 12-stage template), max-fanout cap.
No supervisor changes yet, no agent yet.
CP3.2-C — Planner + simulated Gen3D + supervisor wiring
agents/planner.py, agents/gen3d_executor.py, supervisor.dispatch_plan + dispatch_gen3d, _capabilities.py additions.
Unit tests for token enforcement on the new dispatchers; ledger emits two new event kinds: planner.plan and gen3d.generate.
Integration test: prompt → DAG → simulated artifact, fully offline; artifact sha is deterministic.
CP3.2-D — Bridge + UI live-mode plan preview
bridge.py adds POST /api/plan/preview (request body validated, response is DAG only — no execution) and GET /api/runs/<id> (read from ledger).
adapters.ts + adapters.live.ts add planPreview.
Gen3D.tsx adds the "Preview plan" button + DAG render via the existing WorkflowPipeline primitive. "Generate" stays locked.
Playwright live-mode spec gen3d.plan_preview.spec.ts: prompt → click → DAG renders the Phase-3.2 fixture.
CP3.2-E — Proof bundle + completion report + PR
Re-use phase3_1_proof.py adapted as phase3_2_proof.py (or add a --phase 3.2 switch — preference: standalone for clarity).
Bundle contents: PHASE3_2_PLAN.md, ADR-010, ledger snapshot (now including planner.plan + gen3d.generate events), Playwright JSON, UI build hash, plan-preview replay log.
Completion report mirrors Phase 3.1's structure.
PR Phase 3.2 — Planner + simulated 3D to develop. HARD STOP.
5. Safety gates per checkpoint
Checkpoint	Gate	Enforced by
CP3.2-A	Plan declares zero write capability; ADR-010 forbids LLM I/O in 3.2; ADR-010 adds refusal rule R6 (Planner cannot emit node with unregistered tool)	architect review of doc text
CP3.2-B	DAG cycle test red-greens; max-depth cap rejects > 12; supervisor refuses plan dispatch without registered tool set	unit tests test_dag.py
CP3.2-C	Token enforcement: dispatch_plan and dispatch_gen3d honor R1-R5 + new R6; gen3d_executor refuses any tool ≠ gen3d.generate; simulated artifact path lives under var/orchestration/artifacts/ only (no escape); ledger row written per dispatch with input/output sha	unit + integration tests
CP3.2-D	Bridge POST /api/plan/preview is plan-only (no execution side effect, asserted by integration test that polls ledger after preview and confirms zero gen3d.generate events); bridge still localhost-bound; GET /api/runs/<id> is read-only and returns 404 for unknown ids; UI planPreview validates response shape; UI "Generate" button remains LockedAction	integration test test_plan_preview_roundtrip.py + Playwright spec + grep audit on Gen3D.tsx for absent execute path
CP3.2-E	Proof bundle honesty diff green; completion report references actual paths; no write capability anywhere; source-pattern audit (Phase 0 scanner) re-runs clean over orchestration/, agents/, ui/src/	Layer F honesty gate + bundle verifier
Phase 3.1 boundaries preserved exactly: Moonraker read-only adapter unchanged, fleet bridge unchanged, capability-token model unchanged (only the tools vocabulary grows).

6. Test plan
Layer A — static gates
ruff format/check on orchestration/dag.py, agents/planner.py, agents/gen3d_executor.py, new tests.
Forbidden-pattern scanner extended to fail any new orchestration/agent module that imports subprocess, socket, openai, anthropic, requests (Planner is template-only in 3.2; LLM imports come in 3.3).
Adapter-manifest validator refuses any new flag with phase>=4.
Layer B — unit
Test	Asserts
test_dag.py	construction, topo walk order, cycle → Err::CycleDetected, depth > 12 → Err::DAGTooDeep, fanout cap
test_supervisor_plan_dispatch.py	tokenless plan dispatch → R1; wrong-tool token → R3; expired → R4; phase violation → R5; unregistered tool in DAG → R6; ledger row written with verdict=pass|fail
test_planner.py	fixture prompt set → deterministic DAG (sha-stable); refuses to emit a node with tool="printer.write" or any write-class tool name
test_gen3d_simulated.py	gen3d.generate returns SimulatedModelArtifact with sha derived from (prompt, seed); refuses other tools; artifact written only under var/orchestration/artifacts/
test_capabilities_manifest.py (extend)	new flags plan_dag + gen3d_simulate are phase=3, dangerous=False; manifest with these alongside phase>=4 is refused
Layer C — integration
Test	Asserts
test_plan_preview_roundtrip.py	bridge POST /api/plan/preview returns the planner's DAG; ledger gains exactly one planner.plan event and zero gen3d.generate events; GET /api/runs/<id> returns the run summary; non-localhost client → 403
Layer D2 — UI
Test	Asserts
dashboard.visual.spec.ts	unchanged (still platform-skipped on Linux)
dock.spec.ts	unchanged
fleet.live.spec.ts	unchanged
gen3d.plan_preview.spec.ts (new)	prompt input → "Preview plan" click → DAG renders with N nodes from fixture; "Generate" button still has aria-disabled="true"; zero non-localhost network requests; no popup/window-open attempts
Source-pattern audit (extends Phase 2 + Phase 3.1)
child_process | spawn | exec | execSync | execFile | openExternal | shell.openPath | window.open | shell\. | process\. in ui/src/ and 03_implementation/src/hermes3d/{orchestration,agents} → 0 matches.
New: import openai | import anthropic | import requests in agents/ → 0 matches (Phase 3.2 has no LLM calls).
7. CI / proof expectations
CI
No new job. layer_d2_live_smoke is reused.
layer_d2_live_smoke boots fixture Moonraker + bridge as today; the new gen3d.plan_preview.spec.ts runs in the same npx playwright test invocation as fleet.live.spec.ts.
ui-ci.yml path filter extends to:
03_implementation/src/hermes3d/agents/**
03_implementation/src/hermes3d/orchestration/dag.py
04_testing/fixtures/planner/**
04_testing/pytest/unit/agents/**
04_testing/pytest/integration/test_plan_preview_roundtrip.py
Layer A static gates run on the new Python modules. Layer B unit tests run in the existing matrix.
Proof bundle
Path: 06_release/phase3.2-bundle/<head>-<utc>.zip
Manifest entries (exactly seven):
docs/PHASE3_2_PLAN.md
docs/ADR-010-planner-and-dag.md
evidence/ledger_snapshot.sqlite3
evidence/plan_preview_replay.json
evidence/playwright_report.json
evidence/ui_build_output_hash.json
evidence/dag_fixture_replay.json (new — deterministic prompt-to-DAG mappings used by tests)
sha256 sidecar + manifest JSON sit beside the zip.
Honesty diff (Layer F) confirms manifest matches zip exactly.
8. Definition of "done"
Phase 3.2 is done iff all of the following hold:

#	Criterion	Measure
1	Planner agent emits deterministic DAGs from prompt fixtures	test_planner.py green; same prompt → identical DAG sha across runs
2	Simulated 3D executor produces deterministic artifacts	test_gen3d_simulated.py green; artifact sha derived from request fields
3	DAG primitives reject cycles + over-deep graphs	test_dag.py green
4	Supervisor enforces R1-R6 on the new dispatchers	test_supervisor_plan_dispatch.py green
5	Bridge POST /api/plan/preview does NOT execute	integration test asserts zero gen3d.generate events after preview
6	Bridge stays localhost-only; new routes refuse non-loopback clients	integration test green
7	UI live-mode preview renders the planner's DAG	gen3d.plan_preview.spec.ts green
8	UI "Generate" button remains LockedAction	grep audit on Gen3D.tsx for LockedAction label="Generate" returns ≥ 1
9	Phase 3.1 specs still pass unmodified	full Playwright suite green; fleet.live.spec.ts unchanged
10	Source-pattern audit clean	new patterns (openai|anthropic|requests in agents/) zero matches; existing patterns still zero
11	Proof bundle honest	sha-rollup matches manifest exactly; honesty-diff green
12	Architect review PASS at CP3.2-A, CP3.2-C, CP3.2-D, CP3.2-E	review verdicts in chat
When all 12 hold, Phase 3.2 PR is opened to develop and Phase 3.3 (real LLM-driven Planner + 3D-provider gateway) becomes the next planning candidate — under its own ADR and its own architect approval. Phase 4 (write actions) does not unlock until Phase 3.3 + 3.4 (Blender MCP read + slicer dry-run) ship.
