# Claude 6-Agent Polish, Correctness, and Completion Audit

Updated: 2026-05-06
Owner: codex-master
Target repo: `G:/Github/h3d-gui-wiring-codex`
Target remote: `https://github.com/Ghenghis/Hermes3D`

## Purpose

Claude's 20-agent implementation wave produced a large set of green lane PRs. Before merge, run a strict six-agent second pass that treats green CI as necessary but not sufficient. The goal is production-quality Hermes3D OS: live-backed UI, real runtimes, truthful blocked states, no fake data, no silent safety bypasses, complete proof, and clean GitHub organization.

Do not use this pass to add speculative features. Use it to prove, polish, and correct what exists.

## Current PR Landscape From Claude Wave

Lanes completed with PRs:

- PRs `#53` through `#72` were reported as open and CI passing.
- Reported conflict clusters:
  - `03_implementation/src/hermes3d/api/app.py`: PR `#66` Source OS router plus PR `#69` update center router. Merge `#66` first, then resolve `#69` keeping both routers.
  - `03_implementation/ui/src/api/adapters.ts` and `03_implementation/ui/src/api/adapters.live.ts`: PR `#64` voice methods plus PR `#71` printer methods. Merge `#64` first, then resolve `#71` keeping every voice and printer method.
- Reported high blocker:
  - Pre-existing TypeScript JSX/type regression in many `03_implementation/ui/src/*.tsx` files. Create a dedicated fix PR if this still reproduces. Do not hide it under an unrelated lane.

Recommended merge order after this audit:

1. Tier 1 no-conflict PRs: `#53`, `#54`, `#55`, `#56`, `#57`, `#58`, `#59`, `#60`, `#61`, `#62`, `#63`, `#65`, `#67`, `#68`, `#70`.
2. Tier 2 app router sequence: `#66`, then `#69`, preserving both routers.
3. Tier 3 adapter sequence: `#64`, then `#71`, preserving all voice and printer adapter methods.
4. Final integration report: `#72`.

If current GitHub state differs, use current GitHub truth and update this document or the integration report before merging.

## Non-Negotiable Rules

- Use Hermes locks for every lane: claim task, lock files, heartbeat, append evidence, release files, release task.
- Every failure must be fixed to pass state before a lane is called done.
- No fake, mocked, simulated, placeholder, demo-only, or "looks wired" behavior in visible UI or backend routes.
- A visible button must either perform a real action through a live backend route, be disabled with an honest reason, or be removed.
- Secrets come from `G:/private/.env` at runtime only. Never echo, screenshot, commit, or bundle secrets.
- S1 `192.168.0.12` remains read/camera-only. No movement, no upload, no print, no test.
- T1 #1 `192.168.0.10`, T1 #2 `192.168.0.11`, and V400 `192.168.0.34` may be tested only through backend safety gates.
- Do not edit Codex-owned Hermes Agent code-operator files unless Codex releases them:
  - `03_implementation/src/hermes3d/services/code_history.py`
  - `03_implementation/src/hermes3d/api/routes/code_operator.py`
  - code-operator sections in `03_implementation/src/hermes3d/api/routes/agents.py`
  - code-history schema rows in `03_implementation/src/hermes3d/db/schema.sql`

## Six Audit Agents

### Agent 1: Merge and Conflict Integrity

Task ID: `H3D-CLAUDE-POLISH-MERGE-2026-05-06`

Scope:

- Verify every PR branch is based on the intended project baseline.
- Confirm conflict files and merge order.
- For each conflict resolution, prove both sides survived with targeted grep/tests.
- Confirm no PR drops previously merged routers, adapter methods, tab routes, schema rows, printer safety checks, or source runtime data.

Acceptance:

- Current PR list recorded with status and base/head.
- Conflict resolution notes include exact files, exact kept symbols, and proof commands.
- `git diff --check` passes after each resolution.
- Any unexpected conflict stops the lane and is reported with owner and file path.

### Agent 2: Active UI No-Fake and Button Wiring

Task ID: `H3D-CLAUDE-POLISH-NOFAKE-UI-2026-05-06`

Scope:

- Audit all primary tabs: Source OS, Dashboard, Autopilot, Design, 3D Generation, Jobs, Printers, Observe, Voice, Agents, Learning, Artifacts, Approvals, Plugins, Settings, Roadmap.
- For every visible button/menu/toggle, verify one of:
  - live backend route is called and returns real data,
  - action is policy-blocked with an honest reason,
  - feature is intentionally read-only and labeled as such.
- Check Simple and Main mode parity. Simple mode must not switch back to Main unexpectedly and must not present stale mock state.

Required commands:

```powershell
python 03_implementation/scripts/scan_active_ui_no_fake.py
cd 03_implementation/ui
npm run lint
npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Dashboard|Source OS|Agents|Observe|Settings|Roadmap|Voice|Learning"
```

Acceptance:

- No production mock/fake/simulated UX markers.
- Playwright screenshots or traces exist for each audited tab.
- Every broken button becomes fixed, disabled with proof, or assigned to a blocking issue with owner.

### Agent 3: Runtime Truth and Source OS Completeness

Task ID: `H3D-CLAUDE-POLISH-SOURCE-RUNTIME-2026-05-06`

Scope:

- Verify the Source OS registry count and all 60 app rows.
- Confirm runtime statuses are not invented: installed/source/ready/unknown/blocked must come from proof or real local probes.
- Verify CLI surfacing for apps that expose CLI/service access, especially slicers, modelers, print farm, firmware, 3D generation, and agents.
- Confirm update/backup/rollback readiness is truthful and cannot run destructive actions without approval and proof.

Required probes:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/modules | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8765/api/modules/runtime/agent-cli-readiness | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8765/api/modules/runtime/gaps | ConvertTo-Json -Depth 8
Invoke-RestMethod http://127.0.0.1:8765/api/modules/update/readiness | ConvertTo-Json -Depth 8
```

Acceptance:

- Every `UNKNOWN` badge is justified by missing runtime/proof, not missing implementation.
- Every app with safe CLI/service verifier has a visible CLI/readiness signal.
- Every runner gap is listed in Roadmap or proof with a concrete next action.

### Agent 4: Printer, Camera, and Physical Safety

Task ID: `H3D-CLAUDE-POLISH-PRINTER-SAFETY-2026-05-06`

Scope:

- Verify printers:
  - T1 #1: `192.168.0.10`
  - T1 #2: `192.168.0.11`
  - S1: `192.168.0.12`
  - V400: `192.168.0.34`
- Verify S1 is camera/status only.
- Verify Observe refresh/reconnect works and camera controls do not fake state.
- Verify build-plate clear/occupied state is represented as real evidence or honest unknown.
- Verify upload/start actions require policy, proof, idle target, non-S1 target, and explicit job context.

Required commands:

```powershell
python -m py_compile 03_implementation/src/hermes3d/api/routes/printers.py 03_implementation/src/hermes3d/api/routes/observe.py
cd 03_implementation/ui
npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Observe|Printers"
```

Acceptance:

- S1 physical action attempts return policy block before any network side effect.
- Camera refresh and view settings are real-backed or honestly blocked.
- T1/V400 probes never imply successful movement/print unless backend proof exists.

### Agent 5: Hermes Agents, MCP, Proof, and Security

Task ID: `H3D-CLAUDE-POLISH-AGENT-MCP-PROOF-2026-05-06`

Scope:

- Verify Hermes Agents can see action contracts for all tabs.
- Verify agent-callable actions are proof-required and risk-scoped.
- Verify MCP lock workflow is followed for coding work:
  - intent
  - claim task
  - lock files
  - heartbeat
  - snapshot
  - patch/proof
  - gate
  - evidence
  - release
- Verify path traversal, secret access, prompt/tool poisoning, stdout contamination, and unbounded command execution are blocked.

Required checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/agents/action-catalog | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/mcp-locks/readiness | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/write/readiness | ConvertTo-Json -Depth 6
Invoke-RestMethod http://127.0.0.1:8765/api/code-operator/gates | ConvertTo-Json -Depth 6
```

Acceptance:

- No agent coding action can apply source changes without active same-owner MCP lock and pre/post snapshots.
- No backend returns secret values.
- Any command runner is allowlisted and proof-recorded, not arbitrary shell by default.

### Agent 6: Release, GitHub, and Documentation Truth

Task ID: `H3D-CLAUDE-POLISH-RELEASE-DOCS-2026-05-06`

Scope:

- Update Roadmap and handoff docs with real current state.
- Confirm README and docs do not overclaim runtime/app/agent completion.
- Confirm every PR has a useful body: changed files, proof, tests, screenshots/traces, risks, rollback.
- Confirm all green PRs are ready to merge in the documented order.
- If a PR is not truly ready, mark it blocked and create/assign the fix task.

Acceptance:

- Current GitHub PR table is recorded.
- Docs match live route counts and runtime truth.
- Merge plan includes exact order, conflict notes, and post-merge gates.

## Global Gates Before Any Merge Batch

Run from `G:/Github/h3d-gui-wiring-codex` after applying or rebasing the target PR batch:

```powershell
python -m py_compile 03_implementation/src/hermes3d/api/routes/*.py 03_implementation/src/hermes3d/services/*.py
python 03_implementation/scripts/scan_active_ui_no_fake.py
cd 03_implementation/ui
npm run lint
npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Dashboard|Source OS|Settings|Agents|Observe|Roadmap|Plugins|Jobs|Artifacts|Approvals|Voice|Learning|Autopilot|Design|3D Generation"
```

If any gate fails:

- Fix it before merge if the failure is in the current PR batch.
- If it belongs to another open PR, stop and update the merge order.
- If it is pre-existing, create a dedicated blocker PR and mark the current PR as dependent.

## Branch, Commit, Push, PR Rule

When a lane is complete and locally passing:

1. Stage only lane-owned files.
2. Commit with a specific message.
3. Push the lane branch.
4. Open a PR.
5. Include proof, tests, screenshots/traces, and rollback notes.
6. Do not wait days with completed local work unpushed.

Green PRs can be merged later. Completed local work should still be visible on GitHub immediately so the project truth is not trapped in one machine.

## Final Definition of Done

The Claude polish pass is done when:

- every lane has locks/evidence or a documented block,
- every merged PR passed global gates,
- every open PR has a clear status,
- no visible UI uses fake/mock/simulated data,
- every action is live, blocked with proof, or removed,
- S1 safety remains enforced,
- Hermes Agents can enumerate real action contracts,
- Roadmap reflects what is complete and what still needs work.
