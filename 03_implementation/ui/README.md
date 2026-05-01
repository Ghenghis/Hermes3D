# Hermes3D-OS — UI-Final

Faithful React + Tailwind recreation of [`06_release/UI_FINAL_VISUAL_CONTRACT.png`](../../06_release/UI_FINAL_VISUAL_CONTRACT.png).

**Phase 2 status:** scaffolding (bootstrap + design tokens). Tabs, mock data layer, and Playwright screenshot gate land in subsequent tasks per [`00_overview/PHASE2_PLAN.md`](../../00_overview/PHASE2_PLAN.md).

## Quick start

```bash
cd 03_implementation/ui
npm install --include=dev      # NB: NODE_ENV=production in your shell suppresses devDeps; use --include=dev
npm run dev                    # Vite dev server at http://localhost:5173
npm run build                  # tsc -b + vite build → dist/
npm run preview                # serve dist/ at http://localhost:4173
npm run lint                   # tsc --noEmit
npm run test:visual            # playwright test (1 dashboard + 8 dock state)
npm run test:visual:update     # refresh visual baseline after intentional design change
```

CI uses `npm ci` (deterministic from `package-lock.json`) — keep the lockfile committed and stable. The lockfile is regenerated whenever `npm install --include=dev` is run with new dependencies.

## Layout (per [`hermes3d_gui_contract_kit_v4.1/03_implementation/ui/REACT_STRUCTURE.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/ui/REACT_STRUCTURE.md))

```
src/
├── main.tsx              entrypoint
├── App.tsx               root component
├── styles/
│   ├── globals.css       Tailwind directives + base body styles
│   └── tokens.ts         token constants for raw-value consumers
├── app/                  AppShell, routes, zustand store    [Task 6+]
├── components/           shared primitives (Card, Panel, etc.) [Task 9-12]
├── tabs/                 13 tab components                  [Task 19-38]
├── data/mock/            mock data layer                    [Task 13-18]
├── api/                  adapter interface (mock-only)      [Task 18]
└── types/                TypeScript mirror of hermes3d.adapters.types
```

## Constraints

Per [`feedback_no_ui_design.md`](https://github.com/Ghenghis/Hermes3D/blob/develop/00_overview/PHASE0_BASELINE_REPORT.md):
- **No design freedom.** Every component sourced from the visual contract or kit specs.
- **No real adapter calls.** Mock data only; the swap point for Phase 3 is `src/api/adapters.ts`.
- **No printer command writes.** Phase 6 implements those behind the dry-run-token + Confirmation gate.
- **Gradio launcher untouched.** This UI is additive; the legacy Gradio app at `03_implementation/src/hermes3d/app/launcher.py` stays as stabilization scaffolding.

### Phase 2 safety boundary — no external app launches

The Dashboard, all panels, and the Playwright visual gate are forbidden from launching external applications during Phase 2:

- **No** `child_process` / `spawn` / `exec` / `execSync` / `execFile` from any UI module.
- **No** Electron-style `shell.openPath` / `shell.openExternal` (this is a pure web app — no Electron in Phase 2).
- **No** `<a href="file://…">`, `download` attributes, or `target="_blank"` to OS-handled file extensions.
- **No** `Start-Process` / `os.startfile` / `cmd /c start` from any test or build script.
- Slicer UIs (FLSUN Slicer, PrusaSlicer, OrcaSlicer, Cura), printer hosts (Moonraker, OctoPrint, Printrun, Klipper), and Blender are referenced **as strings only** — adapter unions, mock-data filenames, agent provider tags, log messages. They render as plain text in the DOM; the OS never sees them as a launch instruction.

The actual launch code lives in `03_implementation/src/hermes3d/adapters/*` (Phase 1 skeletons) and is gated by Phase 6's dry-run-token + Confirmation flow. Phase 2 does not touch that path.

If OrcaSlicer (or any slicer / printer host) opens during Phase 2 work, it is **not** caused by this UI or the visual test — investigate manual user action, OS file association, or the slicer's own auto-updater.

## Stack

| Tool | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI |
| TypeScript | 5.6.2 | strict mode |
| Vite | 5.4.8 | bundler + dev server |
| Tailwind CSS | 3.4.13 | styling, design tokens |
| lucide-react | 0.451.0 | icons (sidebar, panels, controls) |
| recharts | 2.13.0 | sparklines + resource gauges |
| zustand | 5.0.0 | active tab + per-panel dock + collapse state |
| @playwright/test | 1.48.0 | UI E2E + visual gate |

## CI — Layer D2 (UI-Final truth gate)

Workflow: [`.github/workflows/ui-ci.yml`](../../.github/workflows/ui-ci.yml).

Steps (Linux, Node 24, `working-directory: 03_implementation/ui`):

1. `actions/checkout@v4`
2. `actions/setup-node@v4` with `cache: "npm"` keyed on `package-lock.json`
3. `npm ci`                            — deterministic install from lockfile
4. `npm run lint`                      — `tsc --noEmit` (strict)
5. `npm run build`                     — `tsc -b && vite build`
6. `npx playwright install --with-deps chromium`
7. `npx playwright test`               — boots `npm run dev` automatically via `playwright.config.ts` `webServer`

Artifact uploads:
- **On failure:** `playwright-report/`, `test-results/`, `artifacts/` (14-day retention).
- **Always:** `artifacts/dashboard-current-1920x1080.png` (so reviewers can eyeball the rendered Dashboard even when the strict diff is platform-skipped).

### Visual baseline scoping

The Dashboard visual baseline is committed only for **chromium-win32**:
- [`tests/visual/dashboard.visual.spec.ts-snapshots/dashboard-1920x1080-chromium-1920x1080-win32.png`](tests/visual/dashboard.visual.spec.ts-snapshots/dashboard-1920x1080-chromium-1920x1080-win32.png)

Sub-pixel font rendering and antialiasing diverge across OSes, so a single baseline cannot strict-diff cleanly on every platform. On non-win32 (Linux CI runners), `dashboard.visual.spec.ts` exports the artifact PNG and then calls `test.skip(process.platform !== "win32")`, so the strict diff does not fire. The dock state-machine tests (8 of 9 specs, including the source-pattern audit) are platform-agnostic and run everywhere.

When a Linux CI lane needs to gate on visuals, regenerate the snapshot once on Linux with `npx playwright test --update-snapshots` and commit `…-linux.png` next to the existing `…-win32.png`.
