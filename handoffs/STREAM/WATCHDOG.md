# STREAM/WATCHDOG.md — Foolproof self-healing layer

> **Goal:** zero-touch overnight operation. If an agent goes idle, gets
> stuck, crashes, or its message reaches SLA timeout, another agent (or
> the watchdog itself) auto-corrects the state. The user wakes up to a
> functioning queue, not a deadlock.

---

## 1. The four watchdog jobs

| Job | Cadence | Runs in | What it does |
|---|---|---|---|
| **W1 — heartbeat-check** | every 1 min | local node script + GH Action cron | Flags any role that hasn't written to STATE.md in >15 min as `IDLE`. Flags any `in_progress` message past expiry as `STUCK`. |
| **W2 — auto-reassign** | triggered by W1 | local node script | When STUCK or IDLE detected on `in_progress` work, posts a `REASSIGN_REQUEST` to all inboxes. ANY role may claim. |
| **W3 — backup-snapshot** | every 30 min | local node script + GH Action cron | Copies all STREAM/*.md into `STREAM/backups/<UTC-iso>/` and prunes >7-day-old snapshots. |
| **W4 — schema-validate** | every commit + 5 min | pre-commit hook + cron | Validates every message in CLAUDE_INBOX/CODEX_INBOX/LEDGER against the schema. Auto-fixes recoverable errors (status enum, header order) by writing back. |

All four are **idempotent** — running them twice produces the same state.
That's how we recover from agent crashes mid-write.

---

## 2. Stuck/idle detection rules

A role is **IDLE** if:
- No STATE.md write attributed to that role in the last 15 minutes
- AND there are open `in_progress` messages addressed to that role
- AND the last heartbeat is missing or older than expected for the message age

A correlation is **STUCK** if:
- Has >3 messages all `open` or `acknowledged` (none `resolved`)
- AND last message in correlation aged >20 min with no follow-up
- OR a message's `expires:` field has passed and `status` is not `resolved`/`expired`

A whole loop is **WEDGED** if:
- Both inboxes have >5 open messages each
- AND no LEDGER.md append in the last 60 min
- AND no PR push events in the last 60 min

WEDGED triggers a **circuit-breaker BLOCKED** that wakes the user (escalates
out of overnight loop).

---

## 3. Auto-correction protocol

When W1 flags STUCK on a correlation:

```text
1. W2 reads the stuck correlation's full thread
2. W2 posts to BOTH inboxes:

   ## msg-<UTC>-<seq> — REASSIGN_REQUEST — <correlation-id>
   - from: WATCHDOG
   - to: ANY
   - status: open

   Correlation `<id>` is STUCK (last activity <UTC>, owner <role>).
   Original work item: <copied subject + body>
   Reassigning to ANY available role. First TASK_CLAIMED wins.

3. W2 marks the original `in_progress` message `status: stuck-reassigned`
4. The next polling agent that's idle picks it up + posts TASK_CLAIMED
5. If 30 min pass with no claim, W2 escalates to BLOCKED (user-facing)
```

When W1 flags IDLE on a role:
- W2 doesn't reassign automatically (the role might be on a long task without heartbeat).
- W2 instead posts a HEARTBEAT_PROBE to the role's inbox; if no response in 10 min, then STUCK rules apply.

---

## 4. Backup snapshots

Every 30 min, `scripts/stream-backup.mjs` copies all `STREAM/*.md` to
`STREAM/backups/<UTC-iso>/`. Retention: 7 days (336 snapshots max). Older
snapshots auto-prune.

Backup path is in `.gitignore` (snapshots are local; STATE/INBOX/LEDGER
already in git provide the durable history).

Recovery: `node scripts/stream-restore.mjs <UTC-iso>` rolls all STREAM/
files back to that snapshot. Useful if a botched message corrupts state.

---

## 5. Multi-client support

The protocol is **client-agnostic** — any agent that can read/write markdown
files in the repo can participate. Currently supported clients with
adapters:

| Client | Adapter | Hook surface |
|---|---|---|
| **Claude Code (CLI)** | `examples/claude_code/streamhooks/` | SessionStart hook reads PROTOCOL.md, PreToolUse hook checks STATE.md, SubagentStop hook posts STATE_UPDATE |
| **Codex CLI** | `examples/codex/streamhooks/` | Codex picks task → posts TASK_CLAIMED, every 3-5 min polls inbox |
| **KiloCode** | `examples/kilocode/streamhooks/` | rules.toml + system-prompt snippet |
| **Cursor** | `examples/cursor/streamhooks/` | `.cursor/rules/stream.mdc` + `.cursor/mcp.json` (HermesProof MCP) |
| **Windsurf** | `examples/windsurf/streamhooks/` | `.windsurfrules` + `mcp_config.json` |
| **VSCode + Copilot** | `examples/vscode/streamhooks/` | `.vscode/mcp.json` + `.github/copilot-instructions.md` snippet |
| **GH Action runner** | `.github/workflows/stream-watchdog.yml` | Cron-triggered watchdog (last-resort if all interactive clients offline) |

Adapter format documented in `CLIENT_ADAPTERS.md`. Each adapter is a
2-3 file drop-in: rules + example messages + (where supported) tool config.

---

## 6. Heartbeat semantics

A heartbeat is a one-line message with type `HEARTBEAT`:

```markdown
## msg-<UTC>-<seq> — HEARTBEAT — <correlation>
- from: <role>
- to: ANY
- correlation: <id>
- status: open
- expires: <UTC>+30min

Still on <correlation>. No blockers. ETA <UTC>.
```

Heartbeats:
- Required every 30 min on tasks `>90 min` estimated effort
- Auto-archived to LEDGER.md after the correlation resolves (don't clog inbox)
- Watchdog uses heartbeat presence as proof-of-life

If a heartbeat is missing past 30 min on an open long task → STUCK detection fires.

---

## 7. Conflict-on-claim resolution

Two clients can race a TASK_CLAIMED. Resolution:

1. Both messages land with timestamps T1, T2.
2. The one with the *earlier UTC timestamp* wins.
3. If T1 == T2 (sub-millisecond tie), tiebreak by lexicographic role-instance-id.
4. The losing claim's author posts a follow-up `TASK_RELEASED` and picks the
   next item from the queue.

Race window is bounded by polling cadence (3-5 min), so two-way collisions
are rare. Three-way is theoretical — the same tiebreak rule cascades.

---

## 8. Recovery from MCP disconnect

If `hermes3d-locks` MCP drops mid-cycle:

- File-based STREAM/ keeps working for read-only status only.
- `STATE.md` flag set: `mcp_status: disconnected` with timestamp.
- Watchdog may run read-only `gh`, `git`, and route probes to report state.
- No source writes, lock-file writes, staging, commits, pushes, merges,
  installs, updates, release actions, provider write tasks, or printer actions
  are allowed while MCP is disconnected or scoped to the wrong workspace.
- When MCP reconnects, `STATE.md` is updated from `hermes_get_state`; any
  task that would have required a write must reacquire same-owner MCP task and
  file locks before continuing.

MCP disconnect does not need to abort the whole conversation, but it does abort
write authority. STREAM inbox messages are proof-of-life only; they are never a
replacement for Hermes locks or evidence.

---

## 9. Retention + privacy

- LEDGER.md is forever (audit trail for the user)
- INBOXes auto-trim to last 30 days (older → LEDGER.md)
- backups/ rotate every 7 days
- No secrets ever — gitleaks scans STREAM/, blocks any commit with a
  matched pattern. The `.gitleaks.toml` allowlist explicitly excludes
  `STREAM/backups/**` from the allowlist (snapshots get scanned too).

---

## 10. Manual override

User can always:
- Post directly to either inbox (becomes the "USER" role, highest precedence)
- Delete a message (allowed only via `git revert` + LEDGER entry explaining why)
- Force a watchdog cycle: `node scripts/stream-watchdog.mjs --force`
- Pause the loop: `touch STREAM/.PAUSED` (watchdog respects this; resumes when removed)

---

## 11. Canonical scripts

All scripts live in HermesProof's `scripts/`:

- `stream-validate.mjs` — schema check, runs in pre-commit + CI
- `stream-watchdog.mjs` — runs W1+W2 (heartbeat + auto-reassign)
- `stream-backup.mjs` — runs W3 (snapshots)
- `stream-archive.mjs` — moves resolved/expired messages to LEDGER.md
- `stream-state-snapshot.mjs` — refreshes STATE.md from real PR/lock state
- `stream-restore.mjs` — rolls back to a backup snapshot
- `sync-stream-protocol.mjs` — keeps Hermes3D and HermesProof PROTOCOL.md in sync

All scripts are zero-deps (Node stdlib only) so they run on any client
machine without `npm install`.

---

*Watchdog spec v1 — 2026-05-03. The four jobs (heartbeat, reassign, backup, validate)
plus client adapters are what makes the system foolproof.*
