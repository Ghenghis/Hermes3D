# Phase 3.1 Completion Report

**Branch:** `feat/phase-3-1-fleet-readonly`
**Base:** `origin/develop`
**Scope:** read-only fleet slice
**Status:** ready for PR after CP3.1-E closeout

## Scope Summary

Phase 3.1 adds a read-only orchestration slice for fleet polling. The slice includes the offline supervisor/token skeleton, append-only ledger, read-only Moonraker adapter, local-only bridge, and UI live-mode resolver.

No write adapter, planner, slicer, Blender, native window, or printer-control capability is introduced.

## Commit List

Captured before the CP3.1-E closeout commit with:

```bash
git log origin/develop..HEAD --oneline
```

```text
0e56592 feat(phase3.1): add local bridge and live adapter resolver
bd79b0e feat(phase3.1): add read-only Moonraker adapter and fixture tests
55cdea0 feat(phase3.1): add offline orchestration skeleton
db73398 feat(phase3.1): add plan + orchestration ADR
```

The CP3.1-E closeout commit adds this report, the proof assembler, CI live-smoke job, and the generated proof bundle.

## Files Touched

Branch diff summary before this closeout report/bundle was added:

```text
.github/workflows/ui-ci.yml                        |  87 +++++++-
00_overview/PHASE3_PLAN.md                         | 172 +++++++++++++++
02_architecture/adr/ADR-009-orchestration-skeleton.md | 139 +++++++++++++
03_implementation/src/hermes3d/adapters/_capabilities.py |  52 +++++
03_implementation/src/hermes3d/adapters/moonraker_readonly.py | 204 ++++++++++++++++++
03_implementation/src/hermes3d/agents/printer_executor.py |  32 +++
03_implementation/src/hermes3d/orchestration/bridge.py | 151 ++++++++++++++
03_implementation/src/hermes3d/orchestration/ledger.py | 114 ++++++++++
03_implementation/src/hermes3d/orchestration/supervisor.py | 230 +++++++++++++++++++++
03_implementation/src/hermes3d/orchestration/types.py |  69 +++++++
03_implementation/ui/src/api/adapters.live.ts      | 128 ++++++++++++
03_implementation/ui/src/api/adapters.ts           |  39 +++-
03_implementation/ui/src/data/mock/printers.ts     |   5 +
03_implementation/ui/src/tabs/Dashboard.tsx        |  68 ++++--
03_implementation/ui/src/tabs/Fleet.tsx            |  65 ++++--
03_implementation/ui/src/types/printer.ts          |   2 +
03_implementation/ui/tests/visual/fleet.live.spec.ts |  98 +++++++++
04_testing/fixtures/moonraker/server.py            |  52 +++++
04_testing/pytest/integration/test_fleet_poll_roundtrip.py | 181 ++++++++++++++++
04_testing/pytest/unit/adapters/test_capabilities_manifest.py | 59 ++++++
04_testing/pytest/unit/adapters/test_moonraker_readonly_contract.py | 123 +++++++++++
04_testing/pytest/unit/orchestration/test_ledger_append.py | 68 ++++++
04_testing/pytest/unit/orchestration/test_supervisor_tokens.py | 100 +++++++++
```

CP3.1-E closeout files:

- `.github/workflows/ui-ci.yml`
- `00_overview/PHASE3_1_COMPLETION_REPORT.md`
- `02_architecture/scripts/scaffolding/phase3_1_proof.py`
- `06_release/phase3.1-bundle/0e56592ddb99-20260501T205203Z.zip`
- `06_release/phase3.1-bundle/0e56592ddb99-20260501T205203Z.manifest.json`
- `06_release/phase3.1-bundle/0e56592ddb99-20260501T205203Z.sha256`

## Gate Results

Run from repo root:

```bash
python -m ruff check 03_implementation/src/hermes3d 04_testing/pytest
python -m pytest 04_testing/pytest/unit/orchestration 04_testing/pytest/unit/adapters 04_testing/pytest/integration -q
```

Result: PASS.

Pytest summary:

```text
........................................................................ [ 36%]
........................................................................ [ 73%]
....................................................                     [100%]
```

Run from `03_implementation/ui`:

```bash
npm run lint
npm run build
npx playwright test
```

Results:

- `npm run lint`: PASS (`tsc --noEmit`)
- `npm run build`: PASS, 2411 modules transformed
- Build outputs: `index.html` 0.42 kB, CSS 20.17 kB / gzip 4.70 kB, JS 679.36 kB / gzip 183.82 kB
- `npx playwright test`: PASS, 10 tests in 11.1s
- Specs: `dashboard.visual.spec.ts`, `dock.spec.ts`, `fleet.live.spec.ts`

## Safety Audit

Token enforcement:

- `OfflineSupervisor.dispatch_poll()` refuses missing tokens.
- Expired tokens are refused.
- Unauthorized tools are refused.
- Tokens are consumed after dispatch, so replay is refused.
- `PrinterExecutor` refuses any non-`printer.poll` request.

Ledger writes:

- `OrchestrationLedger` creates an append-only SQLite event table.
- Required columns are `ts_utc, run_id, agent_id, tool, inputs_sha, outputs_sha, verdict, message`.
- There are no UPDATE/DELETE helpers.
- Stable SHA rollup is covered by unit tests.

Allowlist enforcement:

- `MoonrakerReadonlyAdapter` allows only `127.0.0.1`, `localhost`, and `192.168.0.0/24`.
- Allowed endpoints are only `GET /printer/info`, `GET /printer/objects/query`, and `GET /server/info`.
- The local bridge exposes only `GET /api/printers`, disables docs/openapi, and rejects non-local clients.
- Live UI mode fetches only `http://127.0.0.1:<port>/api/printers`.

Write safety:

- No write routes are present in the bridge.
- Read-only adapter has no write methods.
- Adapter manifest guard refuses write capability before Phase 4.
- Existing dangerous UI actions remain locked.

## Proof Bundle

Bundle path:

```text
06_release/phase3.1-bundle/0e56592ddb99-20260501T205203Z.zip
```

SHA-256:

```text
49a2fdfbb7eb282e09da2c64cd62cc0201cb565c2a56099cec5ce8a64aa08d8a
```

Included files:

```text
docs/ADR-009-orchestration-skeleton.md
docs/PHASE3_PLAN.md
evidence/fixture_replay_log.json
evidence/ledger_snapshot.sqlite3
evidence/playwright_report.json
evidence/ui_build_output_hash.json
```

Verification:

```text
entries=6
missing=[]
extra=[]
mismatches=[]
```

## CI Extension

`.github/workflows/ui-ci.yml` adds:

```text
layer_d2_live_smoke
```

The new job runs on `ubuntu-latest`, installs Python/UI dependencies, boots the deterministic fixture Moonraker server, boots the local bridge, and runs the Playwright live-mode smoke spec. The existing `layer_d2_ui_final` Phase 2 mock job remains unchanged.

## Known Follow-ups

- Planner
- Write adapters

## References

- `02_architecture/adr/ADR-009-orchestration-skeleton.md`
- `00_overview/PHASE3_PLAN.md`

## Stop Point

CP3.1-E closes Phase 3.1. Phase 3.2 must not start until explicitly approved.
