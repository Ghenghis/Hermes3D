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
| **B — v5.3 product build** | in progress: B-PR4 promotes the LangGraph runtime + real multi-agent loop |

### Phase B status (2026-04)

- `core/agents/orchestrator.py` — **runnable**. `LangGraphOrchestrator.run(state, *, max_steps, checkpoint_dir)` drives the 12-node `print_workflow` graph. With the optional `[langgraph]` extra installed it builds a real `StateGraph` (conditional edges + checkpointer); without it, transparently falls back to the hand-rolled `WorkflowGraph` and emits a `LangGraphUnavailableWarning`. Final state always carries `terminal=True`, `aborted: bool`, and `node_results` (alias of `history`).
- `core/agents/multi_agent.py` — **runnable**. New `MultiAgentLoop` runs Executor → Critic → Optimizer against any configured LLM provider (Ollama by default) and captures prompt/response/latency/token-count per round. When no backend is reachable it returns `outcome="no-llm"` instead of failing.
- `print_workflow.run_with_langgraph(state)` is the public entry point that wires the orchestrator into the existing pipeline; the legacy `WorkflowGraph` path is preserved as the default.
- New agent manifests: `agents/orchestrator.yaml`, `agents/multi_agent.yaml` (12/12 manifests valid).
- Optional install: `pip install -e ".[langgraph]"` or `".[all]"`.

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
pip install -e ".[all]" && pytest -q

# 4. Or — for non-coders — guided wizard (zero to UI)
bash scripts/wizard.sh
```

## Repository layout

```
00_overview/contract/   binding contract: master spec, ledger, manifest, gates
01_requirements/        product README, AI programmer + agentic + brain + fleet guides
02_architecture/        ARCHITECTURE.md, SECURITY, TROUBLESHOOTING, CHANGELOG, diagrams
03_implementation/      runnable codebase
  src/hermes3d/         75+ modules, 12-printer fleet, 8 dispatch strategies
  config/               printer + slicer + skill-pack configs
04_testing/             tests
  pytest/               unit + conformance + integration
  acceptance/           48-cell desk-organizer acceptance suite
  (playwright/          to be added in PR #3)
05_truth_proof/         PROOF_PROTOCOL, bundle conformance verifier, evidence schemas, bundles/
06_release/             rollback runbook, branch strategy, release docs
  installer/            cross-platform installer + verify_install
agents/                 machine-readable agent role manifests
scripts/                top-level entry scripts (preflight, wizard, build-bundle, hooks)
  scaffolding/          scaffolding-era scripts (test, build, lint, release, doctor, ...)
env/                    environment templates
var/                    runtime artifacts (gitignored)
```

## Truth + proof

Every dispatch, acceptance, and release emits an HMAC-SHA256 signed proof envelope
(`HERMES3D_PROOF_KEY`). Per-build aggregated proof bundles (zip with logs +
screenshots + test reports + signed manifest) land in `05_truth_proof/bundles/`
via `bash scripts/build-bundle.sh`.

The product is offline-capable. No telemetry, no cloud requirement, no vendor
lock-in. See [`00_overview/contract/MASTER_CONTRACT.md`](00_overview/contract/MASTER_CONTRACT.md)
§0–§44 for the binding spec.

## License + delivery

See [`HERMES3D_DELIVERY_README.md`](HERMES3D_DELIVERY_README.md) for the
delivered v5 zip, full file inventory, and how-to-verify procedure.
