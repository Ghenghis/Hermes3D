# Hermes3D

## Role in H3D OS

`G:\Github\Hermes3D` is the **canonical source-of-truth repository** for the Hermes3D OS project. It is the upstream `Ghenghis/Hermes3D` checkout that holds the structured 7-folder methodology (`00_overview` through `06_release`), the FastAPI service code, the React/Vite UI under `03_implementation/ui/`, the `hermes3d` Python package, the agent contracts, the Hermes-Agent bridge, the truth-gates, and the marketing site (`site/`). It is the repo whose `develop` branch eventually backs the `ghenghis.github.io/Hermes3D` Pages site and whose `main` carries signed releases.

Functionally it ships an "OS for your print farm": a 9-stage orchestrator pipeline (INIT → VISION → GENERATE → REPAIR → TRUTH GATE → SLICE → PRINT → REPORT → DONE), six concurrent printability checks (manifold closure, wall thickness, overhang, support, bridge, first-layer area), 15 slicer/printer adapters, an MCP server with 16 tools, and HMAC-signed proof envelopes. **77 of 79 user-visible features are real today** (per its own README).

This repo also contains every Claude / Codex / Kilocode / Windsurf working-branch (the `claude/*`, `app/*`, `feature/*`, `foundation/*`, `polish-*` branches) plus a complete `agents/` directory of agent role contracts. It is therefore both the production codebase and the multi-agent collaboration substrate.

## Recent activity

Branch in this checkout: `chore/exclude-apps-folder` (HEAD).

```
6020de8 2026-05-03 chore: fully exclude apps/ from git (vendored installs, local-only)
5b11f6c 2026-05-03 docs(adr): ADR-014 — audit of blender-mcp-native (verdict: REJECT)
c3e68d1 2026-05-03 docs(handoff): overnight Codex queue — 1 master + 6 task briefs + roadmap
b767100 2026-05-03 feat(backup): local-only secrets backup — Syncthing + Restic-B2 scripts
```

Note: This worktree has been pinned to `chore/exclude-apps-folder` since 2026-05-03; later development continues in sibling worktrees (the `claude/*` branches are checked out as `+`-prefixed by `git branch -a`, meaning they are active in other worktrees under `G:\Github\hermes3d-mcp-lock-orchestrator\.claude\worktrees\` and `G:\Github\Hermes3D-handoffs\`).

## Branches

Selected (truncated — repo has 30+ branches):

- `backup/phase-2-before-email-rewrite` — restore point
- `chore/exclude-apps-folder` — current HEAD
- `claude/app-shell`, `claude/artifacts-proof`, `claude/design`, `claude/docs-proof`, `claude/final-codex-handoff`, `claude/final-integrator`, `claude/folder-index-2026-05-07` (this work), `claude/gen3d`, `claude/jobs`, `claude/learning-autopilot`, `claude/observe`, `claude/playwright`, `claude/polish-docs-audit`, `claude/polish-merge-audit`, `claude/polish-nofake-audit`, `claude/polish-runtime-audit`, `claude/polish-safety-audit`, `claude/polish-security-audit`, `claude/printers`, `claude/security-mcp`, `claude/settings-plugins`, `claude/source-firmware`, `claude/source-gen3d`, `claude/source-modelers`, `claude/source-printfarm`, `claude/source-slicers`, `claude/source-ui`, `claude/ts7026-ci-trigger-fix` — all checked out in sibling worktrees

Remote: `origin = https://github.com/Ghenghis/Hermes3D.git`

## Key directories (deep tree)

- `00_overview/` — vision, charters, executive summaries
- `01_requirements/` — product requirements, ADRs in pre-impl form
- `02_architecture/` — system + module designs, `02_architecture/policies/` (untracked staging)
- `03_implementation/`
  - `adapter_registry/` — adapter manifests + JSON Schemas (~50 schemas: `bambu_studio`, `cadquery`, `comfyui_trellis_wrapper`, `freecad`, `hermes_agent`, etc.)
  - `config/` — runtime configuration
  - `src/hermes3d/` — Python package
    - `adapters/`, `agents/`, `api/`, `app/`, `cli/`, `core/`, `env/`, `gateways/`, `orchestration/`, `planner/`, `registry/`
    - `api/server.py`, `api/mcp_server.py` — FastAPI + MCP entry points
    - `app/launcher.py` — desktop launcher
  - `ui/` — Vite + Tailwind + Playwright SPA (`src/`, `tests/`, `playwright.config.ts`, `tailwind.config.ts`)
- `04_testing/` — pytest + Playwright fixtures
- `05_truth_proof/` — proof envelopes, HMAC verifiers, Sigstore artifacts
- `06_release/` — release packs, ROADMAPs
- `agents/` — agent contracts (Hermes-Agent, codex-master, kilocode, windsurf, claude-* roles)
- `apps/` — vendored upstream installs (now `.gitignore`-excluded after 6020de8)
- `env/`, `schemas/`, `scripts/`, `site/`, `tmp/`, `var/`
- `handoffs/`, `Hermes3D-GUI-Wiring-Contract-Kit/`, `hermes3d_gui_contract_kit_v4.1/`

## Key files

| File | Purpose |
| --- | --- |
| `README.md` | Marketing-grade landing doc; cites pipeline-9-stage SVG, 17 truth gates, MCP coordination |
| `Hermes3D-OS.md` | OS surface description — 16 pages, factory flows, runtime stack |
| `HERMES3D_DELIVERY_README.md` | Delivery / packaging contract |
| `pyproject.toml` | `hermes3d-os-lite` v5.0.0 — trimesh, rtree, MCP/LangGraph deps |
| `requirements.txt` / `requirements-dev.txt` | Pinned runtime + dev deps |
| `run.bat` | Windows launcher for the FastAPI service + UI |
| `03_implementation/src/hermes3d/api/server.py` | **FastAPI app entry point** |
| `03_implementation/src/hermes3d/api/mcp_server.py` | MCP server (16 tools) |
| `03_implementation/src/hermes3d/app/launcher.py` | Desktop launcher |
| `03_implementation/ui/index.html` + `ui/src/` | Web UI shell |

## Relationships to other H3D repos

- **Hermes3D-handoffs** is a worktree of THIS repo (`.git` file points to `Hermes3D/.git/worktrees/Hermes3D-handoffs`), pinned to `docs/cp5.1-c-handoff` for architect briefs.
- **h3d-gui-wiring-codex** shares the same `origin` (Ghenghis/Hermes3D.git) — it is a separate clone used as the GUI-wiring lane / 20-agent contract workspace.
- **Hermes3D-OS** is a SEPARATE GitHub repo (`Ghenghis/Hermes3D-OS.git`) that holds the GUI shell + apps/web + FastAPI bridge that consumes Hermes3D's contracts.
- **Hermes3D-worktrees/lm-studio-default** is a worktree of THIS repo on `feat/cp-h3d-lm-studio-default`.
- Cross-imports: Hermes3D-OS `apps/api/hermes3d_api/services/hermes_bridge.py` calls into Hermes3D's MCP / FastAPI surface.

## Status

**ACTIVE** — primary canonical repo. The pinned worktree on `chore/exclude-apps-folder` is one of many; sibling worktrees cover the live Claude/Codex/Kilocode/Windsurf lanes, and `develop` is the published branch.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b1020"/>
  <rect x="180" y="120" width="140" height="60" fill="#1e3a8a" stroke="#60a5fa" stroke-width="2" rx="6"/>
  <text x="250" y="145" fill="#e0e7ff" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="bold">Hermes3D</text>
  <text x="250" y="165" fill="#a5b4fc" font-family="sans-serif" font-size="10" text-anchor="middle">canonical repo</text>
  <rect x="20" y="30" width="130" height="40" fill="#831843" stroke="#f472b6" stroke-width="1.5" rx="5"/>
  <text x="85" y="55" fill="#fbcfe8" font-family="sans-serif" font-size="11" text-anchor="middle">Hermes3D-handoffs</text>
  <rect x="20" y="230" width="130" height="40" fill="#1e40af" stroke="#93c5fd" stroke-width="1.5" rx="5"/>
  <text x="85" y="255" fill="#dbeafe" font-family="sans-serif" font-size="10" text-anchor="middle">Hermes3D-worktrees</text>
  <rect x="350" y="30" width="130" height="40" fill="#065f46" stroke="#6ee7b7" stroke-width="1.5" rx="5"/>
  <text x="415" y="50" fill="#d1fae5" font-family="sans-serif" font-size="10" text-anchor="middle">h3d-gui-wiring</text>
  <text x="415" y="62" fill="#d1fae5" font-family="sans-serif" font-size="10" text-anchor="middle">-codex</text>
  <rect x="350" y="230" width="130" height="40" fill="#7c2d12" stroke="#fdba74" stroke-width="1.5" rx="5"/>
  <text x="415" y="255" fill="#fed7aa" font-family="sans-serif" font-size="11" text-anchor="middle">Hermes3D-OS</text>
  <line x1="180" y1="135" x2="150" y2="55" stroke="#f472b6" stroke-width="1.5" stroke-dasharray="4 2"/>
  <line x1="180" y1="165" x2="150" y2="245" stroke="#93c5fd" stroke-width="1.5" stroke-dasharray="4 2"/>
  <line x1="320" y1="135" x2="350" y2="55" stroke="#6ee7b7" stroke-width="1.5"/>
  <line x1="320" y1="165" x2="350" y2="245" stroke="#fdba74" stroke-width="1.5"/>
  <text x="155" y="100" fill="#a5b4fc" font-family="sans-serif" font-size="9">worktree</text>
  <text x="160" y="210" fill="#a5b4fc" font-family="sans-serif" font-size="9">worktree</text>
  <text x="325" y="100" fill="#a5b4fc" font-family="sans-serif" font-size="9">sibling clone</text>
  <text x="335" y="210" fill="#a5b4fc" font-family="sans-serif" font-size="9">consumes API</text>
</svg>
