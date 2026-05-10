# h3d-* enhancement worktrees — index (2026-05-07)

Per-folder index for the seven `G:\Github\h3d-*` worktrees. Each worktree is a single-branch checkout of `https://github.com/Ghenghis/Hermes3D` carrying one focused enhancement / fix on top of `origin/develop`.

**Diff base** for every entry: `origin/develop` (these branches do not share history with `main`).

## By type

### ENHANCEMENT

| Folder | Branch | PR | State | + / - | Lines summary |
| --- | --- | --- | --- | --- | --- |
| [h3d-enh-screenshots](./h3d-enh-screenshots.md) | `docs/launcher-screenshots` | — | OPEN (WIP) | +0 / -0 committed | Playwright capture script + README, uncommitted |
| [h3d-enh-readme-version](./h3d-enh-readme-version.md) | `docs/readme-version-sync` | [#45](https://github.com/Ghenghis/Hermes3D/pull/45) | MERGED | +2 / -1 | README sprint copy → v5.3.0 RC |
| [h3d-routing](./h3d-routing.md) | `feat/cp-h3d-routing-mode` | — | OPEN (no PR) | +1784 / -1 | Provider registry YAML + loader + ADR-017 |
| [h3d-stream-bootstrap](./h3d-stream-bootstrap.md) | `docs/stream-protocol-bootstrap` | [#39](https://github.com/Ghenghis/Hermes3D/pull/39) | MERGED | +1406 / -0 | `handoffs/STREAM/` protocol scaffolding |
| [h3d-pr37](./h3d-pr37.md) | `fix-pr37-ruff-format` | [#37](https://github.com/Ghenghis/Hermes3D/pull/37) | ABANDONED (CLOSED) | +596 / -0 | Partial scaffolds (tool_registry, security stub, ServiceHealthPage) |
| [h3d-pr34](./h3d-pr34.md) | `fix-pr34-ruff-import-sort` | [#34](https://github.com/Ghenghis/Hermes3D/pull/34) | MERGED | +380 / -4 | Mnemosyne recall layer (non-canonical memory) |

### SAFETY

| Folder | Branch | PR | State | + / - | Lines summary |
| --- | --- | --- | --- | --- | --- |
| [h3d-3dprint-safety](./h3d-3dprint-safety.md) | `feat/cp-h3d-3dprint-safety-gates` | [#43](https://github.com/Ghenghis/Hermes3D/pull/43) | MERGED | +2478 / -0 | Four P1 print-safety gates + ADR-018 + matched pytest bundle |

### Aggregate roll-up

- **Merged**: 4 (PRs #34, #39, #43, #45)
- **Open / WIP**: 2 (`h3d-routing`, `h3d-enh-screenshots`)
- **Abandoned**: 1 (`h3d-pr37`)
- **Net committed lines across the seven worktrees**: ~+6646 / -6 (+ uncommitted Playwright scaffolding in screenshots)

## Master diagram — how these enhancements layer onto Hermes3D

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="700" height="400" role="img" aria-label="h3d-* enhancement layering on Hermes3D main repo">
  <style>
    .base { fill: #1e293b; stroke: #475569; stroke-width: 1.5; }
    .enh  { fill: #064e3b; stroke: #10b981; stroke-width: 1.2; }
    .saf  { fill: #7f1d1d; stroke: #ef4444; stroke-width: 1.2; }
    .docs { fill: #1e3a8a; stroke: #60a5fa; stroke-width: 1.2; }
    .bug  { fill: #78350f; stroke: #f59e0b; stroke-width: 1.2; }
    .abd  { fill: #4c1d24; stroke: #f87171; stroke-dasharray: 4 3; }
    .label { fill: #f9fafb; font: 600 12px sans-serif; }
    .sub   { fill: #d1d5db; font: 10.5px sans-serif; }
    .title { fill: #f9fafb; font: 700 16px sans-serif; }
    .stitle{ fill: #f9fafb; font: 700 12px sans-serif; }
    .arrow { stroke: #94a3b8; stroke-width: 1.3; fill: none; marker-end: url(#m); }
    .legend{ fill: #e5e7eb; font: 11px sans-serif; }
  </style>
  <defs>
    <marker id="m" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#94a3b8"/>
    </marker>
  </defs>
  <rect width="700" height="400" fill="#0b1220"/>
  <text class="title" x="350" y="26" text-anchor="middle">Hermes3D `develop` ← seven h3d-* worktrees layering in v5.3.0 RC</text>

  <!-- base repo -->
  <rect class="base" x="220" y="48" width="260" height="60" rx="8"/>
  <text class="stitle" x="350" y="72" text-anchor="middle">Ghenghis/Hermes3D · branch develop</text>
  <text class="sub"    x="350" y="92" text-anchor="middle">core/ · ui/ · 02_specs/policies · handoffs/ · ADRs · tests</text>

  <!-- runtime/code lane (left) -->
  <text class="stitle" x="100" y="140" text-anchor="middle">runtime / source</text>

  <rect class="saf" x="20" y="155" width="160" height="46" rx="6"/>
  <text class="label" x="30" y="174">h3d-3dprint-safety</text>
  <text class="sub"   x="30" y="190">core/safety/ · 4 gates · #43 MERGED</text>

  <rect class="enh" x="20" y="210" width="160" height="46" rx="6"/>
  <text class="label" x="30" y="229">h3d-routing</text>
  <text class="sub"   x="30" y="245">core/llm registry+routing · OPEN</text>

  <rect class="enh" x="20" y="265" width="160" height="46" rx="6"/>
  <text class="label" x="30" y="284">h3d-pr34 (mnemosyne)</text>
  <text class="sub"   x="30" y="300">core/memory recall · #34 MERGED</text>

  <rect class="abd" x="20" y="320" width="160" height="46" rx="6"/>
  <text class="label" x="30" y="339">h3d-pr37 (scaffolds)</text>
  <text class="sub"   x="30" y="355">tool_registry+UI · #37 CLOSED</text>

  <!-- docs lane (right) -->
  <text class="stitle" x="600" y="140" text-anchor="middle">docs / process</text>

  <rect class="docs" x="520" y="155" width="160" height="46" rx="6"/>
  <text class="label" x="530" y="174">h3d-stream-bootstrap</text>
  <text class="sub"   x="530" y="190">handoffs/STREAM · #39 MERGED</text>

  <rect class="docs" x="520" y="210" width="160" height="46" rx="6"/>
  <text class="label" x="530" y="229">h3d-enh-readme-version</text>
  <text class="sub"   x="530" y="245">README sync · #45 MERGED</text>

  <rect class="docs" x="520" y="265" width="160" height="46" rx="6"/>
  <text class="label" x="530" y="284">h3d-enh-screenshots</text>
  <text class="sub"   x="530" y="300">site/screenshots · WIP</text>

  <!-- arrows from worktrees into develop -->
  <path class="arrow" d="M180,178 C 220,170 240,135 280,108"/>
  <path class="arrow" d="M180,233 C 230,210 270,150 310,108"/>
  <path class="arrow" d="M180,288 C 240,250 290,160 340,108"/>
  <path class="arrow" d="M180,343 C 240,300 310,170 360,108" stroke-dasharray="4 3"/>

  <path class="arrow" d="M520,178 C 480,170 460,135 420,108"/>
  <path class="arrow" d="M520,233 C 470,210 430,150 400,108"/>
  <path class="arrow" d="M520,288 C 480,250 440,170 400,108"/>

  <!-- legend -->
  <rect class="enh"  x="30"  y="378" width="14" height="12"/>
  <text class="legend" x="50"  y="389">enhancement (runtime)</text>
  <rect class="saf"  x="195" y="378" width="14" height="12"/>
  <text class="legend" x="215" y="389">safety</text>
  <rect class="docs" x="270" y="378" width="14" height="12"/>
  <text class="legend" x="290" y="389">docs / handoff</text>
  <rect class="abd"  x="395" y="378" width="14" height="12"/>
  <text class="legend" x="415" y="389">abandoned (CLOSED)</text>
  <text class="legend" x="540" y="389">arrows: layered on develop</text>
</svg>
```

## Notes / caveats

- All diffs are computed against `origin/develop` because `main` and these branches do not share history in this repo (empty merge-base). This is consistent with the v5.3.0 sprint convention: feature work targets `develop`, releases roll forward into `main` later.
- `h3d-enh-screenshots` is on the develop tip with **no extra commits** — the Playwright capture script and `site/screenshots/README.md` are still staged as untracked + a one-line README.md edit.
- `h3d-pr37` was closed without merging; the scaffolds (`tool_registry`, security stub, `ServiceHealthPage`) may have been re-landed under a different PR — verify on `develop` before assuming the abandoned state means absent code.
- The eighth folder `h3d-gui-wiring-codex` was not in scope for this index.
