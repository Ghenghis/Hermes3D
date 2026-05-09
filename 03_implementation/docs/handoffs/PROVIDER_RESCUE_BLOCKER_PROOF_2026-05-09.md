# Provider Rescue — Non-Secret Blocker Proof
Date: 2026-05-09  
Contract: PR #124 + `CLAUDE_PROVIDER_COMPLETION_PROMPT_2026-05-08.md`  
Task: H3D-CLAUDE-PROVIDER-COMPLETION  
Owner: claude-provider-rescue  
Workspace: G:\Github\h3d-gui-wiring-codex (verified MCP_LOCK_WORKSPACE match)  
Branch: codex/claude-hermes-runtime-finish-contract-2026-05-08

---

## What Works Now

| Subsystem | Status | Proof |
|---|---|---|
| MCP locks | READY | doctor PASS, 0 zombie locks |
| Folder index | READY | 11 docs loaded |
| Backend | LIVE | 220 routes, no missing agent-workbench routes |
| MiniMax adapter code | CORRECT | Reaches `api.minimax.io/v1/chat/completions`, Bearer auth, model=`MiniMax-M2.7-highspeed`, key resolution prefers `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY` |
| DeepSeek adapter code | CORRECT | Posts to `api.deepseek.com/chat/completions`, Bearer auth, model=`deepseek-v4-pro`, payload includes `thinking={"type":"enabled"}` + `reasoning_effort="high"` for v4-pro |
| OpenCode CLI | DETECTED | v1.4.3-hermes3d, sandbox-ready, write blocked by policy |
| OpenHands CLI | DETECTED | v1.16.0, sandbox-ready, write blocked by policy |
| Docker sandbox | READY | v29.4.1, image present, network=none, denied paths enforced |
| Folder index loaded | READY | E2E readiness shows 11 context docs |

---

## What Is Still Blocked (with evidence IDs)

### MiniMax — provider-side billing/quota issue (NOT code, NOT auth)

| Field | Value |
|---|---|
| Status | BLOCKED |
| HTTP | 429 |
| Provider error class | `insufficient_balance_error` |
| Provider error code | `1008` |
| Provider message | "insufficient balance (1008)" |
| Endpoint reached | YES — `api.minimax.io/v1/chat/completions` |
| Auth header | YES — accepted by MiniMax |
| Model resolved | `MiniMax-M2.7-highspeed` |
| Key source (env name only) | `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY` |
| Latest evidence ID | `ev_cffabca307652c21` (this session) |
| Prior evidence IDs | `ev_6df47ea9e9145c7d`, `ev_01bbc444b58357f4`, `ev_3ad2267cb0d2c42f` |
| MiniMax request_id (provider) | `064dcbe9683e4c7ebc36a0e3836eb876` |

**Root cause class:** Provider-side account balance/credit issue. The Hermes adapter authenticates correctly and reaches MiniMax. MiniMax's billing system rejects the request with 1008.

Per official MiniMax docs ([error codes](https://platform.minimax.io/docs/api-reference/errorcode)) and community reports:
- 1008 occurs when the Token Plan key has **no usable balance** even if the plan duration is active
- Common when account has no payment method or no credit purchase
- For the **Coding Plan** specifically, MiniMax recommends switching to **OAuth portal auth** instead of API key
- Token Plan keys are separate from regular MiniMax keys; balance is tracked separately

### DeepSeek — invalid API key per provider's official 401 definition

| Field | Value |
|---|---|
| Status | BLOCKED |
| HTTP | 401 |
| Provider message | authentication failed |
| Endpoint reached | YES — `api.deepseek.com/chat/completions` (200 connectivity, 401 on auth check) |
| Auth header shape | YES — `Authorization: Bearer <redacted>` (matches official spec) |
| Model resolved | `deepseek-v4-pro` |
| Key source (env name only) | `DEEPSEEK_API_KEY` |
| Latest evidence ID | `ev_bdec2f02c01c17ec` (this session) |
| Prior evidence IDs | `ev_8553fc6248cddb1a`, `ev_ff7d845319c5b745` |

**Root cause class:** Per [DeepSeek official error code docs](https://api-docs.deepseek.com/quick_start/error_codes), HTTP 401 has exactly **one documented cause**: "the wrong API key." HTTP 402 (not 401) is "Insufficient account balance"; HTTP 422 is "Invalid request parameters." So 401 is purely an authentication credential issue.

Possible specific causes:
- Key copied with leading/trailing whitespace or extra character
- Key was rotated/regenerated on platform.deepseek.com but old value left in `G:/private/.env`
- Key belongs to a different DeepSeek account that doesn't have access to v4-pro
- Key was revoked

---

## Adapter Code Audit Result: PASS

I read the adapter source files end-to-end:

`G:/Github/h3d-gui-wiring-codex/03_implementation/src/hermes3d/gateways/providers/deepseek.py`:
- Line 76-77: `url = f"{config.base_url.rstrip('/')}/{config.completion_path.lstrip('/')}"` — base + path from env
- Line 80: `Authorization: Bearer {key}` — matches official spec
- Line 83: model fallback chain `HERMES3D_DEEPSEEK_MODEL` → `DEEPSEEK_MODEL` → `deepseek-v4-pro`
- Line 84-91: payload includes `messages`, `max_tokens`, conditional `thinking={"type":"enabled"}` and `reasoning_effort="high"` when model is `deepseek-v4-pro` — matches DeepSeek V4 Pro spec exactly

`G:/Github/h3d-gui-wiring-codex/03_implementation/src/hermes3d/gateways/providers/minimax.py`:
- Line 76: same URL construction pattern
- Line 79: Bearer auth header
- Line 82: model fallback `HERMES3D_MINIMAX_MODEL` → `MINIMAX_MODEL` → `MiniMax-M2.7-highspeed`
- Line 86: `max_completion_tokens` (correct OpenAI-compatible field name)
- Line 101-114: key resolution chain prefers `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY`, then `MINIMAX_TOKEN_PLAN_API_KEY`, `HERMES3D_MINIMAX_HIGHSPEED_API_KEY`, `MINIMAX_HIGHSPEED_API_KEY`, then config default, `OPENAI_API_KEY`, `MINIMAX_API_KEY`

**No stale model names, invented model IDs, or wrong-payload bugs in active code.** Both adapters match the providers' current official documentation as of 2026-05-09.

---

## Hermes Agents Real Coding PR Now? **NO**

Both providers must return `accepted: true` from `/api/code-operator/providers/smoke` before any provider-backed Hermes Agent coding loop can run. Currently:
- MiniMax: 429 BLOCKED (provider account-side)
- DeepSeek: 401 BLOCKED (key-side)

OpenCode/OpenHands write execution remains correctly fail-closed per policy until provider smoke passes. This is the designed safety behavior, not a bug.

---

## Which File/Branch/PR Contains The Fix

**No code fix is needed.** Both adapters are correct.

The fix is in two **out-of-repo locations** the user controls:

1. **MiniMax dashboard** at `https://platform.minimax.io` → Billing/Token Plan → top up balance, verify Token Plan/Highspeed plan has credits, OR switch to OAuth portal auth for Coding Plan per MiniMax's published recommendation.

2. **`G:\private\.env`** → `DEEPSEEK_API_KEY` value → rotate to a current valid key from `https://platform.deepseek.com/api_keys`. The key value never appears in this repo, in CI logs, in markdown, or in PR bodies.

After both fixes:
1. Restart the backend (the FastAPI process at PID 26244 reads env on start)
2. Re-run `POST /api/code-operator/providers/smoke` for each provider
3. When both return `accepted: true`, the first proof-gated Hermes Agent loop can run

---

## Confirmation: No Private Values Exposed

Reviewed the following surfaces during this rescue session:
- All redacted smoke responses: contain only env key names, base URL host labels, model names, HTTP status codes, evidence IDs, and provider request_ids — no Bearer tokens, no API keys
- All evidence ledger entries: only key names + redacted source labels + outcome
- This report: only env key names and out-of-repo paths
- Adapter code reads: only structural inspection; no env values printed

`git ls-files | grep private` returns empty. `G:/private/.env` is outside the repo. The MiniMax `request_id` shown above is a server-generated correlation token (not a secret), and is the value the user will give to MiniMax support to look up the request.

**No secrets leaked.**

---

## All Evidence IDs This Wave

| ID | Kind | Summary |
|---|---|---|
| `ev_cffabca307652c21` | code_provider_smoke | MiniMax HTTP 429 insufficient_balance via TOKEN_PLAN key |
| `ev_bdec2f02c01c17ec` | code_provider_smoke | DeepSeek HTTP 401 via DEEPSEEK_API_KEY |
| `ev_491fe9d07426cab4` | audit | Adapter code audit: both providers correct per official docs |

Prior evidence preserved in ledger: `ev_6df47ea9e9145c7d`, `ev_8553fc6248cddb1a`, `ev_01bbc444b58357f4`, `ev_ff7d845319c5b745`, `ev_3ad2267cb0d2c42f`.

---

## Locks After This Report

This task's locks (released at end of session):
- `claude-provider-rescue` / `PROVIDER_RESCUE_BLOCKER_PROOF_2026-05-09.md` — released after commit
- task `H3D-CLAUDE-PROVIDER-COMPLETION` — released after commit

`hermes_list_locks` should report 0 active after this report is committed.

---

## Next Three Actions for Codex

1. **No code action required from Codex this round.** Adapter code matches official provider docs. Wait for user to fix MiniMax balance + DeepSeek key.

2. **Optional adapter hardening (if user wants future debug):** Add a `redacted_smoke_classifier` that maps HTTP 429 + body `insufficient_balance_error` to a distinct UI-visible class `provider_billing_required` (not `auth_failed`), and HTTP 401 to `auth_credential_invalid`. Currently both surface as generic `blocked`. This is non-essential.

3. **After user fixes both providers and re-runs smoke:** Codex/Claude should run the first proof task (one harmless docs label fix) through the full chain: claim → lock → snapshot → MiniMax build → DeepSeek review → apply → gates → PR → evidence → release. Only then is Hermes Agents verifiably PASS.
