# hp-hermes-agent-bridge

## Purpose

A working tree of `Ghenghis/HermesProof` parked on the feature branch **`feat/hp-v0.6-anonymous-orchestrator-and-hermes-agent`** — the development lane that introduced the *Hermes Agent bridge* (process-wrapper around the upstream NousResearch Hermes Agent Python runtime) and the *anonymous orchestrator* (skill-rotation + reputation-driven dispatch). The contents here became HermesProof v0.7 once merged; this folder remains as the historical scaffolding for that integration work.

In the Hermes Agent / MCP infrastructure category, this folder is the **predecessor / branch-mirror** of `hermes3d-mcp-lock-orchestrator`. Its role today is read-only reference: comparing v0.6 (here, 36 tools) vs. v0.7 (orchestrator, 44 tools) shows exactly what the bridge + anonymous-orchestrator + A2A + capability-dispatch additions contributed.

## Status

- Git HEAD: `3079f55` merge: forward merge post-PR#33 (supervisor test union)
- Branch: `feat/hp-v0.6-anonymous-orchestrator-and-hermes-agent` (upstream gone)
- package.json version: **0.6.0**
- Lifecycle: **ARCHIVE / REFERENCE** (do not modify; canonical work has moved to v0.7 in `hermes3d-mcp-lock-orchestrator`)

## MCP surface

36 tools registered in `src/server.mjs` — same coordination surface as v0.7 minus eight tools that were added afterwards:

**Present in v0.6 (this folder)**
- `hermes_get_state`, `hermes_doctor`, `hermes_read_policy`
- `hermes_lock_files`, `hermes_release_files`, `hermes_heartbeat`, `hermes_list_locks`, `hermes_recover_stale_locks`
- `hermes_claim_task`, `hermes_release_task`, `hermes_enqueue_task`, `hermes_list_pending_tasks`, `hermes_pick_task`, `hermes_recover_stale_tasks`
- `hermes_request_handoff`, `hermes_approve_handoff`, `hermes_create_blocked_handoff`
- `hermes_list_events`, `hermes_emit_event`, `hermes_mark_event_handled`
- `hermes_append_evidence`, `hermes_verify_evidence`, `hermes_list_gates`, `hermes_run_gate`
- `hermes_anonymous_claim`, `hermes_anonymous_release`, `hermes_anonymous_state`
- `hermes_user_grant_session`, `hermes_user_revoke_session`, `hermes_user_check_authorization`
- `hermes_agent_health`, `hermes_agent_request_user_session`, `hermes_agent_resolve_blocked`, `hermes_agent_revoke_session`

**Added in v0.7 (NOT here)**
- `hermes_list_agents`, `hermes_record_outcome`, `hermes_record_task`, `hermes_dispatch_recommend`
- `hermes_a2a_create_task`, `hermes_a2a_get_task`, `hermes_a2a_update_task`, `hermes_a2a_list_tasks`

## Tech stack

- Node.js ≥ 20, ESM
- `@modelcontextprotocol/sdk` ^1.29.0
- `zod` ^3.24.1
- `dotenv` ^16.4.5
- 19 truth-gates (vs. v0.7's 35) — see `README.md` table

## Key files

| Path | Description |
| --- | --- |
| `src/server.mjs` | MCP server v0.6 — 36 tools, no A2A or dispatch-recommend yet |
| `src/core/lock-manager.mjs` | Lock manager (same shape as v0.7) |
| `src/core/anonymous-orchestrator.mjs` | First version of skill-rotation + reputation dispatch |
| `src/core/hermes-agent-bridge.mjs` | First version of HermesAgent process-wrapper bridge |
| `src/core/gate-runner.mjs` | Allowlisted gate runner |
| `src/core/queue-manager.mjs` | Task queue (pending/claimed/blocked/done) |
| `src/core/event-manager.mjs` | NDJSON event outbox |
| `src/core/registry-providers.mjs` | YAML registry loader for Continue LLM providers |
| `package.json` | v0.6.0 manifest |
| `AGENTS.md` | Same canonical agent rules as v0.7 |
| `policies/`, `prompts/`, `examples/` | v0.6 policy + prompt assets |

## Relationships

- **Direct ancestor of** `hermes3d-mcp-lock-orchestrator` (v0.7); diff = 8 new MCP tools + DI of skills/reputation into CapabilityDispatch + per-PR shutdown handler hardening + a2a-stub + mutex + skill-rotation refactors.
- **Same `HermesAgentBridge` contract** that consumes `hermes-agent-fresh`'s Python runtime — this is where that bridge was first written.
- **Compatible workspace** with `hermes3d-mcp-test-sandbox` (sandbox layout pre-dates this branch).
- **Shares `Ghenghis/HermesProof` origin** with the orchestrator; both can be checked out side-by-side as different worktrees of the same GitHub repo.
- Not a runtime dependency of any other folder — purely a historical reference.

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0f172a"/>
  <text x="250" y="22" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="bold">hp-hermes-agent-bridge — HermesProof v0.6 (predecessor)</text>

  <!-- v0.6 box -->
  <rect x="40" y="50" width="200" height="115" rx="10" fill="#1e293b" stroke="#94a3b8" stroke-width="2" stroke-dasharray="5,3"/>
  <text x="140" y="70" text-anchor="middle" fill="#94a3b8" font-size="12" font-family="sans-serif" font-weight="bold">v0.6 (this folder)</text>
  <text x="140" y="88" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">36 MCP tools</text>
  <text x="140" y="104" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">19 truth-gates</text>
  <text x="140" y="120" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">+ HermesAgentBridge (NEW)</text>
  <text x="140" y="136" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">+ AnonymousOrchestrator (NEW)</text>
  <text x="140" y="152" text-anchor="middle" fill="#94a3b8" font-size="9" font-family="sans-serif">branch: hp-v0.6-...-hermes-agent</text>

  <!-- arrow -->
  <line x1="244" y1="107" x2="280" y2="107" stroke="#a855f7" stroke-width="2"/>
  <polygon points="276,102 286,107 276,112" fill="#a855f7"/>
  <text x="262" y="100" text-anchor="middle" fill="#a855f7" font-size="9" font-family="sans-serif">promote</text>

  <!-- v0.7 box -->
  <rect x="290" y="50" width="190" height="115" rx="10" fill="#1e293b" stroke="#a855f7" stroke-width="2"/>
  <text x="385" y="70" text-anchor="middle" fill="#a855f7" font-size="12" font-family="sans-serif" font-weight="bold">v0.7 (active orchestrator)</text>
  <text x="385" y="88" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">44 MCP tools (+8)</text>
  <text x="385" y="104" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">35 truth-gates</text>
  <text x="385" y="120" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">+ A2A · CapabilityDispatch</text>
  <text x="385" y="136" text-anchor="middle" fill="#cbd5e1" font-size="10" font-family="sans-serif">+ list_agents · record_outcome</text>
  <text x="385" y="152" text-anchor="middle" fill="#94a3b8" font-size="9" font-family="sans-serif">main</text>

  <!-- shared deps row -->
  <text x="250" y="195" text-anchor="middle" fill="#fbbf24" font-size="11" font-family="sans-serif" font-weight="bold">shared (both versions)</text>

  <rect x="40" y="208" width="135" height="32" rx="5" fill="#1e293b" stroke="#06b6d4"/>
  <text x="107" y="228" text-anchor="middle" fill="#06b6d4" font-size="10" font-family="sans-serif">@modelcontextprotocol/sdk</text>

  <rect x="185" y="208" width="135" height="32" rx="5" fill="#1e293b" stroke="#22c55e"/>
  <text x="252" y="228" text-anchor="middle" fill="#22c55e" font-size="10" font-family="sans-serif">LockManager + Gates</text>

  <rect x="330" y="208" width="135" height="32" rx="5" fill="#1e293b" stroke="#ec4899"/>
  <text x="397" y="228" text-anchor="middle" fill="#ec4899" font-size="10" font-family="sans-serif">HermesAgent bridge</text>

  <!-- consumes -->
  <rect x="100" y="252" width="300" height="33" rx="5" fill="#1e293b" stroke="#fbbf24" stroke-width="1.5"/>
  <text x="250" y="271" text-anchor="middle" fill="#fbbf24" font-size="10" font-family="sans-serif" font-weight="bold">consumes hermes-agent-fresh runtime via process wrapper</text>

  <line x1="250" y1="240" x2="250" y2="252" stroke="#fbbf24" stroke-width="1"/>
</svg>
