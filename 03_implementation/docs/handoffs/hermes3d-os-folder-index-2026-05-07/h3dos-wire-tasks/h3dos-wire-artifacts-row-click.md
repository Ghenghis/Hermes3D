# h3dos-wire-artifacts-row-click

- **UI surface**: Artifact card row click (`.artifact-card[data-artifact-id]`)
- **Tab**: Artifacts
- **Backend endpoint**: `GET /api/artifacts/<id>/download`, `POST /api/artifacts/<id>/open-folder` (wired into Action Window primary actions)
- **Files changed** (latest commit `3036094`):
  - `apps/web/app.js` — +23 lines (document-level delegation handler dispatching `actionwindow:render`)
  - Earlier wire commit added `tests/e2e/wire-artifacts-row-click-actionwindow.spec.ts` (in branch history)
- **Status**: MERGED (PR #44 visible in branch log: `feat(wire/artifacts-row-click): artifact row → Action Window (#44)`); this worktree carries a follow-up delegation fix
- **Branch & last commit**: `wire/artifacts-row-click` @ `3036094 fix(artifacts): use document-level delegation for artifact card click handler`
- **Path**: `G:\Github\h3dos-wire-artifacts-row-click`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#60a5fa; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#60a5fa; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
  <rect class="box" x="10" y="40" width="110" height="60" rx="6"/>
  <text class="label" x="20" y="65">.artifact-card</text>
  <text class="small" x="20" y="82">data-artifact-id</text>
  <text class="small" x="20" y="95">click (delegated)</text>
  <path class="arrow" d="M120,70 L160,70"/>
  <rect class="box" x="160" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="170" y="65">ActionWindow</text>
  <text class="small" x="170" y="82">kind=artifact</text>
  <text class="small" x="170" y="95">tab_id=artifacts</text>
  <path class="arrow" d="M280,70 L320,70"/>
  <rect class="box" x="320" y="20" width="75" height="100" rx="6"/>
  <text class="small" x="328" y="40">/api/artifacts</text>
  <text class="small" x="328" y="55">/{id}/download</text>
  <text class="small" x="328" y="75">/api/artifacts</text>
  <text class="small" x="328" y="90">/{id}/open-folder</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">Response shape (binary or JSON)</text>
  <text class="small" x="92" y="205">download → file stream • open-folder → {ok}</text>
</svg>
```
