# atomic-hermes

## Purpose

**AtomicBot-ai/atomic-hermes** — an Electron-based macOS desktop fork of the Hermes Agent that adds native OCR-based computer use, snapshot-backed file editing, a built-in PTY terminal, and a 16+ messenger mission control. It is essentially "Hermes Agent in a window" with a desktop-app skin: same Python agent core (vendored hermes-agent layout: `agent/`, `skills/`, `gateway/`, `mcp_serve.py`) plus an Electron 33 / React 19 desktop layer (`desktop/`).

In the Hermes Agent / MCP infrastructure category, atomic-hermes plays the role of the **end-user-facing fat client** — a reference for what a fully-bundled, GUI-distributed Hermes Agent looks like (electron-builder release pipeline, signed `.dmg`, autostart, delta updater). The lock-orchestrator does not depend on it; it shares architectural DNA via the upstream hermes-agent project.

## Status

- Working tree: clean, but the repo is **not initialized as git** at this top level (no `.git`); it is fetched as a release-tagged source drop. Most recent in-tree change in `desktop/`: 2026-05-01.
- Lifecycle: **ACTIVE — REFERENCE FORK** (do not modify locally; treat as upstream).

## MCP surface

Atomic Hermes ships and consumes MCP servers; it is not itself the orchestrator:

- Re-uses `mcp_serve.py` from the underlying Hermes Agent layout (same 10-tool messaging surface as `hermes-agent-fresh`).
- Distributes a **separately published** computer-use MCP server: `@atomicbotai/computer-use-mcp` (npm) — drop-in for Claude Desktop / Cursor / Windsurf. Exposes screenshot + native-OCR + click/type/drag tool calls.
- Companion library `@atomicbotai/computer-use` (npm) — TS implementation of OCR (Apple Vision / Windows.Media.Ocr), action overlay, session lock.

## Tech stack

- Electron 33 + Node ≥ 18 (`desktop/package.json`, `electron-rebuild`, `electron-builder`)
- React 19 + Redux Toolkit + Monaco Editor (renderer)
- Vite 5 build pipeline (`renderer/vite.config.ts`)
- Vitest test runner
- node-pty for built-in terminal
- Python agent core inherited from hermes-agent layout (`agent/`, `skills/`, `gateway/`, `acp_adapter/`, `acp_registry/`)
- PostHog telemetry
- PolyForm Noncommercial license (NOT MIT — different from upstream)

## Key files

| Path | Description |
| --- | --- |
| `README.md` | Atomic Hermes pitch: native-OCR computer use, file snapshots, local-model bundle |
| `desktop/package.json` | Electron app manifest (`hermes-desktop` v0.1.36); build/dist scripts |
| `desktop/src/` | Electron main + preload TypeScript |
| `desktop/renderer/` | React renderer (chat / files / terminal / dashboard tabs) |
| `desktop/scripts/release.sh` | Release pipeline (patch / minor / major) |
| `cli.py`, `mcp_serve.py` | Inherited Hermes Agent CLI + MCP server entry points |
| `agent/`, `skills/`, `gateway/` | Same agent core as hermes-agent-fresh |
| `acp_adapter/`, `acp_registry/` | Agent Communication Protocol adapter/registry layer |
| `desktop/.env.example` | Required runtime config keys |
| `Dockerfile`, `docker-compose.yml` | Server-mode container build |

## Relationships

- **Sibling fork** of `hermes-agent-fresh` — both share the upstream Python layout; atomic-hermes adds the `desktop/` Electron shell.
- The lock orchestrator (`hermes3d-mcp-lock-orchestrator`) does not import atomic-hermes; both can coexist as MCP clients of the same `hermes3d-locks` server.
- Atomic Hermes' `@atomicbotai/computer-use-mcp` is one possible MCP tool the lock-orchestrator's Claude/Codex/Windsurf clients could compose with alongside `hermes3d-locks`.
- Distinct license (PolyForm NC) means downstream Hermes3D code must avoid copy-paste from this repo.

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0f172a"/>
  <text x="250" y="22" text-anchor="middle" fill="#f1f5f9" font-family="sans-serif" font-size="13" font-weight="bold">atomic-hermes — Electron desktop fork</text>

  <!-- Electron app shell -->
  <rect x="40" y="45" width="420" height="100" rx="10" fill="#1e293b" stroke="#FF9100" stroke-width="2"/>
  <text x="250" y="65" text-anchor="middle" fill="#FF9100" font-family="sans-serif" font-size="12" font-weight="bold">desktop/  (Electron 33 + React 19)</text>

  <rect x="55" y="78" width="90" height="55" rx="5" fill="#0f172a" stroke="#06b6d4"/>
  <text x="100" y="98" text-anchor="middle" fill="#06b6d4" font-size="10" font-family="sans-serif" font-weight="bold">Chat tab</text>
  <text x="100" y="115" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">streaming + tools</text>

  <rect x="155" y="78" width="90" height="55" rx="5" fill="#0f172a" stroke="#22c55e"/>
  <text x="200" y="98" text-anchor="middle" fill="#22c55e" font-size="10" font-family="sans-serif" font-weight="bold">Files tab</text>
  <text x="200" y="115" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">snapshots + diff</text>

  <rect x="255" y="78" width="90" height="55" rx="5" fill="#0f172a" stroke="#a855f7"/>
  <text x="300" y="98" text-anchor="middle" fill="#a855f7" font-size="10" font-family="sans-serif" font-weight="bold">Terminal</text>
  <text x="300" y="115" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">node-pty</text>

  <rect x="355" y="78" width="90" height="55" rx="5" fill="#0f172a" stroke="#ec4899"/>
  <text x="400" y="98" text-anchor="middle" fill="#ec4899" font-size="10" font-family="sans-serif" font-weight="bold">Computer Use</text>
  <text x="400" y="115" text-anchor="middle" fill="#cbd5e1" font-size="9" font-family="sans-serif">native OCR</text>

  <!-- Hermes Agent Python core -->
  <rect x="40" y="170" width="240" height="55" rx="8" fill="#1e293b" stroke="#ec4899" stroke-width="1.5"/>
  <text x="160" y="190" text-anchor="middle" fill="#ec4899" font-family="sans-serif" font-size="11" font-weight="bold">Hermes Agent core (Python)</text>
  <text x="160" y="208" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">cli.py · agent/ · gateway/ · mcp_serve.py</text>

  <!-- npm mcp -->
  <rect x="300" y="170" width="160" height="55" rx="8" fill="#1e293b" stroke="#fbbf24" stroke-width="1.5"/>
  <text x="380" y="190" text-anchor="middle" fill="#fbbf24" font-family="sans-serif" font-size="11" font-weight="bold">@atomicbotai/</text>
  <text x="380" y="208" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="9">computer-use-mcp (npm)</text>

  <!-- co-runs with -->
  <rect x="100" y="248" width="300" height="38" rx="6" fill="#1e293b" stroke="#475569" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="250" y="265" text-anchor="middle" fill="#cbd5e1" font-family="sans-serif" font-size="10">composes with hermes3d-locks (separate MCP server)</text>
  <text x="250" y="278" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="9">parallel client, not a dependency</text>

  <line x1="160" y1="225" x2="160" y2="248" stroke="#475569" stroke-width="1" stroke-dasharray="3,3"/>
</svg>
