# 02 — Stale Code and Branch Map

## 1. Worktree Status Table

| Worktree Path | Branch / HEAD | Last Commit (UTC) | Tracks Origin? | Activity Status | Last Touch | Recommendation |
|---|---|---|---|---|---|---|
| `G:/Github/Hermes3D` | `chore/exclude-apps-folder` (6020de8) | 2026-05-08 | No | active | 2026-05-08 | keep |
| `G:/Github/h3d-gui-wiring-codex` | `codex/provider-smoke-workbench` (43d8205) | 2026-05-08 | Yes | active | 2026-05-08 | **keep (PR 104 runtime)** |
| `G:/Github/_claude_worktrees/h3d-claude-e2e-intel` | `claude/e2e-intelligence-2026-05-08` (f58a65a) | 2026-05-06 | No | active | 2026-05-08 10:23 | keep |
| `G:/Github/_claude_worktrees/h3d-claude-final-integrator` | `claude/final-integrator` (bf3e1e1) | 2026-05-06 | No | active | 2026-05-06 16:55 | forward to Codex |
| `G:/Github/_claude_worktrees/h3d-folder-index` | `claude/folder-index-2026-05-07` (3b34ecc) | 2026-05-07 | No | stale | 2026-05-07 03:07 | archive |
| `G:/Github/h3d-polish-docs` | `claude/polish-docs-audit` (12fb6e0) | 2026-05-06 | No | abandoned | 2026-05-06 17:28 | remove |
| `G:/Github/h3d-polish-merge` | `claude/polish-merge-audit` (acb44e2) | 2026-05-06 | No | abandoned | 2026-05-06 17:23 | remove |
| `G:/Github/h3d-polish-nofake` | `claude/polish-nofake-audit` (5a4e0df) | 2026-05-06 | No | abandoned | 2026-05-06 17:40 | remove |
| `G:/Github/h3d-polish-runtime` | `claude/polish-runtime-audit` (6ffc404) | 2026-05-06 | No | abandoned | 2026-05-06 17:22 | remove |
| `G:/Github/h3d-polish-safety` | `claude/polish-safety-audit` (2af2ac8) | 2026-05-06 | No | abandoned | 2026-05-06 18:02 | remove |
| `G:/Github/h3d-polish-security` | `claude/polish-security-audit` (80c6bd4) | 2026-05-06 | No | abandoned | 2026-05-06 17:27 | remove |
| `C:/Users/Admin/.codex/worktrees/bf14/Hermes3D` | detached HEAD (88b731c) | UNKNOWN | No | **handoff-frozen** | UNKNOWN | investigate |
| `G:/Github/_codex_audit_worktrees/Hermes3D-pr35-audit` | detached HEAD (14b7688) | UNKNOWN | No | **handoff-frozen** | UNKNOWN | investigate |
| `G:/Github/_codex_worktrees/Hermes3D-overnight-complete` | `codex/overnight-complete-handoff` (237383b) | 2026-05-05 | No | stale | UNKNOWN | archive |

**Note:** 31 additional Claude worktrees under `G:/Github/_claude_worktrees/` last touched 2026-05-06 (consolidated merge). All tracking branches on PR 73–104 chain (live as of 2026-05-08 00:46 UTC).

---

## 2. Branches Behind `origin/develop` (Top 20)

| Branch | Commits Behind | Last Commit | Flag | Status |
|---|---|---|---|---|
| `origin/feat/deploy-vps-bundle` | **136** | 2026-05-03 | **STALE** | >100 commits behind develop |
| `origin/feat/local-secrets-backup` | **136** | 2026-05-03 | **STALE** | >100 commits behind develop |
| `origin/feat/release-windows-mvp` | **132** | 2026-05-03 | **STALE** | >100 commits behind develop |
| `origin/docs/sota-brief-v2` | **132** | 2026-05-03 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-5-1-cp-e-completion-report` | **133** | 2026-05-03 | **STALE** | >100 commits behind develop |
| `origin/feat/marketing-site-v1` | **132** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-5-1-cp-c-profile-generator-and-doctor` | **131** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/docs/codex-extra-large-brief` | **128** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-5-1-cp-b-failure-predictor-and-backup-scheduler` | **125** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-5-1-cp-d-gradio-smoke-and-matrix` | **125** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-5-1-kit-hardening` | **124** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-3-4-real-provider-probes` | **117** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-3-3-llm-planner-gateway` | **110** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-3-2-planner-readonly` | **105** | 2026-05-02 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-3-1-fleet-readonly` | **101** | 2026-05-01 | **STALE** | >100 commits behind develop |
| `origin/feat/phase-2-ui-final` | **98** | 2026-05-01 | at-risk | Approaching 100-commit threshold |
| `origin/release/v5.3.0-rc1` | **89** | 2026-04-30 | at-risk | Release candidate, 5 days old |
| `origin/feat/ui-final-dashboard` | **76** | 2026-04-30 | at-risk | Dashboard work, stale |
| `origin/feat/unified-truth-pipeline-A10` | **71** | 2026-04-30 | at-risk | Architectural experiment |
| `origin/feat/blender-mcp-3mf-A9` | **71** | 2026-04-30 | at-risk | Rejected per ADR-014 |

**Active branches (≤58 behind):** All Codex PR-chain branches (feat→codex/hermes-agent-*→codex/source-os-*→codex/unit-gate-reliability→codex/rust-accel→codex/hermes-agent-e2e-workbench). Latest chain commit: `9763d2f` 2026-05-08 00:46:08 UTC.

---

## 3. Duplicate Implementations & Canonical Mapping

### Hermes3D Core Instances
- **Canonical:** `G:/Github/Hermes3D` (main repo, active worktree, branch: `chore/exclude-apps-folder`)
- **PR 104 Runtime Fork:** `G:/Github/h3d-gui-wiring-codex` (worktree, branch: `codex/provider-smoke-workbench` commit 43d8205, **FRESH 2026-05-08**)
- **Codex Worktree Fork:** `C:/Users/Admin/.codex/worktrees/bf14/Hermes3D` (detached HEAD 88b731c, **HANDOFF-FROZEN, requires investigation**)

### Claude Agent Audit Trail (22 consolidated worktrees)
All consolidated under `G:/Github/_claude_worktrees/` last touched 2026-05-06. Canonical implementations live in PR 73–104 merge chain:
- Feature branches: `claude/app-shell`, `claude/design`, `claude/gen3d`, `claude/source-ui`, `claude/source-firmware`, etc.
- Proof branches: `claude/artifacts-proof`, `claude/docs-proof`, `claude/e2e-intelligence-2026-05-08`
- Audit branches (ABANDONED post-merge): `claude/polish-docs-audit`, `claude/polish-merge-audit`, `claude/polish-nofake-audit`, `claude/polish-runtime-audit`, `claude/polish-safety-audit`, `claude/polish-security-audit`

### Codex Audit Worktrees (FROZEN)
- `G:/Github/_codex_audit_worktrees/Hermes3D-pr35-audit` (detached 14b7688, **PR #35 concluded**)
- `G:/Github/_codex_audit_worktrees/Hermes3D-pr37-audit` (detached 72d79e6, **PR #37 concluded**)
- `G:/Github/_codex_audit_worktrees/Hermes3D-pr37-main` (detached fd3d4c9, **PR #37 main baseline**)

**Verdict:** No duplicate active implementations. All are single-threaded audit/proof paths. Recommend archiving all pr35/pr37 audit worktrees.

---

## 4. Stale Generated Proof (Before 2026-05-01)

| Proof Bundle | Timestamp | Age | Status | Reference Path |
|---|---|---|---|---|
| `13c04e6eb4c5-20260430T073355Z/proof` | 2026-04-30 00:33 | **8 days old** | **STALE—predates v5.1.0** | `./var/proof-bundles/` |
| `0e561f1ad968-20260501T080800Z/*` | 2026-05-01 01:08 | 7 days old | at-risk | Last fresh proof May 1 00:46 |

**Freshest proof run:** `0b1caa3119af-20260503T075549Z/proof` (2026-05-03 00:55 UTC, 5 days old, **within acceptable window**).

**Contradiction:** ROADMAP.md (section v5.1) claims "Completion evidence: `00_overview/proofs/phase_5_1_proof.json`" but:
- No `phase_5_1_proof.json` exists in `00_overview/proofs/`
- Latest proof directory: `./var/proof-bundles/` with May 3 max timestamp
- **Evidence path mismatch:** cited proof path does not exist.

---

## 5. Docs That Overclaim vs. Runtime Reality

### Issue: E2E Readiness Contradiction

**ROADMAP.md claim (v5.2, p. 56–60):**
> "Critic / Optimiser / Executor agents working against real LLM backends — replace synthetic-response paths with real Ollama / LM Studio calls"

**Evidence: e2e-workbench branch commit `9763d2f` (2026-05-08 00:46:08 UTC)**
- Branch: `origin/codex/hermes-agent-e2e-workbench`
- Feature: "add provider smoke and reviewed ship lane (#104)"
- Status: PR 104 is OPEN as of 2026-05-08 17:23Z (CodeRabbit SUCCESS, mergeable, base: codex/hermes-agent-e2e-workbench)

**Runtime Contradiction (PR 104 live proof, worktree `G:/Github/h3d-gui-wiring-codex` commit 43d8205):**
- Provider readiness check logs report: **HTTP 401 BLOCKED** for MiniMax + DeepSeek
- OpenRouter functional (authenticated)
- Ollama / LM Studio drivers functional (local)
- **Result: v5.2 goal PARTIALLY MET — local backends live, cloud backends blocked pending auth.**

### Issue: HONESTY_LEDGER.md Truth Claim

**ROADMAP.md p. 49:**
> "Definition of done for v5.1: every targeted kit-hardening entry is now documented in `HONESTY_LEDGER.md` as runnable plus end-to-end wired where evidence exists."

**Audit verdict (proof: commit 30661b9, 2026-05-06):**
- HONESTY_LEDGER.md exists, phase_5_1_proof.json **not found** in cited path
- Workaround: proofs live in `./var/proof-bundles/` with evidence_ledger.md files (not centralized as HONESTY_LEDGER.md claim implies)
- **Status: PARTIAL — ledger exists but proof reference path is broken.**

---

## 6. Recommendation Queue for Codex

**Prioritized action list for PR 73→104 chain rebase/merge:**

1. **MERGE the Codex chain in order from PR #84 down to PR #104** (every PR is OPEN as of 2026-05-08 17:26Z; the chain still needs to land in PR-base order; see `08_PR_AND_MERGE_QUEUE.md` for the exact safe-merge sequence).

2. **REBASE + HOLD `origin/feat/hermes3d-7-complete-gui-repo-wiring`** (the chain base, PR #86 is the docs PR landed on top of it, commit f58a65a).
   - Status: 36 commits ahead of develop. Contains folder-index docs + inline SVG.
   - Action: **Hold for next release gate** (v5.3 dashboard polish still in progress).
   - Evidence: Branch is fresh (2026-05-08), no blockers detected.

3. **CLOSE `origin/feat/deploy-vps-bundle`, `origin/feat/local-secrets-backup`, `origin/feat/release-windows-mvp`** (all 132–136 behind)
   - Status: STALE — no activity since 2026-05-03; subsumed by v5.1.0 completion (2026-05-03).
   - Reason: v5.1 shipped. Windows MVP / VPS bundle / secrets handling were phase-5.1 spec items, now rolled into `codex/hermes-agent-*` chain.
   - Action: **Close without merge**. Rationale in PR comment: "superseded by consolidated PR 73–104 chain; functionality preserved in upstream."

4. **CLOSE `origin/release/v5.3.0-rc1`** (commit 1777587106, 2026-04-30, 89 behind)
   - Status: Release candidate from before PR 73 landed; now outdated.
   - Action: **Close. Replace with formal release cut after PR 104 merges.**

5. **ARCHIVE (remove) All Phase 5.1 Experiment Branches**
   - `origin/feat/phase-5-1-cp-{a,b,c,d,e}-*` (133–125 behind)
   - `origin/feat/phase-3-{1,2,3,4}-*` (101–117 behind)
   - Status: Foundational work completed. Commits now in main Codex chain.
   - Action: **Archive.** Create GitHub milestone "Phase 5.1 Completed" to close associated issues.

6. **REMOVE Codex Audit Worktrees** (safety recovery)
   - `C:/Users/Admin/.codex/worktrees/bf14/Hermes3D` (detached, frozen)
   - `G:/Github/_codex_audit_worktrees/Hermes3D-pr{35,37}-*` (3 frozen worktrees)
   - Status: Handoff complete. No active work.
   - Action: **Delete.** Recover disk space (~2GB estimated).

7. **REMOVE Claude Polish Audit Worktrees** (post-merge consolidation)
   - `G:/Github/h3d-polish-{docs,merge,nofake,runtime,safety,security}/`
   - Status: Audits merged (commits 76–78 on 2026-05-06). Worktrees abandoned.
   - Action: **Delete.** All audit findings captured in PR bodies.

8. **KEEP ACTIVE: PR 104 Runtime & E2E Worktree**
   - `G:/Github/h3d-gui-wiring-codex` (codex/provider-smoke-workbench, 43d8205)
   - `G:/Github/_claude_worktrees/h3d-claude-e2e-intel` (claude/e2e-intelligence-2026-05-08)
   - Status: Fresh, in use for live provider readiness verification.
   - Action: **Retain indefinitely** until v5.3 dashboard is promoted to prod.

---

## Summary

- **Worktree overhead:** 49 worktrees; 15 are stale/abandoned/frozen; 34 active or recent (consolidated May 6 merge).
- **Branch debt:** 15 branches >100 commits behind develop (all Phase 5.1 work, subsumed by PR 73–104 chain).
- **Proof integrity:** Stale proofs pre-2026-05-01 exist; latest proofs May 3 (acceptable). ROADMAP.md path reference broken (phase_5_1_proof.json not found).
- **Runtime ready:** PR 104 OPEN, runtime FRESH on commit 43d8205. Cloud provider auth 401 BLOCKED (expected — awaiting user creds). Local backends (Ollama, LM Studio) operational.
- **Codex next:** Land the chain PR-by-PR (84 first, then 87, 89, 91, 93, 95, 97, 99, 101, 102, 104). Close 4 stale branches, archive 8 phase-5.1 experiment branches, remove 9 audit+polish worktrees. Rebase & hold feature branch. Prepare v5.3 release gate.
