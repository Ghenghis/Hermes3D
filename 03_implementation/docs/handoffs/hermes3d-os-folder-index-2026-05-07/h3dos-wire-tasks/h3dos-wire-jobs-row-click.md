# h3dos-wire-jobs-row-click

- **UI surface**: Job card row click (`#page-jobs .job-card`) — gated to `#page-jobs` to avoid stealing dashboard duplicate
- **Tab**: Jobs
- **Backend endpoint**:
  - `POST /api/jobs/<id>/cancel` — Action Window primary action "Cancel"
  - `POST /api/jobs/<id>/retry` — Action Window primary action "Retry"
- **Files changed** (across 3 commits in branch):
  - `d8cfd52`: `apps/web/app.js` — +28 lines, `tests/e2e/wire-jobs-row-click-actionwindow.spec.ts` — +14 lines
  - `01446d6`: scope-fix to `#page-jobs`
  - `543a2c6`: `apps/web/app.js` — +1 line (gate handler to `#page-jobs`)
- **Status**: MERGED (PR #38 visible in companion branches: `feat(wire/jobs-row-click-actionwindow): job row → Action Window (#38)`); this worktree carries the original commits + two follow-up scope fixes
- **Branch & last commit**: `wire/jobs-row-click-actionwindow` @ `543a2c6 fix(PR38): gate job-card click handler to #page-jobs to avoid stealing dashboard clicks`
- **Path**: `G:\Github\h3dos-wire-jobs-row-click`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#facc15; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#facc15; stroke-width:1.5; fill:none; marker-end:url(#a); }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#facc15"/></marker></defs>
  <rect class="box" x="10" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="20" y="62">#page-jobs</text>
  <text class="small" x="20" y="80">.job-card</text>
  <text class="small" x="20" y="95">click (scoped)</text>
  <path class="arrow" d="M130,70 L170,70"/>
  <rect class="box" x="170" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="180" y="62">ActionWindow</text>
  <text class="small" x="180" y="80">kind=job</text>
  <text class="small" x="180" y="95">tab_id=jobs</text>
  <path class="arrow" d="M290,70 L320,70"/>
  <rect class="box" x="320" y="20" width="75" height="100" rx="6"/>
  <text class="small" x="328" y="40">POST /api/</text>
  <text class="small" x="328" y="54">jobs/{id}/cancel</text>
  <text class="small" x="328" y="78">POST /api/</text>
  <text class="small" x="328" y="92">jobs/{id}/retry</text>
  <rect class="box" x="80" y="160" width="240" height="60" rx="6"/>
  <text class="label" x="92" y="185">Response: { ok: true, job: {...} }</text>
  <text class="small" x="92" y="205">+ status_pill reflects job state</text>
</svg>
```
