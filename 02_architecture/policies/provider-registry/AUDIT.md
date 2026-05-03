# Hermes Provider Completeness Audit

## Verdict

The previous KiloCode extraction was **complete for the uploaded KiloCode zip**, but **not complete for the full provider universe** and **not complete for the user's local LM Studio models**.

This updated pack adds:

- KiloCode provider extraction already created earlier: 35 provider docs + 43 provider mappings.
- Continue LLM runtime classes from `llm.zip`: **62** LLM/provider classes.
- LM Studio local models from the uploaded local model list: **87** model entries extracted.

## What is complete now

| Area | Status |
|---|---|
| KiloCode provider docs/nav | Complete for uploaded `kilocode-main (3).zip` |
| KiloCode legacy/API provider mapping | Complete for uploaded `kilocode-main (3).zip` |
| KiloCode hardened routing YAML | Included in earlier pack |
| Continue LLM runtime classes | Complete for uploaded `llm.zip` |
| LM Studio local model catalog | Extracted from uploaded LM Studio model list |
| Continue Hub infinite model catalog | Not included; it is dynamic/remote and should be fetched live if needed |

## Why this matters

KiloCode tells HermesProof which providers KiloCode knows how to present and configure.

Continue `llms/` tells HermesProof which provider adapter classes exist at runtime.

LM Studio local model list tells Hermes3D/HermesProof which local models the user can route to when `local_private` mode is selected.

## Required routing decision

Use this default:

```yaml
local_private:
  default: lmstudio
  fallback: ollama
  cloud_allowed: false

hybrid:
  architect: anthropic/claude
  implementation: minimax
  budget_implementation: deepseek
  fallback: siliconflow
  local_default: lmstudio
  local_fallback: ollama
```

## Top local models to mark as useful

These are useful candidates from the extracted LM Studio list:

- `qwen/qwen2.5-coder-14b` — coding, local default candidate.
- `qwen3-coder-30b-a3b-instruct` — coding, larger local coding route.
- `glm-4.7-flash-uncensored-heretic-neo-code-imatrix-max` — large GLM/code route.
- `qwen3.5-27b-claude-4.6-opus-reasoning-distilled` variants — local reasoning.
- `NousResearch_Nous-Hermes-2-Vision` — Hermes/vision themed local model.
- `qwen2-vl`, `qwen3-vl` variants — vision-capable local routes.

## Files in this pack

- `continue_llm_classes_from_llm_zip.csv`
- `lmstudio_local_models_catalog.csv`
- `hermes_complete_provider_and_local_model_registry.yaml`

## Not complete / still dynamic

The remote Continue Hub may include hundreds of model entries. Do not treat a static extraction as the final global model catalog. HermesProof should implement a live fetch/cache step later:

```text
continue.provider.docs.extract
continue.llm_classes.extract
lmstudio.models.fetch
ollama.models.fetch
openrouter.models.fetch_optional
```
