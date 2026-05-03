# STREAM/ — Real-Time Anonymous Handoff Protocol

> **Purpose:** A markdown-based pub/sub between Claude (architect+builder) and
> Codex (builder+critic) so neither side ever idles while the user sleeps.
> Both sides poll this directory every 3-5 minutes; messages are anonymous
> (role-based, not identity-based) and timestamped in UTC.
>
> **Authoritative state machine:** the `.hermes3d_orchestrator/` JSON files
> still own ground truth (locks, task queue, evidence ledger). STREAM/ is the
> *conversation layer* on top of that — it's the chat we'd be having if we
> were both in a room. Decisions still get evidenced in the ledger.

---

## 1. Roles (anonymous, rotatable)

Either agent can take either role at any time. Roles are **action stances**, not identities:

- **BUILDER** — claims tasks, writes code, opens PRs, fixes lint/CI breaks
- **CRITIC** — audits PRs, verifies claims, runs gates, posts verdicts
- **SCRIBE** — keeps STATE.md current, archives old INBOX entries to LEDGER.md
- **GATE-SMITH** — proposes new gates, audits coverage, lands gate PRs
- **DOC-KEEPER** — keeps docs, ADRs, READMEs in sync with code

The point of role anonymity: if Claude is buried in a 6-tool refactor and Codex
is idle, Codex can claim BUILDER and keep moving. The HermesProof lock manager
prevents file-level collisions; STREAM/ prevents semantic collisions.

---

## 2. Directory layout

```
handoffs/STREAM/
  PROTOCOL.md              ← this file (read-only contract)
  STATE.md                 ← live snapshot, both sides update
  CLAUDE_INBOX.md          ← messages FOR Claude (Codex writes, Claude reads/clears)
  CODEX_INBOX.md           ← messages FOR Codex (Claude writes, Codex reads/clears)
  LEDGER.md                ← append-only archive of resolved messages (audit trail)
  GATE_GAP_QUEUE.md        ← prioritized list of missing gates being worked
  ENHANCEMENT_QUEUE.md     ← non-gate enhancements (perf, refactor, docs)
```

Each repo has its own `STREAM/` (Hermes3D and HermesProof are separate
workspaces). Cross-repo coordination uses **mirror messages**: post in BOTH
inboxes with the same correlation ID.

---

## 3. Message format

Every message is a markdown H2 block with a YAML-front-matter header:

```markdown
## msg-2026-05-03T11-23-45Z-001 — FIX_PUSHED — pr/34
- from: BUILDER
- to: CRITIC
- correlation: m34-fix-loop
- expires: 2026-05-03T13:23Z   (optional; default = +4h)
- status: open                  (open | acknowledged | resolved | expired)

Pushed `# noqa: F401` to PR #34 to fix the F401 import lint.
CI rerun queued. Need a Tier-A audit only (lint + matrix M
should both go green together).
```

**Header rules**
- ID format: `msg-<UTC-iso8601-with-dashes>-<3-digit-seq>` (monotonic per author per day)
- `from`/`to`: ROLE strings, never identity (BUILDER, CRITIC, SCRIBE, etc.)
- `correlation`: free-form string, used to thread related messages
- `expires`: ISO-8601 UTC; if absent, +4h. Past expiry → SCRIBE archives to LEDGER.md as `expired`
- `status`: open → acknowledged (other side saw it) → resolved (action complete) → expired (no action)

**Body rules**
- Plaintext prose, not JSON
- Reference PR/issue numbers explicitly (`PR #34`, `issue #12`)
- Reference files with full path from repo root (`03_implementation/src/.../foo.py`)
- Quote error output verbatim (in fenced blocks); never paraphrase a CI failure

---

## 4. Message types (all CAPS, in subject after type)

| Type | Use when | Required-action time |
|---|---|---|
| **CORRECTION_REQUEST** | Found bug in other side's PR | Acknowledge ≤15min, fix ≤2h |
| **FIX_PUSHED** | Pushed a fix in response to CORRECTION | Re-audit ≤30min |
| **AUDIT_VERDICT** | Finished audit on a PR | Posted with PASS / NEEDS-FIX / BLOCK |
| **ENHANCEMENT_PROPOSAL** | Suggesting an improvement | No SLA — can defer |
| **GATE_GAP_FOUND** | Found an uncovered failure mode | Add to GATE_GAP_QUEUE.md within 1h |
| **GATE_LANDED** | Shipped a new gate (PR opened or merged) | Acknowledge ≤30min |
| **TASK_CLAIMED** | About to start work on a queue item | Other side avoids same scope |
| **TASK_RELEASED** | Done or blocked, releasing for pickup | Other side may claim |
| **STATE_UPDATE** | Updated STATE.md, FYI | Optional ack |
| **HEARTBEAT** | "Still alive on long task" | Optional |
| **LGTM** | Approved a PR | Other side may merge after green CI |
| **BLOCKED** | Cannot proceed — need architect (user) | Falls through to user only |
| **QUESTION** | Need clarification | Other side answers ≤2h |
| **ANSWER** | Replying to QUESTION | Closes the QUESTION |

`BLOCKED` is the only type that escalates outside the loop — it goes to the
user-visible morning report. Everything else stays in the loop and resolves.

---

## 5. Polling cadence

- **Active-work cadence:** every 3 minutes
- **Idle cadence:** every 5 minutes
- **Sleep cadence:** never. If you're "out of work", you check the queues and
  pick something. STREAM/ never sleeps while the user does.

When you check, you do this:

```text
1. read STATE.md           → know the current snapshot
2. read CLAUDE_INBOX.md (if you're Claude) or CODEX_INBOX.md (if you're Codex)
3. for each `status: open` message addressed to your current role:
     a. acknowledge  (flip status to `acknowledged`, write a one-line ACK reply)
     b. act          (do the requested thing OR post BLOCKED with reason)
     c. resolve      (flip status to `resolved`, post outcome reply)
4. archive any `resolved` or `expired` messages older than 6h to LEDGER.md
5. check GATE_GAP_QUEUE.md — if anything's unclaimed and you're idle, claim it
6. update STATE.md if you changed anything material
```

You never wait silently. If you're processing, post a HEARTBEAT every 30 min
on long tasks.

---

## 6. Handoff "chat" example

```markdown
## msg-2026-05-03T11-15-00Z-001 — CORRECTION_REQUEST — pr/34
- from: CRITIC
- to: BUILDER
- correlation: m34-fix-loop
- status: open

PR #34 Layer A still RED. Ruff says I001 unsorted imports at
`03_implementation/src/hermes3d/core/agents/orchestrator.py:33`.
The `# noqa: F401` you added is fine, but the import block needs
re-sorting (move the MnemosyneRecall import up alphabetically OR
let `ruff check --fix --select I001` do it).

Layer M is downstream cascade — fix Layer A and M will go green automatically.

## msg-2026-05-03T11-19-22Z-002 — ACK — pr/34
- from: BUILDER
- to: CRITIC
- correlation: m34-fix-loop
- status: acknowledged

ACK. Running `ruff check --fix` locally now, will push fix commit.

## msg-2026-05-03T11-26-08Z-003 — FIX_PUSHED — pr/34
- from: BUILDER
- to: CRITIC
- correlation: m34-fix-loop
- status: open

Pushed `9a4b1c2`. `ruff check` now clean locally. CI rerun queued at
https://github.com/Ghenghis/Hermes3D/actions/runs/<id>.
Re-audit when Layer A + M both green.

## msg-2026-05-03T11-44-50Z-004 — AUDIT_VERDICT — pr/34
- from: CRITIC
- to: BUILDER
- correlation: m34-fix-loop
- status: resolved

PASS. All 13 required gates green. CodeRabbit clean. PR ready for architect merge.
Closing m34-fix-loop.
```

That whole exchange happens in ~30 minutes without either side waiting on the user.

---

## 7. Conflict resolution

Two builders can't lock the same files (HermesProof prevents it). But two
agents could still try to **claim the same logical task**. Resolution:

1. First TASK_CLAIMED message wins (timestamp tiebreak, lexicographic on author ID otherwise).
2. The loser of the race posts ACK + drops the claim, picks next item from GATE_GAP_QUEUE.md or ENHANCEMENT_QUEUE.md.
3. Worktree isolation (`isolation: "worktree"` for Agent calls) prevents concurrent file edits even within a single agent's spawned subagents.

If both sides post AUDIT_VERDICT with conflicting verdicts (one PASS, one NEEDS-FIX), the **NEEDS-FIX wins**. Belt-and-suspenders: better to over-audit than under.

---

## 8. Anti-loops

If you see >3 messages on the same `correlation` ID with no progress
(no FIX_PUSHED, no resolution), post **BLOCKED** with reason. Stops infinite
ping-pong before user wakes up to a 200-message inbox.

If a message goes >2h without being acknowledged, the SCRIBE escalates it
(re-posts in the morning report under "stalled handoffs").

---

## 9. Gate gap queue protocol

Gate gaps live in `GATE_GAP_QUEUE.md`. Each entry:

```markdown
## gap-2026-05-03-001 — license-coverage-gate
- domain: supply-chain | perf | a11y | 3d-print-stability | docs | testing | security
- status: unclaimed | claimed:<role-instance-id> | in-pr:<pr#> | merged
- priority: P0 | P1 | P2
- evidence: <link to incident, audit doc, or "research only">
- estimated-effort: S | M | L
- dependencies: <other gap IDs or PRs>

Description in 2-3 sentences.
```

Builders pick from `unclaimed` P0 first, then P1, then P2. Once a gap is in PR,
it gets normal AUDIT_VERDICT treatment.

---

## 10. State file convention (STATE.md)

Both sides keep STATE.md current. It has these top sections:

1. **Last update:** UTC timestamp + role
2. **Active correlations:** open/acknowledged messages summary
3. **Open PRs (this repo):** number, branch, gate status, awaiting-action
4. **Open PRs (cross-repo):** mirror entries
5. **Locks held:** `hermes_get_state` snapshot
6. **Queue depth:** GATE_GAP_QUEUE unclaimed count, ENHANCEMENT_QUEUE unclaimed count
7. **Health:** doctor status, last evidence-ledger row, any circuit-breaker counters

Update STATE.md anytime you change material state. Don't wait — stale STATE.md
is worse than no STATE.md.

---

## 11. Cross-repo mirrors

When a message touches both repos (e.g., a HermesProof gate change that
Hermes3D depends on), post in BOTH inboxes with the same correlation ID and
note `cross-repo: yes` in the header. The receiving side acks in BOTH
inboxes too.

The two `STREAM/` directories are kept in sync this way. Don't try to share
the directory across repos (lock manager doesn't span repos).

---

## 12. Hard rules

1. **Never** auto-merge a PR based on a STREAM message. PRs need green CI + LGTM, then a human (or the explicit YOLO authorization the user gave for tonight).
2. **Never** post secrets in any STREAM/ file. The hardened gitleaks pack scans STREAM/ too.
3. **Never** post fictional state — STATE.md must reflect real PR/CI/queue state, verified by `gh` + `hermes_get_state`.
4. **Never** ignore a CORRECTION_REQUEST silently. ACK or BLOCK within 15min.
5. **Always** archive resolved messages to LEDGER.md within 6h (keeps the inbox readable for the next polling cycle).

---

## 13. Tonight's bootstrap

The user is asleep. The autopilot is running. STREAM/ starts populated with:

- An initial GATE_GAP_QUEUE.md with the gates Claude has identified as missing
- An initial ENHANCEMENT_QUEUE.md with unfinished work (LM Studio, v0.5.1 perf, ServiceHealth integration, injection scanner full port)
- A first STATE.md snapshot
- An opening CODEX_INBOX.md message announcing the protocol and the first 3 work items

Codex's first cycle reads PROTOCOL.md (this file), reads CODEX_INBOX.md,
acks, picks one of the queued items, and starts. Claude's parallel agents
work the rest. Both check inboxes every 3-5 min.

By morning the LEDGER.md will be the proof of cooperation, GATE_GAP_QUEUE.md
will be drained or downgraded, and the user will see what got done.

---

*Protocol v1 — 2026-05-03. Both sides may propose amendments via ENHANCEMENT_PROPOSAL → must reach LGTM from both before changing this file.*
