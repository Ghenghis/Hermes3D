# Claude Provider Completion Prompt

Date: 2026-05-08  
Owner: Codex  
Target repo: `G:\Github\h3d-gui-wiring-codex`  
Goal: make Hermes Agents, OpenCode, and OpenHands run a real proof-gated coding loop without stale provider assumptions or secret exposure.

## Paste This To Claude

You are continuing Hermes3D OS provider/runtime completion. Stay focused. Do not add new feature slices, theme work, marketing copy, app catalog expansion, or speculative architecture. The only goal is to make the existing Hermes Agent coding loop work with truth, proof, MCP locks, OpenCode/OpenHands readiness, and provider smoke evidence.

Hard rules:

- Use Hermes MCP locks for every edit: claim task, verify exact `MCP_LOCK_WORKSPACE`, lock files, heartbeat, append evidence, release files, release task.
- Never print, log, screenshot, serialize, paste, diff, commit, or expose private key values. You may use `G:\private\.env` through approved backend adapters only. You may name env keys and redacted sources only.
- Do not read or restore `G:\private\.env2.txt`; Codex consumed it, selected the authenticated MiniMax slot, updated `G:\private\.env`, and deleted `.env2.txt`.
- Do not claim Hermes Agents are working until both provider smoke routes return `accepted: true` and the first real coding task completes: task claim -> file locks -> snapshots -> MiniMax build -> DeepSeek review -> apply reviewed patch -> gates -> commit/PR -> evidence -> release locks.
- OpenCode/OpenHands are helper CLIs behind the Hermes lock/sandbox/review gate. They must not run unmanaged write commands from chat.
- S1 `192.168.0.12` remains camera/read-only. No move, upload, print, heat, or test.

Current truth state from Codex:

- Backend runs from `G:\Github\h3d-gui-wiring-codex\03_implementation`.
- MiniMax provider wiring was corrected to prefer explicit highspeed token-plan aliases: `HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY`, `MINIMAX_TOKEN_PLAN_API_KEY`, `HERMES3D_MINIMAX_HIGHSPEED_API_KEY`, then `MINIMAX_HIGHSPEED_API_KEY`; generic MiniMax/OpenAI aliases remain fallback only.
- MiniMax model is `MiniMax-M2.7-highspeed` for the user's Max-Highspeed plan. The plan can also support multiple MiniMax feature families (chat/coding, image, voice, music, and other provider-listed models) through capability-specific model/env config. Do not hardcode one chat model as the entire provider.
- User reports Max-Highspeed plan through May 20 with TPS 100 and 15,000 requests per 5 hours. Hermes should support controlled parallel provider work once smoke passes: 2-4 lanes for normal work, 2-8 lanes for broad audit/research, and 2-12 lanes only for explicitly approved high-volume rescue/completion waves. It should not artificially serialize all MiniMax work behind one lane, but every lane must keep per-task proof, budget, and safety gates.
- DeepSeek routing should also be multi-lane: use `deepseek-v4-pro` for high-value review/reasoning and `deepseek-v4-flash` when official docs and task scope favor fast review/triage. Do not downgrade the V4 Pro coding-review lane to legacy `deepseek-chat`.
- Live MiniMax smoke now reads `private_env:HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY` and `private_env:OPENAI_BASE_URL`; it reaches `api.minimax.io` and returns HTTP 429 `insufficient_balance (1008)`. This is no longer a stale-auth, wrong-model, or wrong-alias bug.
- DeepSeek model is `deepseek-v4-pro`. Do not downgrade it to `deepseek-chat` unless the user explicitly asks.
- DeepSeek V4 Pro payload must include `model=deepseek-v4-pro`, `messages`, `max_tokens`, `thinking={"type":"enabled"}`, and `reasoning_effort="high"`.
- Live DeepSeek smoke reads `private_env:DEEPSEEK_API_KEY`, `private_env:DEEPSEEK_BASE_URL`, and `private_env:DEEPSEEK_MODEL`; it still returns HTTP 401. Treat this as configured private env value/account/access/endpoint rejection, not proof the model is invalid.
- OpenCode and OpenHands are detected and sandbox-ready for preflight; write execution remains blocked until provider smoke passes and the full lock/review/gate chain runs.
- Evidence IDs to preserve:
  - `ev_01bbc444b58357f4`: current MiniMax smoke, HTTP 429 insufficient balance using private env explicit token-plan binding.
  - `ev_ff7d845319c5b745`: current DeepSeek smoke, HTTP 401 using private env DeepSeek binding.
  - `ev_3ad2267cb0d2c42f`: Codex provider-smoke summary, no secrets exposed.

Required official research:

- MiniMax: read the current official API overview and chat docs at `https://platform.minimax.io/docs/api-reference/api-overview`. Confirm `MiniMax-M2.7-highspeed`, token-plan/OpenAI-compatible base URL behavior, auth header shape, quota/balance error semantics, and payload token field.
- DeepSeek: read the current official docs at `https://api-docs.deepseek.com/`. Confirm `deepseek-v4-pro`, auth header shape, base URL, chat path, `thinking`, and `reasoning_effort`.
- Do not use stale handoff claims as provider truth if official docs disagree.

Use these agents:

1. MiniMax official-docs agent: verify endpoint, model id, payload, quota/balance behavior, Token Plan key exclusivity, highspeed plan TPS/concurrency semantics, and capability families usable under the plan. Output exact non-secret correction notes only.
2. MiniMax smoke/classifier agent: re-run the Hermes smoke route after backend reload. Confirm whether result is `accepted`, `429 insufficient_balance`, or another redacted status. No key output.
3. DeepSeek official-docs agent: verify V4 Pro payload and whether any extra V4 parameters are required beyond current payload. Output only doc-backed findings.
4. DeepSeek smoke/classifier agent: re-run official path variants and Hermes smoke with redacted output. If 401 persists, identify whether Hermes is reading the wrong env alias or whether the configured value is rejected by DeepSeek.
5. Env-binding auditor: check only env key names, redacted sources, value length/prefix family. Never print values. Confirm `.env2.txt` is absent.
6. Code adapter auditor: inspect provider config, payload generation, error summaries, and tests for stale names like `MiniMax-M2.7`, invented model IDs, or "deepseek-v4-pro invalid" claims.
7. OpenCode/OpenHands sandbox auditor: verify CLI detection, version, Docker sandbox, network policy, denied paths, and write-block behavior.
8. First-loop readiness agent: only after both providers return `accepted: true`, run the smallest possible proof-gated task through Hermes Agents. Use a harmless one-line docs/test label change.
9. Multi-lane provider routing agent: draft follow-up config for MiniMax chat/image/voice/music and DeepSeek V4 Pro/V4 Flash lanes, but do not mark any lane runnable until its own live smoke/proof passes.
10. Secret/security auditor: scan changed files, logs, proof bundles, PR bodies, screenshots, and markdown for leaked secrets or raw auth headers.
11. Gate/PR auditor: run required tests, no-fake scan, py_compile, provider smoke, and verify branch/commit/PR proof before done.

Minimum commands/probes, with redacted output only:

```powershell
curl.exe -s http://127.0.0.1:8765/api/system/runtime-identity

$body = @{ provider_id = 'minimax'; task_id = 'H3D-CLAUDE-PROVIDER-COMPLETION' } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/code-operator/providers/smoke' -Method Post -ContentType 'application/json' -Body $body

$body = @{ provider_id = 'deepseek'; task_id = 'H3D-CLAUDE-PROVIDER-COMPLETION' } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/code-operator/providers/smoke' -Method Post -ContentType 'application/json' -Body $body

python -m pytest 04_testing\pytest\unit\test_code_operator.py 04_testing\pytest\unit\gateways\test_minimax.py 04_testing\pytest\unit\gateways\test_deepseek.py -q
python 03_implementation\scripts\scan_active_ui_no_fake.py
git diff --check
```

Allowed corrections:

- Provider adapter code, tests, and docs that are demonstrably stale or wrong.
- Redacted provider error classification so the UI says the real class of blocker.
- Backend reload/start commands needed to prove current code is active.
- First proof-task execution only after both provider smokes pass.

Blocked / not allowed:

- No raw key display.
- No editing private env in tracked docs.
- No "accepted" or "working" claim from HTTP 429 or HTTP 401.
- No fake local fallback in place of MiniMax + DeepSeek proof.
- No bulk merge or merge-on-green-only behavior.
- No OpenCode/OpenHands write run unless provider smoke, MCP locks, snapshots, review, gates, and rollback proof are complete.

Completion criteria:

1. Provider docs checked against live code.
2. MiniMax smoke is either `accepted:true` or correctly reported as provider-side quota/balance blocked using `MiniMax-M2.7-highspeed`.
3. DeepSeek smoke is either `accepted:true` or correctly reported with exact redacted auth/access blocker using `deepseek-v4-pro`.
4. No stale provider names or invented model IDs remain in active code, tests, or current handoff docs.
5. OpenCode/OpenHands readiness remains sandboxed and fail-closed.
6. If both providers pass, one real low-risk Hermes Agent coding loop runs end to end and creates a PR with proof.
7. If either provider remains blocked, produce a precise non-secret blocker report with evidence IDs and stop provider-backed write execution only, while leaving non-provider gates and PR cleanup ready.
8. All locks released and `git status --short` reported.

Final answer must say exactly:

- What works now.
- What is still blocked, with evidence ID.
- Whether Hermes Agents can run a real coding PR now.
- Which file/branch/PR contains the fix.
- Confirmation that no private values were exposed.
