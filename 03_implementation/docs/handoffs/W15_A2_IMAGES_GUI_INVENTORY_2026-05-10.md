# W15-A2 Images-GUI Inventory (2026-05-10)

**Owner:** Wave 15 — Agent 2 (assembled by Agent 8 from filesystem scan; A2 handoff was missing from `origin/develop` at the time A8 ran)
**Source of truth:** `Images-GUI/` directory at commit `c13e30f` (origin/develop)
**Total PNGs:** 31

## Method

Filesystem walk + `PIL.Image.size` for every `.png` under `Images-GUI/`. Cross-checked the result against the existing `visual-targets.json` (290 LoC, 30 targets) authored by W6-6.

## Counts by section

| Section | Files | Class |
|---|---|---|
| 00-user-current-downloads | 10 | 9 generated + 1 baseline (single) |
| 01-dashboard-modes | 6 | single (advanced/simple/custom × a/b) |
| 02-primary-pages | 3 | collage (4 tabs each) |
| 03-settings-voice | 2 | collage (settings 6 subtabs + voice 3 subtabs) |
| 04-source-os | 3 | 1 collage (60-app matrix) + 2 single |
| 05-action-windows | 2 | single |
| 06-states-responsive | 1 | collage (loading/empty/blocked/recovering) |
| 07-plugins-skills-mcp | 1 | collage (plugins/skills/mcp/connectors) |
| 08-app-utility-pages | 2 | collage (workflow+queue+files+logs / proof+health+notif+safety) |
| 09-themes | 1 | collage (6 theme palettes) |
| **Total** | **31** | **20 single + 11 collage** |

## Dimensions

- **1536 × 1024** (25 files): default reference viewport
- **1672 × 941** (5 files): `Generated image 1.png`, `Generated image 2.png`, `01-dashboard-modes/simple-dashboard-a.png`, `01-dashboard-modes/simple-dashboard-b.png`, `04-source-os/source-os-60-app-coverage-matrix.png`
- **1586 × 992** (1 file): `04-source-os/source-os-remaining-categories.png`

## Collage region counts (estimated; refined in W15-A8 visual-targets.canonical.json)

| File | Regions |
|---|---|
| `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 4 |
| `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 4 |
| `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | 4 |
| `03-settings-voice/settings-subtabs-all.png` | 6 |
| `03-settings-voice/voice-communication-subtabs.png` | 3 |
| `04-source-os/source-os-60-app-coverage-matrix.png` | 60 (1 cell per app) |
| `05-action-windows/action-window-core-apps.png` (single) | n/a |
| `06-states-responsive/states-responsive-reference.png` | 4 (loading/empty/blocked/recovering) |
| `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | 4 |
| `08-app-utility-pages/workflow-printqueue-files-logs.png` | 4 |
| `08-app-utility-pages/proof-health-notifications-safety.png` | 4 |
| `09-themes/theme-variants-reference.png` | 6 (default/cyberpunk/matrix/tron/forge/aurora) |

## Themes referenced

`default`, `cyberpunk`, `matrix`, `tron`, `industrial_forge`, `aurora_operator` — six palettes shown in `09-themes/theme-variants-reference.png`.

## Consumers

- `03_implementation/ui/tests/visual/visual-targets.json` (W6-6, currently locked by W14-PR1 oracle harness)
- `03_implementation/ui/tests/visual/visual-targets.canonical.json` (this W15-A8 PR — canonical superset)
- Future Playwright visual-proof oracle harness (W15-A9)

## Provenance

This handoff was assembled by W15-A8 from a deterministic filesystem scan because the A2-authored variant was not present on `origin/develop`. Treat as the working inventory for downstream lanes until a formal A2 handoff supersedes it.
