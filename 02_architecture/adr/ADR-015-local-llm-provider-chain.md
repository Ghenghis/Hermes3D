# ADR-015 — Local LLM provider chain: LM Studio default + Ollama fallback + Hipfire optional

**Status:** Proposed (CP-HERMES3D-LOCAL-LM-STUDIO).
**Date:** 2026-05-03.
**Supersedes:** none. Refines [ADR-011 — LLM planner gateway](ADR-011-llm-planner-gateway.md) and the local-LLM language in `02_architecture/ARCHITECTURE.md`.
**Related modules:**
- `03_implementation/src/hermes3d/core/llm/providers.py` — provider abstraction touched by this ADR.
- `03_implementation/config/llm_policy.yaml` — per-provider policy entries.
- `03_implementation/config/llm_policy.schema.json` — schema being relaxed.

## Context

Hermes3D-OS ships a provider-agnostic LLM abstraction (`hermes3d.core.llm.providers`) that already speaks five backends: `ollama`, `lmstudio`, `vllm`, `llamacpp`, and `openrouter` (paid). Until now the documented and code-level default has been **Ollama**, which has two well-understood costs in practice:

1. **First-run friction.** New users pull the codebase, set `HERMES3D_LLM_PROVIDER=ollama`, then have to install Ollama, run `ollama pull <model>`, and remember to start the daemon. The error "Ollama unreachable at 127.0.0.1:11434" is the most common opening complaint from operators.
2. **Tool-calling parity.** LM Studio's OpenAI-compat surface (at `:1234/v1`) handles tool-calling and streaming with the exact same shape Hermes3D uses elsewhere (`_OpenAICompatProvider`), so making it the default removes one provider-specific code path.

We also have a second, narrower problem: the AMD inference workstation in the lab runs an on-box helper called **Hipfire** at `:11435/v1`. We want it usable when explicitly enabled, but never the default — a stray `HERMES3D_LLM_PROVIDER=hipfire` on a developer laptop must not silently route traffic to a port that won't answer.

Finally, the LLM-gateway policy schema currently requires `^https://` for `base_url`. That makes it impossible to add a `lm_studio` or `hipfire` provider entry to `llm_policy.yaml` (both run on `http://127.0.0.1`), so the gateway can't probe them, can't cost-cap them, and can't appear in the existing `provider_allowlist` plumbing.

## Decision

### 1. LM Studio is the default local provider

`ProviderConfig.from_env()` now defaults `HERMES3D_LLM_PROVIDER` to `lmstudio` (was `ollama`). Every existing user-set `HERMES3D_LLM_PROVIDER=...` keeps working — only the unset case changes. The provider's base URL stays `http://127.0.0.1:1234/v1` (LM Studio's stock port).

Ollama remains a first-class fallback. Callers that need redundancy use the existing `select_provider()` with an explicit `LLMProvider.OLLAMA` config; `OllamaProvider` is unchanged.

### 2. Hipfire is added as an opt-in provider

A new `HipfireProvider` class (subclass of `_OpenAICompatProvider`) is added to `providers.py` plus `LLMProvider.HIPFIRE` and an entry in `_PROVIDER_REGISTRY`. Construction refuses with `ProviderUnavailable` unless `os.environ.get("HERMES3D_AMD_NODE") == "1"`. This guard is at instantiation time, so even if a user pastes `provider: hipfire` into a config or runs `select_provider(LLMProvider.HIPFIRE)`, it fails fast on a non-AMD host.

### 3. The policy schema is relaxed for LAN-private URLs

`llm_policy.schema.json` `providerConfig.base_url.pattern` is changed from `^https://` to:

```
^(https://|http://(localhost|127\.0\.0\.1|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.))
```

This continues to require HTTPS for any non-LAN host (so a config typo to `http://api.openai.com` is still rejected) but permits the loopback + RFC1918 ranges that on-box providers use.

The `providers` object's `additionalProperties` flips to `true` so future local backends (vllm, llamacpp, ollama mirrors) don't require a schema migration. `lm_studio` and `hipfire` are explicitly listed in `properties` for documentation + IDE-completion value.

### 4. The policy YAML adds local entries (no replacements)

`llm_policy.yaml` keeps `default_mode`, `provider_allowlist`, and the existing `minimax` + `deepseek` blocks intact. Two entries are appended:

- `lm_studio` — `http://127.0.0.1:1234/v1`, `api_key_env: HERMES3D_NULL_API_KEY` (placeholder, no secret stored).
- `hipfire` — `http://127.0.0.1:11435/v1`, same key convention. Reachable only with `HERMES3D_AMD_NODE=1`.

`provider_allowlist` is updated to `[openai-fixture, lm_studio, ollama, hipfire]`.

### 5. LM Studio's existing class is documented + extended (no rewrite)

`LMStudioProvider` already inherited `/v1/models` health and `/v1/chat/completions` POST from `_OpenAICompatProvider`. We add two helpers in-place — `stream(prompt) -> Iterator[str]` for SSE-style chunks and `chat_with_tools(messages, tools)` for OpenAI-compat tool calling — so agentic modules that need a richer surface stop having to special-case the default provider.

## Consequences

**Positive.**
- Clean first-run: install LM Studio, click "Load model", run Hermes3D. No CLI gymnastics.
- Tool-calling and streaming flow through the same code path the cloud providers already use; one fewer provider-specific branch in agent code.
- Hipfire is deployable in the lab without becoming a foot-gun on developer machines.
- The schema can host any future local provider without further migrations.

**Negative.**
- Operators with an existing `HERMES3D_LLM_PROVIDER` unset and a running Ollama instance will get an LM Studio target after upgrade. Mitigation: the env var is one line in `.env`. Documented in the v5.2 changelog.
- One existing unit test (`test_llm_provider_config_from_env_defaults`) had to be updated to assert the new default; an Ollama-default sibling test was added so the fallback contract stays explicit.

**Neutral.**
- The schema relax only widens what's accepted; no previously-valid policy file becomes invalid.

## Rollback

Revert this PR. `providers.py`, `llm_policy.yaml`, and `llm_policy.schema.json` are the only files with semantic changes; the new `HipfireProvider` class is additive and removing it does not affect any existing call site.

## Compatibility

- Schema is **strictly more permissive** for `base_url` and `providers.*`. Old policy files validate unchanged.
- `LLMProvider` enum gains one variant (`HIPFIRE`); existing literal usages of the other variants are unaffected (Python enums tolerate additions).
- The default-provider change is **observable but non-breaking** — every caller that explicitly sets `HERMES3D_LLM_PROVIDER` keeps the provider it had.

## Test plan

- `pytest 04_testing/pytest/unit/test_second_wave_modules.py` — updated default test passes; new Ollama-fallback test passes.
- `pytest 04_testing/pytest/integration/test_hipfire_provider.py` — new file covers (a) refuses without env gate, (b) refuses on `0`/`true`, (c) constructs on `1`, (d) `select_provider()` honors the gate, (e) health probe hits `/v1/models`, (f) generate POSTs to `/chat/completions` and unwraps the content.
- `python -c "import yaml,jsonschema,json; ..."` — `llm_policy.yaml` validates against the relaxed schema.

## References

- `03_implementation/src/hermes3d/core/llm/providers.py` — `LLMProvider`, `ProviderConfig`, `LMStudioProvider`, new `HipfireProvider`.
- `03_implementation/src/hermes3d/gateways/llm.py` — `load_policy()` + `PolicyValidationError` consume the relaxed schema.
- LM Studio OpenAI-compat docs: `https://lmstudio.ai/docs/api/openai-api`.
- Ollama API docs: `https://github.com/ollama/ollama/blob/main/docs/api.md`.
- **Recommended model for fresh installs:** `NousResearch/Hermes-4-14B-FP8` (active May 2026; MIT-licensed code). Weights inherit the Llama 3.1 Community License which permits commercial use under the 700M-MAU cap. Operators above that threshold should consult the model card before locking the license language for downstream deployment.

## Section 8 — Author + status notes

Authored by the LM Studio default provider task (CP-HERMES3D-LOCAL-LM-STUDIO). Hermes evidence chain: PASS expected post-merge. Promotion to "Accepted" follows a green CI run on `develop` plus a smoke run of `python -m hermes3d.cli.doctor` against a live LM Studio instance. Until then this ADR remains "Proposed" so a reviewer can challenge any of §1-§4 without rolling back code that has already shipped.
