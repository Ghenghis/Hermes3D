# UI-Final Screenshot Gate

## Required specs
- `dashboard.visual.spec.ts`
- `tabs.render.spec.ts`
- `dock-undock.spec.ts`
- `settings.registry.spec.ts`
- `dangerous-actions.spec.ts`

## Visual assertions
- Dashboard matches `06_release/UI_FINAL_VISUAL_CONTRACT.png` closely.
- Shared shell unchanged across tabs.
- No white-heavy panels.
- No overflow clipping at desktop size.

## Console policy
Fail on:
- console.error
- uncaught exception
- failed network request except mocked endpoints explicitly allowed
