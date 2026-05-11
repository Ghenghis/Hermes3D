# W18-A4 Hermes Agent Workflow Proof

**Wave / Agent:** W18 / A4
**Date:** 2026-05-11
**Branch:** `claude/w18-a4-agent-workflow`
**Base commit:** `330f521` (`develop`)
**Owner:** `w18-a4` (audit-only)
**Status:** **PASS_REAL**

## Mission recap

Prove from the live Hermes3D GUI that a user can (1) select a Hermes Agent in the
UI, (2) send a real task, (3) receive a real response via real network round-trip,
and (4) see the response content rendered in the UI. No mocks anywhere in the path.

## Verdict

`PASS_REAL` — the full chain is wired and observable end-to-end.

| Step | Surface | Real? | Evidence |
| --- | --- | --- | --- |
| Persona select | `AgentChatMirror` `<select>` in left rail | yes | Roster fetched from `GET /api/agents` (real backend) — 8 personas, `model_provider=local_llm_runtime` |
| Task submit | `<textarea aria-label="Message selected Hermes agent">` + Send button | yes | `POST /api/agents/print-safety-agent/chat` with HTTP 200, 188,986 byte streamed response |
| LLM round-trip | `_runtime_chat_stream` -> `HERMES3D_AGENT_RUNTIME_URL` | yes | proof_events row `hermes_agent_chat_runtime_request` with `runtime_configured=1`, `resolved_model=qwen3.5-9b-glm5.1-distill-v1`, `active_surface=#dashboard:advanced` |
| UI render | assistant message block in `AgentChatMirror` history | yes | DOM block contains literal `W18-A4-PROOF-PING`; spec assertion passed |

## Artifacts

All paths absolute, under `G:\Github\Hermes3D\03_implementation\ui\`:

- Playwright spec: `tests\e2e\w18-a4-agent-workflow.spec.ts`
- HAR (record mode, real round-trip): `test-results\w18-a4\hermes-agent.har` (7,519,560 bytes)
- Screenshot before submit: `test-results\w18-a4\before-send.png`
- Screenshot after assistant reply: `test-results\w18-a4\after-reply.png`
- Assistant reply text actually rendered: `test-results\w18-a4\assistant-reply.txt`
- Network summary: `test-results\w18-a4\network-summary.json`

## Real-handler proof (no fallback / no mock)

Backend code path executed (`03_implementation/src/hermes3d/api/routes/agents.py`):

- Line 176: `runtime_url = _trusted_runtime_url()` -> non-None (live LM Studio at 127.0.0.1:1234)
- Line 178: `async for frame in _runtime_chat_stream(...)` -> runtime branch chosen
- Lines 218-237: `INSERT INTO proof_events (..., 'hermes_agent_chat_runtime_request', ...)` with `runtime_configured=True`
- Lines 271-278: `INSERT INTO agent_conversations (..., 'assistant', 'RUNTIME_STREAM', ...)` with assistant text

DB confirms (table `agent_conversations` in `03_implementation/var/hermes3d.db`):

```
2026-05-11 10:28:50 | print-safety-agent | assistant | RUNTIME_STREAM | W18-A4-PROOF-PING
2026-05-11 10:28:43 | print-safety-agent | user      | TEXT           | Echo back the string 'W18-A4-PROOF-PING' verbatim and then stop.
```

DB confirms (table `proof_events`):

```
hermes_agent_chat_runtime_request | print-safety-agent | runtime_configured=1 | resolved_model=qwen3.5-9b-glm5.1-distill-v1 | active_surface=#dashboard:advanced
```

If the runtime had been absent or untrusted, the backend would have written a
`STATUS_UPDATE` message ("Live Hermes agent runtime is not configured yet.") and
no `proof_events` row would exist. The presence of the `RUNTIME_STREAM` row plus
the `proof_events` row proves the live LLM branch ran.

## HAR cross-check

The HAR captures the marker in three distinct places, none of which would be
populated by a mock:

1. Outbound request body: `POST /api/agents/print-safety-agent/chat` with
   `{"message":"Echo back the string 'W18-A4-PROOF-PING' verbatim and then stop."...}`
2. `GET /api/agents/{persona}/history` response containing the user message that
   the backend persisted to `agent_conversations`.
3. Outbound request to the speech-synthesis endpoint with
   `text: "W18-A4-PROOF-PING"` — the assistant reply that the UI received via
   SSE and forwarded for TTS, confirming the marker round-tripped from the LLM
   back into the running React app.

## Test command

```
cd 03_implementation/ui
npx playwright test --config=playwright.e2e.config.ts tests/e2e/w18-a4-agent-workflow.spec.ts
```

Result:

```
ok 1 [chromium-e2e] > W18-A4 Hermes Agent workflow proof > real persona chat round-trip echoes proof marker in UI (9.7s)
1 passed (20.9s)
```

## Environment confirmed

- Backend uvicorn on `127.0.0.1:8765` (already-running dev instance bound by `LIVE_BASE_URL`).
- Playwright `webServer` spawned a sibling backend on `127.0.0.1:8766` for tab smoke specs, but the AgentChatMirror UI is hardcoded to 8765 so chat traffic landed on the live backend (intentional — exercises the same backend a human user hits).
- LM Studio running locally at `http://127.0.0.1:1234` serving `qwen3.5-9b-glm5.1-distill-v1`.
- `G:\private\.env` provides `HERMES3D_AGENT_RUNTIME_URL` and `HERMES3D_AGENT_RUNTIME_MODEL` (per the strict secret-storage convention; nothing checked into the repo).

## Scope discipline

This audit did NOT touch:

- Backend code (`03_implementation/src/hermes3d/api/routes/agents.py`)
- UI runtime code (`03_implementation/ui/src/components/agents/AgentChatMirror.tsx`)
- `playwright.e2e.config.ts` or any shared helper

Only the new spec file and this handoff doc were added. Locks held under owner
`w18-a4`, role `audit`.
