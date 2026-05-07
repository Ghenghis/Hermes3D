# h3d-enh-screenshots

- **Type**: ENHANCEMENT (DOCS / dev-tooling)
- **Status**: OPEN — work-in-progress, no PR opened yet
- **Branch**: `docs/launcher-screenshots`
- **Last commit on branch tip**: `3fde207 docs(release): draft v5.3.0 release notes` (branch was forked here, no new commits yet)
- **PR link**: none
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Add a deterministic, locally-runnable Playwright capture script that produces 22 reference screenshots of the Hermes3D-OS Lite Gradio launcher, plus a `site/screenshots/` README documenting the capture procedure. The README index in the repo is updated to reference the new directory.

## Files changed

Working tree (uncommitted) on top of the develop tip:

| File | + / - | Status |
| --- | --- | --- |
| `README.md` | +1 / -0 | modified — adds `site/screenshots/` to the directory legend |
| `site/screenshots/capture.py` | new | untracked — Playwright driver capturing 22 PNGs against `127.0.0.1:7860` |
| `site/screenshots/README.md` | new | untracked — capture procedure, prerequisites, why-not-CI rationale |

Total: 1 modified, 2 untracked. No PR yet.

## Notes

- Capture script keys selectors on Gradio `elem_id` values declared in `hermes3d/app/launcher.py`, so the launcher and the script must move in lock-step.
- Screenshots are intentionally produced from a developer machine (not CI) because the launcher pulls in Blender / ComfyUI / Velopack side-effects that are brittle on GitHub-hosted runners.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-enh-screenshots change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .new { fill: #065f46; stroke: #10b981; }
    .mod { fill: #78350f; stroke: #f59e0b; }
    .label { fill: #f9fafb; font: 600 12px sans-serif; }
    .sub { fill: #d1d5db; font: 11px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
  </style>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">docs/launcher-screenshots — file footprint</text>

  <rect class="box mod" x="20" y="50" width="180" height="60" rx="6"/>
  <text class="label" x="30" y="72">README.md</text>
  <text class="sub"   x="30" y="90">+1 / -0 line</text>
  <text class="sub"   x="30" y="104">(directory legend)</text>

  <rect class="box new" x="250" y="50" width="180" height="60" rx="6"/>
  <text class="label" x="260" y="72">site/screenshots/capture.py</text>
  <text class="sub"   x="260" y="90">new — Playwright driver</text>
  <text class="sub"   x="260" y="104">22 PNG capture script</text>

  <rect class="box new" x="250" y="130" width="180" height="60" rx="6"/>
  <text class="label" x="260" y="152">site/screenshots/README.md</text>
  <text class="sub"   x="260" y="170">new — capture procedure</text>
  <text class="sub"   x="260" y="184">prerequisites + why-not-CI</text>

  <rect class="box" x="20" y="130" width="180" height="60" rx="6"/>
  <text class="label" x="30" y="152">launcher.py (unchanged)</text>
  <text class="sub"   x="30" y="170">elem_id contract source</text>
  <text class="sub"   x="30" y="184">selectors keyed off this</text>

  <text class="sub" x="225" y="225" text-anchor="middle" fill="#9ca3af">orange = modified · green = new · gray = referenced only</text>
</svg>
```
