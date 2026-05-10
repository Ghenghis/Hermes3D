# Claude 20-Agent Hermes3D Completion Contract

Updated: 2026-05-06
Owner: codex-master
Purpose: let Claude Opus 4.7 Max coordinate up to 20 agents to complete Hermes3D OS while Codex owns the Hermes Agent programming ecosystem.

## Start Decisions For Claude

Use these answers if Claude asks how to start:

- Working tree: do not stash. First checkpoint the current WIP on `G:/Github/h3d-gui-wiring-codex`, branch `feat/hermes3d-7-complete-gui-repo-wiring`, then push that branch. The current tree contains the active GUI/source/backend work and must become the shared baseline instead of being hidden in a stash.
- Coordination location: `EnterWorktree` or otherwise operate directly in `G:/Github/h3d-gui-wiring-codex`. Do not coordinate from `G:/Github/hermes3d-mcp-lock-orchestrator` except to use Hermes MCP/locks.
- Wave size: use waves of 4-5 agents. Do not launch all 20 at once until the first wave proves the lock/test/proof flow.
- Codex ownership: Codex is actively working the code-operator lane. Do not edit the files listed in the Codex-owned section unless Codex explicitly releases them.
- Branching: after the checkpoint branch exists, each Claude lane creates its own worktree/branch from that checkpoint and locks only its lane files.
- Failure policy: every failing test, no-fake scan, route probe, or Playwright check must be fixed by the owning lane before handoff. No "noted" failures.

## Non-Negotiable Contract

- Use Hermes locks before editing: claim task, lock files, heartbeat, append proof, release files, release task.
- `MCP_LOCK_WORKSPACE` must match the exact worktree being edited. A lock from
  the wrong repo/worktree is false proof and blocks the lane.
- Every visible UI control must be live-backed, proof-backed, or honestly blocked. No fake, mocked, simulated, placeholder, or "looks wired" surfaces.
- Every visible UI change needs visual proof: screenshot artifact path, route,
  viewport, console/404 check result, and proof event id.
- All failures must be corrected to pass state before a lane is called done.
- S1 `192.168.0.12` is camera/read-only only. No move, upload, print, or test.
- T1 #1 `192.168.0.10`, T1 #2 `192.168.0.11`, and V400 `192.168.0.34` can be tested only through policy-gated backend routes.
- Secrets are runtime-only from `G:/private/.env`; never commit, echo, screenshot, or send them to frontend.
- Private env values are usable only through approved backend adapters,
  redacted sandbox env injection, or provider clients that never print values.
  Agents may reference env key names and redacted source/provenance, but must
  never display, diff, copy, serialize, screenshot, log, put into CLI args, PR
  bodies, markdown, proof artifacts, test snapshots, or browser-visible UI.
- Do not touch Codex-owned code-operator files during this contract:
  - `03_implementation/src/hermes3d/services/code_history.py`
  - `03_implementation/src/hermes3d/api/routes/code_operator.py`
  - code-operator sections in `03_implementation/src/hermes3d/api/routes/agents.py`
  - code-history schema rows in `03_implementation/src/hermes3d/db/schema.sql`

## Required Gates For Every Lane

Run the narrow gate for the files changed, then the shared gate:

```powershell
python -m py_compile 03_implementation/src/hermes3d/api/routes/*.py 03_implementation/src/hermes3d/services/*.py
cd 03_implementation/ui
npm run lint
npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Source OS|Settings|Agents|Dashboard|Observe|Roadmap|Plugins|Jobs|Artifacts|Approvals|Voice|Learning|Autopilot|Design|3D Generation"
cd ..
python scripts/scan_active_ui_no_fake.py
```

If a gate fails, fix it in the same lane before handoff. If a failure is outside the lane's files, stop and report the exact file and owner instead of editing across lanes.

Security scans are required for any lane touching auth, provider routing,
process/shell execution, filesystem mutation, MCP/tooling, secrets, printer
policy, network access, or sandbox behavior. A failed scan is a lane blocker.

## 20 No-Conflict Lanes

| Agent | Task ID | Branch suffix | Owned files | Goal |
| --- | --- | --- | --- | --- |
| 01 | H3D-CLAUDE-SOURCE-SLICERS | `claude/source-slicers` | `03_implementation/src/hermes3d/services/module_runtime.py`, slicer tests/proof only | Finish slicer CLI verifiers/runners for Prusa, Orca, FLSUN, CuraEngine, SuperSlicer, Slic3r, Bambu where real CLI exists. |
| 02 | H3D-CLAUDE-SOURCE-MODELERS | `claude/source-modelers` | modeler verifier config/tests/proof only | Finish Blender, OpenSCAD, FreeCAD, CadQuery, build123d, trimesh/numpy-stl/Open3D verifiers with real import/version/help gates. |
| 03 | H3D-CLAUDE-SOURCE-PRINTFARM | `claude/source-printfarm` | print-farm verifier config/tests/proof only | Finish Moonraker/Klipper/Fluidd/Mainsail/OctoPrint/Printrun read-only service/CLI gates. |
| 04 | H3D-CLAUDE-SOURCE-GEN3D | `claude/source-gen3d` | generation verifier config/tests/proof only | Finish ComfyUI/TRELLIS/Hunyuan3D/TripoSR source/runtime readiness without heavy downloads while printers active. |
| 05 | H3D-CLAUDE-SOURCE-FIRMWARE | `claude/source-firmware` | firmware verifier config/tests/proof only | Finish firmware source/toolchain proof gates, never flash or connect to printer boards. |
| 06 | H3D-CLAUDE-SOURCE-UI | `claude/source-ui` | `03_implementation/ui/src/tabs/SourceOS.tsx`, source-os components only | Make Source OS show CLI readiness, setup runner status, proof, update/rollback state clearly without cutoff. |
| 07 | H3D-CLAUDE-SETTINGS-PLUGINS | `claude/settings-plugins` | Settings/Plugins tabs/components/routes only | Finish update center summary, provider health, app updater readiness, failsafe/rollback surfacing. |
| 08 | H3D-CLAUDE-LEARNING-AUTOPILOT | `claude/learning-autopilot` | Learning/Autopilot tabs/routes only | Make idle work kinds truthfully executable or blocked with proof; no hidden fake activation. |
| 09 | H3D-CLAUDE-VOICE | `claude/voice` | Voice tab/routes/components only | Finish transcript history, agent voice playback controls, voice proof review, no frontend secret leakage. |
| 10 | H3D-CLAUDE-OBSERVE | `claude/observe` | Observe tab/routes/components only | Finish camera layouts, refresh reliability, S1 90-degree default, zoom/fit controls, V400 status. |
| 11 | H3D-CLAUDE-PRINTERS | `claude/printers` | Printers tab/routes/config tests only | Finish printer onboarding/profile wizard, Moonraker probe, camera URL validation, S1 lock proof. |
| 12 | H3D-CLAUDE-DESIGN | `claude/design` | Design tab/routes/generator tests only | Expand real CAD templates/provider checks without fake generated assets. |
| 13 | H3D-CLAUDE-GEN3D | `claude/gen3d` | 3D Generation tab/routes/tests only | Expand real generation provider readiness and proof-backed local templates. |
| 14 | H3D-CLAUDE-JOBS | `claude/jobs` | Jobs tab/routes/tests only | Harden job repair/retry/rollback UI and proof state, no printer writes without policy. |
| 15 | H3D-CLAUDE-ARTIFACTS-PROOF | `claude/artifacts-proof` | Artifacts/Proof docs/routes/tests only | Make proof bundles, artifacts, snapshots, screenshots discoverable and auditable. |
| 16 | H3D-CLAUDE-APP-SHELL | `claude/app-shell` | App shell/layout/sidebar/topbar CSS only | Finish resizable panels, no cutoff, density polish, Simple/Main mode parity. |
| 17 | H3D-CLAUDE-PLAYWRIGHT | `claude/playwright` | Playwright tests only | Add tab-specific e2e/visual proofs for all primary tabs and no-fake expectations. |
| 18 | H3D-CLAUDE-DOCS-PROOF | `claude/docs-proof` | docs/proof/README/ROADMAP sections not owned by Codex | Sync docs with live counts, printer policy, proof ids, tab status. |
| 19 | H3D-CLAUDE-SECURITY-MCP | `claude/security-mcp` | security tests/docs and MCP config only | Check MCP/tool boundary, prompt injection/tool poisoning, secret redaction, path traversal. |
| 20 | H3D-CLAUDE-FINAL-INTEGRATOR | `claude/final-integrator` | Integration report only unless explicitly handed files | Compile lane results, identify failed gates, assign fixes, and do not edit lane-owned files. |

## Completion Rule

A lane is complete only when it reports:

- lock task id and file locks used
- exact worktree path and verified `MCP_LOCK_WORKSPACE`
- folder-index files or roadmap sections used for scope
- pre-change snapshots and post-change proof for every touched file
- provider build/review artifacts when the lane uses Hermes Agents, MiniMax,
  DeepSeek, OpenCode, or OpenHands
- changed files
- exact tests/gates run
- visual proof artifact path, viewport, changed tab/route, and console/404
  status for any visible UI change
- security scan result when auth/provider/process/filesystem/MCP/printer/network
  behavior changed
- rollback or restore proof id
- branch, commit, push, and PR evidence
- proof artifact paths and proof event ids
- remaining blockers, if any
- `git status --short`

No lane may call itself done with failing tests, hidden mocks, undocumented
blocked states, stale base/index context, unresolved critic findings, missing
visual proof, missing rollback proof, or unreleased locks.
