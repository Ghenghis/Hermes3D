# Phase 0 — Foundation Baseline Report

**Branch:** `feat/phase-0-foundation-baseline`
**Cut from:** `develop` @ `570de91` (post v4.1 kit landing)
**rc1 baseline:** `v5.3.0-rc1` @ `6dd9e01` — frozen, untouched by Phase 0
**Scope:** Read-only audit of the v4.1 contract kit's foundation (repo/kit, environment, tool registry, adapter registry, security/tunnel, proof). No source code changed. No kit specs edited.
**Coordinator strategy:** 6 specialist audits (4 ran as parallel background agents; 2 stalled silently and were completed directly by the coordinator using the same scope and constraints).

## Top-level verdict: **AMBER · GO**

All six audit domains converge on **GO for Phase 1**. None returned RED. The findings below are work items for Phase 1, not blockers for starting it.

## Per-domain scorecard

| # | Domain | Verdict | Output document | Top blocker | Phase 1 readiness |
|---|---|---|---|---|---|
| 1 | Repo + Kit Validator | **GREEN** | this report (synthesizes) | none — kit is self-consistent, all preconditions met | GO |
| 2 | Environment + GPU Detection | **AMBER** | [`02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md`](../02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md) | no `scripts/env-detect.py` yet (HIGH) | GO |
| 3 | External Tool Registry | **AMBER** | [`01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`](../01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md) | stale validator pseudocode (HIGH) | GO |
| 4 | Adapter Registry | **AMBER** | [`03_implementation/adapter_registry/README.md`](../03_implementation/adapter_registry/README.md) | two divergent method lists (HIGH — closed in adapter README §2) | GO |
| 5 | Security + Tunnel Baseline | **AMBER** | this report (synthesizes; see §6 below) | worker auth scheme unspecified (HIGH); no formal threat model (HIGH) | GO |
| 6 | Proof Baseline | **GREEN** | [`05_truth_proof/PHASE0_PROOF_BASELINE.md`](../05_truth_proof/PHASE0_PROOF_BASELINE.md) | none — existing infra sufficient | GO |

## What Phase 0 produced

1. **`00_overview/PHASE0_BASELINE_REPORT.md`** — this document, the synthesis
2. **`01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`** — registry coverage + Phase 1 work items
3. **`02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md`** — dual-edition env model + reference host
4. **`03_implementation/adapter_registry/README.md`** — adapter taxonomy + reconciled surface + lifecycle states + smoke-gate matrix
5. **`05_truth_proof/PHASE0_PROOF_BASELINE.md`** — proof claim + verification commands + bundle plan

Plus 6 agent-findings working notes under `var/phase0-agents/` (gitignored per `.gitignore` line 21 — local evidence only). The 5 canonical reports above stand on their own.

## Phase 0 preconditions (all met)

Per [`hermes3d_gui_contract_kit_v4.1/00_overview/EXECUTION_ORDER.md`](../hermes3d_gui_contract_kit_v4.1/00_overview/EXECUTION_ORDER.md), Phase 0 is "preserve current stable line." That meant:

| Precondition | State |
|---|---|
| PR #10 merged (Layer D fix-forward + Layer D promoted to hard gate) | ✅ merged into develop at `502499c`, also in rc1 |
| PR #9 GREEN re-run merged (Wave B QA) | ✅ merged at `3e7caee` with both UNSTABLE and GREEN reports preserved |
| `release/v5.3.0-rc1` cut + tagged + GitHub prerelease | ✅ tag `v5.3.0-rc1` annotated at `6dd9e01`; release published with two verified bundles + release dry-run zip |
| v4.1 contract kit landed on develop | ✅ committed at `570de91` |
| Branch hygiene: no `main`/`master` activity | ✅ repo has no `main` branch; only `develop` + `release/*` are integration branches |

Kit's own self-tests pass:

```
$ bash hermes3d_gui_contract_kit_v4.1/scripts/run_v4_1_gates.sh
PASS

$ python hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py \
       hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml
Registry validation PASS: 12 tools checked
```

## Notable HIGH findings (consolidated)

These are the items Phase 1 must address first. Full enumeration with severities is in each domain's output document.

| # | Domain | Finding | Resolution |
|---|---|---|---|
| 1 | Adapter | `ADAPTER_INTERFACE.md` and `ADAPTER_BOUNDARY_ARCHITECTURE.md` publish two non-identical method lists | **Resolved in `03_implementation/adapter_registry/README.md` §2** (single canonical surface, normalized union) |
| 2 | Adapter | Adapter lifecycle state machine undefined | **Resolved in `03_implementation/adapter_registry/README.md` §3** (8-state enum) |
| 3 | Adapter | `dry_run` not bound to `execute` (no token, no replay protection) | **Resolved in `03_implementation/adapter_registry/README.md` §6 + §7** (extended envelope + Confirmation schema with `dry_run_token` binding) |
| 4 | Environment | No `scripts/env-detect.py` exists; adapters/router cannot trust `edition` claims | **Phase 1 deliverable** — script + JSON Schema + 4 mock fixtures |
| 5 | Environment | Edition resolution rule (`desktop_gpu_worker` vs `ubuntu_vps_control_server` vs `blocked_no_gpu`) is implicit | **Phase 1 ADR** (recommendation in env baseline §4) |
| 6 | Registry | `registry_validator_pseudocode.py` is stale — describes a different schema than the live registry | **Phase 1 cleanup** — delete or regenerate from `validate_registry.py` |
| 7 | Security | Worker authentication scheme is unspecified beyond "worker authenticates VPS" | **Phase 1 ADR-007** ("Worker Authentication Scheme" — likely Tailscale ACL + per-worker API key with rotation) |
| 8 | Security | No formal threat model document | **Phase 1 ADR-006** ("Threat Model" — attacker classes + mitigations) |

## Security baseline summary (Agent 5)

The full security audit lives inline in the per-domain agent finding (`var/phase0-agents/agent-5-security-tunnel-baseline.md`). Key results:

- **Secret scan: 0 hits.** Patterns checked: `AKIA…`, `ghp_…`, `github_pat_…`, `-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----`, `(api[_-]?key|secret|password|token)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}`. No matches anywhere in the repo.
- **Sensitive-file scan: clean.** `git ls-files | grep -E '(\.env$|\.env\.|\.pem$|\.key$|id_rsa|credentials|secrets?\.(yaml|yml|json|toml)$)'` returns only `env/.env.example` (template, not a secret).
- **`.gitignore` covers** `.env*` (with explicit allow for `env/.env.example`), per-deployment fleet config (`printers.user.toml`), `var/`, `node_modules/`, vendor forks, proof bundles. **Defensive gap (LOW):** `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx` are not explicitly excluded — Phase 1 should add them.
- **`HERMES3D_PROOF_KEY`** defaults to a literal `hermes3d-default-proof-key-not-secret` in `scripts/_build_bundle.py:38`. Acceptable for RC and Phase 0 internal bundles; GA must override. Documented in `05_truth_proof/PHASE0_PROOF_BASELINE.md` §5.
- **Spec rigor (kit security/tunnel docs):** **direction-correct, implementation-light**. The "no raw shell passthrough" rule, typed-job allowlist, printer write gating, Blender MCP safe-executor, and release-blocking conditions are all explicit. What's missing: chosen auth mechanism, threat model, audit log schema, key rotation policy, rate limiting. None of these are security incidents — they are spec gaps Phase 1 closes before any tunnel/worker code lands.

## Repo + kit baseline summary (Agent 1)

- All **56 files** of `hermes3d_gui_contract_kit_v4.1/` audited; every cross-reference between kit docs resolves.
- 3 LOW findings (none blocking Phase 1):
  1. Visual-contract PNG path mismatch — `EXECUTION_ORDER.md:15` and `UI_FINAL_SCREENSHOT_GATE.md:11` point to `06_release/UI_FINAL_VISUAL_CONTRACT.png`; the file is at kit root as `Hermes3D.png`. Phase 2 cleanup item.
  2. Two registry validators coexist (stale pseudocode + real validator) — also surfaced by Agent 3.
  3. Kit-prescribed `.claude/tasks/TASK-NN-*.md` files don't exist yet — expected, Phase 1 produces `TASK-01-registry-validator.md` first.

## Constraints honored

| Constraint (per user instructions) | State |
|---|---|
| No secrets committed | ✅ verified — secret scan clean |
| No direct commits to `main`/`master` | ✅ no such branches exist on this repo |
| No changes to `release/v5.3.0-rc1` branch or the `v5.3.0-rc1` tag | ✅ `git rev-parse v5.3.0-rc1` returns `6dd9e01…` (unchanged); branch is also at `6dd9e01…` |
| Proof report required before PR | ✅ this document + `05_truth_proof/PHASE0_PROOF_BASELINE.md` |
| PR targets `develop` | ✅ to be opened against `develop` |
| Foundation only — no UI-Final, no tool integration | ✅ no source under `03_implementation/src/hermes3d/` modified; zero adapter `.py` files |
| Stop after Phase 0 report + PR; do not continue to Phase 1 without approval | ✅ coordinator stops here pending user sign-off |

## Phase 1 readiness — summary

**GO across all six domains.** First Phase 1 items (in order of dependency):

1. **Adapter README ADR-008** — codify `03_implementation/adapter_registry/README.md` §3 (lifecycle states) and §7 (Confirmation envelope) as immutable.
2. **Stale pseudocode resolution** — delete or regenerate `registry_validator_pseudocode.py`. (Cheap, removes a confusion source.)
3. **Env-detect script + JSON Schema + fixtures** — `scripts/env-detect.py`, `schemas/env_report.schema.json`, `tests/fixtures/gpu_detection/{nvidia_smi_3090ti,nvidia_smi_no_gpu,no_nvidia_smi,no_gpu}.json`.
4. **ADR-006 "Edition Resolution Rule"** — explicit `desktop_gpu_worker` vs `ubuntu_vps_control_server` vs `blocked_no_gpu` resolution.
5. **ADR-007 "Worker Authentication Scheme"** — chosen mechanism + rotation policy. **Required before any tunnel/worker code lands.**
6. **ADR-005 "Threat Model"** — attacker classes + mitigations.
7. **`02_architecture/AUDIT_LOG_SCHEMA.md`** — schema for "signed/logged worker actions".
8. **`02_architecture/RATE_LIMIT_POLICY.md`** — rate limits on the worker API.
9. **Registry validator hardening** — license field, per-`type` capability matrix, `tested_versions`, URL shape check, structured error model, default-path fix. Per `01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md` §6.
10. **`.gitignore` defensive addendum** — `*.pem`, `*.key`, `id_rsa*`, `*.p12`, `*.pfx`.
11. **Adapter shell** — abstract `ToolAdapter` Python protocol + per-target skeletons with real `detect()` + `version()` + `capabilities()`; all other methods raise `NotImplementedYet`. Per `03_implementation/adapter_registry/README.md` §13.
12. **CI Layer Adapter** — runs detect-only smoke tests on push to `develop` and `release/*`.

## Stop point

This branch + this report constitute Phase 0's terminal state. Coordinator does NOT auto-start Phase 1. The user must explicitly approve the PR and explicitly trigger Phase 1.

## Cross-links

- Phase 0 outputs:
  - [`01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`](../01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md)
  - [`02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md`](../02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md)
  - [`03_implementation/adapter_registry/README.md`](../03_implementation/adapter_registry/README.md)
  - [`05_truth_proof/PHASE0_PROOF_BASELINE.md`](../05_truth_proof/PHASE0_PROOF_BASELINE.md)
- Kit anchors:
  - [`00_overview/EXECUTION_ORDER.md`](../hermes3d_gui_contract_kit_v4.1/00_overview/EXECUTION_ORDER.md)
  - [`00_overview/V4_1_FINAL_READINESS.md`](../hermes3d_gui_contract_kit_v4.1/00_overview/V4_1_FINAL_READINESS.md)
  - [`06_release/V4_1_CLAUDE_HANDOFF_PROMPT.md`](../hermes3d_gui_contract_kit_v4.1/06_release/V4_1_CLAUDE_HANDOFF_PROMPT.md)
  - [`06_release/FINAL_NO_MERGE_RULES.md`](../hermes3d_gui_contract_kit_v4.1/06_release/FINAL_NO_MERGE_RULES.md)
- rc1 release: [github.com/Ghenghis/Hermes3D/releases/tag/v5.3.0-rc1](https://github.com/Ghenghis/Hermes3D/releases/tag/v5.3.0-rc1)
