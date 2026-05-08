# h3dos-wire-dashboard-queue-list

## UI surface
`#dashboardJobs .job-card` — each job card in the Dashboard's job-queue panel. Click opens the Action Window with `data-kind=job` and the job's title.

## Tab
Dashboard.

## Backend endpoint
- `GET /api/workspace` -> includes `jobs[]` (id, title, state, target_printer_id) (read-only; click is fully client-side; no per-click POST).

## Files changed
Wire commit `9b6503d` ("wire(dashboard-queue-list): job queue → Action Window"):

- `apps/web/app.js` (+22) — click handler that wires `.job-card` -> Action Window
- `tests/e2e/wire-dashboard-queue-list.spec.ts` (+44, new)

Total: 2 files, 66 insertions.

## Status
**OPEN** — wire commit on local branch only; not on `origin/main` and not detected on `origin/develop` from this checkout.

## Branch & last commit
- Branch: `wire/dashboard-queue-list`
- Last commit: `9b6503d wire(dashboard-queue-list): job queue → Action Window`

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="140" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="80" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#dashboardJobs</text>
  <text x="80" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">.job-card (click)</text>
  <text x="80" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">Dashboard tab</text>
  <rect x="170" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="220" y="50" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">app.js</text>
  <text x="220" y="65" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">openActionWindow</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">GET</text>
  <text x="340" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">/api/workspace</text>
  <text x="340" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">jobs[]</text>
  <line x1="150" y1="50" x2="170" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="290" y1="50" x2="270" y2="50" stroke="#34d399" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="150" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="175" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">Action Window</text>
  <text x="200" y="193" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">data-kind=job, data-tab-id=dashboard</text>
  <line x1="220" y1="80" x2="200" y2="150" stroke="#a78bfa" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
