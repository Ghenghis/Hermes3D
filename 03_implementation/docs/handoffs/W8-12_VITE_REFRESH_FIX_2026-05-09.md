# W8-12 Vite Fast-Refresh Fix — 2026-05-09

## Lane

**Agent**: W8-12
**Lock owner**: `claude-w8-12-vite-fix`
**Task ID**: `W8-12-VITE-REFRESH-FIX-2026-05-09`
**Base branch**: `feat/hermes3d-7-complete-gui-repo-wiring`
**Working branch**: `claude/w8-12-vite-refresh-fix`

## Problem

W6-6's first visual-proof run failed all 11 live targets with the SPA never
mounting. Boot diagnostics revealed two cascading errors thrown at module
evaluation time on every `.tsx` user module:

```
ReferenceError: $RefreshReg$ is not defined
ReferenceError: $RefreshSig$ is not defined
```

These are global stubs that `@vitejs/plugin-react` is supposed to install on
`window` BEFORE any user module evaluates, via a virtual preamble injected
into `index.html`'s `transformIndexHtml` hook.

## Root cause

Two independent bugs, both fixed:

### Bug A (Class 2 — mixed React + non-React exports)

`03_implementation/ui/src/app/routes.tsx` exported only types and data
arrays (`TabDef`, `TABS`, `PRIMARY_TABS`) — zero React components, zero
JSX. The `.tsx` extension caused `@vitejs/plugin-react`'s OXC refresh
filter (default `/\.(mdx|js|jsx|ts|tsx)$/`) to instrument the file with
refresh-wrapper calls that referenced undefined globals.

### Bug B (Class 4 — react-refresh runtime not loaded)

In `vite@8.0.10` + `@vitejs/plugin-react@6.0.1`, the `transformIndexHtml`
preamble injection does not fire reliably for the plain SPA path. The
served `index.html` lacked the inline `<script type="module">` that
defines `window.$RefreshReg$` and `window.$RefreshSig$`. The
`@vitejs/plugin-react/preamble` virtual module also returned empty
content during testing because its `isEnabled()` closure read
`skipFastRefresh === true` (timing/closure mismatch with `viteBabel`'s
`configResolved` hook in the new Vite-8 environment system).

## Fix

### Fix A — `git mv routes.tsx routes.ts`

Renamed `03_implementation/ui/src/app/routes.tsx` → `routes.ts`. The file
contains zero JSX and zero React component exports, so the `.tsx`
extension was gratuitous. Moving it out of the React-refresh transform
pipeline removes the bogus refresh-wrapper injection. All 5 importers
(`App.tsx`, `Sidebar.tsx`, `SimpleHermesDashboard.tsx`, `Autopilot.tsx`,
`Roadmap.tsx`) use bare paths (no extension) so consumers needed no
changes.

Commit: `1cca312`

### Fix B — `index.html` inline preamble stubs

Added a plain (non-`type="module"`) `<script>` block to
`03_implementation/ui/index.html`, BEFORE the `main.tsx` ESM script:

```html
<script>
  window.$RefreshReg$ = function () {};
  window.$RefreshSig$ = function () {
    return function (type) { return type; };
  };
</script>
```

These match exactly what the plugin's `preambleCode` installs (see
`node_modules/@vitejs/plugin-react/dist/index.js` lines 8-11). The
`injectIntoGlobalHook` import from `/@react-refresh` is omitted because
`/@react-refresh` is a vite-dev-only middleware route; the plugin's
per-module refresh wrapper imports it itself, so we do not need the HTML
preamble to import it.

In production:
- `plugin-react` sets `skipFastRefresh = true`
- the OXC refresh-wrapper is never emitted
- the stubs are unreferenced dead code (~150 bytes in `dist/index.html`)
- zero `RefreshReg`/`RefreshSig` references in the production JS bundle
  (verified via grep on `dist/assets/*.js` after `vite build`)

## Verification

### SPA mounts (boot-check)

A temporary `tests/visual/boot-check.spec.ts` (later removed) confirmed:
- HTTP 200 on `/`
- ZERO `$RefreshReg$` or `$RefreshSig$` page errors
- `#root` element has content after mount

PASS at 2.3s.

### `npm run lint` (TypeScript)

```
> hermes3d-ui-final@0.1.0 lint
> tsc --noEmit
```

Exit 0, zero errors.

### `vite build` (production)

```
✓ 2189 modules transformed.
dist/index.html                     1.96 kB │ gzip:   0.98 kB
dist/assets/index-BcULLGw-.css     46.69 kB │ gzip:   9.88 kB
dist/assets/index-y1zl7lju.js   1,033.16 kB │ gzip: 265.36 kB
✓ built in 1.70s
```

`grep -c "RefreshReg\|RefreshSig" dist/assets/*.js` → `0`

### W6-6 visual-proof harness (the original blocker)

| Run     | total | match | diff | error | skipped-future | error class |
|---------|-------|-------|------|-------|----------------|-------------|
| Before  | 31    | 0     | 0    | 11    | 20             | "wait_test_id dashboard-root mounts" — SPA never mounted |
| After   | 31    | 0     | 0    | 11    | 20             | timeouts + W6-6 snapshotPathTemplate bug — SPA mounts, harness path config issue |

Critically: **no `$RefreshReg$` / `$RefreshSig$` errors in any row** after
the fix. The remaining 11 errors are downstream issues (W6-6 harness path
template, networkidle timeouts on the GUI API) outside W8-12 scope.

## Sources

1. `@vitejs/plugin-react@6.0.1` README — "Initialize HMR runtime in
   client entrypoint":
   <https://github.com/vitejs/vite-plugin-react/blob/plugin-react@6.0.1/packages/plugin-react/README.md#initialize-hmr-runtime-in-client-entrypoint>
   Documents that SSR/non-`transformIndexHtml` apps must import the
   preamble at the entry. Confirms the preamble defines the global
   `$RefreshReg$` / `$RefreshSig$` stubs.

2. React Fast-Refresh package:
   <https://github.com/facebook/react/tree/main/packages/react-refresh>
   Confirms `react-refresh` "implements the wiring necessary to
   integrate Fast Refresh into bundlers" — bundler integrations are
   responsible for installing the runtime hooks before user component
   modules evaluate.

## Locks

| File                                              | Action  |
|---------------------------------------------------|---------|
| `03_implementation/ui/src/app/routes.tsx`         | locked then released after rename |
| `03_implementation/ui/src/app/routes.ts`          | locked then released after rename |
| `03_implementation/ui/src/main.tsx`               | locked, no edit needed (reverted), released |
| `03_implementation/ui/index.html`                 | locked, edited, released |

`vite.config.ts` and `package.json` were skipped after handoff was
declined-by-design (W6-3 / W6-4 still own them; the index.html-only fix
made handoff unnecessary).

## Hermes evidence chain

- Hermes evidence chain: PASS
- Task ID: `W8-12-VITE-REFRESH-FIX-2026-05-09`
- hermes_run_gate: SPA boot-check PASS, npm lint PASS, vite build PASS,
  visual-proof harness re-run shows fix is upstream-resolved (downstream
  W6-6 errors remain)
- Stacked-on: `feat/hermes3d-7-complete-gui-repo-wiring`
- Cherry-picks W6-6 commits `9d9b653` + `43c4fbb` so the visual-proof
  harness can verify the fix. W6-6's PR is opened separately (Part B).

## Files changed

- `03_implementation/ui/src/app/routes.tsx` → `03_implementation/ui/src/app/routes.ts` (rename)
- `03_implementation/ui/index.html` (4 lines of inline `<script>` stubs + 21 lines of comment explaining why)
- `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` (regenerated by harness re-run)
- `03_implementation/docs/handoffs/W8-12_VITE_REFRESH_FIX_2026-05-09.md` (this file)
