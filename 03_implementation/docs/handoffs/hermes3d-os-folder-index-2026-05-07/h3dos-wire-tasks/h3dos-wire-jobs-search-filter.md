# h3dos-wire-jobs-search-filter

## UI surface
`#jobsSearch` text input + `.status-chip` status chips inside `#page-jobs`. Filters the job list by title substring + by job state ("queued" / "running" / "done" / etc.).

## Tab
Jobs.

## Backend endpoint
- `GET /api/workspace` -> already provides `jobs[]` for the Jobs page. Filter is purely client-side; no new server endpoint.

## Files changed
Wire commit `4b60810` ("wire(jobs-search-filter): search + status filter on jobs list", PR #32) plus a develop-merge fix `44f354e`:

- `apps/web/app.js` (+27 / -1) — filter handler against `#jobsSearch` value and active status chip
- `tests/e2e/wire-jobs-search-filter.spec.ts` (+15, new)

Total: 2 files, 41 insertions, 1 deletion.

## Status
**OPEN / IN-DEVELOP** — wire commit landed on `origin/develop` via PR #32, not on `origin/main`. Fix-merge `44f354e` rescoped selectors to `#page-jobs`/`#jobsSearch`/`.status-chip` after develop conflict.

## Branch & last commit
- Branch: `wire/jobs-search-filter`
- Last commit: `44f354e fix(PR32): merge develop, update search IDs to #jobsSearch/.status-chip, scope spec to #page-jobs`
- Wire-feature commit: `4b60810` (PR #32)

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="140" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="80" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#jobsSearch</text>
  <text x="80" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">+ .status-chip</text>
  <text x="80" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">Jobs tab</text>
  <rect x="170" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="220" y="50" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">app.js</text>
  <text x="220" y="65" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">filter handler</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">GET</text>
  <text x="340" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">/api/workspace</text>
  <text x="340" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">jobs[]</text>
  <line x1="150" y1="50" x2="170" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="290" y1="50" x2="270" y2="50" stroke="#34d399" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="150" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="175" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#page-jobs .job-card</text>
  <text x="200" y="193" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">filtered subset rendered</text>
  <line x1="220" y1="80" x2="200" y2="150" stroke="#a78bfa" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
