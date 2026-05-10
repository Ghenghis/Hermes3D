# h3d-pr34

- **Type**: ENHANCEMENT (memory recall) + BUGFIX (ruff lint follow-up)
- **Status**: MERGED
- **Branch (worktree)**: `fix-pr34-ruff-import-sort`
- **Original PR head branch**: `feat/cp-h3d-mnemosyne-recall-recovered`
- **Last commit**: `9197461 style(orchestrator): re-sort TYPE_CHECKING import block (ruff I001)`
- **PR link**: [#34 — feat(memory): Mnemosyne recall layer (recovered from agent collision)](https://github.com/Ghenghis/Hermes3D/pull/34)
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Add the Mnemosyne recall layer — a non-canonical memory plane that lets the dispatcher consult `mnemosyne-memory >=2.0` for prior context without making recall a source of truth. Branch tip is two ruff follow-ups (F401 suppression + I001 import re-sort) that clear CI Layer A on the same PR.

## Files changed (vs `origin/develop`)

| File | + / - |
| --- | --- |
| `00_overview/adr/ADR-015-mnemosyne-recall-layer.md` | +46 |
| `03_implementation/src/hermes3d/core/agents/dispatcher.py` | +43 / -1 |
| `03_implementation/src/hermes3d/core/agents/orchestrator.py` | +3 |
| `03_implementation/src/hermes3d/core/memory/__init__.py` | +17 / -1 |
| `03_implementation/src/hermes3d/core/memory/mnemosyne_recall.py` | +261 |
| `pyproject.toml` | +5 / -1 |
| `requirements.txt` | +6 |

Total: 7 files changed, +380 / -4.

## Notes

- Recovered branch — shipped after an agent-collision incident where the original work was lost; ADR-015 captures the recovered design.
- Recall is explicitly **not canonical** (per memory note "recall NOT canonical") — the dispatcher consults Mnemosyne, but writes still go through the primary store.
- Three commits on this worktree branch: ADR fix-up, F401 suppression, I001 re-sort. Squash-merged as PR #34.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-pr34 change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .new { fill: #065f46; stroke: #10b981; }
    .mod { fill: #78350f; stroke: #f59e0b; }
    .label { fill: #f9fafb; font: 600 11px sans-serif; }
    .sub { fill: #d1d5db; font: 10px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
    .arrow { stroke: #9ca3af; stroke-width: 1.4; fill: none; marker-end: url(#a); }
  </style>
  <defs>
    <marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#9ca3af"/>
    </marker>
  </defs>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">PR #34 Mnemosyne recall — non-canonical memory plane</text>

  <rect class="box new" x="20" y="50" width="180" height="60" rx="5"/>
  <text class="label" x="30" y="70">core/memory/mnemosyne_recall.py</text>
  <text class="sub"   x="30" y="88">+261 — NEW recall plane</text>
  <text class="sub"   x="30" y="102">non-canonical · read-side only</text>

  <rect class="box mod" x="240" y="50" width="190" height="60" rx="5"/>
  <text class="label" x="250" y="70">core/agents/</text>
  <text class="sub"   x="250" y="88">dispatcher.py +43 / -1 (consults)</text>
  <text class="sub"   x="250" y="102">orchestrator.py +3 (wires)</text>

  <path class="arrow" d="M200,80 L240,80"/>

  <rect class="box mod" x="20" y="125" width="180" height="50" rx="5"/>
  <text class="label" x="30" y="145">core/memory/__init__.py</text>
  <text class="sub"   x="30" y="161">+17 / -1 — exports recall</text>

  <rect class="box mod" x="240" y="125" width="190" height="50" rx="5"/>
  <text class="label" x="250" y="145">deps</text>
  <text class="sub"   x="250" y="161">pyproject +5/-1 · requirements +6</text>

  <rect class="box new" x="20" y="190" width="410" height="40" rx="5"/>
  <text class="label" x="30" y="210">ADR-015 (+46) · recovered-from-collision rationale</text>
  <text class="sub"   x="30" y="224">7 files · +380 / -4 · PR #34 MERGED</text>
</svg>
```
