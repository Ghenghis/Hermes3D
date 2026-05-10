# Hermes3D Closed-Unmerged PR Ledger

**Date (UTC):** 2026-05-10
**Owner of record:** Wave 11 Agent 4 (`claude-w11-4-pr85`)
**Repo:** `Ghenghis/Hermes3D`
**Integration target:** `feat/hermes3d-7-complete-gui-repo-wiring`
**Mode:** DOC-ONLY (no source/test edits)
**Companion audits:** A1-A9 at `03_implementation/docs/handoffs/W10_A{1..9}_*_2026-05-10.md` and synthesis at [`CLOSED_UNMERGED_PR_SUPERSESSION_AUDIT_2026-05-10.md`](./CLOSED_UNMERGED_PR_SUPERSESSION_AUDIT_2026-05-10.md).

This document is the source-of-truth for closed-unmerged PRs and their successor PR(s) per Wave 10 audit. It exists to satisfy the `feedback_weakness_correction.md` rule that every PARTIAL audit finding must be paired with a fix-PR — the gap for #85 was provenance-only (production scope is preserved at HEAD, but no replacement-PR body cites #85), and a documentation row in this ledger is the targeted fix for that single-issue weakness. The Wave 11 agent set fans this rule out across all 3 PARTIAL items found by W10-A9.

## Schema

| original_pr | scope | closed_at | superseded_by | status | proof |

Field semantics:

- **original_pr** — closed-unmerged PR number (no merge commit).
- **scope** — one-line summary of what the closed PR shipped (from PR title/body — A1 metadata).
- **closed_at** — ISO-8601 UTC timestamp from `gh pr view` per W10-A1.
- **superseded_by** — comma-separated PR numbers of the merged successors that fold the scope back to HEAD (A2-A7 audit citations; A9 verifier wins on conflicts).
- **status** — one of `SUPERSEDED_COMPLETE`, `SUPERSEDED_PARTIAL`, `LOST_SCOPE`, `INTENTIONALLY_DROPPED` (W10 synthesis nomenclature).
- **proof** — file path + test name (or merged commit ref) that empirically demonstrates the scope is at HEAD.

## Records (Wave 10 audit 2026-05-10)

| original_pr | scope | closed_at | superseded_by | status | proof |
|---|---|---|---|---|---|
| #37 | tool_registry (real, 369-line v0.12 port) + security shell + ServiceHealthPage (UI 176 LoC, integration pending) | 2026-05-03T13:05:23Z | #41 (security in-house rewrite per ADR-016, merge `0c9b6d9`); #42 (ServiceHealthPage + port probe + ServiceCard/StatusPill, merge `4932e7a`); tool_registry relocated to `core/agents/tool_registry.py` (no single PR) | SUPERSEDED_PARTIAL | `04_testing/pytest/test_injection_scanner.py` 56/56 PASS; `test_health_probe.py`+`test_health_endpoint.py` 31 PASS; `test_tool_registrations.py` 24 PASS; **gap:** `03_implementation/ui/tests/visual/health-page.spec.ts` MISSING at HEAD per A9 §5.2 |
| #83 | Proof-gated Hermes Agent git shipping lane (`code.git.*` 6 contracts: `git_create_branch`/`git_commit_owned`/`git_push_current_branch`/`git_open_pull_request`/`git_readiness`/`git_stage_owned`) stacked on #73 | 2026-05-08T17:24:44Z | #105 (`8da4e6b2` recovery — explicitly lists "#83, #85, #88, #90, #92, #94, #96, #98, #100, and #103" in body); #118 (`3bf0ad20` chain audit GET `/e2e/jobs`) | SUPERSEDED_PARTIAL | `04_testing/pytest/unit/test_code_operator.py` (production code in `code_history.py`/`code_operator.py`/`agents.py` has all 6 contract names); **gap:** A9 found "only 1 actual occurrence" of direct test (`test_git_commit_rejects_spoofed_actor_fields`) — assertion coverage thin |
| #85 | Provider execution artifacts (MiniMax `code.teams.run_coding_pass` + DeepSeek `code.teams.run_review_pass` routed through bounded private env, MCP evidence; catalog → 76) | 2026-05-08T17:24:37Z | #84 (team assignment, `f0efa918`); #104 (provider smoke `/api/code-operator/providers/smoke`, `9763d2f7`); #107 (private env aliases); #112/#124/#145/#148 (MiniMax+DeepSeek runtime adapter hardening chain) | SUPERSEDED_PARTIAL (resolved by this ledger row per `feedback_weakness_correction.md`) | `04_testing/pytest/unit/test_code_operator.py::test_provider_smoke_*`; `04_testing/pytest/unit/test_agent_action_catalog.py` (`code.teams.*`/`run_coding_pass`/`run_review_pass` 10 occurrences); `gateways/providers/{minimax,deepseek}.py`; **gap fixed by:** this ledger row records the fold-in chain attribution (A9 found "no explicit 'supersedes #85' string" in any of #84/#104/#107/#112/#124/#145/#148 PR bodies) |
| #88 | Python/CAD verifier family (pymeshlab bridge + cadquery/open3d/build123d/numpy-stl/PyMesh import probes) | 2026-05-08T17:24:30Z | #105 (sub-commit `249f269`) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_source_runtime_contracts.py:122` (`pymeshlab import` verifier); A9 9/9 selective PASS in 2.80s |
| #90 | Print-farm health verifiers (FDM Monster/Fluidd/Mainsail/OctoFarm/OctoPrint local-only) | 2026-05-08T17:24:24Z | #105 (sub-commit `15a2d78`) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_source_runtime_contracts.py:813` (`fdm_monster` fixture); 5 print-farm `local_http_health` rows at `module_runtime.py:278-330` |
| #92 | Safe service start-runner preflights for 10 service/web rows + Start Runner button | 2026-05-08T17:24:17Z | #105 (sub-commits `979e71c`, `65e46e0`) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_source_runtime_contracts.py:843` (`test_service_start_runner_contracts_are_safe_supervised_starts`); `source_service_supervisor.py` blob `aaf6ceb`; routes `/start-runner`+`/stop-runner` |
| #94 | Remove live LAN/Moonraker timeouts from offline fleet unit tests (deterministic transport injection) | 2026-05-08T17:24:10Z | #105 (sub-commit `82bf637`) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_printer_fleet.py::test_probe_fleet_returns_one_entry_per_printer` PASS + `test_tool_registrations.py::test_fleet_status_runs_against_offline_fleet` PASS, both <1s |
| #96 | Rust metadata proof worker `hermes3d-accel` (SHA-256 + bounded G-code/STL metadata + Python bridge with safe fallback) | 2026-05-08T17:24:03Z | #105 (sub-commit "feat(accel): add rust metadata proof worker") | SUPERSEDED_COMPLETE | `03_implementation/rust/hermes3d_accel/{Cargo.toml,Cargo.lock,src/main.rs}` 351 LoC; `services/rust_accel.py` 123 LoC; `04_testing/pytest/unit/test_rust_accel.py` 4/4 PASS |
| #98 | Executable-path runner smoke (proof-only) for printrun/bambustudio/cura | 2026-05-08T17:23:57Z | #105 (sub-commit "feat(source): add executable path runner smoke") | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_source_runtime_contracts.py::test_executable_path_runner_accepts_desktop_launcher_metadata` PASS; `execution_mode == "registered_executable_path_metadata_probe"` (line 492) |
| #100 | Slicer CLI install/config preflights (slic3r/superslicer) + `source.cli_install_config.preflight` action | 2026-05-08T17:23:50Z | #105 (sub-commit "feat(source): add slicer cli config preflights") | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_source_runtime_contracts.py::test_slicer_cli_install_config_preflight_keeps_runtime_blocked` PASS; `execution_mode == "registered_cli_install_config_preflight"` (line 619) |
| #103 | Agents-tab Agent Code Workbench (E2E orchestration), readiness, CLI runner detection, no-mutation provider planning/review, catalog → 88 (`code.e2e.readiness.refresh`, `code.cli_runners.readiness.refresh`, `code.e2e.run`) | 2026-05-08T17:23:37Z | #105 (`8da4e6b2` lists #103 explicitly); #118 (`3bf0ad20` chain audit GET `/e2e/jobs`, 92 passing tests) | SUPERSEDED_COMPLETE | `Agents.tsx` blob `e8a17c10` 54 workbench/`apply.*reviewed`/`provider.*smoke`/`cli_runner`/`e2e_run` matches; `04_testing/pytest/unit/test_source_runtime_contracts.py` (978 lines) |
| #126 | First-proof Hermes Agent E2E loop with real recovery (SUPERSEDED banner on rescue doc) | 2026-05-09T07:09:04Z | #129 (re-base) → #132 (clean cherry-pick, merged 2026-05-09T07:25:09Z) | SUPERSEDED_COMPLETE | `03_implementation/docs/handoffs/PROVIDER_RESCUE_BLOCKER_PROOF_2026-05-09.md` 178 lines; SUPERSEDED block at lines 3-11; PR#132 body: "Clean replacement for #126/#129 after stacked base deletion" |
| #127 | Recovery Controller v1 lean ledger (7 tests; `record_step_failure` + `mark_recovery_outcome` + 3 routes) | 2026-05-09T07:09:05Z | #130 (re-base) → #133 (clean cherry-pick, merged 2026-05-09T07:25:22Z) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_code_operator.py` recovery routes; `test_recovery_controller_freeze.py` 7/7; `test_recovery_runs_route.py` 4/4; A9 22 PASS + 1 skip in 8s |
| #128 | Hermes3D OS visual reference pack (31 PNGs, README, manifest) | 2026-05-09T07:09:05Z | #131 (failed: bundled provider-rescue contamination); #134 (clean, merged 2026-05-09T07:25:29Z) | SUPERSEDED_COMPLETE | 31 PNGs in 10 sub-folders at `Images-GUI/`; README.md + GUI_REFERENCE_MANIFEST.json present; PR#134 body: "Clean replacement for #128/#131" |
| #129 | Re-base of #126 (auto-closed when stacked base deleted) | 2026-05-09T07:23:58Z | #132 | SUPERSEDED_COMPLETE | Same as #126 |
| #130 | Re-base of #127 (auto-closed when stacked base deleted) | 2026-05-09T07:23:59Z | #133 | SUPERSEDED_COMPLETE | Same as #127 |
| #131 | Re-base attempt of #128 (bundled extra files; failed) | 2026-05-09T07:24:01Z | #134 | SUPERSEDED_COMPLETE | Same as #128 |
| #168 | Version-tag proof events (Wave 2 P2-6) — `proof_helpers.py` + `_append_proof_event` augmentation in 3 sinks | 2026-05-10T01:39:56Z | #173 (re-targeted onto integration grandparent, merged 2026-05-10T01:44:09Z) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_proof_event_version_tagging.py` 13/13 PASS; A7 verified +543/-3 byte-identical unique payload; PR#173 body: "Re-targeted from auto-closed PR #168 (...). Content unchanged." |
| #170 | Provider compat matrix per version (Wave 4 P3-5) — `agent_version_provider_compat.py` + `ProviderInfo` + 14 tests + 2421-word doc | 2026-05-10T01:39:57Z | #174 (re-targeted onto integration grandparent, merged 2026-05-10T01:44:12Z) | SUPERSEDED_COMPLETE | `04_testing/pytest/unit/test_agent_version_provider_compat.py` 14/14 PASS; A7 verified +681/-0 byte-identical unique payload; PR#174 body: "Re-targeted from auto-closed PR #170 (...). Content unchanged." |

**Row count:** 19 (matches A1 metadata snapshot of W10 closed-unmerged scope).

**Status breakdown** (per W10 synthesis Final Verdict):

| Status | Count | PRs |
|---|---:|---|
| SUPERSEDED_COMPLETE | 16 | #88, #90, #92, #94, #96, #98, #100, #103, #126, #127, #128, #129, #130, #131, #168, #170 |
| SUPERSEDED_PARTIAL | 3 | #37, #83, #85 |
| LOST_SCOPE | 0 | — |
| INTENTIONALLY_DROPPED | 0 | — |

## PARTIAL gap reconciliation (Wave 11 closing PRs)

Per A9's anti-rubber-stamp verifier verdict and `feedback_weakness_correction.md` ("every weakness/audit-finding must be fixed in a PR, not noted-and-skipped"), each of the 3 PARTIAL items has a single-issue Wave 11 closing PR. None of these are feature PRs — they are targeted fixes of the specific weakness A9 surfaced.

### #37 — ServiceHealthPage UI-side Playwright spec missing at HEAD

- **A9 quote (literal):** "PR#42 body references `03_implementation/ui/tests/visual/health-page.spec.ts` but only the FastAPI smoke `04_testing/playwright/specs/health-page.spec.ts` exists. UI E2E coverage is not verified at HEAD."
- **Closing PR:** **W11-2** — adds the missing 1 file `03_implementation/ui/tests/visual/health-page.spec.ts` (~80 LoC) referencing existing `data-testid` hooks already in `ServiceHealthPage.tsx`/`ServiceCard.tsx`/`StatusPill.tsx`. No production code change.
- **Closes:** the gap row above for #37 (ServiceHealthPage UI Playwright).

### #83 — `code.git.*` test-coverage thinness

- **A9 quote (literal):** "A3 said 'test_code_operator.py — 6 occurrences of git_create_branch/git_commit_owned/...'. Actual: 1 occurrence (`test_git_commit_rejects_spoofed_actor_fields`). Production code DOES contain all 6 contract names in `code_history.py`/`code_operator.py`/`agents.py` — substantive scope is preserved, just not test-asserted as A3 implied."
- **Closing PR:** **W11-3** — adds 5 unit-test cases in `04_testing/pytest/unit/test_code_operator.py`, one per missing contract: `test_git_create_branch_rejects_unsafe_prefix`, `test_git_readiness_returns_clean_status`, `test_git_stage_owned_blocks_unowned_files`, `test_git_push_refuses_dirty_worktree`, `test_git_open_pull_request_uses_body_file`. Each test invokes the existing route with mocked fs/subprocess; no new production code.
- **Closes:** the gap row above for #83 (assertion coverage).

### #85 — Replacement-PR body attribution gap

- **A9 quote (literal):** "A3 cited #84/#104/#107/#112/#124/#145/#148 as superseders. A9 found none of those PR bodies contain explicit 'supersedes #85' string. Production scope (`code.teams.*`, `run_coding_pass`, `run_review_pass`, MiniMax+DeepSeek artifact recording) IS in catalog and exercised by tests; attribution provenance broken."
- **Closing PR:** **this PR** (W11-4) — documentation-only. The ledger row above for #85 records the fold-in chain attribution explicitly (#84 team assignment → #104 provider smoke → #107/#112/#124/#145/#148 hardening chain), satisfying `feedback_weakness_correction.md` "fix in a PR" without a substantive code change.
- **Closes:** the gap row above for #85 (provenance attribution).

## See also

- [`CLOSED_UNMERGED_PR_SUPERSESSION_AUDIT_2026-05-10.md`](./CLOSED_UNMERGED_PR_SUPERSESSION_AUDIT_2026-05-10.md) — the canonical Wave 10 synthesis (A1-A9 unified) that this ledger summarizes per row.
- `W10_A1_PR_METADATA_2026-05-10.md` — `gh pr view` snapshot for all 19 PRs (titles, base/head, closure timestamps, diffs, last comments).
- `W10_A2_SOURCE_OS_RUNNER_AUDIT_2026-05-10.md` — proof for #88, #90, #92, #94, #96, #98, #100.
- `W10_A3_HERMES_AGENT_WORKBENCH_AUDIT_2026-05-10.md` — proof for #83, #85, #103.
- `W10_A4_RECOVERY_FIRST_PROOF_AUDIT_2026-05-10.md` — proof for #126, #127, #129, #130.
- `W10_A5_GUI_REF_PACK_AUDIT_2026-05-10.md` — proof for #128, #131.
- `W10_A6_PR37_SCAFFOLD_AUDIT_2026-05-10.md` — proof for #37 (3 sub-scopes).
- `W10_A7_PR168_170_AUDIT_2026-05-10.md` — proof for #168, #170.
- `W10_A8_OPEN_PR_DEPENDENCY_MAP_2026-05-10.md` — open-PR merge order at audit time.
- `W10_A9_PROOF_VERIFICATION_2026-05-10.md` — anti-rubber-stamp verifier (the doc that surfaced the 3 PARTIAL marks this ledger's reconciliation section closes).

## Sources

1. **Wave 10 audit set (A1-A9 + synthesis)** — empirical audit of all 19 closed-unmerged PRs in scope; `pytest`-verified per-claim proof. Owns the verdicts, replacement-PR citations, and proof file paths cited in this ledger. Quotes in §"PARTIAL gap reconciliation" are literal from `W10_A9_PROOF_VERIFICATION_2026-05-10.md` §5 ("Notable findings") and `CLOSED_UNMERGED_PR_SUPERSESSION_AUDIT_2026-05-10.md` §"Contradictions found and resolved".
2. **ITIL incident-registry pattern (ITIL 4)** — the framework for an incident closure ledger keyed by original incident → resolving change/work-item, cross-referencing both the resolution provenance and the categorical disposition (`SUPERSEDED_*`, `LOST_SCOPE`, `INTENTIONALLY_DROPPED`). The schema in §"Schema" follows this pattern: each closed-unmerged PR is an "incident" (closed without resolution by its original work order), each merged successor PR is a "resolving change", and the `status`/`proof` columns are the disposition + post-implementation review evidence respectively. Reference: `https://www.axelos.com/certifications/itil-service-management/`. (Free-tier reference doc; no paid services per `feedback_no_paid_services.md`.)

## Constraints honored

- **DOC-ONLY PR.** No source/test edits.
- **No secrets.** No `.env`, no token values, no URL credentials.
- **Hermes MCP locks.** This doc + the audit synthesis (link section only) are locked under `claude-w11-4-pr85`.
- **Quotes literal.** All A9/synthesis quotations are byte-identical to the source documents.
- **Free-tier sources only.** ITIL reference is the public Axelos certification page; no paid registration required to read the supersession-vs-lost-scope distinction.

---

*Generated 2026-05-10 — Wave 11 Agent 4.*
