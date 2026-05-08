# _research

## Purpose

`G:\Github\_research\` is a Hermes3D OS research scratchpad. As of 2026-05-07 it contains a single embedded checkout: **`atomic-hermes/`** — a clone of `NousResearch/hermes-agent` (rebranded "Atomic Hermes" by AtomicBot-ai). It is used as a reference implementation for H3D OS work: the agent loop, gateway adapters, plugin/skill systems, ACP/MCP wiring, cron/routine scheduling, desktop Electron shell, and OCR-augmented computer-use are all documented and shippable in this checkout.

Scope inferred from observed file types:
- Python agent core (`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, `hermes_state.py`)
- Electron/macOS desktop shell (`desktop/`)
- React + Vite web admin (`web/`)
- Docusaurus website (`website/`)
- 17+ messaging gateway platform adapters (`gateway/platforms/`)
- 25+ skill domains and a plugin system (`skills/`, `plugins/`)
- ACP (Agent Connect Protocol) adapter + registry (`acp_adapter/`, `acp_registry/`)
- MCP server wiring (`mcp_serve.py`)
- Cron/scheduler (`cron/`)
- 11 release notes covering v0.2.0 → v0.11.0

Top-level state: **not a git repo at `_research/`** (no `.git`); the embedded `atomic-hermes/` IS a git repo (last commit `d733232 hermes-desktop: release v0.1.36`). The parent scratchpad is unversioned, expected to be append-only.

## File inventory — top level of `_research/`

| Entry | Type | LastWrite | Notes |
|---|---|---|---|
| `atomic-hermes/` | dir | 2026-05-06 13:20 | Cloned `NousResearch/hermes-agent` (rebranded build) |

(The parent folder has only this one subdirectory.)

## File inventory — top level of `_research/atomic-hermes/`

### Markdown / docs

| File | Size | One-line summary |
|---|---|---|
| `README.md` | 16 KB | Atomic Hermes pitch — desktop AI agent with chat/files/terminal/computer-use/dashboard, native OCR, 16+ messengers |
| `AGENTS.md` | 34 KB | Dev guide for AI coding assistants — env, structure, file-by-file load-bearing entry points |
| `CONTRIBUTING.md` | 27 KB | Contribution priorities (bugs > x-platform > security > skills); skill-vs-tool decision tree |
| `SECURITY.md` | 7 KB | NousResearch trust model, GHSA reporting, single-tenant assumption, approval system |
| `hermes-already-has-routines.md` | 6 KB | Marketing piece — Hermes shipped scheduled/webhook/API triggers before Anthropic's "Routines" |
| `RELEASE_v0.2.0.md` … `v0.11.0.md` | ~30–46 KB ea. | Per-version release notes (v0.2.0 → v0.11.0) |

### Code / config

| File | Notes |
|---|---|
| `cli.py` (509 KB), `run_agent.py` (640 KB) | Monolithic agent + CLI entrypoints (~12k / ~11k LOC each) |
| `mcp_serve.py` (32 KB) | MCP server exposing Hermes tools |
| `batch_runner.py`, `mini_swe_runner.py`, `rl_cli.py` | Parallel batch / SWE / RL runners |
| `model_tools.py`, `toolsets.py`, `toolset_distributions.py` | Tool orchestration + toolset definitions |
| `hermes_state.py` | SQLite SessionDB with FTS5 search |
| `hermes_constants.py`, `hermes_logging.py`, `hermes_time.py` | Profile-aware paths, logging, time |
| `trajectory_compressor.py` (67 KB) | Session/trajectory compression |
| `setup-hermes.sh`, `hermes` | Installer + launcher |
| `Dockerfile`, `flake.nix`, `flake.lock`, `pyproject.toml`, `package.json`, `uv.lock` | Build/dist (Docker, Nix flake, Python+Node) |
| `.env.example` (19 KB) | Comprehensive env template |
| `cli-config.yaml.example` (50 KB) | Reference YAML config |

### Subdirectories

| Dir | Purpose |
|---|---|
| `agent/` | Provider transports (anthropic/bedrock/codex/gemini/google), context engine, memory, OAuth, rate-guard |
| `gateway/` | Messaging gateway runtime + 17+ platform adapters in `gateway/platforms/` |
| `tools/` | Tool implementations (browser, file, terminal, image-gen, feishu, discord, homeassistant, …) plus `environments/` for terminal backends (local/docker/ssh/modal/daytona/singularity) |
| `skills/` | 25+ skill domains: apple, autonomous-ai-agents, creative, data-science, devops, diagramming, email, feeds, gaming, gifs, github, mcp, media, mlops, note-taking, productivity, red-teaming, research, smart-home, social-media, software-development, … |
| `optional-skills/` | Heavier/niche skills (opt-in) |
| `plugins/` | Plugin system: `memory/`, `context_engine/`, `image_gen/`, `disk-cleanup/`, `example-dashboard/`, `strike-freedom-cockpit/` |
| `hermes_cli/` | CLI subcommands, auth providers, setup wizard, plugins loader, skin engine |
| `acp_adapter/` | Agent Connect Protocol adapter (entry, server, session, tools, permissions, events) |
| `acp_registry/` | ACP `agent.json` + icon |
| `cron/` | Scheduler + jobs |
| `desktop/` | Electron 33 macOS app (renderer, src, tests, entitlements) |
| `web/` | React+Vite admin SPA |
| `website/` | Docusaurus marketing/docs site |
| `tinker-atropos/` | (empty/placeholder) — likely RL "tinker"+"atropos" experiments |
| `.github/` | CI workflows, issue templates |

## Topic categories

### 1. Agent core / runtime (Python)
`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, `hermes_state.py`, `hermes_constants.py`, `hermes_logging.py`, `hermes_time.py`, `agent/`, `trajectory_compressor.py`, `utils.py`, `mini_swe_runner.py`, `batch_runner.py`, `rl_cli.py`. (~13 files + 1 dir)

### 2. Provider / inference adapters
`agent/anthropic_adapter.py`, `agent/bedrock_adapter.py`, `agent/codex_responses_adapter.py`, `agent/gemini_cloudcode_adapter.py`, `agent/gemini_native_adapter.py`, `agent/google_code_assist.py`, `agent/google_oauth.py`, `agent/credential_pool.py`, `agent/nous_rate_guard.py`, `agent/models_dev.py`. (~10 files)

### 3. Tools (capabilities)
`tools/` (~30 files): browser_camofox/cdp, approval, file_operations, file_tools, code_execution_tool, delegate_tool, discord_tool, feishu_*, homeassistant_tool, image_generation_tool, cronjob_tools, environments/. (30+ files)

### 4. Messaging gateway / platforms
`gateway/run.py`, `session.py`, `delivery.py`, `mirror.py`, `pairing.py`, `restart.py`, `sticker_cache.py`, `stream_consumer.py`, `platforms/` (17+ adapters: telegram, discord, slack, whatsapp, homeassistant, signal, matrix, mattermost, email, sms, dingtalk, wecom, weixin, feishu, qqbot, bluebubbles, webhook, api_server). (~25 files)

### 5. Skills (instruction-driven capabilities)
`skills/` 25 domains incl. autonomous-ai-agents, mcp, red-teaming, research, software-development, smart-home, gaming, gifs, mlops, devops, github, …; plus `optional-skills/`.

### 6. Plugins / extensibility
`plugins/memory/`, `plugins/context_engine/`, `plugins/image_gen/`, `plugins/disk-cleanup/`, `plugins/example-dashboard/`, `plugins/strike-freedom-cockpit/`. (6 plugin subtrees)

### 7. Protocols / interop
`mcp_serve.py` (MCP server), `acp_adapter/` (ACP adapter, 9 files), `acp_registry/` (agent.json + icon).

### 8. Scheduler / automation
`cron/jobs.py`, `cron/scheduler.py`, `hermes-already-has-routines.md` (cron + webhook + API triggers).

### 9. Desktop / GUI
`desktop/` (Electron 33 macOS), `web/` (React+Vite admin), `website/` (Docusaurus). (3 dirs)

### 10. CLI / UX
`hermes_cli/` (~20 files: commands, auth, banner, callbacks, claw, completion, config, curses_ui, default_soul, dingtalk_auth, …).

### 11. Build / packaging / governance
`Dockerfile`, `flake.nix`, `pyproject.toml`, `package.json`, `uv.lock`, `MANIFEST.in`, `.env.example`, `cli-config.yaml.example`, `.github/`, `LICENSE` (PolyForm NC), `SECURITY.md`, `CONTRIBUTING.md`, `.mailmap`.

### 12. Release history / docs
11 `RELEASE_v*.md` files (v0.2.0 → v0.11.0), `README.md`, `AGENTS.md`, `docs/api-extensions.md`.

## Notable references found in the markdowns

- **NousResearch/hermes-agent** — upstream repo (per `SECURITY.md`, `RELEASE_v0.11.0.md` PR links)
- **AtomicBot-ai/atomic-hermes** — fork/rebrand publishing macOS releases (per `README.md` badge URLs)
- **Anthropic Claude Code Routines** — referenced and contrasted in `hermes-already-has-routines.md`
- **AWS Bedrock Converse API** — native transport in v0.11.0
- **NVIDIA NIM, Arcee AI, Step Plan, Google Gemini CLI OAuth, Vercel ai-gateway** — five new inference paths in v0.11.0
- **OpenAI Codex OAuth / GPT-5.5** — model auth path
- **Apple Vision OCR / Windows.Media.Ocr** — native OCR for computer-use
- **PolyForm Noncommercial 1.0.0** — license
- **Electron 33, Node 18+, Python (uv)** — runtime stack
- **Honcho, Mem0, Supermemory** — memory plugins
- **Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost, Email/SMS, DingTalk, WeCom, Weixin, Feishu, QQBot, BlueBubbles, HomeAssistant, Webhook, API server** — gateway platforms
- **Docker, Modal, Daytona, Singularity, SSH** — terminal-environment backends
- **Ink (React for terminal)** — `hermes --tui`
- **Docusaurus** — `website/`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 500" width="700" height="500" font-family="Segoe UI, Arial, sans-serif" font-size="11">
  <rect x="0" y="0" width="700" height="500" fill="#0f1419"/>
  <text x="350" y="22" text-anchor="middle" fill="#e6e6e6" font-size="16" font-weight="bold">_research/atomic-hermes — topic categories</text>
  <text x="350" y="40" text-anchor="middle" fill="#9aa0a6" font-size="11">single embedded checkout · NousResearch/hermes-agent · 12 topic clusters</text>

  <!-- Row 1 -->
  <g>
    <rect x="20" y="60" width="155" height="70" rx="6" fill="#1f3a5f" stroke="#4a90e2"/>
    <text x="97" y="80" text-anchor="middle" fill="#fff" font-weight="bold">Agent core</text>
    <text x="97" y="98" text-anchor="middle" fill="#cfd8e3">runtime + state</text>
    <text x="97" y="118" text-anchor="middle" fill="#9bd1ff">~13 files + agent/</text>
  </g>
  <g>
    <rect x="185" y="60" width="155" height="70" rx="6" fill="#1f3a5f" stroke="#4a90e2"/>
    <text x="262" y="80" text-anchor="middle" fill="#fff" font-weight="bold">Provider adapters</text>
    <text x="262" y="98" text-anchor="middle" fill="#cfd8e3">anthropic/bedrock/gemini</text>
    <text x="262" y="118" text-anchor="middle" fill="#9bd1ff">~10 files</text>
  </g>
  <g>
    <rect x="350" y="60" width="155" height="70" rx="6" fill="#3f1f5f" stroke="#a06bd6"/>
    <text x="427" y="80" text-anchor="middle" fill="#fff" font-weight="bold">Tools</text>
    <text x="427" y="98" text-anchor="middle" fill="#e7d6f5">browser/file/exec/env</text>
    <text x="427" y="118" text-anchor="middle" fill="#d2a9ff">30+ files</text>
  </g>
  <g>
    <rect x="515" y="60" width="155" height="70" rx="6" fill="#3f1f5f" stroke="#a06bd6"/>
    <text x="592" y="80" text-anchor="middle" fill="#fff" font-weight="bold">Gateway / platforms</text>
    <text x="592" y="98" text-anchor="middle" fill="#e7d6f5">17+ messengers</text>
    <text x="592" y="118" text-anchor="middle" fill="#d2a9ff">~25 files</text>
  </g>

  <!-- Row 2 -->
  <g>
    <rect x="20" y="150" width="155" height="70" rx="6" fill="#1f5f3a" stroke="#4ade80"/>
    <text x="97" y="170" text-anchor="middle" fill="#fff" font-weight="bold">Skills</text>
    <text x="97" y="188" text-anchor="middle" fill="#d6f5e0">25 domain dirs</text>
    <text x="97" y="208" text-anchor="middle" fill="#a8f0c0">+ optional-skills/</text>
  </g>
  <g>
    <rect x="185" y="150" width="155" height="70" rx="6" fill="#1f5f3a" stroke="#4ade80"/>
    <text x="262" y="170" text-anchor="middle" fill="#fff" font-weight="bold">Plugins</text>
    <text x="262" y="188" text-anchor="middle" fill="#d6f5e0">memory/ctx/image_gen…</text>
    <text x="262" y="208" text-anchor="middle" fill="#a8f0c0">6 subtrees</text>
  </g>
  <g>
    <rect x="350" y="150" width="155" height="70" rx="6" fill="#5f3a1f" stroke="#f5a35a"/>
    <text x="427" y="170" text-anchor="middle" fill="#fff" font-weight="bold">Protocols</text>
    <text x="427" y="188" text-anchor="middle" fill="#f5e0d0">MCP + ACP</text>
    <text x="427" y="208" text-anchor="middle" fill="#ffcc99">mcp_serve + acp_*/</text>
  </g>
  <g>
    <rect x="515" y="150" width="155" height="70" rx="6" fill="#5f3a1f" stroke="#f5a35a"/>
    <text x="592" y="170" text-anchor="middle" fill="#fff" font-weight="bold">Scheduler</text>
    <text x="592" y="188" text-anchor="middle" fill="#f5e0d0">cron + routines</text>
    <text x="592" y="208" text-anchor="middle" fill="#ffcc99">cron/ + .md</text>
  </g>

  <!-- Row 3 -->
  <g>
    <rect x="20" y="240" width="155" height="70" rx="6" fill="#5f1f3a" stroke="#e25a8c"/>
    <text x="97" y="260" text-anchor="middle" fill="#fff" font-weight="bold">Desktop / GUI</text>
    <text x="97" y="278" text-anchor="middle" fill="#f5d6e0">Electron + React + Docu</text>
    <text x="97" y="298" text-anchor="middle" fill="#ffaad4">3 dirs</text>
  </g>
  <g>
    <rect x="185" y="240" width="155" height="70" rx="6" fill="#5f1f3a" stroke="#e25a8c"/>
    <text x="262" y="260" text-anchor="middle" fill="#fff" font-weight="bold">CLI / UX</text>
    <text x="262" y="278" text-anchor="middle" fill="#f5d6e0">hermes_cli/</text>
    <text x="262" y="298" text-anchor="middle" fill="#ffaad4">~20 files</text>
  </g>
  <g>
    <rect x="350" y="240" width="155" height="70" rx="6" fill="#3a3a3a" stroke="#bdbdbd"/>
    <text x="427" y="260" text-anchor="middle" fill="#fff" font-weight="bold">Build / packaging</text>
    <text x="427" y="278" text-anchor="middle" fill="#dddddd">Docker/Nix/uv/PolyForm</text>
    <text x="427" y="298" text-anchor="middle" fill="#cccccc">~10 files</text>
  </g>
  <g>
    <rect x="515" y="240" width="155" height="70" rx="6" fill="#3a3a3a" stroke="#bdbdbd"/>
    <text x="592" y="260" text-anchor="middle" fill="#fff" font-weight="bold">Releases / docs</text>
    <text x="592" y="278" text-anchor="middle" fill="#dddddd">v0.2 → v0.11</text>
    <text x="592" y="298" text-anchor="middle" fill="#cccccc">11 release .md</text>
  </g>

  <!-- Bottom band -->
  <g>
    <rect x="20" y="335" width="650" height="60" rx="6" fill="#102030" stroke="#4a90e2"/>
    <text x="345" y="358" text-anchor="middle" fill="#fff" font-weight="bold">Single embedded git repo · last commit d733232 (hermes-desktop v0.1.36)</text>
    <text x="345" y="378" text-anchor="middle" fill="#9bd1ff">parent _research/ is NOT a git repo · scratchpad / append-only</text>
  </g>

  <!-- Legend -->
  <g font-size="10">
    <rect x="20" y="415" width="14" height="14" fill="#1f3a5f" stroke="#4a90e2"/><text x="40" y="426" fill="#cfd8e3">Runtime</text>
    <rect x="100" y="415" width="14" height="14" fill="#3f1f5f" stroke="#a06bd6"/><text x="120" y="426" fill="#e7d6f5">Capabilities</text>
    <rect x="200" y="415" width="14" height="14" fill="#1f5f3a" stroke="#4ade80"/><text x="220" y="426" fill="#d6f5e0">Extensibility</text>
    <rect x="305" y="415" width="14" height="14" fill="#5f3a1f" stroke="#f5a35a"/><text x="325" y="426" fill="#f5e0d0">Interop</text>
    <rect x="380" y="415" width="14" height="14" fill="#5f1f3a" stroke="#e25a8c"/><text x="400" y="426" fill="#f5d6e0">Frontends</text>
    <rect x="465" y="415" width="14" height="14" fill="#3a3a3a" stroke="#bdbdbd"/><text x="485" y="426" fill="#dddddd">Ops / docs</text>
  </g>

  <text x="350" y="475" text-anchor="middle" fill="#6a737d" font-size="10">indexed 2026-05-07 · 1 top-level dir · ~70 top-level files in atomic-hermes/</text>
</svg>
```

## Index notes for H3D OS work

- **Drop-in references** for H3D OS: `mcp_serve.py` (MCP server pattern), `acp_adapter/` (ACP), `gateway/platforms/` (any messenger), `cron/` (scheduling), `tools/environments/` (sandboxed terminal backends), `agent/transports/` (provider abstraction).
- **Skill model**: instruction-driven, `skills/<domain>/DESCRIPTION.md` shape — usable as a pattern for H3D agent skill loading.
- **Computer-use OCR**: native Apple Vision / Windows.Media.Ocr — directly relevant to H3D OS Action Window pixel-accuracy work.
- **License** is **PolyForm Noncommercial 1.0.0** — copy patterns, do not vendor code into a commercial H3D distribution without a separate license review.
