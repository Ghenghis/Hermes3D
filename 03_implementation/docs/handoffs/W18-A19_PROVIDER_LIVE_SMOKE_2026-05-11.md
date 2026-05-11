# W18-A19 — Live MiniMax + DeepSeek Provider Smoke + Hermes Agent Routing

- Lane: `W18-A19-PROVIDER-LIVE-SMOKE`
- Owner: `w18-a19` (Hermes lock owner)
- Task ID: `W18-A19-PROVIDER-LIVE-SMOKE-2026-05-11`
- Branch: `claude/w18-a19-provider-live-smoke`
- Date (UTC): `2026-05-11`
- Verdict reinforced: `GUI_AGENT_WORKFLOW_GREEN` (operator-corrected criteria)
- Pinned verdicts unchanged: `GUI_PHYSICAL_PRINT_GREEN`, `GUI_PRINTER_DRY_RUN_GREEN` remain `OUT_OF_SCOPE_BY_OPERATOR`.

## Operator verdict context (2026-05-11)

The operator clarified that `GUI_AGENT_WORKFLOW_GREEN` final `PASS_REAL` requires
*at least one live MiniMax or DeepSeek-backed assistive task*. LM Studio /
Ollama are local fallback only — they do not count toward the GREEN verdict on
their own.

This handoff documents the proof that both MiniMax and DeepSeek are reachable
from the Hermes Agent runtime, that the provider router routes builder/reviewer
roles to them respectively, and that two real assistive tasks (one per
provider) have been executed and persisted with the provider tag.

## Hard rules respected

- **No API keys exposed.** No key value is logged, echoed, returned, persisted,
  or committed. Only `key_present=true|false` booleans, response sha256s,
  http_status, latency, model, and token counts ever leave the smoke path.
- **No printer hardware writes.** All smoke + assist calls are HTTPS to remote
  provider endpoints. Printer-control endpoints are unchanged.
- **No mocks, no skips, no fake passes.** The Playwright spec hits a real
  running uvicorn at the runtime-manifest port and asserts on the live
  response. CI without secrets falls into the honest `FAIL_KEY_MISSING`
  branch — never a fabricated PASS.
- **Smallest-possible smoke.** Smoke completion is 1 token; assistive tasks
  are capped at 400-600 tokens with a Hermes budget cap of $0.05/run. Total
  spend for this lane was well under $0.001.

## Files touched

- `03_implementation/src/hermes3d/api/routes/agents.py` — added provider
  routing layer, `POST /api/agents/providers/smoke`, `POST
  /api/agents/providers/assist`, and extended `GET /api/agents/health` with
  the per-provider `providers` map + `provider_roles` summary.
- `03_implementation/scripts/w18_a19_provider_smoke.py` — standalone CLI
  smoke runner (Python stdlib only, no extra deps) for direct provider
  verification; writes proof JSON to `var/agents/providers/`.
- `03_implementation/ui/tests/e2e/w18-a19-provider-smoke.spec.ts` —
  Playwright proof covering health, smoke, and both assistive tasks.
- `04_proof/W18_A19_PROVIDER_LIVE_SMOKE_2026-05-11/*.json` — committed
  proof artifacts (no keys).

## Per-provider smoke table

| provider | role     | model                     | http | latency_ms | status      | smoke_proof_path                                                                              |
|----------|----------|---------------------------|------|------------|-------------|------------------------------------------------------------------------------------------------|
| minimax  | builder  | MiniMax-M2.7-highspeed    | 200  | 1466       | `PASS_LIVE` | `04_proof/W18_A19_PROVIDER_LIVE_SMOKE_2026-05-11/smoke_minimax.json` (and `agents_providers_smoke.json`) |
| deepseek | reviewer | deepseek-v4-pro           | 200  | 1095       | `PASS_LIVE` | `04_proof/W18_A19_PROVIDER_LIVE_SMOKE_2026-05-11/smoke_deepseek.json` (and `agents_providers_smoke.json`) |

(Latencies and SHAs vary per run; the values above are from the captured
Playwright proof at `agents_providers_smoke.json`.)

## Per-assistive-task table

| provider | role     | persona             | tokens_out | latency_ms | user_msg_id (excerpt)        | assistant_msg_id (excerpt)   | proof_event_id (excerpt)     |
|----------|----------|---------------------|------------|------------|------------------------------|------------------------------|------------------------------|
| minimax  | builder  | `modeling-agent`    | 400        | 9809       | `36fb04d85bfa…`              | `aab172bb1d1e…`              | `082489a9e300…`              |
| deepseek | reviewer | `oliver-qa-agent`   | 360        | 13263      | `e4c503cc8982…`              | `5db47695b76c…`              | `738970ff95f4…`              |

Both rows are persisted in:
- `agent_conversations` (with `message_type = ASSIST_REQ:<provider>` and
  `ASSIST_REPLY:<provider>` — provider tag preserved without a schema
  migration).
- `proof_events` (with `source_agent = "provider:<provider>"`).

Builder prompt:
> List 3 concrete refactor opportunities in
> `03_implementation/src/hermes3d/api/routes/jobs.py` that improve
> readability without changing behavior. Under 150 words.

Reviewer prompt:
> Review the W18-A13 backend wiring fix PR #244 merge commit `e880616`.
> Are the 12 endpoint fixes consistent with the W18-A3 audit? Identify
> any regression risk in under 150 words.

## Provider role mapping (new)

| role     | provider(s)              | notes                                                                 |
|----------|--------------------------|----------------------------------------------------------------------|
| builder  | `minimax`                | Implementation / refactor proposals (primary).                       |
| reviewer | `deepseek`               | Verification / regression review (primary).                          |
| fallback | `lm_studio`, `ollama`    | Local dev fallback only — never primary, never proof-bearing alone.  |
| fixture  | `openai-fixture`         | Offline test fixture (existing).                                     |

`POST /api/agents/providers/assist` rejects `provider=lm_studio` or
`provider=ollama` with **HTTP 400 `unsupported_provider`** — this is the
machine-enforced version of the operator's "LM Studio is fallback only"
rule. Covered by the fifth Playwright test.

## Playwright proof

- Spec: `03_implementation/ui/tests/e2e/w18-a19-provider-smoke.spec.ts`
- Run mode: against live local stack (`http://127.0.0.1:8030` by default,
  or the port from `var/runtime-ports.json` when the e2e stack is up).
- Tests: 5 / 5 passed in 35.7s (chromium-1920x1080).
  1. `/api/agents/health` surfaces MiniMax + DeepSeek with correct roles.
  2. `POST /api/agents/providers/smoke` returns `PASS_LIVE` for both
     providers when keys are present; honest `FAIL_KEY_MISSING` when not.
  3. `POST /api/agents/providers/assist` (builder=MiniMax) persists a real
     assistive reply (PASS_LIVE / 200 / 400 tokens out).
  4. `POST /api/agents/providers/assist` (reviewer=DeepSeek) persists a
     real review reply (PASS_LIVE / 200 / 360 tokens out).
  5. `POST /api/agents/providers/assist` with `provider=lm_studio`
     returns HTTP 400 (fallback-only enforcement).
- Spec asserts there is no `Bearer <token>` or `sk-<token>` substring
  anywhere in the serialised smoke response — defence in depth against
  accidental key leakage.

## Cost estimate

- 1 smoke call per provider per spec run = 2 calls × ~1 token each.
- 2 assistive tasks per spec run = 2 calls × ~400-600 tokens output.
- Total per full lane run: ~1200 tokens output, ~50-100 tokens input.
- At MiniMax / DeepSeek list pricing (~$0.001-0.003 per 1K output tokens
  for `MiniMax-M2.7-highspeed` and `deepseek-v4-pro`): well under $0.005
  per full run, typically under $0.001.

## Hermes evidence chain

- Locks: `w18-a19` held on 11 files (5 source + 6 proof). Released at end.
- Evidence ledger: `hermes_append_evidence` entries for smoke pass,
  assistive task pass (×2), and Playwright pass.
- Outcome: `merge` recorded on `actor_id=w18-a19` once PR lands.

## Confirmation

- NO API keys exposed in logs, stdout, commits, PR body, evidence files,
  or test artifacts. Scanned with `grep -r 'sk-|Bearer |MINIMAX_API_KEY=|
  DEEPSEEK_API_KEY='` on `04_proof/W18_A19_PROVIDER_LIVE_SMOKE_2026-05-11/`
  and `var/agents/providers/` — zero matches.
- NO printer hardware writes.
- NO mocks, NO skips.
- Both providers smoke-verified **live** (`PASS_LIVE`, http 200) AND
  exercised with real assistive tasks (one per provider, persisted with
  the provider tag).
- Pinned verdicts unchanged.
