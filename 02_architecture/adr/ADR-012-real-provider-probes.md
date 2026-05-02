# ADR-012: Real Provider Probes — Bounded Provider Adapter Surface, Probe-First Invariant, Per-Provider Budget Caps, Refusal Rules R9 + R10

## Status
Proposed (Phase 3.4, 2026-05-02). Will become Accepted on CP3.4-A merge.

## Context
ADR-011 shipped the bounded LLM gateway for Phase 3.3: a single gateway, fixture-only callers by default, deterministic template fallback, redaction, sanitizer, and budget enforcement. That baseline deliberately avoided provider probes and real-provider routing so the LLM surface could be proven before any real host entered the system.

The remaining operational gap is narrow but important: Hermes3D cannot tell whether a configured real provider is reachable, authenticated, and returning a shape we can safely normalize without making a bounded call. Phase 3.3 explicitly deferred "Real 3D provider probes" and "Real 3D provider gateway" to a later phase; this ADR keeps that deferral for 3D providers and scopes Phase 3.4 only to LLM provider probes for MiniMax (primary) and DeepSeek (secondary).

Phase 3.4 therefore extends the ADR-011 gateway pattern with a probe-first invariant. Real LLM completion may be permitted only after a successful recent probe for the configured provider. Users who do nothing keep the Phase 3.3 default behavior: `default_mode: template`, fixture path available, deterministic fallback intact, and no automatic provider calls.

## Decision

### 1. ProviderProbeGateway contract
A single class exposes one provider-probe method:

```python
ProviderProbeGateway.probe(
    provider_id: str,
    *,
    token: CapabilityToken,
    budget: BudgetState,
) -> Result[ProviderProbeResult]
```

- Refusal rules R1-R5 from ADR-009 are evaluated first.
- The token must declare `tools ⊇ {"provider.probe"}`.
- `provider_id` must be a key in `policy.providers`.
- The per-provider rate cap and per-day probe budget are enforced before the request leaves the process.
- The probe performs the smallest authenticated request that confirms liveness, for example `GET <base_url><probe_path>`.
- The gateway records one `provider.probe` ledger event containing provider id, latency in milliseconds, HTTP status, and sha256 of a redacted response excerpt.
- Raw response bodies, response headers, and authorization headers are never persisted.
- Failures are normalized to `Err` values and redacted before ledger or bundle evidence is written.

### 2. Per-provider config
Provider configuration is validated by `03_implementation/config/llm_policy.schema.json` and is optional in Phase 3.4. The schema adds:

```yaml
providers:
  minimax:
    base_url: https://...
    probe_path: /...
    completion_path: /...
    api_key_env: HERMES3D_MINIMAX_API_KEY
    cost_cap_usd_per_run: 0.05
    cost_cap_usd_per_day: 1.00
  deepseek:
    base_url: https://...
    probe_path: /...
    completion_path: /...
    api_key_env: HERMES3D_DEEPSEEK_API_KEY
```

`api_key_env` names the environment variable. The key value itself never appears in YAML, source, fixtures, ledger rows, logs, or proof bundles. `providers.additionalProperties: false` keeps the provider set closed to MiniMax and DeepSeek until a later ADR explicitly expands it.

### 3. Provider adapter contract
Each provider adapter file under `03_implementation/src/hermes3d/gateways/providers/` exposes:

- `probe_caller(config)` — returns a bounded callable used by `ProviderProbeGateway`.
- `completion_caller(config)` — returns a bounded callable used by `LLMGateway` after probe freshness has been proven.

Adapters normalize provider-specific request and response shapes into Hermes3D DTOs. Adapters are the **only** new files allowed to import `httpx`. This extends ADR-011's path-restricted LLM-import rule: provider networking remains inside the gateway/provider boundary and cannot drift into planners, agents, supervisors, UI code, or tests that are not explicit fixtures.

### 4. Refusal rule R9 — provider not probe-verified
**Trigger:** `llm.complete` is attempted for a configured real provider that has no successful `provider.probe` ledger row newer than `probe_freshness_minutes`.

**Outcome:**
- `LLMGateway.complete` returns `Err::Forbidden("provider_not_probed")`.
- The planner falls back to the deterministic template path per ADR-011 §5.
- The ledger writes `planner.fallback("provider_not_probed")`.
- The fixture provider id `openai-fixture` is exempt because it is not a real network provider.

### 5. Refusal rule R10 — probe budget exhausted
**Trigger:** a `provider.probe` call would exceed `probe_budget_usd_per_day` or the per-provider probe rate cap.

**Outcome:**
- `ProviderProbeGateway.probe` returns `Err::Forbidden("probe_budget_exceeded")`.
- The ledger writes `budget.exceeded` with `tool="provider.probe"` and a message naming the cap that fired.
- Probe failures count against the probe budget because degraded providers can otherwise produce unbounded repeated attempts.

### 6. API key handling
Provider API keys are read **only** from environment variables named by policy, such as `HERMES3D_MINIMAX_API_KEY` and `HERMES3D_DEEPSEEK_API_KEY`.

Keys are never read from disk, settings, UI, or git. They are never logged, ledgered, or bundled. The redactor from ADR-011 §4 masks `Bearer <key>` headers, API-key-shaped values, and known secret prefixes before any evidence leaves the gateway boundary. If the required environment variable is unset, the probe gateway returns `Err::ApiKeyMissing(...)`; any dependent planner path falls back to the template plan.

### 7. Path-restriction extension
ADR-011 restricted LLM SDK and HTTP imports to `gateways/llm.py`. Phase 3.4 extends that rule:

- `import httpx` is allowed in `03_implementation/src/hermes3d/gateways/llm.py`.
- `import httpx` is allowed in `03_implementation/src/hermes3d/gateways/providers/*.py`.
- `openai`, `anthropic`, `google.generativeai`, `requests`, and `urllib.request.urlopen` remain refused outside the explicitly allowed gateway/provider paths.
- Any networking import in planners, agents, supervisors, bridge code, UI code, CLI code outside the probe command boundary, or adapters fails Layer A.

### 8. Probe-first invariant for completion
`LLMGateway.complete` refuses with R9 when the configured real provider has no recent successful probe row. The gateway checks ledger freshness before invoking the provider completion caller. `probe_freshness_minutes` defines the maximum acceptable age.

The fixture provider id `openai-fixture` is exempt and continues to power the Phase 3.3 deterministic tests. Default policy remains `default_mode: template`; real-provider opt-in requires a distinct future flag and operator configuration. Phase 3.4 does not auto-route existing users to real providers.

### 9. Out of scope
- 3D providers (TRELLIS, Hunyuan3D, TripoSR, MiniMax 3D) — Phase 3.5+.
- Default real-provider routing — operator-opt-in only.
- Streaming, function-calling, and tool-use modes.
- Multi-provider routing or fallback chains.
- UI editing of provider configuration.
- Phase 4 write capabilities.

## Rationale
- The single-entry-point gateway pattern prevents provider SDK smuggling and preserves the auditability established by ADR-011.
- The probe-first invariant prevents first-call surprise: authentication failures, rate blocks, schema drift, and unexpected costs are discovered through a bounded operator-triggered path before completion is allowed.
- Environment-only keys close the worst leakage path by keeping secrets out of YAML, source, fixtures, and UI state.
- Per-provider rate caps and a separate probe budget contain the blast radius of degraded providers or buggy callers.
- Separating probe budget from completion budget means health checks cannot starve the LLM planning budget.

## Consequences
- Layer A scanner gains an `httpx` allowance for `gateways/providers/*.py`.
- Bundle verifier gains a sweep over evidence files for provider key patterns.
- The ledger gains `provider.probe` as an event kind while the schema remains unchanged.
- The capability vocabulary gains `provider.probe` with `phase=3` and `dangerous=False`.
- The bridge gains one read-only route, `GET /api/providers/health`.
- The UI gains a non-gating provider status dot.
- Phase 3.3 fallback and template default remain unchanged.

## Cross-links
- [`00_overview/PHASE3_4_PLAN.md`](../../00_overview/PHASE3_4_PLAN.md) (this ADR's execution plan)
- [`02_architecture/adr/ADR-009-orchestration-skeleton.md`](ADR-009-orchestration-skeleton.md)
- [`02_architecture/adr/ADR-010-planner-and-dag.md`](ADR-010-planner-and-dag.md)
- [`02_architecture/adr/ADR-011-llm-planner-gateway.md`](ADR-011-llm-planner-gateway.md)
- [`03_implementation/config/llm_policy.schema.json`](../../03_implementation/config/llm_policy.schema.json)
