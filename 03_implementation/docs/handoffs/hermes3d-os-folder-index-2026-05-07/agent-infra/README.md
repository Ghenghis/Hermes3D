# Agent Infrastructure — category index

Five folders under `G:\Github\` form the Hermes Agent / MCP infrastructure stack: two **agent runtimes** (Python core + Electron desktop fork), one **active orchestrator**, one **predecessor branch** of that orchestrator, and one **disposable test workspace**. They split cleanly into two layers — the LLM agent runtime layer (vendored Nous Research code), and the multi-agent coordination layer (Ghenghis HermesProof code) that brokers locks, handoffs, gates, and evidence between Claude / Codex / Windsurf / Cascade and that runtime.

## Folders

| # | Folder | Role | Status | Version | MCP tools |
| - | --- | --- | --- | --- | --- |
| 1 | [hermes-agent-fresh](./hermes-agent-fresh.md) | Vendored NousResearch Hermes Agent (Python) — TUI + 6 messengers + skill loop | ACTIVE / vendored | v0.12.0 | 10 (messaging bridge) |
| 2 | [atomic-hermes](./atomic-hermes.md) | AtomicBot-ai Electron fork — desktop app, native OCR, file snapshots | ACTIVE / fork | v0.1.36 desktop | 10 inherited + computer-use-mcp (npm) |
| 3 | [hermes3d-mcp-lock-orchestrator](./hermes3d-mcp-lock-orchestrator.md) | **Primary orchestrator** — `hermes3d-locks` MCP server, locks/handoffs/gates/evidence | ACTIVE / primary | v0.7.0 | **44** |
| 4 | [hp-hermes-agent-bridge](./hp-hermes-agent-bridge.md) | Predecessor v0.6 branch where HermesAgentBridge was first written | ARCHIVE / reference | v0.6.0 | 36 |
| 5 | [hermes3d-mcp-test-sandbox](./hermes3d-mcp-test-sandbox.md) | Disposable workspace fixture for orchestrator smoke tests | SANDBOX | n/a | 0 (target only) |

## How the layers connect

- **Layer A — Agent runtime** (Python + Electron): `hermes-agent-fresh` is the upstream; `atomic-hermes` is a desktop fork. Both expose a 10-tool messaging MCP surface (`mcp_serve.py`).
- **Layer B — Coordination plane** (Node ESM): `hermes3d-mcp-lock-orchestrator` is the deployed `hermes3d-locks` server (44 tools, v0.7); `hp-hermes-agent-bridge` is the predecessor v0.6 branch on the same `Ghenghis/HermesProof` repo.
- **Bridge between layers**: `src/core/hermes-agent-bridge.mjs` (in both v0.6 and v0.7) wraps the Python Hermes Agent as a child process the orchestrator can dispatch anonymous tasks into and authorize via `hermes_agent_*` MCP tools.
- **Test target**: `hermes3d-mcp-test-sandbox` provides the workspace shape (`tasks/`, `events/`, `locks/`, `evidence/`, `gates/`, `handoffs/`) that the orchestrator's `hermes_doctor` and queue manager expect — pointed at via `MCP_LOCK_WORKSPACE` for round-trip smoke tests.

## Master SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="700" height="400">
  <rect width="700" height="400" fill="#0f172a"/>
  <text x="350" y="24" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="15" font-weight="bold">Hermes Agent / MCP Infrastructure — five-folder stack</text>

  <!-- Layer A label -->
  <text x="20" y="62" fill="#fbbf24" font-family="sans-serif" font-size="11" font-weight="bold">A · Agent runtime</text>
  <line x1="20" y1="68" x2="680" y2="68" stroke="#fbbf24" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.4"/>

  <!-- hermes-agent-fresh -->
  <rect x="40" y="80" width="220" height="80" rx="10" fill="#1e293b" stroke="#ec4899" stroke-width="2"/>
  <text x="150" y="100" text-anchor="middle" fill="#ec4899" font-family="sans-serif" font-size="12" font-weight="bold">hermes-agent-fresh</text>
  <text x="150" y="116" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">NousResearch · Python · v0.12.0</text>
  <text x="150" y="132" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">cli.py · agent/ · gateway/</text>
  <text x="150" y="148" text-anchor="middle" fill="#06b6d4" font-family="sans-serif" font-size="9">mcp_serve.py · 10 messaging tools</text>

  <!-- atomic-hermes -->
  <rect x="280" y="80" width="220" height="80" rx="10" fill="#1e293b" stroke="#FF9100" stroke-width="2"/>
  <text x="390" y="100" text-anchor="middle" fill="#FF9100" font-family="sans-serif" font-size="12" font-weight="bold">atomic-hermes</text>
  <text x="390" y="116" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">AtomicBot · Electron 33 · macOS</text>
  <text x="390" y="132" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">desktop/ + same Python core</text>
  <text x="390" y="148" text-anchor="middle" fill="#fbbf24" font-family="sans-serif" font-size="9">@atomicbotai/computer-use-mcp</text>

  <!-- shared origin marker -->
  <text x="270" y="125" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="9">fork</text>
  <line x1="260" y1="120" x2="280" y2="120" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,3"/>

  <!-- bridge link to coordination layer -->
  <rect x="520" y="80" width="160" height="80" rx="10" fill="#1e293b" stroke="#22c55e" stroke-width="2"/>
  <text x="600" y="100" text-anchor="middle" fill="#22c55e" font-family="sans-serif" font-size="11" font-weight="bold">HermesAgentBridge</text>
  <text x="600" y="116" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">src/core/hermes-agent-bridge.mjs</text>
  <text x="600" y="132" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">child-process wraps Python</text>
  <text x="600" y="148" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">hermes_agent_* MCP tools</text>

  <line x1="260" y1="120" x2="520" y2="120" stroke="#22c55e" stroke-width="1.5"/>
  <polygon points="516,116 524,120 516,124" fill="#22c55e"/>

  <!-- Layer B label -->
  <text x="20" y="195" fill="#a855f7" font-family="sans-serif" font-size="11" font-weight="bold">B · Coordination plane (Ghenghis/HermesProof)</text>
  <line x1="20" y1="201" x2="680" y2="201" stroke="#a855f7" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.4"/>

  <!-- v0.6 hp-hermes-agent-bridge -->
  <rect x="40" y="215" width="240" height="100" rx="10" fill="#1e293b" stroke="#94a3b8" stroke-width="2" stroke-dasharray="5,3"/>
  <text x="160" y="235" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="12" font-weight="bold">hp-hermes-agent-bridge</text>
  <text x="160" y="251" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">v0.6 · ARCHIVE / reference</text>
  <text x="160" y="267" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">36 MCP tools · 19 truth-gates</text>
  <text x="160" y="283" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">first HermesAgentBridge impl</text>
  <text x="160" y="302" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="9">branch: feat/hp-v0.6-...-hermes-agent</text>

  <!-- promotion arrow -->
  <line x1="284" y1="265" x2="320" y2="265" stroke="#a855f7" stroke-width="2"/>
  <polygon points="316,260 326,265 316,270" fill="#a855f7"/>
  <text x="304" y="258" text-anchor="middle" fill="#a855f7" font-family="sans-serif" font-size="9">promote</text>

  <!-- v0.7 orchestrator -->
  <rect x="330" y="215" width="350" height="100" rx="10" fill="#1e293b" stroke="#a855f7" stroke-width="2.5"/>
  <text x="505" y="235" text-anchor="middle" fill="#a855f7" font-family="sans-serif" font-size="12" font-weight="bold">hermes3d-mcp-lock-orchestrator (active)</text>
  <text x="505" y="251" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">v0.7.0 · MCP server name: hermes3d-locks</text>
  <text x="505" y="267" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">44 MCP tools · 35 truth-gates · Sigstore-signed PROOF</text>
  <text x="505" y="285" text-anchor="middle" fill="#06b6d4" font-family="sans-serif" font-size="9">locks · tasks · events · handoffs · gates · evidence</text>
  <text x="505" y="300" text-anchor="middle" fill="#fbbf24" font-family="sans-serif" font-size="9">+ A2A · CapabilityDispatch · AnonymousOrchestrator</text>

  <!-- bridge box from above feeds into orchestrator -->
  <line x1="600" y1="160" x2="600" y2="215" stroke="#22c55e" stroke-width="1.5" stroke-dasharray="4,2"/>
  <polygon points="596,211 600,219 604,211" fill="#22c55e"/>

  <!-- Layer C label -->
  <text x="20" y="345" fill="#22c55e" font-family="sans-serif" font-size="11" font-weight="bold">C · Workspace target</text>
  <line x1="20" y1="351" x2="680" y2="351" stroke="#22c55e" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.4"/>

  <!-- sandbox -->
  <rect x="160" y="360" width="380" height="32" rx="6" fill="#1e293b" stroke="#22c55e" stroke-width="2"/>
  <text x="350" y="380" text-anchor="middle" fill="#22c55e" font-family="sans-serif" font-size="11" font-weight="bold">hermes3d-mcp-test-sandbox  (MCP_LOCK_WORKSPACE target)</text>

  <line x1="505" y1="315" x2="350" y2="360" stroke="#22c55e" stroke-width="1.5"/>
  <polygon points="346,355 354,362 348,365" fill="#22c55e"/>

  <!-- agent client annotations -->
  <text x="690" y="245" text-anchor="end" fill="#06b6d4" font-family="sans-serif" font-size="9">↑ Claude / Codex / Windsurf / Cascade clients</text>
</svg>

## Quick reference: which folder owns what

- **Locks · handoffs · gates · evidence** → `hermes3d-mcp-lock-orchestrator`
- **Anonymous orchestrator + agent bridge first impl** → `hp-hermes-agent-bridge` (v0.6 reference)
- **Python agent runtime + skills + 6 messengers** → `hermes-agent-fresh`
- **macOS desktop GUI + native OCR computer use** → `atomic-hermes`
- **Workspace shape used by smoke tests** → `hermes3d-mcp-test-sandbox`
