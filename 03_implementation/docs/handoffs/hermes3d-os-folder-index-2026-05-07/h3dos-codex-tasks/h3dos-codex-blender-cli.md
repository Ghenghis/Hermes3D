# h3dos-codex-blender-cli

## Target app
- **Name**: Blender (CLI / `--background` mode)
- **Role**: Modeler / mesh repair worker (used headless for repair, render previews, mesh analysis)
- **Upstream**: https://github.com/blender/blender.git
- **License**: GPL-3.0-or-later

## Source OS module
- **Registry entry**: `groups.modelers[].id == "blender"` in `apps/web/source_manifest.json` (line 127)
- **UX section**: `Modeling / Blender`
- **Manifest target path**: `modelers/Blender`
- **System command env**: `HERMES3D_BLENDER_PATH` (resolves to system `blender` if not set)

## Integration type
- **Method**: `clone-shallow` (reference repo) + system CLI probe — Blender itself is supplied by the host install; integration verifies via `blender --background --version`
- **Probe**: CLI smoke args `["--background", "--version"]` executed via `subprocess.run`
- **Process model**: ad-hoc subprocess invocation (no managed long-running process)
- **Symlink/shortcut**: `link_name: "blender"` placed in source-lab pointing to system command

## Status
- **DRAFT (local-only)** — branch `app/blender-cli` not pushed. HEAD `28d983c feat(app/blender-cli): install and launch smoke`. Stacked above prusaslicer/triposr but below fluidd/octoprint in the local linear chain.

## Branch & last commit
- **Branch**: `app/blender-cli`
- **HEAD**: `28d983c feat(app/blender-cli): install and launch smoke`
- **Working tree**: clean

## Files changed (vs `main`)
- 159 files, ~13,538 insertions / 116 deletions
- Notable additions:
  - `tests/e2e/app-blender-cli.spec.ts` (97 LOC)
  - `apps/api/hermes3d_api/source_install.py::_install_clone` (line 367) — handles `system_command` + `system_env` + `smoke_args`
  - Manifest entry with `clone-shallow` + smoke args (lines 135-142)

## Key files
| Role | Path |
|---|---|
| Verifier | `apps/api/hermes3d_api/source_install.py::_install_clone` (line 367) |
| Smoke probe | `source_install.py` line 165 (`subprocess.run(smoke_cmd, ..., timeout=60)`) |
| Registry / schema | `apps/web/source_manifest.json` line 127 |
| E2E test | `tests/e2e/app-blender-cli.spec.ts` |
| Env override | `HERMES3D_BLENDER_PATH` |

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
  <text class="small" x="170" y="154">_install_clone</text>
  <text class="small" x="170" y="166">subprocess.run</text>

  <rect class="y" x="240" y="120" width="100" height="50" rx="6"/>
  <text x="290" y="138">blender CLI</text>
  <text class="small" x="290" y="154">--background</text>
  <text class="small" x="290" y="166">--version</text>

  <rect class="p" x="360" y="40" width="120" height="50" rx="6"/>
  <text x="420" y="60">Action Window</text>
  <text class="small" x="420" y="76">Smoke probe</text>

  <rect class="p" x="360" y="200" width="120" height="50" rx="6"/>
  <text x="420" y="220">UI badge</text>
  <text class="small" x="420" y="236">version stdout</text>

  <line x1="100" y1="145" x2="120" y2="145" marker-end="url(#a)"/>
  <line x1="220" y1="145" x2="240" y2="145" marker-end="url(#a)"/>
  <path d="M340 135 L360 65" marker-end="url(#a)"/>
  <path d="M340 155 L360 225" marker-end="url(#a)"/>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
