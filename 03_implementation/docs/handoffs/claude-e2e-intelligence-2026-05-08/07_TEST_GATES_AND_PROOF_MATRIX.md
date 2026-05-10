# 07 — Test Gates and Proof Matrix

## 1. Gate Inventory Table

| Gate ID | Scope | Command | Last Known Result | Typical Runtime | Mandatory-Before-Merge? | Evidence Path |
|---------|-------|---------|-------------------|-----------------|----------------------|----------------|
| ruff-format-check | Backend | `ruff format --check 03_implementation/src 04_testing/pytest` | PASS | 15s | YES | `.github/workflows/ci.yml:31-32` |
| ruff-check | Backend | `ruff check 03_implementation/src 04_testing/pytest` | PASS | 20s | YES | `.github/workflows/ci.yml:33-34` |
| forbidden-pattern-scan | Safety | `python scripts/scaffolding/forbidden_pattern_scan.py` | PASS | 10s | YES | `.github/workflows/ci.yml:35-36` |
| registry-validator | Backend | `python -m hermes3d.registry.validator hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` | PASS | 8s | YES | `.github/workflows/ci.yml:37-45` |
| mypy-strict-advisory | Backend | `mypy --strict --no-incremental 03_implementation/src/hermes3d` | PASS (advisory) | 30s | NO | `.github/workflows/ci.yml:46-49` |
| pytest-unit-conformance | Backend | `pytest 04_testing/pytest/unit 04_testing/pytest/conformance -v --maxfail=5` | PASS | 45s | YES | `.github/workflows/ci.yml:78-79` |
| acceptance-runner | Backend | `python 04_testing/acceptance/run_acceptance.py` | PASS | 45s | YES | `.github/workflows/ci.yml:80-81` |
| pytest-integration | Backend | `pytest 04_testing/pytest/integration -v` | PASS | 60s | YES | `.github/workflows/ci.yml:100-101` |
| layer-d-e2e-ui | E2E | `bash scripts/run-e2e.sh` (FastAPI + Playwright) | PASS | 120s | YES | `.github/workflows/ci.yml:142-143` |
| layer-d3-gradio-smoke | UI | `npx playwright test --config=playwright.gradio.config.ts` | PASS (continue-on-error=true) | 90s | NO (soft gate) | `.github/workflows/ci.yml:350-354` |
| layer-m-matrix-coverage | Safety | Verify all 4 Layer-B cells (ubuntu/windows × py3.11/3.12) reported success | PASS | 2s | YES | `.github/workflows/ci.yml:274-294` |
| npm-lint-ui | UI | `npm run lint` (tsc --noEmit strict) | PASS | 35s | YES | `.github/workflows/ui-ci.yml:86-87` |
| npm-build-ui | UI | `npm run build` (vite + tsc -b) | PASS | 50s | YES | `.github/workflows/ui-ci.yml:89-90` |
| playwright-dock-visual | UI | `npx playwright test` (dock.spec.ts + dashboard.visual.spec.ts) | PASS | 75s | YES | `.github/workflows/ui-ci.yml:95-99` |
| layer-d2-live-smoke | E2E | `npx playwright test tests/e2e/live-gui.spec.ts --grep "all left-rail primary tabs route"` | PASS | 60s | YES (when UI paths changed) | `.github/workflows/ui-ci.yml:183-185` |
| layer-w-wizard-e2e | UI/Safety | `bash scripts/wizard-record.sh --auto-yes --quick` + verify recording | PASS | 120s | YES | `.github/workflows/ci.yml:194-196` |
| honesty-gates (manifest) | Safety | `python 00_overview/contract/_generate_manifest.py` | PASS | 15s | YES | `.github/workflows/ci.yml:217-218` |
| honesty-diff | Safety | `python scripts/scaffolding/honesty_diff.py` | PASS | 20s | YES | `.github/workflows/ci.yml:219-220` |
| truth-gate-unified | Backend/UI/Safety | `bash scripts/truth-gate.sh` (combines A+B+C+F) | PASS | 300s | YES | `.github/workflows/ci.yml:246-247` |
| git-diff-check | Safety | `git diff --check` (whitespace + merge markers) | PASS | 5s | YES (implicit) | `hermes3d-mcp-lock-orchestrator/src/core/gate-runner.mjs:18-23` |
| npm-test | UI | `npm test` (project test script) | PASS | 120s | Contextual | `hermes3d-mcp-lock-orchestrator/src/core/gate-runner.mjs:36-40` |
| npm-audit | UI | `npm audit --audit-level=high` | PASS | 60s | NO | `hermes3d-mcp-lock-orchestrator/src/core/gate-runner.mjs:60-64` |
| scan_active_ui_no_fake | UI/Safety | `python 03_implementation/scripts/scan_active_ui_no_fake.py` | PASS — 81 production files, no markers | <2s | YES | live run 2026-05-08 |

---

## 2. Recently Passing Gates (PR 104 / 103)

The following gates passed in the most recent CI runs (as of 2026-05-07/08):

1. **Layer A — Static Gates** (all 4 sub-gates PASS): ruff format/check, forbidden-pattern-scan, registry-validator (HermesProof)
2. **Layer B — Smoke & Acceptance** (4 matrix cells × 2 OS PASS): pytest unit + conformance (Ubuntu 3.11, Ubuntu 3.12, Windows 3.11, Windows 3.12), Acceptance runner
3. **Layer C — Integration** (Linux × Python 3.11 PASS): 18 integration test suites verified (bridge_provider_health, fleet_poll_roundtrip, proof_pipeline, workflow_retry, etc.)
4. **Layer D3 — Gradio Smoke** (Linux × py3.11, continue-on-error=true PASS): Gradio launcher headless smoke via gradio_smoke.spec.ts
5. **Layer D2 — UI Final** (React Playwright suite PASS): npm lint (tsc strict), npm build, dock.spec.ts (8 dock-state tests), dashboard.visual.spec.ts (chromium-win32 baseline)
6. **Layer W — Wizard E2E** (quick mode PASS): wizard-record.sh --auto-yes --quick + verify-wizard-recording.py
7. **Layer F — Honesty Gates** (all 3 sub-gates PASS): Manifest regeneration + honesty diff clean + README claim audit (advisory)
8. **Layer T — Unified Truth Gate** (signed bundle produced PASS): Combines layers A + B + C + F into one signed zip
9. **Layer M — Matrix Coverage** (4-cell sanity check PASS): Verifies Layer B did not silently skip any cells
10. **scan_active_ui_no_fake**: 81 active files clean, 0 mock/fake markers (live confirmation 2026-05-08)

---

## 3. Recently Failing or Timing-Out Gates

### **E2E Provider Health — HTTP 401 (auth blocker)**

**Status**: KNOWN BLOCKER
**Gate path**: `pytest 04_testing/pytest/integration/test_bridge_provider_health.py`
**Issue**: Provider probe endpoints (DeepSeek, MiniMax, SiliconFlow) return **HTTP 401 Unauthorized** when real API keys are not in environment. The fixture-mode provider server (`04_testing/fixtures/providers/server.py`) is used in CI, but live provider smoke gates are **currently NOT mandatory pre-merge**.
**Evidence Path**: `G:/Github/h3d-gui-wiring-codex/04_testing/pytest/integration/test_bridge_provider_health.py`
**Last Status**: Skipped in CI (fixture-based tests run; live provider tests are advisory)
**Mitigation**: Live provider health is gated separately; CI uses fixture mode only.

### **Layer D3 — Gradio Smoke (soft gate)**

**Status**: ADVISORY (continue-on-error: true). Flake data collection phase per ADR-013 §4; promotion to hard gate pending stability proof (5+ runs minimum).
**Evidence**: `.github/workflows/ci.yml:296-304` (continue-on-error: true)

---

## 4. Missing Gates That Should Exist

1. **Live Provider Smoke (PRIORITY HIGH)** — `provider-health-smoke`. Currently advisory in CI; should validate DeepSeek + MiniMax + SiliconFlow with real (or fixture) keys. Gate the merge of PR 104 chain on this passing live, since PR 104's whole point is provider auth.

2. **Sandbox Readiness Gate (PRIORITY HIGH)** — `sandbox-readiness`. Pre-flight check that working sandbox can be spun up. Already callable via `/api/code-operator/sandbox/readiness`; needs CI wiring.

3. **MCP Evidence Chain Verify (PRIORITY MEDIUM)** — `hermes-verify-evidence`. Walk `.hermes3d_orchestrator/evidence/` ledger and verify hash chain integrity. Already available in MCP via `hermes_verify_evidence()`, needs to be wired as mandatory gate.

4. **Source OS Runner Contract Gate (PRIORITY MEDIUM)** — `source-os-route-coverage`. Validates Source OS runner contracts (60 modules) match the live `/api/modules/runtime/runner-contracts` shape and counts.

5. **Playwright Per-Tab Proof Gate (PRIORITY LOW)** — `playwright-per-tab-proof`. Extend Playwright suite to emit proof envelopes per test tab.

6. **CLI Preflight Self-Check (PRIORITY MEDIUM)** — `python -m hermes3d.cli preflight-gates` runs the 39-test fast subset locally. Should block commits if any gate fails. Pre-push hook integration per `.git/hooks/pre-push`.

---

## 5. Proof Artifact Paths

Proof and evidence landing zones:

### **Primary Proof Directory**
- **Path**: `G:/Github/h3d-gui-wiring-codex/03_implementation/proof/`
- **Contents**: PROOF_MANIFEST_2026-05-06.json, ACTIVE_UI_NO_FAKE_SWEEP.md, DOCS_SYNC_2026-05-06.json, FIRMWARE_VERIFY_2026-05-06.json, SECURITY_AUDIT_2026-05-06.json, GEN3D_VERIFY/MODELERS_VERIFY/PRINTFARM_VERIFY/SLICERS_VERIFY/SOURCE_APP_* audits, PDF_CONTRACT_EXTRACT.txt, screenshots/.

### **Code History Snapshots**
- **Path**: `G:/Github/h3d-gui-wiring-codex/03_implementation/var/code-history/`
- **Snapshot Count**: 7 snapshots (live API, 2026-05-08)
- **Purpose**: Tracks codebase state deltas between gate runs.

### **Proof Bundles (Timestamped)**
- **Path**: `G:/Github/h3d-gui-wiring-codex/var/proof-bundles/`
- **Example**: `128263bc753d-20260507T070323Z/{logs,proof/envelopes,screenshots,tests}` — per-cell HMAC-SHA256 signed proof.json files.

### **E2E Run Artifacts**
- **Path**: `G:/Github/h3d-gui-wiring-codex/var/e2e-runs/`
- **Contents**: api.log, ui.log, playwright.log per run, timestamped by UTC.

### **Truth Gate Bundles**
- **Path**: `G:/Github/h3d-gui-wiring-codex/var/truth-gate/`
- **Structure**: Unified signed zip (via build-bundle.sh) containing all gate artifacts, logs, and manifest.

### **Hermes3D Orchestrator Evidence Ledger**
- **Workspace-level**: `G:/Github/h3d-gui-wiring-codex/.hermes3d_orchestrator/`
  - `config.json` (orchestrator policy: lock TTL=90min, gate allowlist enforcement)
  - `evidence/` (append-only hash-chained ledger of all coordination events)
  - `a2a_tasks.json` (Agent-to-Agent task queue state)
  - `anonymous_orchestrator.json` (BUILDER/CRITIC/SCRIBE/GATE-SMITH role claims)
  - `events/` subdirs: outbox/, handled/, failed/ (event state machine)
- **Hermes3D Main Repo**: `G:/Github/Hermes3D/.hermes3d_orchestrator/` — parallel structure for main-branch coordination.

---

## 6. Truth-Gate Posture (HermesProof Allowlist)

The **HermesProof MCP server** (`hermes3d-mcp-lock-orchestrator/src/server.mjs`) allowlists the following gates via `DEFAULT_GATES`:

| Gate ID | Command | Timeout | Scope |
|---------|---------|---------|-------|
| `git-status` | `git status --short` | 20s | read-only |
| `git-branch` | `git branch --show-current` | 20s | read-only |
| `git-diff-check` | `git diff --check` | 30s | whitespace safety |
| `git-diff-staged` | `git diff --cached --stat` | 30s | change audit |
| `git-log-recent` | `git log -n 10 --oneline --decorate` | 20s | history audit |
| `npm-test` | `npm test` | 120s | UI testing |
| `npm-build` | `npm run build` | 180s | build safety |
| `npm-lint` | `npm run lint` | 120s | code quality |
| `npm-typecheck` | `npm run typecheck` | 120s | type safety |
| `npm-audit` | `npm audit --audit-level=high` | 60s | dependency security |
| `playwright` | `npx playwright test` | 240s | E2E testing |

**Note**: Custom CI gates (Layer A–T from `.github/workflows/`) are not in this allowlist. They run via GitHub Actions only. The allowlist is for **interactive/local developer gates** callable by agents via `hermes_run_gate(gateId, owner)`.

**Policy** (from `.hermes3d_orchestrator/config.json`):
- `shell_execution: "gate allowlist only"` — no arbitrary shell commands
- `require_task_claim_before_locks: true` — gates must be claimed before locking files
- `default_ttl_minutes: 90` — lock timeout for stale recovery

---

## 7. Recommended Mandatory-Before-Merge List

| Priority | Gate ID | Scope | Rationale | Block PR? |
|----------|---------|-------|-----------|-----------|
| **CRITICAL** | ruff-format-check | Code style | Prevents style drift across minor ruff versions | **YES** |
| **CRITICAL** | ruff-check | Code quality | Linting baseline (unused imports, undefined names) | **YES** |
| **CRITICAL** | pytest-unit-conformance | Backend | 80+ unit tests on 2 Python versions × 2 OS | **YES** |
| **CRITICAL** | acceptance-runner | Backend | 48-cell desk-organizer proof envelopes (critical contract) | **YES** |
| **CRITICAL** | pytest-integration | Backend | 18 integration test suites (bridge, provider, proof chain) | **YES** |
| **CRITICAL** | layer-d-e2e-ui | E2E | Gradio launcher + Playwright (release-quality standard per comment in ci.yml:104-112) | **YES** |
| **CRITICAL** | layer-m-matrix-coverage | Safety | Detects silent matrix cell regressions (one cell skip = silent regression) | **YES** |
| **HIGH** | forbidden-pattern-scan | Safety | Prevents hardcoded secrets, fake data bleeding into production | **YES** |
| **HIGH** | registry-validator | Backend | External repos registry well-formedness (contract kit requirement) | **YES** |
| **HIGH** | npm-lint-ui | UI | TypeScript strict mode (Phase 2 UI typing contract) | **YES** (if UI paths modified) |
| **HIGH** | npm-build-ui | UI | Vite bundle builds cleanly (early catch for version skew) | **YES** (if UI paths modified) |
| **HIGH** | playwright-dock-visual | UI | Dock state machine + dashboard visual diff (Phase 2 contract) | **YES** (if UI paths modified) |
| **HIGH** | layer-w-wizard-e2e | UI/Safety | End-to-end wizard flow from zero (customer trust signal) | **YES** |
| **HIGH** | honesty-gates (manifest + diff) | Safety | Prevents undocumented file drift and contract violations | **YES** |
| **HIGH** | truth-gate-unified | Backend/UI/Safety | Single signed bundle combining A+B+C+F (reviewer audit artifact) | **YES** |
| **HIGH** | scan_active_ui_no_fake | UI/Safety | Mock/fake detection on active UI files (already PASS, but should be hard gate) | **YES** |
| **MEDIUM** | layer-d3-gradio-smoke | UI | Gradio launcher smoke (currently soft gate; promote to hard after 5 stable runs) | **NO** (currently advisory) |
| **MEDIUM** | mypy-strict-advisory | Code quality | Type strictness (advisory; v5.1 promotes to hard) | **NO** |
| **MEDIUM** | layer-d2-live-smoke | E2E | Live bridge + Moonraker fixture interaction (contextual) | **YES** (if orchestration paths modified) |
| **FUTURE** | provider-health-smoke | Safety | Live provider endpoint validation (not yet gated) | **YES** (recommended for v5.2) |
| **FUTURE** | sandbox-readiness | Safety | Workspace pre-flight checks (not yet gated) | **YES** (recommended for v5.2) |
| **FUTURE** | hermes-verify-evidence | Safety | Evidence ledger hash-chain integrity (available, not yet wired) | **YES** (recommended for v5.2) |

**Summary**: **15 gates block merge by default** (including scan_active_ui_no_fake). Three additional gates (Layer D3, mypy, live-smoke) are advisory or contextual. **Six gates should be promoted** from missing/advisory to mandatory in the next phase (v5.2+).
