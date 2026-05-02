# ADR-011: LLM Planner Gateway — Bounded Provider Surface, Budget, Sanitizer, Redaction, Fallback Policy, Refusal Rules R7 + R8

## Status
Accepted (Phase 3.3, 2026-05-02).

## Context
Phase 3.2 ([`PHASE3_2_PLAN.md`](../../00_overview/PHASE3_2_PLAN.md), [ADR-010](ADR-010-planner-and-dag.md)) shipped the Planner agent with a **deterministic-template** code path that converts a fixture prompt into a `TaskDAG`. No LLM is called; the prompt → DAG mapping lives in `04_testing/fixtures/planner/prompts.json`. The DAG flows through the existing supervisor + capability-token + ledger seam from ADR-009, executed by the simulated `gen3d_executor` from Phase 3.2.

Phase 3.3 introduces the first real outbound model call. To preserve the safety boundary established in Phase 2 (no external launches) and Phase 3.1 (read-only adapters, capability tokens, append-only ledger), the LLM must enter the system through a **single bounded gateway**. Without this gateway, every refusal rule in ADR-009/010 can be silently bypassed by an `import openai` line in a future PR.

This ADR locks the LLM gateway contract: the budget model, the sanitizer + redactor responsibilities, the deterministic fallback policy, and two new refusal rules (R7 budget, R8 planner-output rejection). The gateway sits **above** the supervisor's capability-token layer and **below** the Planner agent. No other module is allowed to import an LLM SDK or open a socket to an LLM host. Phase 3.4 (real 3D provider probes) and Phase 4 (write actions) ship under their own ADRs.

The plan that this ADR codifies is [`PHASE3_3_PLAN.md`](../../00_overview/PHASE3_3_PLAN.md).

## Decision

### 1. LLMGateway contract
A single class `LLMGateway` exposes exactly one execute-class method:

```
LLMGateway.complete(
    prompt: str,
    *,
    token: CapabilityToken,
    budget: BudgetState,
) -> Result[LLMResponse]
```

- **Single entry point.** `complete` is the only path from Hermes3D to any LLM host.
- **Token-gated.** Refusal rules R1-R5 from ADR-009 are evaluated before any other work. Token must declare `tools ⊇ {"llm.complete"}` and have not yet been consumed.
- **Sanitizer first.** Prompt is run through `sanitize.normalize(prompt)` before any HTTP work. Failures return early with `Err::PromptRejected(...)`.
- **Budget gate.** `budget.would_exceed(...)` checks per-run + per-day caps. Exhaustion fires R7.
- **Allowlist.** Provider host must be present in `llm_policy.yaml provider_allowlist`. ADR-009's host-allowlist primitive is reused; non-listed host fires the existing host-not-allowed refusal.
- **Bounded execution.** Per-call timeout (default 30 s); rate cap (≤ 1 call/s per token); single retry on transport-class failure; second failure surfaces as `Err::Upstream(...)`.
- **Redaction pre-write.** `redaction.scrub(...)` runs over every string that enters the ledger or the proof bundle. The raw provider response never leaves the gateway's stack frame.
- **Idempotent ledger emission.** Each call writes one `llm.complete` event with `inputs_sha`, `outputs_sha` (computed over the *redacted* response), `tokens_in`, `tokens_out`, and `cost_usd_estimate`. Token-id is recorded for ADR-009 §3 invariant 4.

`LLMResponse` carries:

| Field | Type | Notes |
|---|---|---|
| `redacted_text` | `str` | post-redaction model output |
| `tokens_in` | `int` | provider-reported input tokens |
| `tokens_out` | `int` | provider-reported output tokens |
| `cost_usd_estimate` | `Decimal` | per-policy USD per token |

The gateway never returns the raw provider HTTP response, never returns headers, never returns auth metadata. Anything outside `LLMResponse` is dropped before the function returns.

### 2. Budget model
`BudgetState` is in-process, owned by the supervisor, persisted to `var/orchestration/budget.json` between runs. Two caps:

| Cap | Default (policy) | Reset cadence |
|---|---|---|
| `cost_cap_usd_per_run` | `0.05` | each new `run_id` |
| `cost_cap_usd_per_day` | `1.00` | UTC midnight |

Rules:
- Caps are **hard**. The gateway computes a worst-case USD estimate from `prompt_tokens × policy.input_usd_per_token + max_completion_tokens × policy.output_usd_per_token` *before* the call and refuses if either cap would be crossed.
- Actual post-call cost replaces the estimate in the ledger; the budget tracker advances by the actual amount.
- An exhaustion event writes one `budget.exceeded` row with the cap that triggered it (`per_run` or `per_day`) and the offending estimate.
- The supervisor reads the day-cap from `budget.json` at boot. Tampering with `budget.json` is detected by the proof bundle's honesty diff (the file is checksummed alongside the ledger).
- Phase 3.4+ may extend the budget model to per-provider caps via a new ADR; the structural shape stays additive.

### 3. Sanitizer rules (`gateways/sanitize.py`)
Before any prompt reaches the gateway socket layer, `sanitize.normalize(prompt)` MUST:

1. **Reject oversize.** Prompts whose UTF-8 byte length exceeds `policy.prompt_max_bytes` (default 4096) → `Err::PromptTooLarge`.
2. **Strip control chars.** Remove `\x00-\x1f` and `\x7f` except `\n` (`0x0a`) and `\t` (`0x09`).
3. **Reject injection markers.** Refuse prompts containing case-insensitive matches for any of: `ignore (all )?previous instructions`, `disregard (the )?(system|safety) (prompt|policy)`, `you are now`, `pretend (to be|you are)`, role-tag impersonation prefixes (`system:`, `assistant:`, `tool:`, `function:` at line start), `<\|system\|>`-style sentinels, or any string Codex's denylist registry adds.
4. **Reject embedded JSON-DAG sentinels.** Prompts MUST NOT contain `{"nodes":` or `"tool":"printer.write"` substrings — these indicate an attempt to pre-cook the planner's output. Refused with `Err::PromptRejected("dag_sentinel")`.
5. **Idempotent.** `normalize(normalize(p)) == normalize(p)` for any safe `p`.

Passing prompts are returned unchanged in semantic content. The sanitizer is conservative — false positives are preferable to false negatives. Future relaxation requires a new ADR.

### 4. Redaction rules (`gateways/redaction.py`)
Before any string enters the ledger, the proof bundle, a log file, or a stack trace, `redaction.scrub(text)` MUST mask:

| Pattern | Mask |
|---|---|
| `sk-[A-Za-z0-9_-]{16,}` (OpenAI-style) | `sk-***` |
| `sk-ant-[A-Za-z0-9_-]{16,}` (Anthropic-style) | `sk-ant-***` |
| `Bearer [A-Za-z0-9._\-]+` | `Bearer ***` |
| JWT-like `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` | `<JWT>` |
| Public IPv4 (anything **not** in `192.168.0.0/24`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`) | `<IP>` |
| Absolute Windows paths `[A-Z]:\\\\[^\s"']+` | `<WINPATH>` |
| Absolute POSIX paths `/(home\|root\|Users)/[^\s"']+` | `<POSIXPATH>` |
| API-key-shaped headers (`X-Api-Key:`, `Authorization:`) values | header preserved, value `***` |

Rules:
- Redaction is **idempotent**: `scrub(scrub(s)) == scrub(s)`.
- Redaction NEVER re-introduces the masked content (no reverse map persisted).
- The bundle verifier re-scans every committed evidence file with the same regex set; any match fails Layer F.

### 5. Fallback policy
The Planner agent's `mode="llm"` path follows this state machine for every plan request:

```
sanitize(prompt)
  └─ Err  → fallback to template, ledger: planner.fallback("sanitize_failed")
  └─ Ok   → gateway.complete(prompt, ...)
              └─ Err::Forbidden("budget_exceeded")  → fallback, ledger: budget.exceeded + planner.fallback("budget")
              └─ Err::Forbidden(other R1-R5/host)   → fallback, ledger: planner.fallback(reason)
              └─ Err::Upstream(timeout|5xx|...)     → fallback, ledger: planner.fallback("upstream")
              └─ Ok(LLMResponse)
                    └─ json.loads(response.redacted_text)
                          └─ raise → fallback, ledger: planner.fallback("invalid_json")
                          └─ Ok    → TaskDAG.validate(parsed)
                                       └─ Err::CycleDetected     → fallback, ledger: planner.fallback("cycle")
                                       └─ Err::DAGTooDeep        → fallback, ledger: planner.fallback("depth")
                                       └─ Err::FanoutExceeded    → fallback, ledger: planner.fallback("fanout")
                                       └─ Err::WriteToolRejected → fallback, ledger: planner.fallback("write_tool")
                                       └─ Err::UnknownTool       → fallback, ledger: planner.fallback("unknown_tool")
                                       └─ Ok(dag) → return dag with metadata.planner_mode = "llm"
```

The template fallback is exactly the Phase 3.2 deterministic path, called with the same prompt. The returned `TaskDAG` always carries `metadata.planner_mode` set to either `"llm"` or `"template"`. The bridge surfaces this field unchanged so the UI can show the mode indicator.

The LLM call is **never retried with a different prompt** — the only retry permitted is the gateway's single transport-class retry. Repeated LLM attempts require a new run.

### 6. Refusal rule R7 — budget exhausted
**Trigger:** an `llm.complete` call would push the per-run or per-day budget over its cap.

**Outcome:**
- Gateway returns `Err::Forbidden("budget_exceeded")`.
- Supervisor refuses to issue further `llm.complete` tokens for the current run (per-run cap) or until UTC midnight (per-day cap).
- Ledger writes a `budget.exceeded` row with `tool="llm.complete"`, `verdict="fail"`, message indicating which cap fired and the offending estimate.
- Planner falls back to the template path per §5.

R7 is enforced **at token issuance** (preventive) **and** **inside the gateway** (defense in depth). A token issued before the budget refresh remains valid until consumed; the gateway re-checks the budget at consume time.

### 7. Refusal rule R8 — planner output rejected
**Trigger:** any post-LLM validation step fails — invalid JSON, schema violation, cycle, over-depth, over-fanout, write-class tool, unknown tool, sanitizer rejection of a node string.

**Outcome:**
- Validator returns `Err::PlannerOutputRejected(reason)`.
- Planner falls back to the template path per §5.
- Ledger writes a `planner.fallback` row with `tool="planner.plan"`, `verdict="fail"`, message containing the reason code (`invalid_json`, `cycle`, `depth`, `fanout`, `write_tool`, `unknown_tool`, `sanitize_failed`, `upstream`, `budget`).
- The returned DAG is the template DAG; `metadata.planner_mode = "template"`.

R8 is the catch-all that guarantees a malformed LLM response can never produce an executable DAG. Combined with R6 (supervisor refuses dispatch of unknown-tool nodes), the worst-case outcome of any LLM behaviour is a deterministic template DAG.

### 8. What this ADR does NOT cover
- LLM tool-use / function-calling mode (text-in / JSON-out only in Phase 3.3).
- Streaming responses (single-shot only).
- Per-provider budget caps (single global cap in Phase 3.3).
- Real 3D provider probes (Phase 3.4 ADR).
- Provider dry-run UI chips (Phase 3.4).
- Write capability of any kind (Phase 4 ADR; Phase-4 manifest flags remain refused at registration per ADR-009).
- Cost reporting in the UI (no budget badge in Phase 3.3 — UI shows only the planner-mode indicator).

## Rationale
- A single gateway concentrates every safety check in one auditable surface. Codex cannot smuggle an LLM call into the codebase without tripping the Layer A path-restriction scanner.
- Budget enforcement at both token issuance and gateway entry guarantees a single misconfigured caller cannot drain the day cap; even an expired-budget token cannot be consumed.
- The sanitizer's conservatism (reject role-tag impersonation, reject DAG sentinels in the prompt) closes the most common prompt-injection vectors before any model sees the input.
- Redaction at the **write boundary** (ledger, bundle, log) — not at read time — guarantees no historical artifact exposes a secret. The bundle verifier re-scans on the same regexes, making the invariant testable.
- The deterministic fallback to the template planner means a malformed or hostile LLM response degrades to a known-good plan, not to an empty response or a runtime error. The DAG's `planner_mode` field makes the degradation visible to the operator.
- Locking R7 + R8 here means Phase 3.4+ (provider probes), Phase 4 (write actions), and Phase 5+ (multi-agent loops) all build on a tested fallback path rather than rediscovering it.

## Consequences
- The forbidden-pattern scanner gains a path-restricted import rule: `import openai|anthropic|requests|httpx`, and `urllib.request.urlopen` are allowed only inside `gateways/llm.py`. Any other location fails Layer A.
- The bundle verifier gains a redaction re-scan step over every committed evidence file.
- The ledger schema is unchanged; three new event-kind values (`llm.complete`, `planner.fallback`, `budget.exceeded`) flow through the existing `tool` + `message` columns.
- The capability-token model is unchanged in shape; the `tools` vocabulary grows by one value (`llm.complete`).
- The Planner agent's public signature is unchanged; only the internal mode dispatch grows. Callers that don't pass `mode=` continue to receive a template DAG.
- The bridge HTTP surface is unchanged; the `POST /api/plan/preview` response payload grows one optional metadata field (`planner_mode`).
- Phase 4 write actions MUST extend the token model with action-class methods and the ADR-008 `Confirmation` envelope; this ADR does not weaken that boundary.

## Cross-links
- [`00_overview/PHASE3_3_PLAN.md`](../../00_overview/PHASE3_3_PLAN.md) §"Phase 3.3 (revised)" (this ADR's execution plan)
- [`02_architecture/adr/ADR-009-orchestration-skeleton.md`](ADR-009-orchestration-skeleton.md) (capability-token model + R1-R5 + host allowlist that this ADR sits on top of)
- [`02_architecture/adr/ADR-010-planner-and-dag.md`](ADR-010-planner-and-dag.md) (template Planner + DAG schema + R6 unknown-tool refusal)
- [`03_implementation/config/llm_policy.schema.json`](../../03_implementation/config/llm_policy.schema.json) (the JSON-Schema that validates `llm_policy.yaml` at supervisor boot — committed in CP3.3-A)
- [`hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md`](../../hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md) (the safety baseline this ADR reinforces)
