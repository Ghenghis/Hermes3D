# Hermes3D GitHub Sync Plan

Updated: 2026-05-06
Branch: `feat/hermes3d-7-complete-gui-repo-wiring`
Remote: `https://github.com/Ghenghis/Hermes3D`

## Current Truth

The active implementation worktree is `G:/Github/h3d-gui-wiring-codex`.

Current status before sync:

- Branch: `feat/hermes3d-7-complete-gui-repo-wiring`
- Upstream shown by git: `origin/develop`
- Dirty paths: 162 total
- Modified: 47
- Deleted: 28
- Untracked: 87

This tree must be checkpointed before Claude 20-agent lanes start. Stashing would hide the work and make agents rebuild or conflict with it.

## Sync Strategy

Do not make one huge anonymous commit unless gates are failing and a rescue checkpoint is needed. Preferred commit order:

1. `docs(contract): sync Hermes3D completion roadmap and Claude handoffs`
   - `03_implementation/ROADMAP.md`
   - `03_implementation/docs/handoffs/*.md`
   - contract/proof docs that describe the current work

2. `feat(api): add live Hermes3D backend routes and proof services`
   - `03_implementation/src/hermes3d/api/**`
   - `03_implementation/src/hermes3d/services/**`
   - `03_implementation/src/hermes3d/db/**`
   - `03_implementation/src/hermes3d/core/**`
   - `03_implementation/src/hermes3d/adapters/**`

3. `feat(ui): wire live Hermes3D tabs and remove mock UX`
   - `03_implementation/ui/src/**`
   - deleted `03_implementation/ui/src/data/mock/**`
   - deleted/replaced old tab shells
   - UI package/config files

4. `feat(source-os): add adapter schemas, source audits, and runtime proof`
   - `03_implementation/adapter_registry/schemas/**`
   - `03_implementation/scripts/**`
   - `03_implementation/proof/**` except oversized/generated archives if not needed

5. `test(e2e): add live GUI and no-fake proof coverage`
   - `03_implementation/ui/tests/e2e/**`
   - Playwright config/scripts
   - no-fake scanner proof

If a commit group fails isolated staging because files are tightly coupled, collapse groups 2-5 into a named checkpoint commit:

`checkpoint(gui): live Hermes3D OS wiring baseline for agent lanes`

Use that only after recording the failure reason in proof/handoff notes.

## Required Gates Before Push

Run:

```powershell
python -m py_compile 03_implementation/src/hermes3d/api/routes/*.py 03_implementation/src/hermes3d/services/*.py
python 03_implementation/scripts/scan_active_ui_no_fake.py
cd 03_implementation/ui
npm run lint
npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Dashboard|Source OS|Settings|Agents|Observe|Roadmap|Plugins|Jobs|Artifacts|Approvals|Voice|Learning|Autopilot|Design|3D Generation"
```

If one gate fails:

- Fix it if it is in the current staged scope.
- If it belongs to a future Claude lane, do not hide it. Commit only a clearly named checkpoint and record the failing gate in this file and in Hermes evidence.

## Push Rule

Push only after at least compile + no-fake scan pass. Full Playwright/lint should pass before opening/merging a PR unless the checkpoint is explicitly a rescue baseline.

Recommended push:

```powershell
git push origin feat/hermes3d-7-complete-gui-repo-wiring
```

Then Claude lanes branch from that pushed branch, not from an uncommitted local tree.

## Claude Coordination Answer

Tell Claude:

- Commit/push current WIP first; do not stash.
- Operate in `G:/Github/h3d-gui-wiring-codex`.
- Start with 4-5 agents, not 20.
- Respect Codex-owned code-operator files.
- Use Hermes locks for every lane.
- Fix failing gates to pass before reporting done.

