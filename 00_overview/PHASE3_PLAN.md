# Phase 3 — Implementation Plan

**Status:** active. Phase 3 is broken into sub-phases; this plan covers **Phase 3.1** only. Subsequent sub-phases (Planner agent, 3D Generation slice, etc.) get their own plan documents and are gated behind explicit human approval.

**Architecture reference:** [`02_architecture/adr/ADR-009-orchestration-skeleton.md`](../02_architecture/adr/ADR-009-orchestration-skeleton.md).

**Branch:** `feat/phase-3-1-fleet-readonly` (forked from `feat/phase-2-ui-final` HEAD; will rebase onto `develop` after Phase 2 PR merges).

---

## Phase 3.1 — Printer Fleet Read-Only Vertical Slice

**Goal:** Replace `getPrinters()` mock with a real Moonraker GET-only client behind a sandboxed orchestration bridge. End-to-end proof of the AdapterAPI swap + supervisor + capability-token + ledger seams. **Zero write capability.**

**Out of scope:** Planner, Repair, Releaser, Auditor, write adapters, UI changes beyond a one-pixel `data-source="live"` chip, 3D / Blender / slicer agents, full DTE pipeline.

---

### Files / modules to create

| Path | Purpose |
|---|---|
| `00_overview/PHASE3_PLAN.md` | this plan, committed before any code |
| `02_architecture/adr/ADR-009-orchestration-skeleton.md` | supervisor + capability-token + ledger contract |
| `03_implementation/src/hermes3d/orchestration/__init__.py` | namespace |
| `…/orchestration/types.py` | DTOs (`Printer`, `Result`, `CapabilityToken`, `PollRequest`, `PollResult`) — mirror `ui/src/types/printer.ts` |
| `…/orchestration/supervisor.py` | issues capability tokens, holds per-printer mutex, dispatches polls |
| `…/orchestration/ledger.py` | SQLite append-only event log at `var/orchestration/ledger.sqlite` |
| `…/orchestration/bridge.py` | local-only HTTP server (FastAPI) exposing the AdapterAPI surface; bound to 127.0.0.1 |
| `…/agents/printer_executor.py` | single agent class, status-poll only, validates with `types.Printer` |
| `…/adapters/moonraker_readonly.py` | real Moonraker client implementing the existing read half of the Phase-1 Protocol; GET endpoints only |
| `…/adapters/_capabilities.py` | manifest schema; refuses to register an adapter declaring `phase>=4` writes |
| `03_implementation/ui/src/api/adapters.live.ts` | live AdapterAPI impl — calls the bridge over `fetch` to `127.0.0.1:<port>` |
| `03_implementation/ui/src/api/adapters.ts` | tiny resolver that picks `mock` vs `live` based on `import.meta.env.VITE_HERMES3D_ADAPTER` (default `mock`) |
| `04_testing/pytest/unit/orchestration/test_supervisor_tokens.py` | capability-token issuance + revocation |
| `04_testing/pytest/unit/orchestration/test_ledger_append.py` | append-only invariants + sha rollup |
| `04_testing/pytest/unit/adapters/test_moonraker_readonly_contract.py` | adapter conforms to read half of Protocol; refuses any write call |
| `04_testing/pytest/integration/test_fleet_poll_roundtrip.py` | bridge round-trips `Printer[]` from a fixture Moonraker mock server |
| `04_testing/playwright_ui/tests/visual/fleet.live.spec.ts` | UI shows `data-source="live"` for the 4 live entries when bridge env var is set |
| `.github/workflows/ui-ci.yml` | extend Layer D2 to run a "live-mode smoke" job against the fixture server |
| `06_release/phase3.1-bundle/` | proof bundle output dir |
| `scripts/scaffolding/phase3_1_proof.py` | bundle assembler (reuses the Phase 0/1 pipeline) |

**UI files changed (one each, minimal):**
- `ui/src/api/adapters.ts` — resolver only.
- `ui/src/data/mock/printers.ts` — add `data_source: "live" | "mock"` field to `Printer` type + each entry; mocks all marked `mock`.
- `ui/src/types/printer.ts` — add the field.
- `ui/src/tabs/Fleet.tsx` + `ui/src/tabs/Dashboard.tsx` (fleet panel) — render the `data-source` chip on each row.

No new tabs. No new dock states. No new primitives.

---

### Checkpoints (5)

#### CP3.1-A — Plan + ADR
**Tasks**
1. Commit `PHASE3_PLAN.md` (this document).
2. Commit `ADR-009-orchestration-skeleton.md` documenting: supervisor, capability-token shape, ledger schema, bridge boundary, refusal rules.

**Acceptance**
- Both files committed on `feat/phase-3-1-fleet-readonly`.
- No code under `03_implementation/src/hermes3d/orchestration/` yet.
- Phase 2 gates still green (`npm run lint`, `npm run build`, `npx playwright test`).

**Safety gates**
- Plan declares the slice has zero write capability.
- ADR explicitly forbids any agent without a token from calling a tool.

---

#### CP3.1-B — Orchestration skeleton (offline)
**Tasks**
3. Implement `orchestration/types.py` — DTOs only, no logic. Mirror UI types exactly; add `Result[Ok, Err]`, `CapabilityToken { agent_id, tools, expires_at }`.
4. Implement `orchestration/ledger.py` — append-only SQLite, schema `(ts_utc, run_id, agent_id, tool, inputs_sha, outputs_sha, verdict, message)`.
5. Implement `orchestration/supervisor.py` — token issuance, per-printer mutex, dispatch loop. No bridge yet, no real adapter yet.
6. Implement `adapters/_capabilities.py` — manifest schema + `register_adapter()` that refuses `phase>=4`.
7. Unit tests: `test_supervisor_tokens.py`, `test_ledger_append.py`.

**Acceptance**
- Layer A static gates pass on the new Python modules (ruff format/check, forbidden-pattern scan, registry validator).
- Layer B unit tests pass on Linux × py3.11/3.12 + Windows × py3.11/3.12.
- No network calls yet; tests run fully offline.

**Safety gates**
- Forbidden-pattern scanner extended to fail any new adapter manifest with `phase>=4` or any `subprocess.Popen` outside the existing slicer/blender allowlist.
- Capability-token tests assert that an agent with no token cannot dispatch.

---

#### CP3.1-C — Read-only Moonraker adapter + fixture server
**Tasks**
8. Implement `adapters/moonraker_readonly.py` — only `/printer/info`, `/printer/objects/query` (subset), `/server/info`. Per-host allowlist, 2-second timeout, 256-KiB response cap.
9. Add `printer_executor.py` agent — accepts `PollRequest`, calls the adapter, validates the response against `types.Printer`, returns `Result`. Refuses any non-poll method.
10. Adapter contract test `test_moonraker_readonly_contract.py` — asserts (a) the adapter implements the read half of the Phase-1 Protocol, (b) every write method on the Protocol raises `NotImplementedError` or is absent.
11. Fixture Moonraker server under `04_testing/fixtures/moonraker/` (FastAPI, deterministic responses, no real network).

**Acceptance**
- Adapter contract test green.
- Layer A scanner passes.
- A Python integration test polls the fixture server and gets back valid `Printer` DTOs.
- No network is reached during test runs.

**Safety gates**
- Allowlist test: adapter refuses to talk to any host outside `192.168.0.0/24` + `127.0.0.1`.
- Cap test: oversized response is truncated and surfaced as `Err::ResponseTooLarge`.

---

#### CP3.1-D — Bridge + UI live-mode resolver
**Tasks**
12. Implement `orchestration/bridge.py` — FastAPI app bound to `127.0.0.1:<port>`, exposes only `GET /api/printers`. Returns the orchestrator's last poll snapshot. No CORS opened to non-localhost.
13. Add the `data_source` field to `Printer` type + mock entries. Update `Fleet.tsx` + `Dashboard.tsx` fleet panel to render the chip (one-line change each).
14. Add `ui/src/api/adapters.live.ts` — `fetch` against `127.0.0.1:<port>/api/printers`, validates response shape at the boundary.
15. Add `ui/src/api/adapters.ts` resolver — env-driven (`VITE_HERMES3D_ADAPTER=mock|live`, default `mock`).
16. Bridge integration test: `test_fleet_poll_roundtrip.py` — boot fixture Moonraker, boot bridge, GET `/api/printers`, assert 4 live + 8 mock entries (live ones from fixture, mocks pass through).

**Acceptance**
- `npm run build` clean.
- `npm run lint` clean.
- Existing Playwright suite (9 specs) **still passes** with default `mock` adapter — no UI baseline drift.
- New live-mode spec `fleet.live.spec.ts` passes against the fixture server.
- Bridge refuses any non-localhost client.

**Safety gates**
- Bridge integration test asserts `127.0.0.1` binding, refuses 0.0.0.0.
- UI live adapter validates every field against the TS type before rendering — invalid data → mock fallback + `data-source="error"`.
- No new launch surface in the UI: re-run the dock-spec source-pattern audit and grep for `child_process | spawn | exec | BrowserWindow | webview | openExternal | window.open | shell. | process.` in `ui/src/` — must remain 0.

---

#### CP3.1-E — Proof bundle + CI extension + closeout
**Tasks**
17. Implement `scripts/scaffolding/phase3_1_proof.py` — assembles a signed bundle containing: `PHASE3_PLAN.md`, `ADR-009`, ledger snapshot, fixture-server replay log, UI build output sha, Playwright JSON report. Reuses the Phase 0/1 signer.
18. Extend `.github/workflows/ui-ci.yml` with a new job `layer_d2_live_smoke`: boots the fixture Moonraker + bridge, runs Playwright live-mode spec on Ubuntu-latest. Layer D2 mock job stays unchanged.
19. Write `00_overview/PHASE3_1_COMPLETION_REPORT.md` modeled after Phase 2's: scope, commit list, files-touched, gate results, safety audit (token issuance count, ledger size, allowlist refusals), known follow-ups (Planner, write adapters), references.
20. Open PR `Phase 3.1 — Printer Fleet read-only` to `develop`. HARD STOP.

**Acceptance**
- All Layer A/B/C gates green on the branch.
- Layer D2 mock job green (Phase 2 contract preserved).
- Layer D2 live smoke job green against fixture server.
- Proof bundle written to `06_release/phase3.1-bundle/<head>-<utc>.zip` with manifest + sha256 sidecars.
- Architect review: PASS on completion report (same checklist as Phase 2 closeout).

**Safety gates**
- Honesty diff (Layer F) passes — manifest claims match physical file set.
- No commit to `main`. No tag. No write to rc1.
- PR body lists every safety boundary preserved (no writes, no native windows, allowlisted hosts, capability-token enforcement).

---

### Success criteria for Phase 3.1

| Criterion | Measure |
|---|---|
| AdapterAPI swap proven | UI runs unchanged against either mock or live adapter via env switch |
| Supervisor + capability-token primitives in place | Unit tests assert tokenless dispatch is refused; mutex prevents concurrent polls of same printer |
| Read-only boundary enforced | Adapter contract test asserts no write method is callable; allowlist rejects non-`192.168.0.0/24` + `127.0.0.1` hosts |
| Ledger functional | Every poll appears in `var/orchestration/ledger.sqlite`; bundle's manifest references exact ledger sha |
| UI baseline preserved | Phase 2 dashboard visual diff still passes; existing 9 specs still pass |
| CI extended without weakening Phase 2 | Layer D2 mock job + new live smoke job both green; no existing gate downgraded |
| Proof bundle honest | Honesty diff green; bundle contents match manifest exactly |
| Zero new launch paths | Source-pattern audit re-runs clean over `ui/src/` and `03_implementation/src/hermes3d/` |

---

### Order of execution

CP3.1-A → CP3.1-B → CP3.1-C → CP3.1-D → CP3.1-E. Strict serial. Each checkpoint gates the next; no leapfrogging. Architect review required at A, C, D, E (B is internal-only).

After CP3.1-E merges, Phase 3.2 unlocks: Planner agent + 3D Generation read-only slice. **Not in this plan.**
