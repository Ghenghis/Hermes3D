# Claude 24-Agent Hermes3D OS Completion Handoff

Updated: 2026-05-08
Prepared by: Codex
Target repo: `G:/Github/h3d-gui-wiring-codex`
Base branch: `feat/hermes3d-7-complete-gui-repo-wiring`
Remote: `https://github.com/Ghenghis/Hermes3D`
Primary goal: finish Hermes3D OS to real daily-use readiness with truth/proof, no fake states, no stale code, no lag, and no skipped blockers.

## Copy/Paste Kickoff For Claude

Read this file fully first:

`G:\Github\h3d-gui-wiring-codex\03_implementation\docs\handoffs\CLAUDE_24_AGENT_COMPLETION_HANDOFF_2026-05-08.md`

Then execute it exactly.

Use `hermes3d-locks` MCP if attached. Claim task, lock files, heartbeat, append evidence, release files, release task. If child agents cannot call MCP tools directly, the Claude orchestrator must claim and lock files for each lane before dispatch, and must reject any child-agent output that edits files outside its locked lane.

Use 24 agents:

- 10 research/audit agents to produce blocker facts, current truth, stale-code findings, proof gaps, and perf/lag findings.
- 14 implementation agents to fix the highest-value lanes with strict file ownership.

Every agent must produce facts, command output, proof paths, evidence IDs, and pass/fail status. No "looks good", no "probably", no fake completion states. Fix until pass. If a blocker requires user-owned secrets or physical printer availability, prove that fact without exposing secrets and continue every non-blocked lane.

Do not touch `G:/private/.env` values except to read key names/presence through backend/private-env loaders. Never echo secrets.

S1 `192.168.0.12`: camera/read-only only. No movement, no upload, no print, no test, no bypass.

## Can Claude Agents Use Hermes MCP Locks?

Yes, if Claude has the `hermes3d-locks` MCP server attached. The required workflow is:

1. `hermes_claim_task`
2. `hermes_lock_files`
3. periodic `hermes_heartbeat`
4. run implementation and gates
5. `hermes_append_evidence`
6. `hermes_release_files`
7. `hermes_release_task`

If child agents do not have MCP tools, Claude must coordinate locks centrally:

- Orchestrator claims the lane task.
- Orchestrator locks the exact file set for the child.
- Child works only in those files.
- Orchestrator verifies `git diff --name-only` matches the lock set.
- Orchestrator appends evidence and releases locks.
- Any diff outside the lock set is rejected and reverted only for that child-owned change.

## Current Baseline Truth

- Latest merged work includes PR `#107`, commit `684a284d534e`.
- Current base branch must be proven clean and fresh with `git status --short --branch` after `git pull --ff-only origin feat/hermes3d-7-complete-gui-repo-wiring`.
- Open PR count was `0` after PR `#107` merge.
- Runtime identity proof after PR `#107` showed:
  - branch `feat/hermes3d-7-complete-gui-repo-wiring`
  - commit `684a284d534e`
  - dirty `false`
  - fresh `true`
  - missing Agent Workbench routes `[]`
- Provider env aliases are now wired:
  - `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`, `MINIMAX_MODEL`
  - `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`
  - OpenCode/OpenHands bin paths
- Provider chat smokes still fail closed:
  - MiniMax evidence `ev_588b6031300f6071`: redacted HTTP 401 at chat completions
  - DeepSeek evidence `ev_44db7d3149d9e415`: redacted HTTP 401 at chat completions
- Provider/env diagnostic evidence:
  - `ev_96fea4b2a1e2aab8`
  - PR merge evidence `ev_dce271817e845367`

## Folder Index And `G:\Github` Location Truth

The folder index has already been created by Claude agents. Do not redo that work blindly.

- Folder index PR: `#86` - <https://github.com/Ghenghis/Hermes3D/pull/86>
- Branch: `claude/folder-index-2026-05-07`
- Base: `feat/hermes3d-7-complete-gui-repo-wiring`
- Merge commit: `99a0882d498dca469f8a9a6379b68295941eb83d`
- Merged: `2026-05-08T17:26:36Z`
- Hermes task: `a2a_1778147261453_661b606f`
- Authorship: 13 parallel Claude sub-agents under `claude-orchestrator`
- Claimed PR bundle stats: 86 markdown files, about 7,024 lines, 12 categories.
- `00_INDEX.md` stats: 71 folders indexed as 60 included + 11 excluded, 83 markdown files.
- `02_EXCLUSIONS.md` stats: 7 excluded top-level folders.

Important: the PR body and index docs have a totals mismatch (`7 excluded` vs `11 excluded`, `86 markdowns` vs `83 markdowns`). Claude must not treat either number as gospel until it re-reads `00_INDEX.md`, `02_EXCLUSIONS.md`, and the directory tree. Record the refreshed count in the final report.

The 60+ folders under `G:\Github` are not all newly created by Claude or Codex. They are a mix of:

- existing source repos,
- linked git worktrees,
- vendored upstream snapshots,
- dedicated integration worktrees,
- prior audit/sandbox folders,
- and generic Source OS source checkouts.

PR `#86` indexed and documented them. It did not prove that every folder is runtime-ready, installed, configured, or usable by Hermes Agents. Refresh each row through the live backend/verifier before marking it ready.

### Source OS Registry Truth

The Source OS registry count is exactly 60 module rows across 11 sections:

- modelers: 13
- slicers: 11
- print_farm: 10
- agents: 7
- firmware: 6
- three_d_generation: 6
- hardware: 3
- library: 1
- materials: 1
- research: 1
- utilities: 1

Canonical sources:

1. `G:\Github\Hermes3D\Hermes3D-GUI-Wiring-Contract-Kit\03_REPO_REGISTRY\external_repos_registry.yaml`
2. `G:\Github\h3d-gui-wiring-codex\03_implementation\proof\SOURCE_REGISTRY_TRUTH_AUDIT.json`
3. `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\db\load_modules.py`
4. `G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\api\routes\modules.py`

Only 5 of 60 Source OS rows have dedicated `h3dos-codex-*` integration folders:

| Folder | Module |
| --- | --- |
| `G:\Github\h3dos-codex-blender-cli` | Blender |
| `G:\Github\h3dos-codex-fluidd` | Fluidd |
| `G:\Github\h3dos-codex-octoprint` | OctoPrint |
| `G:\Github\h3dos-codex-prusaslicer` | PrusaSlicer |
| `G:\Github\h3dos-codex-triposr` | TripoSR |

The other 55 rows rely on the generic loader path and runtime verifier state. Do not create 55 new folders unless a specific row actually needs a dedicated integration lane. The next work is usually refresh, verify, configure, or add a safe runner, not recreate folders.

### Worktree And Vendored Snapshot Truth

- Worktree umbrellas: `_claude_worktrees`, `_codex_worktrees`, `_codex_audit_worktrees`; index reported 49 linked worktrees.
- Vendored snapshots live under `G:\Github\apps\`, about 1.08 GB total. These are extracted/downloaded snapshots, not git repos.
- Notable vendored snapshots: Blender, OrcaSlicer, PrusaSlicer, Printrun, Hermes Desktop, locale overlay.
- Agent infrastructure includes:
  - `G:\Github\hermes3d-mcp-lock-orchestrator` - active HermesProof/Hermes locks orchestrator.
  - `G:\Github\hermes-agent-fresh` - NousResearch Hermes Agent reference.
  - `G:\Github\atomic-hermes` - Atomic Hermes reference.

Do not treat a vendored snapshot as installed or runnable until a non-mutating proof exists: executable path, import proof, version probe, service health probe, or explicit blocked reason.

### Required Location Refresh Before Dispatch

Before any Claude implementation agent edits code, the orchestrator must refresh location truth:

```powershell
cd G:\Github\h3d-gui-wiring-codex
git fetch origin
git status --short --branch
git pull --ff-only origin feat/hermes3d-7-complete-gui-repo-wiring
gh pr list --repo Ghenghis/Hermes3D --state open --limit 80
Get-Content 03_implementation\docs\handoffs\hermes3d-os-folder-index-2026-05-07\00_INDEX.md -Raw
Get-Content 03_implementation\docs\handoffs\hermes3d-os-folder-index-2026-05-07\02_EXCLUSIONS.md -Raw
Get-Content 03_implementation\docs\handoffs\hermes3d-os-folder-index-2026-05-07\source-os-60-apps\REGISTRY.md -Raw
```

Then, with the local backend running, probe live truth:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/system/runtime-identity
Invoke-RestMethod http://127.0.0.1:8765/api/modules/runtime/runner-contracts
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/e2e/readiness
```

If the backend is not on `8765`, locate the current port from the running dev stack and record it. Do not assume stale browser ports.

If any command above fails, do not continue into implementation. Record the exact failing command, exit code, and owner. Fix the environment first unless the failure is a proven external provider/secret blocker.

### Location Ownership Map

Use these locations exactly:

| Purpose | Location | Rule |
| --- | --- | --- |
| Target implementation repo | `G:\Github\h3d-gui-wiring-codex` | Main code edits and PR branches for this completion pass. |
| Canonical GitHub repo | `https://github.com/Ghenghis/Hermes3D` | Open PRs here. |
| Main sibling worktree/repo | `G:\Github\Hermes3D` | Do not edit unless explicitly assigned; use as registry/reference only. |
| Private secrets | `G:\private\.env` | Read through backend/private env loaders only; never echo values. |
| MCP lock orchestrator | `G:\Github\hermes3d-mcp-lock-orchestrator` | Use `hermes3d-locks` MCP, not ad hoc lock files. |
| Source OS generic checkouts | `G:\Github\h3d-gui-wiring-codex\source-lab\sources\...` or backend-resolved `local_path` | Verify from API/loader before using. |
| Dedicated app lanes | `G:\Github\h3dos-codex-*` | Only 5 known dedicated integration folders. |
| Vendored app snapshots | `G:\Github\apps\*` | Source/reference/runtime candidate only after proof. |
| Folder index docs | `G:\Github\h3d-gui-wiring-codex\03_implementation\docs\handoffs\hermes3d-os-folder-index-2026-05-07\` | Read first; refresh counts if inconsistent. |

Claude agents should refresh, verify, and wire what exists. They should not inflate readiness or generate duplicate folders because a row has a name.

## Mandatory Read-First Docs

Claude and every relevant subagent must use these as source-of-truth context:

- `03_implementation/ROADMAP.md`
- `03_implementation/proof/ACTIVE_UI_NO_FAKE_SWEEP.md`
- `03_implementation/docs/handoffs/HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md`
- `03_implementation/docs/handoffs/CLAUDE_20_AGENT_E2E_COMPLETION_INTELLIGENCE_CONTRACT_2026-05-08.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/00_EXECUTIVE_MAP.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/03_HERMES_AGENT_RUNTIME_GAP_MAP.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/04_SOURCE_OS_60_APP_COMPLETION_MAP.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/05_TAB_BY_TAB_ACTIVE_UI_NO_FAKE_AUDIT.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/07_TEST_GATES_AND_PROOF_MATRIX.md`
- `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/09_CODEX_NEXT_50_TASKS.md`
- `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/00_EXECUTIVE_TAKEOVER_SUMMARY.md`
- `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/04_RUNTIME_TRUTH_AND_NO_FAKE_AUDIT.md`
- `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/05_PRINTER_SAFETY_AND_PHYSICAL_IO_AUDIT.md`
- `03_implementation/docs/handoffs/claude-final-audit-2026-05-06/06_SECURITY_MCP_AND_AGENT_ACCESS_AUDIT.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/00_INDEX.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/01_TAXONOMY.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/02_EXCLUSIONS.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/README.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/REGISTRY.md`
- `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/agent-infra/README.md`

## Definition Of "Hermes Agents Work"

Hermes Agents are not considered working just because chat, UI, keys, or CLI detection exist. They are working only when this full chain passes with proof:

1. User or operator submits a real low-risk Hermes3D task.
2. Agent task loads the folder-index context and records which files/docs were used.
3. Task claims MCP task and locks files.
4. Pre-change snapshots are captured.
5. MiniMax builder produces a bounded coding plan or patch artifact.
6. DeepSeek reviewer reviews the same task/proofs.
7. Reviewed patch is applied only under same-owner file locks.
8. Post-change snapshot and diff proof are captured.
9. Required gates pass.
10. Branch is created with allowed prefix.
11. Files are staged only if they have snapshots and active locks.
12. Commit is created with proof IDs.
13. Branch is pushed.
14. PR is opened.
15. Rollback/restore path is proven.
16. Evidence is appended.
17. Locks and task are released.

The first accepted smoke task should be tiny: one docs line, one non-runtime UI label, or a test fixture. Do not start with Source OS broad work.

## Known Blockers That Must Not Be Skipped

| Blocker | Current proof | Required action | Done condition |
| --- | --- | --- | --- |
| MiniMax provider chat auth fails | `ev_588b6031300f6071`, redacted HTTP 401 | Audit endpoint/model/auth headers using current docs, verify `G:/private/.env` key names only, fix code/config if stale; if key itself is invalid, write exact user-action blocker without leaking value. | `/api/code-operator/providers/smoke` for MiniMax returns accepted with MCP evidence. |
| DeepSeek provider chat auth fails | `ev_44db7d3149d9e415`, redacted HTTP 401 | Audit endpoint/model/auth headers using current docs, verify key names only, fix code/config if stale; if key itself is invalid, write exact user-action blocker. | `/api/code-operator/providers/smoke` for DeepSeek returns accepted with MCP evidence. |
| Provider artifacts not fully chained to patch apply | `HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md` | Implement or verify reviewed patch extraction -> same-owner lock validation -> apply -> post snapshot -> gates -> PR. | First Hermes Agent PR smoke completes. |
| OpenCode/OpenHands write execution blocked | `ROADMAP.md` Agents row | Keep detection/preflight; add only sandboxed task-scoped runs with captured output, no raw arbitrary command strings. | One read-only sandbox run proof, then one reviewed patch run proof. |
| Source OS 24 runner gaps remain | `ROADMAP.md` Source OS row | Use Hermes Agents after first co-dev smoke; do not manually close rows with fake runnable states. | Every row has runtime-ready proof or exact blocked reason. |
| UI lag/performance risk | User reports lag/oversized/stale UI historically | Audit polling, large renders, layout overflow, resize behavior, camera reconnect, Source OS list rendering. | Measured/visual proof: no long blocking render, no unreadable side panels, no stale API process confusion. |
| Active UI no-fake must stay clean | latest scan passed 81 files | Run no-fake scan after every UI change. | `scan_active_ui_no_fake.py` passes. |
| S1 safety must stay locked | prior safety audit zero violations | No movement/upload/test/print for S1. Camera/read-only allowed. | Printer safety tests and route grep prove no bypass. |
| Stale code/process confusion | User reports stale code and app restarts | Runtime identity guard must be checked after backend restart. | `/api/system/runtime-identity` fresh, dirty false, missing routes empty. |

## Global Rules For All Agents

- No fake/mock/simulated/demo UX.
- No visible success unless a real backend/local/API action completed.
- Every disabled control must show an exact blocked reason.
- Never edit `G:/private/.env` values or echo secrets.
- Read key names/presence only through backend/private env helpers.
- No Azure infrastructure beyond Azure Speech already used; do not introduce Azure hosting.
- Free/open-source/local-first tools only unless the user explicitly configured provider API keys.
- No printer physical actions unless route policy and user approval allow it.
- S1 is camera/read-only.
- No hidden broad refactors.
- No generated proof claiming a pass unless command actually passed.
- No skipping timed-out tests. Record timeout and fix or mark blocker.
- Use branches and PRs; do not leave multi-day unpushed work.
- Merge green PRs only under standing authorization and only after required proof gates pass.
- If `git status --short` is dirty before a lane starts, stop and classify the changes by owner. Do not build on stale or unowned local edits.
- Any agent report that lacks exact commands, exit status, changed files, and proof artifact paths is incomplete and must be rejected by the orchestrator.

## Required Gates Before Any Implementation PR

At minimum, each PR must record:

```powershell
git diff --check
python -m py_compile <changed-python-files>
pytest -q <targeted-tests>
npm run lint              # for UI/type changes
python 03_implementation/scripts/scan_active_ui_no_fake.py
```

Add these when relevant:

- Playwright/browser proof for UI route changes.
- Route smoke for backend API changes.
- Provider smoke for agent runtime changes.
- Sandbox readiness/preflight for OpenCode/OpenHands changes.
- Secret/path traversal/shell execution scan for route, command, provider, or filesystem changes.
- Printer policy tests for printers/jobs/observe/safety changes.
- Source OS verifier/runner contract proof for Source OS rows.
- Evidence chain append with proof IDs.

## 10 Research / Audit Agents

Each audit agent is read-only unless explicitly assigned a tiny doc correction by the orchestrator. Each must produce markdown findings under:

`03_implementation/docs/handoffs/claude-24-agent-completion-2026-05-08/audits/`

| Agent | Task ID | Scope | Required output |
| --- | --- | --- | --- |
| A1 | `H3D-CLAUDE24-A1-TRUTH` | Current truth + roadmap | DONE/PARTIAL/BLOCKED matrix for every primary tab, Hermes Agent runtime, Source OS, proof gates. |
| A2 | `H3D-CLAUDE24-A2-PROVIDERS` | MiniMax/DeepSeek provider loop | Exact endpoint/model/auth findings from current code and current official docs; no secret values. |
| A3 | `H3D-CLAUDE24-A3-CLI-SANDBOX` | OpenCode/OpenHands/sandbox | Runner detection, sandbox policy, missing write-execution proof, task-scoped restrictions. |
| A4 | `H3D-CLAUDE24-A4-SOURCEOS` | Source OS 60 apps | Per-family gap matrix, runner-ready vs source-ready vs blocked, no fake runnable rows. |
| A5 | `H3D-CLAUDE24-A5-PRINTERS` | Printers/cameras/safety | S1 lock proof, T1/V400 policy, camera read-only proof, build-plate gate proof. |
| A6 | `H3D-CLAUDE24-A6-TABS` | UI tab coverage | 16/18 tab readiness, missing routes/actions, blocked controls, proof evidence. |
| A7 | `H3D-CLAUDE24-A7-PERF` | Lag/performance/layout | Polling, large lists, camera rendering, resize/overflow, stale server confusion. |
| A8 | `H3D-CLAUDE24-A8-GATES` | Tests/proof gates | Required gate matrix and missing merge-blocking gates. |
| A9 | `H3D-CLAUDE24-A9-ENV` | Env/runtime config | Key names only, alias compatibility, runtime identity, restart behavior. |
| A10 | `H3D-CLAUDE24-A10-GIT` | Git/worktrees/PRs/stale docs | Branch/PR/worktree truth, stale local work, unpushed branches, merge queue. |

## 14 Implementation Agents

Each implementation agent must use a separate branch and strict file ownership. If the agent cannot acquire locks, it must stop and report.

Suggested branch pattern: `claude24/<lane-name>`.

| Agent | Task ID | Lane | File ownership | Acceptance |
| --- | --- | --- | --- | --- |
| I1 | `H3D-CLAUDE24-I1-PROVIDER-SMOKE` | Provider auth/smoke | `03_implementation/src/hermes3d/services/agent_runtime.py`, `03_implementation/src/hermes3d/services/code_history.py`, `03_implementation/src/hermes3d/api/routes/code_operator.py`, provider section of `03_implementation/ui/src/tabs/Agents.tsx` | MiniMax and DeepSeek smokes either pass, or one precise human-secret-required blocker remains with all code/config causes eliminated. |
| I2 | `H3D-CLAUDE24-I2-E2E-CODE-LOOP` | Agent E2E code loop | `03_implementation/src/hermes3d/services/code_history.py`, `03_implementation/src/hermes3d/api/routes/code_operator.py`, Agent Code Workbench portions of `03_implementation/ui/src/tabs/Agents.tsx`, and needed adapter methods in `03_implementation/ui/src/api/adapters.live.ts` / `03_implementation/ui/src/api/adapters.ts` | First low-risk Hermes Agent task completes lock -> snapshot -> provider -> review -> patch -> gates -> PR -> rollback proof. |
| I3 | `H3D-CLAUDE24-I3-OPENCODE-OPENHANDS` | OpenCode/OpenHands runner | CLI runner portions of `03_implementation/src/hermes3d/services/code_history.py`, sandbox route/types in `03_implementation/src/hermes3d/api/routes/code_operator.py`, and matching UI rows in `03_implementation/ui/src/tabs/Agents.tsx` | One read-only sandbox run proof; no write run until review/gate/rollback path exists. |
| I4 | `H3D-CLAUDE24-I4-SOURCEOS-CORE` | Source OS runner contracts core | `03_implementation/src/hermes3d/services/module_runtime.py`, `03_implementation/src/hermes3d/api/routes/modules.py` | 60-row matrix has no unknown bucket and exact runner/blocker state. |
| I5 | `H3D-CLAUDE24-I5-SLICERS-MODELERS` | Slicer/modeler CLI/package rows | slicer/modeler adapters, schemas, runner rows only | Prusa/Orca/FLSUN/Slic3r/SuperSlicer/modeler rows show real CLI/package proof or exact blocked reason. |
| I6 | `H3D-CLAUDE24-I6-SERVICES` | Service/web app runners | source service supervisor, service rows for Fluidd/Mainsail/OctoPrint/FDM Monster/OctoFarm/Manyfold/ComfyUI | Safe setup/start runner exists only behind sandbox/process supervisor and post-start health proof. |
| I7 | `H3D-CLAUDE24-I7-FIRMWARE-FARM` | Firmware/farm read-only runners | firmware/farm verifier rows | Source inventory/read-only health proof only; no flash/upload/move. |
| I8 | `H3D-CLAUDE24-I8-PRINTER-SAFETY` | Printer safety actions | `03_implementation/src/hermes3d/api/routes/printers.py`, `03_implementation/src/hermes3d/api/safety.py`, `03_implementation/src/hermes3d/core/safety/*`, `04_testing/pytest/unit/test_printer_policy.py`, `04_testing/pytest/unit/test_jobs_policy.py`, and relevant `04_testing/pytest/test_safety_*.py` files | S1 stays hard locked; T1/V400 actions policy-gated and proof-recorded. |
| I9 | `H3D-CLAUDE24-I9-OBSERVE-CAMERA` | Observe/camera | `03_implementation/src/hermes3d/api/routes/observe.py`, `03_implementation/ui/src/tabs/Observe.tsx`, `03_implementation/ui/src/components/observe/ObserveConsole.tsx`, and observe adapter methods | Cameras refresh, reconnect, rotate/zoom controls work visually without physical movement. |
| I10 | `H3D-CLAUDE24-I10-PERF-SHELL` | UI performance/app shell | `03_implementation/ui/src/app/AppShell.tsx`, `03_implementation/ui/src/components/layout/Sidebar.tsx`, `03_implementation/ui/src/components/layout/TopBar.tsx`, `03_implementation/ui/src/components/layout/ResizablePane.tsx`, `03_implementation/ui/src/styles/globals.css`, shared polling hooks/adapters | Main UI is responsive, resizable, no cutoff side panels, no excessive font sizing, no stale API lag. |
| I11 | `H3D-CLAUDE24-I11-SOURCEOS-UI` | Source OS UI | `03_implementation/ui/src/tabs/SourceOS.tsx`, `03_implementation/ui/src/components/source-os/*`, Source OS types/adapters | 60 rows readable, resizable panels, correct badges, verify/setup controls wired. |
| I12 | `H3D-CLAUDE24-I12-AGENTS-VOICE-LEARNING` | Agents/Voice/Learning UI | chat/voice/learning portions of `03_implementation/ui/src/tabs/Agents.tsx`, `03_implementation/ui/src/tabs/Voice.tsx`, `03_implementation/ui/src/tabs/Learning.tsx`, and matching backend/adapter methods | Hermes Agent chat supports mic/files/context; voice uses Azure through backend only; learning jobs prove real blocked/runnable state. |
| I13 | `H3D-CLAUDE24-I13-PRINT-WORKFLOW` | Dashboard/jobs/printers/autopilot workflow | `03_implementation/ui/src/tabs/Dashboard.tsx`, `03_implementation/ui/src/tabs/Jobs.tsx`, `03_implementation/ui/src/tabs/Printers.tsx`, `03_implementation/ui/src/tabs/Autopilot.tsx`; coordinate with I8/I9 | Print workflow actions are proof-backed, no S1 bypass, no fake job states. |
| I14 | `H3D-CLAUDE24-I14-PROOF-GATES` | Proof/test enforcement | `04_testing/pytest/*`, `03_implementation/ui/tests/*`, `03_implementation/scripts/scan_active_ui_no_fake.py`, proof bundle scripts/artifacts | Required gates are runnable, documented, and fail closed in CI/local proof. |

## Conflict Boundaries

- `03_implementation/src/hermes3d/services/code_history.py`: I1 owns provider status/smoke, I2 owns patch/git/MCP flow, I3 owns OpenCode/OpenHands. Do not overlap without explicit lock transfer.
- `03_implementation/ui/src/tabs/Agents.tsx`: split by panel. I1 provider smoke, I2 code workbench, I12 chat/voice.
- `03_implementation/src/hermes3d/api/routes/modules.py` and `03_implementation/src/hermes3d/services/module_runtime.py`: I4 owns structural contract; I5/I6/I7 submit narrow row-family patches.
- `03_implementation/src/hermes3d/api/routes/printers.py`, `03_implementation/src/hermes3d/api/routes/observe.py`, `03_implementation/src/hermes3d/api/safety.py`, and `03_implementation/src/hermes3d/core/safety/*`: I8/I9 coordinate. No one else changes physical safety.
- `03_implementation/ui/src/api/adapters.live.ts`: shared integration file. Reserve final integration edits for orchestrator or one appointed integrator.
- `03_implementation/ui/src/app/AppShell.tsx`, `03_implementation/ui/src/components/layout/Sidebar.tsx`, `03_implementation/ui/src/styles/globals.css`: I10 only.
- `03_implementation/proof/*`: I14 or final integrator only, except route-generated proof artifacts.
- Source-lab/vendor checkouts: do not edit from this completion pass unless a lane explicitly owns that external source.

## Required Final Integrator

After agent PRs are open, Claude must run a final integrator pass:

1. Pull base branch.
2. List open PRs.
3. Confirm every PR has proof IDs and passes checks.
4. Detect conflicts.
5. Merge in safe order only if green and authorized.
6. Rerun global gates.
7. Run browser/Playwright visual proof for:
   - Dashboard
   - Agents
   - Source OS
   - Observe
   - Settings
   - Roadmap
8. Update:
   - `03_implementation/ROADMAP.md`
   - `03_implementation/proof/ACTIVE_UI_NO_FAKE_SWEEP.md`
   - a final completion report under `03_implementation/docs/handoffs/claude-24-agent-completion-2026-05-08/`
9. Release all locks/tasks.

## Final Report Files Claude Must Create

Create these markdown files:

`03_implementation/docs/handoffs/claude-24-agent-completion-2026-05-08/`

- `00_EXECUTIVE_STATUS.md`
- `01_BLOCKER_MATRIX.md`
- `02_AGENT_RUNTIME_COMPLETION.md`
- `03_SOURCE_OS_60_APP_STATUS.md`
- `04_UI_TAB_AND_PERFORMANCE_STATUS.md`
- `05_PRINTER_CAMERA_SAFETY_STATUS.md`
- `06_PROOF_GATES_AND_TEST_RESULTS.md`
- `07_PR_BRANCH_LOCK_MATRIX.md`
- `08_USER_NEXT_ACTIONS_IF_ANY.md`

Each file must include:

- PASS/BLOCKED/PARTIAL
- proof commands
- evidence IDs
- PR links
- exact files changed
- exact remaining blocker, if any

## Stop Condition

Claude is done only when:

- All 24 agents reported.
- Every implementation lane either merged green or has a proof-backed blocker.
- Hermes locks are released or explicitly listed with reason.
- Open PR/branch matrix is written.
- Runtime identity is fresh and non-stale.
- No fake UI scan passes.
- Printer safety passes.
- The first Hermes Agent E2E smoke task is attempted and either passes or is blocked only by proven provider-secret rejection.

If provider secrets remain rejected, do not pretend daily-autonomous readiness. State: "Hermes Agent runtime is wired and proof-gated; provider-backed execution is blocked by rejected private provider values." Then continue all non-provider-dependent fixes.
