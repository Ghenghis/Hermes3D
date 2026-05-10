# Hermes RC v2 Active-Loop Routes (W6-2, 2026-05-09)

**Status**: shipped (W6-2 PR; commits 3-5 of RC v2)
**Lane**: 2 of the user's 5-lane finish order
**Worktree**: `G:/Github/h3d-gui-wiring-codex`
**Branch**: `claude/w6-2-rc-v2-active-loop` (off `feat/hermes3d-7-complete-gui-repo-wiring`)

## Summary

This doc covers the four **active-loop routes** added to the Hermes Recovery
Controller v2 in W6-2. After this PR the controller can orchestrate the full
sequence:

```
failure -> [v1 record] -> freeze -> propose -> review -> apply -> resume -> thaw
```

without mocks in the source path. LLM provider calls (MiniMax for
proposals, DeepSeek for reviews) are dispatched through swappable adapter
callables. The defaults raise `ProviderNotConfigured` so an unconfigured
deployment surfaces a generic `503` rather than a silent no-op or a
secret-leaking error message.

PR #149 added commits 1+2 (state machine + freeze/thaw saga step 2). PR
#154 added the read-only `GET /api/code-operator/recovery/runs` route.
PR #171 pinned cross-version saga semantics across v0.12 + v0.13. PR #175
added the `test_recovery_loop_drill` end-to-end fixture with mocked
provider phases. **W6-2 wires the actual route + service surface those
drills proved out, so the loop can now run for real.**

## Routes

All four routes live on the existing `code_operator` `APIRouter` (FastAPI
"bigger applications" layout — see source #2 below) under the prefix
`/api/code-operator/recovery/`. Each is a thin wrapper over a service
method in `hermes3d.services.recovery_controller`.

### `POST /api/code-operator/recovery/propose`

| Field        | Type   | Notes                                  |
| ------------ | ------ | -------------------------------------- |
| `run_id`     | string | 32-char hex `attempt_id` from freeze   |
| `failure_summary` | string (<= 400) | optional; falls back to spec.failure_summary |

Service: `recovery_controller.propose_fix`.
Default state precondition: run must be in `proposing`.
Adapter: `recovery_controller._minimax_adapter` (default raises 503).

**Status-code mapping**:
- `200` — proposal returned, run advanced to `reviewing`.
- `404` — `run_id` not in registry.
- `409` — run is not in `proposing` (run state surfaced in response).
- `422` — body validation failure or adapter returned malformed data.
- `503` — provider not configured (generic message; see below).

### `POST /api/code-operator/recovery/review`

| Field         | Type   | Notes                              |
| ------------- | ------ | ---------------------------------- |
| `run_id`      | string | as above                           |
| `proposal_id` | string | must match the run's `proposal_id` |

Service: `recovery_controller.review_proposal`.
Adapter: `recovery_controller._deepseek_adapter` (default raises 503).

Verdict in response: `approved | rejected | needs-revision`.
On `approved` the run transitions to `awaiting_human_confirm`. On
`rejected` / `needs-revision` the run stays in `reviewing` (caller can
re-`propose`).

### `POST /api/code-operator/recovery/apply`

| Field         | Type    | Notes                                          |
| ------------- | ------- | ---------------------------------------------- |
| `run_id`      | string  | as above                                       |
| `proposal_id` | string  | must match                                     |
| `confirm`     | boolean | **must be `true`** (confirm-by-default policy) |

Service: `recovery_controller.apply_proposal`.
Underlying call: `code_history.apply_reviewed_patch_proposal`
(already in-tree; this PR just wires it through the controller).

**Preconditions**:
- run state == `awaiting_human_confirm`,
- review verdict == `approved`,
- caller passes `confirm=true`.

**Status-code mapping**:
- `200` — patch applied, run transitions to `re_running_gate`.
- `409` — review pending / not approved / proposal mismatch.
- `422` — `confirm=false` (confirm-by-default).
- `502` — apply itself raised; saga compensation has already run
  (`mark_recovery_outcome("retry_failed")` + run transitioned to
  `retry_failed`).

### `POST /api/code-operator/recovery/resume`

| Field     | Type            | Notes                                |
| --------- | --------------- | ------------------------------------ |
| `run_id`  | string          | as above                             |
| `gate_id` | string \| null  | override; defaults to `failed_step`  |

Service: `recovery_controller.resume_run`.
Underlying call: `code_history.run_mcp_gate`.

If the gate passes, the run transitions to `recovered`,
`mark_recovery_outcome("recovered")` writes the v1 outcome row, and
`thaw_run` releases all file locks. If the gate fails, the run
transitions to `escalated`, the v1 outcome row is closed with that
status, and locks are still released.

## Auth

All four routes use the same auth scheme as the rest of the
`code_operator` router. `api/app.py` reads `HERMES3D_API_TOKEN` from the
environment; when set, every request needs `Authorization: Bearer <token>`.
When unset (the default in dev), the API is open. **No new auth surface
is added in this PR** — the existing scheme covers the new routes
because they are mounted on the same `router` instance.

## Data flow

1. **Request** arrives at the route handler (`code_operator.py`).
2. **Body validation** via Pydantic `StrictBody` model (extra fields
   forbidden). 32-char `run_id` constraint matches the
   `code_history` attempt-id format.
3. **Service dispatch** to `recovery_controller.<method>`.
4. **Pre-state check** under `_REGISTRY_LOCK`: run exists, in expected
   state, proposal_id matches if applicable.
5. **MCP locks** were already acquired in `freeze_run` (saga step 2).
   The active-loop methods do NOT re-lock; they assume the run's
   `locked_files` are still held.
6. **LLM call** via the swappable adapter. The adapter receives a
   redacted request dict and is responsible for its own auth +
   timeouts. Provider failures bubble up as `ProviderNotConfigured`
   (mapped to 503) or generic exceptions (caught + redacted).
7. **Proof event** written to `proof_events` via
   `_emit_phase_proof`. Each phase emits a unique `event_type`
   (`recovery_fix_proposal`, `recovery_review`, `recovery_apply`,
   `recovery_resume`, `recovery_escalated`,
   `recovery_apply_failed`, `recovery_resume_gate_error`). Every row
   carries `version_label` / `upstream_tag` / `checkout_path` per
   PR #168.
8. **DB write** is best-effort: if `proof_events` insert fails (e.g.
   sqlite not initialized in a unit-test path), the helper returns
   `None` and the run still records the phase in its in-memory history.
9. **State transition** under `_REGISTRY_LOCK` via `_transition` —
   updates `last_event_utc`, appends to `history`, optionally marks
   the run terminal.
10. **Response** mirrors the run's `to_state_payload()` plus the new
    `proposal_record` / `review_record` / `apply_record` / `resume_record`
    fields.

## Operator setup (with credentials)

The W5-7 runbook (`HERMES_AGENT_OPERATOR_RUNBOOK_2026-05-09.md`)
covers the credential-storage convention: secrets live OUTSIDE every
repo workspace at `G:/private/` per the user's MEMORY rule
`reference_secret_storage`. To wire a real provider:

1. Place the API key in a private env file (e.g. `G:/private/hermes-providers.env`).
2. In your supervisor / launcher, source the file before starting
   the FastAPI app so the adapter sees the key.
3. Implement the adapter to read the key + dispatch the call. A
   skeleton:

```python
from hermes3d.services import recovery_controller

def my_minimax_adapter(request: dict) -> dict:
    # request keys: attempt_id, task_id, failed_step, failure_class,
    # failure_summary (already redacted), context_pack, agent_stack
    api_key = os.environ["MY_PROVIDER_KEY"]  # NEVER hardcode
    response = httpx.post(
        "https://your-provider/v1/coding-pass",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"prompt": request["failure_summary"], ...},
        timeout=60,
    )
    payload = response.json()
    return {
        "proposal_id": payload["id"],
        "files_touched": payload["files"],
        "rationale": payload["explanation"],
        "model_meta": {
            "provider": "my_provider",
            "model": payload["model"],
            "credit_spent_usd": float(payload.get("cost_usd", 0)),
            "cost_usd": float(payload.get("cost_usd", 0)),
        },
    }

recovery_controller._minimax_adapter = my_minimax_adapter
```

4. Same shape for the DeepSeek (review) adapter; verdict must be one
   of `approved | rejected | needs-revision`.

5. **No paid services**: per the user's MEMORY rule
   `feedback_no_paid_services`, this codebase MUST NOT auto-spend
   real credit. Every adapter the project bundles defaults to
   raising `ProviderNotConfigured`. If you wire a paid provider in a
   private fork, set spending caps at the provider account level.

## Saga compensation: what happens when apply fails

The saga pattern (Garcia-Molina + Salem 1987) defines a long-lived
transaction as a sequence of compensable local transactions. RC v2's
freeze step (lock + snapshot) is already a saga; the active loop adds
`apply_proposal` as the highest-stakes step.

**Apply failure compensation** (when `code_history.apply_reviewed_patch_proposal`
raises):

1. A `recovery_apply_failed` proof event is written with the redacted
   error class + summary.
2. `code_history.mark_recovery_outcome(status="retry_failed", ...)`
   closes the v1 ledger row with the apply failure as the final
   outcome.
3. The run transitions `APPLYING -> RETRY_FAILED` (terminal). It can
   no longer be addressed by `propose` / `review` / `apply` — those
   routes return `404` or `409` because the run is terminal.
4. The proposal record stays on the run (`run.proposal_record`,
   `run.review_record`) for forensic review.
5. **File locks remain held** until an operator explicitly calls
   `thaw_run` (or the lock TTL expires after 30 min). This is
   intentional: a partially-applied patch is the worst outcome, and
   keeping the locks prevents another agent from racing into the
   same files until the operator has assessed damage.
6. If the operator decides to retry, they start a **new** recovery
   run for the same failure (the idempotency index does not reuse
   terminal runs).

**Why the proposal stays addressable**: the request URL keeps
`proposal_id` so audit logs can correlate later forensic queries.
A re-apply against the same proposal is impossible because the run
is terminal; a new run can reuse the same `proposal_id` only if the
proposal source (the patch text) is still in `code_history`'s
proposal store, which it always is — proposals are not garbage
collected.

## Tests

`04_testing/pytest/integration/test_rc_v2_active_loop.py` — 8 tests:

| # | Test                                                                  | Result    |
| - | --------------------------------------------------------------------- | --------- |
| 1 | `/propose` 503 when no provider configured                            | PASS      |
| 2 | `/propose` 200 + ProposalRecord with mocked MiniMax                   | PASS      |
| 3 | `/review` 200 + ReviewRecord(approved) with mocked DeepSeek           | PASS      |
| 4 | `/apply` 409 when review pending or rejected                          | PASS      |
| 5 | `/apply` 200 + ApplyRecord with approved review + mocked patch        | PASS      |
| 6 | `/resume` runs gate; green->resumed, red->escalated                   | PASS      |
| 7 | End-to-end sequence ordering (failure->...->thaw)                     | PASS      |
| 8 | `credit_spent_usd == 0.0` for every mocked LLM call                   | PASS      |

All adapters mocked via `monkeypatch.setattr` on the module-level
`_minimax_adapter` / `_deepseek_adapter` callables. **No real LLM
calls in the test path.** The v1 ledger primitives
(`code_history.lock_mcp_files`, `release_mcp_files`, `snapshot_file`,
`record_step_failure`, `mark_recovery_outcome`,
`apply_reviewed_patch_proposal`, `run_mcp_gate`, `append_mcp_evidence`)
are also stubbed so the suite runs free of orchestrator I/O.

## Sources

1. **Saga pattern** — Garcia-Molina, H. & Salem, K. (1987). "Sagas."
   ACM SIGMOD Record, 16(3): 249-259. The compensation rule
   (`apply_proposal` failure -> close v1 row + RETRY_FAILED + locks
   held until operator review) follows the original "compensating
   action is the inverse of the local transaction" pattern.
   See <https://temporal.io/blog/saga-pattern-made-easy> for a
   modern reference impl.

2. **FastAPI bigger-applications router pattern** — the four new
   routes are appended to the existing `code_operator` `APIRouter`
   instance (rather than living in a new module) because they share
   the same prefix, tags, and validation chain. This matches the
   project's existing layout and the official guide:
   <https://fastapi.tiangolo.com/tutorial/bigger-applications/>

## Files changed

| Path                                                                              | Lines      |
| --------------------------------------------------------------------------------- | ---------- |
| `03_implementation/src/hermes3d/services/recovery_controller.py`                  | +540       |
| `03_implementation/src/hermes3d/api/routes/code_operator.py`                      | +210       |
| `04_testing/pytest/integration/test_rc_v2_active_loop.py`                         | +470 (new) |
| `03_implementation/docs/handoffs/HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md`          | +new       |

## Hermes MCP locks

Owner: `claude-w6-2-rc-active-loop`
Files locked for the duration of the PR:

- `03_implementation/src/hermes3d/services/recovery_controller.py`
- `03_implementation/src/hermes3d/api/routes/code_operator.py`
- `04_testing/pytest/integration/test_rc_v2_active_loop.py`
- `03_implementation/docs/handoffs/HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md`

Released on PR open.
