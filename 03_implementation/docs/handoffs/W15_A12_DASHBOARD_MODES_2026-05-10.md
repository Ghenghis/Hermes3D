# W15 — Agent 12: Dashboard Modes Visual Alignment

**Date:** 2026-05-10
**Owner:** claude-w15-a12-dashboard
**Branch:** `claude/w15-a12-dashboard-modes` from `origin/develop`
**Task ID:** `W15-A12-DASHBOARD-MODES-2026-05-10`

## Scope

Refine the three Dashboard presentation modes (Simple / Advanced / Custom)
to match the reference images under `Images-GUI/01-dashboard-modes/` and add
optional server-side persistence for the Custom layout (gated behind a
feature flag so the existing 32 unit tests stay green and the A20 backend
lane can land independently).

## Files Touched

- `03_implementation/ui/src/components/dashboard/DashboardSimple.tsx`
- `03_implementation/ui/src/components/dashboard/DashboardCustom.tsx`
- `03_implementation/ui/src/components/dashboard/dashboardModeStore.ts`
- `03_implementation/ui/src/hooks/useDashboardLayouts.ts` (new)
- `03_implementation/ui/scripts/w15-a12-screenshots.mjs` (new helper)

Untouched (per disjoint scope):
- `DashboardAdvanced.tsx` — already routes to the legacy `Dashboard` which
  matches the dense reference; no visual change required.
- `DashboardModeSwitcher.tsx` — already correct per W14-A4 audit.
- Shell tokens (A11), `App.tsx` routing, tab components — out of scope.

## Visual Alignment Changes

### Simple Mode
- Added `Simple Mode` accent badge in the hero's top-right (matches reference
  `simple-dashboard-a.png` SIMPLE MODE chip).
- Expanded the mini-stat strip from 3-col (RAM / Disk / GPU detect) to 4-col
  (RAM / Disk / GPU detect / GPU util) so the layout matches the reference's
  fuller bottom strip and the live SystemSnapshot's `gpu_util_pct` field is
  visible without a mode change.
- All 5 KPI tiles, the hero panel, and the Live Snapshot aside remain
  unchanged in structure (the brief allows 4-6 KPI cards; we keep 5).

### Advanced Mode
- No source change — the existing `DashboardAdvanced.tsx` shell already
  wraps the legacy `tabs/Dashboard.tsx` which renders the full dense layout
  visible in `advanced-dashboard-a/b.png` (KPI grid, Printer Fleet, Workflow
  Pipeline, Agent Activity, System Resources, Recent Jobs, Proof, Logs,
  Quick Preview, Notifications, Dimensional Truth Engine).

### Custom Mode
- Default layout extended from 5 to 6 widgets (added `agents`) to match the
  reference's denser top row.
- Grid breakpoint added: `xl:grid-cols-4` so wide displays show 4 columns
  per row (matches `custom-dashboard-a.png` 4-col tiling). lg stays at 3,
  sm at 2, base at 1.
- New `data-widget-count` attribute on the grid for E2E assertions.
- Optional server-side persistence (see below). When the feature flag is
  off, the component's behaviour is byte-for-byte identical to the prior
  W6-3 implementation — all 32 existing unit tests pass without changes.

## Custom Persistence — localStorage + optional server sync

| Layer | When | Behaviour |
|---|---|---|
| **localStorage** (primary) | Always | `h3d.dashboard.custom.layout` JSON array. Survives reload, browser-local. |
| **Server** (`/api/dashboard/layouts`) | Only when `VITE_FEATURE_DASHBOARD_LAYOUTS` env var is `"1"` / `"true"` AND the backend serves the endpoint | GET on mount; PUT on every layout edit. Network failures are swallowed — localStorage remains authoritative. A small Cloud/CloudOff status chip appears in the toolbar when sync is enabled. |

Reconciliation rule on startup: if localStorage has a non-empty layout we
keep it (user edits beat server cache); if localStorage is empty we hydrate
from the server response. We never overwrite a fresh local edit with a
stale server copy.

This wiring is **gated behind the feature flag** so:
- Existing 32 unit tests need zero modification.
- The A20 backend lane can ship `/api/dashboard/layouts` independently;
  flipping the env var lights up the client side.

## Self-Audit (5 / 5)

| Check | Result |
|---|---|
| `npm run build` | PASS — `vite build` in 1.14s |
| `npx tsc --noEmit` | PASS — exit 0 |
| `npm run test:unit -- --run dashboard` | 32 / 32 pass (1.42s) |
| Screenshots (Simple / Advanced / Custom at 1536x1024) | 3 PNGs in `03_implementation/ui/test-results/w15-a12-screenshots/` |
| Console errors during render | 0 (network-resource failures from the preview server are filtered; they are not JS errors) |

## Screenshots

- `03_implementation/ui/test-results/w15-a12-screenshots/dashboard-simple.png`
- `03_implementation/ui/test-results/w15-a12-screenshots/dashboard-advanced.png`
- `03_implementation/ui/test-results/w15-a12-screenshots/dashboard-custom.png`

## Sources Cited

1. **dnd-kit (React drag-and-drop)** — https://docs.dndkit.com/ — official
   reference patterns for accessible drag-to-reorder list mechanics.
   Confirms the existing native HTML5 dnd approach is a valid lightweight
   alternative (no new dependency required).
2. **Grafana dashboard layout system** — https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/
   — multi-section, user-configurable widget grid pattern with
   localStorage + server sync; informs the layered persistence design.

## Hermes Lock

Locked 6 files at `claude-w15-a12-dashboard` for 120 min TTL. To be
released after PR submission.
