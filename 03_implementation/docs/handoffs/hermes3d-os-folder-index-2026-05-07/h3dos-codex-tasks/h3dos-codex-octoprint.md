# h3dos-codex-octoprint

## Target app
- **Name**: OctoPrint
- **Role**: Printer host / web UI for FDM printers (legacy plugin ecosystem)
- **Upstream**: https://github.com/OctoPrint/OctoPrint.git
- **License**: AGPL-3.0

## Source OS module
- **Registry entry**: `groups.printer_farm[].id == "octoprint"` in `apps/web/source_manifest.json` (also mirrored in `source-lab/source_manifest.json`)
- **UX section**: `Printer Farm / Plugin Bridge`
- **Manifest target path**: `print-farm/OctoPrint`
- **Backend tool key**: `octoprint` (referenced in `apps/api/hermes3d_api/main.py`)

## Integration type
- **Method**: `pip` (install) + managed subprocess (launch)
- **Probe**: pip module import probe (`import_name: "octoprint"`) + HTTP probe at `http://127.0.0.1:5000`
- **Process model**: `managed-process` — Source OS spawns `.venv\Scripts\octoprint.exe` and tracks PID in `process_state`
- **Smoke API key**: `OCTOPRINT_SMOKE_API_KEY = "hermes3d-octoprint-smoke-key"` (line 88, main.py)

## Status
- **DRAFT (local-only)** — branch `app/octoprint` exists locally but is not pushed to `origin`. Latest tip commit is `737dd40 feat(app/octoprint): install + launcher + Action Window + e2e`. The branch chains on top of merged PRs #22 fluidd / #23 blender / #24 prusaslicer / #25 — all five lanes are stacked linearly in this worktree.

## Branch & last commit
- **Branch**: `app/octoprint`
- **HEAD**: `737dd40 feat(app/octoprint): install + launcher + Action Window + e2e`
- **Working tree**: clean

## Files changed (vs `main`)
- 162 files, ~14,323 insertions / 116 deletions (largest of the five lanes; carries the full stack of prior lanes)
- Notable additions:
  - `apps/api/hermes3d_api/source_install.py` (636 LOC) — generic install dispatcher
  - `apps/api/hermes3d_api/main.py` — `_launch_octoprint`, `/api/source-apps/octoprint/{install,launch,stop,process-state}` routes
  - `apps/api/hermes3d_api/process_state.py` (107 LOC) — managed-process tracker
  - `apps/web/source_manifest.json` (611 LOC), `apps/web/source-os.js` (804 LOC), `apps/web/action-window.js` (141 LOC)
  - `tests/e2e/app-octoprint.spec.ts` (125 LOC)
  - 5 ux-lab proof PNGs + Source OS HTML/CSS/JS
  - Hermes Voice layer (Azure STT/TTS) and ComfyUI generation pipeline

## Key files
| Role | Path |
|---|---|
| Verifier / install dispatcher | `apps/api/hermes3d_api/source_install.py` (`_install_pip`, line 326) |
| Launcher | `apps/api/hermes3d_api/main.py` `_launch_octoprint` (line 893) |
| Registry / schema | `apps/web/source_manifest.json` (line 304), `source-lab/source_manifest.json` |
| E2E test | `tests/e2e/app-octoprint.spec.ts` |
| Process state | `apps/api/hermes3d_api/process_state.py` |
| Subprocess probes | `source_install.py` lines 165, 304, 344, 357 (`subprocess.run`) |

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
  <text class="small" x="170" y="154">_install_pip</text>
  <text class="small" x="170" y="166">subprocess.run</text>

  <rect class="y" x="240" y="120" width="100" height="50" rx="6"/>
  <text x="290" y="138">OctoPrint</text>
  <text class="small" x="290" y="154">.venv pip pkg</text>
  <text class="small" x="290" y="166">:5000 HTTP</text>

  <rect class="p" x="360" y="40" width="120" height="50" rx="6"/>
  <text x="420" y="60">Action Window</text>
  <text class="small" x="420" y="76">Install/Launch/Stop</text>

  <rect class="p" x="360" y="200" width="120" height="50" rx="6"/>
  <text x="420" y="220">UI badge</text>
  <text class="small" x="420" y="236">install_status</text>

  <line x1="100" y1="145" x2="120" y2="145" marker-end="url(#a)"/>
  <line x1="220" y1="145" x2="240" y2="145" marker-end="url(#a)"/>
  <path d="M340 135 L360 65" marker-end="url(#a)"/>
  <path d="M340 155 L360 225" marker-end="url(#a)"/>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
