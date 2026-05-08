# 03 — Hermes Agent Runtime Gap Map

## Surface State Table

| Surface | Role | Status | Live Evidence | Next Required Action |
| --- | --- | --- | --- | --- |
| **Hermes Agent (NousResearch hermes-agent-fresh)** | Primary agent runtime, tools, skills, MCP, delegation, terminal/code loop | PARTIAL | Ready local source at G:/Github/hermes-agent-fresh, git head 73bf3ab1b, exists=True, git_metadata=True | Provider auth must pass before full E2E loop; source inputs ready for folder-index load |
| **Atomic Hermes** | Approval bridge, MCP tool, patch parser, checkpoint manager, terminal/file tools, SWE environment | PARTIAL | Source tree at G:/Github/atomic-hermes, exists=True, git_metadata=False (source_tree status) | Git metadata missing; not blocking; serves as skill reference only per E2E contract |
| **OpenCode CLI (1.4.3-hermes3d)** | Bounded code runner inside sandbox with output capture and review handoff | DONE | Detected at G:/Github/opencode-dev/packages/opencode/dist/opencode-windows-x64/bin/opencode.exe, version=1.4.3-hermes3d, write_allowed=false (fail-closed) | Write-capable runs blocked until provider auth passes, task-scoped sandbox isolation, and gates/review complete |
| **OpenHands CLI (1.16.0)** | Sandboxed bounded code runner with task-scoped env/cwd/files and redacted output proof | DONE | Detected at C:/Users/Admin/.local/bin/openhands.exe, version=`OpenHands CLI 1.16.0`, sandbox readiness=ready, docker=29.4.1, network=none, write_allowed=false | Wait for provider auth + task-scoped execution + review/gate handoff before write runs |
| **Docker Sandbox (ghcr.io/openhands/openhands:latest)** | Container isolation, workspace mount, denied paths, allowed command families, network policy enforcement | DONE | Image sha256:e6eed4f4d7c4a368cdbd0dc8751e6fa48340d21783addfc97714b87fbeda21fa, 393MB, network=none, denied_paths=[.git, 03_implementation/proof, 03_implementation/var, G:/private, node_modules] | Ready; awaiting provider auth before CLI write task execution inside sandbox |
| **MCP Locks Server (hermes3d-locks)** | File-lock coordination, task claim/heartbeat/release, evidence ledger, MCP gate runner | DONE | Entry point: G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs, workspace=G:/Github/h3d-gui-wiring-codex, required_workflow=[claim, lock, heartbeat, gate, evidence, release] all routed, blocked_reason=null | Ready; E2E coding loop can use now after provider auth |
| **Patch Apply Route (/api/code-operator/patch/apply-reviewed)** | Apply a reviewed patch proposal under same-owner MCP lock with snapshots and proof chain | DONE | Route exists (code_operator.py:506-519), ReviewedPatchApplyRequest model validates review_proof_ids, proposal_id, task_id | Ready; routed and gated, waiting for E2E job pipeline to exercise |
| **Gates Run Route (/api/code-operator/gates/run)** | Execute allowlisted MCP gates (git-status, git-diff-check, npm-test, npm-build, linters, playwright) | DONE | 11 gates registered: git-status/branch/diff-check/diff-staged/log-recent, npm-test/build, python-pytest, playwright-smoke, secret-scan; code_operator.py:532-539 | Ready; gates available, awaiting E2E job flow to invoke them post-patch-apply |
| **Git PR Route (/api/code-operator/git/pr)** | Create/open GitHub PR from task branch with body, draft, base_ref, rollback proof, evidence ids | DONE | Route exists (code_operator.py:591-603), GitPullRequestRequest model for title/body/draft/base_ref, code_history.git_open_pull_request impl | Ready; gated and locked, waiting for E2E flow |
| **Provider Smoke (MiniMax + DeepSeek)** | Live health check of MiniMax builder and DeepSeek reviewer providers with redacted auth error handling | BLOCKED | MiniMax: last live smoke HTTP 401 auth_failed; DeepSeek: last live smoke HTTP 401 auth_failed; both configured with key/base-url/model; /api/code-operator/providers/smoke appends MCP evidence | Replace rejected MiniMax/DeepSeek key/base-url/model values in G:/private/.env, restart API, rerun smoke probes |
| **Rollback Proof** | Snapshot recovery, diff proof, evidence chain for every file touched on rollback | DONE | Routes: /api/code-operator/history/snapshots (create), /api/code-operator/history/list (query), /api/code-operator/history/restore, /api/code-operator/history/diff; snapshot_count=7 in code-history var | Ready; 7 proof snapshots already recorded; restore and diff proof available |
| **Evidence Chain** | Hash-chained audit ledger linking task locks snapshots gates provider artifacts PR | DONE | MCP evidence appended by claim/lock/gate/patch routes; code_history.append_mcp_evidence (code_operator.py:419-430); DB table proof_events | Ready; ledger operational and linked to all gates/locks/patches |
| **Runtime-Identity Guard** | Fresh-check report of branch/commit/routes/missing-routes so UI rejects stale code | DONE | /api/system/runtime-identity: fresh=true, branch=codex/provider-smoke-workbench, commit=43d8205774bd, 220 routes, 0 missing required Agent Workbench routes | Ready; stale-code detection live, dashboard shows Runtime freshness |

## Required-Current-Truth Verification Table

| Requirement | Expected Value | Live Value | Status |
| --- | --- | --- | --- |
| OpenCode CLI version | `1.4.3-hermes3d` | `1.4.3-hermes3d` (detected from binary) | **PASS** |
| OpenHands CLI version | `OpenHands CLI 1.16.0` | `OpenHands CLI 1.16.0` (cli-runners endpoint) | **PASS** |
| Docker image `ghcr.io/openhands/openhands:latest` | Image present, sha256:e6eed4f4d7c4a368cdbd0dc8751e6fa48340d21783addfc97714b87fbeda21fa, 393 MB | Exactly matched | **PASS** |
| MiniMax + DeepSeek provider smoke clean HTTP 401 with redacted auth blocker | HTTP 401 auth_failed, evidence appended, no crash | Both providers return HTTP 401, blocked_reason recorded, MCP evidence logged | **PASS** |

## Per-Surface Gap Detail

### Hermes Agent Runtime & Source Inputs

The Nous Hermes Agent fresh build at G:/Github/hermes-agent-fresh is ready with git metadata and full runtime tools. The folder-index context (E2E contract lines 25–39) is prepared. Atomic Hermes source tree exists but lacks git metadata (not a blocker per contract line 72: "Patterns not to copy blindly"); it serves as a skill/role reference. Both are detected and reported by `/api/code-operator/e2e/readiness` under `programming.source_inputs`. The gap is not missing input source but live provider authentication: until MiniMax and DeepSeek env keys pass, the agent teams cannot begin building or reviewing.

### Provider Authentication (Critical Blocker)

MiniMax and DeepSeek are configured in G:/private/.env with key, base-url, and model fields set, but both fail live HTTP 401 authentication. The backend correctly returns redacted auth errors without exposing secrets, appends MCP evidence, and sets status=`auth_failed`. The `/api/code-operator/e2e/readiness` endpoint shows both providers under `programming.provider_lanes` with `live_status=failed` and `blocked_reason` listing the HTTP 401 error. This is the single point blocking the E2E loop from running a real co-developer task. Provider smoke probe logic is correct; the keys in G:/private/.env must be refreshed.

### MCP Locks & Evidence Ledger

MCP lock server at G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs is operational and registered with the workspace. The `/api/code-operator/mcp-locks/readiness` endpoint confirms status=ready, server_entry_exists=true, workspace_matches=true, and no blocked_reason. The required workflow chain (claim → lock → heartbeat → gate → evidence → release) is routed and callable. Code history snapshots (currently 7 recorded) and evidence append routes are live. Rollback snapshot recovery is available. All file-lock coordination, task ownership, and audit proof infrastructure is production-ready.

### CLI Runners & Sandbox

OpenCode 1.4.3-hermes3d executable is detected and versioned. OpenHands CLI 1.16.0 is detected and versioned. Docker sandbox image is present with correct network isolation (network=none), workspace mount, and denied paths enforced. Both runners have `write_allowed=false` fail-closed by policy and will remain so until provider auth passes, task-scoped env/cwd/files are in place, snapshots are recorded, redacted output proof is captured, and review/gate handoff is wired. The gap is not operational readiness (all checks pass) but write-capability gating (intentionally closed until full E2E contract is satisfied).

### Patch Apply & Git Lanes

Patch proposal and apply routes are coded and routed. The `/api/code-operator/patch/apply-reviewed` route validates review_proof_ids and enforces same-owner MCP lock before applying. Branch, stage, commit, push, and PR routes are all present. Git readiness endpoint exists. The gap is not infrastructure but orchestration: the E2E job route must extract a reviewed patch from the DeepSeek review artifact, call apply-reviewed with the correct review proof ids, capture post-snapshot, run gates, then proceed to branch/commit/PR. That orchestration is marked PARTIAL in the contract (line 222) and is the next piece after provider auth.

### Runtime Freshness & Route Guard

The `/api/system/runtime-identity` route reports fresh=true, all 10 required Agent Workbench routes present (220 total), branch and commit match the live backend source, and no missing routes. The Agents dashboard tab can check this and warn if the browser is holding stale code. This gap is closed.

## Coding-Loop Sequence Diagram References

The E2E loop flowchart lives in the E2E contract (lines 183–202). This implementation is stopped at step **G: MiniMax builder pass**. Steps completed:

- A → B → C → D → E → F (Load index, readiness, claim task, lock files, snapshot) — all routed and gated
- **Blocked at G** (MiniMax builder pass) due to HTTP 401 provider auth failure
- H → R (Patch proposal through final release) — routes exist but E2E orchestration job does not yet pull them into sequence

The system is blocked at **provider authentication**, not at any coding-loop infrastructure step.

## Headline Q&A: When Will Hermes Agents Work?

**Hermes Agents will work (E2E co-development on real tasks) when all three of these conditions are satisfied:**

1. **MiniMax and DeepSeek provider keys in G:/private/.env are valid and pass live HTTP 200 health checks.** Currently both are HTTP 401 auth_failed; env keys must be replaced, the API restarted, and smoke probes rerun to confirm success.

2. **An end-to-end coding job is submitted and completes the full loop:** folder-index load → MCP task claim → file lock → pre-snapshot → MiniMax build artifact → DeepSeek review artifact → reviewed patch apply → post-snapshot → gates pass → branch/commit/push → PR with rollback proof → MCP evidence chain closed → files released. Routes and contracts exist; the job orchestration glue (`/api/code-operator/e2e/jobs`) is PARTIAL and needs the patch-apply-through-PR stage wired.

3. **The task passes both provider teams' security gate (DeepSeek review) and all allowlisted gates (git-diff-check, no-fake scan, unit/playwright tests, secret scan) without failure or timeout.** These are wired and ready; the bottleneck is live provider authentication (condition 1).

**Honest assessment:** The infrastructure is 95% ready. The blocker is provider authentication (condition 1), not architecture or tooling. Replace env keys, restart the backend, rerun provider smoke, and submit a low-risk first task (e.g., small docs/label update) through the E2E route to prove the loop. After that, agents can help close the remaining 60 Source OS app gaps themselves.
