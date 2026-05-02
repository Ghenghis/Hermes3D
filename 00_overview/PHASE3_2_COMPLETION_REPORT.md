# Phase 3.2 Completion Report

**Branch:** `feat/phase-3-2-planner-readonly`
**Base:** `origin/develop`
**Scope:** Planner + DAG read-only slice
**Status:** ready for PR after CP3.2-E closeout

## Scope Summary

Phase 3.2 adds the planner + DAG read-only slice. The slice includes the
Phase 3.2 plan and ADR-010, pure DAG primitives, type-only orchestration DTOs,
a deterministic template Planner agent, a simulated Gen3D executor, supervisor
dispatch paths for `planner.plan` and `gen3d.generate`, a localhost-only plan
preview bridge route, and a UI live-mode plan preview flow.

No real LLM gateway, real 3D provider, slicer, Blender, printer write, native
window, external process, or Phase 3.3 capability is introduced.

## Commit List

Captured before the CP3.2-E closeout commit with:

```bash
git log origin/develop..HEAD --oneline
```

```text
8ccf241 feat(phase3.2): add plan preview bridge and UI flow
0660776 fix(phase3.2): normalize supervisor token validation and handler types
73a396b feat(phase3.2): add planner and simulated Gen3D executor
5cd31f0 feat(phase3.2): add DAG primitives and types
fe488ca feat(phase3.2): add planner + DAG plan and ADR
```

The CP3.2-E closeout commit adds this report, the proof assembler, and the
generated proof bundle.

## Files Touched

Branch diff summary before this closeout report/bundle was added:

```text
00_overview/PHASE3_2_PLAN.md                       | 152 +++++++++++++
02_architecture/adr/ADR-010-planner-and-dag.md     | 166 ++++++++++++++
03_implementation/src/hermes3d/adapters/_capabilities.py | 18 ++
03_implementation/src/hermes3d/agents/gen3d_executor.py | 75 +++++++
03_implementation/src/hermes3d/agents/planner.py   | 114 ++++++++++
03_implementation/src/hermes3d/orchestration/__init__.py | 16 ++
03_implementation/src/hermes3d/orchestration/bridge.py | 119 ++++++++++-
03_implementation/src/hermes3d/orchestration/dag.py | 147 +++++++++++++
03_implementation/src/hermes3d/orchestration/supervisor.py | 238 ++++++++++++++++++---
03_implementation/src/hermes3d/orchestration/types.py | 53 ++++-
03_implementation/ui/src/api/adapters.live.ts      | 117 ++++++++++
03_implementation/ui/src/api/adapters.ts           | 7 +-
03_implementation/ui/src/data/mock/dag.ts          | 27 +++
03_implementation/ui/src/tabs/Gen3D.tsx            | 97 ++++++++-
03_implementation/ui/src/types/dag.ts              | 25 +++
03_implementation/ui/tests/visual/gen3d.plan_preview.spec.ts | 75 +++++++
04_testing/pytest/integration/test_plan_preview_roundtrip.py | 102 +++++++++
04_testing/pytest/unit/adapters/test_capabilities_manifest.py | 17 ++
04_testing/pytest/unit/agents/__init__.py          | 1 +
04_testing/pytest/unit/agents/test_gen3d_simulated.py | 70 ++++++
04_testing/pytest/unit/agents/test_planner.py      | 74 +++++++
04_testing/pytest/unit/orchestration/test_dag.py   | 149 +++++++++++++
04_testing/pytest/unit/orchestration/test_supervisor_plan_dispatch.py | 171 +++++++++++++++
23 files changed, 1994 insertions(+), 36 deletions(-)
```

CP3.2-E closeout files:

- `00_overview/PHASE3_2_COMPLETION_REPORT.md`
- `02_architecture/scripts/scaffolding/phase3_2_proof.py`
- `06_release/phase3.2-bundle/8ccf241bd6f1-20260501T235342Z.zip`
- `06_release/phase3.2-bundle/8ccf241bd6f1-20260501T235342Z.manifest.json`
- `06_release/phase3.2-bundle/8ccf241bd6f1-20260501T235342Z.sha256`

## Gate Results

Run from repo root:

```bash
python -m ruff check 03_implementation/src/hermes3d 04_testing/pytest
python -m pytest 04_testing/pytest/unit/orchestration 04_testing/pytest/unit/adapters 04_testing/pytest/unit/agents 04_testing/pytest/integration -q
```

Results:

- `ruff check`: PASS
- `pytest`: PASS, 224 tests

Run from `03_implementation/ui`:

```bash
npm run lint
npm run build
npx playwright test
```

Results:

- `npm run lint`: PASS (`tsc --noEmit`)
- `npm run build`: PASS, 2412 modules transformed
- Build outputs: `index.html` 0.42 kB, CSS 20.36 kB / gzip 4.75 kB, JS 682.77 kB / gzip 184.83 kB
- `npx playwright test`: PASS, 11 tests in 12.0s
- Specs: `dashboard.visual.spec.ts`, `dock.spec.ts`, `fleet.live.spec.ts`, `gen3d.plan_preview.spec.ts`

Playwright JSON report was regenerated for the proof bundle with:

```bash
npx playwright test --reporter=json
```

Result: PASS, 11 tests in 12.2s.

## Safety Audit

Planner determinism:

- `PlannerAgent` is fixture-template only.
- Fixture prompts `calibration cube` and `mini vase` produce stable DAG payloads.
- Planner tests assert stable DAG IDs for repeated prompts.
- Planner source tests assert no `openai`, `anthropic`, or `requests` imports.

R1-R6 enforcement:

- R1 tokenless dispatch is refused.
- R2 replayed/unknown token is refused.
- R3 wrong-tool token is refused.
- R4 expired token is refused.
- R5 phase violation is refused.
- R6 unregistered DAG tool is refused before dispatch.
- Supervisor token flow is normalized to one validation + one consume path via `_validate_and_consume_token()`.

No execution during preview:

- `POST /api/plan/preview` returns DAG data only.
- Integration tests assert exactly one `planner.plan` ledger event for preview.
- Integration tests assert zero `gen3d.generate` events after preview.
- Integration tests assert no simulated artifact directory is created by preview.
- UI "Generate" remains a disabled `LockedAction`.

Read-only and locality boundaries:

- Bridge remains localhost-only.
- Non-localhost bridge clients get 403.
- `GET /api/runs/{run_id}` is read-only and returns 404 for unknown runs.
- UI live mode posts only to `http://127.0.0.1:<port>/api/plan/preview`.

## Proof Bundle

Bundle path:

```text
06_release/phase3.2-bundle/8ccf241bd6f1-20260501T235342Z.zip
```

SHA-256:

```text
d351a229b25e03470e307d3ad9412aa455b0d859472ec3dac175ea52f555ab86
```

Included files:

```text
docs/ADR-010-planner-and-dag.md
docs/PHASE3_2_PLAN.md
evidence/dag_fixture_replay.json
evidence/ledger_snapshot.sqlite3
evidence/plan_preview_replay.json
evidence/playwright_report.json
evidence/ui_build_output_hash.json
```

Verification:

```text
entries=7
missing=[]
extra=[]
mismatches=[]
```

## Known Follow-ups

- LLM planner (Phase 3.3)
- Real 3D providers

## References

- `02_architecture/adr/ADR-010-planner-and-dag.md`
- `00_overview/PHASE3_2_PLAN.md`

## Stop Point

CP3.2-E closes Phase 3.2. Phase 3.3 has not started.
