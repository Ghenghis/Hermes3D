# h3dos-wire-agents-list

- **UI surface**: Agents list panel `#agentsList` — `.agent-card` row click, plus initial render of the list
- **Tab**: Agents (`#page-agents`)
- **Backend endpoint**:
  - `GET /api/agents/list` — populates the list
  - `GET /api/agents/<id>/health` — Action Window primary action "Check Health"
  - `POST /api/agents/<id>/dispatch` — Action Window primary action "Dispatch Task"
- **Files changed** (commit `05cda10`):
  - `apps/web/app.js` — +41 lines (`renderAgentsList()` async fetch, click delegation → ActionWindow)
  - `apps/web/index.html` — +9 lines (`#agentsList` panel inside `#page-agents`)
  - `tests/e2e/wire-agents-list-actionwindow.spec.ts` — +15 lines
- **Status**: OPEN (single feature commit on top of merged base; no PR-merge marker observed in branch log)
- **Branch & last commit**: `wire/agents-list-actionwindow` @ `05cda10 wire(agents-list-actionwindow): agents list -> Action Window`
- **Path**: `G:\Github\h3dos-wire-agents-list`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#34d399; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#34d399; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#34d399"/></marker></defs>
  <rect class="box" x="10" y="20" width="110" height="55" rx="6"/>
  <text class="label" x="20" y="42">#agentsList</text>
  <text class="small" x="20" y="58">render (load)</text>
  <path class="arrow" d="M120,45 L260,45"/>
  <rect class="box" x="260" y="20" width="130" height="55" rx="6"/>
  <text class="small" x="270" y="42">GET /api/agents/list</text>
  <text class="small" x="270" y="58">→ Agent[]</text>
  <rect class="box" x="10" y="100" width="110" height="55" rx="6"/>
  <text class="label" x="20" y="122">.agent-card</text>
  <text class="small" x="20" y="138">click → AW</text>
  <path class="arrow" d="M120,125 L160,125"/>
  <rect class="box" x="160" y="100" width="100" height="55" rx="6"/>
  <text class="small" x="170" y="125">kind=agent</text>
  <text class="small" x="170" y="142">tab_id=agents</text>
  <path class="arrow" d="M260,125 L300,125"/>
  <rect class="box" x="300" y="80" width="95" height="100" rx="6"/>
  <text class="small" x="308" y="100">/api/agents/</text>
  <text class="small" x="308" y="115">{id}/health</text>
  <text class="small" x="308" y="140">/api/agents/</text>
  <text class="small" x="308" y="155">{id}/dispatch</text>
  <rect class="box" x="80" y="200" width="240" height="40" rx="6"/>
  <text class="small" x="92" y="225">Response: agent[] / health{} / dispatch{ok}</text>
</svg>
```
