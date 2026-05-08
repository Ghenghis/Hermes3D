# h3dos-codex-fluidd

## Target app
- **Name**: Fluidd
- **Role**: Printer host UI (Klipper / Moonraker dashboard, single-page Vue app)
- **Upstream**: https://github.com/fluidd-core/fluidd.git
- **License**: GPL-3.0

## Source OS module
- **Registry entry**: `groups.printer_farm[].id == "fluidd"` in `apps/web/source_manifest.json` (line 277)
- **UX section**: `Printer Farm / Device UI`
- **Manifest target path**: `print-farm/Fluidd`
- **Static URL**: `/static/fluidd/` (served from build output `dist/`)

## Integration type
- **Method**: `npm-build` — clone repo, run `npm ci --include=dev` then `npm run build`, mount `dist/` as static
- **Probe**: build artifact existence (no HTTP probe; SPA is static)
- **Process model**: static-mounted assets (no managed subprocess); requires Moonraker upstream

## Status
- **DRAFT (local-only)** — branch `app/fluidd` is local-only (not on origin). HEAD `11ee525 feat(app/fluidd): install + launcher + Action Window + e2e`. Sits below `app/octoprint` in the local linear stack; commit history shows this lane's PR was already merged into the prior chain (`376597c Merge pull request #25 from Ghenghis/app/fluidd`) but has not been pushed to GitHub origin.

## Branch & last commit
- **Branch**: `app/fluidd`
- **HEAD**: `11ee525 feat(app/fluidd): install + launcher + Action Window + e2e`
- **Working tree**: clean

## Files changed (vs `main`)
- 160 files, ~13,815 insertions / 116 deletions
- Notable additions:
  - `tests/e2e/app-fluidd.spec.ts` (107 LOC)
  - `apps/api/hermes3d_api/source_install.py` `_install_npm_build` (line 521)
  - `apps/web/source_manifest.json` Fluidd entry with `npm-build` install block (lines 285-291)
  - Carries the previously merged prusaslicer + blender-cli + triposr stack

## Key files
| Role | Path |
|---|---|
| Verifier (build) | `apps/api/hermes3d_api/source_install.py::_install_npm_build` (line 521) |
| Subprocess invocation | `source_install.py` line 509 (`subprocess.run` for `npm ci`/`npm run build`) |
| Registry / schema | `apps/web/source_manifest.json` line 277 |
| E2E test | `tests/e2e/app-fluidd.spec.ts` |
| Static mount | `static_url: /static/fluidd/` in manifest install block |

## Integration path diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0e1117"/>
  <style>
    .b{fill:#1f6feb;stroke:#58a6ff;stroke-width:1.5}
    .g{fill:#238636;stroke:#3fb950;stroke-width:1.5}
    .y{fill:#9e6a03;stroke:#d29922;stroke-width:1.5}
    .p{fill:#6e40c9;stroke:#a371f7;stroke-width:1.5}
    text{fill:#f0f6fc;font-family:Segoe UI,sans-serif;font-size:11px;text-anchor:middle}
    .small{font-size:9px;fill:#8b949e}
    line,path{stroke:#58a6ff;stroke-width:1.5;fill:none}
  </style>
  <rect class="b" x="10" y="120" width="90" height="50" rx="6"/>
  <text x="55" y="142">H3D backend</text>
  <text class="small" x="55" y="158">FastAPI</text>

  <rect class="g" x="120" y="120" width="100" height="50" rx="6"/>
  <text x="170" y="138">source_install</text>
  <text class="small" x="170" y="154">_install_npm_build</text>
  <text class="small" x="170" y="166">npm ci/build</text>

  <rect class="y" x="240" y="120" width="100" height="50" rx="6"/>
  <text x="290" y="138">Fluidd</text>
  <text class="small" x="290" y="154">dist/ static</text>
  <text class="small" x="290" y="166">/static/fluidd/</text>

  <rect class="p" x="360" y="40" width="120" height="50" rx="6"/>
  <text x="420" y="60">Action Window</text>
  <text class="small" x="420" y="76">Install/Open</text>

  <rect class="p" x="360" y="200" width="120" height="50" rx="6"/>
  <text x="420" y="220">UI badge</text>
  <text class="small" x="420" y="236">build_output ok</text>

  <line x1="100" y1="145" x2="120" y2="145" marker-end="url(#a)"/>
  <line x1="220" y1="145" x2="240" y2="145" marker-end="url(#a)"/>
  <path d="M340 135 L360 65" marker-end="url(#a)"/>
  <path d="M340 155 L360 225" marker-end="url(#a)"/>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
