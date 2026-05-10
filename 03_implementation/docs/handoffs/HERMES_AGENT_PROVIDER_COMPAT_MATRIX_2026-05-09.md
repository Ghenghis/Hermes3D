# Hermes Agent Provider Compatibility Matrix — v0.12 vs v0.13 (2026-05-09)

**Author:** Wave 4 P3-5 (`claude-lead-p3-5-providers`)
**Working branch:** `claude/p3-5-provider-compat-matrix` (stacked on `claude/agent-version-registry`)
**Pairs with:** `services/agent_version_registry.py` (Wave 2 P2-1, commit `afd8999`) and the new sibling
`services/agent_version_provider_compat.py` (this PR).

This document is the source of truth for **which LLM providers are reachable on each shipped Hermes Agent
version, what env-var name authorises them, what redaction layer wraps their responses, and where the
import path lives**. Hermes3D call-sites that need to dispatch a provider call to a specific Hermes Agent
version should consult either this doc or the runtime helper
`services.agent_version_provider_compat.providers_for(version)`.

---

## 0. Audience and scope

This matrix has **three distinct lanes** of "provider":

| Lane | Where the code lives | Reachability across Hermes Agent versions |
|---|---|---|
| **A. Hermes3D-side direct probes** | `03_implementation/src/hermes3d/gateways/providers/<name>.py` | Identical on v0.12 and v0.13 — these talk to provider HTTP APIs directly, not through the upstream Hermes Agent. |
| **B. Upstream Hermes-Agent-side LLM providers** | `agent/<name>_adapter.py` and the unified mapping in `agent/models_dev.py` (`PROVIDER_TO_MODELS_DEV`) | Same 33-entry mapping in both v0.12 and v0.13 (verified by `diff` of `models_dev.py:PROVIDER_TO_MODELS_DEV`). v0.13 changes redaction default + adds Tenacity retry; the surface stays stable. |
| **C. Hermes3D-side CLI-runner sandboxes** | `03_implementation/src/hermes3d/services/code_history.py` (`opencode`, `openhands` entries) | Hermes3D-only; not provider-keyed by Hermes Agent version. Documented here for completeness because the parent brief grouped them with providers. |

The compat-matrix code module that ships with this PR (`agent_version_provider_compat.py`) covers only
**Lane A** (the providers that have actual `build_probe_request` adapters in
`hermes3d.gateways.providers`). Lanes B and C are documented narratively; rebuilding their full registries in
Python would duplicate `agent/models_dev.py:PROVIDER_TO_MODELS_DEV` and fight Stripe-style per-version
stability (see §6).

---

## 1. TL;DR matrix — Lane A (Hermes3D direct probes)

| Provider | v0.12 reachable | v0.13 reachable | Module path | API-key env-var name | Redaction layer | Notes |
|---|:-:|:-:|---|---|---|---|
| `minimax` | YES | YES | `hermes3d.gateways.providers.minimax` | `HERMES3D_MINIMAX_API_KEY` (chained: `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY` → `MINIMAX_TOKEN_PLAN_API_KEY` → `HERMES3D_MINIMAX_HIGHSPEED_API_KEY` → `MINIMAX_HIGHSPEED_API_KEY` → policy `api_key_env` → `OPENAI_API_KEY` → `MINIMAX_API_KEY`) | `hermes3d.gateways.redaction.redact_text` (always-on, Hermes3D layer) | Smoke 3 PASS (2026-05-09) — `Authorization: Bearer ***`, `auth-header-present=True`. |
| `deepseek` | YES | YES | `hermes3d.gateways.providers.deepseek` | `HERMES3D_DEEPSEEK_API_KEY` (policy `api_key_env`) | `hermes3d.gateways.redaction.redact_text` (always-on, Hermes3D layer) | Smoke 4 PASS (2026-05-09) — graceful refusal when env unset; PR #145/#148 fix active (RuntimeError without env-var name leak). |

**Why v0.12 == v0.13 for Lane A:** the Hermes3D `gateways/providers/` adapters are entirely Hermes3D code,
not vendored from `hermes-agent`. Switching `HERMES_AGENT_CHECKOUT` between
`G:/Github/hermes-agent-fresh` (v0.12) and `G:/Github/hermes-agent-v013-canary` (v0.13) does NOT change
which `gateways/providers/*.py` modules are importable. The only cross-version effect is on **upstream-side
redaction** (Lane B), which is layered _on top of_ the Hermes3D `redact_text` call and only matters when
Hermes3D dispatches through the upstream agent, not when it probes a provider directly.

---

## 2. TL;DR matrix — Lane B (upstream Hermes-Agent-side providers)

The upstream Hermes Agent ships a unified provider registry in `agent/models_dev.py`. Both v0.12
(`v2026.4.30`) and v0.13 (`v2026.5.7`) register **the same 33 entries** in
`PROVIDER_TO_MODELS_DEV`. Verified by `diff agent/models_dev.py` between the two checkouts: only the
`supports_vision` derivation logic was tightened in v0.13; the provider table is byte-identical.

| Family | v0.12 | v0.13 | Notes |
|---|:-:|:-:|---|
| `anthropic`, `openai`, `openai-codex`, `gemini`, `google`, `xai`, `bedrock` | YES | YES | Native OAuth/API-key adapters in `agent/anthropic_adapter.py`, `agent/codex_responses_adapter.py`, `agent/gemini_native_adapter.py`, `agent/bedrock_adapter.py`. |
| `openrouter`, `ai-gateway`, `huggingface`, `togetherai`, `mistral`, `groq`, `nvidia`, `cohere`, `perplexity`, `fireworks`, `ollama-cloud` | YES | YES | OpenAI-compatible. |
| `minimax`, `minimax-oauth`, `minimax-cn` | YES | YES | Same env (`MINIMAX_API_KEY`, `MINIMAX_CN_API_KEY`) on both. |
| `deepseek` | YES | YES | `DEEPSEEK_API_KEY`. |
| `kimi-coding`, `kimi-coding-cn`, `stepfun`, `alibaba`, `qwen-oauth`, `xiaomi` | YES | YES | China region. |
| `opencode-zen`, `opencode-go`, `kilocode` | YES | YES | Hermes-Agent-internal namespaces; `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY`, `KILOCODE_API_KEY`. **Distinct from Lane C (the OpenCode CLI runner).** |
| `copilot` | YES | YES | OAuth via `COPILOT_GITHUB_TOKEN` / `gh auth token`. |
| `zai` | YES | YES | `GLM_API_KEY` (provider id `zai`). |

**Net change v0.12 → v0.13:** zero providers added/removed. The surface stability follows the Stripe
"monthly release = backward-compatible" pattern (see §6). The user-facing changes that landed in v0.13 are
behavioural (redaction default flip, retry/Tenacity, Kanban, heartbeat-reclaim, zombie-detection,
pluggable-providers-dir scaffold) and these are already enumerated as flags on
`HermesAgentVersion.has_*` in the registry. The provider directory itself is the same.

---

## 3. TL;DR matrix — Lane C (Hermes3D CLI runners)

Not LLM providers. Sandbox-spawned coding/audit binaries. Listed because the brief mentions OpenCode and
OpenHands.

| Runner | Detected via | Binary env vars | Source-pin env vars | Reachable v0.12 | Reachable v0.13 | Smoke ref |
|---|---|---|---|:-:|:-:|---|
| `opencode` | `services.code_history.cli_runner_status("opencode")` | `HERMES3D_OPENCODE_BIN`, `OPENCODE_BIN` | `HERMES3D_OPENCODE_SOURCE`, `OPENCODE_SOURCE` | YES (Hermes3D-side) | YES (Hermes3D-side) | Smoke 5 PASS — `version_tail='1.4.3-hermes3d'`. |
| `openhands` | `services.code_history.cli_runner_status("openhands")` | `HERMES3D_OPENHANDS_BIN`, `OPENHANDS_BIN` | `HERMES3D_OPENHANDS_SOURCE`, `OPENHANDS_SOURCE` | YES (Hermes3D-side) | YES (Hermes3D-side) | Smoke 6 PASS — `version_tail='OpenHands CLI 1.16.0'`; `policy.write_runs_allowed=False` (separate gate, BLK-013). |

These are detected/spawned by Hermes3D itself, not the upstream Hermes Agent, so the
`HERMES_AGENT_CHECKOUT` env switch does not change their reachability.

---

## 4. Per-provider reference (Lane A, the binding source of truth)

### 4.1 MiniMax

| Field | Value |
|---|---|
| File | `03_implementation/src/hermes3d/gateways/providers/minimax.py` |
| `build_probe_request` | line 25, signature `(config: ProviderConfig) -> tuple[str, str, dict[str, str]]` |
| Returns | `(method="GET", url=f"{base_url}/{probe_path}", headers={"Authorization": "Bearer ***", "Accept": "application/json"})` |
| Auth header NAME | `Authorization` (Bearer scheme) |
| Endpoint URL | `https://api.minimax.io/v1/models` (probe), `https://api.minimax.io/v1/chat/completions` (completion) — `03_implementation/config/llm_policy.yaml:19,21` |
| API-key env chain | line 110-118, 7-step: `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY` → `MINIMAX_TOKEN_PLAN_API_KEY` → `HERMES3D_MINIMAX_HIGHSPEED_API_KEY` → `MINIMAX_HIGHSPEED_API_KEY` → policy.api_key_env (`HERMES3D_MINIMAX_API_KEY` per yaml) → `OPENAI_API_KEY` → `MINIMAX_API_KEY`. Squad G fix (PR #145 sibling) — `RuntimeError`, never echoes the env-var name. |
| Redaction default | `redact_text` (Hermes3D, `gateways.redaction`) — always-on, NOT a per-version flag. |
| Cross-version notes | Identical bytes in `gateways/providers/minimax.py` between v0.12 and v0.13 dispatch (because this file is in Hermes3D, not in `hermes-agent`). v0.13 _additionally_ applies upstream `agent/redact.py` redaction-default-on if and only if Hermes3D round-trips through the Agent, which the direct-probe path does not. |
| Smoke result | Smoke 3 PASS (2026-05-09): `MiniMax: config-OK, url=https://api.minimax.io/v1/models, auth-header-present=True`. |

### 4.2 DeepSeek

| Field | Value |
|---|---|
| File | `03_implementation/src/hermes3d/gateways/providers/deepseek.py` |
| `build_probe_request` | line 25, signature `(config: ProviderConfig) -> tuple[str, str, dict[str, str]]` |
| Returns | `(method="GET", url=f"{base_url}/{probe_path}", headers={"Authorization": "Bearer ***", "Accept": "application/json"})` |
| Auth header NAME | `Authorization` (Bearer scheme) |
| Endpoint URL | `https://api.deepseek.com/v1/models` (probe), `https://api.deepseek.com/v1/chat/completions` (completion) — `03_implementation/config/llm_policy.yaml:30,32` |
| API-key env | line 37, single read of `os.environ.get(config.api_key_env)` (resolves to `HERMES3D_DEEPSEEK_API_KEY` via yaml). PR #145/#148 fix active: explicit `RuntimeError` instead of bare `KeyError`, no env-var-name leak. |
| Redaction default | `redact_text` (Hermes3D, `gateways.redaction`) — always-on. |
| Cross-version notes | Identical signature on v0.12 and v0.13 dispatch. v0.13 adds upstream `agent/redact.py` ON-by-default but, again, only matters for round-tripped traffic. |
| Smoke result | Smoke 4 PASS (2026-05-09): graceful-refusal path. |

### 4.3 OpenAI / Anthropic — direct from Hermes3D?

**NOT directly callable from Hermes3D.** No `gateways/providers/anthropic.py` or `gateways/providers/openai.py`
exists. Only `openai-fixture` (a test stub at `gateways/llm.py:98,195`) is referenced. Hermes3D dispatches to
Anthropic / OpenAI **only via the upstream Hermes Agent** (Lane B), which does have full
`agent/anthropic_adapter.py` and the OpenAI/Codex `agent/codex_responses_adapter.py`.

| Field | Value |
|---|---|
| Direct adapter on Hermes3D side | None |
| Reachable via upstream Hermes Agent | YES on both v0.12 and v0.13 |
| Upstream module (v0.12 + v0.13) | `agent/anthropic_adapter.py`, `agent/codex_responses_adapter.py` |
| Auth pattern | OAuth (Claude Max + extra credits), API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), or device-code flow |
| Cross-version diff | `agent/anthropic_adapter.py` differs between v0.12 and v0.13 (`diff` returns "differ") but the public surface (provider id `anthropic`, env vars) is stable. |

### 4.4 Local providers (lm_studio, ollama, hipfire)

| Provider | File | Env | Notes |
|---|---|---|---|
| `lm_studio` | `hermes3d.core.llm.lmstudio_client` (also referenced in `gateways.llm`) | `HERMES3D_NULL_API_KEY` (placeholder; LM Studio doesn't require a key) | Local on-ramp per ADR-015. |
| `ollama` | `hermes3d.core.llm.ollama_client` | none required | Fallback per ADR-015. |
| `hipfire` | `hermes3d.core.llm.providers` (`HipfireProvider`) | `HERMES3D_NULL_API_KEY`, gate via `HERMES3D_AMD_NODE=1` | Refuses to instantiate without `HERMES3D_AMD_NODE=1`. |

These are not in `gateways/providers/` because they don't need the `build_probe_request` shape (they hit
local OpenAI-compatible servers); they're listed in the policy `provider_allowlist` instead. Reachable
identically on v0.12 and v0.13.

---

## 5. Migration callouts (v0.12 → v0.13 behavioural changes that affect provider traffic)

These do not add/remove providers, but they change observable runtime behaviour for any provider call
routed through the upstream Hermes Agent. Hermes3D's direct-probe path (Lane A) is unaffected; the changes
matter only when Hermes3D delegates an LLM call up the chain.

| Change | v0.12 (`v2026.4.30`) | v0.13 (`v2026.5.7`) | Source |
|---|---|---|---|
| Upstream redaction default | OFF — `_REDACT_ENABLED = os.getenv("HERMES_REDACT_SECRETS", "")` | **ON** — `_REDACT_ENABLED = os.getenv("HERMES_REDACT_SECRETS", "true")` per upstream issue #17691 | `agent/redact.py:59-67` (verified by `diff`) |
| `redact_sensitive_text` arity | `(text, *, force=False)` | `(text, *, force=False, code_file=False)` — new `code_file` skip flag for source-code text | `agent/redact.py:308,311` |
| Tenacity retry | not present (manual retry in callers) | **landed** as part of v0.13 "Tenacity Release" — affects upstream provider calls | Registry flag `HermesAgentVersion.has_heartbeat_reclaim=True` on V013 |
| Kanban + zombie detection + pluggable providers dir | `False` | `True` | Registry `HermesAgentVersion.has_kanban`, `has_zombie_detection`, `has_pluggable_providers_dir` |
| 4 new modules in `agent/` | not present | `agent/curator_backup.py`, `agent/i18n.py`, `agent/think_scrubber.py`, `agent/tool_guardrails.py` | `diff <(ls agent/) <(ls agent/)` — none are provider adapters |
| v0.13-only files at root | n/a | `RELEASE_v0.13.0.md`, `README.zh-CN.md`, `docs/`, `locales/` | `diff <(ls v012/) <(ls v013/)` |

The upstream `models_dev.py:PROVIDER_TO_MODELS_DEV` (33 entries) is identical between both checkouts.

---

## 6. Hermes3D-side caller table

Where the Hermes3D codebase imports from `hermes3d.gateways.providers` — these are the call sites that
must be safe across v0.12 and v0.13 dispatch. Because the provider modules live in Hermes3D (not vendored
from `hermes-agent`), all four imports are version-stable.

| Caller | Line | Imports |
|---|---|---|
| `03_implementation/src/hermes3d/gateways/llm.py` | 197 | `from hermes3d.gateways.providers import load_probe_policy` |
| `03_implementation/src/hermes3d/orchestration/supervisor.py` | 454 | `from hermes3d.gateways.providers import load_probe_policy` |
| `03_implementation/src/hermes3d/orchestration/bridge.py` | 115 | `from hermes3d.gateways.providers import load_probe_policy` |
| `03_implementation/src/hermes3d/cli/probe.py` | 15 | `from hermes3d.gateways.providers import deepseek, load_probe_policy, minimax` |

Verified import-stable: none of these reference `agent/*_adapter.py` directly, and none change behaviour
based on `HERMES_AGENT_CHECKOUT`. The Hermes3D code-operator route (`api/routes/code_operator.py`) talks
to the `code_history` service for OpenCode/OpenHands runners (Lane C); it does NOT import any provider
adapter directly.

---

## 7. Stability model (Stripe-versioning analogue)

This matrix follows the Stripe API-versioning stability convention: **major releases may be
backward-incompatible; monthly releases are guaranteed backward-compatible**. v0.12 → v0.13 is a major
upgrade by Hermes Agent's own semver but the **provider directory is unchanged** — the changes are
behavioural (redaction default, retry policy), not structural. From Stripe docs:

> "Each major release includes changes that aren't backward-compatible with previous releases. Each
> monthly release includes only backward-compatible changes."
> — https://docs.stripe.com/api/versioning

Hermes Agent v0.12 → v0.13 is **structurally backward-compatible at the provider layer** (no rows added,
removed, or renamed) and **behaviourally diff** at the redaction layer. Hermes3D's strategy: pin the
provider table per HermesAgentVersion record (`agent_version_provider_compat.COMPAT`) so any future
unannounced upstream rename is caught by the unit tests, not by a runtime AttributeError.

This is the same per-version-pinning strategy Stripe uses for SDK stability: SDK versions pin to the API
version current at SDK release.

---

## 8. Security: API-key env-var hygiene (OWASP A02:2021)

Per OWASP A02:2021 "Cryptographic Failures", section on hardcoded credentials (CWE-259, CWE-321):

> "Keys should be generated cryptographically randomly and stored in memory as byte arrays."
> — https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/

This compat matrix follows three rules accordingly:

1. **Env-var NAMES are public; values never are.** Every `ProviderInfo.env_var_name` in
   `agent_version_provider_compat.COMPAT` is the string name of the env var only (e.g.
   `"HERMES3D_MINIMAX_API_KEY"`). The actual key value is never written to source, doc, log, or test
   fixture. A unit test (`test_no_literal_token_value_in_compat`) regex-checks every entry to enforce
   this.
2. **Naming convention.** Hermes3D-side env vars start with `HERMES3D_` (e.g. `HERMES3D_DEEPSEEK_API_KEY`,
   `HERMES3D_MINIMAX_API_KEY`). MiniMax has fall-through aliases (`MINIMAX_API_KEY`,
   `MINIMAX_HIGHSPEED_API_KEY`, etc.) consumed by `_minimax_api_key()` for backward compatibility with
   pre-Hermes3D operator scripts; these are documented in §4.1 and not the primary canonical name.
3. **Failure path does not echo the env-var name.** Both `minimax.py:122-125` and `deepseek.py:39-42`
   raise `RuntimeError("... API key env variable is unset. Set the configured key in the private env
   file before invoking the probe.")` — _not_ `KeyError(config.api_key_env)`. This was Squad G's PR
   #145/#148 fix. Operators see "configure your env file" instead of "we tried `HERMES3D_DEEPSEEK_API_KEY`",
   matching OWASP's principle of not aiding reconnaissance through error messages.

Secrets, per the workspace convention, live at `G:\private\` outside every repo workspace and are sourced
into the process via `~/.hermes/.env` or equivalent operator tooling — not committed to `.env` files in
the repo.

---

## 9. Sources cited

| # | Citation | Used for |
|---|---|---|
| 1 | OWASP A02:2021 Cryptographic Failures — https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/ | §8 — env-var-NAMES-only convention; `RuntimeError` failure path; test regex enforcement |
| 2 | Stripe API versioning — https://docs.stripe.com/api/versioning | §7 — per-version stability model; SDK-pinning rationale for the immutable `COMPAT` tuple |
| 3 | NousResearch/hermes-agent (upstream repo, v0.12 = `v2026.4.30`, v0.13 = `v2026.5.7`) | §2, §4.3, §5 — `agent/models_dev.py` PROVIDER_TO_MODELS_DEV mapping; `agent/redact.py` default flip |
| 4 | `services/agent_version_registry.py` (Wave 2 P2-1, commit `afd8999`) | The frozen-dataclass record we extend; provides `V012`, `V013`, `KNOWN_VERSIONS`, `active_version()` |
| 5 | `HERMES_AGENT_V013_CANARY_SMOKE_2026-05-09.md` (Smokes 3, 4, 5, 6) | §1, §3, §4.1, §4.2 — observed test results |

---

## 10. Reading this matrix at runtime

Hermes3D code that needs to know "given the active Hermes Agent version, what providers can I dispatch a
probe to?" should:

```python
from hermes3d.services.agent_version_registry import active_version
from hermes3d.services.agent_version_provider_compat import providers_for

v = active_version()      # V012 | V013 | None
if v is None:
    # operator pointed HERMES_AGENT_CHECKOUT at a custom fork; fall back conservatively
    providers = ()
else:
    providers = providers_for(v)   # tuple[ProviderInfo, ...] for that version

# every ProviderInfo has: name, module_path, env_var_name, auth_header,
# endpoint_url, redaction_default_on
```

The `redaction_default_on` field on `ProviderInfo` is **the upstream Hermes Agent's redaction default for
that version**, not Hermes3D's (Hermes3D's `redact_text` is always-on). Hermes3D callers that round-trip
through the agent should treat `redaction_default_on=False` (v0.12) as "wrap with my own redaction layer"
and `redaction_default_on=True` (v0.13) as "upstream already redacted, my layer is defence-in-depth".

---

## 11. What this PR does not do

- Does not modify `services/agent_version_registry.py` (frozen, P2-1).
- Does not vendor or copy any upstream `agent/*_adapter.py` into Hermes3D.
- Does not change `gateways/providers/minimax.py` or `deepseek.py` behaviour — both are read-only here.
- Does not call any provider live in tests; the FS-importability check (`test_module_paths_are_importable_strings`)
  uses a path-existence assertion against the static module tree, not a Python `import`.
- Does not document the **upstream-side** `models_dev.py:PROVIDER_TO_MODELS_DEV` registry in code (would
  duplicate 33 lines of upstream data and rot fast). Lane B is documented narratively in §2 only.
