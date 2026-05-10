# h3dos-wire-printers-discover-button

## UI surface
`#printersDiscover` button on the Printers tab. Click triggers a printer-discovery POST and surfaces a `#hermes-toast` toast with the result.

## Tab
Printers.

## Backend endpoint
- `POST /api/printers/discover` -> `{ discovered: <int> }` (from `tests/e2e/wire-printers-discover-button.spec.ts`).

## Files changed
Wire commit `3a0ee13` ("feat(wire/printers-discover-button): Discover button + toast", PR #28) + handler-fix `e02762a`:

- `apps/web/app.js` (+18) — POST + toast handler
- `apps/web/index.html` (+4) — adds `#printersDiscover` and `#hermes-toast` element
- `tests/e2e/wire-printers-discover-button.spec.ts` (+16, new)

Total: 3 files, 38 insertions.

## Status
**OPEN / IN-DEVELOP** — wire commit `3a0ee13` is on `origin/develop` via PR #28; not on `origin/main`. Subsequent fix `e02762a` rewires the click handler and re-adds the toast element after a develop merge.

## Branch & last commit
- Branch: `wire/printers-discover-button`
- Last commit: `e02762a fix(wire/printers-discover-button): wire click handler and add toast element`
- Wire-feature commit: `3a0ee13` (PR #28)

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="140" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="80" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#printersDiscover</text>
  <text x="80" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">button (click)</text>
  <text x="80" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">Printers tab</text>
  <rect x="170" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="220" y="50" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">app.js</text>
  <text x="220" y="65" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">fetch + toast</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="42" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">POST</text>
  <text x="340" y="58" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">/api/printers/</text>
  <text x="340" y="72" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="9">discover</text>
  <line x1="150" y1="50" x2="170" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="270" y1="50" x2="290" y2="50" stroke="#fbbf24" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="150" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="175" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#hermes-toast</text>
  <text x="200" y="193" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">"Discovered N printers"</text>
  <line x1="340" y1="80" x2="280" y2="150" stroke="#a78bfa" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
