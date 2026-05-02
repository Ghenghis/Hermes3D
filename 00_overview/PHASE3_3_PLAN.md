# Phase 3.3 (revised) — LLM Planner Gateway only

**Status:** design only · no code · no commits.
**Architecture references:** [`02_architecture/adr/ADR-009-orchestration-skeleton.md`](../02_architecture/adr/ADR-009-orchestration-skeleton.md), [`02_architecture/adr/ADR-010-planner-and-dag.md`](../02_architecture/adr/ADR-010-planner-and-dag.md).
**Branch:** `feat/phase-3-3-llm-planner-gateway` (forks from `develop` after Phase 3.2 merge).
**Scope discipline:** smaller than Phase 3.2 — **no new tabs**, **no new bridge routes**, **no new adapters**, **no provider probes**, **no UI provider chips**.

---

## 1. Revised objective

Replace the deterministic-template Planner with an **LLM-backed Planner** behind a **bounded gateway**. The gateway enforces budget, rate, timeout, host allowlist, and redaction. LLM responses are validated against the existing `TaskDAG` schema; any failure deterministically falls back to the Phase 3.2 template planner, recorded in the ledger as `planner.fallback`. The existing `POST /api/plan/preview` route is reused unchanged in shape — only its response payload now carries `metadata.planner_mode` so the UI can show whether the DAG came from the LLM or the template fallback.

The 3D Generation tab gains **one** UI affordance: a small "via LLM ✓ / template ↻" indicator next to the existing "Preview plan" button. Nothing else in the UI changes.

---

## 2. Revised out-of-scope

The following are **NOT** in Phase 3.3. Each is deferred to a later phase with its own ADR + checkpoint:

- **Real 3D provider probes** (TRELLIS / Hunyuan3D / TripoSR / MiniMax) → **Phase 3.4**
- **Provider dry-run UI chips** → **Phase 3.4**
- **Real 3D provider gateway** → **Phase 3.4+**
- **Blender MCP read-only / slicer dry-run** → later phase
- Any actual 3D model generation, simulated or real (Phase 3.2 simulated executor unchanged)
- Mesh QA / Slicer QA / Repair / Releaser / Auditor agents
- Multi-agent loops (Planner remains single-shot)
- Streaming LLM responses
- Tool-use / function-calling LLM mode (text-in / JSON-out only)
- New bridge routes (existing `POST /api/plan/preview` and `GET /api/runs/<id>` are reused)
- New tabs, new dock states, new primitives, new mock tabs
- New provider chips, provider lists, provider settings UI
- Persistence of raw LLM responses on disk; only redacted traces enter ledger + bundle
- Any Phase-4 write capability

---

## 3. Reduced file / module list

### Python — gateway, planner, capabilities
| Path | Status | Purpose |
|---|---|---|
| `00_overview/PHASE3_3_PLAN.md` | new | this plan |
| `02_architecture/adr/ADR-011-llm-planner-gateway.md` | new | gateway contract, budget model, redaction rules, sanitizer rules, fallback policy, refusal rules R7 + R8 |
| `03_implementation/src/hermes3d/gateways/__init__.py` | new | namespace |
| `03_implementation/src/hermes3d/gateways/llm.py` | new | `LLMGateway` class — single bounded entry point: `complete(prompt, *, token, budget) -> Result[LLMResponse]`. Internally combines budget check, sanitizer, host allowlist, timeout, retry-once policy, and redaction. **Only file in the codebase allowed to import an LLM SDK or call out to an LLM host.** |
| `03_implementation/src/hermes3d/gateways/budget.py` | new | per-run + per-day token + USD cost caps; emits `budget.exceeded` ledger event on overflow |
| `03_implementation/src/hermes3d/gateways/redaction.py` | new | scrubs API keys, secrets, public IPs, absolute paths from any string before it reaches logs/ledger/bundle |
| `03_implementation/src/hermes3d/gateways/sanitize.py` | new | input-prompt sanitizer: strips control chars, well-known injection markers, oversize prompts (cap 4 KiB) |
| `03_implementation/src/hermes3d/agents/planner.py` | modify (additive) | new `mode="llm"` path that calls `LLMGateway`; existing `mode="template"` path unchanged. Default mode read from policy. Validation: LLM JSON → existing `TaskDAG`; any failure → fallback to template + `planner.fallback` ledger event. **No new DTOs introduced** — LLM response is parsed straight into the Phase 3.2 schema |
| `03_implementation/src/hermes3d/orchestration/types.py` | modify (additive) | three small DTOs: `LLMResponse { redacted_text, tokens_in, tokens_out, cost_usd_estimate }`, `BudgetState`, `PlannerMode = "llm" \| "template"`. `TaskDAG.metadata` gains an optional `planner_mode` field (additive — old clients ignore it) |
| `03_implementation/src/hermes3d/orchestration/supervisor.py` | modify (additive) | tokens for the LLM-mode planner carry `tools ⊇ {"llm.complete", "planner.plan"}`; supervisor refuses to issue `llm.complete` token when budget exhausted (R7) |
| `03_implementation/src/hermes3d/orchestration/ledger.py` | modify (additive) | three new event kinds: `llm.complete`, `planner.fallback`, `budget.exceeded`. Schema unchanged (existing columns suffice). Append-only invariant preserved |
| `03_implementation/src/hermes3d/adapters/_capabilities.py` | modify (additive) | one new flag `llm_complete` (phase=3, dangerous=False). Manifest still refuses `phase>=4` |
| `03_implementation/config/llm_policy.yaml` | new | `default_mode: template`, `provider_allowlist: [openai-fixture]`, `cost_cap_usd_per_run: 0.05`, `cost_cap_usd_per_day: 1.00`, `timeout_seconds: 30`, `prompt_max_bytes: 4096`, `retry_max: 1` |
| `03_implementation/config/llm_policy.schema.json` | new | JSON-Schema for the policy; loaded at supervisor boot, refusal at validation failure |

### UI — minimal additive surfaces
| Path | Status | Purpose |
|---|---|---|
| `03_implementation/ui/src/types/dag.ts` | modify (additive) | `TaskDAG.metadata.planner_mode?: "llm" \| "template"` |
| `03_implementation/ui/src/tabs/Gen3D.tsx` | modify (additive) | one small badge next to the existing "Preview plan" button reading `via LLM ✓` (cyan) or `template ↻` (muted), driven by `previewDag?.metadata?.planner_mode`. **No** other UI changes — no provider chip, no budget badge, no settings panel |

> Removed from Phase 3.3 (was in v1, deferred to Phase 3.4): `gen3d_probe.py`, gen3d-provider fixture, provider dry-run chip in `Gen3D.tsx`, budget badge in panel header, `getBudgetState` AdapterAPI method, `data/mock/llm.ts`, `types/llm.ts`, `gen3d.llm_indicator.spec.ts` (renamed to `gen3d.planner_mode.spec.ts`).

### Tests / fixtures
| Path | Status | Purpose |
|---|---|---|
| `04_testing/pytest/unit/gateways/test_llm_gateway.py` | new | tokenless / expired / phase-violation / budget-exceeded / rate-cap / timeout / non-allowlisted host refusals; redaction applied to ledger entry |
| `04_testing/pytest/unit/gateways/test_budget.py` | new | per-run + per-day overflow, deterministic accounting, ledger emission |
| `04_testing/pytest/unit/gateways/test_redaction.py` | new | masks API key patterns, public IPs, absolute paths, common secret formats; idempotent |
| `04_testing/pytest/unit/gateways/test_sanitize.py` | new | strips control chars, injection markers, oversize prompts |
| `04_testing/pytest/unit/agents/test_planner_llm_mode.py` | new | LLM happy path, malformed JSON → fallback, cycle/over-deep DAG → fallback, write-class tool → fallback, budget exceeded → fallback. Each fallback emits `planner.fallback` |
| `04_testing/pytest/integration/test_planner_llm_fallback_roundtrip.py` | new | bridge `POST /api/plan/preview` against fixture LLM that returns malformed JSON → response surfaces template DAG with `metadata.planner_mode="template"` and ledger contains `planner.fallback` |
| `04_testing/playwright_ui/tests/visual/gen3d.planner_mode.spec.ts` | new | `?adapter=live` + fixture-routed LLM happy response → indicator reads "via LLM ✓"; fixture-routed malformed LLM → indicator reads "template ↻"; "Generate" button still locked; zero non-localhost network requests |
| `04_testing/fixtures/llm/responses.json` | new | deterministic LLM responses (valid DAG, malformed JSON, write-class tool, oversize, injection-laden) consumed by the gateway fixture |
| `04_testing/fixtures/llm/server.py` | new | tiny FastAPI fixture for the LLM provider; deterministic responses keyed by prompt sha |

### CI
| Path | Status | Purpose |
|---|---|---|
| `.github/workflows/ui-ci.yml` | modify | extend path filter only — `gateways/**`, `agents/planner.py`, `config/llm_policy.{yaml,schema.json}`, new tests + fixtures. **No new job.** Existing `layer_d2_live_smoke` boots the LLM fixture alongside the existing Moonraker fixture and runs `gen3d.planner_mode.spec.ts` in the same Playwright invocation |

---

## 4. Checkpoint breakdown — CP3.3-A → CP3.3-E

Strict serial. Architect review at A, C, D, E.

### CP3.3-A — Plan + ADR-011 + policy schema
- Commit `PHASE3_3_PLAN.md` (this document).
- Commit `ADR-011-llm-planner-gateway.md` defining: gateway contract, budget model, redaction + sanitizer rules, fallback policy, refusal rules R7 + R8.
- Commit `llm_policy.schema.json` only. **Not** `llm_policy.yaml` yet — that lands in CP3.3-B with safe defaults.
- No code under `gateways/`. Phase 3.2 gates remain green.

### CP3.3-B — Gateway + budget + redaction + sanitize (offline, mock-callable)
- `gateways/llm.py`, `gateways/budget.py`, `gateways/redaction.py`, `gateways/sanitize.py` + DTO additions in `types.py`.
- Commit `llm_policy.yaml` with `default_mode: template`, conservative caps.
- Unit tests for each module. Gateway tested with a mock callable injected at construction — **no real HTTP**, no fixture server yet.
- No agent changes yet, no bridge changes yet.

### CP3.3-C — Planner LLM mode + supervisor wiring + fixture LLM server
- `agents/planner.py` gains `mode="llm"` path; default still `template` per policy.
- `supervisor.py` token issuance grows to include `"llm.complete"` for the planner; budget gate at issuance time (R7).
- `_capabilities.py` adds `llm_complete` flag.
- `04_testing/fixtures/llm/server.py` + `responses.json`.
- Unit tests for planner LLM mode + every fallback trigger.
- Integration test offline: `dispatch_plan(mode="llm")` against fixture LLM (malformed response) → fallback DAG; ledger has `planner.fallback` exactly once.

### CP3.3-D — UI mode indicator + bridge envelope additive field
- Bridge: existing `POST /api/plan/preview` response now carries `metadata.planner_mode` in the returned DAG (additive — schema bump in DTO, old clients ignore unknown keys). **No new route.**
- UI: `Gen3D.tsx` adds the small "via LLM ✓ / template ↻" badge next to the existing "Preview plan" button; `dag.ts` type extended.
- Playwright spec `gen3d.planner_mode.spec.ts` covers happy + fallback paths.
- Phase 2 + 3.1 + 3.2 specs still pass unchanged. Dashboard visual baseline untouched.

### CP3.3-E — Proof bundle + completion report + PR
- Bundle assembler reuses Phase 3.1's `phase3_1_proof.py` pattern (suggest `phase3_3_proof.py`, single-purpose, sibling location).
- Bundle contents: `PHASE3_3_PLAN.md`, `ADR-011`, ledger snapshot (with `llm.complete` + `planner.fallback` + `budget.exceeded` events), redacted LLM trace samples, plan-preview replay, Playwright JSON, UI build hash.
- Completion report mirrors Phase 3.1/3.2 structure; adds explicit "Risks observed" §9 evidence.
- PR `Phase 3.3 — LLM Planner Gateway` to `develop`. HARD STOP.

---

## 5. Safety gates per checkpoint

Refusal rules R1–R6 carry forward from ADR-009 / ADR-010. Phase 3.3 adds **two** rules:

| Rule | Trigger | Outcome |
|---|---|---|
| **R7** | LLM call attempted while budget exhausted (per-run or per-day) | `Err::Forbidden("budget_exceeded")`; planner falls back to template; ledger writes `budget.exceeded` |
| **R8** | LLM response cannot be validated as `TaskDAG`, contains a write-class tool, exceeds DAG depth/fanout caps, or any node fails sanitizer | `Err::PlannerOutputRejected("…")`; planner falls back to template; ledger writes `planner.fallback` with reason |

| Checkpoint | Gate | Enforced by |
|---|---|---|
| CP3.3-A | ADR-011 declares numeric budget caps, non-empty redaction list, non-empty allowlist; rules R7/R8 documented; policy schema lints against JSON-Schema draft-07 | architect doc review |
| CP3.3-B | Gateway refuses calls without token, with expired token, beyond budget, beyond rate (≤ 1/s), beyond timeout (default 30 s), to non-allowlisted host. Sanitizer strips injection markers + oversize. Redactor masks every secret pattern in fixture trace | unit tests |
| CP3.3-C | Planner LLM mode validates response → `TaskDAG`; on any failure, falls back to template, emits `planner.fallback` ledger event, surfaces `metadata.planner_mode="template"`. Supervisor refuses `llm.complete` token issuance when budget exhausted | unit + integration tests |
| CP3.3-D | UI never displays raw LLM text — only the validated DAG + the mode indicator. Bridge envelope addition is backward-compatible (Phase 3.1/3.2 specs unchanged). No new bridge route. Source-pattern audit clean. LLM-import path-restricted to `gateways/llm.py` only | Playwright + Phase 0 scanner |
| CP3.3-E | Bundle honesty diff: ledger snapshot contains at least one each of `llm.complete`, `planner.fallback`, `budget.exceeded` events; redacted trace files contain zero matches for known secret patterns; manifest matches zip exactly | bundle verifier + grep audit |

Phase 3.1 + 3.2 boundaries preserved exactly. The bridge stays localhost-only. Capability-token model unchanged in shape — only the `tools` vocabulary grows by one value (`llm.complete`).

---

## 6. Test plan

### Layer A — static gates
- ruff format/check on `gateways/**`, `agents/planner.py`, new tests.
- Forbidden-pattern scanner extended:
  - **Path-restricted LLM-import rule**: `import openai | import anthropic | import requests | import httpx | urllib.request.urlopen` is allowed **only** inside `gateways/llm.py`. Any other location fails Layer A.
  - No raw API keys in source (regex on common secret prefixes).
  - No `subprocess | spawn | exec | BrowserWindow | webview | window.open | shell\. | process\.` in any new module.
- `llm_policy.yaml` validated against `llm_policy.schema.json` at supervisor boot; CI runs the validator on every push.

### Layer B — unit
| Test | Asserts |
|---|---|
| `test_llm_gateway.py` | tokenless → R1; expired token → R4; phase violation → R5; budget exceeded → R7; rate cap; timeout; non-allowlisted host (R9 substrate from ADR-009 host-allowlist already in place); redacted trace stored in ledger |
| `test_budget.py` | per-run cap, per-day cap, sequential calls accumulate deterministically, overflow event written |
| `test_redaction.py` | masks `sk-…`, `Bearer …`, JWT-like, public IPv4 outside `192.168.0.0/24`, absolute Win + POSIX paths; idempotent |
| `test_sanitize.py` | strips control chars (`\x00-\x1f` except `\n\t`), injection markers ("ignore previous instructions", role-tag impersonation, system: prefixes), oversize → `Err::PromptTooLarge` |
| `test_planner_llm_mode.py` | happy path: gateway returns valid JSON-DAG → `mode="llm"` result; malformed JSON → fallback + `planner.fallback`; DAG with `printer.write` → fallback; cycle → fallback; over-deep → fallback; over-fanout → fallback; budget exceeded → fallback |

### Layer C — integration
| Test | Asserts |
|---|---|
| `test_planner_llm_fallback_roundtrip.py` | bridge `POST /api/plan/preview` against fixture LLM returning malformed JSON → response carries template DAG with `metadata.planner_mode="template"`; ledger has exactly one `planner.fallback` event for the run; bridge still localhost-only; happy-path fixture returns valid DAG with `metadata.planner_mode="llm"` |

### Layer D2 — UI
| Test | Asserts |
|---|---|
| `dashboard.visual.spec.ts` | unchanged (still platform-skipped on Linux) |
| `dock.spec.ts` | unchanged |
| `fleet.live.spec.ts` | unchanged |
| `gen3d.plan_preview.spec.ts` (Phase 3.2) | unchanged |
| `gen3d.planner_mode.spec.ts` (new) | preview-plan with happy LLM fixture → indicator reads "via LLM ✓"; preview-plan with malformed LLM fixture → indicator reads "template ↻"; "Generate" button still has `aria-disabled="true"`; zero non-localhost network requests beyond bridge + fixture LLM; no popup/window-open attempts |

---

## 7. Proof bundle contents

- Path: `06_release/phase3.3-bundle/<head>-<utc>.zip`
- Manifest entries (exactly **seven**):
  - `docs/PHASE3_3_PLAN.md`
  - `docs/ADR-011-llm-planner-gateway.md`
  - `evidence/ledger_snapshot.sqlite3`
  - `evidence/llm_redacted_trace_sample.json`
  - `evidence/plan_preview_replay.json`
  - `evidence/playwright_report.json`
  - `evidence/ui_build_output_hash.json`
- sha256 sidecar + manifest JSON beside the zip.
- Honesty diff (Layer F) confirms manifest matches zip exactly.
- Bundle verifier additionally asserts:
  - Redacted trace files contain **zero** matches for the secret-pattern regexes used in `test_redaction.py`.
  - Ledger snapshot includes at least one each of `llm.complete`, `planner.fallback`, `budget.exceeded` rows (from fixture-driven tests).

---

## 8. Definition of "done"

Phase 3.3 is **done** iff all hold:

| # | Criterion | Measure |
|---|---|---|
| 1 | LLMGateway enforces budget (R7), allowlist, rate, timeout, token rules | `test_llm_gateway.py` + `test_budget.py` green |
| 2 | Sanitizer + redactor never let raw secrets / injection markers through | `test_sanitize.py` + `test_redaction.py` green; bundle verifier finds zero secret matches |
| 3 | Planner LLM mode validates output to TaskDAG; every invalid case falls back to template + emits `planner.fallback` | `test_planner_llm_mode.py` + integration test green |
| 4 | Default `planner_mode` per policy is `template`; LLM is opt-in | grep on `llm_policy.yaml` for `default_mode: template` |
| 5 | LLM-import path restriction holds | Layer A scanner finds zero LLM-SDK imports outside `gateways/llm.py` |
| 6 | Bridge envelope addition is backward compatible | Phase 3.1 + 3.2 specs unchanged + green |
| 7 | UI never displays raw LLM text | grep audit on `Gen3D.tsx` for absent rendering of unvalidated text; Playwright asserts only DAG nodes + indicator render |
| 8 | "Generate" button remains LockedAction | grep audit ≥ 1 match for `LockedAction label="Generate"` in `Gen3D.tsx` |
| 9 | No new bridge route added; no new tab; no new primitive | bridge route count unchanged for execute-class operations; no new file under `tabs/` or `components/` |
| 10 | Source-pattern audit clean (R1–R8 substrate intact, LLM-import path-restricted) | Phase 0 scanner green |
| 11 | Proof bundle honest; verifier finds zero secret matches and required ledger events | bundle verifier green |
| 12 | Architect review PASS at CP3.3-A, CP3.3-C, CP3.3-D, CP3.3-E | review verdicts in chat |

When all 12 hold, PR `Phase 3.3 — LLM Planner Gateway` opens to `develop`. **Phase 3.4** (real 3D provider probes + provider dry-run UI chips) becomes the next planning candidate, under its own ADR. **Phase 4 (write actions) does not unlock until Phase 3.4 + 3.5 ship and pass architect review.**

---

## 9. Risks + mitigations

Each risk has its mitigation, the refusal rule it depends on, and the test that exercises it.

| # | Risk | Mitigation | Refusal | Test |
|---|---|---|---|---|
| R-1 | **Provider cost runaway** — long completions, retry storms, prompt amplification | per-run + per-day USD cap in `budget.py`; gateway refuses on overflow; planner falls back to template; `budget.exceeded` ledger event | R7 | `test_llm_gateway.py::test_budget_exceeded` + `test_budget.py` |
| R-2 | **Malformed DAG** from LLM — invalid JSON, cycles, over-depth, unregistered tools, write-class tools | strict schema validation against existing `TaskDAG`; cycle + depth + fanout caps; write-class denylist; any failure → deterministic template fallback + `planner.fallback` event | R6 + R8 | `test_planner_llm_mode.py::test_*_fallback` |
| R-3 | **Prompt injection** — model coerced into emitting unsafe tools, exfil, role hijack | `sanitize.py` strips injection markers + oversize; system-message instructions enforce JSON-only output; LLM output validated as JSON-DAG, never executed as natural language; write-class tools refused at validation | R8 | `test_sanitize.py` + `test_planner_llm_mode.py::test_write_class_rejected` |
| R-4 | **External provider failure** — 5xx, timeout, network partition | timeout (30 s default); single retry only; on second failure → fallback to template; never blocks planner indefinitely; fixture provider exercises every error class in CI | R8 | `test_llm_gateway.py::test_timeout` + integration fallback test |
| R-5 | **Secret leakage** — API key or IP appears in ledger, bundle, UI, or stack trace | `redaction.py` scrubs every string before it enters logs/ledger/bundle; bundle verifier asserts zero secret matches; UI never displays raw LLM text | n/a (defense-in-depth) | `test_redaction.py` + bundle verifier |
| R-6 | **No write escalation** — LLM emits a node whose tool is `printer.write`, `gcode.send`, `slicer.execute`, etc. | DAG validator's denylist rejects every write-class tool; supervisor's R6 also refuses dispatch; capability manifest refuses `phase>=4`; Phase 4 boundary unchanged | R6 + R8 | `test_planner_llm_mode.py::test_write_class_rejected` + `test_capabilities_manifest.py` |
| R-7 | **LLM-SDK import drift** — a future PR adds an SDK import outside the gateway, bypassing budget/redaction | Layer A scanner restricts LLM SDK imports to `gateways/llm.py` only; PR template requires architecture-checkpoint marker | n/a (static gate) | Phase 0 scanner |
| R-8 | **Backsliding into Phase 4 by accident** — a future PR adds a write capability under cover of a Phase 3 ADR | adapter manifest validator refuses `phase>=4` flags at registration; forbidden-pattern scanner rejects any new `dangerous=True` flag in the orchestration tree without a new ADR | R5 | `test_capabilities_manifest.py::test_phase_4_refused` + Layer A scanner |

The completion report's "Risks observed in this phase" section enumerates these eight items with fixture-driven evidence (ledger row counts, bundle verifier output, test pass IDs).
