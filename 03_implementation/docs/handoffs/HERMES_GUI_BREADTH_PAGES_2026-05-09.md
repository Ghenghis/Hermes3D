# Hermes3D GUI Breadth Pages — W8-2 (2026-05-09)

Agent: `claude-w8-2-gui-breadth`
Branch: `claude/w8-2-gui-settings-approvals-apps`
Base: `feat/hermes3d-7-complete-gui-repo-wiring`

## Scope

Settings, Approvals, and per-app detail surfaces, plus the Apps registry tab
they hang off. Built from the visual reference at
`G:/Github/h3d-gui-wiring-codex/Images-GUI/` (PR #128).

## Routes added (hash-based — repo convention)

- `#settings` — General subtab is now the default landing pane.
- `#settings` → General / Providers / Agents / **MCP** (new) / Printers /
  Environment / Update Center / About.
- `#approvals` — pending queue with **Approve / Deny / Defer** actions and a
  collapsible **file scope** disclosure per row. 5s polling cadence (override
  via `window.__HERMES_APPROVALS_POLL_MS__`).
- `#apps` — 60-app registry table (new tab in the sidebar).
- `#apps/<id>` — per-app detail with status, tested versions, last-10 proof
  history, and rollback (when `rollback_supported`). Hash sub-routing is
  parsed inside `tabs/AppRegistry.tsx`; `tabIdFromHash` was extended to keep
  the head segment when the hash contains a `/`.

We did NOT introduce `react-router-dom`. The existing AppShell uses hash
routing exclusively, and the brief explicitly notes "(or `/#settings` per
existing W5-3 finding)". This keeps the bundle weight unchanged and matches
the rest of the codebase.

## File map

```
03_implementation/ui/
├── src/
│   ├── App.tsx                                  (apps tab + nested-hash sync)
│   ├── api/
│   │   ├── adapters.live.ts                     (deferApprovalLive)
│   │   ├── adapters.ts                          (deferApproval API)
│   │   └── appsClient.ts                        (NEW — registry façade)
│   ├── app/
│   │   ├── routes.tsx                           (Apps tab def)
│   │   └── store.ts                             (apps + nested-hash parse)
│   ├── components/
│   │   ├── AppRegistry/
│   │   │   ├── AppDetailPanel.tsx               (NEW)
│   │   │   └── AppStatusPanel.tsx               (NEW)
│   │   └── settings/
│   │       ├── GeneralSubtab.tsx                (NEW)
│   │       ├── McpSubtab.tsx                    (NEW)
│   │       └── SettingsPage.tsx                 (wires General + MCP)
│   ├── tabs/
│   │   ├── AppRegistry.tsx                      (NEW)
│   │   └── Approvals.tsx                        (defer + file scope + 5s)
│   └── types/
│       ├── app-registry.ts                      (NEW)
│       └── approval.ts                          (deferred + fileScope)
├── tests/
│   ├── e2e/
│   │   ├── _helpers.ts                          (apps fixture)
│   │   └── gui-breadth-pages.spec.ts            (NEW Playwright spec)
│   └── unit/
│       ├── AppDetailPanel.test.tsx              (NEW)
│       ├── Approvals.test.tsx                   (NEW)
│       ├── GeneralSubtab.test.tsx               (NEW)
│       ├── McpSubtab.test.tsx                   (NEW)
│       ├── appsClient.test.ts                   (NEW)
│       └── setup.ts                             (NEW Vitest setup)
├── package.json                                 (Vitest + RTL + jsdom)
└── vitest.config.ts                             (NEW)
```

## Reference image-GUI matches

Source pack: `G:/Github/h3d-gui-wiring-codex/Images-GUI/`

- Settings layout: `03-settings-voice/settings-subtabs-all.png` — left rail
  with Providers / Agents / Printers / Environment subtabs. We added
  **General** at the top and **MCP** between Agents and Printers; the
  existing rail UX (icon + label + descriptor + selected accent) is
  preserved.
- Approvals queue: `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png`
  — pending list with status pill, title, requested-at metadata, and inline
  action buttons. The three-action pattern (Approve / Deny / Defer) extends
  the previous two-action layout without altering the row chrome.
- App detail: `04-source-os/source-os-60-app-coverage-matrix.png` — apps as
  rows with versions, lane, license; the per-app detail mirrors the right-
  hand panel from that image (header → status → versions → proof history).

## Mock-or-live data sources

| Surface | Live route | Fallback |
|---------|------------|----------|
| Settings General theme | `GET /api/settings`, `PUT /api/settings` | localStorage `h3d.settings.general.*` |
| Settings MCP locks | `GET /api/mcp/locks` | empty list + honest error banner |
| Approvals pending | `GET /api/approvals?status=pending` | empty list |
| Approvals defer | `POST /api/approvals/{id}/defer` | error toast on failure |
| Apps list | `GET /api/apps` (preferred) → fallback `GET /api/source-os/modules` | typed `AppsClientError` |
| App detail | `GET /api/apps/{id}` → fallback `GET /api/source-os/modules/{id}` | typed `AppsClientError` |
| Run proof | `POST /api/apps/{id}/run-proof` → fallback `POST /api/source-os/modules/{id}/run-proof` | non-2xx → `accepted: false` with redacted reason |

No mock data is invented at runtime. When both endpoints are unavailable the
GUI surfaces a real "blocked" alert per the existing no-fake helper rules.

## Test coverage

Unit (Vitest + Testing Library):

- `appsClient.test.ts` — mapper unknowns, fallback ordering, `AppsClientError`.
- `AppDetailPanel.test.tsx` — header, versions, rollback gating, error state,
  Run-proof click path.
- `Approvals.test.tsx` — file scope visibility, three actions present, defer
  flow calls `deferApproval`, empty state.
- `GeneralSubtab.test.tsx` — initial theme load, save-disabled-until-dirty,
  `saveSettings({theme})`, localStorage persistence, error toast.
- `McpSubtab.test.tsx` — row rendering, stale tally, error state, empty state.

E2E (`tests/e2e/gui-breadth-pages.spec.ts`):

- Settings → General + MCP subtabs render and switch; screenshot per pane.
- Approvals → pending items render with file scope; defer flow happy path.
- Apps → list renders, `View details` navigates to `#apps/<id>`, detail
  shows tested versions + rollback section + proof history; screenshots at
  each step.
- Asserts no fake/placeholder phrases and no console errors per spec.

## Sources cited

1. **WAI-ARIA Authoring Practices** — `https://www.w3.org/WAI/ARIA/apg/`
   - Form pattern (radiogroup + status messages) for `GeneralSubtab`.
   - Table pattern (rowgroup + columnheader semantics) for `McpSubtab` and
     `AppStatusPanel`.
   - Region/Section pattern for `AppDetailPanel` ARIA labels.

2. **React Router DOM concepts** — `https://reactrouter.com/en/main/start/concepts`
   - Hash routing rationale; we deliberately avoid adding the dep and stay
     on the existing AppShell hash convention. Cited so the next agent
     knows the decision was conscious, not accidental.

## Coordination

- **W6-3** (Dashboard modes) — untouched.
- **W6-4** (ActionWindow + TaskMonitor) — untouched.
- **W6-5** (API client) — `appsClient` is W8-2's GUI-side façade. If W6-5
  later ships a canonical `appsClient` under `hermes3dClient.ts`, the W8-2
  client can be re-exported as a thin wrapper without changing GUI imports.
- **W6-7** (60-app registry route) — when the live `/api/apps` route lands,
  the appsClient automatically prefers it over `/api/source-os/modules`.

## Verification (next steps for the integrator)

```bash
cd 03_implementation/ui
npm install
npm run test:unit            # Vitest, all *.test.tsx in tests/unit
npm run lint                 # tsc --noEmit
npm run build                # tsc -b && vite build
npm run test:breadth         # Playwright on a Vite-preview prod build
```

Local verification result on this branch:

- `npm run test:unit` — **5 files, 21 tests, all green**.
- `npm run lint` — clean.
- `npm run build` — clean (one pre-existing chunk-size advisory).
- `npm run test:breadth` — **3 Playwright specs, all green**, screenshots
  written to `test-results/e2e/screenshots/`.

The breadth spec uses a separate `playwright.breadth.config.ts` that runs
against `vite preview` (production build) rather than `vite dev`. This sidesteps
a Vite 8 + `@vitejs/plugin-react` 6 dev-server quirk where Fast Refresh wraps
non-component callbacks (e.g. `TABS.filter((tab) => …)` inside `routes.tsx`)
with `$RefreshReg$` calls before injecting the runtime helper, leading to
`ReferenceError: $RefreshReg$ is not defined` at module-eval time. Production
builds disable Fast Refresh entirely, so the wrapping never happens.

The full live e2e (`npm run test:visual`) remains driven by
`scripts/start-e2e-stack.mjs` which boots the Python backend; the breadth
spec is intentionally orthogonal to that stack.

## Lock release

LOCK OWNER: `claude-w8-2-gui-breadth`
Lock scope was constrained to W8-2 files; locks have been released at
end-of-task.
