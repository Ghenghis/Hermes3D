# Claude 10+ Agent Hermes Runtime Finish Contract

Updated: 2026-05-08
Owner: codex-master
Target repo: `G:/Github/h3d-gui-wiring-codex`
Remote: `https://github.com/Ghenghis/Hermes3D`
Primary goal: make Hermes Agents, OpenCode, and OpenHands complete one real proof-gated Hermes3D coding loop.

## Copy/Paste Command For Claude

Read this file in full:

`G:/Github/h3d-gui-wiring-codex/03_implementation/docs/handoffs/CLAUDE_10_AGENT_HERMES_RUNTIME_FINISH_CONTRACT_2026-05-08.md`

Then execute it exactly with 10 or more agents. Do not widen scope. Do not build more public-site polish, more Source OS rows, more screenshots, or more roadmap prose unless it directly fixes a blocker listed here.

The only mission is:

1. make the Hermes Agent coding loop real,
2. make OpenCode/OpenHands usable through Hermes3D's safe sandboxed contracts,
3. prove MiniMax builder and DeepSeek reviewer auth or report the exact redacted blocker,
4. fix any PR/check failures blocking this lane,
5. produce one real low-risk agent-made PR with locks, snapshots, review, gates, rollback proof, and evidence.

If an agent starts a new feature not required for that mission, stop it and redirect it.

## Why This Contract Exists

The project has made real progress, but the user is correctly frustrated that many things are still partial. The failure mode is scope drift: agents keep improving nearby surfaces instead of closing the central runtime loop.

This contract is a fence.

Hermes Agents are not "working" because the UI renders, because CLI binaries are detected, or because a plan artifact exists. Hermes Agents work only when they can help finish Hermes3D OS through this closed loop:

`intent -> folder index -> MCP task claim -> file locks -> pre-snapshots -> MiniMax build pass -> DeepSeek review pass -> reviewed patch -> apply under same-owner locks -> gates -> rollback proof -> branch -> commit -> push -> PR -> evidence -> release`

Until that chain passes on a real Hermes3D task, the system is `IN_PROGRESS`, not done.

## Current Truth Snapshot

Verified from local API/GitHub on 2026-05-08:

| Area | Current truth | Action |
| --- | --- | --- |
| MCP locks | Ready and workspace-matched to `G:/Github/h3d-gui-wiring-codex`. | Use for every edit. |
| Folder index | Ready and loaded by E2E readiness route. | Must be included in provider context. |
| Nous Hermes Agent source | Present at `G:/Github/hermes-agent-fresh`, git metadata ready. | Use as primary runtime/source reference. |
| Atomic Hermes source | Present at `G:/Github/atomic-hermes`, source tree only. | Use patterns only where they close rollback/snapshot gaps. |
| OpenCode CLI | Detected from private env, version `1.4.3-hermes3d`. | Preflight ok; write execution still blocked by policy. |
| OpenHands CLI | Detected from private env, version `OpenHands CLI 1.16.0`. | Preflight ok; write execution still blocked by policy. |
| Docker sandbox | Ready, Docker `29.4.1`, image `ghcr.io/openhands/openhands:latest`, network mode `none`. | Use as default execution boundary. |
| MiniMax | Env names present, live smoke HTTP 401. | Fix private key/base/model or report exact redacted blocker. |
| DeepSeek | Env names present, live smoke HTTP 401. | Fix private key/base/model or report exact redacted blocker. |
| Agent E2E readiness | Blocked only by provider auth lanes. | Do not claim E2E complete until auth smoke passes. |
| Source OS runners | Better classified now, but runner rows are downstream. | Pause unless needed for first agent PR. |
| PR stack | Most current PRs are clean; PR `#121` has a real failing UI-Final check. | Fix or isolate before merge. |

Important: do not echo values from `G:/private/.env`. It is acceptable to report env key names, source labels, status, base URL host labels, model names, HTTP status, and redacted blockers.

## Research Anchors

Use current sources only to remove blockers, not as an excuse to redesign the project.

- OpenHands Docker sandbox docs say Docker is the recommended local sandbox and that mounting a repo read-write allows the agent to modify it. Hermes3D must combine that with MCP locks before writes: `https://docs.openhands.dev/openhands/usage/sandboxes/docker`
- OpenHands agent platform research emphasizes sandboxed execution, multi-agent coordination, and evaluation benchmarks: `https://arxiv.org/abs/2407.16741`
- Nous Hermes Agent documents memory, skills, long-running operation, and self-improving workflows. Use these as runtime/skill patterns, not as proof that Hermes3D coding is complete: `https://github.com/NousResearch/hermes-agent`
- MiniMax's OpenAI-compatible chat endpoint is `https://api.minimax.io/v1/chat/completions` with `Authorization: Bearer <token>` and model names such as `MiniMax-M2.7`: `https://platform.minimax.io/docs/api-reference/text-chat`
- MiniMax-M2 docs also describe an OpenAI-compatible endpoint under `https://minimax-m2.com/api/v1/chat/completions`. If private env uses a different base URL, verify with a redacted smoke instead of guessing: `https://minimax-m2.com/docs/api/chat-completions`
- OpenCode is a CLI/TUI AI coding agent. Hermes3D may use it only through registered CLI runner contracts and sandbox policy, not as raw host shell access: `https://www.opencode.live/`

## Non-Negotiable Rules

- No broadening the product surface until the first Hermes Agent coding PR exists.
- No merge, rebase, retarget, or delete without user instruction or explicit contract permission.
- No edits without Hermes task claim and file locks.
- No host write access for OpenCode/OpenHands unless same-owner MCP file locks, snapshots, sandbox, output proof, review, and gates are already satisfied.
- No provider secret values in logs, markdown, screenshots, PR bodies, or command arguments.
- No claims of "working" unless route probe, evidence id, test/gate output, and UI/PR proof exist.
- No S1 write actions. S1 `192.168.0.12` stays read-only/camera-only/no test/no upload/no movement/no print.
- No fake green states. Use `PASS`, `BLOCKED`, `FAIL`, `PARTIAL`, or `NOT RUN`.
- No workaround that bypasses MiniMax builder and DeepSeek reviewer. Local fallback may help analysis, but it cannot satisfy the two-team acceptance proof unless clearly labeled fallback.
- No new app/runner work unless it is required for the first Hermes Agent coding PR.

## Required First Proof Task

Pick exactly one low-risk task that still proves the whole chain. Good candidates:

- a one-line docs or UI label correction in a non-sensitive file,
- a small test fixture update,
- a tiny no-fake wording fix.

Bad candidates:

- provider/auth rewrites,
- printer/network actions,
- multi-file UI refactors,
- source runner expansion,
- README/GitHub Pages polish,
- broad roadmap rewrites.

The task must produce:

- task id,
- locked file list,
- folder-index docs loaded,
- MiniMax builder artifact id,
- DeepSeek reviewer artifact id,
- pre-snapshot id,
- reviewed patch id,
- post-snapshot id,
- gates run and results,
- rollback/restore proof id,
- branch,
- commit,
- PR URL,
- evidence ids,
- released locks and task.

If any of those cannot happen, the agent must stop and write the blocked reason.

## 10-Agent Execution Plan

Run these agents in parallel only where their file scopes do not overlap. Every implementation agent must have one reviewer/auditor cross-check before PR.

| Agent | Role | Scope | Allowed edits | Required proof |
| --- | --- | --- | --- | --- |
| A1 | PR Stack Stabilizer | Audit open PRs, especially `#121` failing UI-Final. | Only tiny CI/test fix if directly needed. | Current PR matrix, failing check log, exact fix or blocked reason. |
| A2 | Provider Auth Specialist | MiniMax and DeepSeek smoke using `G:/private/.env` without exposing values. | Provider config parsing only if route is wrong. | Redacted request contract, HTTP status, evidence ids, no secret leakage. |
| A3 | MiniMax Builder Smoke | Run the smallest builder pass after A2 says MiniMax is live. | None unless paired with E2E task. | Builder artifact id and content hash. |
| A4 | DeepSeek Reviewer Smoke | Run review pass after A2 says DeepSeek is live. | None. | Reviewer artifact id and content hash. |
| A5 | E2E Loop Integrator | Drive first proof task from folder index through reviewed patch. | One or two low-risk files only. | Full closed-loop evidence bundle. |
| A6 | OpenCode Runner Auditor | Verify OpenCode runner contracts, preflight, sandbox boundary, output capture. | Only code-operator runner fixes if missing and scoped. | CLI path/version, sandbox status, blocked/write policy proof. |
| A7 | OpenHands Runner Auditor | Verify OpenHands runner contracts, Docker sandbox, denied paths, network policy. | Only code-operator runner fixes if missing and scoped. | CLI version, Docker image, mount policy, no secret mount proof. |
| A8 | MCP Evidence/Locks Auditor | Verify claim/lock/heartbeat/evidence/release chain. | No source edits unless lock bug found. | Ledger ids, stale-lock table, no orphan locks. |
| A9 | UI Workbench/Visual Tester | Verify Agents tab can run/inspect workbench state without fake UI. | UI-only fix if button/state is broken. | Playwright screenshot, route responses, no-fake scan. |
| A10 | Final Gate/Release Reviewer | Cross-check all artifacts and block false completion. | Markdown summary only. | Final PASS/BLOCKED verdict with every missing proof listed. |

Optional read-only agents:

- Linux/VPS Base Researcher: decide whether Linux/VPS should be a future worker target. It must not pivot the current task. Output is a decision matrix only.
- Performance Watcher: measure lag/polling only if it directly affects the Agents workbench.

## Linux/VPS Decision Boundary

Linux can help Hermes3D OS because most 3D, agent, Docker, and service stacks are smoother in Linux. But Linux does not replace the missing proof chain.

Current decision:

- Local Windows remains the user's primary GUI and printer-control workstation.
- Docker sandbox is the default local execution boundary.
- Linux VPS is allowed as an optional remote agent worker after the local closed loop passes.
- A Linux distro/base-image plan is allowed only after the first Hermes Agent coding PR exists.
- Do not migrate the project or make Linux the new blocker for this sprint.

Research output must answer only:

1. Which base is best for remote workers: Ubuntu LTS, Debian stable, or a custom container image?
2. Which dependencies belong in the Hermes3D agent image: Python, Node, Playwright, Rust, git, gh, OpenHands, OpenCode, slicer/modeling CLIs?
3. Which tasks are safe on VPS and which must stay local due to printers/cameras/GPU?
4. What proof confirms a VPS worker cannot access `G:/private`, printers, or local cameras unless explicitly bridged?

## Provider Auth Checklist

A2 must do this in order:

1. Confirm the backend reads `G:/private/.env` at runtime.
2. Confirm accepted key names only, not values:
   - `MINIMAX_API_KEY`
   - `MINIMAX_BASE_URL`
   - `MINIMAX_MODEL`
   - `DEEPSEEK_API_KEY`
   - `DEEPSEEK_BASE_URL`
   - `DEEPSEEK_MODEL`
   - optional `HERMES3D_*` aliases.
3. Confirm the configured MiniMax base URL and chat path are correct for the selected MiniMax model.
4. Confirm the configured DeepSeek base URL and chat path are correct for the selected DeepSeek model.
5. Run `/api/code-operator/providers/smoke` for each provider.
6. If HTTP 401 remains, report only:
   - provider id,
   - env key name,
   - base URL host label,
   - model name,
   - HTTP status,
   - evidence id,
   - recommended user action.
7. Do not attempt E2E patch execution while either provider is `auth_failed`.

## OpenCode/OpenHands Permission Model

OpenCode/OpenHands are allowed as CLI workers only through Hermes3D:

Allowed now:

- detect executable,
- detect version,
- verify source path,
- verify sandbox readiness,
- run read-only preflight,
- return blocked write policy.

Allowed only after provider smoke passes:

- read-only analysis inside sandbox,
- bounded patch proposal with no source mutation,
- output artifact capture with redaction.

Allowed only after reviewer approval:

- same-owner locked patch apply,
- gate runner,
- git branch/stage/commit/push/PR.

Never allowed:

- raw OpenCode/OpenHands shell command from chat,
- secrets in CLI args,
- writeable mount of `G:/private`,
- printer/network automation through coding agents,
- source mutation without MCP locks and snapshots.

## PR Stack Discipline

Before any merge recommendation, A1 must produce this table:

| PR | Base | State | Checks | Risk | Action |
| --- | --- | --- | --- | --- | --- |

Required current attention:

- PR `#121` is `UNSTABLE` because `Layer D2 - UI-Final (React @ 1920x1080)` failed. Fix or isolate this before claiming the stack is merge-ready.
- Clean PRs may still conflict after merge. Do not say "all done" until a merged-state verification branch or explicit merge-order proof exists.
- If a PR is based on the wrong branch, retarget/rebase only if it is in this contract's scope or the user explicitly approves.

## Required Commands

Run these or direct equivalents and paste summarized outputs into the final report:

```powershell
cd G:/Github/h3d-gui-wiring-codex
git status --short --branch
gh pr list --repo Ghenghis/Hermes3D --state open --limit 80 --json number,title,headRefName,baseRefName,mergeStateStatus,statusCheckRollup
gh pr checks 121 --repo Ghenghis/Hermes3D
Invoke-RestMethod http://127.0.0.1:8765/api/system/runtime-identity | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/e2e/readiness | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/providers/smoke -Method Post -Body '<provider payload>' -ContentType 'application/json'
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/cli-runners | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/sandbox/readiness | ConvertTo-Json -Depth 10
python 03_implementation/scripts/scan_active_ui_no_fake.py
```

If a command is unavailable, record the exact error. Do not substitute a green claim.

## Mandatory Gates For Any Code Change

Minimum:

- `git diff --check`
- targeted unit/compile test for changed backend files
- UI lint/typecheck for changed UI files
- `python 03_implementation/scripts/scan_active_ui_no_fake.py`
- focused Playwright proof for changed visible UI
- provider smoke if provider path changed
- CLI preflight if OpenCode/OpenHands path changed
- sandbox readiness if runner/sandbox changed
- MCP evidence append and release proof

High-risk additions:

- security/path/secret scan for auth, providers, env, shell/process, file system, MCP, git, and printer/network code.
- S1 policy test for printer-adjacent code.

## Final Output Required From Claude

Create or update one markdown report under:

`03_implementation/docs/handoffs/claude-24-agent-completion-2026-05-08/`

Recommended filename:

`HERMES_RUNTIME_FINISH_REPORT.md`

It must include:

- which agents ran,
- exact PR/check status,
- provider smoke result,
- CLI runner result,
- sandbox result,
- first proof task result,
- all evidence ids,
- all branches/commits/PRs created,
- all active locks after release,
- whether Hermes Agents are now `PASS`, `PARTIAL`, or `BLOCKED`,
- first three next actions for Codex.

## Stop Conditions

Stop immediately if:

- provider secrets would need to be printed,
- S1 write/printer action is requested,
- an agent tries to bypass MCP locks,
- a write-capable CLI run would mount denied paths,
- PR `#121` or any critical check is failing and no scoped fix is possible,
- MiniMax/DeepSeek auth remains 401 after redacted smoke.

In a stop case, write a blocked report with exact proof and do not continue widening.

Claude is done only when one of these is true:

1. `PASS`: a real Hermes Agent first proof task completed through PR with all evidence, or
2. `BLOCKED`: the exact remaining blocker is documented with proof, no locks are orphaned, and no fake completion is claimed.

There is no third state.
