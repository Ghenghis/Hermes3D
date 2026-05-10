# W14-A1 — GUI Reference Inventory (2026-05-10)

**Owner:** claude-w14-a1-reference-inventory
**Mode:** Read-only (no edits to `Images-GUI/`)
**Lock task:** none (read-only)
**Predecessors:** PR #128 (Images-GUI pack), W11-4 ledger (manifest of 31 PNGs), W8-15 viewport-align fix (1536x1024 baseline)
**Sources cited:**
1. Pillow `PIL.Image.Image.size` (RGB pixel dimensions of each PNG, Python 3 docs).
2. `Images-GUI/GUI_REFERENCE_MANIFEST.json` (folder/category map + total count of 31).

## 1. Total PNG Count

**31** PNGs found via `Glob("Images-GUI/**/*.png")` — matches `total_png_references: 31` in `GUI_REFERENCE_MANIFEST.json` and the W11-4 ledger. Zero drift.

## 2. Sub-folder Breakdown

| Folder | Count | Purpose (per manifest) |
|---|---:|---|
| `00-user-current-downloads/` | 10 | User-provided/current approved references kept for comparison |
| `01-dashboard-modes/` | 6 | Simple, Advanced, and Custom dashboard mode references |
| `02-primary-pages/` | 3 | Primary tab references (composite, 4 tabs per PNG) |
| `03-settings-voice/` | 2 | Settings subtabs + voice/communication subtabs (composites) |
| `04-source-os/` | 3 | Source OS categories + 60-app coverage matrix |
| `05-action-windows/` | 2 | Resizable Action Window templates |
| `06-states-responsive/` | 1 | Responsive layouts and state screens |
| `07-plugins-skills-mcp/` | 1 | Plugins, skills, MCP servers, app connectors |
| `08-app-utility-pages/` | 2 | Workflows / queue / files / logs / proof / health / notifications / safety |
| `09-themes/` | 1 | Theme variants (default/cyberpunk/matrix/tron/forge/aurora) |
| **TOTAL** | **31** | — |

## 3. Per-Image Inventory

Categories: **single** = one PNG → one route/state | **collage** = multiple states/regions in one image, requires crop map | **state-variant** = light/dark/empty/full variations of the same target | **direction** = stylistic reference, not a 1:1 page snapshot.

Suggested route mappings come from `03_implementation/ui/tests/visual/visual-targets.json`. Viewport-normalization needed when dimensions != reference baseline `1536x1024` (set by W8-15).

| Path | Filename | Dims | Category | Classification | Suggested Route | Viewport-norm needed? |
|---|---|---|---|---|---|---|
| `00-user-current-downloads/Generated image 1.png` | Generated image 1.png | 1672x941 | direction | direction (not strict 1:1) | `/#dashboard` (status=future) | **Yes** |
| `00-user-current-downloads/Generated image 2.png` | Generated image 2.png | 1672x941 | direction | direction | `/#dashboard` (future) | **Yes** |
| `00-user-current-downloads/Generated image 3.png` | Generated image 3.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 4.png` | Generated image 4.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 5.png` | Generated image 5.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 6.png` | Generated image 6.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 7.png` | Generated image 7.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 8.png` | Generated image 8.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Generated image 9.png` | Generated image 9.png | 1536x1024 | direction | direction | `/#dashboard` (future) | No |
| `00-user-current-downloads/Hermes3D.png` | Hermes3D.png | 1536x1024 | user-baseline | single | `/` (live, baseline) | No |
| `01-dashboard-modes/advanced-dashboard-a.png` | advanced-dashboard-a.png | 1536x1024 | advanced | state-variant (A) | `/#dashboard` (live) | No |
| `01-dashboard-modes/advanced-dashboard-b.png` | advanced-dashboard-b.png | 1536x1024 | advanced | state-variant (B) | `/#dashboard` (future) | No |
| `01-dashboard-modes/custom-dashboard-a.png` | custom-dashboard-a.png | 1536x1024 | custom | state-variant (A) | `/#dashboard` (future) | No |
| `01-dashboard-modes/custom-dashboard-b.png` | custom-dashboard-b.png | 1536x1024 | custom | state-variant (B) | `/#dashboard` (future) | No |
| `01-dashboard-modes/simple-dashboard-a.png` | simple-dashboard-a.png | 1672x941 | simple | state-variant (A) | `/?ui=simple#dashboard` (future) | **Yes** |
| `01-dashboard-modes/simple-dashboard-b.png` | simple-dashboard-b.png | 1672x941 | simple | state-variant (B) | `/?ui=simple#dashboard` (future) | **Yes** |
| `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | primary-tabs-artifacts-approvals-plugins-roadmap.png | 1536x1024 | primary-composite | **collage (4 tabs)** | `/#artifacts` (live, anchor only; per-tab specs cover others) | No |
| `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | primary-tabs-autopilot-design-gen3d-jobs.png | 1536x1024 | primary-composite | **collage (4 tabs)** | `/#autopilot` (live, anchor only) | No |
| `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | primary-tabs-printers-observe-agents-learning.png | 1536x1024 | primary-composite | **collage (4 tabs)** | `/#printers` (live, anchor only) | No |
| `03-settings-voice/settings-subtabs-all.png` | settings-subtabs-all.png | 1536x1024 | settings | **collage (6 subtabs)** | `/#settings` (live) | No |
| `03-settings-voice/voice-communication-subtabs.png` | voice-communication-subtabs.png | 1536x1024 | voice | **collage (3 subtabs)** | `/#voice` (live) | No |
| `04-source-os/source-os-60-app-coverage-matrix.png` | source-os-60-app-coverage-matrix.png | 1672x941 | source-os | **collage (60 apps grid)** | `/#sources` (live) | **Yes** |
| `04-source-os/source-os-core-categories.png` | source-os-core-categories.png | 1536x1024 | source-os | **collage (multi-category)** | `/#sources` (live) | No |
| `04-source-os/source-os-remaining-categories.png` | source-os-remaining-categories.png | 1586x992 | source-os | **collage (multi-category)** | `/#sources` (live) | **Yes** |
| `05-action-windows/action-window-advanced-tools.png` | action-window-advanced-tools.png | 1536x1024 | action-window | **collage (multi-template)** | `/#dashboard` (future, W6-4) | No |
| `05-action-windows/action-window-core-apps.png` | action-window-core-apps.png | 1536x1024 | action-window | **collage (multi-template)** | `/#dashboard` (future, W6-4) | No |
| `06-states-responsive/states-responsive-reference.png` | states-responsive-reference.png | 1536x1024 | states | **collage (loading/empty/blocked/recovering)** | `/#dashboard` (future) | No |
| `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | plugins-skills-mcp-app-connectors.png | 1536x1024 | plugins | **collage (plugins+skills+mcp+connectors)** | `/#plugins` (live) | No |
| `08-app-utility-pages/proof-health-notifications-safety.png` | proof-health-notifications-safety.png | 1536x1024 | utility-composite | **collage (4 surfaces)** | `/#observe` (future, anchor only) | No |
| `08-app-utility-pages/workflow-printqueue-files-logs.png` | workflow-printqueue-files-logs.png | 1536x1024 | utility-composite | **collage (4 surfaces)** | `/#jobs` (future, anchor only) | No |
| `09-themes/theme-variants-reference.png` | theme-variants-reference.png | 1536x1024 | themes | **collage (6 theme variants)** | `/#dashboard` (future) | No |

Live targets per `visual-targets.json`: 11. Future targets: 20. Total: 31 — matches manifest.

## 4. Collage Images Requiring Crop Maps

15 PNGs are composites packing multiple regions/states into a single reference. They cannot be visually-diffed against a single route; W14 must produce per-region crop maps.

| # | PNG | Region count (rough) | Notes |
|---:|---|---:|---|
| 1 | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 4 | autopilot, design, gen3d, jobs |
| 2 | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 4 | printers, observe, agents, learning |
| 3 | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | 4 | artifacts, approvals, plugins, roadmap |
| 4 | `03-settings-voice/settings-subtabs-all.png` | 6 | providers, agents, printers, environment, updates, about |
| 5 | `03-settings-voice/voice-communication-subtabs.png` | 3 | voice_browser, transcript_history, proof_review |
| 6 | `04-source-os/source-os-60-app-coverage-matrix.png` | ~60 | 60-app grid; needs per-app crop map |
| 7 | `04-source-os/source-os-core-categories.png` | ~6 | core categories panel grid |
| 8 | `04-source-os/source-os-remaining-categories.png` | ~5 | remaining categories panel grid |
| 9 | `05-action-windows/action-window-core-apps.png` | 4-6 | multiple Action Window templates side-by-side |
| 10 | `05-action-windows/action-window-advanced-tools.png` | 4-6 | multiple advanced-tool templates side-by-side |
| 11 | `06-states-responsive/states-responsive-reference.png` | 4-6 | loading, empty, blocked, recovering, compact, fullscreen |
| 12 | `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | 4 | plugins, skills, MCP servers, app connectors |
| 13 | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 4 | workflow, print queue, files & projects, system logs |
| 14 | `08-app-utility-pages/proof-health-notifications-safety.png` | 4 | proof & reports, service health, notifications, safety/security |
| 15 | `09-themes/theme-variants-reference.png` | 6 | default, cyberpunk, matrix, tron, industrial forge, aurora operator |

**Region-count total (rough): ~115 distinct UI states** packed into 15 collage PNGs.

The 6 dashboard PNGs in `01-dashboard-modes/` are state-variants (A/B per mode), not collages — each represents one full-screen state. The user baseline `Hermes3D.png` and the 9 `Generated image *.png` are direction/single-state, not collages.

## 5. Dimension Outliers

Reference baseline (per W8-15 / `playwright.visual.config.ts`): **1536x1024**.

26 of 31 PNGs (84%) match the baseline. **5 outliers** require viewport-normalization decisions:

| # | Path | Dims | Outlier type | Used in visual-targets? | Notes |
|---:|---|---|---|---|---|
| 1 | `04-source-os/source-os-60-app-coverage-matrix.png` | 1672x941 | wider+shorter than baseline | live target `04_source_os_60_app_coverage_matrix` | Flagged by W13-6 / W8-15 as a remaining-diff target after viewport-align. |
| 2 | `04-source-os/source-os-remaining-categories.png` | 1586x992 | slightly wider+shorter | live target `04_source_os_remaining_categories` | Flagged by W13-6 / W8-15. |
| 3 | `01-dashboard-modes/simple-dashboard-a.png` | 1672x941 | wider+shorter | future target `01_dashboard_simple_a` | Status=future today; will hit the same diff mode as #1 once Simple dashboard ships (W6-3). |
| 4 | `01-dashboard-modes/simple-dashboard-b.png` | 1672x941 | wider+shorter | future target `01_dashboard_simple_b` | Same as #3. |
| 5 | `00-user-current-downloads/Generated image 1.png` | 1672x941 | wider+shorter | future target `00_user_generated_1` (direction-only, soft tolerance 0.2) | Direction reference; non-blocking. |
| 5b | `00-user-current-downloads/Generated image 2.png` | 1672x941 | wider+shorter | future target `00_user_generated_2` (direction-only) | Direction reference; non-blocking. |

(Two `Generated image *.png` outliers are listed under #5 because they share class — total count of unique outliers is 6 PNGs across 5 outlier dimension groups: `1672x941`, `1586x992`. Distinct outlier shapes = 2.)

**Live, blocking outliers:** 2 (`04-source-os` matrix + remaining-categories). Both already known per W8-15.
**Future, non-blocking outliers:** 4 (2 simple-dashboard + 2 generated-image direction PNGs).

### Recommendation for W14

Two viable paths (echoing W8-15's option matrix, now scoped per-image instead of globally):

- **Per-image viewport override.** Extend `visual-targets.json` schema with optional `viewport: { width, height }` so the spec resizes the viewport per target (e.g. 1672x941 for `04_source_os_60_app_coverage_matrix`). Surgical, no PR #128 churn, but adds spec complexity.
- **Re-capture outliers at 1536x1024.** Simpler in the harness, but mutates user-approved baselines — out of scope per W8-15's option B veto.

Wave 14 should pick the per-image override path unless user explicitly authorizes baseline re-capture.

## 6. Manifest vs Filesystem Reconciliation

| Field | Manifest value | Filesystem value | Drift? |
|---|---|---|---|
| `total_png_references` | 31 | 31 | No |
| `remaining_images_needed_for_current_scope` | 0 | 0 | No |
| `reference_groups[*].folder` | 10 sub-folders | 10 sub-folders | No (all 10 present, all populated) |
| `coverage.primary_tabs.covered` | 16 / 16 | 3 PNGs cover 12 tabs (4-per-collage) + per-tab via composites; all 16 reachable as anchors | Aligned (collages cover 12 of 16; remaining 4 — Source OS, Dashboard, Voice, Settings — covered by their dedicated folders) |
| `coverage.settings_subtabs.covered` | 6 / 6 | 1 PNG (`settings-subtabs-all.png`) | Aligned (collage) |
| `coverage.voice_subtabs.covered` | 3 / 3 | 1 PNG (`voice-communication-subtabs.png`) | Aligned (collage) |
| `coverage.source_os_categories.covered` | 11 / 11 | 2 PNGs (`source-os-core-categories.png` + `source-os-remaining-categories.png`) | Aligned (split across 2 collages) |
| `coverage.themes` | 6 themes | 1 PNG (`theme-variants-reference.png`) | Aligned (collage with 6 variants) |
| `reference_groups[*]` folder list | Lists 10 folders | All 10 exist on disk | No drift |

**No drift detected.** Manifest, README, and filesystem are consistent. Filesystem PNG count (31) equals manifest declaration (31) equals W11-4 ledger expectation (31).

### Cross-reference with `visual-targets.json`

`visual-targets.json` declares 31 targets, one per PNG, with status `live` (11) or `future` (20). All 31 PNG paths in the filesystem appear as `reference` fields in `visual-targets.json`. No orphan PNGs. No missing targets.

## Sources

1. **Pillow `PIL.Image.size` documentation** — `Image.size` returns `(width, height)` in pixels for the open image. Used to capture every PNG's true dimensions (executed via `python -c "from PIL import Image; ..."` over `Images-GUI/**/*.png`).
2. **`Images-GUI/GUI_REFERENCE_MANIFEST.json`** — declares `total_png_references: 31`, the 10-folder map, and per-category coverage counts. Used to reconcile filesystem against the W11-4 ledger expectation.

Supporting artifact (not counted as a primary source): `03_implementation/ui/tests/visual/visual-targets.json` — provides the suggested route mappings per PNG (route, status, tolerance, wait_test_id).
