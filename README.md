# Hermes3D-OS

Agentic 3D-printing orchestration layer for a 12-printer Klipper/Moonraker farm.
Validates print safety, dispatches jobs by 8 strategies, manages spool inventory,
predicts failures, learns from outcomes, signs every decision with HMAC-SHA256.

**Repo:** `Ghenghis/Hermes3D` · **Active branch:** `develop` (integration)

---

## Status

| Macro-phase | Status |
|---|---|
| **v5.0 baseline** | tagged `v5.0.0-baseline` (initial commit `13c04e6`) |
| **A — Kit hardening** | in progress on `feat/kit-hardening-v5.3` |
| **B — v5.3 product build** | queued (post-A) |

The kit's pre-hardening state, gap inventory, and rubric assessment live in
[`var/audit/baseline_v5.0.md`](var/audit/baseline_v5.0.md).

## Branch strategy (gitflow)

```
main         ← production. Protected. Only release/* and hotfix/* may merge here.
develop      ← integration. All feature branches merge here first.
feat/<area>/<desc>   ← features. PR → develop.
release/v<x.y.z>     ← release prep. PR → main + develop.
hotfix/<id>          ← production fixes. PR → main + develop.
```

Direct pushes to `main` are blocked at three layers:
- local **pre-push hook** (`.githooks/pre-push`)
- **branch-guard CI workflow** (`.github/workflows/branch-guard.yml`)
- repository branch-protection rules (set via `gh repo edit`)

Open a feature branch with `bash scripts/new-feature.sh <area> <short-desc>`.

## Quick start

```bash
# 1. Validate environment
bash scripts/preflight.sh

# 2. Install hooks (one-time, project-local; does not touch global git)
bash scripts/install-hooks.sh

# 3. Install Python deps + run tests
cd 02-SCAFFOLDING && pip install -e ".[all]" && pytest -q && cd ..

# 4. Or — for non-coders — guided wizard (zero to UI)
bash scripts/wizard.sh
```

## Repository layout (current; A.1 restructure pending)

```
00-CONTRACT/         contract docs, manifest, ledger, gates
01-ARCHITECTURE/     architecture diagrams (.mmd source)
02-SCAFFOLDING/      runnable codebase, tests, CI, scripts
  src/hermes3d/      75 modules, 12-printer fleet, 8 dispatch strategies
  tests/             unit + conformance + integration
03-PROOF-SYSTEM/     PROOF_PROTOCOL + bundle conformance verifier
04-TEST-CASE-DESK-ORGANIZER/   48-cell acceptance suite
05-INSTALLER/        cross-platform installer + verify
06_release/          rollback runbook, branch strategy, release artifacts (new)
07-DOCS/             architecture, security, troubleshooting, guides
agents/              machine-readable agent role manifests (new in A.2)
scripts/             top-level entry scripts (preflight, wizard, build-bundle, hooks)
var/                 runtime artifacts (gitignored)
```

A planned restructure to `00_overview / 01_requirements / 02_architecture / 03_implementation / 04_testing / 05_truth_proof / 06_release / agents / scripts` will land as a dedicated PR (`feat/kit-restructure-A1`) after the additive hardening work merges to `develop`.

## Truth + proof

Every dispatch, acceptance, and release emits an HMAC-SHA256 signed proof envelope
(`HERMES3D_PROOF_KEY`). Per-build aggregated proof bundles (zip with logs +
screenshots + test reports + signed manifest) land in `05-truth-proof/bundles/`
via `bash scripts/build-bundle.sh`.

The product is offline-capable. No telemetry, no cloud requirement, no vendor
lock-in. See [`00-CONTRACT/MASTER_CONTRACT.md`](00-CONTRACT/MASTER_CONTRACT.md)
§0–§44 for the binding spec.

## License + delivery

See [`HERMES3D_DELIVERY_README.md`](HERMES3D_DELIVERY_README.md) for the
delivered v5 zip, full file inventory, and how-to-verify procedure.
