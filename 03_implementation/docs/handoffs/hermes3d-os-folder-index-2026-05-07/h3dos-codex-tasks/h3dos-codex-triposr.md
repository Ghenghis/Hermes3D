# h3dos-codex-triposr

## Target app
- **Name**: TripoSR (VAST-AI-Research)
- **Role**: 3D generator (fast image-to-3D preview mesh, fallback before expensive Hunyuan3D / TRELLIS pipelines)
- **Upstream**: https://github.com/VAST-AI-Research/TripoSR.git
- **License**: MIT

## Source OS module
- **Registry entry**: `groups.generation[].id == "triposr"` in `apps/web/source_manifest.json` (line 459)
- **UX section**: `3D Generation / Fast Preview`
- **Manifest target path**: `generation/TripoSR`
- **Setup marker**: `.hermes3d-venv-ready` (created when venv install completes)

## Integration type
- **Method**: `clone-full-venv` — full clone, create `.venv`, install `requirements.txt`
- **Probe**: file existence (`probe_files: ["run.py", "gradio_app.py"]`) + setup marker
- **Process model**: ad-hoc Python invocations via venv interpreter (no managed long-running daemon at this lane)
- **Constraint**: PyTorch / CUDA must be supplied by host per upstream guidance (no cloud / paid services)

## Status
- **OPEN (pushed to origin)** — branch `app/triposr` is the only one of the five lanes published to `origin`. HEAD `7094212 fix(web): align page title with Hermes3D smoke`. PR #21 (predecessor docs/agent-starters) is already merged into main per `8e4bf98 Merge pull request #21 from Ghenghis/docs/agent-starters`.

## Branch & last commit
- **Branch**: `app/triposr`
- **HEAD**: `7094212 fix(web): align page title with Hermes3D smoke`
- **Recent commits**: `94f199f ci(e2e): add npm lockfile`, `a7ac037 fix(source-os): tighten source click selectors`, `b3477fd feat(app/triposr): install source with venv and e2e`
- **Working tree**: clean

## Files changed (vs `main`)
- 157 files, ~13,020 insertions / 116 deletions (smallest of the five — base of the stack)
- Notable additions:
  - `tests/e2e/app-triposr.spec.ts` (97 LOC)
  - `apps/api/hermes3d_api/source_install.py::_install_clone_full_venv` (line 413)
  - `source-lab/download-report.md` (63 LOC) — clone evidence
  - `source-lab/source_manifest.json` (590 LOC)
  - Manifest entry lines 459-475 (clone-full-venv install block)

## Key files
| Role | Path |
|---|---|
| Verifier | `apps/api/hermes3d_api/source_install.py::_install_clone_full_venv` (line 413) |
| Subprocess probes | `source_install.py` lines 387, 403 (`subprocess.run` for git clone + venv pip install) |
| Registry / schema | `apps/web/source_manifest.json` line 459 |
| E2E test | `tests/e2e/app-triposr.spec.ts` |
| Download evidence | `source-lab/download-report.md` |

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
  <text class="small" x="170" y="154">clone_full_venv</text>
  <text class="small" x="170" y="166">git + pip venv</text>

  <rect class="y" x="240" y="120" width="100" height="50" rx="6"/>
  <text x="290" y="138">TripoSR</text>
  <text class="small" x="290" y="154">run.py</text>
  <text class="small" x="290" y="166">gradio_app.py</text>

  <rect class="p" x="360" y="40" width="120" height="50" rx="6"/>
  <text x="420" y="60">Action Window</text>
  <text class="small" x="420" y="76">Install probe</text>

  <rect class="p" x="360" y="200" width="120" height="50" rx="6"/>
  <text x="420" y="220">UI badge</text>
  <text class="small" x="420" y="236">setup_marker</text>

  <line x1="100" y1="145" x2="120" y2="145" marker-end="url(#a)"/>
  <line x1="220" y1="145" x2="240" y2="145" marker-end="url(#a)"/>
  <path d="M340 135 L360 65" marker-end="url(#a)"/>
  <path d="M340 155 L360 225" marker-end="url(#a)"/>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
