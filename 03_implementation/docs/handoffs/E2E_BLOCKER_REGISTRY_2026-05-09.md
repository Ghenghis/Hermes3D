# E2E Blocker Registry — Hermes3D OS

**Date:** 2026-05-09
**Mission:** Find, research, reproduce, fix, test, and prove every blocker preventing Hermes3D OS from working end-to-end.
**Mandate:** No vague "done." No fake pass. No broad skip. No secret leaks. No unlocked edits.
**Convert every blocker into one of:**
1. fixed with PR and passing proof,
2. upstream/environment blocked with exact evidence,
3. user-action required with exact steps,
4. deferred by explicit user approval.

---

## STATUS UPDATE 2026-05-10 (post Wave 5; W5-8b doc-fix)

The Wave 5 swarm executed PRs #155–#174 between 2026-05-09T23:23Z and 2026-05-10T01:44Z. Several rows below are now superseded. The supersessions in this STATUS UPDATE are authoritative; the table further down is the historical pre-Wave-5 verdict.

| Row | Pre-Wave-5 status | Post-Wave-5 status | Source of truth |
|---|---|---|---|
| **DoD #3** "Hermes Agent proof lane passing OR formally deferred" | `deferred` | **`superseded-by-PR-#160`** — v0.13 promoted to production default 2026-05-10T00:19Z (squash `3158a4e`); v0.12 remains opt-in fallback via `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`. Re-grouped main `Tests` runs by `workflow_id=242054771`: **39/100 green** (correcting the earlier "0 succeeded" query artifact); cf. `HERMES_AGENT_ONLY_SWARM_STATUS_2026-05-09.md:L13`. | PR #160 metadata; `services/agent_checkout.py:L31` (`DEFAULT_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-v013-canary")`). |
| **DoD #1** MiniMax smoke | `open` | `open` (live re-smoke pending; provider env confirmed by `PROVIDER_RESCUE_BLOCKER_PROOF_2026-05-09.md`: HTTP 200 `accepted:true` `ev_4a52d9b1336ca9f2`). | PROVIDER_RESCUE_BLOCKER_PROOF |
| **DoD #2** DeepSeek smoke | `open` | `open` (live re-smoke pending; provider env confirmed: HTTP 200 `accepted:true` `ev_e708071cb269f170`). | PROVIDER_RESCUE_BLOCKER_PROOF |
| **BLK-011** "v0.13.0 upstream tests.yml continuously red \| last 100 main runs: 0 succeeded" | `upstream-blocked` | **`superseded-by-PR-#160`** — corrected to 39/100 green when re-grouped by canonical workflow_id; PR #160 then promoted v0.13 to default. | gh api workflows/242054771/runs (re-grouped); PR #160 |
| **BLK-021** Hermes Agent v0.13 cold-start race (DB schema not yet migrated when GUI loads) | (not yet in registry) | **new — P2** | `HERMES_AGENT_V013_GUI_E2E_2026-05-09.md:L137-138` (lives on the W5-3 branch) — cold-start UX race; git-tracked schema confirmed at `03_implementation/src/hermes3d/db/schema.sql`. Tracked here so it is not lost when that branch lands. |

**v0.13 deferral verdict (was at table row "BLK-011 stays deferred; v0.13.0 stays deferred until clean proof lane"):** **superseded.** v0.13 is now the production default. The "stays deferred" sentence below is retained for historical fidelity but **must not be acted on as a current decision**.

---

## E2E Definition of Done

Hermes3D OS is **not E2E-ready** until every row below is `verified` or has explicit user approval to defer:

| # | DoD item | Status |
|---|---|---|
| 1 | MiniMax smoke passes | open (provider audit, Agent 14, says env-ready; needs live re-smoke) |
| 2 | DeepSeek smoke passes | open (same — Agent 14 confirms code path, needs live re-smoke) |
| 3 | Hermes Agent proof lane passing OR formally deferred with safe fallback | **deferred** (Agent 1 swarm: upstream main is continuously red; v0.13 stays deferred) |
| 4 | OpenCode + OpenHands run a real bounded coding/audit task (not just preflight) | open (squad C) |
| 5 | Recovery Controller v2 handles failure → repair → review → retry | paused (squad B; RC v1 ledger fixes done in PR #137) |
| 6 | 60 apps have update/install/proof profiles | open (Agent 3 swarm: 0/60 rows have any of those fields today) |
| 7 | No fake UI states in active tabs | partial (Agent 15 swarm: 16/16 tabs wire to live adapters; needs Playwright proof) |
| 8 | Printer safety gates pass | open (squad F) |
| 9 | S1 remains camera-only | open (squad F) |
| 10 | Build plate clear gate enforced | open (squad F) |
| 11 | GUI has Playwright proof for changed pages | open (squad E) |
| 12 | Staged updater has backup + rollback proof | partial (PR #137 closed auto-repair gap; needs an end-to-end backup→update→rollback drill) |
| 13 | No secret values in logs/proofs/docs | **verified** (Bonus 14 + Agent 14: NO_LEAKS_FOUND) |
| 14 | CI + local gates pass | partial (pre-push hook green; CI lane is CodeRabbit-only on this base) |

---

## Blocker Registry

| ID | Subsystem | Sev | Symptom | Reproduction | Squad | Files | Receipts | Fix PR | Tests/Proof | Rollback | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BLK-001 | hermes-agent.update | P0 | Bonus 12 #5 SSRF / silent-degrade | `_remote_release_tags` returned `[]` on every Exception → `already_current` masking stale checkout | swarm | `agent_updates.py:222-255` | bonus12-bug-finder.md, CWE-918, OWASP CICD-SEC-1 | **#139** (e0b719d) | `test_agent_updates_ssrf.py` 12/12 | n/a (additive failure mode) | **verified** |
| BLK-002 | hermes-agent.update | P0 | Bonus 12 #6 redaction asymmetry — agent_config persisted raw payload | `INSERT INTO agent_config` wrote unredacted output strings | swarm | `agent_updates.py:161,191` | OWASP A02/A09, Sentry redaction docs | **#140** (32b05d4) | `test_agent_updates_config_redaction.py` 4/4 | n/a | **verified** |
| BLK-003 | code-history | P0 | Bonus 12 #7 TOCTOU + crash-window in `apply_patch_proposal` | hash verified AFTER `os.replace`; no fsync; no inflight DB record | swarm | `code_history.py:1473-1484` | etcd #13839, LWN #457667 | **#141** (e5ff363) | `test_apply_patch_toctou.py` 5/5+1skip | rollback path tested via simulated crash | **verified** |
| BLK-004 | code-history | P0 | Bonus 12 #1 recovery-ledger file-lock gap | concurrent `record_step_failure` interleaved partial JSONL lines | swarm | `code_history.py:3995-4173` | fcntl/msvcrt docs, Codecov 2021 | **#137** (a4d3c1d) | `test_recovery_ledger_locking.py` 8/8 | n/a | **verified** |
| BLK-005 | code-history | P0 | Bonus 12 #2 non-idempotent `mark_recovery_outcome` | retries appended duplicate outcome rows | swarm | `code_history.py:4101` | atomic-read-then-append pattern | **#137** | included in BLK-004 tests | atomic check inside lock | **verified** |
| BLK-006 | hermes-agent.update | P0 | Bonus 12 #3 HTTPException escapes auto-repair | failed mid-step `git checkout` returned 502, left repo on unverified tag | swarm | `agent_updates.py:115` | per-loop try/except pattern | **#137** | `test_agent_updates_auto_repair.py` 3/3 | structured rollback verified | **verified** |
| BLK-007 | hermes-agent.update | P0 | Bonus 12 #4 ZIP path-traversal + missing allowZip64 | symlink/oversized backup leaked into archive | swarm | `agent_updates.py:_zip_dirty_entries` | CWE-22, zipfile docs | **#138** (d308cc3) | `test_agent_updates_zip_dirty.py` 8/8 | n/a | **verified** |
| BLK-008 | hermes-agent.update | P0 | Staged-update gate fake-pass surface (path-only ignore + skip path) | `HERMES_AGENT_RUN_PYTEST` unset returned `status=skipped` | swarm | `agent_updates.py:_run_update_checks` | upstream tests.yml, OWASP CICD-SEC-1 | **#136** (320107a) | `test_agent_updates_skip_path.py` 11/11 + meta 3/3 | n/a | **verified** |
| BLK-009 | mcp.tools | P1 | Bonus 12 #8 `_call_mcp_tool` Popen deadlock pattern | manual reader threads + sleep loop + terminate/kill ladder | squad-G | `code_history.py:3380-3429` | Python subprocess docs | open (Agent 9 diff ready) | open | open | **fixing** |
| BLK-010 | docs.audit | P2 | Bonus 13 schema/audit errata: 42 SPDX-invalid, 5 repo URL mismatches, 60/60 missing tested_versions | doc only | doc-team | `bonus13-schema-inconsistency.md` | SPDX list, Fedora/Debian SPDX migration | open (Agent 10 diff ready) | open | n/a (docs) | **fixing** |
| BLK-011 | hermes-agent.update | P0 | v0.13.0 upstream tests.yml continuously red | last 100 main runs: 0 succeeded; PR #22567 closed-not-merged | squad-A | upstream `tests.yml` | Agent 1 swarm: gh api workflow runs | n/a (env/upstream) | meta-test pins our gate | n/a | **upstream-blocked** |
| BLK-012 | recovery-controller | P1 | RC v2 active repair loop missing | failure→repair→review→retry not implemented | squad-B | proposed `services/recovery_controller.py` | RC v1 ledger lock (PR #137) is prerequisite | n/a (paused) | n/a | n/a | **paused** |
| BLK-013 | agents.providers | P1 | OpenCode + OpenHands run real bounded task (not just preflight) | currently CLI-detection + sandbox-readiness only | squad-C | `code_history.py` CLI runners | Agent 14 swarm receipts | n/a | open | n/a | **open** |
| BLK-014 | apps.registry | P1 | 60-app update profile matrix has 0/60 rows with method/proof/env/rollback | YAML loader-real has none of these fields | squad-D | `Hermes3D-GUI-Wiring-Contract-Kit/03_REPO_REGISTRY/external_repos_registry.yaml`, `db/load_modules.py` | Agent 3 swarm; Bonus 13 | n/a | n/a | n/a | **open** |
| BLK-015 | ui.proof | P1 | No Playwright pixel-diff proof against `Images-GUI/` | ref pack landed PR #128/#134; specs not written | squad-E | `04_testing/playwright/specs/` | Agent 15 swarm | n/a | n/a | n/a | **open** |
| BLK-016 | printer.safety | P0 | S1 camera-only / build-plate-clear gates not e2e-proven | gate code exists; no end-to-end live drill | squad-F | `printer_policy`, `printer_safety` | prior PR #43, #51 | n/a | n/a | n/a | **open** |
| BLK-017 | observe.fake-ui | P2 | Active-UI no-fake sweep needs re-run after recent PRs | sweep proof exists at `proof/ACTIVE_UI_NO_FAKE_SWEEP.md` | squad-E | UI tabs | sweep doc | n/a | n/a | n/a | **open** |
| BLK-018 | secrets.scan | P2 | Continuous secret-leak guard not in CI | only manual grep done so far; Bonus 14 NO_LEAKS at 2026-05-09 | squad-G | `.github/workflows/` | TruffleHog / Gitleaks | n/a | n/a | n/a | **open** |
| BLK-019 | ci.lanes | P1 | No Hermes Agent proof workflow on free GHA runner | Agent 13 swarm provided drop-in YAML | squad-H | `.github/workflows/hermes-agent-proof.yml` (proposed) | Agent 13 receipts | n/a | n/a | n/a | **open** |
| BLK-020 | desktop-updates | P2 | Same un-summarized agent_config write pattern as BLK-002 | `desktop_updates.py:120-122` | swarm | `desktop_updates.py` | Agent 7 swarm cross-table audit | n/a | n/a | n/a | **open** |
| BLK-021 | hermes-agent.gui-e2e | P2 | Hermes Agent v0.13 cold-start race — DB schema not yet migrated when GUI loads on first run | git-tracked file confirmed at `03_implementation/src/hermes3d/db/schema.sql`; race observed during W5-3 GUI E2E drill | squad-E | `03_implementation/src/hermes3d/db/load_modules.py`, `schema.sql` | `HERMES_AGENT_V013_GUI_E2E_2026-05-09.md:L137-138` (W5-3 branch) | n/a | n/a | n/a | **open** (cold-start UX) |

---

## Hard Blocker Squad Assignments

| Squad | Hard blocker | Members |
|---|---|---|
| **A** | Hermes Agent v0.13 update proof lane (BLK-011) | research / reproducer / fix-builder (env) / test-builder / sec-reviewer / integrator |
| **B** | Recovery Controller v2 active repair loop (BLK-012) | same shape |
| **C** | OpenCode/OpenHands real coding task (BLK-013) | same |
| **D** | 60-app update/install/proof matrix (BLK-014) | same |
| **E** | GUI from Images-GUI + Playwright (BLK-015, BLK-017) | same |
| **F** | Printer/fleet/safety/observe (BLK-016) | same |
| **G** | Provider/secrets/process/sandbox (BLK-009, BLK-018) | same |
| **H** | CI/merge/update/rollback (BLK-019) | same |

Each squad uses up to 6 agents. Editing agents must hold MCP locks. No two squads edit the same file set without explicit handoff.

---

## Discovery Audit Plan

Run repo-wide grep for the following classes and classify every hit:

| Pattern | Classification axes |
|---|---|
| `TODO\|FIXME\|HACK\|XXX` | harmless / test fixture / real blocker / security / fake-UI / deferred |
| `mock\|fake\|simulated\|placeholder\|stub\|dummy` | same |
| `NotImplemented\|raise NotImplementedError` | same |
| `^\s*pass\s*$` (suspicious empty bodies) | same |
| `xfail\|@pytest.mark.skip\|@pytest.mark.xfail\|pytest.skip(` | same |
| `except Exception\|except:` (broad excepts) | same |
| `subprocess\|Popen\|os.system\|shell=True` | same |
| `urlopen\|requests.get\|httpx\.` | same |
| `zipfile\|tarfile\|extractall` | same |
| `os.environ\|getenv\|secrets\|password\|token\|api_key` | same |
| `# disabled\|# todo:\|# fixme` | same |
| `disabled-test\|skip_in_ci\|HIDDEN_DEMO\|DEMO_MODE` | same |

The discovery audit is delegated to swarm agents below. Each agent returns a classified table with file:line, class, and recommendation.

---

## Execution Order

1. **DONE** — Build registry (this file).
2. Run discovery audit (delegated to a 5-agent classification swarm).
3. Assign top 8 hardest blockers to squads (already mapped above; squads A–H).
4. Fix one PR at a time. Current cadence: PRs #136, #137, #138, #139, #140, #141 closed BLK-001/002/003/004/005/006/007/008.
5. No PR merges unless tests/proof pass — enforced by pre-push hook + CodeRabbit.
6. If a squad cannot pass after 2 loops, escalate with exact blocker and evidence.
7. Continue until registry has no open P0/P1 blockers.

---

## Provenance

- Audit doc: `60-apps-batch2/bonus12-bug-finder.md` (PR #135 / commit 5ecd8ff)
- Pre-existing 20-agent swarm output banks: Agents 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 (all returned)
- Standing user constraints honored: free/OSS only; no paid services; secrets at `G:/private/`. ~~v0.13.0 stays deferred until clean proof lane~~ **[SUPERSEDED 2026-05-10 by PR #160 — v0.13 is production default; v0.12 remains opt-in fallback via `HERMES_AGENT_CHECKOUT`.]**
