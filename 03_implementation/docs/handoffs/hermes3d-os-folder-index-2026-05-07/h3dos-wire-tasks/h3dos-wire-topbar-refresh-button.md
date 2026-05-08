# h3dos-wire-topbar-refresh-button

- **UI surface**: Top-bar `#refreshBtn` (and optional `#dashboardRefreshBtn` via optional chaining)
- **Tab**: Global top-bar (re-pulls active tab's data via the existing `refresh()` orchestrator)
- **Backend endpoint**: INFERRED — `refresh()` re-runs every per-tab `render*()` fetch (e.g. `/api/jobs/list`, `/api/agents/list`, `/api/printers/list`, etc.). No new endpoint is added; the refresh button is a client-side fan-out.
- **Files changed** (commit `1634e66`):
  - `apps/web/app.js` — +16 / -1 lines (replaces bare `refresh()` with async loading-state wrapper that disables button and shows "Refreshing…")
  - `tests/e2e/wire-topbar-refresh-button.spec.ts` — +11 lines
- **Status**: OPEN (single feature commit; no PR-merge marker)
- **Branch & last commit**: `wire/topbar-refresh-button` @ `1634e66 wire(topbar-refresh-button): Refresh btn re-pulls active tab data`
- **Path**: `G:\Github\h3dos-wire-topbar-refresh-button`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#22d3ee; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#22d3ee; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#22d3ee"/></marker></defs>
  <rect class="box" x="10" y="40" width="110" height="60" rx="6"/>
  <text class="label" x="20" y="62">#refreshBtn</text>
  <text class="small" x="20" y="80">click → disable</text>
  <text class="small" x="20" y="95">"Refreshing…"</text>
  <path class="arrow" d="M120,70 L160,70"/>
  <rect class="box" x="160" y="40" width="100" height="60" rx="6"/>
  <text class="label" x="170" y="62">refresh()</text>
  <text class="small" x="170" y="80">await all</text>
  <text class="small" x="170" y="95">render*()</text>
  <path class="arrow" d="M260,70 L300,70"/>
  <rect class="box" x="300" y="20" width="95" height="100" rx="6"/>
  <text class="small" x="308" y="40">/api/jobs/list</text>
  <text class="small" x="308" y="56">/api/agents/list</text>
  <text class="small" x="308" y="72">/api/printers/list</text>
  <text class="small" x="308" y="88">/api/artifacts</text>
  <text class="small" x="308" y="104">… per active tab</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">Then: btn.disabled = false</text>
  <text class="small" x="92" y="205">Restored label, fresh tab data shown</text>
</svg>
```
