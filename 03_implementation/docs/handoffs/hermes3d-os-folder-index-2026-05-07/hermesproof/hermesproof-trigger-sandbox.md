# hermesproof-trigger-sandbox

**Component**: TRIGGER (most-developed of the six folders)
**Status**: ACTIVE-as-fixture / SANDBOX (single `init` commit, but rich captured runtime state)
**Branch**: `main`
**Last commit**: `c7de02c init` (2026-05-02)

## Purpose

`hermesproof-trigger-sandbox` is the only one of the six HermesProof folders that contains a real captured run of the orchestrator. It models the TRIGGER side of the HermesProof pipeline — the entry point where a contract (`contracts/CP-UX-A_*.md`) is filed, tasks are claimed, gates are run, evidence is emitted, locks are taken and released, and handoffs are approved. The captured artifacts (`tasks/`, `locks/` history, `gates/`, `evidence/`, `handoffs/`, `ledger.ndjson`) document the **canonical fixture** for what a complete HermesProof trigger run looks like.

It was driven by the `MCP Lock Orchestrator` (per `config.json`) against contracts owned by `claude-lead` (architect role) and `codex-impl-01` (implementation role) for a UX work-package called `CP-UX-A`. Two example task files (`CP-UX-A-ARCHITECT.json`, `CP-UX-A-CODEX.json`), three gate runs (`git-status`, `git-diff-check`), three handoffs, and a hash-chained evidence ledger are all preserved.

## Branch & last commit

- Branch: `main`
- Working tree: untracked `.hermes3d_orchestrator/` (the captured runtime state)
- Commit: `c7de02c init`

## Key files / artifacts

| Path                                                        | Role                                              |
|-------------------------------------------------------------|---------------------------------------------------|
| `contracts/CP-UX-A_SCOPE_LOCK.md`                           | Scope lock for the work-package                   |
| `contracts/CP-UX-A_CODEX_IMPLEMENTATION.md`                 | Codex implementation prompt                       |
| `03_implementation/ui/src/tabs/Agents.tsx`                  | File under lock (target of `CP-UX-A-CODEX`)       |
| `03_implementation/ui/src/tabs/Dashboard.tsx`               | File under lock (target of `CP-UX-A-CODEX`)       |
| `.hermes3d_orchestrator/config.json`                        | Orchestrator config (90-min TTL, sorted-path tx)  |
| `.hermes3d_orchestrator/tasks/*.json`                       | 2 captured tasks (architect + codex)              |
| `.hermes3d_orchestrator/gates/gate_*.json`                  | 6 captured gate runs                              |
| `.hermes3d_orchestrator/evidence/released_*.json`           | 12 lock-evidence packets w/ acquire->heartbeat->release history |
| `.hermes3d_orchestrator/evidence/ledger.ndjson`             | Hash-chained NDJSON ledger (prev_hash + entry_hash)|
| `.hermes3d_orchestrator/handoffs/handoff_*.json`            | 3 captured handoffs                               |
| `.hermes3d_orchestrator/events.ndjson`                      | 10 KB event-bus history                           |

## Truth-gate / proof-gate flow

The captured state demonstrates the full HermesProof trigger flow end-to-end:

1. **Task claim** — `hermes_claim_task` writes `tasks/<id>.json` with `status: "claimed"`, `claimed_utc`, `heartbeat_utc`.
2. **Lock acquire** — `hermes_lock_files` writes per-lock evidence with `acquired_utc`, `expires_utc = +90 min`, and an immutable `history[]` of `acquired` / `heartbeat` events.
3. **Gate execute** — `hermes_run_gate` runs an allowlisted command (e.g., `git status --short`), captures `exit_code`, `duration_ms`, `stdout_tail`, `stderr_tail`, and writes `gates/gate_<id>_<ms>.json`.
4. **Event emit** — every state change calls `hermes_emit_event`, appending an entry to `events.ndjson` and a hash-chained record to `evidence/ledger.ndjson` (with `prev_entry_id`, `prev_hash`, `entry_hash`).
5. **Handoff** — `hermes_request_handoff` + `hermes_approve_handoff` produce `handoffs/handoff_<id>.json` with requester/owner/decision_note.
6. **Release** — `hermes_release_files` + `hermes_release_task` append `released` history entries; the lock-evidence file becomes the durable proof.

The evidence ledger is the proof: each entry's `entry_hash` is computed from the row + `prev_hash`, so any tamper in history breaks the chain. This is what other HermesProof folders consume — the trigger-sandbox is the **producer of the canonical proof shape**.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300" font-family="system-ui,sans-serif" font-size="11">
  <rect width="500" height="300" fill="#fafafa"/>
  <text x="250" y="20" text-anchor="middle" font-size="14" font-weight="bold">hermesproof-trigger-sandbox (canonical fixture)</text>
  <rect x="15" y="50" width="100" height="40" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="65" y="68" text-anchor="middle">contract</text>
  <text x="65" y="82" text-anchor="middle" font-size="9">CP-UX-A_*.md</text>
  <rect x="135" y="50" width="100" height="40" fill="#fff2cc" stroke="#b58c2a"/>
  <text x="185" y="68" text-anchor="middle">claim_task</text>
  <text x="185" y="82" text-anchor="middle" font-size="9">tasks/*.json</text>
  <rect x="255" y="50" width="100" height="40" fill="#fff2cc" stroke="#b58c2a"/>
  <text x="305" y="68" text-anchor="middle">lock_files</text>
  <text x="305" y="82" text-anchor="middle" font-size="9">evidence/*.json</text>
  <rect x="375" y="50" width="100" height="40" fill="#fff2cc" stroke="#b58c2a"/>
  <text x="425" y="68" text-anchor="middle">run_gate</text>
  <text x="425" y="82" text-anchor="middle" font-size="9">gates/*.json</text>
  <line x1="115" y1="70" x2="135" y2="70" stroke="#333" marker-end="url(#a)"/>
  <line x1="235" y1="70" x2="255" y2="70" stroke="#333" marker-end="url(#a)"/>
  <line x1="355" y1="70" x2="375" y2="70" stroke="#333" marker-end="url(#a)"/>
  <rect x="15" y="130" width="100" height="40" fill="#ffe6e6" stroke="#a33"/>
  <text x="65" y="148" text-anchor="middle">emit_event</text>
  <text x="65" y="162" text-anchor="middle" font-size="9">events.ndjson</text>
  <rect x="135" y="130" width="220" height="40" fill="#e6ffe6" stroke="#2e8b57"/>
  <text x="245" y="148" text-anchor="middle" font-weight="bold">evidence/ledger.ndjson</text>
  <text x="245" y="162" text-anchor="middle" font-size="9">hash-chained: prev_hash -> entry_hash</text>
  <rect x="375" y="130" width="100" height="40" fill="#ffe6e6" stroke="#a33"/>
  <text x="425" y="148" text-anchor="middle">handoff</text>
  <text x="425" y="162" text-anchor="middle" font-size="9">handoffs/*.json</text>
  <line x1="425" y1="90" x2="425" y2="130" stroke="#333" marker-end="url(#a)"/>
  <line x1="65" y1="90" x2="65" y2="130" stroke="#333" marker-end="url(#a)"/>
  <line x1="115" y1="150" x2="135" y2="150" stroke="#333" marker-end="url(#a)"/>
  <line x1="355" y1="150" x2="375" y2="150" stroke="#333" marker-end="url(#a)"/>
  <rect x="135" y="210" width="220" height="40" fill="#e6f0ff" stroke="#3b6cb5"/>
  <text x="245" y="228" text-anchor="middle" font-weight="bold">release_files + release_task</text>
  <text x="245" y="244" text-anchor="middle" font-size="9">history[] appended; lock evidence durable</text>
  <line x1="245" y1="170" x2="245" y2="210" stroke="#333" marker-end="url(#a)"/>
  <text x="15" y="280" font-size="9">Captured: 2 tasks, 6 gate runs, 12 lock-evidence packets, 3 handoffs, 10KB events.</text>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#333"/></marker></defs>
</svg>
```
