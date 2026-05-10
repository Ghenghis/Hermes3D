# hermes3d-mcp-test-sandbox

## Purpose

A minimal **disposable test workspace** that mimics a Hermes3D project layout, used to exercise the `hermes3d-mcp-lock-orchestrator` (a.k.a. `hermes3d-locks`) end-to-end without touching a real product repo. It contains the directory shape the orchestrator's `hermes_doctor` and queue/event managers expect (`tasks/`, `events.ndjson`, `locks/`, `evidence/`, `gates/`, `handoffs/`) plus a contracts layout (`03_implementation/`, `contracts/`) consistent with the larger Hermes3D-OS multi-lane handoff convention.

In the Hermes Agent / MCP infrastructure category, this folder is the **destination** of orchestrated work — the workspace MCP clients lock into via `MCP_LOCK_WORKSPACE` or `HERMES3D_WORKSPACE` env vars when the lock orchestrator is being smoke-tested. Its `.hermes3d_orchestrator/` state is live (already initialized).

## Status

- Git HEAD: `0219405` sandbox: initial layout
- Single-commit repo (intentionally minimal); state directory `.hermes3d_orchestrator/` is populated from prior smoke runs
- Lifecycle: **SANDBOX** (test fixture; safe to wipe `.hermes3d_orchestrator/` between runs)

## MCP surface

This folder does **not** expose its own MCP tools — it is the workspace target. The tools acting on it come from `hermes3d-mcp-lock-orchestrator`:

- All `hermes_lock_files` / `hermes_release_files` calls write under `.hermes3d_orchestrator/locks/`
- `hermes_emit_event` / `hermes_list_events` write `events.ndjson` and `events/outbox`, `events/handled`, `events/failed` here
- `hermes_enqueue_task` / `hermes_pick_task` write under `tasks/{pending,claimed,blocked,done}/`
- `hermes_append_evidence` writes `evidence/` NDJSON
- `hermes_run_gate` reads `gates/` allowlist
- `hermes_doctor` / `hermes_get_state` audit the directory structure

## Tech stack

- No code — pure filesystem layout
- Designed to exercise the orchestrator's:
  - workspace-init (directories present)
  - queue manager round-trips (enqueue → pick → done)
  - event outbox / handled / failed flow
  - lock + handoff integration
  - evidence-ledger append + verify

## Key files

| Path | Description |
| --- | --- |
| `README.md` | Single-line "Hermes3D-like sandbox" descriptor |
| `.gitignore` | Excludes orchestrator state from git |
| `.hermes3d_orchestrator/config.json` | Live orchestrator config (post-run state) |
| `.hermes3d_orchestrator/events.ndjson` | Live event stream |
| `.hermes3d_orchestrator/locks/` | Atomic mkdir EEXIST lock directories |
| `.hermes3d_orchestrator/tasks/` | Pending/claimed/blocked/done queue dirs |
| `.hermes3d_orchestrator/evidence/` | Append-only NDJSON evidence ledger |
| `.hermes3d_orchestrator/gates/` | Allowlisted gate definitions |
| `.hermes3d_orchestrator/handoffs/` | Pending/approved handoff records |
| `03_implementation/ui/src/tabs/` | Stub Hermes3D-OS-style implementation tree |
| `contracts/CP-UX-A_*.md` | Sample lane contract files (CP-UX-A scope-lock + Codex impl) |

## Relationships

- **Test target of** `hermes3d-mcp-lock-orchestrator` — used by the orchestrator's smoke tests and as a manual `MCP_LOCK_WORKSPACE` for stdio probes.
- **Mirrors** the directory shape used by core repos `Hermes3D` and `Hermes3D-OS` (specifically the `03_implementation/` + `contracts/` lane convention from the 4-agent split plan).
- **Independent of** the Python Hermes Agent stack (`hermes-agent-fresh`, `atomic-hermes`); the sandbox only cares about Node-side coordination state.
- **Companion to** `hp-hermes-agent-bridge` for testing the v0.6 anonymous-orchestrator + agent-bridge paths before promotion to v0.7.

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0f172a"/>
  <text x="250" y="22" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="bold">hermes3d-mcp-test-sandbox — disposable workspace</text>

  <!-- orchestrator on top -->
  <rect x="120" y="40" width="260" height="42" rx="8" fill="#1e293b" stroke="#a855f7" stroke-width="2"/>
  <text x="250" y="60" text-anchor="middle" fill="#a855f7" font-size="11" font-family="sans-serif" font-weight="bold">hermes3d-mcp-lock-orchestrator</text>
  <text x="250" y="74" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">MCP_LOCK_WORKSPACE → this folder</text>

  <line x1="250" y1="82" x2="250" y2="105" stroke="#a855f7" stroke-width="1.5"/>
  <polygon points="245,100 250,110 255,100" fill="#a855f7"/>

  <!-- workspace box -->
  <rect x="40" y="115" width="420" height="170" rx="10" fill="#1e293b" stroke="#22c55e" stroke-width="2"/>
  <text x="250" y="135" text-anchor="middle" fill="#22c55e" font-size="12" font-family="sans-serif" font-weight="bold">.hermes3d_orchestrator/  (state dir)</text>

  <rect x="55" y="148" width="95" height="36" rx="4" fill="#0f172a" stroke="#06b6d4"/>
  <text x="102" y="164" text-anchor="middle" fill="#06b6d4" font-size="10" font-family="sans-serif" font-weight="bold">locks/</text>
  <text x="102" y="178" text-anchor="middle" fill="#cbd5e1" font-size="8" font-family="sans-serif">mkdir EEXIST</text>

  <rect x="160" y="148" width="95" height="36" rx="4" fill="#0f172a" stroke="#fbbf24"/>
  <text x="207" y="164" text-anchor="middle" fill="#fbbf24" font-size="10" font-family="sans-serif" font-weight="bold">tasks/</text>
  <text x="207" y="178" text-anchor="middle" fill="#cbd5e1" font-size="8" font-family="sans-serif">pending claimed done</text>

  <rect x="265" y="148" width="95" height="36" rx="4" fill="#0f172a" stroke="#a855f7"/>
  <text x="312" y="164" text-anchor="middle" fill="#a855f7" font-size="10" font-family="sans-serif" font-weight="bold">events/</text>
  <text x="312" y="178" text-anchor="middle" fill="#cbd5e1" font-size="8" font-family="sans-serif">outbox handled failed</text>

  <rect x="370" y="148" width="80" height="36" rx="4" fill="#0f172a" stroke="#ec4899"/>
  <text x="410" y="164" text-anchor="middle" fill="#ec4899" font-size="10" font-family="sans-serif" font-weight="bold">handoffs/</text>

  <rect x="55" y="195" width="135" height="36" rx="4" fill="#0f172a" stroke="#22c55e"/>
  <text x="122" y="211" text-anchor="middle" fill="#22c55e" font-size="10" font-family="sans-serif" font-weight="bold">evidence/ NDJSON</text>
  <text x="122" y="225" text-anchor="middle" fill="#cbd5e1" font-size="8" font-family="sans-serif">append-only ledger</text>

  <rect x="200" y="195" width="120" height="36" rx="4" fill="#0f172a" stroke="#06b6d4"/>
  <text x="260" y="211" text-anchor="middle" fill="#06b6d4" font-size="10" font-family="sans-serif" font-weight="bold">gates/ allowlist</text>

  <rect x="330" y="195" width="120" height="36" rx="4" fill="#0f172a" stroke="#fbbf24"/>
  <text x="390" y="211" text-anchor="middle" fill="#fbbf24" font-size="10" font-family="sans-serif" font-weight="bold">events.ndjson</text>

  <rect x="55" y="244" width="395" height="32" rx="4" fill="#0f172a" stroke="#475569"/>
  <text x="252" y="263" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">03_implementation/ui/  +  contracts/CP-UX-A_*.md  (Hermes3D-OS shape)</text>
</svg>
