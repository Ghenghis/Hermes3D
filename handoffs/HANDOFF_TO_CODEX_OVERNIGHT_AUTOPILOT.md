# HANDOFF_TO_CODEX — Overnight Autopilot Master Prompt

> **Status:** ACTIVE once user authorizes "go". The user is going to sleep. You have explicit authorization to run unattended for the rest of the night, picking up tasks from the HermesProof queue (or the handoffs/ folder fallback), shipping PRs, and looping until the queue is empty.
>
> **Auto-merge is NOT authorized.** Open PRs and leave them OPEN with green CI for morning review by the architect. The architect (Claude) merges in the morning.
>
> **Architect contact:** Claude reviews everything in the morning. Do NOT block on architect questions overnight — write a `HANDOFF_TO_CLAUDE_<TASKID>_BLOCKED.md`, release locks + task, and skip to the next task. Loop continues.

---

## 1. Loop protocol

Every iteration of the overnight loop:

```text
1. hermes_doctor                        → confirm ok=true
2. hermes_get_state                     → confirm 0 codex-impl-* locks held
3. Determine the next task and its owner string from §3 (each brief specifies its
   owner — they are NOT all `codex-impl-04`). For the first iteration use the
   highest-priority unclaimed brief in §3. Then:
     hermes_pick_task owner=<owner-from-brief> prefer_task_id=<task-id-from-brief>
   |
   | If queue empty for that owner: ls handoffs/HANDOFF_TO_CODEX_*.md, find the
   |  highest-priority unclaimed brief (priority order in §3 below), claim it via
   |  hermes_claim_task using the Task ID and owner listed in the brief.
   |
   | If no unclaimed briefs: STOP. Write the morning report (see §4) and stop.

4. Read the claimed brief end-to-end.
5. Verify lock list against actual files on develop (catch architect-side
   contradictions BEFORE editing — same discipline you've used on B1/B2).
   |
   | If contradiction: write HANDOFF_TO_CLAUDE_<TASKID>_BLOCKED.md with the
   |  exact ambiguity, release locks + task, append evidence kind=block,
   |  GO TO STEP 1 (try next task).

6. hermes_lock_files (matches brief)
7. Implement per brief
8. Run local validation: npm test (if applicable), pytest -q, ruff,
   git-status, git-diff-check, plus any brief-specific gates
9. git push -u origin <branch>; gh pr create
10. Wait up to 12 minutes for CI: poll `gh pr view <N> --json statusCheckRollup`
    every 60 seconds. Required gates that must go green: mechanical-review,
    Layer A, Layer B (all 4 cells), Layer C, Layer D, Layer D3, Layer F,
    Layer M, Layer T, Layer W. Layer E correctly SKIPPED on non-release branches.
11. **DO NOT MERGE.** Leave the PR open with green CI. The architect reviews
    and merges in the morning.
12. Close out HermesProof state: hermes_append_evidence (kind=checkpoint,
    summary=PR #N opened at SHA <commit>, all gates green, awaiting architect
    review), hermes_release_files, hermes_release_task.
13. GO TO STEP 1.
```

**Circuit breaker:** if you hit 3 consecutive blocked-handoffs OR 3 consecutive CI
failures that don't self-resolve, STOP and write `HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md`
(same filename as the normal-completion report — distinguished by content). Set the
report's "Halt reason" field to `circuit-breaker-3-strikes`. Don't keep churning.

**Verified-contradiction handling (§1 step 5):** a contradiction in a brief's
lock list vs. reality is a "blocked-handoff" and DOES count toward the 3-strike
circuit-breaker. This prevents getting stuck on consecutively-broken briefs.

**12-min CI timeout:** if `gh pr view <N> --json statusCheckRollup` doesn't show
all required gates as `SUCCESS` or `FAILURE` after 12 polls (12 minutes), treat
the iteration as a CI failure for circuit-breaker purposes. Update the PR body
with `[ci-timeout-pending-review]` and proceed to next task.

**Heartbeat:** if a task takes longer than 90 minutes, call `hermes_heartbeat`
to extend the lock TTL. Don't let locks expire mid-work.

**CI red but not blocker:** if CI fails on something you can fix (lint, test
flake, missing import), push a fix commit and re-poll. If CI fails on something
you cannot fix in <2 attempts, treat as blocked and skip.

---

## 2. Boundaries — what you CAN and CANNOT do unattended

### ✅ CAN do without user input

- Pick + claim + lock + implement + open PR per §1
- **Open PRs and leave them open** for morning architect review
- Self-correct: revert your own commits, fix linting, retry pre-push hooks,
  rebase your own feature branch on top of fresh `develop` if there's been
  a merge while you were working
- Spawn online research agents for narrowly-scoped questions (e.g., "what's
  the gitleaks 2026 custom-pattern syntax for Anthropic API keys")
- Add advisory CI jobs (continue-on-error) that don't gate merges
- Update your own PR body / commit messages on PRs you own

### 🚫 CANNOT do — these require user awake

- **Auto-merge any PR**, including your own. Architect merges in the morning.
- **Cut `release/v5.3.0` or any `release/*` branch**
- **Push, merge, or modify `main` in any way** (branch protection blocks anyway)
- **Tag any `v*` version** or run `gh release create`
- **Connect to the user's VPS / SSH / Tailscale tailnet**
- **Run actual deployment commands** (`docker compose up`, `caddy reload`, etc. on real infra)
- **Read or write any of these paths:**
  - `G:\private\` (anything)
  - `C:\Users\Admin\Downloads\VPS\` (anything)
  - Any `.env*` file in any repo working tree (only `.env.example` /
    `.env.vps.example` templates)
  - Any file containing API key values
- **Modify branch protection rules, GH secrets, repo settings**
- **Force-push to any branch you don't own** (your own feature branches OK
  with `--force-with-lease`)
- **Hard-reset shared branches** (develop, main, release/*)
- **Delete any branch on origin**
- **Modify CI workflows that gate merges** (Layer A/B/C/D/D3/F/M/T/W) — adding
  new advisory layers OK; modifying required layers is NOT
- **Open PRs that include any file under `04_testing/playwright/`'s recorded
  baselines** without a clear test-update justification

### ⚠️ ASK YOURSELF before any non-listed action

"Would the user want to be woken up to approve this?" If yes, write the blocked
handoff and skip. If no, proceed. **Default is conservative — when in doubt, skip.**

---

## 3. Tonight's queue (priority order)

**Task 1 — H3D-SOTA-MARKETING-V2 (B5)** ⭐ TOP PRIORITY
- Brief: `handoffs/HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md` (already on develop)
- Marketing site + README v2 with R3F hero + gcode-preview + VHS demo
- User explicitly excited about your design instincts on this — give it your best
- Owner string: `codex-impl-04`
- Lock list and full spec in the existing brief

**Task 2 — H3D-BLENDER-AUDIT** (research only — smallest scope, lowest risk)
- Brief: `handoffs/HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md` (this PR)
- Audit `https://github.com/rakaarwaky/blender-mcp-native` — output is an ADR,
  no code changes
- Owner string: `codex-impl-05`

**Task 3 — CP-HERMESPROOF-0.6** (gate pack — foundational)
- Brief: `handoffs/HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md` (this PR)
- gitleaks + auto_linter + agentic-testing + HERMES3D_ENV_FILE +
  hardened .gitignore
- This goes in the **HermesProof repo** (`G:\Github\hermes3d-mcp-lock-orchestrator`),
  NOT Hermes3D. Different working tree.
- Owner string: `codex-impl-hp` (HermesProof-specific owner to avoid collision
  with `codex-impl-05` used in Hermes3D Task 2; the HermesProof state is a
  separate workspace, but explicit prefix prevents confusion in cross-repo logs)

**Task 4a — CP-HERMES3D-LOCAL-LM-STUDIO** (split from former mega-task)
- Brief: `handoffs/HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md` (this PR)
- LM Studio default provider, Ollama fallback (modify existing `ollama_client.py`),
  Hipfire optional. NO UI changes, NO Mnemosyne, NO port monitor.
- Owner string: `codex-impl-06`

**Task 4b — CP-HERMES3D-MNEMOSYNE-RECALL** (split from former mega-task)
- Brief: `handoffs/HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md` (this PR)
- `mnemosyne-memory` (correct PyPI name) integration as recall layer
- Owner string: `codex-impl-07`

**Task 4c — CP-HERMES3D-SERVICE-HEALTH** (split from former mega-task)
- Brief: `handoffs/HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md` (this PR)
- In-house port probe + new top-level `/health` React route + `/api/health/services`
  FastAPI endpoint. NO Settings tab assumption (the audit confirmed it doesn't exist).
- Owner string: `codex-impl-08`

**Order matters:** B5 first (most user-visible), then BLENDER-AUDIT (smallest, validates
the loop works), then HermesProof v0.6 (foundational), then 4a → 4b → 4c (split from
the former mega-task; each independently completable so a Mnemosyne package quirk
doesn't block LM Studio or Service Health).

If you finish all six, claim a v0.5.1 perf-companion PR for HermesProof addressing
Gemini's 4 deferred items (init-once guard, O(1) heartbeat-by-id, parallel readTasks,
per-task error handling in recoverStaleTasks). Owner: `codex-impl-hp-perf`. Stop after that.

---

## 4. The morning report

When the loop finally stops (queue empty OR circuit breaker tripped), write:

`handoffs/HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md`

Containing:

- **Summary table:** task id, status (PR opened / blocked / skipped), PR #, commit SHA, test counts
- **What's open for review:** list of PRs awaiting architect merge, with one-line descriptions
- **What blocked:** list of each blocked-handoff with link to the file and a one-line reason
- **What was skipped:** any task that was claimed but couldn't proceed for a non-blocker reason
- **Surprises / observations:** anything unusual you noticed (test infra issues, develop drift,
  unexpected file states, agent research results worth flagging, etc.)
- **Recommended next steps:** what the architect should look at first when they wake up

Then commit + push to `docs/overnight-results-<utc>` branch and open a PR for visibility.
DO NOT auto-merge this morning report PR — it's the hand-back to the architect.

---

## 5. Hard rules summary (one-liner version)

1. Pick → lock → implement → PR → leave OPEN with green CI → release locks + task → loop
2. Skip on blocker, never block on the architect overnight
3. No auto-merge, no release cut, no main push, no tags, no VPS, no secrets
4. Heartbeat long tasks; circuit-breaker after 3 consecutive failures
5. Write the morning report when done; that PR does NOT auto-merge either

The discipline you've shown across CP5.1-A through B4 has earned this trust. Sleep is the user's; the work is yours.
