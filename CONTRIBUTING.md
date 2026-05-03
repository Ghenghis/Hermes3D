# Contributing to Hermes3D-OS

Thanks for your interest. This guide is the canonical contributor brief — branch model, CI layer map, evidence discipline, and dev-quickstart. The marketing-grade overview lives in [`README.md`](./README.md); the dev-internal mechanics live here.

---

## Branch model (gitflow)

```text
main         ← production. Protected. Only release/* and hotfix/* may merge.
develop      ← integration. All feature branches merge here first.
feat/<area>/<desc>   ← features. PR → develop.
release/v<x.y.z>     ← release prep. PR → main + develop.
hotfix/<id>          ← production fixes. PR → main + develop.
```

**Direct pushes to `main` are blocked at three layers** — a local pre-push hook, the `branch-guard` CI workflow, and GitHub branch-protection rules. Always work on a feature branch and PR into `develop`.

Branch naming:

- `feat/<area>/<short-desc>` for new functionality
- `fix/<area>/<short-desc>` for bug fixes
- `docs/<short-desc>` for documentation-only changes
- `chore/<short-desc>` for tooling and scaffolding

---

## CI layer map

Every PR into `develop` runs the full CI matrix. All layers must pass.

| Layer | Scope | Runs on |
| --- | --- | --- |
| **A** | Static gates — `ruff format` · `ruff check` · `mypy` · forbidden-pattern scan | Every PR |
| **B** | Smoke + acceptance — 4 cells: ubuntu/windows × py3.11/3.12 | Every PR |
| **C** | Integration — real adapter I/O (Linux only) | Every PR |
| **D** | UI E2E — Playwright + Gradio launcher | Every PR |
| **D3** | Gradio launcher smoke (advisory until stability data confirms) | Every PR |
| **E** | Release dry-run | `release/*` branches |
| **F** | Honesty gates — regenerate manifest + claim audit | Every PR |
| **M** | Matrix coverage — silent-regression catch | Every PR |
| **T** | Unified truth gate — consolidated proof bundle | Every PR |
| **W** | Wizard E2E — recorded universal-setup-wizard run | Every PR |

The unified Layer T runs the same 17 truth gates that re-prove the system on every push to `main`. See [`PROOF_E2E_REPORT.md`](./PROOF_E2E_REPORT.md) for the latest run.

---

## Dev quickstart

```bash
git clone https://github.com/Ghenghis/Hermes3D
cd Hermes3D
git checkout develop

# Editable install with the dev + UI extras
pip install -e ".[dev,ui]"

# Cross-platform prereq probe (returns JSON envelope)
python scripts/scaffolding/doctor.py --json

# Full unit + acceptance suite
pytest -q

# CLI smoke
hermes3d truth-gate ./mymesh.stl

# Launch the Gradio UI
python -m hermes3d.app.launcher    # → http://127.0.0.1:7860
```

Wire the MCP server into every supported AI client with the universal setup wizard:

```bash
npm run wizard --prefix ../HermesProof
```

---

## Repository layout

```text
00_overview/        Phase plans, contracts, roadmap, honesty ledger
01_research/        Research artifacts feeding architecture decisions
02_architecture/    ADRs · diagrams · contracts · API surface
03_implementation/  Source: hermes3d/ package, config/, ui/
04_testing/         pytest suites · Playwright E2E · matrix fixtures
05_proof/           PROOF/latest.json · proof verifier · gates
06_release/         PyInstaller spec · Velopack · Hostinger VPS bundle
handoffs/           Open architect → implementer briefs
site/               Marketing landing page (GH Pages, ./site/)
```

---

## Truth + proof discipline

Every change must keep the truth chain unbroken. Specifically:

- **Honesty ledger** — every user-visible claim is enumerated in [`00_overview/contract/HONESTY_LEDGER.md`](./00_overview/contract/HONESTY_LEDGER.md) with status (REAL · PARTIAL · DISABLED). PRs that change behavior must update the ledger in the same commit.
- **Proof envelope** — [`PROOF/latest.json`](./PROOF/latest.json) is regenerated on every push to `main` and signed via Sigstore (keyless OIDC). Don't hand-edit it.
- **Evidence-backed phase reports** — [`00_overview/`](./00_overview/) holds Phase 1 → 5.1 reports. Each cited result must link to a reproducible artifact.
- **No "Coming Soon" buttons.** If a feature isn't real, disable it conspicuously with an explanation.

---

## Phase status

**Current sprint:** Phase 5.1 — kit hardening. Plan: [`00_overview/PHASE5_1_PLAN.md`](./00_overview/PHASE5_1_PLAN.md).

Open architect → implementer briefs live at [`handoffs/`](./handoffs/). Pick one matching your owner ID (e.g. `codex-impl-04`) and follow the structured pre-flight (`hermes_doctor` → `hermes_pick_task`).

---

## Multi-agent contract

Hermes3D is governed end-to-end by [HermesProof](https://github.com/Ghenghis/HermesProof). When multiple AI agents (Claude, Codex, Cursor, Windsurf, VS Code Copilot, Kilo Code) work on the repo concurrently:

- **Claim** the task before editing — `hermes_claim_task` with your owner ID
- **Lock** the files you touch — `hermes_lock_files` (TTL'd, heart-beated)
- **Hand off** explicitly when done — `hermes_request_handoff` → `hermes_approve_handoff`
- **Append evidence** as you go — `hermes_append_evidence` builds a hash-chained ledger
- **Run gates** before claiming completion — `hermes_run_gate` validates against the 17-gate suite

The lock layer guarantees that concurrent agents don't clobber each other's work. See HermesProof's `AGENTS.md` for the full contract.

---

## License

By contributing, you agree your contributions will be licensed under the MIT License (see [`LICENSE`](./LICENSE)).
