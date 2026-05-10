# h3dos-wire-voice-state-status-pill

## UI surface
`#voiceStatusPill` — the voice-state status pill in the topbar. Polls voice state on a timer and opens the Action Window on click.

## Tab
Topbar / Voice (pill is rendered in the topbar but routes to the Voice tab's Action Window detail).

## Backend endpoint
- `GET /api/voice/state` -> `{ status: "idle"|"listening"|"speaking"|..., muted: bool }` (drives pill text/color and click target)

## Files changed
Wire commit `3f73055` ("wire(voice-state-status-pill): voice pill polls state + click → Action Window", PR #35):

- `apps/web/app.js` (+30)
- `apps/web/index.html` (+1)
- `tests/e2e/wire-voice-state-status-pill.spec.ts` (+11, new)

Total: 3 files, 42 insertions.

## Status
**OPEN / IN-DEVELOP** — wire commit landed on `origin/develop` via PR #35; not on `origin/main`. A subsequent fix-merge `ce38644` reappended a slot-9 handler after a develop conflict.

## Branch & last commit
- Branch: `wire/voice-state-status-pill`
- Last commit: `ce38644 fix(PR35): merge develop into voice-state-status-pill, reappend slot 9 handler after conflict`
- Wire-feature commit: `3f73055`

## SVG diagram
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <rect width="400" height="250" fill="#0e1116"/>
  <rect x="10" y="20" width="130" height="60" rx="6" fill="#1f2937" stroke="#60a5fa"/>
  <text x="75" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">#voiceStatusPill</text>
  <text x="75" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">topbar pill (click)</text>
  <rect x="160" y="20" width="100" height="60" rx="6" fill="#1f2937" stroke="#fbbf24"/>
  <text x="210" y="50" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">app.js</text>
  <text x="210" y="65" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">poll + open AW</text>
  <rect x="280" y="20" width="110" height="60" rx="6" fill="#1f2937" stroke="#34d399"/>
  <text x="335" y="45" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="11">GET</text>
  <text x="335" y="62" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">/api/voice/state</text>
  <line x1="140" y1="50" x2="160" y2="50" stroke="#60a5fa" stroke-width="2" marker-end="url(#a)"/>
  <line x1="260" y1="50" x2="280" y2="50" stroke="#fbbf24" stroke-width="2" marker-end="url(#a)"/>
  <rect x="80" y="140" width="240" height="60" rx="6" fill="#1f2937" stroke="#a78bfa"/>
  <text x="200" y="165" fill="#e5e7eb" text-anchor="middle" font-family="sans-serif" font-size="12">Action Window kind=voice</text>
  <text x="200" y="183" fill="#9ca3af" text-anchor="middle" font-family="sans-serif" font-size="10">{ status, muted } -> rendered detail</text>
  <line x1="210" y1="80" x2="200" y2="140" stroke="#a78bfa" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#60a5fa"/></marker></defs>
</svg>
```
