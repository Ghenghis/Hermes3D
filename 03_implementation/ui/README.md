# Hermes3D-OS — UI-Final

Faithful React + Tailwind recreation of [`06_release/UI_FINAL_VISUAL_CONTRACT.png`](../../06_release/UI_FINAL_VISUAL_CONTRACT.png).

**Current status:** the React shell is wired to the local Hermes3D GUI API. Empty states mean the backend returned no rows or the corresponding bridge is unavailable.

## USER strict runtime rules

- Production UI never imports mock data and never renders invented
  printer telemetry, slicer state, generated models, proof bundles,
  notifications, agent activity, setup state, or remote-host state.
- Buttons either call a real backend endpoint or are disabled with a
  specific reason such as missing setup, unavailable bridge, or printer
  safety lock.
- Hermes Agents are user-authorized operator/admin delegates. They may
  use Hermes3D-OS, the user's PC, local files, installed apps, web
  services/accounts, VPS or remote hosts, source repositories, GitHub
  branches, commits, pushes, and PRs when the user assigns that work.
- Missing source paths, repository URLs, credentials, model files,
  remote hosts, material choices, or printer/user preferences must be
  requested from the user or shown as blocked. They must not be guessed.
- FLSUN S1 at `192.168.0.12` is offline/locked/no-test for now. Status
  metadata can be edited, but movement, upload, capture, and test
  actions remain blocked until the user clears the lock.

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
├── tabs/                 16 routed tab components
├── api/                  live/local backend adapter interface
└── types/                TypeScript mirror of hermes3d.adapters.types
```

## Constraints

Per [`feedback_no_ui_design.md`](https://github.com/Ghenghis/Hermes3D/blob/develop/00_overview/PHASE0_BASELINE_REPORT.md):
- **No design freedom.** Every component sourced from the visual contract or kit specs.
- **No invented UI data.** Production tabs must use the local GUI API or render a truthful empty/unavailable state.
- **Printer command writes go through the backend.** The frontend must call
  Hermes3D API routes that enforce dry-run/confirmation gates and printer
  locks; it must not bypass them from browser code.
- **Gradio launcher untouched.** This UI is additive; the legacy Gradio app at `03_implementation/src/hermes3d/app/launcher.py` stays as stabilization scaffolding.

### Runtime safety boundary

The browser UI and Playwright visual gate do not launch external
applications directly. Hermes Agents may use external apps, web
services, source checkouts, VPS/remote hosts, and local PC tools through
Hermes3D backend adapters and user-authorized automation flows.

- **No** `child_process` / `spawn` / `exec` / `execSync` / `execFile` from any UI module.
- **No** Electron-style `shell.openPath` / `shell.openExternal` from browser UI code.
- **No** `<a href="file://…">`, `download` attributes, or `target="_blank"` to OS-handled file extensions.
- **No** `Start-Process` / `os.startfile` / `cmd /c start` from any test or build script.
- Slicer UIs (FLSUN Slicer, PrusaSlicer, OrcaSlicer, Cura), printer hosts (Moonraker, OctoPrint, Printrun, Klipper), and Blender must be surfaced through source-backed modules or explicit unavailable states.

External launches and remote setup belong in `03_implementation/src/hermes3d/adapters/*`
or explicit agent automation code, with proof events and safety gates.

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
