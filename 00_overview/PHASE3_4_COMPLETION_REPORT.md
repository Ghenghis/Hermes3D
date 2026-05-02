# Phase 3.4 Completion Report

## Scope Summary

Phase 3.4 adds the real-provider probe substrate for the Phase 3 LLM planner
gateway without changing the default planner path. The default policy remains
`default_mode: template`, and no user who does nothing will route completions to
a real provider.

The new provider surface is intentionally narrow. MiniMax and DeepSeek are the
only configured provider keys; provider calls are represented through a bounded
`ProviderProbeGateway`, a `provider.probe` capability, and adapter files whose
network import boundary is explicitly path-restricted.

The probe-first invariant is now enforced before a non-fixture LLM completion is
accepted. A provider must have a recent successful `provider.probe` ledger row or
`LLMGateway.complete()` returns `provider_not_probed`; planner LLM mode then
falls back to the deterministic template DAG.

The bridge adds one read-only route, `GET /api/providers/health`, which only
summarizes existing ledger evidence. The UI adds a non-gating status dot in the
existing Gen3D providers panel. It does not trigger probes, edit provider config,
unlock Generate, add tabs, or add polling.

Out of scope: real 3D providers, write actions, auto-probing, provider config UI,
default real-provider routing, streaming, function-calling, multi-provider
routing or fallback chains, and Phase 4 execution capability.

## Commit List

Captured with:

```bash
git log origin/develop..HEAD --oneline
```

```text
79aadaf feat(phase3.4): add providers/health bridge route + ui dot + playwright (CP3.4-D)
1f16a73 feat(phase3.4): wire R9/R10 + provider.probe capability + cli + integration (CP3.4-C)
5023e70 feat(phase3.4): add probe gateway + minimax/deepseek adapter substrate (CP3.4-B)
2fe40b5 feat(phase3.4): add Phase 3.4 plan + ADR-012 + extended policy schema (CP3.4-A)
```

The CP3.4-E closeout commit adds this report, the proof assembler, the generated
proof bundle, and the PR body.

## Files Touched

Captured with:

```bash
git diff origin/develop..HEAD --stat
```

```text
00_overview/PHASE3_4_PLAN.md                       | 241 +++++++++++++++++++++
.../adr/ADR-012-real-provider-probes.md            | 129 +++++++++++
03_implementation/config/llm_policy.schema.json    |  70 ++++++
03_implementation/config/llm_policy.yaml           |  19 ++
.../src/hermes3d/adapters/_capabilities.py         |   1 +
03_implementation/src/hermes3d/cli/__init__.py     |   2 +
03_implementation/src/hermes3d/cli/probe.py        |  89 ++++++++
03_implementation/src/hermes3d/gateways/llm.py     |  34 ++-
03_implementation/src/hermes3d/gateways/probe.py   | 226 +++++++++++++++++++
.../src/hermes3d/gateways/providers/__init__.py    |  75 +++++++
.../src/hermes3d/gateways/providers/deepseek.py    | 105 +++++++++
.../src/hermes3d/gateways/providers/minimax.py     | 104 +++++++++
.../src/hermes3d/orchestration/bridge.py           |  73 +++++++
.../src/hermes3d/orchestration/supervisor.py       |  67 +++++-
.../src/hermes3d/orchestration/types.py            |  21 ++
03_implementation/ui/src/api/adapters.live.ts      |  78 +++++++
03_implementation/ui/src/api/adapters.ts           |  23 +-
03_implementation/ui/src/tabs/Gen3D.tsx            |  51 ++++-
03_implementation/ui/src/types/provider.ts         |  10 +
.../ui/tests/visual/gen3d.provider_health.spec.ts  | 164 ++++++++++++++
04_testing/fixtures/providers/__init__.py          |   1 +
.../fixtures/providers/deepseek_responses.json     |  45 ++++
.../fixtures/providers/minimax_responses.json      |  48 ++++
04_testing/fixtures/providers/server.py            |  39 ++++
.../integration/test_bridge_provider_health.py     | 121 +++++++++++
.../integration/test_provider_probe_roundtrip.py   | 241 +++++++++++++++++++++
04_testing/pytest/unit/cli/__init__.py             |   1 +
04_testing/pytest/unit/cli/test_probe.py           |  98 +++++++++
04_testing/pytest/unit/gateways/test_deepseek.py   |  60 +++++
04_testing/pytest/unit/gateways/test_minimax.py    |  60 +++++
04_testing/pytest/unit/gateways/test_probe.py      | 217 +++++++++++++++++++
31 files changed, 2508 insertions(+), 5 deletions(-)
```

## Gate Results

- `cd 03_implementation && python -m pytest ../04_testing/pytest -q`: PASS, 662 tests.
- `cd 03_implementation && python -m ruff check src ../04_testing/pytest`: PASS.
- `cd 03_implementation && python -m ruff format --check src ../04_testing/pytest`: PASS.
- `cd 03_implementation/ui && npm run lint`: PASS (`tsc --noEmit`).
- `cd 03_implementation/ui && npm run build`: PASS, 2412 modules transformed.
- UI build outputs: `index.html` 0.42 kB / gzip 0.29 kB, CSS 20.57 kB / gzip 4.78 kB, JS 685.52 kB / gzip 185.42 kB.
- `cd 03_implementation/ui && npx playwright test --reporter=json > playwright-report.json`: PASS, JSON report contains 16 passed tests.
- `cd 03_implementation/ui && npx playwright test --reporter=list`: PASS, 16 tests.
- `python 02_architecture/scripts/scaffolding/phase3_4_proof.py --playwright-json 03_implementation/ui/playwright-report.json`: PASS, `verified=true`.

## Safety Audit

### Planner determinism

Planner source was not modified in Phase 3.4. The deterministic template planner
remains the fallback and the default. R9 refusal evidence in the bundle shows
planner LLM mode returning a template DAG with `planner.fallback` when a provider
is not probe-verified.

### R9-R10 enforcement

R9 is enforced inside `LLMGateway.complete()` for non-fixture providers. R10 is
enforced at probe token issuance through the supervisor budget check and inside
the probe gateway budget/rate substrate. The bundle ledger contains
`planner.fallback=1` and `budget.exceeded=1`.

### No execution during preview

`POST /api/plan/preview` remains DAG-only. The new `GET /api/providers/health`
route is read-only and derives health from existing ledger rows; it never invokes
`ProviderProbeGateway.probe()` and never issues provider tokens.

### Read-only and locality boundaries

The bridge remains localhost-only and now has exactly four routes:
`GET /api/printers`, `POST /api/plan/preview`, `GET /api/runs/{run_id}`, and
`GET /api/providers/health`. The UI provider dot is informational only, and
`LockedAction` Generate remains disabled.

### Provider gateway boundaries

The proof and tests use in-process FastAPI fixtures through `TestClient`. No
provider probe is triggered from bridge or UI, and no real provider call is made.
Provider responses are normalized into `ProviderProbeResult` and ledgered as
redacted excerpts plus hashes.

### Path-restricted provider imports

The import scan is clean outside the allowed gateway/provider boundary. `httpx`
appears only in `03_implementation/src/hermes3d/gateways/providers/minimax.py`
and `03_implementation/src/hermes3d/gateways/providers/deepseek.py`; no new
tests, CLI, bridge code, or UI files import it.

## Proof Bundle

Path:

```text
06_release/phase3.4-bundle/79aadaf8e611-20260502T212648Z.zip
```

SHA-256:

```text
bf19783977ed2cf3d6ff16d877d28de2cb2f02770e2e2c342cbb38af95813c91
```

Included files:

```text
docs/ADR-012-real-provider-probes.md
docs/PHASE3_4_PLAN.md
evidence/ledger_snapshot.sqlite3
evidence/plan_preview_replay.json
evidence/playwright_report.json
evidence/provider_probe_replay.json
evidence/ui_build_output_hash.json
```

Verification result:

```json
{
  "bundle": "06_release\\phase3.4-bundle\\79aadaf8e611-20260502T212648Z.zip",
  "ledger_counts": {
    "budget.exceeded": 1,
    "llm.complete": 1,
    "planner.fallback": 1,
    "planner.plan": 2,
    "provider.probe": 2
  },
  "manifest": "06_release\\phase3.4-bundle\\79aadaf8e611-20260502T212648Z.manifest.json",
  "manifest_count": 7,
  "sha256": "bf19783977ed2cf3d6ff16d877d28de2cb2f02770e2e2c342cbb38af95813c91",
  "verified": true
}
```

## Known Follow-ups

- Real 3D providers / Phase 3.5+.
- Blender MCP read-only.
- Slicer dry-run.
- Write capability / Phase 4.
- Per-provider completion budget caps beyond the initial provider config map.
- Streaming and function-calling LLM modes.

## Risks Observed

R-9 Provider not probe-verified: mitigated by a probe-freshness check before
real-provider completion. Refusal: R9. Bundle evidence: `planner.fallback=1`
with `provider_not_probed`. Tests: `test_provider_probe_roundtrip.py`.

R-10 Probe budget exhaustion: mitigated by supervisor preflight budget checks and
probe gateway budget/rate checks. Refusal: R10. Bundle evidence:
`budget.exceeded=1`. Tests: `test_probe.py`, `test_provider_probe_roundtrip.py`.

R-11 Provider key leakage: mitigated by env-only key names, redaction of probe
excerpts, and bundle verifier redaction-regex scanning. Refusal: defense in
depth. Bundle evidence: provider replay verifier passed with zero regex matches.
Tests: `test_minimax.py`, `test_deepseek.py`, bundle verifier.

R-12 Provider response drift: mitigated by adapter normalization and failure
classification for malformed or unexpected provider responses. Refusal: R8 where
planner output would otherwise be accepted. Bundle evidence:
`provider.probe=2`, including one failed probe. Tests: `test_minimax.py`,
`test_deepseek.py`.

R-13 Probe storm on degraded provider: mitigated by per-provider rate cap plus
per-day probe budget. Refusal: R10. Bundle evidence: failed probes are ledgered
as `provider.probe` failures. Tests: `test_probe.py::test_rate_cap_exceeded`.

R-14 Cost surprise on real-provider opt-in: mitigated by default template mode,
fixture-provider exemption, and R9 probe-first refusal for non-fixture providers.
Refusal: R7 + R9. Bundle evidence: `llm.complete=1` only after a successful
`provider.probe` row; otherwise planner fallback is recorded. Tests:
`test_provider_probe_roundtrip.py`.

## Stop Point

CP3.4-E closes Phase 3.4. Phase 3.5 has not started.
