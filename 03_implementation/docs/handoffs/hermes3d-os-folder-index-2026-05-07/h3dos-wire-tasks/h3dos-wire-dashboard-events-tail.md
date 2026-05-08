# h3dos-wire-dashboard-events-tail

## UI surface
`#dashboardEvents .event-card` — each event row in the Dashboard's "events tail" panel. Click opens the Action Window for that event.

## Tab
Dashboard.

## Backend endpoint
- `GET /api/workspace` -> includes `events[]` (`event_type`, `message`, `created_at`). No new event-detail endpoint; the click renders from the already-fetched event payload.

## Files changed
Wire commit `d9e908d` ("feat(wire/dashboard-events-tail): event card click → Action Window", PR #30):

- `tests/e2e/wire-dashboard-events-tail.spec.ts` (+11, new)

Plus earlier branch commit `3cf7a54 fix(wire/dashboard-events-tail): add click handler for event cards` which added the actual handler in `apps/web/app.js` (subsequently merged into develop and rescued by `439699c fix(develop): restore #dashboardEvents click handler lost during -X theirs merge`).

## Status
**OPEN / IN-DEVELOP** — PR #30 commit `d9e98ed` is on `origin/develop`; not on `origin/main`. Note: the click handler was lost once during a develop merge and had to be restored in `439699c`.

## Branch & last commit
- Branch: `wire/dashboard-events-tail`
- Last commit: `8f7b191 Merge remote-tracking branch 'origin/develop' into wire/dashboard-events-tail`
- Wire-feature commit: `d9e908d` (PR #30); handler patch `3cf7a54`; cascade-restore `439699c`

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="140" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="80" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#dashboardEvents</text>
  <text x="80" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">.event-card (click)</text>
  <text x="80" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">Dashboard tab</text>
  <rect x="170" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="220" y="50" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">app.js</text>
  <text x="220" y="65" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">openActionWindow</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">GET</text>
  <text x="340" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">/api/workspace</text>
  <text x="340" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">events[]</text>
  <line x1="150" y1="50" x2="170" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="290" y1="50" x2="270" y2="50" stroke="#34d399" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="150" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="175" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">Action Window kind=event</text>
  <text x="200" y="193" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">{ event_type, message, created_at }</text>
  <line x1="220" y1="80" x2="200" y2="150" stroke="#a78bfa" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
