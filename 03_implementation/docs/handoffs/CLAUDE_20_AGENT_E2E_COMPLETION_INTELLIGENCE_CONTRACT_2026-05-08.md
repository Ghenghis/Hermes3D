# Claude 20+ Agent E2E Completion Intelligence Contract

Updated: 2026-05-08  
Owner: codex-master  
Target repo: `G:/Github/h3d-gui-wiring-codex`  
Ecosystem root to audit: `G:/Github`  
Primary output directory: `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/`

## Purpose

Codex is continuing implementation. Claude should now spend its remaining value on a strict read-only intelligence sweep that tells Codex exactly what exists, what is stale, what is missing, what is duplicated, and what must be completed next for Hermes3D OS to become e2e working.

This is not a coding contract. Do not implement features. Do not edit source code outside the markdown outputs listed below. The goal is to create high-quality, actionable handoff documents that let Codex finish faster without guessing.

## Non-Negotiable Rules

- Read-only audit only. No feature coding, no source edits, no installer execution, no package upgrades, no printer actions.
- Do not touch `G:/private/.env` except to report env-key names required/missing; never read or echo secret values.
- S1 `192.168.0.12`: no movement, no upload, no print, no test.
- Use Hermes locks for the markdown files you write.
- Every claim must have evidence: path, command, file line, route, proof JSON, PR number, or exact blocked reason.
- No fake DONE states. Mark each item `DONE`, `PARTIAL`, `BLOCKED`, `STALE`, `DUPLICATE`, `UNKNOWN`, or `NEEDS-CODEX-FIX`.
- If a prior folder index is stale, say exactly which row is stale and what the current truth is.
- Do not merge PRs. Do not delete worktrees/folders. Do not release Codex-owned locks.
- Stop after creating the markdown bundle, opening one docs PR, and releasing Claude-owned locks.

## Required Context To Read First

Read these files before dispatching agents:

- `03_implementation/ROADMAP.md`
- `03_implementation/docs/handoffs/HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/00_INDEX.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/01_TAXONOMY.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/02_EXCLUSIONS.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/README.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/REGISTRY.md`
- `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/00_EXECUTIVE_TAKEOVER_SUMMARY.md` if present.

Also inspect current open PRs on `Ghenghis/Hermes3D`, but do not merge them.

## Required Commands

Run these or equivalent read-only commands and include key outputs in the bundle:

```powershell
cd G:/Github/h3d-gui-wiring-codex
git status --short --branch
git log --oneline --decorate -20
git worktree list
gh pr list --repo Ghenghis/Hermes3D --state open --limit 100 --json number,title,headRefName,baseRefName,isDraft,mergeStateStatus,statusCheckRollup
Get-ChildItem G:/Github -Directory | Select-Object Name,FullName,LastWriteTime
python 03_implementation/scripts/scan_active_ui_no_fake.py
Invoke-RestMethod http://127.0.0.1:8765/api/system/runtime-identity | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/e2e/readiness | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/cli-runners | ConvertTo-Json -Depth 10
Invoke-RestMethod http://127.0.0.1:8765/api/modules/runtime/runner-contracts | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8765/api/roadmap/tab-completion | ConvertTo-Json -Depth 8
```

If an API is offline, record that honestly and include the exact connection error.

## Required Output Files

Create this directory:

`03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/`

Write these files:

1. `00_EXECUTIVE_MAP.md`
   - One-page current truth.
   - What works now, what is blocked, what Codex should do next.
   - Include a hard answer to: "When will Hermes Agents work?"

2. `01_GITHUB_FOLDER_ECOSYSTEM_AUDIT.md`
   - Audit `G:/Github` folders related to Hermes3D, HermesProof, Hermes agents, source apps, worktrees, stale experiments, rescue folders, and generated indexes.
   - Compare the actual folders against the 2026-05-07 folder index.
   - Table columns: folder, category, current role, git repo/worktree/source-only, branch/HEAD when available, stale risk, keep/merge/archive recommendation, evidence.
   - Include the 60+ folders the user mentioned. Do not ignore old or duplicate folders.

3. `02_STALE_CODE_AND_BRANCH_MAP.md`
   - Find stale code surfaces: old worktrees, branches behind target, duplicated implementations, stale API/UI ports, stale generated proof, and docs that overclaim.
   - Include open PRs and branches by status.
   - Mark what Codex should rebase, merge, close, or ignore.

4. `03_HERMES_AGENT_RUNTIME_GAP_MAP.md`
   - Audit Hermes Agent, Nous Hermes Agent, Atomic Hermes, OpenCode, OpenHands, MiniMax, DeepSeek, sandbox, MCP locks, patch apply, gates, git PR, rollback, and evidence.
   - State what is DONE vs BLOCKED.
   - Required current truth to verify:
     - OpenCode should be detected as `1.4.3-hermes3d`.
     - OpenHands should be detected as `OpenHands CLI 1.16.0`.
     - Docker sandbox should inspect `ghcr.io/openhands/openhands:latest`.
     - MiniMax and DeepSeek smoke may be blocked with clean HTTP 401 auth blockers until private env is corrected.

5. `04_SOURCE_OS_60_APP_COMPLETION_MAP.md`
   - Audit all 60 Source OS rows.
   - For each: source path, launch kind, verifier family, runtime state, agent executable state, env keys, proof source, missing setup, next safe runner.
   - Highlight remaining runner gaps by family and exact next implementation order.

6. `05_TAB_BY_TAB_ACTIVE_UI_NO_FAKE_AUDIT.md`
   - Audit every visible tab against `ROADMAP.md` and `ACTIVE_UI_NO_FAKE_SWEEP.md` if present.
   - Table columns: tab, visible UI state, live API route(s), fake/mock risk, missing buttons/actions, responsiveness/density issues, required Playwright proof, verdict.
   - Include Simple GUI and Main GUI separately.

7. `06_ENV_KEYS_AND_RUNTIME_CONFIG_MAP.md`
   - List every required env key by subsystem: providers, voice, printers/cameras, source services, OpenHands/OpenCode, sandbox, update system, GitHub/PR tools.
   - Do not include values.
   - Mark key state as `present`, `missing`, `unknown`, or `not-readable-by-policy`.
   - Separate secret keys from non-secret URL/path keys.

8. `07_TEST_GATES_AND_PROOF_MATRIX.md`
   - Map all current gates/tests/proof commands.
   - Include what has recently passed, what times out, what is missing, and what should become mandatory before merge.
   - Include no-fake scan, pytest slices, TypeScript/lint, Playwright, provider smoke, CLI preflight, sandbox readiness, Source OS runner contracts, and printer safety.

9. `08_PR_AND_MERGE_QUEUE.md`
   - Current PR list with mergeability, branch, base, conflicts, CI, audit status, and action.
   - Include which PRs are Codex-owned and must not be overwritten.
   - Include recommended merge order if safe.

10. `09_CODEX_NEXT_50_TASKS.md`
    - A prioritized, concrete task queue for Codex.
    - Each row: priority, task, files/routes likely touched, prerequisite, acceptance proof, risk, can Hermes Agents help yet.
    - The first tasks must focus on unblocking Hermes Agents provider auth/smoke and safe CLI execution, then use agents to close Source OS runner gaps.

11. `10_DIAGRAMS.md`
    - Mermaid diagrams only.
    - Required diagrams:
      - GitHub folder/worktree topology.
      - Hermes Agent e2e coding loop.
      - Source OS 60-app runtime ladder.
      - UI no-fake verification flow.
      - Provider/sandbox/CLI trust boundary.
      - Codex takeover queue.

12. `11_FINAL_CLAUDE_NOTE.md`
    - A short message Claude can paste back to the user.
    - Must include: created docs, PR URL, remaining hard blockers, and "Codex can continue from this bundle."

## Optional 20+ Agent Fan-Out

If using subagents, split like this. All agents are read-only except the final aggregator writing markdown.

| Agent | Scope | Output file contribution |
| --- | --- | --- |
| 01 | `G:/Github` folder inventory | `01_GITHUB_FOLDER_ECOSYSTEM_AUDIT.md` |
| 02 | Worktrees and stale branches | `02_STALE_CODE_AND_BRANCH_MAP.md` |
| 03 | Open PRs and merge queue | `08_PR_AND_MERGE_QUEUE.md` |
| 04 | Hermes Agent runtime/backend routes | `03_HERMES_AGENT_RUNTIME_GAP_MAP.md` |
| 05 | Provider auth/smoke and private-env key names | `03`, `06` |
| 06 | OpenCode/OpenHands CLI and sandbox | `03`, `07` |
| 07 | MCP locks/evidence/rollback workflow | `03`, `07` |
| 08 | Source OS slicers/modelers | `04` |
| 09 | Source OS print farm/services | `04` |
| 10 | Source OS firmware/reference rows | `04` |
| 11 | Source OS agents/research/utilities | `04` |
| 12 | Dashboard/Simple UI | `05` |
| 13 | Agents/Voice/Learning UI | `05` |
| 14 | Source OS/Plugins/Settings UI | `05` |
| 15 | Printers/Observe/Jobs UI | `05` |
| 16 | Design/3D Generation/Artifacts/Approvals UI | `05` |
| 17 | Test gate inventory | `07` |
| 18 | Proof artifact inventory | `07` |
| 19 | Env-key and runtime config map | `06` |
| 20 | Diagrams | `10` |
| 21+ | Extra reviewer agents | Cross-check overclaims, stale index rows, missing acceptance proof |

Each agent must report:

- `PASS`, `PARTIAL`, `BLOCKED`, `STALE`, or `NEEDS-CODEX-FIX`.
- Evidence commands/paths used.
- Exact files it inspected.
- Exact Codex action if not PASS.

## Acceptance Checklist

Claude is done only when:

- All 12 markdown files exist under the output directory.
- Every output has evidence, not vibes.
- The actual `G:/Github` folder ecosystem is reconciled against the folder index.
- Hermes Agents blockers are stated cleanly and specifically.
- Source OS 60 rows have a current completion map.
- Open PRs/branches/worktrees have a current queue.
- All Claude-owned locks are released.
- A docs-only PR is opened.
- Claude stops without feature coding.

## Final Stop Message Template

Use this shape:

```text
Claude E2E intelligence bundle complete.

Docs: 03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/
PR: <url>
Hard blockers: <short list>
Codex next: <first 3 tasks>
Locks: <released or exact active list>

Codex can continue from this bundle.
```
