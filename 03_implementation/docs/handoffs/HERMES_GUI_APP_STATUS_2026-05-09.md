# W6-8 — GUI App Registry Status Surface

Date: 2026-05-09
Lane: W6-8 (lane 4 of the user's 5-lane finish order)
Owner: claude-w6-8-gui-app-status
Branch: claude/w6-8-gui-app-status (forked from feat/hermes3d-7-complete-gui-repo-wiring)

## Scope

Expose the 60-app registry status in the Hermes3D GUI. The lane consumes
the W6-7 backend's registry routes:

- `GET /api/source-os/modules`                  → list of app records
- `GET /api/source-os/modules/{id}`             → single-app detail
- `POST /api/source-os/modules/{id}/run-proof`  → request a fresh proof run

The original W6-8 brief referenced `/api/apps`; the canonical paths in
this checkout are `/api/source-os/modules`.

### Coordination with W6-5

W6-5 ships a typed domain client at
`03_implementation/ui/src/api/hermes3dClient.ts` with an `appsClient`
sibling. That branch had not yet merged into the upstream
`feat/hermes3d-7-complete-gui-repo-wiring` base when this lane started,
so to stay unblocked we ship a self-contained `appsClient.ts` here.
Both clients expose the same `appsClient` surface
(`listApps` / `getApp` / `runProof`), so when the W6-5 wrapper lands
upstream this module can be replaced with a single re-export without
touching call sites.

## Files shipped

| File | Purpose |
| --- | --- |
| `03_implementation/ui/src/types/app-registry.ts` | Type definitions for the registry (`RegistryApp`, `RegistryAppDetail`, `RegistryRunProofResponse`, lifecycle/lane/proof-status enums). |
| `03_implementation/ui/src/api/appsClient.ts` | Self-contained client for `/api/source-os/modules*`. Maps the backend record into the rich `RegistryApp` shape via `toRegistryApp()`. Ships `redactProofReason()` so the GUI never echoes raw `proof_command` output. Drop-in replaceable by a re-export from `hermes3dClient.ts` once W6-5 lands upstream. |
| `03_implementation/ui/src/components/AppRegistry/AppStatusPanel.tsx` | Table view of all registry apps. 30 s polling, ARIA grid semantics, run-proof / view-details / rollback row actions, toast feedback, loading skeleton, error toast. |
| `03_implementation/ui/src/components/AppRegistry/AppDetailPanel.tsx` | Single-app detail surface with full metadata, last 5 proof results, and rollback runbook link when supported. |
| `03_implementation/ui/src/tabs/AppRegistry.tsx` | Tab/page that switches between status panel and detail panel based on the `#apps[/<id>]` hash. Roots at `data-testid="apps-root"`. |
| `03_implementation/ui/src/main.tsx` | Hash gate: when the URL hash starts with `apps`, the registry surface renders standalone instead of the regular `<App />`. See "Mode integration" below for rationale. |
| `03_implementation/ui/tests/e2e/app-status.spec.ts` | Four Playwright specs: table render, run-proof toast, detail navigation + recent proofs, full-page 1920×1080 screenshot. |

## Component API

### `<AppStatusPanel />`

```ts
interface AppStatusPanelProps {
  /** Override navigation when "View details" is clicked.
   *  Defaults to setting window.location.hash to `apps/<id>`. */
  onNavigateDetail?: (appId: string) => void;
  /** Polling interval in ms; pass 0 to disable polling. Default 30 000. */
  pollIntervalMs?: number;
}
```

- Polls `GET /api/apps` every 30 s via `setInterval`. Aborts the in-flight
  fetch when the component unmounts so unit tests do not leak handles.
- On a fetch failure, retains the last known list and surfaces a
  non-blocking error banner; keeps polling so the UI self-heals when
  the backend recovers.
- Run-proof button posts `POST /api/apps/{id}/run-proof` and emits a
  toast (`status` role for success/info, `alert` role for errors).
- Rollback button is intentionally a navigation action (no destructive
  call from the table); it routes to the detail panel where the
  operator must read the runbook before continuing.

### `<AppDetailPanel />`

```ts
interface AppDetailPanelProps {
  appId: string;
  /** Optional close affordance; shown as "Back" button. */
  onClose?: () => void;
}
```

- Single load on mount with abort-on-unmount.
- Shows the app metadata as a `<dl>` plus the last 5 proof events.
- Rollback runbook link is rendered with `target="_blank" rel="noreferrer"`.

## Polling strategy

- Primary panel: 30 s interval (`POLL_INTERVAL_MS = 30_000`).
- Detail panel: single fetch + on-demand refresh when "Run proof" is
  clicked. No background poll — operators are typically reading the
  page momentarily.
- Both panels use `AbortController` to cancel any in-flight fetch on
  unmount or before re-issue, preventing setState-after-unmount warnings.

## Routing

- `#apps` → `AppStatusPanel`
- `#apps/<id>` → `AppDetailPanel` for that app

The hash gate is implemented in `main.tsx`. When the URL hash starts
with `apps`, the standalone shell renders instead of `<App />`. This
keeps the surface reachable while `App.tsx` and `store.ts` remain owned
by the W6-3 lane (lane 3). When W6-3 lands DashboardAdvanced, the hash
gate can be removed and `<AppStatusPanel />` embedded directly there.

## Mode integration TODO

> The brief asked for the panel to be embedded in DashboardAdvanced,
> which W6-3 owns. At the time this lane finished, `App.tsx` and
> `store.ts` were locked by `claude-w6-3-gui-dashboard`
> (`W6-3-GUI-DASHBOARD-MODES-2026-05-09`). To honour the brief's
> escape hatch ("if locked, ship as a standalone route … document the
> TODO"), we shipped:
>
> 1. `AppStatusPanel` and `AppDetailPanel` as standalone exports under
>    `components/AppRegistry/`. They have no implicit DashboardAdvanced
>    coupling and can be imported anywhere.
> 2. A hash gate in `main.tsx` that activates the standalone surface
>    on `#apps[/<id>]` so QA and the user can reach the registry today.
>
> **Follow-up for W6-3**: import `AppStatusPanel` from
> `components/AppRegistry/AppStatusPanel` and render it inside the
> Advanced dashboard mode. Once embedded, the hash gate in `main.tsx`
> can be removed.

## Reference Image-GUI comparison

The closest reference asset is
`Images-GUI/04-source-os/source-os-60-app-coverage-matrix.png`, which
shows the 60-app coverage matrix. The status panel intentionally does
not duplicate the matrix's checklist UX; it focuses on per-app proof
status, which the matrix does not. The two surfaces are complementary:

- **Coverage matrix (Source OS tab)**: which apps are mapped to which
  capabilities — answer to "do we cover X?".
- **App Registry (this lane)**: per-app live proof health — answer to
  "is X actually working right now?".

## Sources consulted (2 required)

1. **TanStack Table v8** docs — https://tanstack.com/table/v8.
   Considered, but the registry is small (≤ 60 rows) and the rest of
   the Hermes3D UI uses hand-rolled Tailwind tables. Adding the
   dependency would inflate the bundle without benefit. We adopt the
   conceptual columns/header-row split TanStack documents but render it
   directly with `<table>` + ARIA roles.
2. **W3C ARIA APG · Table pattern** —
   https://www.w3.org/WAI/ARIA/apg/patterns/table/. Followed for the
   `role="table"`, `role="rowgroup"`, `role="row"`, `role="rowheader"`,
   `role="columnheader"`, and `role="cell"` semantics.
   `aria-rowcount` / `aria-rowindex` are emitted so screen readers
   announce row position even when the panel paginates in a future
   iteration.

## Test coverage

Playwright spec: `03_implementation/ui/tests/e2e/app-status.spec.ts`

- **Test 1 — table render**: 3 mocked apps (stable / canary / frozen)
  visible, mixed lifecycle badges, rollback button gated on
  `rollback_supported`.
- **Test 2 — run-proof toast**: clicking the row's "Run proof" button
  hits the mocked POST and asserts the success toast appears with the
  app name.
- **Test 3 — detail navigation**: clicking "View details" navigates to
  `#apps/hermes-agent`, the detail panel mounts, and recent proofs
  render with their data-testids.
- **Test 4 — full-page screenshot at 1920×1080**: saved to
  `test-results/app-status-1920x1080.png`.

The repo does not currently have a Vitest install, so per-component
unit tests are folded into the Playwright spec which exercises render
+ interaction surfaces with mocked routes. If Vitest is added later,
the testids on every interactive element make a port straightforward.

## Security / no-fake contract

- The GUI never displays raw `proof_command` output. All proof reasons
  pass through `redactProofReason()` which strips control characters
  and caps length to 280 chars. The backend is also expected to redact;
  this is defense in depth.
- "Unknown" / missing values are rendered as an em-dash with
  `aria-label="value unknown"` rather than fabricated data.
- License "Unknown" is highlighted in amber so operators see the gap.

## Locks held during this lane

- `03_implementation/ui/src/components/AppRegistry/AppStatusPanel.tsx`
- `03_implementation/ui/src/components/AppRegistry/AppDetailPanel.tsx`
- `03_implementation/ui/src/tabs/AppRegistry.tsx`
- `03_implementation/ui/src/types/app-registry.ts`
- `03_implementation/ui/src/api/appsClient.ts`
- `03_implementation/ui/src/main.tsx`
- `03_implementation/ui/tests/e2e/app-status.spec.ts`
- `03_implementation/docs/handoffs/HERMES_GUI_APP_STATUS_2026-05-09.md`

All released at lane completion. `App.tsx`, `app/store.ts`, and
`app/routes.tsx` were intentionally not modified; W6-3 owns them.
