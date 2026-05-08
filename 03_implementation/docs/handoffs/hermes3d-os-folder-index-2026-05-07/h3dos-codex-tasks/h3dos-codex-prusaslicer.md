# h3dos-codex-prusaslicer

## Target app
- **Name**: PrusaSlicer
- **Role**: Slicer (FDM CLI slicer producing G-code from STL/3MF)
- **Upstream**: https://github.com/prusa3d/PrusaSlicer.git (binary release 2.9.4)
- **License**: AGPL-3.0

## Source OS module
- **Registry entry**: `groups.slicers[].id == "prusaslicer"` in `apps/web/source_manifest.json` (line 8 — first entry)
- **UX section**: `Slicer Bench / Prusa`
- **Manifest target path**: `slicers/PrusaSlicer`
- **Backend launch**: `prusaslicer` is one of two `launch_supported` apps (line 766, main.py: `{"prusaslicer", "octoprint"}`)

## Integration type
- **Method**: `binary-download` — fetches `PrusaSlicer-2.9.4.zip` from GitHub releases, extracts, locates `prusa-slicer.exe` / `prusa-slicer-console.exe`
- **Probe**: binary existence + invocation (`subprocess.run` of CLI executable)
- **Process model**: GUI launch (Source OS spawns the desktop binary), with managed PID tracking
- **Mock test layer**: PR `fd0daf4 test(app/prusaslicer): mock binary install launch flow` introduced a mocked binary fixture

## Status
- **DRAFT (local-only)** — branch `app/prusaslicer` not pushed. HEAD `a49df3c fix(app/prusaslicer): preserve TripoSR registry after rebase`. Sits at base of stack (above triposr only). Has 3 lane commits: feat / test (mock) / fix (rebase preservation).

## Branch & last commit
- **Branch**: `app/prusaslicer`
- **HEAD**: `a49df3c fix(app/prusaslicer): preserve TripoSR registry after rebase`
- **Working tree**: clean

## Files changed (vs `main`)
- 158 files, ~13,320 insertions / 116 deletions
- Notable additions:
  - `tests/e2e/app-prusaslicer.spec.ts` (98 LOC)
  - `apps/api/hermes3d_api/source_install.py::_install_binary_download` (line 467) — uses `urllib.request` + `zipfile`
  - `source-lab/source_manifest.json` (596 LOC) — full source-lab manifest
  - Manifest entry lines 8-22 (binary-download install block)

## Key files
| Role | Path |
|---|---|
| Verifier | `apps/api/hermes3d_api/source_install.py::_install_binary_download` (line 467) |
| Subprocess probe | `source_install.py` lines 304, 344 (binary smoke checks) |
| Launcher | `apps/api/hermes3d_api/main.py` PrusaSlicer launch path (line 766+) |
| Registry / schema | `apps/web/source_manifest.json` line 8, `source-lab/source_manifest.json` |
| E2E test | `tests/e2e/app-prusaslicer.spec.ts` |

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
  <text class="small" x="170" y="154">_install_binary</text>
  <text class="small" x="170" y="166">urllib + zipfile</text>

  <rect class="y" x="240" y="120" width="100" height="50" rx="6"/>
  <text x="290" y="138">PrusaSlicer</text>
  <text class="small" x="290" y="154">prusa-slicer.exe</text>
  <text class="small" x="290" y="166">CLI / GUI</text>

  <rect class="p" x="360" y="40" width="120" height="50" rx="6"/>
  <text x="420" y="60">Action Window</text>
  <text class="small" x="420" y="76">Install/Launch</text>

  <rect class="p" x="360" y="200" width="120" height="50" rx="6"/>
  <text x="420" y="220">UI badge</text>
  <text class="small" x="420" y="236">launch_supported</text>

  <line x1="100" y1="145" x2="120" y2="145" marker-end="url(#a)"/>
  <line x1="220" y1="145" x2="240" y2="145" marker-end="url(#a)"/>
  <path d="M340 135 L360 65" marker-end="url(#a)"/>
  <path d="M340 155 L360 225" marker-end="url(#a)"/>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
