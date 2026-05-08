# Hermes3D-OS

## Role in H3D OS

`G:\Github\Hermes3D-OS` is the **standalone Hermes-powered 3D print factory controller** — a SEPARATE GitHub repo (`Ghenghis/Hermes3D-OS.git`, distinct remote) that ships the user-facing GUI shell. It is the consumer of the contracts produced in `Hermes3D` and `h3d-gui-wiring-codex`. Layout-wise it diverges from the 7-folder methodology and adopts a Node-style monorepo: `apps/web/` (the static SPA shell that boots on Source OS by default), `apps/api/` (FastAPI bridge module `hermes3d_api`), `packages/`, `skills/`, `workflows/`, `profiles/`, plus Playwright E2E (`playwright.config.ts`).

The repo embodies the OS surface described in `Hermes3D-OS.md`: 16 pages (Source OS → Dashboard → Autopilot → Design → 3D Generation → Jobs → Printers → Observe → Voice → Agents → Learning → Artifacts → Approvals → Plugins → Settings → Roadmap), 55 manifest modules, and the digital thread Source Bench → Design/CAD → 3D Generation → Slicer Compiler → Dispatch → Observation → Materials/Calibration → Trust/Audit. It is where Action Window wiring, font-scale popover, agents-dispatch buttons, and approval row → Action Window flows were implemented across 4 lanes (Claude/Codex/Kilocode/Windsurf).

It also bridges to the upstream Hermes Agent system through `apps/api/hermes3d_api/services/hermes_bridge.py` (currently uncommitted) and adds Workflow Gates, Skills, Work Queue services.

## Recent activity

Branch: `develop` (HEAD).

```
e9c22e8 2026-05-04 Windsurf-4: Agents Dispatch, Learning Bookmark, Artifacts Download, Approvals Approve/Reject buttons (#31)
ccfd189 2026-05-04 feat(wire/artifacts-row-click): artifact row → Action Window (#44)
4871302 2026-05-04 feat(wire/action-window-history): back/fwd navigation in Action Window (#34)
4515d6b 2026-05-04 wire(global-event-bus-logger): debug logger on actionwindow:render when ?debug=1 (#46)
d0ee37d 2026-05-04 feat(ui): font scale popover + Codex handoff prompts (#9)
9da8f72 2026-05-04 docs(handoffs): 4-agent split plan (Claude/Codex/Kilocode/Windsurf) (#10)
6b2f5fe 2026-05-04 feat: add UI settings with persistence and E2E tests (Windsurf-1) (#17)
e43917f 2026-05-04 wire(approvals-pending-actionwindow): approval row → Action Window (#47)
0938671 2026-05-04 wire(observe-camera-tile-click): camera tile → Action Window (#41)
7985de0 2026-05-04 wire(learning-topics-actionwindow): learning topic -> Action Window (#39)
```

Dirty files: `apps/api/hermes3d_api/{db,main,schemas}.py`, `apps/web/{index.html,source_manifest.json}`. Untracked: `services/{agents.py,gates/,hermes_bridge.py,skills.py,work_queue.py}`, `gates-panel.js`, `skills-panel.js`, `tests/api/`, `tests/e2e/setting-reference-app-cards.spec.ts`, `docs/hermes-agent-bridge.md`, `skills/`.

## Branches

Selected (truncated):

- `develop` — current HEAD
- `app/blender-cli`, `app/comfyui`, `app/cura`, `app/fluidd`, `app/langgraph-langchain`, `app/octoprint`, `app/openscad`, `app/pip-orchestration`, `app/prusaslicer`, `app/python-utils`, `app/triposr`
- `btn/dashboard-and-jobs`, `btn/printers-observe-voice`
- `codex/hermes3d-os-ui-docs-alignment`
- `docs/agent-starters`, `docs/kilocode-wiring-codex-installs`
- `feat/install-foundation-and-trimesh`
- `feature/api`, `feature/docs`, `feature/fdm-monster-sidecar`, `feature/hermes-runtime`, `feature/modeling-worker`, `feature/moonraker-connector`, `feature/slicer-worker`, `feature/web-ui`, `feature/workflow-gates`
- `foundation/action-window`, `foundation/install-endpoint`, `foundation/playwright-harness`

Remote: `origin = https://github.com/Ghenghis/Hermes3D-OS.git` (DIFFERENT remote from Hermes3D).

## Key directories (deep tree)

- `apps/`
  - `api/` — FastAPI bridge (`Dockerfile`, `README.md`, `hermes3d_api/`)
    - `hermes3d_api/` → `db.py`, `main.py`, `schemas.py`, `services/` (untracked: `agents.py`, `gates/`, `hermes_bridge.py`, `skills.py`, `work_queue.py`)
  - `web/` — static SPA: `index.html`, `app.js`, `action-window.js`, `gates-panel.js`, `skills-panel.js`, `settings-panel.js`, `source-os.js`, `voice-panel.js`, `voice-settings.html`, `styles.css`, `source_manifest.json`, `proof/`
- `configs/`, `data/`, `node_modules/`, `packages/`, `profiles/`, `scripts/`, `skills/` (untracked), `source-lab/`, `storage/`, `tests/` (Playwright E2E + API), `ux-lab/`, `workflows/`
- `docs/` — `ARCHITECTURE.md`, `BRANCHING.md`, `DAY_TO_DAY_ROADMAP.md`, `DEVELOPMENT.md`, `FULL_STACK_3D_GENERATION.md`, `GETTING_STARTED.md`, `HERMES_AGENT_SYSTEM.md`, `IDLE_LEARNING_MODE.md`, `LOCAL_MODEL_SETUP.md`, `MVP_RUNBOOK.md`, `OS_INTERFACE_DESIGN.md`, `PRINTER_ONBOARDING.md`, `RESEARCH_2026_ACTION_PLAN.md`, `ROADMAP.md`, `TEST_PRINTER_DATA.md`, `UI_VISUAL_PROOF.md`, `VISION_AGENT_CONTRACT.md`, `VISUAL_EVIDENCE.md`, `VOICE_LAYER.md`, `WORKFLOW_GATES.md`, `handoffs/`, `hermes-agent-bridge.md` (untracked), `ui-proof/`

## Key files

| File | Purpose |
| --- | --- |
| `README.md` | Hermes3D OS overview — 16 pages, 55 manifest modules, factory flows |
| `package.json` | `hermes3d-os-e2e` v0.0.1 — Playwright E2E harness, serve:web (8000), serve:api (uvicorn 18081) |
| `pyproject.toml` | `hermes3d-os` v0.1.0 — FastAPI 0.115.6, httpx, pydantic 2.10.5, uvicorn 0.34.0 |
| `playwright.config.ts` | E2E harness config |
| `apps/api/hermes3d_api/main.py` | FastAPI app entry (currently dirty) |
| `apps/web/app.js` | SPA bootstrap |
| `apps/web/action-window.js` | Action Window controller (back/fwd history, render bus) |
| `apps/web/source-os.js` | Source OS page controller |
| `apps/web/source_manifest.json` | 55-module source registry |
| `docs/HERMES_AGENT_SYSTEM.md` | Agent system contract (consumer view) |
| `docker-compose.example.yml` | Reference compose stack |

## Relationships to other H3D repos

- **Distinct remote** from `Hermes3D` and `h3d-gui-wiring-codex` (different GitHub repo).
- `apps/api/hermes3d_api/services/hermes_bridge.py` (untracked) is the bridge to Hermes3D's MCP/FastAPI surface — consumes contracts from canonical `Hermes3D`.
- `apps/web/source_manifest.json` mirrors the 55-module list described in `Hermes3D/Hermes3D-OS.md`.
- Workflow gates / skills / agents UIs are the consumer side of contracts validated in `h3d-gui-wiring-codex`.
- Independent of `Hermes3D-handoffs` and `Hermes3D-worktrees` (no worktree relationship).

## Status

**ACTIVE** — most recent commit 2026-05-04 (Windsurf-4 PR #31). 5 dirty files + multiple untracked services (`agents`, `gates`, `hermes_bridge`, `skills`, `work_queue`) suggest current in-flight Hermes-bridge integration work.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b1020"/>
  <rect x="170" y="120" width="160" height="60" fill="#7c2d12" stroke="#fdba74" stroke-width="2" rx="6"/>
  <text x="250" y="145" fill="#fed7aa" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="bold">Hermes3D-OS</text>
  <text x="250" y="165" fill="#fed7aa" font-family="sans-serif" font-size="10" text-anchor="middle">GUI shell + apps/api</text>
  <rect x="20" y="30" width="130" height="50" fill="#1e3a8a" stroke="#60a5fa" stroke-width="1.5" rx="5"/>
  <text x="85" y="50" fill="#e0e7ff" font-family="sans-serif" font-size="11" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="85" y="68" fill="#a5b4fc" font-family="sans-serif" font-size="9" text-anchor="middle">FastAPI + MCP source</text>
  <rect x="350" y="30" width="130" height="50" fill="#065f46" stroke="#6ee7b7" stroke-width="1.5" rx="5"/>
  <text x="415" y="50" fill="#d1fae5" font-family="sans-serif" font-size="10" text-anchor="middle">h3d-gui-wiring-codex</text>
  <text x="415" y="68" fill="#a7f3d0" font-family="sans-serif" font-size="9" text-anchor="middle">contracts</text>
  <rect x="20" y="220" width="130" height="50" fill="#3b0764" stroke="#c084fc" stroke-width="1.5" rx="5"/>
  <text x="85" y="240" fill="#e9d5ff" font-family="sans-serif" font-size="10" text-anchor="middle">apps/web (SPA)</text>
  <text x="85" y="255" fill="#e9d5ff" font-family="sans-serif" font-size="9" text-anchor="middle">16 OS pages</text>
  <rect x="350" y="220" width="130" height="50" fill="#3b0764" stroke="#c084fc" stroke-width="1.5" rx="5"/>
  <text x="415" y="240" fill="#e9d5ff" font-family="sans-serif" font-size="10" text-anchor="middle">apps/api</text>
  <text x="415" y="255" fill="#e9d5ff" font-family="sans-serif" font-size="9" text-anchor="middle">FastAPI bridge → Hermes3D</text>
  <line x1="170" y1="135" x2="150" y2="55" stroke="#60a5fa" stroke-width="1.5"/>
  <line x1="330" y1="135" x2="350" y2="55" stroke="#6ee7b7" stroke-width="1.5" stroke-dasharray="3 2"/>
  <line x1="200" y1="180" x2="135" y2="220" stroke="#c084fc" stroke-width="1.5"/>
  <line x1="300" y1="180" x2="365" y2="220" stroke="#c084fc" stroke-width="1.5"/>
  <line x1="350" y1="245" x2="150" y2="55" stroke="#fdba74" stroke-width="1" stroke-dasharray="2 3" opacity="0.6"/>
  <text x="120" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">consumes</text>
  <text x="320" y="100" fill="#cbd5e1" font-family="sans-serif" font-size="9">conforms to</text>
  <text x="200" y="295" fill="#cbd5e1" font-family="sans-serif" font-size="9">hermes_bridge.py → Hermes3D MCP/FastAPI</text>
</svg>
