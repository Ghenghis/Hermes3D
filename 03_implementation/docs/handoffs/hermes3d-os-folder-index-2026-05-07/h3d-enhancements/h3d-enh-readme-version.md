# h3d-enh-readme-version

- **Type**: ENHANCEMENT (DOCS)
- **Status**: MERGED
- **Branch**: `docs/readme-version-sync`
- **Last commit**: `19c0256 docs(readme): sync sprint copy to v5.3.0 RC + link release notes`
- **PR link**: [#45 — docs(readme): sync sprint copy to v5.3.0 RC + link release notes](https://github.com/Ghenghis/Hermes3D/pull/45)
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Sync the top-level `README.md` "current sprint" copy to the v5.3.0 RC and add a link to the freshly-drafted v5.3.0 release notes. A small surface-area docs touch — fixes a stale version reference rather than introducing new content.

## Files changed (vs `origin/develop`)

| File | + / - |
| --- | --- |
| `README.md` | +2 / -1 |

Total: 1 file changed, 2 insertions, 1 deletion.

## Notes

- One-commit branch on top of `3fde207 docs(release): draft v5.3.0 release notes`.
- Pure documentation; no code or CI changes.
- Squash-merged into `develop` as PR #45.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-enh-readme-version change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .mod { fill: #78350f; stroke: #f59e0b; }
    .label { fill: #f9fafb; font: 600 12px sans-serif; }
    .sub { fill: #d1d5db; font: 11px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
    .arrow { stroke: #9ca3af; stroke-width: 1.5; fill: none; marker-end: url(#a); }
  </style>
  <defs>
    <marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#9ca3af"/>
    </marker>
  </defs>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">docs/readme-version-sync — README.md before / after</text>

  <rect class="box" x="30" y="60" width="170" height="140" rx="6"/>
  <text class="label" x="40" y="82">README.md (before)</text>
  <text class="sub"   x="40" y="104">"current sprint: v5.2.x"</text>
  <text class="sub"   x="40" y="124">no link to release notes</text>
  <text class="sub"   x="40" y="160">3fde207 (develop tip)</text>

  <path class="arrow" d="M205,130 L245,130"/>

  <rect class="box mod" x="250" y="60" width="170" height="140" rx="6"/>
  <text class="label" x="260" y="82">README.md (after)</text>
  <text class="sub"   x="260" y="104">"current sprint: v5.3.0 RC"</text>
  <text class="sub"   x="260" y="124">+ link → V5_3_0_RELEASE_NOTES</text>
  <text class="sub"   x="260" y="160">19c0256 — PR #45 MERGED</text>

  <text class="sub" x="225" y="225" text-anchor="middle" fill="#9ca3af">+2 / -1 · single-file docs sync</text>
</svg>
```
