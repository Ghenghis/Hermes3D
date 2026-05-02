# Phase 3.4 (initial) — Real Provider Probes

**Status:** design + schema only · no gateway code · no YAML edit yet.
**Architecture references:** [`02_architecture/adr/ADR-009-orchestration-skeleton.md`](../02_architecture/adr/ADR-009-orchestration-skeleton.md), [`02_architecture/adr/ADR-010-planner-and-dag.md`](../02_architecture/adr/ADR-010-planner-and-dag.md), [`02_architecture/adr/ADR-011-llm-planner-gateway.md`](../02_architecture/adr/ADR-011-llm-planner-gateway.md), [`02_architecture/adr/ADR-012-real-provider-probes.md`](../02_architecture/adr/ADR-012-real-provider-probes.md).
**Branch:** `feat/phase-3-4-real-provider-probes` (forks from `develop` after Phase 3.3 merge).
**Scope discipline:** smaller than Phase 3.3 — no real 3D, no write actions, no auto-probing, default mode stays template.

---

## 1. Objective

Introduce a bounded, opt-in provider probe capability for MiniMax (primary) and DeepSeek (secondary) that lets the supervisor verify provider liveness before any LLM completion is permitted to call out, without changing default behaviour and without breaking Phase 3.3 fallback.

---

## 2. Out of scope

The following are **NOT** in Phase 3.4. Each is deferred to a later phase with its own ADR + checkpoint:

- Real 3D providers (TRELLIS / Hunyuan3D / TripoSR / MiniMax 3D), including real 3D probes — Phase 3.5+.
- Real LLM completion executed by default. The fixture/template path remains the default for users who do nothing.
- Any write capability (`printer.write`, `slicer.execute`, `gcode.send`, `blender.execute`, `printer.print_start`) — Phase 4 boundary unchanged.
- Provider list editing from the UI. The allowlist remains config-only.
- Provider chips or labels that imply a provider is ready for production use. The UI dot only reports probe state.
- Streaming, function-calling, and tool-use LLM modes.
- Per-provider routing or fallback chains. One provider is selected per request.
- API keys read from disk, settings, UI, or git. Keys are environment-only.
- Auto-probing on app boot, page load, or interval timers.
- New tabs, new dock states, or new UI primitives.
- Removal of the Phase 3.3 fixture path.

---

## 3. File / module list

### Python — gateway, providers, supervisor, CLI
| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `00_overview/PHASE3_4_PLAN.md` | CP3.4-A | new | this plan |
| `02_architecture/adr/ADR-012-real-provider-probes.md` | CP3.4-A | new | probe gateway contract, provider config, R9/R10, path restriction |
| `03_implementation/config/llm_policy.schema.json` | CP3.4-A | modify (additive) | optional provider and probe policy fields |
| `03_implementation/src/hermes3d/gateways/probe.py` | CP3.4-B | new | `ProviderProbeGateway.probe(provider_id, *, token, budget) -> Result[ProviderProbeResult]` |
| `03_implementation/src/hermes3d/gateways/providers/__init__.py` | CP3.4-B | new | provider adapter namespace |
| `03_implementation/src/hermes3d/gateways/providers/minimax.py` | CP3.4-B | new | MiniMax probe and completion caller factory; one of the only new `httpx` import locations |
| `03_implementation/src/hermes3d/gateways/providers/deepseek.py` | CP3.4-B | new | DeepSeek probe and completion caller factory; one of the only new `httpx` import locations |
| `03_implementation/src/hermes3d/orchestration/types.py` | CP3.4-B | modify (additive) | `ProviderProbeResult` DTO |
| `03_implementation/config/llm_policy.yaml` | CP3.4-B | modify (additive) | optional `providers` map with safe defaults; default mode remains `template` |
| `03_implementation/src/hermes3d/orchestration/supervisor.py` | CP3.4-C | modify (additive) | R9/R10 helpers and `provider.probe` token issuance checks |
| `03_implementation/src/hermes3d/adapters/_capabilities.py` | CP3.4-C | modify (additive) | `provider.probe` capability, phase=3, dangerous=False |
| `03_implementation/src/hermes3d/gateways/llm.py` | CP3.4-C | modify (additive) | probe-freshness check before real-provider completion; fixture provider exempt |
| `03_implementation/src/hermes3d/cli/__init__.py` | CP3.4-C | new | CLI namespace |
| `03_implementation/src/hermes3d/cli/probe.py` | CP3.4-C | new | operator-triggered `python -m hermes3d.cli.probe <provider_id>` |
| `02_architecture/scripts/scaffolding/phase3_4_proof.py` | CP3.4-E | new | proof bundle assembler and verifier |
| `00_overview/PHASE3_4_COMPLETION_REPORT.md` | CP3.4-E | new | completion report |
| `06_release/PHASE3_4_PR_BODY.md` | CP3.4-E | new | PR body |
| `06_release/phase3.4-bundle/<run_id>.zip` | CP3.4-E | generated | proof bundle |
| `06_release/phase3.4-bundle/<run_id>.manifest.json` | CP3.4-E | generated | bundle manifest |
| `06_release/phase3.4-bundle/<run_id>.sha256` | CP3.4-E | generated | bundle digest sidecar |

### UI — read-only health indicator
| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `03_implementation/src/hermes3d/orchestration/bridge.py` | CP3.4-D | modify (additive) | `GET /api/providers/health` read-only route returning redacted probe summaries |
| `03_implementation/ui/src/api/adapters.ts` | CP3.4-D | modify (additive) | `getProviderHealth()` AdapterAPI method |
| `03_implementation/ui/src/api/adapters.live.ts` | CP3.4-D | modify (additive) | live `getProviderHealth()` fetch to localhost bridge |
| `03_implementation/ui/src/types/provider.ts` | CP3.4-D | new | provider health DTOs |
| `03_implementation/ui/src/tabs/Gen3D.tsx` | CP3.4-D | modify (additive) | small non-gating status dot in the providers panel |

### Tests / fixtures
| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `04_testing/pytest/unit/gateways/test_probe.py` | CP3.4-B | new | ProviderProbeGateway unit coverage: token, budget, rate, allowlist, redaction |
| `04_testing/pytest/unit/gateways/test_minimax.py` | CP3.4-B | new | MiniMax adapter request/response normalization against fixtures |
| `04_testing/pytest/unit/gateways/test_deepseek.py` | CP3.4-B | new | DeepSeek adapter request/response normalization against fixtures |
| `04_testing/fixtures/providers/__init__.py` | CP3.4-B | new | provider fixture namespace |
| `04_testing/fixtures/providers/minimax_responses.json` | CP3.4-B | new | MiniMax deterministic probe and error responses |
| `04_testing/fixtures/providers/deepseek_responses.json` | CP3.4-B | new | DeepSeek deterministic probe and error responses |
| `04_testing/fixtures/providers/server.py` | CP3.4-B | new | mock provider server used through injected callers only |
| `04_testing/pytest/unit/cli/test_probe.py` | CP3.4-C | new | CLI probe command coverage |
| `04_testing/pytest/integration/test_provider_probe_roundtrip.py` | CP3.4-C | new | R9/R10 integration, provider.probe ledger evidence, completion refusal without probe |
| `03_implementation/ui/tests/visual/gen3d.provider_health.spec.ts` | CP3.4-D | new | status dot visual/behavioral coverage |

---

## 4. Checkpoint breakdown — CP3.4-A → CP3.4-E

Strict serial. Architect review at CP3.4-A, CP3.4-C, CP3.4-D, and CP3.4-E.

### CP3.4-A — Plan + ADR-012 + schema additions
- Commit this plan.
- Commit `ADR-012-real-provider-probes.md`.
- Extend `llm_policy.schema.json` with optional provider/probe fields only.
- Do **not** edit `llm_policy.yaml`.
- Do **not** create gateway, provider, supervisor, bridge, UI, or test code.
- Architect review: **YES**.

### CP3.4-B — Probe gateway + provider adapter substrate
- Add `ProviderProbeGateway` and provider adapters for MiniMax and DeepSeek.
- Add provider DTOs and provider fixtures.
- Add optional YAML provider config with safe defaults; `default_mode` remains `template`.
- Unit-test the gateway and provider adapters with mock callers only.
- Architect spot-check; full review at CP3.4-C.

### CP3.4-C — Supervisor R9/R10 + capability + CLI + integration
- Add `provider.probe` capability.
- Add R9/R10 checks in supervisor issuance and LLM gateway probe-freshness check.
- Add operator-only CLI probe command.
- Add integration coverage for provider probe roundtrip and completion refusal without a recent probe.
- Architect review: **YES**.

### CP3.4-D — Bridge route + UI dot
- Add `GET /api/providers/health` read-only route.
- Add AdapterAPI provider-health read.
- Add a small non-gating provider status dot to the existing Gen3D providers panel.
- Add Playwright spec for green/amber/red/idle dot states.
- Architect review: **YES**.

### CP3.4-E — Proof bundle + completion report + PR body
- Build proof bundle with provider.probe ledger evidence and redacted replay.
- Create completion report and PR body.
- Open Phase 3.4 PR after architect approval.
- Architect review: **YES**.
- HARD STOP. Phase 3.5 requires its own ADR and kickoff.

---

## 5. Safety gates per checkpoint

Refusal rules R1-R8 carry forward from ADR-009, ADR-010, and ADR-011. Phase 3.4 adds **two** rules:

| Rule | Trigger | Outcome |
|---|---|---|
| **R9** | `llm.complete` is attempted for a configured real provider with no successful `provider.probe` row newer than `probe_freshness_minutes` | `Err::Forbidden("provider_not_probed")`; planner falls back to template; ledger writes `planner.fallback("provider_not_probed")` |
| **R10** | `provider.probe` would exceed probe daily budget or per-provider rate cap | `Err::Forbidden("probe_budget_exceeded")`; ledger writes `budget.exceeded` with `tool="provider.probe"` |

| Checkpoint | Gate | Enforced by |
|---|---|---|
| CP3.4-A | Plan and ADR declare R9/R10, env-only keys, no default real-provider routing, and optional-only schema additions | architect doc review + schema validation |
| CP3.4-B | Probe gateway refuses token failures, unknown providers, missing keys, rate cap, and probe budget exhaustion; provider adapters normalize malformed provider responses without crashing | unit tests |
| CP3.4-C | Supervisor and LLMGateway enforce probe-first invariant; fixture provider remains exempt; CLI is operator-only and never auto-runs | unit + integration tests |
| CP3.4-D | Bridge provider-health route is read-only and localhost-only; UI dot never gates action; `LockedAction` Generate remains present | integration + Playwright |
| CP3.4-E | Bundle includes `provider.probe` success/fail and `planner.fallback("provider_not_probed")`; secret-pattern scan passes | bundle verifier |

Layer A path restriction extends R-7 from Phase 3.3: `httpx` is allowed only in `gateways/llm.py` and `gateways/providers/*.py`; any other import location fails.

---

## 6. Test plan

### Layer A — static gates
- JSON Schema validates against draft-07.
- Existing `llm_policy.yaml` validates unchanged.
- Source-pattern scanner remains clean.
- LLM/provider network import restriction:
  - `httpx` allowed in `03_implementation/src/hermes3d/gateways/llm.py`.
  - `httpx` allowed in `03_implementation/src/hermes3d/gateways/providers/*.py`.
  - `openai`, `anthropic`, provider SDKs, `requests`, and `urllib.request.urlopen` remain refused outside explicitly allowed gateway paths.
- No API keys in source or committed fixtures.

### Layer B — unit
| Test | Asserts |
|---|---|
| `test_probe.py` | R1-R5 token refusals, unknown provider refusal, env-var key handling, per-provider rate cap, R10 budget exceeded, redacted ledger excerpt |
| `test_minimax.py` | MiniMax adapter builds bounded probe request, parses success, redacts excerpt, treats unexpected shapes as probe failure |
| `test_deepseek.py` | DeepSeek adapter builds bounded probe request, parses success, redacts excerpt, treats unexpected shapes as probe failure |
| `test_probe.py::test_failures_count_against_budget` | failed probes still count against probe budget |
| `test_redaction.py::test_provider_key_patterns` | provider key-shaped values are masked |

### Layer C — integration
| Test | Asserts |
|---|---|
| `test_provider_probe_roundtrip.py` | provider probe success/failure ledger rows, R9 refusal before recent probe, R10 budget exceeded, fixture provider exemption, planner fallback on R9 |

### Layer D2 — UI
| Test | Asserts |
|---|---|
| `gen3d.provider_health.spec.ts` | provider dot displays green/amber/red/idle based on mocked health; dot is non-gating; Generate remains locked; no external network or popups |
| Existing Phase 3.3 specs | unchanged and green |

---

## 7. Proof bundle contents

- Path: `06_release/phase3.4-bundle/<head>-<utc>.zip`
- Manifest entries (planned, finalized in CP3.4-E):
  - `docs/PHASE3_4_PLAN.md`
  - `docs/ADR-012-real-provider-probes.md`
  - `evidence/ledger_snapshot.sqlite3`
  - `evidence/provider_probe_replay.json`
  - `evidence/plan_preview_replay.json`
  - `evidence/playwright_report.json`
  - `evidence/ui_build_output_hash.json`
- Ledger snapshot must contain at least one each:
  - `provider.probe` success
  - `provider.probe` failure
  - `planner.fallback("provider_not_probed")`
- Honesty diff confirms manifest matches zip exactly.
- Bundle verifier re-scans evidence for provider key and secret patterns.

---

## 8. Definition of done

Phase 3.4 is **done** iff all hold:

| # | Criterion | Measure |
|---|---|---|
| 1 | ProviderProbeGateway enforces budget (R10), allowlist, rate, and key handling | `test_probe.py` green |
| 2 | Provider adapters normalize success/failure without leaking raw keys or crashing on unexpected shape | `test_minimax.py` + `test_deepseek.py` green |
| 3 | LLMGateway refuses completion without recent probe (R9) | `test_provider_probe_roundtrip.py` green |
| 4 | Default policy `default_mode` remains `template` | grep on `llm_policy.yaml` |
| 5 | Path-restriction holds: `httpx` only in `gateways/llm.py` and `gateways/providers/*.py` | Layer A scanner |
| 6 | No new write capability | capability manifest tests + source-pattern scanner |
| 7 | Bridge envelope remains backward-compatible; Phase 3.1/3.2/3.3 specs unchanged and green | pytest + Playwright |
| 8 | UI dot is non-gating and `LockedAction` Generate remains present | `gen3d.provider_health.spec.ts` + grep audit |
| 9 | Source-pattern audit clean | Phase 0 scanner |
| 10 | Proof bundle honest; verifier finds zero secret matches and required ledger events | bundle verifier |
| 11 | Architect review PASS at CP3.4-A, CP3.4-C, CP3.4-D, CP3.4-E | review verdicts in chat |

---

## 9. Risks + mitigations

| # | Risk | Mitigation | Refusal | Intended test |
|---|---|---|---|---|
| R-9 | Provider not probe-verified — `llm.complete` runs against an unprobed or stale provider, yielding auth/rate/cost surprise | Probe-freshness check at gateway entry; refuse and fall back to template | R9 | `test_llm_gateway::test_completion_refused_without_recent_probe` + `test_provider_probe_roundtrip.py` |
| R-10 | Probe budget exhaustion — automated or buggy callers spam probes, draining cost budget | Per-day probe cap + per-provider rate cap; failures count against budget | R10 | `test_probe_gateway::test_budget_exceeded` + `test_rate_cap` |
| R-11 | Provider key leakage — API key appears in ledger, log, bundle, or stack trace | Keys read only from env vars named in policy; redactor masks Bearer keys and known prefixes; bundle verifier rescans evidence | n/a | `test_redaction::test_provider_key_patterns` + bundle verifier |
| R-12 | Provider response drift — provider returns malformed JSON or unexpected schema | Provider response normalized to `ProviderProbeResult`; unknown shape becomes probe failure, not crash | R8 | `test_minimax::test_unexpected_response_shape` |
| R-13 | Probe storm on degraded provider — repeated probe failures cause exponential ledger growth | Per-provider rate cap and per-day budget; failures count like successes | R10 | `test_probe_gateway::test_failures_count_against_budget` |
| R-14 | Cost surprise on real-provider opt-in — operator enables real provider and planner immediately routes through it | Two-key opt-in: env var plus future distinct real-provider mode plus recent successful probe; default policy remains `template` | R7 + R9 | `test_planner_real_provider_opt_in` integration |

R-7 from Phase 3.3 is extended: the path-restriction now allows `httpx` in `gateways/llm.py` and `gateways/providers/*.py` only. R-8 from Phase 3.3 remains unchanged: Phase 4 write capabilities stay refused by manifest validation and source-pattern gates.

---

## Cross-links

- [ADR-012](../02_architecture/adr/ADR-012-real-provider-probes.md)
- [ADR-011](../02_architecture/adr/ADR-011-llm-planner-gateway.md)
- [PHASE3_3_PLAN.md](PHASE3_3_PLAN.md)
