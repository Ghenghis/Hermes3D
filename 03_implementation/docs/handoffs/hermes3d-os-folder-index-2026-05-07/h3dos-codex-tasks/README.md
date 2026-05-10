# h3dos-codex-* folder index

Five Codex-driven implementation worktrees under `G:\Github\h3dos-codex-*`. Each lane carries a `feat(app/<id>): install + launcher + Action Window + e2e` commit on top of `main` and shares a single dispatcher (`apps/api/hermes3d_api/source_install.py`) plus the Source OS Action Window UI.

## Lanes

| Folder | Branch | Group | Method | Status | Notes |
|---|---|---|---|---|---|
| [h3dos-codex-octoprint](./h3dos-codex-octoprint.md) | `app/octoprint` | printer_farm | pip + managed-process | DRAFT (local) | HTTP probe :5000, smoke API key |
| [h3dos-codex-fluidd](./h3dos-codex-fluidd.md) | `app/fluidd` | printer_farm | npm-build (static) | DRAFT (local) | Built into `dist/`, served at `/static/fluidd/` |
| [h3dos-codex-blender-cli](./h3dos-codex-blender-cli.md) | `app/blender-cli` | modelers | clone-shallow + system CLI | DRAFT (local) | Smoke args `--background --version` |
| [h3dos-codex-prusaslicer](./h3dos-codex-prusaslicer.md) | `app/prusaslicer` | slicers | binary-download | DRAFT (local) | Release zip 2.9.4, GUI launch supported |
| [h3dos-codex-triposr](./h3dos-codex-triposr.md) | `app/triposr` | generation | clone-full-venv | OPEN (origin) | Only lane pushed to GitHub origin |

## Shared architecture

- All lanes share `apps/api/hermes3d_api/source_install.py` (~636 LOC) — single dispatch entrypoint with method-specific handlers (`_install_pip`, `_install_clone`, `_install_clone_full_venv`, `_install_npm_build`, `_install_binary_download`, `_install_noop`).
- Per-app metadata (registry / probe args) lives in `apps/web/source_manifest.json` and `source-lab/source_manifest.json`.
- Verification is mostly via `subprocess.run` (8 call sites in `source_install.py`); HTTP probe is OctoPrint-specific (`http://127.0.0.1:5000`).
- Each lane adds a Playwright E2E spec under `tests/e2e/app-<id>.spec.ts` plus the shared foundation specs (`foundation-action-window.spec.ts`, `foundation-install-endpoint.spec.ts`).
- Lanes are stacked linearly in commit history through PRs #21 (docs/agent-starters), #22 (triposr), #23 (prusaslicer), #24 (blender-cli), #25 (fluidd) — only #21 (predecessor docs) is merged into `main` on origin; #22-25 plus the latest octoprint commit live only in local worktrees.

## Master SVG: H3D Source OS verifier-readiness flow

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="700" height="400">
  <rect width="700" height="400" fill="#0e1117"/>
  <style>
    .b{fill:#1f6feb;stroke:#58a6ff;stroke-width:1.5}
    .g{fill:#238636;stroke:#3fb950;stroke-width:1.5}
    .pip{fill:#9e6a03;stroke:#d29922;stroke-width:1.2}
    .npm{fill:#bf3989;stroke:#db61a2;stroke-width:1.2}
    .bin{fill:#cf222e;stroke:#ff7b72;stroke-width:1.2}
    .clone{fill:#6e40c9;stroke:#a371f7;stroke-width:1.2}
    .venv{fill:#1a7f37;stroke:#3fb950;stroke-width:1.2}
    .ui{fill:#0969da;stroke:#58a6ff;stroke-width:1.2}
    text{fill:#f0f6fc;font-family:Segoe UI,sans-serif;font-size:11px;text-anchor:middle}
    .small{font-size:9px;fill:#c9d1d9}
    .head{font-size:13px;font-weight:600}
    line,path{stroke:#58a6ff;stroke-width:1.3;fill:none}
  </style>

  <text class="head" x="350" y="22">Hermes3D Source OS — verifier readiness (5 Codex lanes)</text>

  <rect class="b" x="20" y="170" width="120" height="60" rx="8"/>
  <text x="80" y="195" class="head">H3D backend</text>
  <text class="small" x="80" y="212">FastAPI / main.py</text>
  <text class="small" x="80" y="224">/api/source-apps/*</text>

  <rect class="g" x="180" y="170" width="140" height="60" rx="8"/>
  <text x="250" y="195" class="head">source_install.py</text>
  <text class="small" x="250" y="212">dispatcher + state</text>
  <text class="small" x="250" y="224">subprocess.run × 8</text>

  <line x1="140" y1="200" x2="180" y2="200" marker-end="url(#a)"/>

  <rect class="pip" x="360" y="40" width="160" height="44" rx="6"/>
  <text x="440" y="58">pip install (OctoPrint)</text>
  <text class="small" x="440" y="74">.venv\Scripts\octoprint.exe → :5000</text>

  <rect class="npm" x="360" y="100" width="160" height="44" rx="6"/>
  <text x="440" y="118">npm-build (Fluidd)</text>
  <text class="small" x="440" y="134">npm ci + npm run build → dist/</text>

  <rect class="clone" x="360" y="180" width="160" height="44" rx="6"/>
  <text x="440" y="198">clone-shallow (Blender)</text>
  <text class="small" x="440" y="214">blender --background --version</text>

  <rect class="bin" x="360" y="240" width="160" height="44" rx="6"/>
  <text x="440" y="258">binary-download (PrusaSlicer)</text>
  <text class="small" x="440" y="274">unzip → prusa-slicer.exe</text>

  <rect class="venv" x="360" y="300" width="160" height="44" rx="6"/>
  <text x="440" y="318">clone-full-venv (TripoSR)</text>
  <text class="small" x="440" y="334">.venv + requirements.txt</text>

  <path d="M320 200 L360 62" marker-end="url(#a)"/>
  <path d="M320 200 L360 122" marker-end="url(#a)"/>
  <path d="M320 200 L360 202" marker-end="url(#a)"/>
  <path d="M320 200 L360 262" marker-end="url(#a)"/>
  <path d="M320 200 L360 322" marker-end="url(#a)"/>

  <rect class="ui" x="560" y="80" width="120" height="60" rx="8"/>
  <text x="620" y="105" class="head">Action Window</text>
  <text class="small" x="620" y="122">Install / Launch</text>
  <text class="small" x="620" y="134">Stop / Open Browser</text>

  <rect class="ui" x="560" y="240" width="120" height="60" rx="8"/>
  <text x="620" y="265" class="head">UI badge</text>
  <text class="small" x="620" y="282">install_status</text>
  <text class="small" x="620" y="294">process_state</text>

  <path d="M520 62 L560 100" marker-end="url(#a)"/>
  <path d="M520 122 L560 110" marker-end="url(#a)"/>
  <path d="M520 202 L560 130" marker-end="url(#a)"/>
  <path d="M520 262 L560 270" marker-end="url(#a)"/>
  <path d="M520 322 L560 285" marker-end="url(#a)"/>

  <text class="small" x="350" y="380">All lanes share source_install.py + source_manifest.json + Action Window. Method varies per app.</text>

  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#58a6ff"/></marker></defs>
</svg>
```
