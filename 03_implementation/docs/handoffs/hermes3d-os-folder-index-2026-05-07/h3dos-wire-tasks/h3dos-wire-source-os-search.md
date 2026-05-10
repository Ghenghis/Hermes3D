# h3dos-wire-source-os-search

## UI surface
`#sourceSearch` text input — filters `#sourceModuleList` (the Source OS module/source-stack list) by name as the user types.

## Tab
Source OS.

## Backend endpoint
None (purely client-side filter over the already-loaded module manifest in `apps/web/source-os.js`). Module list itself loads from `apps/web/source_manifest.json` plus `GET /api/sources/...` endpoints already wired by sibling tasks. INFERRED: no new endpoint introduced by this wire.

## Files changed
Wire commit `c06406e` ("wire(source-os-search): search box filters source module list"):

- `apps/web/index.html` (+1) — adds the search input
- `apps/web/source-os.js` (+8) — filter handler
- `tests/e2e/wire-source-os-search.spec.ts` (+16, new)

Total: 3 files, 25 insertions.

## Status
**OPEN** — wire commit on local branch only; not on `origin/main` and not detected on `origin/develop` from this checkout.

## Branch & last commit
- Branch: `wire/source-os-search`
- Last commit: `c06406e wire(source-os-search): search box filters source module list`

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="130" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="75" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#sourceSearch</text>
  <text x="75" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">text input</text>
  <rect x="160" y="20" width="120" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="220" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">source-os.js</text>
  <text x="220" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">filter handler</text>
  <rect x="290" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="340" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">module list</text>
  <text x="340" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">re-rendered</text>
  <line x1="140" y1="50" x2="160" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="280" y1="50" x2="290" y2="50" stroke="#fbbf24" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="140" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="165" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">source_manifest.json (preloaded)</text>
  <text x="200" y="183" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">no network call on each keystroke</text>
  <line x1="340" y1="80" x2="320" y2="140" stroke="#a78bfa" stroke-width="2"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
