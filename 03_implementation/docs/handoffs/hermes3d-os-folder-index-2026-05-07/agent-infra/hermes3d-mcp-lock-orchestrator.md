# hermes3d-mcp-lock-orchestrator

## Purpose

The **active orchestrator repo** — published on GitHub as `Ghenghis/HermesProof` v0.7.0 and deployed under the MCP server name `hermes3d-locks`. It is the per-file lock manager, atomic-handoff broker, allowlisted gate runner, and append-only evidence ledger that lets Claude · Codex · Windsurf · Cascade coordinate edits on the same repository without clobbering each other. Every push to `main` re-proves the system through 35 truth gates and signs `PROOF/latest.json` with Sigstore.

In the Hermes Agent / MCP infrastructure category, this repo is the **coordination plane**: it sits below the LLM agents (Claude / Codex / Windsurf) and above the workspace filesystem, mediating who edits what and emitting a verifiable evidence trail. The `HermesAgentBridge` (in `src/core/`) is the integration point that lets the Nous Research Hermes Agent participate as one of those orchestrated agents.

## Status

- Git HEAD: `c37d7dd` fix(P1): hermes_list_agents shows roles + CapabilityDispatch DI
- Branch: `claude/nifty-hofstadter-ee4b17` (worktree active)
- package.json version: **0.7.0**
- Lifecycle: **ACTIVE — PRIMARY** (this is the canonical orchestrator)

## MCP surface

44 tools registered in `src/server.mjs` under server name `hermes3d-lock-orchestrator` (deployed as `hermes3d-locks`). Grouped by capability:

**Lock & state**
- `hermes_get_state`, `hermes_doctor`, `hermes_read_policy`, `hermes_list_agents`
- `hermes_lock_files`, `hermes_release_files`, `hermes_heartbeat`, `hermes_list_locks`
- `hermes_recover_stale_locks`

**Task lifecycle**
- `hermes_claim_task`, `hermes_release_task`, `hermes_record_task`
- `hermes_enqueue_task`, `hermes_list_pending_tasks`, `hermes_pick_task`, `hermes_recover_stale_tasks`

**Handoff**
- `hermes_request_handoff`, `hermes_approve_handoff`, `hermes_create_blocked_handoff`

**Events**
- `hermes_list_events`, `hermes_emit_event`, `hermes_mark_event_handled`

**Evidence + gates**
- `hermes_append_evidence`, `hermes_verify_evidence`
- `hermes_list_gates`, `hermes_run_gate` (allowlisted: git-status, diff-check, npm-test, audit, …)

**Anonymous orchestration**
- `hermes_anonymous_claim`, `hermes_anonymous_release`, `hermes_anonymous_state`
- `hermes_record_outcome`, `hermes_dispatch_recommend`

**A2A (Agent-to-Agent task pool)**
- `hermes_a2a_create_task`, `hermes_a2a_get_task`, `hermes_a2a_update_task`, `hermes_a2a_list_tasks`

**User authorization**
- `hermes_user_grant_session`, `hermes_user_revoke_session`, `hermes_user_check_authorization`

**Hermes Agent bridge**
- `hermes_agent_health`, `hermes_agent_request_user_session`
- `hermes_agent_resolve_blocked`, `hermes_agent_revoke_session`

## Tech stack

- Node.js ≥ 20, ESM (`"type": "module"`)
- `@modelcontextprotocol/sdk` ^1.29.0 (stdio JSON-RPC)
- `zod` ^3.24.1 schemas
- `dotenv` ^16.4.5 (with profile-aware `resolveEnvFile`)
- Atomic mkdir EEXIST file locks, NDJSON append-only evidence ledger
- `node --test` smoke harness (~25 test files)
- Sigstore keyless OIDC signing for `PROOF/latest.json`
- 35 truth-gates pipeline (`scripts/truth-gates.mjs`)

## Key files

| Path | Description |
| --- | --- |
| `src/server.mjs` | MCP server — registers 44 `hermes_*` tools, owns DI graph |
| `src/core/lock-manager.mjs` | Atomic per-file locks, TTL/heartbeat, blocked-state tracking |
| `src/core/gate-runner.mjs` | Allowlisted gate execution (no raw shell) |
| `src/core/anonymous-orchestrator.mjs` | Skill-rotation + reputation-driven anonymous dispatch |
| `src/core/hermes-agent-bridge.mjs` | Adapter wrapping NousResearch Hermes Agent runtime |
| `src/core/capability-dispatch.mjs` | Capability-based task routing with DI of skills + reputation |
| `src/core/a2a-stub.mjs` | Agent-to-Agent task pool (Google A2A wire shape) |
| `src/core/registry-providers.mjs` | Loads 62 Continue LLM providers from policies registry |
| `scripts/truth-gates.mjs` | 35-gate proof harness (run on every push to main) |
| `scripts/wizard.mjs` | Universal client-wiring wizard (Claude Desktop / Code / Codex / Windsurf) |
| `AGENTS.md` | Canonical agent rules (claim → lock → edit → handoff → gate → release) |

## Relationships

- **Successor of** `hp-hermes-agent-bridge` (v0.6 feature branch); v0.7 promoted that branch's `anonymous-orchestrator` + `hermes-agent-bridge` into the main release.
- **Consumes** `hermes-agent-fresh` indirectly via `HermesAgentBridge` (process wrapper around the Python agent).
- **Coordinates** Claude / Codex / Windsurf / Cascade clients editing the parent Hermes3D / HermesProof workspace (`HERMES3D_WORKSPACE` env).
- **Tested against** `hermes3d-mcp-test-sandbox` (sandbox workspace targets the orchestrator's protocol).
- **Subsystem clients** of this server appear in core repo `Hermes3D` (Action Window, dispatcher) and orchestration repo `Hermes3D-OS`.

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0f172a"/>
  <text x="250" y="22" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="bold">hermes3d-mcp-lock-orchestrator (HermesProof v0.7)</text>

  <!-- agents -->
  <rect x="20" y="50" width="80" height="32" rx="4" fill="#1e293b" stroke="#06b6d4"/>
  <text x="60" y="71" text-anchor="middle" fill="#06b6d4" font-size="10" font-family="sans-serif" font-weight="bold">Claude</text>
  <rect x="110" y="50" width="80" height="32" rx="4" fill="#1e293b" stroke="#a855f7"/>
  <text x="150" y="71" text-anchor="middle" fill="#a855f7" font-size="10" font-family="sans-serif" font-weight="bold">Codex</text>
  <rect x="200" y="50" width="80" height="32" rx="4" fill="#1e293b" stroke="#22c55e"/>
  <text x="240" y="71" text-anchor="middle" fill="#22c55e" font-size="10" font-family="sans-serif" font-weight="bold">Windsurf</text>
  <rect x="290" y="50" width="80" height="32" rx="4" fill="#1e293b" stroke="#ec4899"/>
  <text x="330" y="71" text-anchor="middle" fill="#ec4899" font-size="10" font-family="sans-serif" font-weight="bold">Cascade</text>
  <rect x="380" y="50" width="100" height="32" rx="4" fill="#1e293b" stroke="#fbbf24"/>
  <text x="430" y="71" text-anchor="middle" fill="#fbbf24" font-size="10" font-family="sans-serif" font-weight="bold">Hermes Agent</text>

  <!-- arrows down -->
  <line x1="60" y1="82" x2="170" y2="115" stroke="#475569"/>
  <line x1="150" y1="82" x2="200" y2="115" stroke="#475569"/>
  <line x1="240" y1="82" x2="250" y2="115" stroke="#475569"/>
  <line x1="330" y1="82" x2="300" y2="115" stroke="#475569"/>
  <line x1="430" y1="82" x2="335" y2="115" stroke="#475569"/>

  <!-- orchestrator -->
  <rect x="60" y="115" width="380" height="105" rx="10" fill="#1e293b" stroke="#a855f7" stroke-width="2.5"/>
  <text x="250" y="135" text-anchor="middle" fill="#a855f7" font-size="12" font-family="sans-serif" font-weight="bold">hermes3d-locks (44 MCP tools)</text>

  <rect x="75" y="148" width="115" height="28" rx="3" fill="#0f172a" stroke="#06b6d4"/>
  <text x="132" y="166" text-anchor="middle" fill="#06b6d4" font-size="9" font-family="sans-serif">LockManager · locks/</text>

  <rect x="195" y="148" width="115" height="28" rx="3" fill="#0f172a" stroke="#22c55e"/>
  <text x="252" y="166" text-anchor="middle" fill="#22c55e" font-size="9" font-family="sans-serif">GateRunner · gates/</text>

  <rect x="315" y="148" width="115" height="28" rx="3" fill="#0f172a" stroke="#fbbf24"/>
  <text x="372" y="166" text-anchor="middle" fill="#fbbf24" font-size="9" font-family="sans-serif">EvidenceLedger NDJSON</text>

  <rect x="75" y="184" width="170" height="28" rx="3" fill="#0f172a" stroke="#ec4899"/>
  <text x="160" y="202" text-anchor="middle" fill="#ec4899" font-size="9" font-family="sans-serif">AnonymousOrchestrator · A2A</text>

  <rect x="255" y="184" width="175" height="28" rx="3" fill="#0f172a" stroke="#fbbf24"/>
  <text x="342" y="202" text-anchor="middle" fill="#fbbf24" font-size="9" font-family="sans-serif">HermesAgentBridge · 62-providers</text>

  <!-- workspace -->
  <rect x="100" y="245" width="300" height="40" rx="6" fill="#1e293b" stroke="#22c55e" stroke-width="1.5"/>
  <text x="250" y="263" text-anchor="middle" fill="#22c55e" font-size="11" font-family="sans-serif" font-weight="bold">workspace (Hermes3D / any project)</text>
  <text x="250" y="278" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">35 truth-gates · Sigstore-signed PROOF/latest.json</text>
  <line x1="250" y1="220" x2="250" y2="245" stroke="#22c55e" stroke-width="1.5"/>
</svg>
