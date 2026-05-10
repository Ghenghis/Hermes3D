# Hermes Agent v0.13 Production + Multi-Version Pipelines — Action Plan (2026-05-09)

> **STATUS UPDATE 2026-05-10 (W5-8b doc-fix): EXECUTED 2026-05-09 → 2026-05-10.** Pipeline A landed via PR #160 (squash `3158a4e`, merged 2026-05-10T00:19:20Z). Pipeline C (v0.12 fallback) remains operational via `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`. Source-of-truth constant `DEFAULT_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-v013-canary")` is live in `services/agent_checkout.py:L31` (no longer a "future 1-line change"). The "**This plan is NOT executing**" line below is **superseded** — the plan ran end-to-end via PRs #155, #157, #159, #160, #165, #171, #172, #173, #174 between 2026-05-09T23:23Z and 2026-05-10T01:44Z. PR #169 is the only follow-on still in flight.

**Mission:** Promote v0.13 to production AND keep all Hermes Agent versions operational concurrently. 20-agent swarm across 3 pipelines.

**Inputs:**
- PR #155: canary env-switch resolver (per-call read of `HERMES_AGENT_CHECKOUT`)
- PR #156: HERMES_AGENT_ONLY_SWARM_STATUS (Wave A findings)
- PR #157: 7 PASS / 1 N/A / 0 FAIL canary smoke results
- BLK-013 bounded-task plan (Wave B10 / Master Continuation Wave)

**Goal state:**
- **Pipeline A (Stable)**: production default = v0.13.0 (`v2026.5.7`)
- **Pipeline B (Canary)**: opt-in candidate = v2026.5.8+ when tagged, OR latest green main HEAD
- **Pipeline C (Legacy)**: v0.12 (`v2026.4.30`) remains operational as opt-in fallback for any consumer who can't move
- All three pipelines selectable per-process (and ideally per-request) via `HERMES_AGENT_CHECKOUT` + `HERMES_AGENT_VERSION` envs
- No single version's failure can take down the others

---

## Architecture: 3-Pipeline Coexistence

```
                       Hermes3D OS
                            |
                            v
              +------ hermes_agent_checkout() ------+
              |                                     |
       env: HERMES_AGENT_CHECKOUT (path)       version registry
              |                                     |
       +------+------+----------+--------------+
       |             |          |              |
    v0.12        v0.13       v0.14+ /         (custom)
  PRODUCTION    CANARY        DEV
  hermes-agent- hermes-agent- hermes-agent-
  fresh         v013-canary   future
       |             |          |
   verified     promotable    forward-
   fallback     today         investment
```

**Concurrency rules:**
- Production process is bound to ONE version at boot (per current resolver semantics).
- **Per-request version routing** is a future enhancement (see Pipeline B Agent B5).
- Each version has its own checkout, venv, proof events. No file collision.
- Backups, MCP locks, recovery ledger all version-tagged.

---

## Hard gates (before promotion)

The 3 conditional gates from PR #157 §6 MUST clear:

1. **Live probes** — MiniMax + DeepSeek `POST /api/code-operator/providers/smoke` against canary venv return `accepted=true` with redacted evidence. (Operator-driven; one-time credit spend.)
2. **BLK-013 bounded-task ships** OR explicit operator approval to defer.
3. **Upstream `tui_gateway/entry.py:143-145` Windows guard** merges OR explicit operator approval to ship without the TUI/PTY surface.

If gate 1 fails: do NOT promote; document blocker. If 2 or 3 fail: promote with documented partial-functionality scope.

---

## 20-Agent Plan

### Pipeline P1 — Production v0.13 Promotion (8 agents)

| ID | Role | Mission | Stop condition |
|---|---|---|---|
| **P1-1** | Live MiniMax probe runner | Execute `POST /providers/smoke` for MiniMax against canary venv with `HERMES_AGENT_CHECKOUT` set; capture redacted-evidence shape | `accepted=true` + sha256-only auth_contract OR document blocker |
| **P1-2** | Live DeepSeek probe runner | Same for DeepSeek | same |
| **P1-3** | Upstream Windows-guard PR builder | File PR against NousResearch/hermes-agent: 1-line `if sys.platform != 'win32':` guard at `tui_gateway/entry.py:143-145` around `signal.SIGPIPE`/`SIGHUP` | PR opened upstream OR exact reason cannot file |
| **P1-4** | BLK-013 bounded-task implementer | Apply Wave B10's refined plan: ~300 LoC service + ~30 LoC route + ~120 LoC tests for `POST /cli-runners/run-bounded-task` | PR shipped + 6/6 tests pass OR explicit blocker |
| **P1-5** | Promotion PR builder | 1-line change in `services/agent_checkout.py:DEFAULT_AGENT_CHECKOUT` to canary path; ~5 LoC test updates | PR ready-to-merge waiting on user merge auth |
| **P1-6** | Rollback runbook builder | Operator runbook: how to flip back to v0.12 in <60s; includes `HERMES_AGENT_CHECKOUT=hermes-agent-fresh` mid-process flip + DB cleanup | runbook published OR exact gap |
| **P1-7** | Post-promotion smoke runner | Re-run all 8 smokes from PR #157 against the new default | 8 PASS OR exact regression |
| **P1-8** | Adversarial reviewer | Try to break promotion safety: race conditions, env-leak, stale-cache, double-spawn | reject any unproven path; require explicit fix-and-retry |

### Pipeline P2 — Multi-Version Coexistence (6 agents)

| ID | Role | Mission | Stop condition |
|---|---|---|---|
| **P2-1** | Version registry designer | Add `services/agent_version_registry.py`: declares known versions (v0.12, v0.13, future) with their checkout paths, venv paths, supported feature flags | doc + skeleton class shipped |
| **P2-2** | Per-request version routing planner | Design `HERMES_AGENT_VERSION` query param or header that the FastAPI route honors; default = process default. Includes auth + audit considerations | PR brief, NOT shipped (advisory until P1 promotion lands) |
| **P2-3** | v0.12 regression test pinner | Run `_repo_path()` + `_run_update_checks` + provider config + CLI runner detection ALL against v0.12 with `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`; pin behavior so the v0.13 promotion can't silently break v0.12 | regression suite added; CI pin |
| **P2-4** | v0.13 regression test pinner | Same against v0.13 canary | same |
| **P2-5** | Cross-version compat matrix | Document which Hermes3D features work on each version (Kanban, heartbeat, providers, MCP, redaction); flag any feature that ONLY works on v0.13 (e.g. redaction default-ON) | matrix doc + feature-flag wiring brief |
| **P2-6** | Version-tagged proof events | Each `_append_proof_event` call now records the active `hermes_agent_checkout()` and the upstream tag (e.g. `v2026.5.7`) so the proof ledger is version-traceable | service edit + tests |

### Pipeline P3 — v0.14+ / Main HEAD Forward Pipeline (6 agents)

| ID | Role | Mission | Stop condition |
|---|---|---|---|
| **P3-1** | Upstream tag/SHA watcher | Cron-style script that polls `gh api repos/NousResearch/hermes-agent/tags` weekly + last-5-green-main-runs heuristic from Wave A1; on hit, opens an issue and seeds canary candidate | script + GHA cron + first run executed |
| **P3-2** | Canary-flow harness | Reusable Python script that takes a SHA + path, clones, venvs, pip installs, runs the 8-smoke matrix from PR #157; produces redacted JSON evidence | harness + 8-smoke replay against current canary |
| **P3-3** | Multi-version GHA proof workflow | `.github/workflows/hermes-agent-versions.yml`: matrix runs against v0.12 + v0.13 + (when available) v0.14 on ubuntu-24.04 + Windows | workflow file landed + first run green for v0.12+v0.13 |
| **P3-4** | Recovery Controller version-aware smoke | Confirm RC v2 commits 1+2 (PR #149) work identically against both versions; freeze/snapshot/MCP-lock semantics unchanged | RC v2 freeze test runs against both checkouts |
| **P3-5** | Provider compat matrix per version | For each version, which providers are reachable + what redaction layer is active; pin in registry | matrix entry per version |
| **P3-6** | Final commander | Synthesize 19 prior agents' outputs; produce go/no-go for production v0.13 promotion + v0.14 readiness | one document with: 3-pipeline state, hard gates, next-PR queue |

---

## Sequencing (waves of 5-7, synthesize between)

### Wave 1 — Live probes + production-blockers (5 agents, parallel)
P1-1, P1-2, P1-3, P1-4, P1-5
- **Goal:** clear all 3 hard gates and prepare the promotion PR
- **Stop early if:** any gate fails → switch to "documented blocker" mode

### Wave 2 — Coexistence infrastructure (5 agents, parallel)
P2-1, P2-2, P2-3, P2-4, P2-5
- **Depends on:** Wave 1 promotion-PR landed (or explicit-defer agreement)
- **Goal:** ensure no single version's failure can take down others; pin both versions in CI

### Wave 3 — Promotion + safety net (5 agents, parallel)
P1-6, P1-7, P1-8, P2-6, P3-4
- **Depends on:** Wave 2 regression suite green for both versions
- **Goal:** flip the default + rollback runbook + adversarial-reject + version-tagged proofs + RC v2 confirmed working post-promotion

### Wave 4 — Forward pipeline (5 agents, parallel)
P3-1, P3-2, P3-3, P3-5, P3-6
- **Depends on:** Wave 3 promotion landed + 8-smoke green
- **Goal:** automate v0.14+ pickup; no human polling; final commander synthesizes the whole effort

---

## Required outputs per agent (persistence rule)

Per the prior swarm contract (no vague "blocked"):
- exact command
- exact failure or success snapshot
- exact file/function affected
- exact next-fix-attempt (even on success — what would invalidate it)
- evidence ID (MCP-chained)
- handoff explicit (yes/no + which agent next)
- 2-source research minimum (1 primary + 1 cross-comparison)
- no secret values in any artifact
- if 2 loops produce no new evidence: escalate

---

## Stop-conditions for the swarm

The swarm halts and reports when ANY of:
1. **Production v0.13 promoted + 8 smokes green + rollback runbook published** (success)
2. **One of the 3 hard gates fails AND user does not approve the fallback path** (documented partial-stop with exact upstream/operator next-step)
3. **>2 agents loop without new evidence** (per-agent escalation rule)
4. **Any safety regression in v0.12 fallback path** (immediate halt; v0.12 sanctity is non-negotiable)
5. **Secret leak detected in any artifact** (immediate halt; redact + retry)

---

## What is NOT in scope

- GUI/Playwright work (already gated by Agent 9; needs separate authorization)
- 60-app schema backfill (cross-repo Hermes3D, not codex)
- Printer safety drill (BLK-016, separate squad)
- Recovery Controller v2 commits 3-5 (still paused per user)
- Non-Hermes-Agent Bonus 12 follow-ups (BLK-021/024/etc.)

This plan is **strictly Hermes Agent versions + integration**.

---

## Provenance

Built on:
- HERMES-AGENT-ONLY 20-Agent Fix Swarm Wave A (5 agents, all returned)
- Master Continuation Wave (10 agents, all returned)
- Wave A4 + A5 combined PR #155
- Wave A1 corrected verdict (39/100 green main runs, not 0/100)
- Wave A3 re-run (330/375 modules pass on Windows)
- PR #157 canary smoke results (7 PASS / 1 N/A / 0 FAIL)

## Authorization required

This plan is **NOT executing**. Agent dispatch waits on user approval. On approval, swarm runs Wave 1 → synth → Wave 2 → synth → Wave 3 → synth → Wave 4 → final.

Estimated PR count: 6-10 across the 4 waves (live probes use existing endpoints, not PRs; promotion is 1 small PR; rollback runbook is 1 doc PR; coexistence + version-aware proofs are 2-3 PRs; forward pipeline is 1-2 workflow PRs + 1 doc PR).
