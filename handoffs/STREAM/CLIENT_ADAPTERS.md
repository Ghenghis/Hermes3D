# STREAM/CLIENT_ADAPTERS.md — How any AI coding client joins the loop

> Any client that can read/write markdown in the repo can participate.
> This file documents the smallest possible drop-in for each major client.
> Adapters are in `examples/<client>/streamhooks/` (created on-demand).

---

## Universal contract (works in any client)

A client is "STREAM-aware" if, at the start of every coding session OR every
3-5 minutes of inactivity, it:

1. Reads `handoffs/STREAM/PROTOCOL.md` (skim first time, cache after)
2. Reads `handoffs/STREAM/STATE.md`
3. Reads its own inbox (CLAUDE_INBOX or CODEX_INBOX or — for new clients —
   creates a new `<CLIENT>_INBOX.md` with first claim)
4. ACKs any open messages addressed to its role (within 15 min)
5. Acts on resolution (within SLA per type)
6. Updates STATE.md if material state changed

That's it. The rest is per-client convenience tooling.

---

## Claude Code (CLI)

**Drop-in path:** `examples/claude_code/streamhooks/`

- `settings.hooks.json` — SessionStart hook reads PROTOCOL+STATE, PreToolUse
  hook on Edit|Write|MultiEdit checks if the target file is in an active
  TASK_CLAIMED scope; if yes and not your claim, blocks with explanation.
- `skills/streamhandoff/SKILL.md` — instructions for the skill: poll inbox,
  ACK, resolve, archive.

Install: `node scripts/install-clients.mjs --target=claude-code`

---

## Codex CLI

**Drop-in path:** `examples/codex/streamhooks/`

- `system-prompt.md` — append to user's system prompt: "Every 3-5 min,
  read handoffs/STREAM/, ACK open messages, post TASK_CLAIMED before
  starting work."
- `mcp_config.json` — HermesProof MCP server registration (already shipped
  in v0.5.0 wizard).

Install: `node scripts/install-clients.mjs --target=codex`

---

## KiloCode

**Drop-in path:** `examples/kilocode/streamhooks/`

- `rules.toml`:
  ```toml
  [stream]
  protocol_path = "handoffs/STREAM/PROTOCOL.md"
  inbox_path = "handoffs/STREAM/KILOCODE_INBOX.md"
  poll_interval = "3min"

  [hooks]
  on_session_start = "read protocol + state"
  on_idle = "poll inbox"
  on_long_task = "post HEARTBEAT every 30min"
  ```
- `system-prompt-snippet.md` — paste into KiloCode's system prompt config.

Install: `node scripts/install-clients.mjs --target=kilocode`

---

## Cursor

**Drop-in path:** `examples/cursor/streamhooks/`

- `.cursor/rules/stream.mdc` — Cursor rule format:
  ```
  ---
  description: HermesProof STREAM coordination protocol
  globs: handoffs/STREAM/**, .hermes3d_orchestrator/**
  alwaysApply: true
  ---
  Before any code change, read handoffs/STREAM/STATE.md...
  ```
- `.cursor/mcp.json` — adds HermesProof MCP server.

Install: `node scripts/install-clients.mjs --target=cursor`

---

## Windsurf

**Drop-in path:** `examples/windsurf/streamhooks/`

- `.windsurfrules` — markdown rule file (Windsurf reads automatically):
  protocol summary + polling instructions.
- `mcp_config.json` — Windsurf MCP server config.

Install: `node scripts/install-clients.mjs --target=windsurf`

---

## VSCode + GitHub Copilot

**Drop-in path:** `examples/vscode/streamhooks/`

- `.vscode/mcp.json` — Copilot MCP registration (HermesProof).
- `.github/copilot-instructions.md` — repo-level instructions snippet
  pointing at PROTOCOL.md.

Install: `node scripts/install-clients.mjs --target=vscode`

---

## GitHub Actions runner (last-resort watchdog)

**Path:** `.github/workflows/stream-watchdog.yml`

If all interactive clients are offline, a cron-triggered Action runs:

```yaml
on:
  schedule:
    - cron: '*/15 * * * *'  # every 15 min
  workflow_dispatch:
jobs:
  watchdog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>
      - run: node scripts/stream-watchdog.mjs
      - run: node scripts/stream-archive.mjs
      - if: failure()
        run: gh issue create --title "[STREAM] watchdog wedged" --body-file ...
```

This is the last-line guarantee. Even if every interactive AI client crashes,
the GH Action runner keeps doing W1-W4 and ensures the queue doesn't rot.

---

## Anonymous role rotation across clients

Each client picks ONE of the canonical roles per polling cycle:

- BUILDER (claims tasks, writes code)
- CRITIC (audits PRs)
- SCRIBE (curates STATE/LEDGER)
- GATE-SMITH (proposes/lands gates)
- DOC-KEEPER (syncs docs/ADRs)
- WATCHDOG (only the cron Action picks this)

Roles are claimed at message-write time, not at session-start. A single
client can rotate roles within a session. The role string in the message
header is what other clients see — they don't see "this is KiloCode" or
"this is Codex". Anonymity is the point — work flows to whoever's free.

---

*Adapter spec v1 — 2026-05-03. New client? Add a section here + a folder
under examples/ + an install target. PR welcome.*
