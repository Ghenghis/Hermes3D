# Hermes3D-OS — Contract Kit Hardening + v5.3 Product Build

## Context

The Hermes3D-OS Lite v5 kit at `G:\Github\Hermes3D` is delivered with documentation
claiming 264/264 tests, all green, "FINAL." Ground-truth audit shows it's **~70–75%
complete against the user's actual rubric** (agent-executability + proof enforcement),
not against lines-of-code. The honesty ledger and READMEs accurately describe code
but the kit fails the user's 7-criteria readiness rubric:

1. **Structural** — phase folders not aligned with `/00_overview … /06_release /agents /scripts`
2. **Agent execution readiness** — no machine-readable agent role manifests with I/O contracts
3. **Truth/proof gates** — STL truth gates exist, but **no Playwright UI E2E**, no screenshot diffing, no blocking enforcement on UI surfaces
4. **Self-correction/recovery** — no retry-budget controller, no Repair agent role
5. **Branch discipline** — no enforced "never main" git policy, no pre-push hook, no rollback runbook
6. **Evidence ledger** — HMAC proof envelopes exist per dispatch, but no per-build **proof bundle zip** with logs+screenshots+commit hash+test report
7. **End-to-end non-coder flow** — `run.bat` exists but no guided wizard / failure recovery for non-technical operators

Concrete code gaps from audit:
- `core/agents/orchestrator.py:180` — `LangGraphOrchestrator.run` raises `NotImplementedError`
- `core/modeling/blender_mcp_server.py` — 4 tool fns raise `NotImplementedError`
- `core/integrations/remote_control.py:91-100` — Telegram/Discord routing partial
- `pyproject.toml` — `matplotlib` missing → integration test collect fails on clean clone
- `02_architecture/diagrams/` — empty
- `app/launcher.py` — 1 of 4 tabs disabled; v5.1 promised 6 more tabs (dispatch, skill browser, incident log, remote-control test, LLM provider switcher, calibration timeline)
- LangGraphOrchestrator + Blender MCP are deferred to v5.2; v5.3 promises live cost widget + spool deduction trace + failure forecast tile + calibration history per printer

**User decisions captured:**
- Phase 2 target = Promote Hermes3D-OS to v5.3 production
- Folder layout = restructure to `/00_overview … /06_release /agents /scripts`
- Proof stack = Playwright UI E2E + screenshots (rubric also mandates pre-push git hooks, per-build proof bundle, retry/repair framework — all included as non-negotiable per the user's stated rubric)

The work is split into two macro-phases: **A) Kit Hardening (close the 25–30%)**,
**B) v5.3 Product Build (promote scaffold tabs + deferred modules to runnable)**.
Each macro-phase is decomposed into the user's Phase 0–5 model.

---

## Macro-Phase A: Kit Hardening (close the 25–30% gap)

### A.0 Preflight — environment + audit baseline
- `scripts/preflight.{ps1,sh}` — checks Python 3.11, git, Node 20+ (for Playwright), Blender (optional), Ollama (optional). Emits JSON capability report to `var/preflight/<timestamp>.json`.
- Snapshot current test state: `pytest --collect-only -q` → `var/audit/baseline.txt`.
- Snapshot current honesty ledger; freeze as `00_overview/audit_baseline.md`.
- **Gate A0**: preflight JSON shows Python+git+Node present; if not, halt with remediation steps.

### A.1 Restructure to user's folder schema
Reorganize repo (git mv preserves history). Mapping:
```
00_overview/contract          → 00_overview/contract/
02_architecture      → 02_architecture/
03_implementation/src   → 03_implementation/src/
04_testing/pytest → 04_testing/pytest/
scripts/scaffolding→ scripts/scaffolding/
05_truth_proof      → 05_truth_proof/
04-TEST-CASE-...     → 04_testing/acceptance/
06_release/installer         → 06_release/installer/
07-DOCS              → 01_requirements/ + 02_architecture/docs/
```
New top-level dirs added:
- `agents/` — agent role manifests (YAML), one file per role
- `scripts/` — top-level entry scripts (preflight, run-all, build-bundle)
- `04_testing/playwright/` — UI E2E suite (new)
- `05_truth_proof/bundles/` — per-build proof bundle output

Update: `pyproject.toml` package paths, `pytest.ini`, `.github/workflows/ci.yml`, all
scripts that reference old paths, `KIT_MANIFEST.json`, all docs cross-refs.

**Critical files modified:**
- `pyproject.toml` (package roots)
- `scripts/scaffolding/*.{sh,ps1}` (path constants)
- `.github/workflows/ci.yml`
- `00_overview/contract/KIT_MANIFEST.json`
- All `07-DOCS/*.md` (cross-refs)

**Gate A1**: `pytest` still collects same number of tests post-move; `python -m hermes3d --help` works.

### A.2 Agent role manifests (`/agents/`)
Create one YAML per agent role, executable by Claude Code multi-agent (or any
orchestrator). Each manifest:
```yaml
role: QA
model: sonnet|opus|haiku
inputs:
  - name: built_ui_url
    type: url
    required: true
action_sequence:
  - run: scripts/playwright-suite.sh
outputs:
  - path: var/proof-bundles/{run_id}/playwright-report.html
  - path: var/proof-bundles/{run_id}/screenshots/
gates:
  - name: pass_rate
    threshold: 100
    blocking: true
retry_policy:
  max_retries: 3
  backoff: exponential
escalate_to: Repair
```

Roles to define (initial set):
- `Architect`, `Implementer`, `QA`, `Repair`, `Reviewer`, `Releaser`, `Auditor`,
  `Preflight`, `BranchGuard`, `BundleSigner`

Reference existing patterns: `03_implementation/src/hermes3d/core/agents/multi_agent.py`
(Critic/Optimizer/Executor) — reuse the role-protocol shape; do not reinvent.

**Gate A2**: every role manifest validates against `agents/_schema.json`; CI step
`python scripts/validate-agents.py` passes.

### A.3 Truth/proof gates — Playwright + screenshot diffing
- `04_testing/playwright/` — new Node project. Install Playwright (Chromium only).
- Test specs covering every Gradio tab + every FastAPI endpoint that returns HTML/JSON:
  - `truth-gate-tab.spec.ts`
  - `desk-organizer-tab.spec.ts`
  - `dry-run-pipeline.spec.ts`
  - `fleet-dashboard.spec.ts` (B-phase tab; spec written now, gated as `xtest` until tab lands)
  - `api-health.spec.ts`, `api-fleet.spec.ts`, `api-dispatch.spec.ts`
- Each test: navigate → assert DOM → screenshot → diff against `04_testing/playwright/__snapshots__/`
- `playwright.config.ts` — fail on console errors, fail on missing assets (404s).
- New script `scripts/run-e2e.{ps1,sh}` — boots Gradio + FastAPI, waits for health, runs Playwright, tears down.

**Gate A3**: `scripts/run-e2e.sh` exits 0 with 100% pass; any console.error or 404 fails the build.

### A.4 Retry/repair framework
- New module `03_implementation/src/hermes3d/core/orchestration/retry_controller.py`:
  - `RetryBudget(max_retries, backoff)`, `@with_retry` decorator, `RepairEscalation` exception
- New module `core/orchestration/repair_agent.py`:
  - Inputs: failure context (logs, last good state)
  - Tries: known-fix lookup in skill_store → LLM-generated patch → escalate to human via notifier
- Wire into `print_workflow.py` 12-node pipeline: every node runs under `@with_retry`; on terminal failure, RepairAgent invoked.
- Tests: 3 unit tests + 1 integration test simulating slicer crash → repair → recovery.

**Gate A4**: `pytest 04_testing/pytest/test_retry_controller.py` green; integration test recovers from injected slicer fault.

### A.5 Branch discipline + safety
- `.husky/pre-push` (or `.git/hooks/pre-push` installed by `scripts/install-hooks.sh`):
  - Reject push if branch ∈ {`main`, `master`}
  - Require tests passing locally (runs `scripts/test.sh --fast`)
- `.github/workflows/branch-guard.yml` — refuses direct push to main; PR-only.
- `06_release/ROLLBACK_RUNBOOK.md` — written procedure: previous-tag rollback, proof bundle reference, communication template.
- `scripts/new-feature.{ps1,sh}` — wizard that creates + switches to feature branch, with naming convention `feat/<area>/<short-desc>`.

**Gate A5**: pre-push hook actively blocks a test push to main; CI workflow blocks PRs that target main from main.

### A.6 Per-build proof bundle
- New script `scripts/build-bundle.{ps1,sh}` — runs after green CI/local build, produces `05_truth_proof/bundles/<git-sha>-<utc>.zip` containing:
  - `manifest.json` (commit hash, branch, build time, env fingerprint, signer identity)
  - `tests/pytest-report.xml`, `tests/playwright-report.html`, `tests/screenshots/`
  - `logs/build.log`, `logs/install.log`, `logs/runtime-smoke.log`
  - `proof/envelopes/*.json` (existing HMAC envelopes)
  - `evidence_ledger.md` (auto-generated: every claim → its proof file path)
  - `.sig` (HMAC over manifest.json, key from `HERMES3D_PROOF_KEY`)
- Verifier: extend existing `05_truth_proof/conformance_runner.py` to validate bundle.

**Gate A6**: `python 05_truth_proof/conformance_runner.py --bundle <zip>` validates manifest + signature + cross-refs.

### A.7 Code gaps from audit
- Add `matplotlib>=3.8` to `pyproject.toml` `[project.optional-dependencies].ui` and `.all`.
- Implement Telegram/Discord routing in `core/integrations/remote_control.py:91-100` — finite command table mapped to existing tool registry; tests use mock transports.
- Render at least one Mermaid → SVG diagram into `02_architecture/diagrams/` (system context); leave roadmap-tier diagrams as `.mmd` source.
- Re-verify clean-clone test count; update HONESTY_LEDGER + README to **actual** number.

**Gate A7**: `pip install -e ".[all]" && pytest -q` collects + passes 100% from a fresh venv on Windows + Linux (CI matrix). Forbidden-pattern scan green.

### A.8 Non-coder flow
- `scripts/wizard.{ps1,sh}` — interactive: detects missing deps, prompts to install, runs preflight, runs first acceptance, shows proof bundle path, opens browser to Gradio UI.
- `06_release/QUICKSTART_NONCODER.md` — 5-step checklist with screenshots for each step.

**Gate A8**: wizard takes a clean Win11 box from zero to seeing the desk-organizer rendered in the UI, with no manual file editing. Recorded as a Playwright test against the wizard transcript.

---

## Macro-Phase B: v5.3 Product Build (Hermes3D-OS itself)

Driven by the hardened kit. Each task gated by A's framework.

### B.0 Preflight
Run `scripts/preflight.sh` against the dev workstation; identify which printers are
reachable on the LAN; record fleet snapshot to `var/fleet-discovery/<utc>.json`.

### B.1 Requirements lock
Promote the user-decision answers + v5.1/v5.2/v5.3 roadmap items into
`01_requirements/v53_scope.md`. Explicit list:
- v5.1: 6 Gradio tabs to runnable (dispatch, skill browser, incident log, remote-control test, LLM provider switcher, calibration timeline) + Layer-D UI smoke + CI matrix Win+Ubuntu × Py3.11+3.12
- v5.2: real LangGraphOrchestrator (replace `NotImplementedError`); real Critic/Optimizer/Executor against Ollama; .skillpack importer wired to UI; tool-registry REPL
- v5.3: live cost-per-hour widget; spool deduction trace; failure forecast tile; calibration history timeline

### B.2 Architecture deltas
For each B.1 item, append a short ADR to `02_architecture/adr/`. ADRs reference
existing modules to reuse:
- LangGraph promotion: reuse `core/orchestration/agent_graph.py` checkpointing
- Cost widget: reuse `core/farm/cost_estimator.py`
- Forecast tile: reuse `core/intelligence/failure_predictor.py`
- Calibration timeline: reuse `core/agents/calibration.py` + `core/farm/print_history.py`

### B.3 Implementation (sequenced by dependency)
Sub-tasks as parallelizable agent jobs:
1. `B3-LG` LangGraphOrchestrator runtime — file `core/agents/orchestrator.py`
2. `B3-RC` Remote-control routing finalization (overlap with A.7)
3. `B3-MC` Multi-agent loop against real Ollama — file `core/agents/multi_agent.py`
4. `B3-SK` .skillpack importer UI hook — file `app/launcher.py` (skill browser tab)
5. `B3-DT` Dispatch tab — `app/launcher.py`
6. `B3-IL` Incident log tab
7. `B3-LP` LLM provider switcher tab
8. `B3-CW` Cost-per-hour widget — `app/launcher.py` farm dashboard
9. `B3-SD` Spool deduction trace — `core/farm/spool_tracker.py` + UI
10. `B3-FF` Failure forecast tile
11. `B3-CT` Calibration history timeline
12. `B3-BL` Blender MCP server — `core/modeling/blender_mcp_server.py` (only if Blender + bpy detected by preflight; otherwise leaves `NotImplementedError` and ledger row stays "spec")

Tasks 1–4 sequentially (B3-LG before B3-MC). Tasks 5–11 in parallel (each Implementer agent gets one tab, isolated by module). B3-BL last (independent).

Every implementation task TDD: write failing test in `04_testing/pytest/` first, then implement.

### B.4 Testing
- Per task: pytest (unit + integration) + new Playwright spec in `04_testing/playwright/`
- Visual regression: each new tab snapshot baselined
- Acceptance runner regression: re-run `04_testing/acceptance/run_acceptance.py` 48-cell — must remain 48/48
- Hardware-in-the-loop optional: if real Moonraker reachable in B.0 discovery, run `04_testing/hardware/` smoke against one printer

### B.5 Truth + proof
- Update `00_overview/contract/HONESTY_LEDGER.md` — every promoted module moves from "spec/scaffold" to "runnable" with new test count
- Build proof bundle for the v5.3 release tag
- Verify: `python 05_truth_proof/conformance_runner.py --bundle <bundle>` green

### B.6 Release / handoff
- Tag `v5.3.0` on feature branch (NOT main; user merges via PR)
- Generate signed wheel + proof bundle in `06_release/dist/`
- Auto-update `CHANGELOG.md`
- Run wizard end-to-end on clean VM; record Playwright transcript as final evidence

---

## Verification (end-to-end)

From a clean clone:
```bash
git clone <repo> hermes3d && cd hermes3d
bash scripts/preflight.sh                           # Gate A0
bash scripts/install-hooks.sh                       # Gate A5
pip install -e ".[all]"                             # Gate A7
pytest -q                                           # Gate A7
bash scripts/run-e2e.sh                             # Gate A3
bash 04_testing/acceptance/run_acceptance.py        # 48/48
bash scripts/build-bundle.sh                        # Gate A6
python 05_truth_proof/conformance_runner.py --bundle 05_truth_proof/bundles/*.zip  # Gate A6
bash scripts/wizard.sh                              # Gate A8 (dry-run)
```
Every gate above must exit 0. Bundle SHA recorded in `00_overview/contract/RELEASE_LOG.md`.

A run is **complete** when:
- All A.0–A.8 gates green (kit hardened)
- All B.3 tasks have promoted ledger rows + tests + Playwright specs
- Final proof bundle verifies signature + cross-refs
- Wizard transcript shows non-coder path zero→working UI

---

## Critical files (most-touched)

- `pyproject.toml` — package paths, matplotlib dep, optional groups
- `00_overview/contract/HONESTY_LEDGER.md` → `00_overview/contract/HONESTY_LEDGER.md`
- `03_implementation/src/hermes3d/app/launcher.py` (Gradio tabs)
- `03_implementation/src/hermes3d/core/agents/orchestrator.py`
- `03_implementation/src/hermes3d/core/integrations/remote_control.py`
- `03_implementation/src/hermes3d/core/orchestration/print_workflow.py` (retry wiring)
- `.github/workflows/ci.yml` (matrix + branch-guard)
- New: `agents/*.yaml`, `scripts/*.{sh,ps1}` (preflight, wizard, build-bundle, install-hooks, new-feature, run-e2e, validate-agents)
- New: `04_testing/playwright/**`
- New: `03_implementation/src/hermes3d/core/orchestration/retry_controller.py`
- New: `03_implementation/src/hermes3d/core/orchestration/repair_agent.py`

## Agent dispatch plan (how this gets executed across agents)

After approval I will spawn agents in this order (single message = parallel where independent):

**Wave 1 (parallel, A-phase foundation):**
- `Plan` agent: produce ADRs for A.1 restructure + A.4 retry framework
- `Explore` agent: enumerate every cross-reference to old paths to update in A.1
- `general-purpose` agent: scaffold `/agents/*.yaml` schema + initial 10 manifests

**Wave 2 (sequential, A.1 restructure must land first):**
- A.1 git mv + path rewrites (one agent, careful)
- Verify pytest still collects same count

**Wave 3 (parallel after A.1):**
- A.2 agents/ manifests
- A.3 Playwright suite scaffolding
- A.4 retry_controller + repair_agent + tests
- A.5 hooks + branch-guard CI
- A.6 build-bundle script
- A.7 audit code-gap fixes
- A.8 wizard + quickstart

**Wave 4 (B-phase, parallel where module-isolated):**
- B3-LG → B3-MC (sequential)
- B3-DT, B3-IL, B3-LP, B3-CW, B3-SD, B3-FF, B3-CT, B3-SK (parallel; one tab each)
- B3-BL (last; conditional on Blender)

**Wave 5 (sequential, release):**
- Run full verification chain
- Build + sign final v5.3 proof bundle
- Update HONESTY_LEDGER, CHANGELOG, RELEASE_LOG
- Tag on feature branch; user merges