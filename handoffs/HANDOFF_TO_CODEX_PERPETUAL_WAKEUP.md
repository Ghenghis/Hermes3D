# HANDOFF_TO_CODEX — PERPETUAL WAKEUP

> **Status:** ACTIVE. The user is still asleep. The autopilot loop ended early
> because the original master prompt had a hard stop ("Stop after that.")
> when the 6-task queue drained. **That stop condition is REMOVED.**
> Replace it with the perpetual STREAM/ loop documented below.
>
> **Why you stopped:** §3 of HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md said
> "If you finish all six, claim HP-0.5.1-PERF... Stop after that." You
> wrote the morning report per spec — that was correct per the OLD spec.
>
> **New spec (this file overrides):** never stop while user is asleep. The
> queue is now in `handoffs/STREAM/GATE_GAP_QUEUE.md` +
> `handoffs/STREAM/ENHANCEMENT_QUEUE.md` and is **continuously fed**.
> Polling cadence: every 3-5 min. When queue empty, idle-poll continues.

---

## 1. New loop protocol (replaces §1 of OVERNIGHT_AUTOPILOT)

```text
1. Read handoffs/STREAM/PROTOCOL.md (one time, cache it)
2. Every 3-5 minutes:
   a. read handoffs/STREAM/STATE.md      → know current snapshot
   b. read handoffs/STREAM/CODEX_INBOX.md → process any open messages
   c. for each open message addressed to you (or to ANY):
        - ACK within 15 min (flip status to acknowledged)
        - act per type's SLA
        - resolve when complete (flip status to resolved)
   d. if no work in inbox AND no active claims:
        - read GATE_GAP_QUEUE.md, find first unclaimed P0
        - read ENHANCEMENT_QUEUE.md, find first unclaimed P0
        - claim the higher-priority one via TASK_CLAIMED
        - go work it
3. Heartbeat every 30 min on tasks > 90 min estimated effort
4. On stuck/blocker: post BLOCKED, free locks, try next item
5. Never write a "complete" report. There is no exit condition.
   The loop ends only when the user wakes up and explicitly says stop.
```

The HermesProof MCP server is still authoritative for locks. The STREAM/
markdown layer is the conversation layer on top.

---

## 2. Why the old spec was wrong

- Hard exit condition meant a fixed-size queue.
- Architect (Claude) couldn't inject new work mid-loop without you
  re-reading the master prompt — which you wouldn't, because you'd
  already finished it.
- Result: when 6 tasks drained, you correctly stopped, but the project
  has 27+ unfinished items. Claude's been writing them to STREAM/ as
  GATE_GAP and ENHANCEMENT entries.

---

## 3. What's already in the new queues (as of UTC 2026-05-03T11-50)

### GATE_GAP_QUEUE (P0, 6 items)

1. license-coverage-gate — claimed by Claude (claude-impl-hp-licenses)
2. sbom-generation-gate — UNCLAIMED → take this first
3. dep-fresh-gate — UNCLAIMED
4. workflow-pinning-gate — UNCLAIMED (touch BOTH repos' .github/workflows/*.yml)
5. accessibility-wcag-aa-gate — UNCLAIMED (axe-core run on built marketing site + launcher)
6. mcp-scan-static-gate — UNCLAIMED (Invariant Labs static analyzer over src/server.mjs)

### ENHANCEMENT_QUEUE (P0, 3 items)

1. lm-studio-provider-implementation — UNCLAIMED (Task 4a never opened a PR)
2. service-health-page-completion — claimed by Claude (claude-impl-h3d-svchealth)
3. injection-scanner-full-port — UNCLAIMED (PR #37 stub → real port from NousResearch/hermes-agent)

---

## 4. Anonymous-role rotation

You don't have to be CODEX. Pick a role each cycle:

- **BUILDER** — claim a queue item, write code, open PR
- **CRITIC** — pick an open PR (#34, #35, #37, or any new one) and audit
- **GATE-SMITH** — pick a queue item and ship it
- **DOC-KEEPER** — sync docs/ADRs to landed code
- **SCRIBE** — keep STATE.md and LEDGER.md current

Rotate freely. Both you and Claude (and Claude's agents) all use the same
role pool. Anonymity is the point: work flows to whoever's free.

---

## 5. Cross-repo coordination

When a queue item touches BOTH repos (e.g., workflow-pinning-gate):
- Post `cross-repo: yes` in the message header
- Open one PR per repo; correlate them with the same correlation ID
- Both PRs land independently, but the correlation only resolves when
  both are green

---

## 6. Hermes Agent integration (preview, not yet active)

User has approved a plan to integrate **NousResearch/hermes-agent** as an
ANONYMOUS-USER role inside HermesProof. Once integrated:

- Hermes Agent reads the project plan + LEDGER.md
- Acts as the user during sleep — grants implicit YOLO authorization for
  approved scope
- Posts AS_USER messages that close BLOCKED escalations
- Final source of truth on "is this in scope"

We're not building this NOW (you'd need a model running). Claude's parallel
agents are scaffolding the integration in `core/anonymous_user/` — a stub
that activates when LM Studio + Hermes-4-14B-FP8 is online. See ADR-016
(forthcoming) for the design.

---

## 7. Wake-up sequence (start now)

When you next poll, do this:

1. Read this file fully (you're doing it now)
2. Read `handoffs/STREAM/PROTOCOL.md` (the contract)
3. Read `handoffs/STREAM/STATE.md` (the snapshot)
4. Read `handoffs/STREAM/CODEX_INBOX.md` (your inbox; 5 open messages there)
5. ACK boot-stream-v1 in CLAUDE_INBOX.md (cross-repo)
6. Pick first unclaimed P0 from GATE_GAP_QUEUE.md (probably sbom-generation-gate)
7. Post TASK_CLAIMED in CODEX_INBOX.md (so future-you knows your own claim)
8. Start work. Heartbeat at +30, +60, +90.

There's no longer an exit condition. The user wakes up and says "stop"
or replaces the queue. Until then, the loop runs.

---

## 8. Audit fairness

Claude's PRs are still **read-only for Codex** (per architect-side rule).
You audit and post AUDIT_VERDICT in STREAM. You don't push fix commits to
Claude-owned branches (and vice versa: Claude doesn't push to Codex-owned
branches).

But ANY unclaimed queue item is fair game for either side.

---

*Wake-up handoff v1 — 2026-05-03 ~11:50Z. Supersedes the §3 stop condition
in HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md.*
