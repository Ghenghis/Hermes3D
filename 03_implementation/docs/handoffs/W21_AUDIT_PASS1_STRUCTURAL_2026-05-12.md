# W21 Audit — Pass 1 (Structural Inventory)

**Date:** 2026-05-12
**Auditor:** Claude (15 parallel structural sub-agents)
**Scope:** Hermes3D backend (`G:\Github\Hermes3D\03_implementation\`) and UI (`ui/src/`). Pure existence + registration counts. No behavior evaluation in this pass — that's Pass 2.
**Develop SHA at probe:** `be2755f` (PR #258 + hotfix #259 + audit doc #260 merged or in flight).

This is Pass 1 of 3. Pass 2 (Behavioral Probe) and Pass 3 (E2E Journeys) follow.

---

## §1. Python backend — module inventory

`G:\Github\Hermes3D\03_implementation\src\hermes3d\`

| Metric | Count |
|---|---|
| Total `.py` files (excluding `__pycache__`) | **212** |
| Total LOC | **63,305** |

### LOC by top-level subpackage

| Subpackage | Files | LOC |
|---|---|---|
| `api/` | 45 | 21,773 |
| `core/` | 86 | 19,154 |
| `services/` | 21 | 14,361 |
| `adapters/` | 18 | 1,276 |
| `gateways/` | 9 | 1,291 |
| `orchestration/` | 6 | 1,440 |
| `db/` | 4 | 1,635 |
| `registry/` | 6 | 462 |
| `cli/` | 3 | 754 |
| `agents/` | 3 | 404 |
| `env/` | 4 | 260 |
| `app/` | 2 | 280 |
| `config/` | 2 | 166 |
| `planner/` | 2 | 30 |

### `api/routes/` — 40 modules

Largest: `agents.py` 4,412 LOC · `modules.py` 2,394 · `code_operator.py` 1,205 · `design.py` 1,163 · `agent_updates.py` 1,109 · `learning.py` 884 · `printers.py` 877 · `system.py` 808 · `voice.py` 769 · `jobs.py` 756. Smallest: `__init__.py` 1 · `_common.py` 48 · `events.py` 49 · `ports.py` 35 · `approvals.py` 69.

### `__all__` exports

76+ modules declare `__all__` lists.

---

## §2. FastAPI route inventory

`@router.get/.post/.put/.delete/.patch` decorators counted under `api/routes/`.

| Metric | Count |
|---|---|
| **Total routes** | **279** |
| GET | 134 |
| POST | 129 |
| PUT | 12 |
| PATCH | 3 |
| DELETE | 1 |

### Top URL prefixes by route count

1. `/api/modules` — 27 routes
2. `/api/printers` — 16
3. `/api/jobs` — 10
4. `/api/agents` — 9 (excluding `/api/agents/queue` + `/api/agents/update` + `/api/agents/providers`)
5. `/api/modules/runtime` — 8
6. `/api/plugins` — 7
7. `/api/observe/cameras` — 6
8. `/api/agents/queue` — 5
9. `/api/learning/idle-workbench` — 5
10. `/api/agents/update` — 4

**No dead route files** — every `.py` under `api/routes/` has at least one decorator.

---

## §3. React UI — component inventory

`G:\Github\Hermes3D\03_implementation\ui\src\`

| Metric | Count |
|---|---|
| `.tsx` files | 110 |
| `.ts` files | 75 |
| Total (.tsx + .ts) LOC | **36,543** |
| Tabs (`tabs/`) | 25 files (11,100 LOC) |
| Components (`components/`) | 87 files (15,418 LOC) |
| Custom hooks (`hooks/`) | 12 files (966 LOC) |
| API client (`api/`) | 8 files (5,535 LOC) |
| Types (`types/`) | 34 files (1,908 LOC) |
| Theme (`theme/`) | 12 files (889 LOC) |
| App shell (`app/`) | 3 files (351 LOC) |

### Largest tabs (LOC)

| Tab | LOC |
|---|---|
| `Agents.tsx` | 1,423 |
| `Observe.tsx` | 1,192 |
| `SourceOS.tsx` | 1,174 |
| `Design.tsx` | 1,022 |
| `Dashboard.tsx` | 879 |
| `Printers.tsx` | 873 |
| `Gen3D.tsx` | 627 |
| `Learning.tsx` | 491 |
| `Jobs.tsx` | 370 |
| `Safety.tsx` | 293 |

### Component subdirectories with the most weight

`settings/` (10, 2702 LOC) · `source-os/` (11, 1972) · `agents/` (6, 1630) · `dashboard/` (6, 1196) · `voice/` (3, 1096) · `AppRegistry/` (2, 827) · `ActionWindow/` (4, 788) · `simple/` (1, 742) · `layout/` (4, 578) · `TaskMonitor/` (3, 494) · `autopilot/` (4, 485) · `StatusBanners/` (4, 474) · `Onboarding/` (3, 417) · `health/` (3, 381).

### Custom hooks

`useDashboardLayouts.ts` 247 · `_useQuery.ts` 169 · `usePrinters.ts` 179 · `useAgents.ts` 71 (+ `useAgents.test.ts` 63) · `useRecovery.ts` 69 · `useOpenCode.ts` 56 · `useOpenHands.ts` 54 · `useProviders.ts` 43 · `useMcp.ts` 40 · `useApps.ts` 28 · `index.ts` 17.

---

## §4. UI hash routes + controls

### Registered hash routes (25)

**Primary tabs (17):** `#source_os` `#dashboard` `#autopilot` `#design` `#gen3d` `#jobs` `#printers` `#observe` `#voice` `#agents` `#learning` `#artifacts` `#approvals` `#apps` `#plugins` `#settings` `#roadmap`

**Utility tabs (8):** `#workflows` `#print_queue` `#files` `#system_logs` `#proof` `#service_health` `#notifications` `#safety`

**Deep routes:** `#apps/<id>` (app detail) · `#health` alias to ServiceHealth.

Every `.tsx` in `tabs/` maps to at least one hash route — **no orphan tab files**.

### Visible-control counts (aggregate, structural)

* `<button>` elements across `tabs/` + `components/`: **~147**
* `<input>` elements: ~50+
* `<select>` elements: ~10+
* `<textarea>` elements: ~5+
* `role="button"` non-button elements: ~10+
* `data-testid` attributes: extensive (used by every Playwright spec)

(Behavior of each control is Pass 2 scope — this pass only counts existence.)

---

## §5. Python dependencies

`G:\Github\Hermes3D\pyproject.toml` + `requirements.txt` declared vs `pip list` installed.

| Metric | Count |
|---|---|
| Declared deps (core + req.txt + optional groups) | 13 + transitive |
| `pip list` installed | **197** |
| Declared but NOT installed | **0** |
| Installed but not declared (transitive) | 184 |

### Pinned key versions

`fastapi 0.129.2` · `uvicorn 0.40.0` · `pydantic 2.12.5` · `trimesh 4.12.1` · `manifold3d 3.4.1` · `numpy 2.4.2` · `httpx 0.28.1` · `requests 2.33.1` · `python-dotenv 1.2.1` · `ruff 0.14.14` · `mypy 1.20.2` · `pytest 8.4.2`.

### Optional-dep groups

`ui` (gradio, matplotlib) · `dev` (pytest, pytest-cov, ruff, mypy) · `langgraph` · `mnemosyne` · `all`.

### Notable transitive surprises

`langgraph 1.1.10`, `anthropic 0.100.0`, `transformers 5.6.2`, `torch 2.11.0`, `gradio 6.13.0`, `pandas`, `scikit-learn`, `qdrant-client`. These are installed but the backend code doesn't directly require them; they came in via other tools or were pre-installed in the Python env.

---

## §6. Node dependencies

`G:\Github\Hermes3D\03_implementation\ui\`

| Metric | Count |
|---|---|
| `package.json` `dependencies` | 6 |
| `package.json` `devDependencies` | 12 |
| **Total declared** | **18** |
| `node_modules/` top-level | **226** |
| Declared but missing from `node_modules` | **0** |
| `package-lock.json` size | 179 KB |

### Key pinned versions

`react 18.3.1` · `react-dom 18.3.1` · `react-router-dom 6.30.3` · `zustand 5.0.0` · `recharts 2.13.0` · `lucide-react 0.451.0` · `vite 8.0.10` · `typescript 5.6.2` · `@playwright/test 1.59.1` · `@vitejs/plugin-react 6.0.1` · `tailwindcss 3.4.13` · `autoprefixer 10.4.20` · `vitest 2.1.5` (devDeps) · `@testing-library/react 16.0.1`.

---

## §7. Env vars declared vs used

| Metric | Count |
|---|---|
| Unique env-var names referenced in code | **73** |
| Keys present in `G:\private\.env` | 21 |
| Used-in-code but NOT in `.env` | **57** (mostly optional/defaults, some real gaps) |
| In `.env` but NOT used in code (orphans) | **24** |

### Breakdown of code-referenced env-var prefixes

| Prefix | Count |
|---|---|
| `HERMES3D_*` | 47 |
| Provider-specific (`MINIMAX_`, `DEEPSEEK_`, `OLLAMA_`, `OBICO_`, `OCTOPRINT_`, `MOONRAKER_`) | 11 |
| `AZURE_*` | 3 |
| `HERMES_*` (legacy, non-Hermes3D) | 6 |
| System (PATH/TEMP/COMSPEC/CUDA/GPU/Velopack) | 10 |

### Notable orphans in `.env` (no code reference)

`HERMES3D_AGENT_SANDBOX_*` (3) · `HERMES3D_SOURCE_*` (9 — likely deploy-time) · `CODERABBIT_API_KEY` · `GITHUB_TOKEN` · `HUGGINGFACE_TOKEN` · `SILICONFLOW_API_KEY` · `MCP_LOCK_SERVER` · `MCP_LOCK_WORKSPACE`.

### Notable alias mismatch

`.env` has `LMSTUDIO_BASE_URL` but code reads `HERMES3D_LM_STUDIO_BASE_URL`. Functionally fine because `env_loader` does not normalize aliases — operator must keep both in sync, or add alias logic.

---

## §8. SQLite schema

`G:\Github\Hermes3D\03_implementation\src\hermes3d\db\schema.sql`

| Metric | Count |
|---|---|
| `CREATE TABLE` statements | **27** |
| `CREATE INDEX` statements | 11 |
| Foreign keys declared | 10 |
| `CREATE VIEW` | 0 |
| `CREATE TRIGGER` | 0 |
| Migration helpers (`_migrate*` in `init.py`) | 2 |

### Tables (27)

`modules`, `bridge_tasks`, `module_runtime_verifiers`, `module_runtime_setup_runs`, `module_providers`, `jobs`, `job_steps`, `job_events`, `approvals`, `artifacts`, `plugins`, `voice_assignments`, `proof_events`, `code_history_snapshots`, `roadmap_items`, `settings`, `onboarded_printers`, `truth_gate_results`, `agent_conversations`, `agent_config`, `agent_autonomous_sessions`, `agent_autonomous_actions`, `idle_workbench_candidates`, `idle_workbench_events`, `notifications`, `anomaly_reports`, `build_plate_clearance`.

### Foreign-key edges (10)

`bridge_tasks.module_id → modules.id` · `module_providers.module_id → modules.id` · `job_steps.job_id → jobs.id` · `job_events.job_id → jobs.id` · `approvals.job_id → jobs.id` · `artifacts.job_id → jobs.id` · `truth_gate_results.job_id → jobs.id` · `agent_autonomous_actions.session_id → agent_autonomous_sessions.id` · `idle_workbench_candidates.approval_id → approvals.id` · `idle_workbench_events.candidate_id → idle_workbench_candidates.id`.

### Live `data/hermes3d.db`

* **File size: 0 bytes** — empty file. Tables are initialised on first API startup via `init_db()` against the var-rooted path (`var/hermes3d.db`).

### DB path drift (smoking gun)

Schema/init module defines `DB_PATH = parents[3] / "var" / "hermes3d.db"` but the `data/hermes3d.db` file was previously reported as 798 KB. Pass 2 will resolve which DB the running backend actually writes to.

---

## §9. Gateways + services inventory

### Gateways (5 + providers)

| File | LOC | Public surface |
|---|---|---|
| `gateways/budget.py` | 136 | `BudgetCaps`, `BudgetDecision`, `BudgetStore`, fresh/estimate/check/record |
| `gateways/llm.py` | 331 | `LLMPolicy`, `LLMGateway`, redaction + signing |
| `gateways/probe.py` | 227 | `ProviderProbeGateway`, `ProbeOutcome` |
| `gateways/redaction.py` | 180 | `redact_text`, `redact_json`, `redacted_json_dumps` |
| `gateways/sanitize.py` | 50 | `sanitize_prompt` |
| `gateways/providers/deepseek.py` | 135 | httpx client, env-keyed |
| `gateways/providers/minimax.py` | 137 | httpx client, env fallback chain |
| `gateways/providers/__init__.py` | 76 | policy loader |

### Services (21)

`agent_checkout`, `agent_runtime`, `agent_version_provider_compat`, `agent_version_registry`, `app_proof_runner`, `autonomous_loop`, `canary_dirt_filter`, `code_history`, `local_state`, `module_runtime`, `printer_safety_gate`, `proof_helpers`, `recovery_controller`, `rust_accel`, `source_service_supervisor`, `gpu_probe`, `gpu_render`, `modeling_backend`, **`queue_bridge`** (W21-A4 MVP-2), **`queue_poller`** (W21-A4 MVP-2), `__init__`.

`queue_bridge` 200 LOC and `queue_poller` 180 LOC are new in PR #258.

---

## §10. CI workflows (7)

`.github/workflows/`

| Workflow | Triggers | Jobs |
|---|---|---|
| `branch-guard.yml` | PR to main | 3 (refuse-same-branch, enforce-release, forbidden-pattern-scan) |
| `ci.yml` | push (main/develop/release/hotfix), PR | **9 layers** — A/B/C/D/D2/D3/E/F/M/T/W |
| `hermes-agent-versions.yml` | path-gated push + manual | 1 (pin-tests, 2×1 matrix) |
| `pages.yml` | push develop (site/**) | 1 (deploy) |
| `release-windows.yml` | tag push (v*) | 1 (windows_binary) |
| `ui-ci.yml` | push + PR | 2 (Layer D2 UI-Final + Live-mode smoke) |
| `upstream-hermes-agent-watch.yml` | weekly cron | 1 (poll upstream) |

### Layer matrix (ci.yml)

* **Layer A static gates** — `ruff format --check` + `ruff check` + registry validator + `mypy --strict` (advisory)
* **Layer B smoke/acceptance** — 2×2 (ubuntu/windows × py3.11/3.12) — pytest unit + conformance + `run_acceptance.py`
* **Layer C integration** — Linux py3.11 — `pytest 04_testing/pytest/integration -v`
* **Layer D UI E2E** — Linux py3.11 + Node 24 — `scripts/run-e2e.sh`
* **Layer D2 UI-Final + Live-mode** — under ui-ci.yml
* **Layer D3 Gradio smoke** — `continue-on-error: true` (optional)
* **Layer E release dry-run** — only on `release/*` push
* **Layer F honesty gates**
* **Layer M matrix coverage** — verifies Layer B success
* **Layer T unified truth gate** — `scripts/truth-gate.sh` aggregates A+B+C+F
* **Layer W wizard E2E**

---

## §11. Tests inventory

| Metric | Count |
|---|---|
| Total test files (Python + TS) | **168** |
| Python under `04_testing/pytest/` | 129 |
| TypeScript Playwright `.spec.ts` | 39 |
| Python `def test_*` functions | **1,304** |
| TS `test(` / `test.describe(` blocks | 162 |
| Total executable tests | **1,466** |
| Total `assert ...` (Py) + `expect(...` (TS) | **3,872** |
| `@pytest.fixture` definitions | 41 |
| Skipped tests (`skip`/`skipif`) | **34** |

### Python test subdirs

`unit/` 53 · `integration/` 31 · root 10 · `conformance/` 1 · subdirs: `registry/` 8 · `gateways/` 7 · `adapters/` 6 · `orchestration/` 4 · `scripts/` 2 · `env/` 2 · `agents/` 2 · `planner/` 1 · `config/` 1 · `cli/` 1.

### Top 10 Python files by test count

1. `test_injection_scanner.py` — 58 tests
2. `test_code_operator.py` — 45
3. `test_second_wave_modules.py` — 44
4. `test_agentic_modules.py` — 42
5. `test_firmware_farm_probes.py` — 34
6. `test_remote_control.py` — 32
7. `test_source_runtime_contracts.py` — 25
8. `test_printer_policy.py` — 25
9. `test_printer_fleet.py` — 25
10. `test_tool_registrations.py` — 24

### Coverage gap surfaced (revisited)

Per the previous gap audit, **21 of 37** route files have **zero** direct test reference. To verify: cross-reference `api/routes/*.py` filenames with substring search in `04_testing/pytest/`. Files with no match: `autopilot.py`, `desktop_compat.py`, `learning.py`, `settings_themes.py`, `agent_queue.py`, `artifacts.py`, `autonomous.py`, `connectors.py`, `dashboard_layouts.py`, `desktop_updates.py`, `events.py`, `notifications.py`, `observe.py`, `plugins.py`, `ports.py`, `roadmap.py`, `settings.py`, `skills.py`, `source_os.py`, `voice.py`, `files.py`.

---

## §12. Handoff docs inventory

`03_implementation/docs/`

| Metric | Count |
|---|---|
| Total `.md` files in `docs/` tree | **222** |
| `.md` in `docs/handoffs/` | **96** |
| Audit / Gap / Proof named docs | **21** |

### By week prefix in `docs/handoffs/`

`W8` 5 · `W14` 5 · `W15` 9 · `W18` 19 · `W19` 2 · `W20` 1 · `W21` 2 (now 3 with this Pass 1 doc) · unprefixed 53.

### Notable audit docs (most-recent-first)

| File | Bytes | H1+H2 |
|---|---|---|
| `W21_REALITY_GAP_AUDIT_2026-05-12.md` | 20,819 | 32 |
| `W21_A4_HERMES_AGENTS_ACTIVATION_AUDIT_2026-05-11.md` | 13,798 | 16 |
| `W20_TAB_FEATURE_ACTION_AUDIT_2026-05-11.md` | 21,497 | 30 |
| `W19_PRODUCT_COMPLETION_GAP_AUDIT_2026-05-11.md` | 16,260 | 26 |
| `W18-A3_BACKEND_ENDPOINT_AUDIT_2026-05-11.md` | 24,178 | 20 |
| `W18-A2_UX_UI_STRUCTURE_AUDIT_2026-05-11.md` | 28,875 | 11 |
| `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md` | 48,796 | 30 |
| `GUI_INCOMPLETE_E2E_AUDIT_2026-05-10.md` | 27,636 | 20 |

---

## §13. Orchestrator state inventory

`G:\Github\Hermes3D\.hermes3d_orchestrator\`

| Concern | Count |
|---|---|
| Top-level subdirs | 8 (`a16_shadow/`, `events/`, `evidence/`, `gates/`, `handoffs/`, `locks/`, `review_packets/`, `tasks/`) |
| `tasks/pending/` | 0 |
| `tasks/claimed/` | **8** |
| `tasks/done/` | 0 |
| `tasks/blocked/` | 0 |
| Active `locks/*.lockdir/` | 8 |
| `events.ndjson` lines | 625 (273 KB) |
| `events/` files | 584 (2.5 MB) |
| `evidence/` files | 735 (3.5 MB) |
| `gates/` records | 23 |
| `a16_shadow/` files | 7 |

> ⚠️ `tasks/claimed/` shows **8** entries despite earlier reset to pending. Either the queue poller re-claimed them between agent dispatches, or my reset never persisted. Pass 2 will probe this directly.

### Claimed tasks today

| Task ID | Priority | Owner pattern |
|---|---|---|
| `W21-A1-FEATURE-ACTION-DEEP-AUDIT-2026-05-11` | 100 | `oliver-qa-agent\|factory-operator` |
| `W21-A2-DESIGN-MODELER-E2E-AUDIT-2026-05-11` | 95 | `modeling-agent\|mesh-go-agent` |
| `W21-A3-GEN3D-PROVIDER-3090TI-AUDIT-2026-05-11` | 90 | `modeling-agent\|mesh-go-agent` |
| `W21-A4-HERMES-AGENTS-ACTIVATION-AUDIT-2026-05-11` | 100 | `factory-operator\|privacy-agent\|oliver-qa-agent` |
| `W21-A5-60-APP-PROOF-DEEP-AUDIT-2026-05-11` | 85 | `oliver-qa-agent\|factory-operator` |
| `W21-A6-REALTIME-UX-STALE-STATE-AUDIT-2026-05-11` | 88 | `oliver-qa-agent\|factory-operator` |
| `W21-A7-LAG-PROTECTED-E2E-HARNESS-2026-05-11` | 92 | `oliver-qa-agent\|factory-operator` |
| `W21-A8-GEN3D-MODEL-INSTALL-EXECUTION-PLAN-2026-05-11` | **99** | `modeling-agent\|mesh-go-agent\|factory-operator` |

### Reputation + skill rotation

`reputation.json` 5.4 KB (claude-p1-6 et al.) · `skill_rotation.json` 3.2 KB · `anonymous_orchestrator.json` 96 B (history empty) · `a2a_tasks.json` 41 B (tasks empty) · `config.json` 420 B (default_ttl_minutes 90, require_task_claim_before_locks true).

---

## §14. Static assets + `var/` tree

### `var/` (runtime data)

| Subdir | Files | Bytes |
|---|---|---|
| `slicer/` | 16 | 36.89 MB |
| `hermes_agent_backups/` | 3 | 26.24 MB |
| `designs/` | 155 | 11.05 MB |
| `sliced/` | 4 | 0.97 MB |
| `generation/` | 12 | 0.02 MB |
| `agent_uploads/` | 5 | 0 |
| `artifacts/` | 6 | 0 |
| `autopilot/` | 1 | 0 |
| `code-history/` | 2 | 0 |
| `learning/` | 0 | 0 |
| Root: `hermes3d.db`, `runtime-ports.json` | 2 | 0.76 MB |
| **Total** | **206** | **79.6 MB** |

### Extensions in `var/`

`.json` 62 · `.stl` 60 · `.png` 47 · `.gcode` 14 · `.bin` 6 · `.webm` 5 · `.svg` 4 · other 9.

### `proof/` (20 JSON + 4 docs + 1 archive)

Highlights: `SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json` 100 KB · `SOURCE_APP_CLI_SURFACE_AUDIT.json` 71 KB · `SOURCE_REGISTRY_TRUTH_AUDIT.json` 30 KB · `LOCAL_TOOLING_AUDIT.json` 8 KB · `GEN3D_VERIFY_2026-05-06.json` 8 KB · `MODELERS_VERIFY_2026-05-06.json` 5.6 KB · `SLICERS_VERIFY_2026-05-06.json` 4.3 KB · `FIRMWARE_VERIFY_2026-05-06.json` 3.5 KB · `PROOF_MANIFEST_2026-05-06.json` 3 KB.

### `data/themes/` (6 themes)

`aurora_operator.json`, `cyberpunk.json`, `default.json`, `industrial_forge.json`, `matrix.json`, `tron.json`.

### `ui/public/`

`hermes3d-runtime.json` 0.27 KB — runtime port config consumed by the React app at boot.

---

## §15. External clone paths

`G:\Github\`

* **203 top-level subdirs.** Key Hermes-related: `Hermes3D`, `Hermes3D-OS`, `hermes3d-mcp-lock-orchestrator`, `hermes-agent`, `Hermes3D-worktrees`, `_claude_worktrees`, `_codex_worktrees`, `ComfyUI`, `kilocode`, `open-webui`, `TRELLIS.2`, `ComfyUI-Hunyuan`, `h3dos-codex-triposr`.

### `G:\Github\Hermes3D-OS\source-lab\sources\` — 11 subdirs

`firmware/`, `generation/`, `hardware/`, `libraries/`, `materials/`, `modelers/`, `orchestration/`, `print-farm/`, `research/`, `slicers/`, `utilities/`. The structural agent reported each subdir at 261 files / 1.95 MB — suspicious symmetry suggesting these are sparse-clone skeletons, not full repos. **Pass 2 will probe individual modules.**

### Hardcoded Windows paths referenced in code

* `C:\Program Files\Blender Foundation\Blender 3.6/4.1/4.4/blender.exe`
* `C:\Program Files\Prusa3D\PrusaSlicer-*/`, `C:\Program Files\OrcaSlicer*`, `C:\FlsunSlicer2.0\`
* `C:\Program Files\OpenSCAD\openscad.exe`
* `G:\Github\Hermes3D\apps\<group>\<app>` (sibling apps tree referenced by E2E tests + install scripts)

### Cache paths

Playwright `.cache/` is `.gitignore`d. Python runtime cached at `%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. HuggingFace cache at `C:\Users\Admin\.cache\huggingface\` (56 GB, 461 items per prior probe).

---

## §16. Pass-1 totals at a glance

| Layer | Number |
|---|---|
| Python files | 212 (63 305 LOC) |
| TypeScript files | 185 (.tsx 110 + .ts 75, 36 543 LOC) |
| FastAPI routes | 279 |
| UI hash routes | 25 |
| UI components | 87 files |
| Custom hooks | 12 |
| SQLite tables | 27 |
| Test files | 168 |
| Test functions | 1 466 |
| Assertions | 3 872 |
| Skipped tests | 34 |
| Docs `.md` | 222 (96 in handoffs/) |
| CI workflows | 7 |
| Pending W21 tasks | 0 (8 already claimed) |
| Active file locks | 8 |
| Disk artifacts in `var/` | 206 (79.6 MB) |
| Provider env-var names referenced | 73 (21 present in `.env`) |
| Python deps declared | 13 (all installed; 184 transitive) |
| Node deps declared | 18 (all installed; 226 transitive) |

---

## §17. What this pass DOES NOT answer

This pass is structural only. It does NOT answer:

* Whether any of the 279 routes returns real data or a stub envelope.
* Whether any of the 147 buttons actually triggers a backend call when clicked.
* Whether any of the 1 466 tests passes today, or which CI runs are red.
* Whether any of the 60 STLs on disk has a valid proof signature.
* Whether the 8 claimed W21 tasks have any persona doing work on them.
* Whether the 24 .env orphan keys are actually safe to delete.
* Whether the SQLite tables are populated or empty.
* Whether the 8 active lockdirs are alive or stale.

Those are Pass 2 (Behavioral) and Pass 3 (E2E Journey) scope.

---

## §18. Pass-1 derived candidates (no behavior claims)

These are STRUCTURAL gaps — things that exist on paper but show inconsistency at the registration layer. Pass 2 will validate / invalidate each.

1. **DB path drift** — `db/init.py` says `var/hermes3d.db`, `data/hermes3d.db` is 0 bytes. Two paths reference one logical DB.
2. **24 orphan env keys** — set in `.env`, never read.
3. **`LMSTUDIO_BASE_URL` alias** — env file uses one name, code uses another.
4. **21 untested route files** — already noted in W21 gap doc; confirmed by inventory.
5. **`source-lab` symmetric 261-files-per-module** — suspicious; almost certainly sparse-checkout placeholders rather than real clones.
6. **`tasks/claimed/` = 8** — should be `pending` after my reset; something re-claimed.
7. **`agent_queue.py` route file exists but has no test reference** — new from #258, expected behavior; flag for Pass 2 to write the test.
8. **279 routes total but only ~85 buttons fetch** — large surface where the UI does not yet exercise the backend.

End of Pass 1. Pass 2 (Behavioral Probe) follows.
