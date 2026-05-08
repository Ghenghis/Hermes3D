# h3dos-wire-global-event-bus-logger

- **UI surface**: Cross-cutting devtools logger — listens on `document` for the `actionwindow:render` custom event when `?debug=1` is in the URL
- **Tab**: All tabs (global; not tied to one Hermes3D tab)
- **Backend endpoint**: NONE (INFERRED — this is a pure client-side instrumentation; no backend route is wired). The logger inspects already-dispatched payloads bound for ActionWindow.
- **Files changed** (PR #46, commit `4515d6b`):
  - `apps/web/app.js` — +15 lines (gated `if (?debug=1)` block, group-logging tab_id, item_id, status_pill, primary_actions, full payload)
  - `tests/e2e/wire-global-event-bus-logger.spec.ts` — +19 lines
- **Status**: MERGED (PR #46 in branch history); this worktree carries cascade re-resolves
- **Branch & last commit**: `wire/global-event-bus-logger` @ `1af1f6a merge(develop): cascade x2 — re-append debug logger after approvals handler`
- **Path**: `G:\Github\h3dos-wire-global-event-bus-logger`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#fbbf24; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#fbbf24; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fbbf24"/></marker></defs>
  <rect class="box" x="10" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="20" y="65">?debug=1 URL</text>
  <text class="small" x="20" y="82">enables listener</text>
  <path class="arrow" d="M130,70 L170,70"/>
  <rect class="box" x="170" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="180" y="62">document.</text>
  <text class="label" x="180" y="78">addEventListener</text>
  <text class="small" x="180" y="95">actionwindow:render</text>
  <path class="arrow" d="M290,70 L330,70"/>
  <rect class="box" x="330" y="40" width="65" height="60" rx="6"/>
  <text class="small" x="338" y="62">console.</text>
  <text class="small" x="338" y="76">group()</text>
  <text class="small" x="338" y="92">payload</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">No backend — passive devtools tap</text>
  <text class="small" x="92" y="205">Logs tab_id, item_id, status_pill, actions</text>
</svg>
```
