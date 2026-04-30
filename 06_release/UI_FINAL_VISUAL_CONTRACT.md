# UI-Final Visual Contract

The authoritative visual spec for the UI-Final dashboard lives at:

```
06_release/UI_FINAL_VISUAL_CONTRACT.png
```

This is the screenshot the project owner committed as the lockdown spec for the React + Tailwind dashboard rebuild (see [`02_architecture/adr/ADR-ui-final-dashboard.md`](../02_architecture/adr/ADR-ui-final-dashboard.md) and [`01_requirements/ui_final_dashboard_scope.md`](../01_requirements/ui_final_dashboard_scope.md)).

## Status

**File pending drop** — the .png file needs to be saved at the path above before the parallel UI-Final work begins. The image was attached in the conversation that approved this branch on 2026-04-30 but cannot be saved automatically by the agent. Drop it manually:

```bash
# From the repo root, with the screenshot file at hand:
cp /path/to/screenshot.png 06_release/UI_FINAL_VISUAL_CONTRACT.png
git add 06_release/UI_FINAL_VISUAL_CONTRACT.png
git commit -m "feat(ui-final): commit visual contract screenshot"
git push
```

## Rules

1. The image at `UI_FINAL_VISUAL_CONTRACT.png` is **authoritative**. The Playwright capture for UI-Final must visually match it.
2. Any change to the visual spec replaces this file with rationale in the commit message — no silent edits.
3. Do not delete or move this file; downstream tests reference its path directly.
