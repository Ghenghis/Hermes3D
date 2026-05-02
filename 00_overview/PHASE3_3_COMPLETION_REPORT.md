# Phase 3.3 Completion Report

## Scope Summary

Phase 3.3 adds the bounded LLM Planner Gateway slice. The gateway is the only
Phase 3.3 boundary for LLM-style completion, and it enforces policy loading,
prompt sanitization, redaction, token checks, budget checks, retry limits, and
deterministic fallback behavior before the planner accepts any suggestion.

The deterministic template planner remains the authority. LLM mode can suggest a
fixture prompt, but every accepted output is normalized through the existing
TaskDAG path. Invalid, malformed, over-budget, missing-caller, or unsafe LLM
paths fall back to the deterministic template DAG and record `planner.fallback`
ledger evidence.

The bridge HTTP surface remains unchanged. `POST /api/plan/preview` still
returns a DAG-only preview and now carries `metadata.planner_mode`; `GET
/api/runs/{run_id}` remains read-only. The UI change is limited to the existing
3D Generation tab, where a small mode badge displays either `via LLM` or
`template` from the validated DAG metadata.

The proof bundle generated for this closeout includes the Phase 3.3 plan,
ADR-011, a SQLite ledger snapshot, redacted LLM trace samples, plan-preview
replay, Playwright JSON, and UI build output hashes. The verifier checks manifest
honesty, required ledger event rows, and redaction invariants.

Out of scope: real 3D providers, provider probes, provider chips, Blender MCP,
slicer dry-run, streaming LLM responses, function-calling LLM mode, new bridge
routes, new tabs, external process launch, and Phase 4 write capability.

## Commit List

Captured with:

```bash
git log origin/develop..HEAD --oneline
```

```text
4ae1607 feat(phase3.3): surface planner_mode in bridge envelope + UI badge (CP3.3-D)
8de7eb7 feat(phase3.3): integrate LLM planner mode with safe fallback (CP3.3-C)
a213718 feat(phase3.3): integrate LLM planner mode with safe fallback
8845089 fix(phase3.3): rework CP3.3-B to canonical gateway contract
b0bacc8 feat(phase3.3): implement LLM planner gateway fallback path
918e5f1 feat(phase3.3): add LLM planner gateway plan and ADR
```

The CP3.3-E closeout commit adds this report, the proof assembler, the generated
proof bundle, and the PR body.

## Files Touched

Captured with:

```bash
git diff origin/develop..HEAD --stat
```

```text
00_overview/PHASE3_3_PLAN.md                       | 238 +++++++++++++++++
02_architecture/adr/ADR-011-llm-planner-gateway.md | 173 ++++++++++++
03_implementation/config/llm_policy.schema.json    |  99 +++++++
03_implementation/config/llm_policy.yaml           |  12 +
.../src/hermes3d/adapters/_capabilities.py         |   1 +
03_implementation/src/hermes3d/agents/planner.py   | 181 ++++++++++++-
.../src/hermes3d/gateways/__init__.py              |  27 ++
03_implementation/src/hermes3d/gateways/budget.py  | 135 ++++++++++
03_implementation/src/hermes3d/gateways/llm.py     | 289 +++++++++++++++++++++
.../src/hermes3d/gateways/redaction.py             | 112 ++++++++
.../src/hermes3d/gateways/sanitize.py              |  49 ++++
.../src/hermes3d/orchestration/bridge.py           |   5 +-
.../src/hermes3d/orchestration/supervisor.py       |  80 +++++-
.../src/hermes3d/orchestration/types.py            |  24 ++
03_implementation/src/hermes3d/planner/__init__.py |   5 +
.../src/hermes3d/planner/llm_adapter.py            |  25 ++
03_implementation/ui/src/tabs/Gen3D.tsx            |  19 ++
03_implementation/ui/src/types/dag.ts              |   2 +-
.../ui/tests/visual/gen3d.planner_mode.spec.ts     | 126 +++++++++
04_testing/fixtures/llm/__init__.py                |   5 +
04_testing/fixtures/llm/responses.json             |  34 +++
04_testing/fixtures/llm/server.py                  |  39 +++
.../test_bridge_plan_preview_envelope.py           |  29 +++
.../test_planner_llm_fallback_roundtrip.py         | 189 ++++++++++++++
04_testing/pytest/unit/gateways/__init__.py        |   1 +
04_testing/pytest/unit/gateways/test_budget.py     |  98 +++++++
.../pytest/unit/gateways/test_llm_gateway.py       | 243 +++++++++++++++++
04_testing/pytest/unit/gateways/test_redaction.py  |  62 +++++
04_testing/pytest/unit/gateways/test_sanitize.py   |  54 ++++
.../pytest/unit/planner/test_llm_integration.py    | 216 +++++++++++++++
30 files changed, 2565 insertions(+), 7 deletions(-)
```

## Gate Results

- `python -m ruff check 03_implementation/src/hermes3d 04_testing/pytest 02_architecture/scripts/scaffolding/phase3_3_proof.py`: PASS.
- `cd 03_implementation && python -m pytest ../04_testing/pytest -q`: PASS, 633 tests.
- `cd 03_implementation/ui && npm run lint`: PASS (`tsc --noEmit`).
- `cd 03_implementation/ui && npm run build`: PASS, 2412 modules transformed.
- UI build outputs: `index.html` 0.42 kB / gzip 0.29 kB, CSS 20.36 kB / gzip 4.75 kB, JS 683.33 kB / gzip 184.94 kB.
- `cd 03_implementation/ui && npx playwright test --reporter=list`: PASS, 13 tests in 14.3s.
- `cd 03_implementation/ui && npx playwright test --reporter=json > playwright-report.json`: PASS, JSON report contains 13 passed tests.

## Safety Audit

### Planner determinism

The template path remains deterministic and is still the default mode in
`03_implementation/config/llm_policy.yaml`. LLM mode can suggest only fixture
planner prompts; accepted LLM output is routed back through the deterministic
planner path, and fallback DAGs carry `metadata.planner_mode="template"`.

### R1-R8 enforcement

R1-R5 continue through capability-token validation. R6 remains the TaskDAG
registered-tool check. R7 is enforced at `llm.complete` token issuance and inside
`LLMGateway.complete`, with `budget.exceeded` ledger evidence. R8 is enforced by
planner validation; malformed or unsafe LLM output writes `planner.fallback` and
returns a template DAG.

### No execution during preview

The bridge preview route returns DAG data only. The Phase 3.2 and Phase 3.3
integration tests assert that preview produces planner evidence without creating
Gen3D artifacts or dispatching `gen3d.generate`. The UI `Generate` button remains
a disabled `LockedAction`.

### Read-only and locality boundaries

The bridge remains localhost-only and has exactly three routes:
`GET /api/printers`, `POST /api/plan/preview`, and `GET /api/runs/{run_id}`.
There are no printer writes, slicer calls, Blender calls, native windows, or
external process launches in this slice.

### LLM gateway boundaries

The gateway uses injected callers in tests and proof generation. The fixture LLM
server is consumed in-process through `TestClient`; no real provider, provider
probe, SDK call, or network path is introduced. Raw LLM response text is not
displayed in the UI.

### Path-restricted LLM-import

The LLM SDK import scan is clean outside `gateways/llm.py`; CP3.3 paths contain
no `openai`, `anthropic`, `google.generativeai`, `requests`, or `httpx` imports
outside the allowed gateway boundary.

## Proof Bundle

Path:

```text
06_release/phase3.3-bundle/4ae16075915a-20260502T114728Z.zip
```

SHA-256:

```text
a5a77b55981ddc1f9b81ac59f47a633ff61f12a8b7b7c6dd9ce00f46355bc47a
```

Included files:

```text
docs/ADR-011-llm-planner-gateway.md
docs/PHASE3_3_PLAN.md
evidence/ledger_snapshot.sqlite3
evidence/llm_redacted_trace_sample.json
evidence/plan_preview_replay.json
evidence/playwright_report.json
evidence/ui_build_output_hash.json
```

Verification result:

```json
{
  "bundle": "06_release\\phase3.3-bundle\\4ae16075915a-20260502T114728Z.zip",
  "ledger_counts": {
    "budget.exceeded": 1,
    "llm.complete": 3,
    "planner.fallback": 2,
    "planner.plan": 4
  },
  "manifest": "06_release\\phase3.3-bundle\\4ae16075915a-20260502T114728Z.manifest.json",
  "manifest_count": 7,
  "sha256": "a5a77b55981ddc1f9b81ac59f47a633ff61f12a8b7b7c6dd9ce00f46355bc47a",
  "verified": true
}
```

## Known Follow-ups

- Real 3D providers / Phase 3.4.
- Blender MCP read-only.
- Slicer dry-run.
- Write capability / Phase 4.
- Per-provider budget caps.
- Streaming and function-calling LLM modes.

## Risks Observed

R-1 Provider cost runaway: mitigated by per-run and per-day budget caps, R7, and
`budget.exceeded` ledger evidence. Bundle evidence: `budget.exceeded=1`.
Tests: `test_llm_gateway.py`, `test_budget.py`,
`test_planner_llm_fallback_roundtrip.py`.

R-2 Malformed DAG from LLM: mitigated by strict planner validation and template
fallback under R8. Bundle evidence: `planner.fallback=2`, including malformed
fixture replay. Tests: `test_llm_integration.py`,
`test_planner_llm_fallback_roundtrip.py`.

R-3 Prompt injection: mitigated by sanitizer rejection of role/system markers and
write-class output refusal under R8. Bundle evidence: fallback rows remain
template-only and no executable DAG is emitted from malformed fixture input.
Tests: `test_sanitize.py`, `test_llm_integration.py`.

R-4 External provider failure: mitigated by injected-caller gateway boundary,
timeout/retry handling, and deterministic fallback. Bundle evidence:
`llm.complete=3` from in-process fixture calls only. Tests:
`test_llm_gateway.py`, `test_planner_llm_fallback_roundtrip.py`.

R-5 Secret leakage: mitigated by redaction at trace/ledger/bundle boundaries.
Bundle evidence: verifier scanned `llm_redacted_trace_sample.json` with the
gateway redaction regexes and returned `verified=true`. Tests:
`test_redaction.py`, bundle verifier.

R-6 No write escalation: mitigated by write-class denylist, registered-tool
checks, and Phase 4 manifest refusal. Refusal rules: R6 and R8. Bundle evidence:
preview and fallback rows contain no write tool dispatch. Tests:
`test_capabilities_manifest.py`, `test_llm_integration.py`.

R-7 LLM-SDK import drift: mitigated by path-restricted import scanning. Bundle
evidence: CP3.3 verification scan returned no matches outside `gateways/llm.py`.
Tests/gates: LLM SDK import scan.

R-8 Backsliding into Phase 4: mitigated by adapter manifest gating and locked UI
actions. Bundle evidence: proof replay remains read-only and UI Playwright
asserts `Generate` stays disabled. Tests: `test_capabilities_manifest.py`,
`gen3d.planner_mode.spec.ts`.

## Stop Point

CP3.3-E closes Phase 3.3. Phase 3.4 has not started.
