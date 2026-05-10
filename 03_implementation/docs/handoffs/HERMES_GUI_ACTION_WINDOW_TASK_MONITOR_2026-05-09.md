# Hermes3D GUI — Action Window + Task Monitor (W6-4)

Date: 2026-05-09
Lane: W6-4 (lane 3 of the user's 5-lane GUI finish order)
Branch: `claude/w6-4-gui-action-window-task-monitor`
Lock owner: `claude-w6-4-action-window`

## Summary

W6-4 ships two reusable, independently mountable surfaces for the Hermes3D
Proof-Gated Agentic Workbench:

1. **Action Window** — resizable workbench panel with Code / Output / Diff
   tabs, pop-out into a dedicated browser tab, viewport-aware resize math,
   and localStorage size persistence.
2. **Task Monitor drawer** — slide-out from the right edge listing live
   recovery runs from `GET /api/code-operator/recovery/runs` (RC v2 read-only
   registry). Polls every 5 s with abort-on-unmount and exponential
   backoff on 5xx; rows expand to show the proof-event timeline; a UI-only
   "Clear completed" filter hides terminal runs.

Both components are wired through standalone mount components
(`ActionWindowMount`, `TaskMonitorMount`) so they can later be hosted from
the AppShell without touching `App.tsx` (which W6-3 owns during this wave).

## Files added

```
03_implementation/ui/src/api/recoveryRuns.ts                                 — RC v2 client + types
03_implementation/ui/src/components/ActionWindow/ActionWindow.tsx            — resizable panel
03_implementation/ui/src/components/ActionWindow/ActionWindow.test.tsx       — Vitest suite (20 tests)
03_implementation/ui/src/components/ActionWindow/ActionWindowMount.tsx       — toggle + floating host
03_implementation/ui/src/components/ActionWindow/DetachedActionWindow.tsx    — full-viewport pop-out host
03_implementation/ui/src/components/ActionWindow/useResizable.ts             — pure resize hook
03_implementation/ui/src/components/TaskMonitor/TaskMonitorDrawer.tsx        — drawer + timeline
03_implementation/ui/src/components/TaskMonitor/TaskMonitorDrawer.test.tsx   — Vitest suite (14 tests)
03_implementation/ui/src/components/TaskMonitor/TaskMonitorMount.tsx         — toggle + drawer host
03_implementation/ui/src/components/TaskMonitor/useRecoveryRunsPoll.ts       — polling hook
03_implementation/ui/src/action-window-detached.tsx                          — pop-out entry module
03_implementation/ui/src/test-setup-w6-4.ts                                  — Vitest setup (jest-dom + Node 25 localStorage shim)
03_implementation/ui/action-window.html                                      — pop-out HTML entry (Vite multi-page)
03_implementation/ui/tests/e2e/action-window-task-monitor.spec.ts            — Playwright spec (5 tests, 5 screenshots)
03_implementation/ui/vite.config.ts                                          — second entry + vitest config block
```

## Component API surface

### `<ActionWindow />`

```ts
interface ActionWindowProps {
  detached?: boolean;
  initialSize?: { width: number; height: number };
  detachUrl?: string;            // default "/action-window?detached=1"
  onClose?: () => void;
  codeContent?: string;
  output?: ActionWindowOutputEntry[];
  diff?: ActionWindowDiff | null;
  defaultTab?: "code" | "output" | "diff";
}
```

- Min 600×400, max viewport. Right + bottom + corner pointer-event handles.
- Pop-out opens `/action-window?detached=1` via `window.open(...,
  "hermes3d-action-window", "noopener,noreferrer")`.
- `data-testid="action-window-root"` exposed for Playwright; tabs:
  `action-window-tab-{code,output,diff}`; panels:
  `action-window-panel-{code,output,diff}`; handles:
  `action-window-handle-{right,bottom,corner}`.

### `<TaskMonitorDrawer />`

```ts
interface TaskMonitorDrawerProps {
  open: boolean;
  onClose: () => void;
  pollOptions?: {
    enabled?: boolean;
    intervalMs?: number;
    taskId?: string;
    fetchRunsImpl?: typeof fetchRecoveryRuns;
  };
  staticData?: RecoveryRunsResponse;  // bypasses polling, used by tests
}
```

- 420 px max-width drawer pinned to `right-0 top-0`. Slides via translate-x.
- State badges map to `created/proposing/reviewing/awaiting_human_confirm/
  applying/re_running_gate/recovered/retry_failed/escalated/cancelled`
  (verbatim from `RecoveryState` in `recovery_controller.py`).
- Click row → expands `task-monitor-timeline` with proof-event history
  sorted ascending by `ts_utc`.
- "Clear completed" toggle hides runs whose `state ∈ {recovered,
  retry_failed, escalated, cancelled}`. UI-only — never mutates server.

### Standalone mounts

- `<ActionWindowMount />` — floating toggle + panel; for AppShell wiring.
- `<TaskMonitorMount />` — toggle button + drawer; for AppShell wiring.
- `<DetachedActionWindow />` — full-viewport pop-out entry (`/action-window`).

When W6-3's lane lands and `App.tsx` opens up, integrators can drop both
mounts into `AppShell.tsx` next to `<TopBar />` and the new components light
up automatically.

## Resize math

Pure helpers in `useResizable.ts`:

- `clamp(value, min, max)` — `NaN` collapses to `min`.
- `computeNextSize(start, dx, dy, direction, limits)` — direction selects
  which deltas apply (`right` = width only, `bottom` = height only,
  `corner` = both).
- `capToViewport(size, limits)` — final clamp on every render and on
  `window.resize` so a smaller viewport never strands the panel oversized.
- `loadPersistedSize(key, fallback)` / `persistSize(key, size)` — JSON
  round-trip with graceful fallback for restricted/quota-exceeded storage.
  Pass `key = null` (detached mode) to disable persistence.

The hook itself uses **HTML5 Pointer Events**
(https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events). Each
handle sets pointer-capture on `pointerdown` so the drag survives leaving
the handle's bounding box. `pointermove` recomputes the size via
`computeNextSize`; `pointerup` / `pointercancel` releases capture and
unhooks listeners. Unmount cleanup forcibly releases capture if the
component dismounts mid-drag.

Defaults: `minWidth = 600`, `minHeight = 400`, viewport for max. Persisted
under `hermes3d:action-window:size`.

## Polling strategy

`useRecoveryRunsPoll` (default 5 s interval):

- Each cycle creates an `AbortController`. On unmount, the controller
  aborts the in-flight request — no setState-after-unmount warnings.
- Inspired by **TanStack Query**'s `refetchInterval`/`backoff`
  (https://tanstack.com/query/latest). Implemented inline so we don't
  pull TanStack into the bundle for one screen.
- `classifyError`: 4xx → `fatal` (surfaced to UI as `error`); 5xx, 0
  (network), and AbortError → `retry` (silent backoff).
- `nextBackoffMs(step, baseIntervalMs)`: doubles each step, capped at
  60 s (`MAX_BACKOFF_MS`). Successful poll resets `backoffStep` to 0.
- `enabled = false` (drawer closed) skips fetching entirely.
- API base URL list mirrors `adapters.live.ts`: `VITE_API_BASE` →
  `127.0.0.1:VITE_HERMES3D_BRIDGE_PORT` → `127.0.0.1:8765/8766/8767`.
  No URL is hardcoded inside the components.

## Image-GUI reference comparison

Pixel-target images in the repo:

- `Images-GUI/05-action-windows/action-window-core-apps.png`
- `Images-GUI/05-action-windows/action-window-advanced-tools.png`

Match notes:

- The reference Action Window is a workbench panel with a header, tab
  strip, and a primary content area. W6-4 follows that anatomy: header
  contains the size label + maximize + pop-out + close; tab strip below
  with three tabs; content fills remaining height with a monospace font.
- Resize handles are visually transparent (1.5–3 px wide hit zones) so
  they match the unobtrusive treatment in the reference. Hover shows a
  blue accent (`accent-blue/40`).
- Task Monitor uses the surface/border tokens already shipped by the
  AppShell theme (`bg-surface`, `border-border`, etc.) so it visually
  joins the existing dashboard. State badges reuse the
  green/amber/red/blue accent tones used elsewhere in the dashboard.

The Playwright suite lays down 5 PNG screenshots under
`03_implementation/ui/test-results/e2e/action-window-task-monitor/`:

```
01-action-window-detached.png
02-action-window-diff-tab.png
03-task-monitor-three-runs.png
04-task-monitor-expanded.png
05-task-monitor-filtered.png
```

These are runtime proofs (per the always-runtime-proof discipline). They
also serve as the diff baseline future visual-contract checks can compare
against the Images-GUI reference.

## Constraints honoured

- **No secrets in UI.** All endpoints derive from `VITE_API_BASE`
  /`VITE_HERMES3D_BRIDGE_PORT` env vars; the same fallback list as
  `adapters.live.ts`.
- **No mutations to other lanes' files.** `App.tsx`, `package.json`,
  `vitest.config.ts` are owned by W6-3 during this wave; we ship the
  W6-4 vitest config inside our owned `vite.config.ts` (using
  `defineConfig` + `/// <reference types="vitest" />`).
- **MCP file locks.** All new files locked under
  `claude-w6-4-action-window` before edit. Released at lane close.
- **2 sources cited for the design choices.** Pointer events docs +
  TanStack Query — both in the repo per the constraint.

## Known issues + follow-ups

1. **Pre-existing vite-dev `$RefreshSig$` bug.** Vite 8.0.10 +
   `@vitejs/plugin-react` 6.0.1 fail to inject the Fast Refresh preamble
   into served HTML in this repo. Existing E2E tests at HEAD also fail
   on the same root cause. The W6-4 spec works around it via
   `page.addInitScript` to define no-op `$RefreshReg$`/`$RefreshSig$`
   stubs. A repo-wide fix (e.g. pin vite to 5.x, or add
   `@vitejs/plugin-react/preamble` import to `index.html`) belongs in a
   follow-up PR — out of scope for W6-4 lane 3.
2. **No App.tsx integration in this PR.** Mount points exist
   (`ActionWindowMount`, `TaskMonitorMount`) but are not yet imported
   into `AppShell`. W6-3 owns `App.tsx` for this wave; integration
   lands when their lane merges, by adding the two mounts as siblings
   of `<TopBar />`.
3. **Task Monitor row click → /api/code-operator/recovery/runs/{id}.**
   Future deeper-detail panel can fetch the per-run state when RC v2
   commits 3-5 ship dedicated read-detail routes. For now, expansion
   uses the `history[]` already returned by the registry.

## Test results (commit-time)

- `npx vitest run --config vite.config.ts` — **34 / 34 passed**
  (20 ActionWindow + 14 TaskMonitorDrawer).
- `npx tsc --noEmit -p tsconfig.json` — **clean**.
- `npx vite build` — **success**, both `index.html` and
  `action-window.html` produced.
- `npx playwright test --config=playwright.e2e.config.ts
  tests/e2e/action-window-task-monitor.spec.ts` — **5 / 5 passed**,
  5 screenshots saved.
