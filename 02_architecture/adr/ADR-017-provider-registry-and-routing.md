# ADR-017 — Provider registry + routing-mode integration (`local_private` vs `hybrid`)

**Status:** Proposed.
**Date:** 2026-05-03.
**Related:** [ADR-011 LLM planner gateway](ADR-011-llm-planner-gateway.md), [ADR-012 real provider probes](ADR-012-real-provider-probes.md), HermesProof PR `feat/gate-provider-registry`.
**Tracking:** ROADMAP.md "Provider hardening" row; HermesProof task `HP-V0.6-PROVIDER-REGISTRY`.

## Context

Hermes3D's LLM provider abstraction (`03_implementation/src/hermes3d/core/llm/providers.py`)
ships five concrete backends today: Ollama, LM Studio, vLLM, llama.cpp, and OpenRouter.
Selection is via the `HERMES3D_LLM_PROVIDER` env var, and the only fleet-level routing
policy lives implicitly in whichever value the user happens to set.

That implicit policy is fine for a single developer machine but breaks down once we have
two distinct deployment shapes:

1. **Local-private** — privacy-sensitive deployments where no prompts may leave the host.
   The fleet brain must run entirely against LM Studio (default) or Ollama (fallback).
   Cloud providers are forbidden.

2. **Hybrid** — performance-tuned deployments where Claude (or another cloud architect)
   coordinates implementation work, while local providers serve as cheap fallback and
   privacy-budget overflow.

A user-supplied provider-registry pack (`policies/provider-registry/registry.yaml`,
schema `hermes.provider_completeness.v1`) enumerates 62 LLM provider classes from the
Continue project plus 87 local LM Studio model entries — enough to make routing
decisions deterministic instead of guessed.

The pack also requires a sibling `routing.yaml` (schema `hermes.routing.v1`) that
encodes the two modes:

```yaml
schema: hermes.routing.v1
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

## Decision

**Adopt the routing registry as the single source of truth for fleet-level provider
selection.** Hermes3D ships a Python loader at
`03_implementation/src/hermes3d/core/llm/registry_loader.py` that:

- Reads `02_architecture/policies/provider-registry/routing.yaml` via PyYAML.
- Honours the `HERMES3D_ROUTING_MODE` env var (`local_private` | `hybrid`).
- Falls back to **`local_private`** for any unknown value, preserving privacy by default.
- Exposes `get_routing_config(mode=…) -> RoutingConfig` with primary/fallback/
  cloud_allowed/failover_order resolved.
- Maps registry provider names (`minimax`, `deepseek`, `siliconflow`, …) to the existing
  `LLMProvider` enum values via a small lookup table; cloud names funnel through
  `LLMProvider.OPENROUTER` until per-cloud transport classes ship.

`ProviderConfig.from_env` consults the loader **only when `HERMES3D_LLM_PROVIDER` is
unset**. Existing callers that pin the provider explicitly are unaffected.

HermesProof (the MCP lock orchestrator) ships seven companion truth gates that prove
the registry's structural correctness on every push to `main`:

| Gate                                  | Level    | Proves                                                         |
| ------------------------------------- | -------- | -------------------------------------------------------------- |
| `provider.registry.validate`          | required | YAML schema + `class`/`provider_name`/`source_path` per entry  |
| `local.models.catalog.validate`       | required | `lmstudio_local_models.csv` header columns                     |
| `continue.llm_classes.validate`       | required | All 62 expected provider names present                         |
| `kilocode.provider.mapping.validate`  | warn     | Stub gate — `not_applicable` until KiloCode mapping CSV ships  |
| `lmstudio.health`                     | warn     | LM Studio reachable at `LMSTUDIO_BASE_URL`                     |
| `ollama.health`                       | warn     | Ollama reachable at `OLLAMA_BASE_URL`                          |
| `secret.scan`                         | required | Repo scanned for secrets via gitleaks (stdlib regex fallback)  |

## Consequences

### Positive

- **Privacy-by-default.** Unknown `HERMES3D_ROUTING_MODE` values fall back to
  `local_private`, so a misconfigured deployment never leaks prompts to a cloud.
- **One source of truth.** Cloud-routing decisions live in one YAML file, version-
  controlled and gate-validated, not scattered across env-var conventions.
- **Forward-compatible.** Adding a new cloud provider only requires updating
  `PROVIDER_NAME_TO_ENUM` and (eventually) writing a transport class — the routing
  shape stays stable.

### Negative

- **Cloud transport stub.** Cloud providers named in the registry (`minimax`,
  `deepseek`, `siliconflow`) currently funnel through `LLMProvider.OPENROUTER` rather
  than getting their own transport class. This is a stub: prompts go through the
  OpenAI-compat shape but the model name needs to be set explicitly via
  `HERMES3D_LLM_MODEL` for the time being. A follow-up PR (tracking issue: §wiring)
  should add per-cloud transport classes.

- **HermesAgent bridge wiring is a follow-up.** The HermesProof orchestrator's
  agent-bridge failover order (`[lm_studio, ollama]` for `local_private`, six-provider
  cascade for `hybrid`) is **not** wired in this PR. The bridge file does not yet
  exist in either repo; this ADR documents the contract so the next PR can implement
  it without re-arguing the design:

  ```text
  local_private mode  →  failover = [lm_studio, ollama]      # cloud forbidden
  hybrid       mode  →  failover = [
      anthropic/claude,    # architect
      minimax,             # implementation
      deepseek,            # budget_implementation
      siliconflow,         # fallback
      lmstudio,            # local_default
      ollama,              # local_fallback
  ]
  ```

- **YAML dependency.** The loader requires PyYAML (already a Hermes3D dep).

### Neutral

- The registry pack ships as a flat artifact — no live fetch from Continue Hub or
  LM Studio. Live fetching is explicitly deferred (see HermesProof AUDIT.md
  "Not complete / still dynamic").

## Rejected alternatives

1. **Inline routing in `providers.py`.** Considered; rejected because it conflates
   transport with policy and makes the policy untestable in isolation.
2. **Hard-fail on unknown routing mode.** Considered; rejected because it would
   demote privacy-by-default in favour of breaking startup for typos.
3. **Per-cloud transport classes shipped now.** Considered; rejected because each
   cloud has different auth/headers/streaming shapes and the PR would balloon.
   Stubbing through `OPENROUTER` keeps this PR's surface minimal.

## References

- `02_architecture/policies/provider-registry/routing.yaml` (this PR)
- `03_implementation/src/hermes3d/core/llm/registry_loader.py` (this PR)
- `04_testing/pytest/test_registry_loader.py` (this PR — 16 unit tests)
- HermesProof PR `feat/gate-provider-registry` — 7 companion truth gates
- `02_architecture/policies/provider-registry/AUDIT.md` — registry completeness verdict
