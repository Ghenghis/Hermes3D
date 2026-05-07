# h3dos-wire-action-window-history

## UI surface
Back/forward navigation buttons inside the Action Window panel — adds a history ring so users can traverse previously-opened detail panes (printer -> job -> printer).

## Tab
Action Window (cross-cutting overlay; not its own tab — invoked from Dashboard, Printers, Jobs, Agents, Observe, Learning).

## Backend endpoint
None (client-side history ring inside `apps/web/action-window.js`). The Action Window itself is populated by `GET /api/workspace`. INFERRED: no new server endpoint is added.

## Files changed
Wire commit `404e048` ("wire(action-window-history): back/forward history ring on Action Window") and PR-merge commit `4871302`:

- `apps/web/action-window.js` (+54 / -2)
- `tests/e2e/wire-action-window-history.spec.ts` (+29, new)

Total: 2 files, 81 insertions, 2 deletions.

## Status
**OPEN / IN-DEVELOP** — wire commit landed on `origin/develop` (PR #34) but not yet on `origin/main`.

## Branch & last commit
- Branch: `wire/action-window-history`
- Last commit: `369a0c9 merge(develop): cascade x2 — take develop's app.js (includes observe camera + voice + learning slots)`
- Wire-feature commit: `404e048` / merged via `4871302` (PR #34)

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="120" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="70" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">Action Window</text>
  <text x="70" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">[Back] [Fwd]</text>
  <rect x="150" y="20" width="120" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="210" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">history ring</text>
  <text x="210" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">action-window.js</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">render pane</text>
  <text x="340" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">prev/next entry</text>
  <line x1="130" y1="50" x2="150" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="270" y1="50" x2="290" y2="50" stroke="#34d399" stroke-width="2" marker-end="url(#a)"/>
  <text x="200" y="120" fill="#9ca3af" font-family="sans-serif" font-size="11">Initial pane content sourced from:</text>
  <rect x="80" y="140" width="240" height="50" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="165" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">GET /api/workspace</text>
  <text x="200" y="180" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">printers / jobs / events / approvals</text>
  <text x="200" y="220" fill="#6b7280" text-anchor="middle" font-family="sans-serif" font-size="10">No new server endpoint. Pure client-side history.</text>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
