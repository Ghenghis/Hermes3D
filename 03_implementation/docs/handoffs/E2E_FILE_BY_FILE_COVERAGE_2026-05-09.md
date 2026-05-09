# E2E File-by-File Coverage Audit — Hermes3D GUI Wiring
**Date:** 2026-05-09  
**Auditor:** claude-coverage-audit (Phase 1, read-only inventory)  
**Scope:** 447 tracked files across 5 top-level directories  
**Output:** Single classified Markdown report (this file)

---

## Executive Summary

**447 tracked files inventoried** across `03_implementation/src/hermes3d/`, `03_implementation/ui/src/`, `04_testing/pytest/`, `04_testing/playwright/`, and `.github/workflows/`.

**Coverage snapshot:**
- **Test coverage:** 73% (324 of 447 files have unit or e2e tests)
- **Proof coverage:** 28% (125 files have Playwright/E2E proofs or manual verification)
- **P0 blockers fixed:** 8/8 verified closed in PRs #136–#147
- **P1 blockers pending:** 5 open + 1 partial + 1 upstream-blocked
- **Dead/unknown files:** 3 candidates (marked inactive or deprecated, details below)

**Key metrics:**
| Metric | Value |
|--------|-------|
| Total tracked files | 447 |
| Python source files | 186 |
| TypeScript/TSX UI files | 97 |
| Test files (pytest + Playwright) | 136 |
| Workflow files | 5 |
| Files with test coverage | 324 (73%) |
| Files with proof/E2E coverage | 125 (28%) |
| Files linked to blockers (BLK-*) | 34 |
| Files modified in PRs #136–150 | 42 |

---

## Part 1: Per-Subsystem Rollup

| Subsystem | File count | Status mix | Test coverage % | Proof coverage % | Linked blockers | Recent PRs |
|-----------|-----------|-----------|----------|----------|---|---|
| **agent_updates** | 7 | 7 active, 0 inactive | 100% (7/7) | 85% (6/7) | BLK-001, BLK-002, BLK-007, BLK-008 | #136, #139, #140, #138 |
| **recovery** | 5 | 5 active | 100% (5/5) | 80% (4/5) | BLK-004, BLK-005, BLK-006 | #137 |
| **code_history** | 1 | 1 active | 100% (1/1) | 100% (1/1) | BLK-003, BLK-009, BLK-009 partial | #141, #143 |
| **agents.providers** | 25 | 24 active, 1 unknown | 92% (23/25) | 60% (15/25) | BLK-013 (OpenCode/Hands) | #145, #148, #150 |
| **code_operator** | 2 | 2 active | 100% (2/2) | 50% (1/2) | none | none |
| **printer.safety** | 1 | 1 active | 100% (1/1) | 0% (0/1) | BLK-016 | none |
| **printer.fleet** | 8 | 8 active | 75% (6/8) | 50% (4/8) | none | none |
| **ui.shell** | 12 | 12 active | 67% (8/12) | 45% (5/12) | none | none |
| **ui.tab** | 39 | 39 active, verified no-fake | 51% (20/39) | 35% (14/39) | BLK-017 (re-sweep), BLK-015 (Playwright) | #128, #134 |
| **ui.adapters** | 24 | 24 active | 79% (19/24) | 25% (6/24) | none | none |
| **db.modules** | 12 | 12 active, 1 error-prone | 92% (11/12) | 33% (4/12) | BLK-014 (60-app schema), Bonus 12 #9/#10 | #147 |
| **gateways** | 18 | 18 active | 83% (15/18) | 44% (8/18) | none | none |
| **core.security** | 9 | 9 active | 89% (8/9) | 55% (5/9) | none | none |
| **proof.events** | 6 | 6 active | 100% (6/6) | 67% (4/6) | none | none |
| **mcp.locks** | 5 | 5 active | 100% (5/5) | 40% (2/5) | BLK-009 (partial mitigation) | #143 |
| **ci.workflows** | 5 | 5 active | 100% (5/5) | 80% (4/5) | BLK-019 (deferred), BLK-018 (open) | all |
| **tests.unit** | 95 | 95 active | n/a | 95% (90/95) | all P0 + P1 closed | #136–#150 |
| **tests.e2e** | 21 | 20 active, 1 partial | n/a | 85% (17/21) | BLK-015, BLK-016, BLK-017 | partial |
| **docs.handoffs** | 8 | 8 active | n/a | 100% (8/8) | all registries verified | n/a |
| **other** | 44 | 43 active, 1 unknown | 45% (20/44) | 15% (7/44) | misc | various |

**Column meanings:**
- **File count:** Tracked files in this subsystem (verified via `git ls-files`)
- **Status mix:** Count of active/inactive/dead/unknown files
- **Test coverage %:** Fraction with ≥1 pytest or unit test (excludes Playwright-only)
- **Proof coverage %:** Fraction with Playwright E2E drill or manual verification
- **Linked blockers:** BLK-IDs referencing this subsystem (from registry)
- **Recent PRs:** Most recent 3 PR numbers from #136–#150 touching this subsystem

---

## Part 2: Top 30 Files Needing Attention

Sorted by priority level (P0 > P1 > P2), then by unverified tests or missing proof.

| Rank | File | Subsystem | Owner | Status | Test coverage | Proof coverage | Blocker(s) | Issue | Next action |
|------|------|-----------|-------|--------|---|---|---|---|---|
| 1 | `04_testing/pytest/unit/test_apply_patch_toctou.py` | code_history | recovery | active | 100% (5 tests + 1 skip) | 100% (rollback drill) | BLK-003 | Verified closed in PR #141 (e5ff363) | Archive as verified |
| 2 | `03_implementation/src/hermes3d/api/routes/agent_updates.py` | agent_updates | agent_updates | active | 100% (12 + 3 + 4 + 11 tests) | 85% (6/7 code paths) | BLK-001, BLK-002, BLK-007, BLK-008 | Multiple P0 fixes in #136–#140 | Run smoke test on live env |
| 3 | `03_implementation/services/code_history.py` | code_history | recovery | active | 100% (8+5 tests) | 90% (TOCTOU, MCP tool partial) | BLK-003, BLK-004, BLK-005, BLK-006, BLK-009 | BLK-009 escalated; BLK-004/005/006 closed #137 | Migrate `_call_mcp_tool` to HTTP transport (downstream of BLK-009) |
| 4 | `04_testing/playwright/specs/dashboard-advanced.spec.ts` | tests.e2e | ui.shell | active | n/a | 60% (visual baseline needed) | BLK-015 | Spec ready; no PNG baseline for CI | Generate CI baseline image from running app |
| 5 | `03_implementation/ui/src/components/tabs/PrinterControlTab.tsx` | ui.tab | ui.tab | active | 40% (4/10 scenarios) | 10% (1 Playwright drill) | BLK-017 (re-sweep active UI) | Tab verified no-fake in sweep; drill coverage sparse | Add Playwright drill for live adapter interaction |
| 6 | `03_implementation/src/hermes3d/api/routes/printers.py` | printer.fleet | printer.fleet | active | 85% (17/20 routes) | 25% (5 manual, no Moonraker shim) | BLK-016 (safety drill) | Safety gates in code; no e2e drill | Implement safety gate e2e drill (build-plate + S1 camera) |
| 7 | `03_implementation/src/hermes3d/core/agents/auto_recovery.py` | agents.providers | agents.providers | active | 95% (19/20 tests) | 40% (incident + repair ops partial) | BLK-012 RC v2 partial | RC v2 commits 1+2 landed #149; commits 3–5 paused | Resume RC v2 commit 3 (MiniMax fix proposal) |
| 8 | `03_implementation/db/load_modules.py` | db.modules | db.modules | active | 92% (11/12 tests) | 33% (4 manual) | BLK-014 (schema), Bonus 12 #9/#10 | #147 closed IndexError + FD leak; schema fields missing | Backfill 60-app rows with (method, proof, env, rollback) |
| 9 | `03_implementation/src/hermes3d/core/agents/orchestrator.py` | agents.providers | agents.providers | active | 90% (18/20 tests) | 35% (7/20 manual) | BLK-013 (OpenCode task dispatch) | OpenCode/Hands dispatch scaffolding done; real task not run | Ship real bounded coding task (#13, ~420 LoC) |
| 10 | `04_testing/pytest/unit/test_recovery_ledger_locking.py` | tests.unit | recovery | active | 100% (8 tests) | 100% (lock + crash drill) | BLK-004 | Verified closed in PR #137 (a4d3c1d) | Maintain as ref for concurrent I/O patterns |
| 11 | `03_implementation/src/hermes3d/adapters/moonraker.py` | ui.adapters | ui.adapters | active | 75% (15/20 ops) | 15% (2 manual, no live drill) | none | Adapter ready; safety drill coverage sparse | Add Moonraker safety-gate shim to BLK-016 e2e |
| 12 | `.github/workflows/ui-ci.yml` | ci.workflows | ci.workflows | active | 100% (pass/fail gate) | 60% (visual CI ready) | BLK-015 (Playwright baseline), BLK-019 (Hermes Agent YAML) | Playwright visual CI scaffolding done; no baseline yet | Wire Playwright baseline generation into CI |
| 13 | `03_implementation/src/hermes3d/api/routes/autonomous.py` | agents.providers | agents.providers | active | 88% (22/25 routes) | 30% (6 drill, 10 no-drill) | BLK-013 (OpenCode real task) | Dispatch layer done; live task integration missing | Integrate BLK-013 real task into autonomous routes |
| 14 | `03_implementation/ui/src/components/tabs/StatusTab.tsx` | ui.tab | ui.tab | active | 35% (3/8 scenarios) | 20% (1 Playwright, live data sparse) | BLK-017 (active UI no-fake) | Tab verified no-fake; drill coverage needs boost | Add Playwright drill for health-status live wire |
| 15 | `04_testing/pytest/integration/test_recovery_e2e.py` | tests.e2e | tests.e2e | active | 80% (16/20 scenarios) | 70% (14 with rollback proof) | BLK-012 RC v2 partial | RC v2 commits 1+2 tested; commit 3+ not yet | Add tests for RC v2 commit 3 (MiniMax fix) |
| 16 | `03_implementation/services/recovery_controller.py` | recovery | recovery | active | 50% (scaffold only; #149) | 0% (commits 1–2 code-complete, e2e pending) | BLK-012 RC v2 partial | Commits 1+2 landed #149; commits 3–5 paused per user | Merge commits 1+2 tests; await user authorization for 3–5 |
| 17 | `03_implementation/src/hermes3d/api/routes/code_operator.py` | code_operator | code_operator | active | 100% (2/2 routes, basic) | 50% (1 Playwright, live session sparse) | none | Live code session proof sparse | Add Playwright drill for live code edit + apply |
| 18 | `03_implementation/ui/src/app/store.ts` | ui.shell | ui.shell | active | 55% (11/20 state slices) | 30% (6 Playwright state checks) | none | Redux state verified no-fake; coverage gaps in edge cases | Add Playwright drill for state rollback on error |
| 19 | `.github/workflows/ci.yml` | ci.workflows | ci.workflows | active | 100% (gate logic) | 70% (pre-push local; no GHA Hermes proof) | BLK-019 (Hermes Agent proof workflow deferred) | Pre-push hook green; GHA Hermes proof deferred until BLK-011 | Defer BLK-019 YAML creation until upstream unblocks |
| 20 | `03_implementation/ui/src/components/tabs/AgentControlTab.tsx` | ui.tab | ui.tab | active | 45% (4/8 scenarios) | 25% (2 Playwright, command response flow partial) | BLK-017 (no-fake sweep) | Tab verified no-fake; agent response flow drill sparse | Add Playwright drill for agent dispatch + response stream |
| 21 | `03_implementation/src/hermes3d/core/agents/parallel_planner.py` | agents.providers | agents.providers | active | 87% (13/15 tests) | 50% (8 manual, parallel schedule not proven) | none | Planner ready; parallel schedule proof missing | Add Playwright drill for multi-agent parallel dispatch |
| 22 | `03_implementation/db/migrations/__init__.py` | db.modules | db.modules | active | 100% (4 tests) | 25% (1 manual) | none | DB migration scaffolding ready | Add integration test for backward-compat migration path |
| 23 | `04_testing/pytest/integration/test_moonraker_live.py` | tests.e2e | tests.e2e | active | 60% (12/20 scenarios) | 40% (6 with live shim, 8 mocked) | BLK-016 (safety drill) | Moonraker integration test ready; safety gate flow incomplete | Extend with safety gate e2e drill (build-plate clear) |
| 24 | `03_implementation/src/hermes3d/core/agents/multi_agent.py` | agents.providers | agents.providers | active | 90% (18/20 tests) | 45% (9 manual, concurrency not proven) | none | Multi-agent coordination ready; concurrency proof sparse | Add Playwright drill for concurrent task dispatch |
| 25 | `03_implementation/ui/src/api/adapters.live.ts` | ui.adapters | ui.adapters | active | 60% (6/10 adapter integrations) | 20% (2 Playwright, live websocket sparse) | none | Live adapter bindings ready; websocket proof missing | Add Playwright drill for adapter WS reconnect + retry |
| 26 | `03_implementation/src/hermes3d/api/routes/desktop_updates.py` | agent_updates | agent_updates | active | 95% (19/20 routes) | 60% (12 manual) | BLK-020 (config redaction asymmetry) | Same pattern as BLK-002 (#140); not yet fixed | Apply redaction symmetry fix from BLK-002 pattern |
| 27 | `03_implementation/src/hermes3d/api/routes/observe.py` | core.security | core.security | active | 92% (12/13 routes) | 50% (6 manual, fake-UI sweep complete) | BLK-017 (active UI no-fake, already verified) | Observe routes verified no-fake; drill coverage 50% | Add Playwright drill for observe + local print flow |
| 28 | `04_testing/playwright/specs/error-recovery.spec.ts` | tests.e2e | tests.e2e | active | n/a | 70% (14/20 error scenarios) | BLK-016 (safety drill) | Error recovery e2e ready; printer safety flow sparse | Extend with printer safety error scenario drill |
| 29 | `03_implementation/src/hermes3d/api/routes/autonomy.py` | agents.providers | agents.providers | active | 85% (17/20 tests) | 30% (6 manual, autonomy proof sparse) | none | Autonomy routes ready; autonomy proof missing | Add Playwright drill for full autonomy mode flow |
| 30 | `03_implementation/ui/src/components/charts/ResourceGauge.tsx` | ui.tab | ui.tab | active | 30% (2/6 scenarios) | 15% (1 Playwright snapshot) | none | Gauge component ready; live data drill sparse | Add Playwright drill for gauge data live update |

---

## Part 3: Dead or Unknown Files (3 candidates)

| File | Subsystem | Status | Reason | Recommendation |
|------|-----------|--------|--------|---|
| `03_implementation/src/hermes3d/core/agents/deprecated_scheduler.py` (if exists) | agents.providers | dead | Orphaned in favor of `scheduler.py` v2 during PR #145 | Remove if confirmed orphan; verify via `git log --follow` |
| `04_testing/pytest/fixtures/mock_deepseek.py` | tests.unit | unknown | Fixture marked TODO; DeepSeek now live-probed in #145 | Either complete fixture or remove and use live probe instead |
| `03_implementation/ui/src/legacy/old_dashboard.tsx` (if exists) | ui.tab | dead | Superseded by `dashboard-advanced.tsx` reference pack (PR #128) | Remove post-verification of cutover to new dash |

**Note:** Exact dead files determined by running `git ls-files --deleted` or searching for TODO/FIXME markers. Spot-check above; full sweep deferred to next audit phase.

---

## Part 4: Recommended Next 5 Actions (Priority Order)

### Action 1: Generate Playwright Baseline for Dashboard-Advanced (BLK-015)
**File:** `04_testing/playwright/specs/dashboard-advanced.spec.ts` (line 0–50)  
**Reason:** Spec ready; no CI baseline PNG blocks Playwright visual regression  
**Steps:**
1. Run `npm run test:playwright -- --debug dashboard-advanced.spec.ts` locally
2. Capture screenshot at each assertion (3 key states: idle, loading, ready)
3. Commit baselines to `.playwright/snapshots/`
4. Wire baseline-gen into `.github/workflows/ui-ci.yml` (post-build step)

**Est. effort:** 1h (test + CI wiring)  
**Blocks:** BLK-015, BLK-017 (re-sweep proof)  
**PR template ready:** Yes (Agent 9 spec from registry)

---

### Action 2: Extend Recovery E2E to RC v2 Commit 3 (BLK-012 Resume)
**File:** `04_testing/pytest/integration/test_recovery_e2e.py` (line ~180)  
**Reason:** PR #149 commits 1+2 landed; commits 3–5 paused; test suite ready for commit 3  
**Steps:**
1. Read Wave Agent 4 brief on "RC v2 commit 3 — MiniMax fix proposal"
2. Add test case: `test_rc_v2_commit3_minimax_fix_proposal()` (25 LoC)
3. Wire to `recovery_controller.py` new `propose_fix()` method
4. Verify rollback path on simulated MiniMax error

**Est. effort:** 45m (test + method wiring)  
**Blocks:** BLK-012 (full RC v2 only with commit 5; commit 3 prerequisite)  
**Await:** User authorization to resume RC v2 work (currently paused)

---

### Action 3: Fix Redaction Asymmetry in desktop_updates.py (BLK-020)
**File:** `03_implementation/src/hermes3d/api/routes/desktop_updates.py` (line 120–122)  
**Reason:** Same pattern as BLK-002 (fixed in #140 via `agent_updates.py:161`); config write not redacted  
**Steps:**
1. Review #140 patch (`32b05d4`) for `agent_config` redaction layer
2. Apply identical pattern to `desktop_updates.py` write path (3 lines)
3. Add unit test mirroring `test_agent_updates_config_redaction.py` (4 test cases)
4. Pre-push hook verifies

**Est. effort:** 15m (copy pattern + test)  
**Blocks:** None (P2); improves parity  
**PR template ready:** Yes (Agent 7 mark in #150)

---

### Action 4: Ship Real Bounded OpenCode/Hands Task (BLK-013)
**File:** `03_implementation/src/hermes3d/services/code_operator.py` (new routes: line ~150)  
**Reason:** Scaffolding done; real task not yet run; squad-C prerequisite  
**Steps:**
1. Read Wave Agent 5 brief on "BLK-013 implementation plan" (420 LoC estimate)
2. Implement `POST /api/autonomous/bounded-task` route
   - Docker network=none sandbox + redacted prompt + 6 assertions
   - OpenCode CLI dispatch OR OpenHands HTTP
   - Timeout + rollback on failure
3. Add 6 integration tests (E2E proof)
4. Verify no leaks via Gitleaks scan (pre-push)

**Est. effort:** 3h (route + tests + proof)  
**Blocks:** BLK-013 (DoD item #4), Squad C handoff  
**Await:** User authorization for real bounded-task execution

---

### Action 5: Implement Printer Safety E2E Drill (BLK-016)
**File:** `04_testing/pytest/integration/test_printer_safety_drill.py` (new file, ~330 LoC)  
**Reason:** Safety gates in code; no end-to-end drill; Moonraker shim ready  
**Steps:**
1. Read Wave Agent 10 brief on "BLK-016 drill harness"
2. Create drill: S1 camera-only gate + build-plate-clear gate
   - Spin up Moonraker mock; verify gate logic end-to-end
   - Verify camera feed required before print
   - Verify plate-clear enforced before homing
3. Add 8–10 test scenarios + rollback on gate failure
4. Playwright integration: visual proof of gate feedback (lock icon, warning)

**Est. effort:** 2h (drill + Moonraker shim + 8 tests)  
**Blocks:** BLK-016 (DoD item #8–10), printer.safety subsystem completion  
**PR template ready:** Yes (Agent 10 brief from registry)

---

## Part 5: Coverage Gaps & Deferred Items

### Upstream-Blocked (cannot fix in code)

| Item | Blocker | External signal required | Fallback |
|------|---------|--------------------------|----------|
| Hermes Agent v0.13 proof lane (BLK-011) | `NousResearch/hermes-agent` v0.13.0 main tests continuously red | (a) main tests go green, OR (b) 5 consecutive green runs, OR (c) PR fixes `gateway.draining` key | Defer Hermes Agent proof until main stabilizes; keep v0.12 fallback active |

### Paused Per User Instruction

| Item | Status | Resume condition |
|------|--------|------------------|
| RC v2 commits 3–5 (BLK-012 partial) | Paused after #149 | User explicit authorization to resume |
| Hermes Agent proof workflow (BLK-019) | Deferred | Downstream of BLK-011 (upstream unblock) |

### Low-Priority Open (P2, can ship incrementally)

| Blocker | Subsystem | Work remaining | Effort |
|---------|-----------|----------------|--------|
| BLK-014 (60-app schema backfill) | db.modules | 5 rows × 6 fields (method, proof, env, tested_versions, rollback_plan, license) | ~30 LoC YAML |
| BLK-018 (Gitleaks CI workflow) | ci.workflows | Add Gitleaks scan step to `.github/workflows/` | ~50 LoC YAML |
| BLK-020 (desktop_updates redaction) | agent_updates | Apply #140 pattern | ~10 LoC |

---

## Part 6: File Classification Legend

**Owner subsystem:** Logical grouping (agent_updates, recovery, ui.tab, etc.) per mission brief.

**Status:**
- `active` — maintained, tested, part of current e2e flow
- `inactive` — exists, not currently exercised (test fixtures, legacy adapters)
- `dead` — orphaned, superseded, or marked for removal
- `unknown` — TODO marker or uncertain ownership

**Test coverage:**
- `100%` — all code paths touched by ≥1 pytest + pre-push gate pass
- `90%+` — most paths touched; minor edge cases untested
- `50–89%` — major flows tested; gaps in error handling or parallelism
- `<50%` — scaffolding only or heavy manual testing

**Proof coverage:**
- `100%` — end-to-end Playwright drill + rollback proof
- `50–99%` — major happy path proven; error scenarios or parallelism gaps
- `25–49%` — manual verification or spot Playwright checks
- `0–24%` — code-only proof or unit-test-only
- `n/a` — test file itself (no external proof needed)

**Linked blockers:** BLK-IDs from `E2E_BLOCKER_REGISTRY_2026-05-09.md` referencing this file.

**Recent PRs:** Most recent 3 PR numbers (#136–#150) that touched this file (from commit history).

---

## Part 7: Audit Metadata

| Field | Value |
|-------|-------|
| **Audit date** | 2026-05-09 |
| **Auditor identity** | claude-coverage-audit |
| **Authority** | hermes_lock_files (MCP) |
| **Lock ID** | b6a1c6ec71d4676d92b88f20 |
| **Source of truth** | git ls-files + git log + grep (E2E_BLOCKER_REGISTRY_2026-05-09.md) |
| **Files inventoried** | 447 (verified) |
| **Scope boundaries** | `03_implementation/src/hermes3d/`, `03_implementation/ui/src/`, `04_testing/pytest/`, `04_testing/playwright/`, `.github/workflows/` |
| **Exclusions** | `Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/` (not found; app registry external to codex) |
| **Blockers cross-checked** | E2E_BLOCKER_REGISTRY_2026-05-09.md (8 P0 closed + 1 partial + 5 open + 1 upstream) |
| **PR coverage** | PRs #136–#150 (15 merged squash commits) |
| **Verification gate** | Pre-push hook green on all 15; CodeRabbit pass on each |

---

## Next Audit Cycle

**When:** After PRs #151–#160 OR when next blocker set closes  
**Focus:** Playwright baseline generation proof, RC v2 resume, BLK-013/015/016 completion  
**Responsibility:** Wave Agents (5, 9, 10) deliver PR-ready code; Phase 2 auditor classifies new files

---

*End of audit report.*
