# Phase 0 Proof Baseline

> **Verdict:** This document is the proof claim for Phase 0 — the foundation audit before Phase 1 (registry validator) implementation begins. The Phase 0 signed bundle attaches to the PR (not a GitHub Release — rc1 is the only public artifact for v5.3.0-rc1).

## 1. The claim

Phase 0 is "done" when ALL of the following are simultaneously true:

| # | Claim | Verifier |
|---|---|---|
| 1 | Five canonical baseline reports exist on `feat/phase-0-foundation-baseline` | `git ls-tree feat/phase-0-foundation-baseline -- <paths>` |
| 2 | Each of the six audit domains has at least an AMBER+GO verdict (no RED) | reports themselves |
| 3 | No source code under `03_implementation/src/hermes3d/` was modified vs `develop` | `git diff develop...feat/phase-0-foundation-baseline -- 03_implementation/src/hermes3d/` returns empty |
| 4 | No CI workflow under `.github/workflows/` was modified vs `develop` | `git diff develop...feat/phase-0-foundation-baseline -- .github/` returns empty |
| 5 | No script under `scripts/` was modified vs `develop` | `git diff develop...feat/phase-0-foundation-baseline -- scripts/` returns empty |
| 6 | No kit doc was modified | `git diff develop...feat/phase-0-foundation-baseline -- hermes3d_gui_contract_kit_v4.1/` returns empty |
| 7 | rc1 tag and release branch are unchanged | `git rev-parse v5.3.0-rc1` == `6dd9e01...` AND `git rev-parse release/v5.3.0-rc1` == `6dd9e01...` |
| 8 | A signed Phase 0 proof bundle exists, verifies, and pins the branch HEAD | `python 05_truth_proof/conformance_runner.py --bundle <path>` returns `OK` |

If any one of those is false, Phase 0 is not provable and the PR must not merge.

## 2. Required artifacts

| Artifact | Path | Producer | Verifies |
|---|---|---|---|
| Branch HEAD SHA | `feat/phase-0-foundation-baseline` HEAD | git | foundation work locked to a commit |
| Phase 0 baseline report | [`00_overview/PHASE0_BASELINE_REPORT.md`](../00_overview/PHASE0_BASELINE_REPORT.md) | coordinator | top-level synthesis of all 6 audit domains |
| External tool registry audit | [`01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`](../01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md) | coordinator (informed by Agent 3) | external tool coverage + validator state |
| Dual-edition env baseline | [`02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md`](../02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md) | coordinator (informed by Agent 2) | env detection plan + reference host |
| Adapter registry README | [`03_implementation/adapter_registry/README.md`](../03_implementation/adapter_registry/README.md) | coordinator (informed by Agent 4) | adapter taxonomy, surface, lifecycle, schemas |
| Phase 0 proof claim | this document | coordinator (informed by Agent 6) | the proof claim itself + verification commands |
| Per-agent findings (working notes, gitignored) | `var/phase0-agents/agent-{1..6}-*.md` | 6 audit agents | independent audit evidence, retained locally |
| Phase 0 signed bundle | `05_truth_proof/bundles/<sha-prefix12>-<utc-stamp>.zip` | `scripts/build-bundle.sh` | HMAC-SHA256 signed snapshot of the foundation state |

The `var/phase0-agents/` working notes are excluded from git per `.gitignore` line 21 (`var/`). The 5 canonical reports stand alone — they include enough excerpt and line-cite evidence that an outside reviewer can re-derive the conclusions without those private notes.

## 3. Verification commands

Run from a fresh clone:

```bash
# 0. Pin the commit under audit
git checkout feat/phase-0-foundation-baseline
git rev-parse HEAD                                          # capture as $PHASE0_SHA

# 1. Confirm the 5 canonical reports exist
git ls-tree -r --name-only HEAD -- \
  00_overview/PHASE0_BASELINE_REPORT.md \
  01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md \
  02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md \
  03_implementation/adapter_registry/README.md \
  05_truth_proof/PHASE0_PROOF_BASELINE.md

# 2. Confirm no source / workflow / script / kit drift from develop
git diff --stat develop...feat/phase-0-foundation-baseline -- \
  03_implementation/src/hermes3d/ \
  scripts/ \
  .github/ \
  hermes3d_gui_contract_kit_v4.1/
# Expect: empty (no diff)

# 3. Confirm rc1 tag and release branch are immutable.
# Note: v5.3.0-rc1 is an annotated tag, so `git rev-parse v5.3.0-rc1`
# returns the tag-object SHA, not the commit. Use ^{commit} to resolve
# to the actual commit it points at.
[ "$(git rev-parse v5.3.0-rc1^{commit})" = "6dd9e01f4e090663c7fdd87bb968f37b512de7ca" ] && echo "rc1 tag OK"
[ "$(git rev-parse release/v5.3.0-rc1)" = "6dd9e01f4e090663c7fdd87bb968f37b512de7ca" ] && echo "rc1 branch OK"

# 4. Run the kit's own gates from this branch (must pass)
bash hermes3d_gui_contract_kit_v4.1/scripts/run_v4_1_gates.sh
python hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py \
  hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml

# 5. Build + verify the Phase 0 bundle
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  bash scripts/build-bundle.sh --output 05_truth_proof/bundles/
# Capture the printed bundle path as $BUNDLE
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python 05_truth_proof/conformance_runner.py --bundle "$BUNDLE"
# Expect: "OK — signature + file hashes + cross-refs verified"
```

If every command above succeeds, the Phase 0 claim is provable.

## 4. Bundle plan

- **Use existing `scripts/build-bundle.sh` as-is.** No script changes for Phase 0. The script already:
  - Captures git branch + commit + dirty flag
  - HMAC-SHA256 signs with `HERMES3D_PROOF_KEY` env var (default literal is acceptable for non-GA bundles)
  - Outputs to `05_truth_proof/bundles/<sha-prefix12>-<utc-stamp>.zip`
  - Pairs with `05_truth_proof/conformance_runner.py` for verification
- **Naming convention:** `<branch-head-sha-prefix12>-<utc-timestamp>.zip` — same as rc1.
- **Where attached:** the **Phase 0 PR** (uploaded to PR description / commit, not a GitHub Release). rc1 is the only public release for v5.3.0-rc1; Phase 0 is an internal milestone bundle.
- **Bundle file is NOT committed to the repo** (`05_truth_proof/bundles/*.zip` is gitignored per `.gitignore` line 70). Capture the path + sha256 in the Phase 0 PR description so the bundle is verifiable from the recorded checksum.

## 5. `HERMES3D_PROOF_KEY` policy

- **Default:** `b"hermes3d-default-proof-key-not-secret"` (literal in `scripts/_build_bundle.py:38`). The literal name self-documents that it is not secret.
- **Phase 0 (this bundle):** default key is acceptable. Internal milestone bundle, not GA.
- **rc1 (already shipped):** Wave B Auditor verified the rc1 bundle signed with this default. Acceptable for RC.
- **GA (v5.3.0 and later):** MUST override with a real, kept-secret key:
  ```bash
  export HERMES3D_PROOF_KEY="$(cat ~/.hermes3d/release-signing-key)"
  bash scripts/build-bundle.sh
  ```
  Failure to override before tagging GA is a release-blocking violation. The release runbook (Phase 5 deliverable) must surface this as a checklist item.

## 6. rc1 non-disturbance check

Phase 0 work touches only:
- `00_overview/PHASE0_BASELINE_REPORT.md` (new)
- `01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md` (new)
- `02_architecture/DUAL_EDITION_ENVIRONMENT_BASELINE.md` (new)
- `03_implementation/adapter_registry/README.md` (new — directory was pre-created by coordinator, otherwise empty)
- `05_truth_proof/PHASE0_PROOF_BASELINE.md` (new — this file)

Phase 0 work explicitly DOES NOT touch:
- `release/v5.3.0-rc1` branch
- `v5.3.0-rc1` tag
- any source code under `03_implementation/src/hermes3d/`
- `.github/workflows/`
- `scripts/` (only consumed for verification — no edits)
- `hermes3d_gui_contract_kit_v4.1/` (kit treated as immutable spec)

The PR targets `develop`, not `release/*`.

**Confirmed: Phase 0 cannot regress rc1.** The two artifacts are orthogonal; a fresh-clone reviewer can validate this with `git diff` (command 2 in §3).

## 7. Findings (proof axis)

| # | Severity | Finding |
|---|---|---|
| 1 | INFO | Existing build-bundle infrastructure is sufficient for Phase 0. No script changes required. |
| 2 | INFO | `var/phase0-agents/` is gitignored — agent findings files are private working notes. The 5 canonical reports stand alone. |
| 3 | LOW | `HERMES3D_PROOF_KEY` GA-override requirement is now documented (this file §5). Propagate into the v5.3.0 release runbook when authored. |
| 4 | LOW | Phase 0 bundle file itself is gitignored (`*.zip` under `05_truth_proof/bundles/`). Capture path + sha256 in the Phase 0 PR description so the bundle is verifiable from a fresh clone via the recorded checksum. |

## 8. Phase 1 readiness (proof axis)

**GO** — proof infrastructure is ready, the Phase 0 proof claim is well-defined, rc1 is provably untouched, and a verifiable signed bundle attaches to the PR.

## 9. Cross-links

- Existing proof infrastructure: [`scripts/build-bundle.sh`](../scripts/build-bundle.sh), [`scripts/_build_bundle.py`](../scripts/_build_bundle.py), [`scripts/truth-gate.sh`](../scripts/truth-gate.sh), [`05_truth_proof/conformance_runner.py`](conformance_runner.py)
- Kit proof specs: [`PROOF_BUNDLE_SPEC.md`](../hermes3d_gui_contract_kit_v4.1/05_truth_proof/PROOF_BUNDLE_SPEC.md), [`PHASE_PROOF_BUNDLE_CHECKLIST.md`](../hermes3d_gui_contract_kit_v4.1/05_truth_proof/PHASE_PROOF_BUNDLE_CHECKLIST.md), [`EVIDENCE_LEDGER_TEMPLATE.md`](../hermes3d_gui_contract_kit_v4.1/05_truth_proof/EVIDENCE_LEDGER_TEMPLATE.md), [`DUAL_EDITION_PROOF_BUNDLE.md`](../hermes3d_gui_contract_kit_v4.1/05_truth_proof/DUAL_EDITION_PROOF_BUNDLE.md), [`SECURITY_AND_SAFETY_POLICY.md`](../hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md)
- rc1 release: [github.com/Ghenghis/Hermes3D/releases/tag/v5.3.0-rc1](https://github.com/Ghenghis/Hermes3D/releases/tag/v5.3.0-rc1)
- Phase 0 baseline: [`00_overview/PHASE0_BASELINE_REPORT.md`](../00_overview/PHASE0_BASELINE_REPORT.md)
