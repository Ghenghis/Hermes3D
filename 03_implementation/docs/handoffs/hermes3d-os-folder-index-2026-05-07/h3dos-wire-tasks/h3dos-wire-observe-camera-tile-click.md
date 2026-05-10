# h3dos-wire-observe-camera-tile-click

- **UI surface**: Observe-tab camera tile click (camera card per printer)
- **Tab**: Observe
- **Backend endpoint**:
  - `POST /api/observe/mute/<printer_id>` — Action Window primary action "Mute Camera"
  - `GET /api/observe/stream/<printer_id>` — Action Window `stream_url` (live SSE log panel)
- **Files changed** (PR #41, commit `0938671`):
  - `apps/web/app.js` — +22 lines (Slot 8: camera-card click → ActionWindow `kind=printer` with stream_url)
  - `tests/e2e/wire-observe-camera-tile-click.spec.ts` — +14 lines
- **Status**: MERGED (PR #41 in branch log); this worktree carries cascade re-resolves
- **Branch & last commit**: `wire/observe-camera-tile-click` @ `ce361d6 merge(develop): cascade re-resolve x2 — re-append observe camera AW handler`
- **Path**: `G:\Github\h3dos-wire-observe-camera-tile-click`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#f472b6; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#f472b6; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f472b6"/></marker></defs>
  <rect class="box" x="10" y="40" width="110" height="60" rx="6"/>
  <text class="label" x="20" y="62">camera tile</text>
  <text class="small" x="20" y="80">.camera-card</text>
  <text class="small" x="20" y="95">click</text>
  <path class="arrow" d="M120,70 L160,70"/>
  <rect class="box" x="160" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="170" y="62">ActionWindow</text>
  <text class="small" x="170" y="80">kind=printer</text>
  <text class="small" x="170" y="95">tab_id=observe</text>
  <path class="arrow" d="M280,70 L320,70"/>
  <rect class="box" x="320" y="20" width="75" height="100" rx="6"/>
  <text class="small" x="328" y="40">POST /api/</text>
  <text class="small" x="328" y="54">observe/mute/{id}</text>
  <text class="small" x="328" y="78">GET /api/</text>
  <text class="small" x="328" y="92">observe/stream/{id}</text>
  <text class="small" x="328" y="106">(SSE)</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">Response shape</text>
  <text class="small" x="92" y="205">mute → {ok} • stream → text/event-stream</text>
</svg>
```
