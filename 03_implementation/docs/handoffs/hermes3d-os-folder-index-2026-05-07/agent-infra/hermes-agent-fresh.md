# hermes-agent-fresh

## Purpose

Upstream **NousResearch/hermes-agent** clone — the canonical "Hermes Agent" Python codebase by Nous Research. This is the open-source self-improving AI agent (TUI + multi-platform messaging gateway + skill / memory loop) the Ghenghis ecosystem is named after and integrates with via the `HermesAgentBridge` adapter inside the lock orchestrator. It is *not* the MCP lock orchestrator itself; it is the LLM agent runtime that the orchestrator dispatches work into.

The clone is treated as a vendor reference: it provides the agent role surface (skills, gateway, mcp_serve), the canonical 9-tool MCP channel-bridge surface (`conversations_list`, `messages_send`, `events_poll`, …), and the model-routing layer that the lock orchestrator's registry-providers loader mirrors against. Local edits should remain minimal — pull updates from upstream `main` rather than diverging.

## Status

- Git HEAD: `73bf3ab1b` chore: release v0.12.0 (2026.4.30) (#18057)
- Branch: tracking upstream NousResearch/hermes-agent main
- Lifecycle: **ACTIVE — VENDORED REFERENCE** (do not modify; refresh from upstream)

## MCP surface

Exposes a stdio MCP server via `mcp_serve.py` (entry: `hermes mcp serve`). Tool names mirror OpenClaw's 9-tool channel bridge plus a Hermes extra:

- `conversations_list`, `conversation_get`
- `messages_read`, `messages_send`
- `attachments_fetch`
- `events_poll`, `events_wait`
- `permissions_list_open`, `permissions_respond`
- `channels_list` (Hermes-specific)

This is the **agent-facing** MCP surface (messaging conversations) — distinct from the lock-orchestrator's coordination surface (`hermes_lock_files`, `hermes_run_gate`, …).

## Tech stack

- Python 3.11+ (pyproject.toml + uv.lock)
- Click-based CLI (`hermes` binary), Textual TUI (`tui_gateway/`, `ui-tui/`)
- Stdio MCP server (`mcp_serve.py`)
- Multi-platform gateways: Telegram / Discord / Slack / WhatsApp / Signal / Email (`gateway/`)
- Six terminal backends: local / Docker / SSH / Daytona / Singularity / Modal (`environments/`)
- Skills system (`skills/`, `optional-skills/`) compatible with agentskills.io
- Atropos RL trajectory tooling (`tinker-atropos/`, `batch_runner.py`)
- Nix flake (`flake.nix`) and Docker (`Dockerfile`, `docker-compose.yml`)

## Key files

| Path | Description |
| --- | --- |
| `README.md` | Hermes Agent overview, install (`scripts/install.sh`), CLI vs messaging table |
| `package.json` | Thin Node shim for `agent-browser` browser tools (Python is the real stack) |
| `pyproject.toml` | Python build + extras (`.[all]`, `.[termux]`) |
| `cli.py` | Top-level `hermes` Click CLI dispatcher |
| `mcp_serve.py` | Stdio MCP server exposing the 10-tool messaging surface |
| `run_agent.py` | Direct agent runner (non-CLI entry) |
| `agent/` | Core agent loop, tool calling, model routing |
| `gateway/` | Telegram/Discord/Slack/WhatsApp/Signal/Email bridges |
| `skills/` | Skill definitions consumed by the agent (curated) |
| `cron/` | Built-in scheduled-automation engine |
| `tools/` | Built-in tool implementations (file ops, search, browser, etc.) |

## Relationships

- Consumed by `hermes3d-mcp-lock-orchestrator` via `src/core/hermes-agent-bridge.mjs` — the bridge wraps a Hermes Agent process so the orchestrator can dispatch anonymous tasks to it.
- `hp-hermes-agent-bridge` is the v0.6 ancestor of that bridge implementation.
- `atomic-hermes` is a downstream **Electron desktop fork** of this same Hermes Agent project.
- The 62-provider registry the orchestrator loads (`policies/provider-registry/registry.yaml`) is the lock-orchestrator's mirror of Hermes Agent's model-router catalog.

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0f172a"/>
  <text x="250" y="22" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="bold">hermes-agent-fresh — vendored Nous Research agent</text>

  <!-- Hermes Agent core -->
  <rect x="170" y="50" width="160" height="70" rx="8" fill="#1e293b" stroke="#ec4899" stroke-width="2"/>
  <text x="250" y="74" text-anchor="middle" fill="#ec4899" font-family="sans-serif" font-size="12" font-weight="bold">Hermes Agent (Python)</text>
  <text x="250" y="92" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">cli.py · agent/ · skills/</text>
  <text x="250" y="108" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">v0.12.0</text>

  <!-- mcp_serve -->
  <rect x="20" y="160" width="140" height="55" rx="6" fill="#1e293b" stroke="#06b6d4" stroke-width="1.5"/>
  <text x="90" y="180" text-anchor="middle" fill="#06b6d4" font-family="sans-serif" font-size="11" font-weight="bold">mcp_serve.py</text>
  <text x="90" y="196" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">conversations_list,</text>
  <text x="90" y="208" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">messages_send, events_poll</text>

  <!-- gateways -->
  <rect x="180" y="160" width="140" height="55" rx="6" fill="#1e293b" stroke="#a855f7" stroke-width="1.5"/>
  <text x="250" y="180" text-anchor="middle" fill="#a855f7" font-family="sans-serif" font-size="11" font-weight="bold">gateway/</text>
  <text x="250" y="196" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">Telegram · Discord · Slack</text>
  <text x="250" y="208" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">WhatsApp · Signal · Email</text>

  <!-- environments -->
  <rect x="340" y="160" width="140" height="55" rx="6" fill="#1e293b" stroke="#22c55e" stroke-width="1.5"/>
  <text x="410" y="180" text-anchor="middle" fill="#22c55e" font-family="sans-serif" font-size="11" font-weight="bold">environments/</text>
  <text x="410" y="196" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">local · Docker · SSH</text>
  <text x="410" y="208" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">Daytona · Modal · Singularity</text>

  <!-- arrows -->
  <line x1="220" y1="120" x2="120" y2="160" stroke="#475569" stroke-width="1.5"/>
  <line x1="250" y1="120" x2="250" y2="160" stroke="#475569" stroke-width="1.5"/>
  <line x1="280" y1="120" x2="380" y2="160" stroke="#475569" stroke-width="1.5"/>

  <!-- consumer -->
  <rect x="100" y="245" width="300" height="40" rx="6" fill="#1e293b" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="4,3"/>
  <text x="250" y="262" text-anchor="middle" fill="#fbbf24" font-family="sans-serif" font-size="11" font-weight="bold">hermes3d-mcp-lock-orchestrator</text>
  <text x="250" y="277" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">core/hermes-agent-bridge.mjs wraps this runtime</text>
  <line x1="250" y1="215" x2="250" y2="245" stroke="#fbbf24" stroke-width="1.5" stroke-dasharray="3,3"/>
</svg>
