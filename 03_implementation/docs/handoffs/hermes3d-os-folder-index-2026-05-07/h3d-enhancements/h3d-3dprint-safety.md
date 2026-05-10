# h3d-3dprint-safety

- **Type**: SAFETY
- **Status**: MERGED
- **Branch**: `feat/cp-h3d-3dprint-safety-gates`
- **Last commit**: `70e4c64 style(safety): apply ruff format to satisfy CI Layer A`
- **PR link**: [#43 — feat(safety): 4 P1 3D-printing safety gates batch (H3D-V5.3-3DPRINT-SAFETY)](https://github.com/Ghenghis/Hermes3D/pull/43)
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Land the four P1 3D-printing safety gates as a single bundle: G-code bounds validator, material-window checker, thermal-runaway monitor, and emergency-stop handler. Each gate ships with a focused pytest module, plus ADR-018 to document the safety architecture.

## Files changed (vs `origin/develop`)

| File | + / - |
| --- | --- |
| `00_overview/adr/ADR-018-3d-printing-safety-gates.md` | +204 |
| `03_implementation/src/hermes3d/core/safety/__init__.py` | +253 |
| `03_implementation/src/hermes3d/core/safety/emergency_stop.py` | +207 |
| `03_implementation/src/hermes3d/core/safety/gcode_bounds.py` | +518 |
| `03_implementation/src/hermes3d/core/safety/material_db.yaml` | +59 |
| `03_implementation/src/hermes3d/core/safety/material_window.py` | +299 |
| `03_implementation/src/hermes3d/core/safety/thermal_runaway.py` | +205 |
| `04_testing/pytest/test_safety_bundle.py` | +125 |
| `04_testing/pytest/test_safety_emergency_stop.py` | +66 |
| `04_testing/pytest/test_safety_gcode_bounds.py` | +233 |
| `04_testing/pytest/test_safety_material_window.py` | +158 |
| `04_testing/pytest/test_safety_thermal_runaway.py` | +151 |

Total: 12 files changed, +2478 / -0.

## Notes

- Pure additive change — no existing files modified, new `core/safety/` subpackage.
- Two commits: `cfea942` (logic) + `70e4c64` (ruff-format follow-up to clear CI Layer A).
- Squash-merged as PR #43.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-3dprint-safety change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .new { fill: #065f46; stroke: #10b981; }
    .label { fill: #f9fafb; font: 600 11px sans-serif; }
    .sub { fill: #d1d5db; font: 10px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
  </style>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">core/safety/ — four gates + matched test bundle</text>

  <rect class="box new" x="20" y="45" width="170" height="38" rx="5"/>
  <text class="label" x="30" y="62">gcode_bounds.py</text>
  <text class="sub"   x="30" y="76">+518 · test +233</text>

  <rect class="box new" x="20" y="92" width="170" height="38" rx="5"/>
  <text class="label" x="30" y="109">material_window.py</text>
  <text class="sub"   x="30" y="123">+299 · test +158 · DB.yaml +59</text>

  <rect class="box new" x="20" y="139" width="170" height="38" rx="5"/>
  <text class="label" x="30" y="156">thermal_runaway.py</text>
  <text class="sub"   x="30" y="170">+205 · test +151</text>

  <rect class="box new" x="20" y="186" width="170" height="38" rx="5"/>
  <text class="label" x="30" y="203">emergency_stop.py</text>
  <text class="sub"   x="30" y="217">+207 · test +66</text>

  <rect class="box new" x="220" y="45" width="210" height="80" rx="6"/>
  <text class="label" x="230" y="65">__init__.py — gate aggregator</text>
  <text class="sub"   x="230" y="83">+253 · exports 4 gates</text>
  <text class="sub"   x="230" y="98">+ test_safety_bundle.py +125</text>
  <text class="sub"   x="230" y="113">end-to-end orchestration tests</text>

  <rect class="box new" x="220" y="139" width="210" height="60" rx="6"/>
  <text class="label" x="230" y="159">ADR-018</text>
  <text class="sub"   x="230" y="177">+204 · safety architecture rationale</text>

  <text class="sub" x="225" y="232" text-anchor="middle" fill="#9ca3af">12 files · +2478 / -0 · PR #43 MERGED</text>
</svg>
```
