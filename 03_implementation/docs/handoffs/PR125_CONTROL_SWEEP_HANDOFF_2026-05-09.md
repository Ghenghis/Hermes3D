# PR #125 Control Sweep Handoff

> **POST-MERGE 2026-05-09T07:09Z (W5-8b doc-fix):** PR #125 was MERGED on 2026-05-09T07:09:15Z. The body of this doc is the **pre-merge sweep record** authored before that merge landed; it is preserved verbatim for the audit trail. Treat every "OPEN, CLEAN" / "not merged yet" reference below as historical state, not current state.
>
> **Provider rescue update (W5-8b doc-fix):** the §"MiniMax BLOCKED HTTP 429" / "DeepSeek BLOCKED HTTP 401" rows in the audit table below are **superseded** by `PROVIDER_RESCUE_BLOCKER_PROOF_2026-05-09.md:L1-9` ("SUPERSEDED — Providers Now PASS", `accepted:true` HTTP 200, evidence `ev_4a52d9b1336ca9f2` MiniMax + `ev_e708071cb269f170` DeepSeek). The original BLOCKED state was an out-of-repo `.env` issue, not a code bug.

Date: 2026-05-09  
Contract: PR #125 `docs(agent): tighten control gates` — OPEN, CLEAN  *(see banner above; merged 2026-05-09T07:09:15Z)*  
Executed by: claude-sweep-docs (task H3D-PR125-SWEEP-DOCS)  
Workspace: G:\Github\h3d-gui-wiring-codex  
Branch: codex/claude-hermes-runtime-finish-contract-2026-05-08  
MCP workspace: G:\Github\Hermes3D (state dir) / G:\Github\h3d-gui-wiring-codex (edit workspace)  
MCP workspace match: VERIFIED

---

## 10-Agent Audit Results

| Agent | Role | Status | Evidence |
|---|---|---|---|
| A1 | PR merge/conflict matrix | PASS | See matrix below |
| A2 | MCP lock/zombie audit | PASS | 2 stale locks recovered, 0 remaining |
| A3 | Secret leak audit | PASS | No values found; test fixtures use placeholders only |
| A4 | MiniMax/DeepSeek smoke | BLOCKED | MiniMax now reaches the token-plan endpoint and returns HTTP 429 insufficient balance; DeepSeek still returns HTTP 401 from the configured private env binding |
| A5 | OpenCode/OpenHands/sandbox | PASS | Both detected, sandbox READY, write policy-blocked |
| A6 | E2E code loop | BLOCKED | Blocked by provider auth failures |
| A7 | Source OS 60-app runners | PASS | 60 apps, 0 unknown families, 53 verifiers |
| A8 | UI no-fake/stale-route | PASS | 81 files scanned, 0 fake markers |
| A9 | Printer safety/S1 lock | PASS | S1 camera-only at all 3 layers (backend/frontend/observe) |
| A10 | Docs/roadmap vs PR #125 | NEEDS-FIX (non-blocking) | PR #125 not merged yet; ROADMAP.md updates pending merge |

---

## Step 1 Reality Check

| Check | Result |
|---|---|
| MCP Doctor | PASS — workspace writable, git ok, Node v25.8.2 |
| Active locks | 0 (2 zombie I12 locks recovered) |
| Open PRs | 18 open, all CLEAN |
| PR #125 | OPEN, CLEAN, CodeRabbit PASS — treating as controlling contract |
| Backend running | G:\Github\h3d-gui-wiring-codex, branch codex/claude-hermes-runtime-finish-contract-2026-05-08, commit c5c51148067c |
| Backend dirty | YES — untracked docs only (this report + HERMES_RUNTIME_FINISH_REPORT.md) |
| MCP workspace match | PASS — configured_workspace matches edit_workspace |

---

## PR Merge Matrix

All 18 open PRs target `feat/hermes3d-7-complete-gui-repo-wiring` (except #109 → `develop`).

**Safe merge sequence (into `feat/hermes3d-7-complete-gui-repo-wiring`):**

```
 1. #108  docs(handoff): Claude 24-agent completion contract         CLEAN — merge first
 2. #116  proof(I14): no-fake sweep 2026-05-08 — 81 files, PASS     CLEAN — proof/scripts only
 3. #111  test(I8): printer safety — S1 camera-lock tests            CLEAN — no conflicts
 4. #119  fix(I4): runner_family 60 rows                             CLEAN — modules.py only
 5. #112  fix(I1): provider auth config audit                        CLEAN — code_history.py FIRST
 6. #118  feat(I2): E2E code loop /e2e/jobs                          CLEAN — code_history.py SECOND
 7. #121  feat(I3): OpenCode/OpenHands sandbox readiness             CLEAN — code_history.py + Agents.tsx THIRD
 8. #120  feat(I7): firmware source inventory probes                 CLEAN — module_runtime.py FIRST
 9. #122  feat(I6): service/web-app health probes                    CLEAN — module_runtime.py SECOND
10. #123  fix(I5): slicer/modeler CLI probes                         CLEAN — module_runtime.py THIRD
11. #110  fix(I10): polling lag, sidebar layout                      CLEAN — UI only
12. #114  fix(I11): SourceOS 60-row rendering                        CLEAN — SourceOS.tsx only
13. #113  fix(I13): print workflow no fake states                    CLEAN — Dashboard/Jobs/Printers/Autopilot
14. #115  fix(observe): camera health probing                        CLEAN — Observe.tsx only
15. #117  fix(I12): agent chat/voice/learning                        CLEAN — Agents.tsx AFTER #121
16. #124  docs(handoff): tighten Hermes runtime finish contract      CLEAN — docs only
17. #125  docs(agent): tighten control gates  [CONTROLLING CONTRACT] CLEAN — merge last after all above
```

Then: `feat/hermes3d-7-complete-gui-repo-wiring` → `main`  
Separately: `#109 docs(readme,pages)` → `develop`

**Conflict chains that must NOT be broken:**
- `code_history.py`: #112 → #118 → #121 (in order)
- `module_runtime.py`: #120 → #122 → #123 (in order)
- `Agents.tsx`: #121 → #117 (in order)

---

## Provider Smoke Result (A4)

| Provider | Key Env | Base URL Host | Model | Status | Evidence ID |
|---|---|---|---|---|---|
| minimax | OPENAI_API_KEY / OPENAI_BASE_URL token-plan binding from `G:/private/.env`; MiniMax aliases accepted as fallback | api.minimax.io | MiniMax-M2.7-highspeed | **BLOCKED HTTP 429: insufficient balance/quota** | ev_0f7b0fe27dd0b49a |
| deepseek | DEEPSEEK_API_KEY | api.deepseek.com | deepseek-v4-pro | **BLOCKED HTTP 401: configured private env value rejected by DeepSeek** | ev_0a7d65d00436a1b8 |

**Per PR #125 non-negotiable rule 7:** MiniMax and DeepSeek are NOT working until real chat-completions smoke passes. Hermes Agent coding loop is BLOCKED.

**Required user actions (env values must never appear here — key names only):**
1. Keep `MINIMAX_MODEL=MiniMax-M2.7-highspeed` for the user's MiniMax Highspeed 2.7 token plan.
2. Keep the working MiniMax token-plan binding in `G:/private/.env`: `OPENAI_API_KEY` and `OPENAI_BASE_URL` are now accepted for the MiniMax lane; MiniMax-specific aliases remain accepted as fallback. `G:/private/.env2.txt` was consumed and deleted after selecting the authenticated MiniMax candidate.
3. Resolve the MiniMax provider-side `insufficient_balance (1008)` / HTTP 429 condition outside the repo before the builder lane can spend tokens.
4. Keep `DEEPSEEK_MODEL=deepseek-v4-pro` when using the current DeepSeek V4 Pro API model. Do not downgrade to older aliases unless the user explicitly chooses them.
5. Verify that `DEEPSEEK_API_KEY` in `G:/private/.env` is the exact API key that works against the DeepSeek API site; both official path variants returned HTTP 401 with the configured private env value.
6. After updating provider account/env state, restart the backend and re-run `/api/code-operator/providers/smoke` for each provider.

---

## OpenCode / OpenHands Audit (A5)

| Runner | Executable | Version | Sandbox | Write | Policy |
|---|---|---|---|---|---|
| OpenCode | G:/Github/opencode-dev/.../opencode.exe | 1.4.3-hermes3d | READY | BLOCKED | Detect/preflight only until provider smoke + MCP locks + gates pass |
| OpenHands | C:/Users/Admin/.local/bin/openhands.exe | 1.16.0 | READY | BLOCKED | Detect/preflight only |
| Docker sandbox | ghcr.io/openhands/openhands:latest | 29.4.1 | READY | N/A | network=none, denied paths enforced |

Write execution unlocks only after: provider smoke PASS + same-owner MCP locks + snapshots + reviewed patch + gates + rollback proof.

---

## Secret Safety Verdict (A3): PASS

- No API key values, bearer tokens, or credentials found in any tracked file
- Test fixtures use explicit placeholder strings (e.g. `sk-SECRETPLACEHOLDERDONOTLOG`)
- `G:/private/.env` is outside the repo, not tracked by git
- All proof bundles contain only env key NAMES and redacted source labels
- No private values appear in any PR body, markdown, CI output, or frontend

---

## Printer Safety Verdict (A9): PASS

S1 (192.168.0.12) camera-only enforcement verified at all three layers:
- `printers.py`: `CAMERA_ONLY_IPS = frozenset({"192.168.0.12"})`, HTTP 403 on all write routes
- `observe.py`: S1 routes are camera-only HEAD/GET, no control commands
- `Printers.tsx`: UI disables all S1 write controls with policy warning message

T1 `192.168.0.10`, T1 `192.168.0.11`, V400 `192.168.0.34` — all write routes are policy-gated through backend.

---

## MCP Lock Release Status

| Lock | Status |
|---|---|
| claude-a1-pr121-fix / Agents.tsx | RELEASED (previous session) |
| claude-24agent-i12 / Learning.tsx | RECOVERED (zombie TTL expired) |
| claude-24agent-i12 / Voice.tsx | RECOVERED (zombie TTL expired) |
| claude-sweep-docs / PR125_CONTROL_SWEEP_HANDOFF_2026-05-09.md | ACTIVE (this task) |
| claude-sweep-docs / HERMES_RUNTIME_FINISH_REPORT.md | ACTIVE (this task) |

All other 24-agent wave locks expired and were recovered. Lock state is clean.

---

## Hermes Agent / OpenCode / OpenHands Readiness

| Subsystem | Status | Notes |
|---|---|---|
| MCP locks | READY | Workspace-matched, doctor PASS |
| Folder index | READY | 11 docs loaded into E2E readiness |
| Nous Hermes source | READY | 73bf3ab1b at G:/Github/hermes-agent-fresh |
| Docker sandbox | READY | v29.4.1, network=none |
| OpenCode CLI | READY (preflight) | Write blocked by policy |
| OpenHands CLI | READY (preflight) | Write blocked by policy |
| MiniMax provider | **BLOCKED** | HTTP 429 insufficient balance/quota — auth path now reaches the highspeed token-plan endpoint |
| DeepSeek provider | **BLOCKED** | HTTP 401 — configured private env value rejected by DeepSeek; `deepseek-v4-pro` is a current provider-listed model |
| E2E code loop | **BLOCKED** | Cannot run until both providers pass smoke |
| First proof PR | NOT RUN | Blocked by provider auth |
| **Overall verdict** | **BLOCKED** | |

---

## Exact Next Actions for Codex

**STOP condition per PR #125:** Do not run E2E coding loop, apply patches, or call any provider-backed execution until provider smoke returns `accepted: true`.

**Priority order:**

1. **[USER ACTION REQUIRED] Fix `G:/private/.env`:**
   - Env key: `DEEPSEEK_MODEL` → keep the provider-listed `deepseek-v4-pro`
   - Env key: `DEEPSEEK_API_KEY` → verify it is the exact API key that passes the official DeepSeek API smoke
   - Env keys: `OPENAI_API_KEY` / `OPENAI_BASE_URL` → keep the MiniMax token-plan binding Hermes now reads
   - Env key: `MINIMAX_MODEL` → keep `MiniMax-M2.7-highspeed`
   - Provider account state: resolve MiniMax HTTP 429 `insufficient_balance (1008)` before builder execution
   - Restart backend after provider/env changes
   - Re-run `POST /api/code-operator/providers/smoke` for each provider
   - Do not proceed to step 2 until both return `accepted: true`

2. **[CODEX] Merge PRs in sequence after PR #121 CI green:**
   Follow the 17-step merge sequence above into `feat/hermes3d-7-complete-gui-repo-wiring`. Use `gh pr merge <N> --squash --delete-branch` one at a time. After each merge, verify next PR still shows CLEAN before merging it.

3. **[CODEX/CLAUDE] First proof task after provider auth passes:**
   Select one low-risk file (e.g., a one-word label fix in `03_implementation/ROADMAP.md` or a test fixture). Run the full loop: `hermes_claim_task → hermes_lock_files → snapshot → POST /api/code-operator/providers/smoke (both PASS) → MiniMax build pass → DeepSeek review pass → apply patch → gates → branch/commit/push → PR → evidence → hermes_release_files → hermes_release_task`. All proof IDs must be recorded. Only then is Hermes Agents `PASS`.

---

## All Proof IDs This Session

| ID | Kind | Summary |
|---|---|---|
| ev_ffa9a8c3e3bd4a40 | gate | tsc PASS after TS6133 fix in Agents.tsx |
| ev_3ef0c842f7148e83 | commit | 6c348f9 pushed to PR #121 branch |
| ev_dbf23c31c04af4ca | code_provider_smoke | Historical MiniMax smoke BLOCKED HTTP 401 before adapter correction |
| ev_a736131a4b0d8c6e | code_provider_smoke | Historical DeepSeek smoke BLOCKED HTTP 401 |
| ev_e8ed04d923a294c9 | code_provider_smoke | Interim MiniMax smoke reached highspeed token-plan binding before `.env2` consolidation, BLOCKED HTTP 429 insufficient balance |
| ev_5702585f7b8a83a7 | code_provider_smoke | Interim DeepSeek smoke BLOCKED HTTP 401 with configured private env binding |
| ev_0f7b0fe27dd0b49a | code_provider_smoke | Current MiniMax smoke reads `G:/private/.env` `OPENAI_API_KEY`/`OPENAI_BASE_URL`, BLOCKED HTTP 429 insufficient balance |
| ev_0a7d65d00436a1b8 | code_provider_smoke | Current DeepSeek smoke reads `G:/private/.env` and remains BLOCKED HTTP 401 |
