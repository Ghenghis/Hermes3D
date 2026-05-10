# Hermes3D-OS GUI Wiring Layer (W6-5)

Owner: claude-w6-5-gui-wiring · 2026-05-09 · branch `claude/w6-5-gui-wiring-layer`

This document maps the GUI wiring layer landed in W6-5: a typed client
wrapper plus seven React hooks bridging the React/Vite dashboard
(`03_implementation/ui/`) to the FastAPI backend
(`03_implementation/src/hermes3d/api/`).

## Files added

- `03_implementation/ui/src/api/hermes3dClient.ts` — typed domain clients
- `03_implementation/ui/src/api/hermes3dClient.test.ts` — `node --test` unit suite
- `03_implementation/ui/src/hooks/_useQuery.ts` — React Query-shape primitives
- `03_implementation/ui/src/hooks/useAgents.ts`
- `03_implementation/ui/src/hooks/useOpenCode.ts`
- `03_implementation/ui/src/hooks/useOpenHands.ts`
- `03_implementation/ui/src/hooks/useProviders.ts`
- `03_implementation/ui/src/hooks/useMcp.ts`
- `03_implementation/ui/src/hooks/useApps.ts`
- `03_implementation/ui/src/hooks/useRecovery.ts`
- `03_implementation/ui/src/hooks/index.ts` — barrel export
- `03_implementation/ui/src/hooks/useAgents.test.ts` — hook-shape smoke
- `03_implementation/ui/src/components/agents/HermesAgentBanner.tsx`
- `03_implementation/ui/tests/e2e/gui-wiring-smoke.spec.ts`

## Files updated

- `03_implementation/ui/src/components/layout/Sidebar.tsx` — wires
  `<HermesAgentBanner compact />` into the OS header. Single existing
  component update — TopBar.tsx, Dashboard mode components, Action
  Window, Task Monitor are intentionally untouched (W6-3/W6-4 own them).
- `03_implementation/ui/tsconfig.json` — adds
  `"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx"]` so the
  `node:test`-based unit tests don't trip `tsc --noEmit`.

## API surface mapping (UI domain → backend route)

| Hook                 | Client method                      | HTTP method + path                                           |
| -------------------- | ---------------------------------- | ------------------------------------------------------------ |
| `useAgentUpdateStatus` | `agentsClient.getUpdateStatus`     | `GET /api/agents/update/status`                              |
| `useAgents`          | `agentsClient.listAgents`          | `GET /api/agents`                                            |
| `useAgentHealth`     | `agentsClient.health`              | `GET /api/agents/health`                                     |
| `useAgentMutations.backup`     | `agentsClient.backup`     | `POST /api/agents/update/backup`                             |
| `useAgentMutations.stagedUpdate` | `agentsClient.stagedUpdate` | `POST /api/agents/update/staged`                       |
| `useAgentMutations.rollback`   | `agentsClient.rollback`   | `POST /api/agents/update/rollback`                           |
| `useOpenCode`        | `openCodeClient.getReadiness`      | `GET /api/code-operator/cli-runners`                         |
|                      | `openCodeClient.getSandboxReadiness` | `GET /api/code-operator/sandbox/readiness`                 |
| `useOpenCodeMutations.preflight` | `openCodeClient.preflight` | `GET /api/code-operator/cli-runners/preflight?runner_id=opencode` (POST fallback) |
| `useOpenCodeMutations.spawnBoundedTask` | `openCodeClient.spawnBoundedTask` | `POST /api/code-operator/cli-runners/run-bounded-task` (`runner_id="opencode"`) |
| `useOpenHands*`      | mirrored against `runner_id="openhands"` | same paths                                          |
| `useProviders.providers` | `providersClient.list`         | `GET /api/providers/health`                                  |
| `useProviders.teams` | `providersClient.getTeamReadiness` | `GET /api/code-operator/teams/readiness`                     |
| `useProviderMutations.smoke` | `providersClient.smoke`    | `POST /api/code-operator/providers/smoke`                    |
| `useMcp.readiness`   | `mcpClient.readiness`              | `GET /api/code-operator/mcp-locks/readiness`                 |
| `useMcp.locks`       | `mcpClient.listLocks`              | `GET /api/code-operator/mcp-locks/state`                     |
| `useMcpMutations.heartbeat` | `mcpClient.heartbeat`       | `POST /api/code-operator/mcp-locks/heartbeat`                |
| `useApps`            | `appsClient.list`                  | `GET /api/source-os/modules`                                 |
| `useAppDetail(id)`   | `appsClient.detail`                | `GET /api/source-os/modules/{id}`                            |
| `useRecovery.runs`   | `recoveryClient.listRuns`          | `GET /api/code-operator/recovery/runs`                       |
| `useRecovery.state`  | `recoveryClient.getState`          | `GET /api/code-operator/recovery/state`                      |
| `useRecoveryMutations.proposeFailure` | `recoveryClient.proposeFailure` | `POST /api/code-operator/recovery/record-failure` |
| `useRecoveryMutations.markOutcome` | `recoveryClient.markOutcome` | `POST /api/code-operator/recovery/mark-outcome`        |

The MCP endpoints proxy the stdio-only `hermes3d-locks` MCP server through
`code_operator.mcp_lock_*` route handlers; the GUI never speaks MCP
directly. Apps endpoints belong to W6-8 (`/api/source-os/modules`); W6-5
ships only the typed read-side client.

## Auth flow

- The default token provider reads `import.meta.env.VITE_HERMES3D_BEARER_TOKEN`
  at build time. When unset (the local-first default), no `Authorization`
  header is attached — Hermes3D's opt-in auth posture.
- Runtime override:
  ```ts
  import { setBearerTokenProvider } from "../api/hermes3dClient";
  setBearerTokenProvider(() => useAuthStore.getState().token ?? null);
  ```
- Tokens are NEVER logged. All client error messages route through
  `redactSensitive()` which strips `Bearer …`, `?token=…`, `&access_token=…`,
  `token=…` (free-form), `*_KEY=…`, etc. The redaction marker is `***`,
  matching the backend's `gateways.redaction.redact_text` shape.

## Polling strategy

- Status hooks poll every **5 s** (`STATUS_POLL_MS` constant in `_useQuery.ts`).
- Polling uses `safeGetJson` under the hood — transport failures or
  non-2xx responses return `null` rather than throwing, so banners stay
  mounted across transient outages.
- Component-level mutations (`backup`, `stagedUpdate`, `rollback`,
  `preflight`, `spawnBoundedTask`, `smoke`, `heartbeat`,
  `proposeFailure`, `markOutcome`) use `postJson` and DO throw —
  consumers should wire them to a toast.

## Error handling

| Status            | Surface           | Behaviour                                              |
| ----------------- | ----------------- | ------------------------------------------------------ |
| 2xx               | typed payload     | `data` field on `useQuery` / `mutate` resolves         |
| 5xx (polling)     | `null` data       | `error` stays unset; component shows last-good payload |
| 5xx (mutation)    | thrown `Error`    | redacted message, propagates via `MutationState.error` |
| 401 (mutation)    | thrown `Error`    | message redacted, app should surface a re-auth prompt  |
| Transport failure | retried across `API_BASE_URLS` then null/throw | sequential fallback to ports 8765/8766/8767 |

## Test results

- Unit (Node 22+ built-in `node:test` + `--experimental-strip-types`):
  - `node --test --experimental-strip-types --no-warnings src/api/hermes3dClient.test.ts` — **14 / 14 pass**
  - `node --test --experimental-strip-types --no-warnings src/hooks/useAgents.test.ts` — **5 / 5 pass**
  - Combined: **19 / 19 pass** (~250 ms).
- Lint (`npm run lint` = `tsc --noEmit`): all W6-5 files compile cleanly.
  Pre-existing errors in `App.tsx` / `DashboardCustom.tsx` /
  `TopBar.tsx` are owned by W6-3 (Dashboard modes) and out of scope here.
- Playwright: `tests/e2e/gui-wiring-smoke.spec.ts` exercises the
  `/api/agents/update/status` route stub and asserts the banner reports
  v0.13 / v2026.5.7 / `offline` correctly. Runs with the existing
  `playwright.e2e.config.ts` web-server fixture.

## Why not React Query?

The UI bundle deliberately ships zero data-fetching deps (see
`package.json`). `_useQuery.ts` mirrors React Query's
`{ data, error, isLoading, refetch }` and `{ mutate, isLoading, error,
data }` shapes so a future migration is a one-line `import` swap. We
gain: AbortSignal-aware fetches, mounted-ref guarded state updates,
reset semantics on `mutationKey` change, and 5 s polling — without a new
runtime dep.

## Lock release

Locks held under `claude-w6-5-gui-wiring` released at end of session.
