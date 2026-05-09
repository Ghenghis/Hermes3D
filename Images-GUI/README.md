# Hermes3D OS GUI Reference Pack

Created: 2026-05-08

This folder is the visual direction pack for the next Hermes3D OS GUI pass. It is a source-of-truth reference collection for the desired look, density, layout behavior, dashboard modes, themes, and app/action-window surfaces.

Important: these images are visual references, not runtime proof. Runtime truth must come from Playwright screenshots, console checks, no-fake scans, and backend evidence after implementation.

## Current Count

- Total PNG references: 31
- Remaining images needed for this reference-pack scope: 0
- Primary tabs covered: 16 of 16
- Settings subtabs covered: 6 of 6
- Voice subtabs covered: 3 of 3
- Source OS categories covered: 11 of 11
- 60-app workbench covered: yes, by category and coverage matrix
- Themes covered: default, cyberpunk, matrix, tron, industrial forge, aurora operator

## Required Visual Direction

All future Hermes3D OS GUI work should follow this direction:

- Even darker background than the current app.
- Multi-color accents, not a one-note blue dashboard.
- Sharp operational panels, about 6px radius.
- Dense but usable command-center layout.
- Resizable central Action Window for slicer, modeling, camera, proof, logs, agents, and all 60 apps.
- Simple, Advanced, and Custom dashboard modes.
- Custom dashboards must allow draggable/resizable widgets.
- Theme selection must be user-changeable.
- Existing backend truth must be preserved: no fake data, no invented readiness, no exposed secrets.
- Every visible feature must map to a real backend route, app state, proof artifact, or honest blocked state.

## Folder Map

| Folder | Purpose |
|---|---|
| `00-user-current-downloads/` | User-provided/current approved references kept for comparison. |
| `01-dashboard-modes/` | Simple, Advanced, and Custom dashboard mode references. |
| `02-primary-pages/` | Primary tab references covering Autopilot, Design, 3D Generation, Jobs, Printers, Observe, Agents, Learning, Artifacts, Approvals, Plugins, and Roadmap. |
| `03-settings-voice/` | Settings subtabs and Voice/communication subtabs. |
| `04-source-os/` | Source OS categories plus the 60-app coverage matrix. |
| `05-action-windows/` | Resizable Action Window templates for core apps and advanced tools. |
| `06-states-responsive/` | Loading, empty, blocked, recovering, compact desktop, and fullscreen action states. |
| `07-plugins-skills-mcp/` | Plugins, skills, MCP servers, app connectors, and integration center. |
| `08-app-utility-pages/` | Workflows, Print Queue, Files & Projects, System Logs, Proof & Reports, Service Health, Notifications, Safety/Security. |
| `09-themes/` | Theme variants: default, cyberpunk, matrix, tron, industrial forge, aurora operator. |

## Page Coverage

Primary Hermes3D tabs covered:

- Source OS
- Dashboard
- Autopilot
- Design
- 3D Generation
- Jobs
- Printers
- Observe
- Voice
- Agents
- Learning
- Artifacts
- Approvals
- Plugins
- Settings
- Roadmap

Additional app/utility surfaces covered:

- Workflows
- Print Queue
- Files & Projects
- Proof & Reports
- System Logs
- Service Health
- Notifications Center
- Safety/Security
- Blender MCP
- Slicing
- OpenCode/OpenHands terminal workspace
- MCP Hub
- Skills Registry
- Plugin Marketplace
- App Connector Center
- Agent Recovery Controller

Source OS app coverage:

- Modelers: 13
- Slicers: 11
- Print Farm: 10
- Agents: 7
- Firmware: 6
- 3D Generation: 6
- Hardware: 3
- Library: 1
- Materials: 1
- Research: 1
- Utilities: 1

## Implementation Contract

Claude/Codex implementation must not copy these by vibes. It must convert them into a measured visual system:

1. Define design tokens:
   - backgrounds
   - panel colors
   - accent palette
   - status colors
   - border radius
   - shadow/glow rules
   - typography scale
   - grid gaps
   - card heights
   - sidebar/topbar dimensions

2. Build one shared shell:
   - sidebar
   - top bar
   - mode selector
   - theme selector
   - resizable Action Window
   - task/proof drawer
   - widget grid
   - app launcher

3. Build three dashboard modes:
   - Simple
   - Advanced
   - Custom

4. Make every app open inside the Action Window:
   - slicers
   - modelers
   - cameras
   - proof viewer
   - logs
   - agents
   - OpenCode/OpenHands
   - MCP Hub
   - 60-app detail views

5. Preserve all current features:
   - no route removals
   - no hidden tabs
   - no fake data
   - no secret values in UI
   - no unsupported production claims

## Playwright Visual Oracle

Implementation is not accepted until Playwright captures and verifies:

- Every primary tab at desktop size.
- Simple, Advanced, and Custom dashboards.
- All settings subtabs.
- All voice subtabs.
- Source OS home plus every category.
- Action Window normal, expanded, and fullscreen.
- Compact desktop layout.
- Loading, empty, blocked, recovering, completed states.
- Theme switching.
- Console clean: no runtime errors.
- No network 404s for expected app routes.
- `scan_active_ui_no_fake.py` passes.

Suggested screenshot matrix:

- `1920x1080`
- `1600x900`
- `1366x768`
- compact desktop with collapsed sidebar

## Non-Negotiables

- Keep the user-approved references always accessible.
- Do not overwrite this folder with generated runtime screenshots.
- Store future Playwright proofs under proof/artifact folders, then link them back here.
- Treat this folder as the visual target, and Playwright evidence as the runtime proof.
