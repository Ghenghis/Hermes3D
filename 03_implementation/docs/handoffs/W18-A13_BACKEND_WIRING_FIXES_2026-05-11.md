# W18-A13 — Backend Wiring Fixes (12 endpoints + silent-empty banners)

**Lane:** W18-A13 — fix lane for the W18-A3 audit findings
**Date:** 2026-05-11
**Owner / Hermes lock:** `w18-a13`
**Branch:** `claude/w18-a13-backend-wiring-fixes` (worktree `.claude/worktrees/w18-a13/`)
**Task ID:** `W18-A13-BACKEND-WIRING-FIXES-2026-05-11`
**Verdict gate:** `GUI_BACKEND_WIRING_GREEN`
**Audit consumed:** `03_implementation/docs/handoffs/W18-A3_BACKEND_ENDPOINT_AUDIT_2026-05-11.md`
  (branch `claude/w18-a3-endpoint-audit`)

## Operator freeze confirmation (mandatory)

**NO printer hardware was enabled by this PR.**

- `/api/printers/probe` was already GET-only on develop (the audit
  observation against POST was stale). No change to the FE adapter,
  the BE handler, or any G-code/M-code path. The handler still calls
  `MoonrakerClient.server_info()` (read-only) and rejects S1 IPs at
  the policy gate before any network probe.
- `GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR` — unchanged.
- `GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR` — unchanged.
- A static AST-based guard test
  (`test_no_printer_write_endpoints_exercised`) refuses to let any
  future contributor add a printer-hardware-write call to the W18-A13
  test file.

## Per-endpoint truth table (before → after)

| # | Endpoint | Audit Verdict | Before | After | Fix Kind |
|---|---|---|---|---|---|
| 1 | `GET /api/health/services` | FAIL_NOT_WIRED + silent-empty | 404 swallowed → empty grid, no banner | 404 / accepted=false → honest-blocked banner with reason | FE (adapter envelope + page banner) |
| 2 | `GET /api/source-os/modules/update-readiness` | FAIL_BACKEND_MISSING | 404 (route is `/api/modules/update/readiness`) | 200 (alias added in BE + FE points at canonical) | BE alias + FE path correction |
| 3 | `POST /api/source-os/modules/{id}/run-proof` | FAIL_BACKEND_MISSING | 404 (route is `/api/apps/{id}/run-proof`) | 200 (alias delegates to apps run-proof) | BE alias |
| 4 | `POST /api/approvals/{id}/defer` | FAIL_BACKEND_MISSING | 404 | 200 — transitions pending → deferred | BE handler |
| 5 | `GET /api/agents/action-catalog` | FAIL_BROKEN (>20s timeout) | No FE timeout → infinite hang | 8s AbortSignal timeout → honest-blocked envelope (BE already cached 8s) | FE timeout helper |
| 6 | `GET /api/agents/config` | FAIL_BROKEN (405 on GET) | PUT-only → 405 → empty form | 200 — returns `{accepted, status, config, api_key_configured, redacted}` | BE handler |
| 7 | `POST /api/printers/probe` | FAIL_BROKEN (method) | FE already used GET on develop; finding was stale | No change | n/a (audit stale) |
| 8 | `GET /api/modules/runtime/verifiers` | FAIL_BROKEN (>20s) | Cold start traversed 60 modules | 8s response cache → warm calls return instantly + 15s FE AbortSignal | BE cache + FE timeout |
| 9 | `GET /api/modules/runtime/agent-cli-readiness` | FAIL_BROKEN (>20s) | Same root cause | Same 8s cache; no FE caller, so FE timeout not needed | BE cache |
| 10 | `GET /api/mcp/locks` (shape) | FAIL_NOT_WIRED | FE read `data.locks` + `file` (singular) | FE reads `data.items` + `files[]` array (one row per file) | FE shape fix |
| 11 | `GET /api/health/services` (silent-empty) | FAIL_NOT_WIRED | 404 swallowed | Banner with `http_404` reason | FE banner |
| 12 | `POST /api/autopilot/next-gate` (409) | FAIL_NOT_WIRED | "Blocked: <statusText>" generic | "Honest-blocked: Next failing check: <name> — <message>" surfaces the truthful blocker | FE handler |

## Code diff summary

| File | +/- | Purpose |
|---|---|---|
| `03_implementation/src/hermes3d/api/routes/agents.py` | +41 | New `GET /api/agents/config` handler |
| `03_implementation/src/hermes3d/api/routes/approvals.py` | +18 | New `POST /api/approvals/{id}/defer` handler |
| `03_implementation/src/hermes3d/api/routes/apps.py` | +18 | New `POST /api/source-os/modules/{id}/run-proof` alias |
| `03_implementation/src/hermes3d/api/routes/modules.py` | +80 | New `update-readiness` alias + 8s response cache for `verifiers`/`agent-cli-readiness` |
| `03_implementation/ui/src/api/adapters.live.ts` | +143 | `getServiceHealthEnvelopeLive`, `fetchJsonWithTimeout`, action-catalog timeout |
| `03_implementation/ui/src/api/adapters.ts` | +6 | Wire `getServiceHealthEnvelope` into the adapters interface |
| `03_implementation/ui/src/api/hermes3dClient.ts` | +15 | `sourceOsClient.updateReadiness` → canonical path |
| `03_implementation/ui/src/components/health/ServiceHealthPage.tsx` | +43 | Honest-blocked banner with reason testid |
| `03_implementation/ui/src/components/settings/McpSubtab.tsx` | +63 | `items[]`/`files[]` shape + legacy fallback |
| `03_implementation/ui/src/tabs/Autopilot.tsx` | +60 | `isHonestNextGate` + improved `actionSummary` + testid |
| `03_implementation/ui/src/tabs/SourceOS.tsx` | +10 | 15s AbortSignal for `verifiers` |
| `03_implementation/ui/src/types/serviceHealth.ts` | +22 | New `ServiceHealthEnvelope` type |
| **Existing source total** | **+485 / -34** | (excludes new test/config/handoff files) |
| `03_implementation/ui/playwright.w18-a13.config.ts` | +68 | New |
| `03_implementation/ui/tests/e2e/w18-a13-backend-wiring.spec.ts` | +230 | New |
| `03_implementation/ui/tests/unit/w18-a13-mcp-subtab.test.tsx` | +142 | New |
| `03_implementation/ui/tests/unit/w18-a13-service-health.test.tsx` | +100 | New |
| `03_implementation/ui/tests/unit/w18-a13-wiring.test.ts` | +155 | New |
| `04_testing/pytest/integration/test_w18_a13_backend_wiring.py` | +338 | New |

## Pytest proof (13/13 PASS)

```
$ python -m pytest 04_testing/pytest/integration/test_w18_a13_backend_wiring.py
.............                                                            [100%]
13 passed
```

Tests cover:
- `test_approvals_defer_route_is_registered` — POST /defer no longer 404s as "path not registered".
- `test_approvals_defer_transitions_pending_to_deferred` — Pending → deferred verdict.
- `test_approvals_defer_rejects_already_decided` — 409 on second defer.
- `test_agents_config_get_route_is_registered` — GET returns 200 (was 405).
- `test_agents_config_get_returns_envelope_shape` — `{accepted, status, config, api_key_configured, redacted}`.
- `test_agents_config_get_never_echoes_api_key` — api_key value is redacted on the GET path.
- `test_source_os_update_readiness_alias_registered` — alias returns 200.
- `test_source_os_update_readiness_alias_matches_canonical` — same shape as canonical.
- `test_source_os_module_run_proof_alias_registered` — alias delegates correctly.
- `test_runtime_verifiers_response_is_cached` — warm calls < 2s (was >20s).
- `test_runtime_agent_cli_readiness_response_is_cached` — same.
- `test_mcp_locks_envelope_shape` — locks BE contract.
- `test_no_printer_write_endpoints_exercised` — AST-based freeze guard.

Regression sweep:
- `test_w17_backend_gaps.py` 13/13 PASS (existing).
- `test_app_registry_proof_run.py` 10/10 PASS (existing).

## Vitest proof (14/14 PASS)

```
$ npx vitest run tests/unit/w18-a13-*.test.{ts,tsx}
✓ tests/unit/w18-a13-mcp-subtab.test.tsx     (5 tests)
✓ tests/unit/w18-a13-service-health.test.tsx (3 tests)
✓ tests/unit/w18-a13-wiring.test.ts          (6 tests)

Test Files  3 passed (3)
     Tests  14 passed (14)
```

Full vitest sweep: **194 passed | 4 skipped** (skipped count unchanged
relative to develop; no W18-A13 regression).

## Playwright proof (4/4 PASS)

```
$ W18_A13_LIVE_BASE_URL=http://127.0.0.1:5198 \
  npx playwright test --config=playwright.w18-a13.config.ts

ok 1 W18-A13: ServiceHealthPage renders honest-blocked banner on 404 (473ms)
ok 2 W18-A13: ServiceHealthPage surfaces backend reason on accepted=false (507ms)
ok 3 W18-A13: McpSubtab reads data.items and expands files[] into rows (466ms)
ok 4 W18-A13: Autopilot 409 renders Honest-blocked + truthful next.message (567ms)

4 passed (3.2s)
```

Screenshots captured under `test-results/w18-a13/`:
- `service-health-404.png`
- `service-health-blocked.png`
- `mcp-subtab-items-files.png`
- `autopilot-409-honest-blocked.png`

## Hermes evidence chain

- `hermes_record_task(actor_id=w18-a13, task_type=infra)` → 2026-05-11.
- `hermes_lock_files(owner=w18-a13, ...)` → 15 + 4 file locks acquired across
  two batches (handoff/tests/src/configs).
- `hermes_heartbeat(owner=w18-a13)` — fired at start and mid-PR.
- `hermes_run_gate(gateId=GUI_BACKEND_WIRING_GREEN, owner=w18-a13)` —
  see PR body.

## Coordination with W18-A1-pickup

`hermes_list_locks` at PR-open time showed `w18-a1` holds locks ONLY on
audit-specific files (`W18-A1_FULL_PRODUCT_ROUTE_WALKER_2026-05-11.md`,
`playwright.w18-a1.config.ts`, `w18-a1-full-route-walk.spec.ts`,
`w18-a1-build-report.mjs`) — no collision with the wiring-fix file set.
No handoff needed.

## Out-of-scope / deferred

- Dead routes (~88 of 241) not touched. The audit's section C lists them;
  they need a separate trim lane.
- Cold-start latency on `/api/code-operator/e2e/readiness` (19s) and
  `/api/code-operator/sandbox/readiness` (18s) — these have honest-
  blocked responses already; adding spinners/skeletons is UX polish, not
  a wiring fix, and is owned by a separate UX lane.
- Hermes Agent update banner: the `upstream_error:"rate limit exceeded"`
  substring is honest-blocked-but-not-actionable. Surfacing the cause
  string verbatim is a presentation tweak owned by the agent-update
  UX lane (PR #225 follow-up).

---

**End of handoff. The verdict line `GUI_BACKEND_WIRING_GREEN = PASS_REAL`
is established by the 31 passing tests above (13 pytest + 14 vitest +
4 playwright) and the per-endpoint truth table.**
