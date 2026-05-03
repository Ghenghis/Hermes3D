# Enabling the Hermes Agent — for Claude Code, Codex CLI, and any MCP client

> The Hermes Agent USER bridge is **disabled by default**. Once you've merged
> v0.6 (PR #20) and the registry pack PR, follow this doc to switch it on.
> Both Claude and Codex use the same MCP tools — no per-client configuration
> beyond the standard MCP wiring.

---

## TL;DR — fastest path

```bash
# 1. Put your API keys in G:\private\.env (NEVER inside any repo)
#    Required (one or more): DEEPSEEK_API_KEY, MINIMAX_API_KEY, SILICONFLOW_API_KEY
#    Optional cloud: any of the 62 Continue LLM provider API keys
#    Optional local: LMSTUDIO_BASE_URL, OLLAMA_BASE_URL, HIPFIRE_BASE_URL

# 2. Tell HermesProof where the env file lives (already convention; verify it):
#    HERMES3D_ENV_FILE=G:\private\.env

# 3. Enable the bridge + scope it
export HERMES_AGENT_ENABLED=1
export HERMES_AGENT_PROJECT_GOALS="<one-paragraph project description>"
export HERMES_AGENT_SCOPE="merge_pr,close_blocked,grant_minor_enhancement"
# Optional: pick routing mode
export HERMES3D_ROUTING_MODE=hybrid    # or local_private (cloud forbidden)

# 4. From any MCP client (Claude Code, Codex CLI, KiloCode, Cursor, Windsurf,
#    VSCode+Copilot), call:
hermes_agent_health
# → { ok: true, healthy_provider: "deepseek", model: "deepseek-chat" }

hermes_agent_request_user_session
  requested_scope=["merge_pr","close_blocked"]
  ttl_hours=8
# → { ok: true, session: {...}, rationale: "...", provider_used: "deepseek", model_used: "deepseek-chat" }
```

That's it. From this point, any caller of `hermes_user_check_authorization` against an action in scope will get `{allowed: true, granted_by: "hermes-agent"}` and the Hermes Agent's rationale is recorded in the evidence ledger.

---

## What "enabled" gives you

When the bridge is on:

- **The user can sleep.** Hermes Agent acts as the USER role on STREAM/ messages tagged `BLOCKED`, calling `hermes_agent_resolve_blocked` to emit approve/decline/defer verdicts that close blocking handoffs without waking you.
- **Auto-approval of pre-authorized scope.** Actions in the granted scope (`merge_pr`, `close_blocked`, etc.) pass `hermes_user_check_authorization` immediately; out-of-scope actions still require the human.
- **Provider failover.** DeepSeek → MiniMax → SiliconFlow → LM Studio → Ollama → Hipfire → any of the **62 Continue LLM classes** registered in `policies/provider-registry/registry.yaml` for which you've supplied an API key.
- **Cross-client.** Same MCP tools work from every client; no special Claude or Codex glue.

---

## All providers supported (62 classes via registry)

The Hermes Agent bridge accepts ANY of the 62 Continue LLM provider classes from `policies/provider-registry/registry.yaml`. Per the user's directive: don't exclude any provider.

**Built-in (preferred order, hardcoded for fast-path):**

| # | Provider | env var | endpoint |
|---|---|---|---|
| 1 | DeepSeek (v4) | `DEEPSEEK_API_KEY` | api.deepseek.com |
| 2 | MiniMax highspeed 2.1-2.7 | `MINIMAX_API_KEY` | api.minimaxi.com |
| 3 | SiliconFlow | `SILICONFLOW_API_KEY` | api.siliconflow.cn |
| 4 | LM Studio | `LMSTUDIO_BASE_URL` | localhost:1234 |
| 5 | Ollama | `OLLAMA_BASE_URL` | localhost:11434 |
| 6 | Hipfire (AMD) | `HIPFIRE_BASE_URL` | user-supplied |

**Registry-loaded (the other 56):**

Anthropic, Cohere, OpenAI, Mistral, Groq, Fireworks, Together, OpenRouter, Cerebras, NVidia, Cloudflare, DeepInfra, SambaNova, Nebius, Novita, OVHcloud, Moonshot, Kindo, Venice, xAI, Voyage, Relace, Inception, AskSage, Scaleway, Tensorix, NCompass, zAI, Nous, Gemini, Bedrock, Azure, VertexAI, WatsonX, Replicate, TextGenWebUI, HuggingFaceTGI, HuggingFaceTEI, HuggingFaceInferenceAPI, Llamafile, LlamaCpp, Lemonade, Mimo, BedrockImport, SageMaker, Flowise, ContinueProxy, Docker, Msty, ClawRouter, Vllm, CometAPI, FunctionNetwork, LlamaStack, TARS, MockLLM, TestLLM.

To activate any of them: set the corresponding `*_API_KEY` env var (the bridge derives the name as `<PROVIDER>_API_KEY` upper-snake by default; override via the registry entry's `api_key_env` field).

---

## Routing modes

Two modes documented in `policies/provider-registry/routing.yaml`:

**`local_private` (cloud forbidden, fully air-gapped):**
- default: `lmstudio`
- fallback: `ollama`
- `cloud_allowed: false` — bridge will refuse cloud providers in this mode

**`hybrid` (default):**
- architect: `anthropic/claude` (or whichever you set)
- implementation: `minimax`
- budget_implementation: `deepseek`
- fallback: `siliconflow`
- local_default: `lmstudio`
- local_fallback: `ollama`

Switch with `export HERMES3D_ROUTING_MODE=local_private` (or `hybrid`).

---

## Per-client setup

### Claude Code (CLI + Desktop)

If you've already run `hermesproof init-project` or the wizard, the MCP server is wired. Verify:

```bash
claude mcp list
# Expect: hermes3d-locks  ✓ Connected
```

In any Claude Code session, call:

```
hermes_agent_health()
```

If it returns `{ok: true, ...}`, you're done. Claude Code will call `hermes_user_check_authorization` automatically when it tries an action that needs USER scope.

### Codex CLI

Codex's master prompt now includes the perpetual loop instructions (see `handoffs/HANDOFF_TO_CODEX_PERPETUAL_WAKEUP.md`). Once you point Codex at this repo, it polls `handoffs/STREAM/CODEX_INBOX.md` every 3-5 min. When it encounters a BLOCKED message it can call:

```
hermes_agent_resolve_blocked
  correlation=<id>
  summary=<short>
  full_thread=<verbatim thread>
```

The agent's verdict closes (or defers) the BLOCKED handoff.

### KiloCode

Drop the snippet from `examples/kilocode/streamhooks/rules.toml` into your KiloCode rules. The bridge tools work from KiloCode the same way as from Claude/Codex.

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hermes3d-locks": {
      "command": "node",
      "args": ["G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs"],
      "env": {
        "HERMES_AGENT_ENABLED": "1",
        "HERMES_AGENT_PROJECT_GOALS": "<one paragraph>",
        "HERMES_AGENT_SCOPE": "merge_pr,close_blocked"
      }
    }
  }
}
```

### Windsurf

Add to `mcp_config.json`:

```json
{
  "mcpServers": {
    "hermes3d-locks": {
      "command": "node",
      "args": ["G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs"]
    }
  }
}
```

The env vars are inherited from the shell that launches Windsurf.

### VSCode + GitHub Copilot

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "hermes3d-locks": {
      "type": "stdio",
      "command": "node",
      "args": ["G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs"]
    }
  }
}
```

In `.github/copilot-instructions.md`, add a snippet like:

```
This repo uses the HermesProof MCP server for multi-agent coordination.
Before destructive actions, call hermes_user_check_authorization. If the
user has authorized Hermes Agent (via hermes_agent_request_user_session),
in-scope actions are auto-approved.
```

---

## Disabling the bridge

```bash
unset HERMES_AGENT_ENABLED
# OR explicitly:
export HERMES_AGENT_ENABLED=0
```

The bridge will report `{ok: false, reason: 'bridge disabled'}` from health probes; AS_USER sessions issued by the bridge are still valid until their TTL expires (or you call `hermes_agent_revoke_session`).

---

## Auditing

Every bridge decision is evidenced in `.hermes3d_orchestrator/evidence.ndjson` with:

- `kind: user_session_grant`
- `granted_by: "hermes-agent"`
- `session_id: <opaque>`
- `hash: <sha256 redacted from public reads>`
- (Bridge-side) `provider_used`, `model_used`, `rationale`

To replay or verify:

```bash
hermes_verify_evidence
# → { ok: true, length: N, hash_chain: valid }
```

To revoke a Hermes-Agent-granted session immediately (e.g. you wake up and disagree):

```bash
hermes_user_revoke_session
  session_id=<the bridge session id>
```

Or surrender the bridge's authority entirely:

```bash
hermes_agent_revoke_session
```

---

## Security model summary

- API keys read from env only; never logged, never echoed to evidence
- Capability scope bounds every session (default empty = no auto-approval)
- TTL bounds every session (default 8h, max 48h)
- Session hash redacted from public state reads
- Provider failures fail-closed → defer to human
- Bridge can be disabled / revoked at any time
- All decisions evidenced (provider + model + rationale + hash chain)
- `.gitleaks.toml` blocks accidental commits of any provider key
- `.gitignore` paranoid blocklist for `.env*` variants

See ADR-016 for the full rationale.
