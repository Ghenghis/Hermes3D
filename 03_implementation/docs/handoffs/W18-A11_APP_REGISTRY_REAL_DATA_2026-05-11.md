# W18-A11 App Registry Real-Data Proof

**Status:** PASS_REAL
**Branch:** `claude/w18-a11-app-registry-real-data`
**Spec:** `03_implementation/ui/tests/e2e/w18-a11-app-registry-real-data.spec.ts`
**Config:** `03_implementation/ui/playwright.w18-a11.config.ts`
**Audit JSON:** `03_implementation/ui/test-results/w18-a11/audit.json`
**Screenshots:** `03_implementation/ui/test-results/w18-a11/{app-registry-full,app-detail-hermes_agent,app-detail-langchain,app-detail-cadquery,app-detail-kiln}.png`
**Hermes locks owner:** `w18-a11`
**Task ID:** `W18-A11-APP-REGISTRY-REAL-DATA-2026-05-11`
**Run UTC:** `2026-05-11T11:06:08.749Z`
**Verdict gate driven:** GUI_60_APPS_GREEN

## Mission

Audit-only proof that the Hermes3D dashboard's App Registry tab
(`#apps`) loads real backend data, detail panels open with real
per-app state, and per-app action buttons (Run proof / Rollback) are
either wired to the real backend OR honestly disabled with a real
backend reason. No mocks, no fake "ready", no skipped tests.

## Real app count vs. operator's expectation

| Source | Count |
| --- | ---: |
| Operator's brief expectation | **60** |
| Backend `GET /api/apps` (count field) | **60** |
| Backend `GET /api/apps` (apps[] length) | **60** |
| Backend `GET /api/source-os/modules` (length) | **60** |
| GUI rendered `tr[data-testid^="app-row-"]` rows | **60** |

**Divergence from operator's expectation: none.** Real count
matches expectation exactly (60). Reflected in the audit JSON
`count_matches_operator_expectation: true`.

## Result summary

| Field | Value |
| --- | --- |
| Verdict | **PASS_REAL** |
| Backend `/api/apps` status | 200 |
| Backend `/api/source-os/modules` status | 200 |
| GUI fetched real backend | true |
| GUI fetch URL observed | `http://127.0.0.1:8765/api/apps` |
| Rendered row count | 60 / 60 |
| Detail panels opened | 4 / 4 (`hermes_agent`, `langchain`, `cadquery`, `kiln`) |
| Run-proof buttons clicked | 4 (all non-printer-lane) |
| Run-proof buttons skipped (printer lane) | 0 |
| Rollback affordances inspected | 4 |
| Honest-disabled buttons | 1 (kiln rollback section, hidden because backend `rollback_supported=0`) |
| Console errors | 0 |
| Page errors | 0 |
| Network failures (>=400 or net::ERR_*) | 0 |
| Pinned verdicts changed | **NONE** |

## Per-app rows exercised

| App | Section | Printer lane? | `/api/apps/{id}` | Detail panel | Run proof button | Rollback affordance |
| --- | --- | :---: | :---: | :---: | --- | --- |
| `hermes_agent` | agents | NO | 200 | opened | clicked → POST 200, `accepted=true status=pass` | runbook section visible (backend `rollback_supported=1`, runbook URL present) |
| `langchain` | agents | NO | 200 | opened | clicked → POST 200, `accepted=false status=fail` | runbook section visible (backend `rollback_supported=1`) |
| `cadquery` | modelers | NO | 200 | opened | clicked → POST 200, `accepted=false status=fail` | runbook section visible (backend `rollback_supported=1`) |
| `kiln` (negative-proof) | agents | NO | 200 | opened | clicked → POST 200, `accepted=false status=not_set` (backend `proof_command=null`) | runbook section **hidden** (backend `rollback_supported=0`) — **HONEST_DISABLED** |

All four detail panels rendered the real backend fields:
`current_version`, `license`, `lifecycle`, `update_lane`,
`tested_versions`, `rollback_supported`, `upstream_url`. The kiln
detail panel honestly shows `License: unknown`, `Tested versions:
(none on record)`, `Rollback supported: no` — no fabricated values.

### Negative-proof exercise — kiln

`kiln` is the audit's negative-proof case. The backend record has
`proof_command=null, rollback_supported=0`. Observations:

- **Rollback runbook section is honestly hidden** by `AppDetailPanel.tsx`
  (the section is gated on `detail.rollback_supported` and is only
  rendered when true). Audit verdict: `HONEST_DISABLED` (UI agrees
  with the backend record).
- **Run-proof button is NOT gated** on `proof_command` presence —
  the UI sends the POST anyway. The backend then honestly responds
  `accepted=false, status=not_set` (per `apps.py:run_app_proof`
  early-return path). Audit verdict: `PASS_REAL` because the action
  IS wired to the real backend; the "no proof_command" reality is
  surfaced via the backend response, not by a fake "Coming soon"
  label.

  Optional UX follow-up (out of this audit's scope): the UI could
  also short-circuit the click when `detail.proof_command` is empty
  and surface "no proof command configured" inline, but the current
  behavior is honest end-to-end and is not a finding.

## Backend endpoint contract (from `src/hermes3d/api/routes/apps.py`)

```
GET  /api/apps                              -> {count, filters, apps:[...]}
GET  /api/apps/{app_id}                     -> {id, display_name, ..., proof_command, rollback_supported, ...}
POST /api/apps/{app_id}/run-proof           -> {accepted, status, app_id, exit_code, ..., evidence_id}
POST /api/apps/{app_id}/rollback            -> 501 if not rollback_supported, else {accepted, status, next_route}
```

The GUI's `appsClient.ts` consumes either `/api/apps/*` or the
legacy `/api/source-os/modules/*` fallback. In this run, the GUI
hit `/api/apps` directly (see `gui_fetch_url_observed` in the audit
JSON).

## Buttons clicked / skipped — final tally

- **Buttons clicked: 4** — run-proof for `hermes_agent`,
  `langchain`, `cadquery`, `kiln`. All four POSTs hit
  `http://127.0.0.1:8765/api/apps/{id}/run-proof` and returned 200
  with real backend payloads. Zero of those buttons dispatched to
  a printer or to `/api/jobs`.
- **Buttons skipped (printer-lane): 0**, because the four target
  apps are all in non-printer sections (`agents`, `modelers`). The
  printer-lane sections (`firmware`, `print_farm`, `slicers`,
  `hardware`) are recognized by the spec's `PRINTER_LANE_SECTIONS`
  set and would have been recorded as
  `OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE` if any target app had
  fallen in one. None did, by design — see the rationale comment in
  the spec at the `TARGET_APPS` definition.
- **Honestly disabled: 1** — kiln rollback runbook section
  (`app-detail-rollback`) is correctly hidden because the backend
  reports `rollback_supported=false`.

## How the proof is produced

The Playwright spec runs in `chromium-w18-a11` against the live
stack the operator is auditing:

- Frontend: `http://localhost:5173` (Vite)
- Backend:  `http://127.0.0.1:8765` (FastAPI)

The dedicated config `playwright.w18-a11.config.ts` has **no
`webServer` block** so the audit hits the real running stack and
not a second backend on 8766/8642 (which would diverge from the
truth the operator is auditing).

Step list (audit-only, no mutating side effects beyond
`POST /api/apps/{id}/run-proof` on four non-printer-lane apps,
which only updates the `modules.last_proof_*` columns in SQLite):

1. `backend_apps_count` — `GET /api/apps` → 200, `count=60`.
2. `backend_modules_count` — `GET /api/source-os/modules` → 200,
   `length=60` (the GUI's primary fallback endpoint).
3. `navigate_apps` — `#apps` opens; `apps-root` and
   `app-status-panel` both visible.
4. `gui_real_fetch` — observed `GET http://127.0.0.1:8765/api/apps`
   from the page; not a mock.
5. `rendered_row_count` — 60 `tr[data-testid^="app-row-"]` rows.
6. For each of `hermes_agent`, `langchain`, `cadquery`, `kiln`:
   - `backend_detail` — `GET /api/apps/{id}` → 200.
   - `open_detail_panel` — click `app-row-{id}-detail`,
     `app-detail-panel` visible.
   - `rendered_fields` — capture text of
     `app-detail-versions` block.
   - `screenshot` — full-page PNG.
   - `run_proof_button` — click `app-detail-run-proof`; assert real
     POST to `/api/apps/{id}/run-proof`; capture response.
   - `rollback_section` — assert visibility matches backend
     `rollback_supported`.
   - `back_to_list` — return to status panel.
7. `write_audit_json` — assemble all observations into
   `test-results/w18-a11/audit.json`.

## Hard rules observed

- **No mocks.** Live FastAPI is the source of truth; the spec
  consumes its real responses.
- **No `test.skip` / conditional skips.** The spec has zero skip
  sites. Missing surfaces would be recorded as `FAIL_NOT_WIRED`
  (none observed in this run).
- **No printer hardware writes.** Printer-domain action buttons
  are out-of-scope per the 2026-05-11 operator freeze. The four
  target apps are all in non-printer sections (`agents`,
  `modelers`), and none of the four `POST /api/apps/{id}/run-proof`
  calls were dispatched to `/api/jobs` or `/api/printers/*`. Zero
  printer-domain side effects.
- **Pinned verdicts unchanged.**
  `GUI_PHYSICAL_PRINT_GREEN=OUT_OF_SCOPE_BY_OPERATOR` and
  `GUI_PRINTER_DRY_RUN_GREEN=OUT_OF_SCOPE_BY_OPERATOR` are recorded
  unchanged in the audit JSON's `pinned_verdicts` block.

## Console / network noise observed

- `console_errors`: **0**
- `page_errors`: **0**
- `network_failures`: **0**

## Files

- Spec: `03_implementation/ui/tests/e2e/w18-a11-app-registry-real-data.spec.ts`
- Config: `03_implementation/ui/playwright.w18-a11.config.ts`
- Audit JSON: `03_implementation/ui/test-results/w18-a11/audit.json`
- Full-tab screenshot: `03_implementation/ui/test-results/w18-a11/app-registry-full.png`
- Detail screenshots:
  `03_implementation/ui/test-results/w18-a11/app-detail-{hermes_agent,langchain,cadquery,kiln}.png`

## Scope discipline confirmation

**This audit did NOT touch printers.** The four target apps were
selected so their `section` is in (`agents`, `modelers`) — not in
the printer-lane set. Zero printer-control API calls were made.
Zero clicks on `firmware`/`print_farm`/`slicers`/`hardware` action
buttons. The two pinned verdicts
`GUI_PHYSICAL_PRINT_GREEN=OUT_OF_SCOPE_BY_OPERATOR` and
`GUI_PRINTER_DRY_RUN_GREEN=OUT_OF_SCOPE_BY_OPERATOR` are unchanged
by this run, both in the handoff and in the audit JSON.

## Out of scope (NOT part of this audit)

- **Printer-domain launch / proof / rollback.** Out of scope per
  operator freeze. The spec's `PRINTER_LANE_SECTIONS` set would
  catch any target app that fell in those sections and record
  `OUT_OF_SCOPE_BY_OPERATOR_PRINTER_LANE` instead of clicking.
- **Stale-lock recovery.** The W6-7 AppRegistry source files
  (`src/components/AppRegistry/*.tsx`, `src/tabs/AppRegistry.tsx`,
  `src/types/app-registry.ts`, `tests/e2e/live-gui.spec.ts`) carry
  stale locks from `claude-w9-2g-final-3` (2026-05-10). Read-only
  inspection only; no recovery / release attempted (out of scope
  for this audit per brief).
- **The other 56 apps.** This audit exercises 4 of the 60 apps
  end-to-end; the other 56 are validated via the count match
  (`rendered_row_count=60`), the `/api/apps` shape proof, and the
  zero-error noise budget. Per-row interactivity for printer-lane
  apps is permanently out of scope under the operator freeze.
