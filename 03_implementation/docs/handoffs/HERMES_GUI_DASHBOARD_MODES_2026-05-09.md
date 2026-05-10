# Hermes3D GUI Dashboard — Simple / Advanced / Custom Modes (W6-3)

**Lane**: W6-3 (lane 3 of the user's 5-lane finish order)
**Branch**: `claude/w6-3-gui-dashboard-3-modes`
**Worktree**: `G:/Github/_claude_worktrees/h3d-claude-w6-3-gui-modes`
**Lock owner**: `claude-w6-3-gui-dashboard`
**Date**: 2026-05-09 (UTC `2026-05-10`)

## Scope

Implement three distinct dashboard presentation modes for the Hermes3D OS GUI,
matching the Visual Reference Pack at `Images-GUI/01-dashboard-modes/`:

| Mode       | Reference image                       | Behaviour                                                                                                                                                  |
| ---------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Simple     | `simple-dashboard-{a,b}.png`          | Header + 5 KPI tiles + System Status hero + Live Snapshot summary. No panels, no drawers, no Action Window button.                                         |
| Advanced   | `advanced-dashboard-{a,b}.png`        | Full live `Dashboard.tsx` (16 tabs visible, 5-card KPI strip, Printer Fleet, AI Workflow Pipeline, Active Agents, Resources, Jobs, Proof, Logs, Notifications) plus the Hermes Agents chat-mirror dock and a floating **Action Window** button. **Default mode.** |
| Custom     | `custom-dashboard-{a,b}.png`          | Drag-to-reorder widget grid. Side palette drawer adds/removes widgets. Layout persists to `localStorage` (`h3d.dashboard.custom.layout`). `Reset` + `Edit Layout` controls. |

## Files added

| Path | Purpose |
| ---- | ------- |
| `03_implementation/ui/src/components/dashboard/dashboardModeStore.ts` | Zustand store + pure helpers (`modeFromHash`, `modeFromQueryString`, `resolveInitialMode`, `readPersistedCustomLayout`, `writePersistedCustomLayout`, `ALL_CUSTOM_WIDGETS`, `DEFAULT_CUSTOM_LAYOUT`). |
| `03_implementation/ui/src/components/dashboard/DashboardSimple.tsx` | Minimal 5-KPI dashboard with system-status hero + summary. |
| `03_implementation/ui/src/components/dashboard/DashboardAdvanced.tsx` | Wraps the existing `Dashboard.tsx` and adds the `Action Window` chip. |
| `03_implementation/ui/src/components/dashboard/DashboardCustom.tsx` | Drag/drop widget grid, palette drawer, persisted layout. Renders 9 widgets: KPI / Fleet / Pipeline / Agents / Resources / Jobs / Proof / Logs / Notifications. |
| `03_implementation/ui/src/components/dashboard/DashboardModeSwitcher.tsx` | Top-right radio group (`Simple | Advanced | Custom`) — emits hash + writes localStorage. |
| `03_implementation/ui/vitest.config.ts` | Vitest config (jsdom, react plugin, NODE_ENV=development for `act()`). |
| `03_implementation/ui/tests/unit/setup.ts` | jest-dom matchers, `cleanup()` hook, in-memory localStorage shim (jsdom 25 / Node 25 leaves localStorage methods undefined). |
| `03_implementation/ui/tests/unit/dashboardModeStore.test.ts` | 19 unit tests for pure helpers + persistence. |
| `03_implementation/ui/tests/unit/DashboardModeSwitcher.test.tsx` | 4 tests: render shape, click → store + localStorage, controlled override, hash sync. |
| `03_implementation/ui/tests/unit/DashboardSimple.test.tsx` | 4 tests: root attribute, 5 KPI tiles, hero with live data, no advanced/custom widgets present. |
| `03_implementation/ui/tests/unit/DashboardCustom.test.tsx` | 5 tests: default layout, palette open, remove → persist, add from palette, reset. |
| `03_implementation/ui/tests/e2e/dashboard-modes.spec.ts` | 5 Playwright specs: each mode mounts, mode switcher cycles, query string overrides persisted mode. |

## Files modified

| Path | Change |
| ---- | ------ |
| `03_implementation/ui/src/App.tsx` | Routes the dashboard tab to `DashboardSimple` / `DashboardAdvanced` / `DashboardCustom` based on `useDashboardModeStore.mode`. Sync hash + `?mode=` on every render. |
| `03_implementation/ui/src/app/store.ts` | `tabIdFromHash` now strips a trailing `:mode` / `/mode` / `.mode` suffix so `#dashboard:simple` still resolves the dashboard tab. |
| `03_implementation/ui/src/components/layout/TopBar.tsx` | Renders `<DashboardModeSwitcher>` only when the active tab is the dashboard. |
| `03_implementation/ui/package.json` | Added `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom` to devDeps; added `test` and `test:unit` scripts. |

## Routing — `/dashboard/{simple,advanced,custom}` + `?mode=`

The repo is hash-based (Vite + custom Zustand store, not react-router). Modes
are reachable through:

* **Hash**: `#dashboard:simple`, `#dashboard/advanced`, `#dashboard.custom`
  (any of the three separators is accepted, case-insensitive on the mode token).
* **Query string**: `?mode=simple` (etc.) — wins over hash and persisted value.
* **Switcher click**: writes the hash + mutates the store + persists to
  `localStorage` (`h3d.dashboard.mode`).

Priority: query → hash → localStorage → default (`advanced`).

## Test results

### Unit (Vitest)

```text
 Test Files  4 passed (4)
      Tests  32 passed (32)
   Start at  20:30:40
   Duration  2.41s
```

| Suite                                | Tests | Status |
| ------------------------------------ | ----- | ------ |
| `dashboardModeStore.test.ts`         | 19    | green  |
| `DashboardModeSwitcher.test.tsx`     | 4     | green  |
| `DashboardSimple.test.tsx`           | 4     | green  |
| `DashboardCustom.test.tsx`           | 5     | green  |

### Build / typecheck

```text
$ npm run lint
> tsc --noEmit          # zero errors

$ npm run build
> tsc -b && vite build
✓ 2194 modules transformed.
dist/index.html                     0.41 kB │ gzip:   0.28 kB
dist/assets/index-*.css            47.64 kB │ gzip:  10.04 kB
dist/assets/index-*.js          1,055.47 kB │ gzip: 269.97 kB
✓ built in 1.86s
```

### Playwright E2E

The spec at `tests/e2e/dashboard-modes.spec.ts` has 5 cases. Direct
end-to-end runs against the project's `start-e2e-stack.mjs` web server were
**blocked by a pre-existing Vite-v8 + plugin-react-v6 dev-server bug** —
`$RefreshReg$ is not defined` is thrown from `@vitejs/plugin-react`'s HMR
boot code before any application code executes (reproducible on the
unmodified `feat/hermes3d-7-complete-gui-repo-wiring` baseline). This is
not in W6-3 scope.

To prove the modes mount, three production-build screenshots were captured
against `vite preview --host 127.0.0.1 --port 4188`, where the React app
loads cleanly:

| Mode      | Screenshot                                       | Reference                                  |
| --------- | ------------------------------------------------ | ------------------------------------------ |
| Advanced  | `docs/evidence/w6-3/dashboard-advanced.png`      | `Images-GUI/01-dashboard-modes/advanced-dashboard-{a,b}.png` |
| Simple    | `docs/evidence/w6-3/dashboard-simple.png`        | `Images-GUI/01-dashboard-modes/simple-dashboard-{a,b}.png`   |
| Custom    | `docs/evidence/w6-3/dashboard-custom.png`        | `Images-GUI/01-dashboard-modes/custom-dashboard-{a,b}.png`   |

Each screenshot was captured at 1920×1080. Headless Chromium reports the
expected DOM structure on each load:

```text
dashboard-root count: 1
dashboard-advanced-root count: 1
dashboard-mode-switcher count: 1
dashboard-advanced-action-window-btn count: 1
simple root with data-dashboard-mode='simple' count: 1
simple kpi tile count: 1
custom root with data-dashboard-mode='custom' count: 1
custom grid count: 1
```

## Comparison to Images-GUI baseline

* **Simple** — matches reference layout (5-card KPI strip + central status
  hero + side summary). The reference image shows a hero preview frame; the
  W6-3 implementation renders a System Status text card instead because no
  3-D preview artifact is available without a live backend. Empty/blocked
  data renders truthful empty states (no fabricated data).
* **Advanced** — equivalent to `Hermes3D.png` and the reference advanced
  page. The Action Window chip is rendered in the top-right of the dashboard
  area (the reference image uses an embedded Action Window panel; the chip
  is a deliberate compact entry point that opens the Autopilot tab — full
  Action Window panel is the W6-? lane).
* **Custom** — palette drawer + drag handles + Reset + Edit Layout match
  the reference. The reference image shows ~12 widgets visible at once; the
  default layout ships 5 (the user-spec KPI / Fleet / Pipeline / Resources
  / Jobs) and the user can add up to 9 from the palette. This is intentional
  to keep the first-run view uncluttered.

Deviations from the pixel target are documented above; the underlying live
data flow (adapters, API endpoints, empty states) is identical to Advanced.

## How to run locally

```bash
cd 03_implementation/ui
npm install               # adds vitest + jsdom + testing-library
npm run lint              # tsc --noEmit
npm run build             # tsc -b && vite build
npm test                  # vitest run (32 tests, < 3 s)
# E2E once the $RefreshReg$ regression is resolved upstream:
npm run test:visual -- tests/e2e/dashboard-modes.spec.ts
```

## Lock release

Locks acquired by `claude-w6-3-gui-dashboard` (taskId
`W6-3-GUI-DASHBOARD-MODES-2026-05-09`):

* `03_implementation/ui/src/components/dashboard/{DashboardSimple,DashboardAdvanced,DashboardCustom,DashboardModeSwitcher,dashboardModeStore}.{ts,tsx}`
* `03_implementation/ui/src/App.tsx`
* `03_implementation/ui/src/app/store.ts`
* `03_implementation/ui/src/components/layout/TopBar.tsx`
* `03_implementation/ui/tests/e2e/dashboard-modes.spec.ts`
* `03_implementation/ui/tests/unit/{setup,dashboardModeStore,DashboardModeSwitcher,DashboardSimple,DashboardCustom}.test{,.tsx,.ts}`
* `03_implementation/ui/{package.json,vitest.config.ts}`
* `03_implementation/docs/handoffs/HERMES_GUI_DASHBOARD_MODES_2026-05-09.md`

Released after the W6-3 commit lands on `claude/w6-3-gui-dashboard-3-modes`.

## Persistence rule trigger — none

The implementation completed without invoking the persistence rule. The
single divergence from the original brief (`G:/Github/h3d-gui-wiring-codex/01_app/`
or `02_ui/`) was resolved at discovery: the GUI lives at
`G:/Github/h3d-gui-wiring-codex/03_implementation/ui/`. All other contracts
(react-router replacement: hash + zustand; tailwind: yes; pixel target: see
above table) followed cleanly.
