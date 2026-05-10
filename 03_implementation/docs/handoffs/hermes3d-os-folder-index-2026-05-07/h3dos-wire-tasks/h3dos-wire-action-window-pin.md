# h3dos-wire-action-window-pin

- **UI surface**: Pin icon (`📌`) added to the Action Window header (`[data-aw-pin]` button); when active, incoming `actionwindow:render` dispatches are silently ignored
- **Tab**: Cross-cutting (Action Window itself; not bound to a single Hermes3D tab)
- **Backend endpoint**: NONE (INFERRED — pure client-side state; Slot 19 is a UX gate over the AW dispatch event, no API call wired)
- **Files changed** (commit `814c727`):
  - `apps/web/action-window.js` — +17 lines (`pinned` module-scoped state, pin button in header, click/close handlers, gate at top of `renderActionWindow`)
  - `tests/e2e/wire-action-window-pin.spec.ts` — +29 lines
- **Status**: OPEN (single feature commit; no PR-merge marker)
- **Branch & last commit**: `wire/action-window-pin` @ `814c727 wire(action-window-pin): pin icon prevents dispatch replacement`
- **Path**: `G:\Github\h3dos-wire-action-window-pin`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#ef4444; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#ef4444; stroke-width:1.5; fill:none; marker-end:url(#a); }
    .arrow-blocked { stroke:#6b7280; stroke-width:1.5; stroke-dasharray:4 3; fill:none; }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ef4444"/></marker></defs>
  <rect class="box" x="10" y="20" width="110" height="55" rx="6"/>
  <text class="label" x="20" y="42">incoming</text>
  <text class="small" x="20" y="58">actionwindow:render</text>
  <path class="arrow-blocked" d="M120,45 L260,45"/>
  <text class="small" x="155" y="38">blocked when pinned</text>
  <rect class="box" x="260" y="20" width="130" height="55" rx="6"/>
  <text class="label" x="270" y="42">renderActionWindow</text>
  <text class="small" x="270" y="58">if (pinned) return host()</text>
  <rect class="box" x="100" y="105" width="200" height="55" rx="6"/>
  <text class="label" x="110" y="125">📌 [data-aw-pin] button</text>
  <text class="small" x="110" y="142">toggles pinned, .active class</text>
  <path class="arrow" d="M200,105 L200,80"/>
  <rect class="box" x="80" y="180" width="240" height="50" rx="6"/>
  <text class="label" x="92" y="205">No backend — client-only state</text>
  <text class="small" x="92" y="223">Reset to false on AW close</text>
</svg>
```
