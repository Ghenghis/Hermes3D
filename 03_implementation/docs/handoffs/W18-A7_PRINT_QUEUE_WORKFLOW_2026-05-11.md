# W18-A7 Print Queue Workflow Proof

**Status:** PASS_REAL
**Branch:** `claude/w18-a7-print-queue-workflow`
**Spec:** `03_implementation/ui/tests/e2e/w18-a7-print-queue-workflow.spec.ts`
**Audit JSON:** `03_implementation/ui/test-results/w18-a7/audit.json`
**Screenshot:** `03_implementation/ui/test-results/w18-a7/print-queue-after-submit.png`
**Hermes locks owner:** `w18-a7`
**Run UTC:** `2026-05-11T10:29:57.725Z`

## Mission

Submit sliced output into the live `#print_queue` tab from the running GUI and
prove the job persisted end-to-end (UI -> POST `/api/jobs` -> SQLite -> GET
`/api/jobs` -> UI redraw). Physical printing is explicitly NOT authorized;
`dry_run=true` is asserted on the persisted row.

## Result summary

| Field | Value |
| --- | --- |
| `job_id` | `2b5a3a8166f048a1bb73c31a35abecac` |
| `name` | `W18-A7 04_testing/fixtures/w18_a7_cube_10mm.gcode -> flsun_t1_a` |
| `job_type` | `slice` |
| `status` | `queued` |
| `printer_id` | `flsun_t1_a` (T1 #1, 192.168.0.10, write-enabled, online) |
| `dry_run` | `1` (true) |
| `created_at` | `2026-05-11 10:29:57` |
| `artifact reference` | `04_testing/fixtures/w18_a7_cube_10mm.gcode` (encoded in job name) |

All 10 audit steps returned `PASS_REAL`.

## Evidence

### 1. POST `/api/jobs` response (HTTP 201)

```json
{
  "id": "2b5a3a8166f048a1bb73c31a35abecac",
  "name": "W18-A7 04_testing/fixtures/w18_a7_cube_10mm.gcode -> flsun_t1_a",
  "job_type": "slice",
  "status": "queued",
  "printer_id": "flsun_t1_a",
  "dry_run": 1,
  "created_at": "2026-05-11 10:29:57",
  "updated_at": "2026-05-11 10:29:57"
}
```

### 2. SQLite row dump (proof of persistence)

```
$ sqlite3 03_implementation/var/hermes3d.db \
    "SELECT id, name, job_type, status, printer_id, dry_run, created_at \
     FROM jobs WHERE id='2b5a3a8166f048a1bb73c31a35abecac';"

2b5a3a8166f048a1bb73c31a35abecac|W18-A7 04_testing/fixtures/w18_a7_cube_10mm.gcode -> flsun_t1_a|slice|queued|flsun_t1_a|1|2026-05-11 10:29:57
```

### 3. GET `/api/jobs?status=queued` returns the row

The audit spec asserts the new `job_id` is present in the queued list; the
detail in `audit.json` step `backend_list_contains_job` records the full
matching row returned by the backend.

### 4. GET `/api/jobs/{id}` returns the detail row

```
status=queued
printer_id=flsun_t1_a
steps_count=0
events_count=0
artifacts_count=0
```

`steps`, `events`, and `artifacts` are empty because the job has not yet been
picked up by the orchestrator — that is the correct state for a fresh
queue-only submission.

### 5. UI redraw

After the dialog's `onSubmitted` callback called `refresh()`, the queue lane
rendered the tile `data-testid="print-queue-job-2b5a3a8166f048a1bb73c31a35abecac"`.
Screenshot captured at `03_implementation/ui/test-results/w18-a7/print-queue-after-submit.png`.

## How the proof is produced

The Playwright spec runs in `chromium-e2e` against the live stack started by
`scripts/start-e2e-stack.mjs` (FastAPI :8765 + Vite :5173). It exercises the
real surfaces only — no mocks, no route stubs.

Step list (all `PASS_REAL`):

1. `printers_list` — `GET /api/printers` (4 rows: T1-A, T1-B, S1, V400).
2. `navigate_print_queue` — `#print_queue` mounts; `print-queue-root` visible.
3. `open_dialog` — clicks `print-queue-submit`; `submit-job-dialog` visible.
4. `fill_form` — fills name (encodes the fixture path), type=`slice`, printer=`flsun_t1_a`, `dry_run=true`.
5. `post_jobs` — submits and waits for `POST /api/jobs` -> 201; captures the returned row.
6. `dialog_closed` — `submit-job-dialog` hidden after success.
7. `backend_list_contains_job` — `GET /api/jobs?status=queued` contains the new id.
8. `backend_detail_endpoint` — `GET /api/jobs/{id}` returns 200 with the row.
9. `ui_shows_job` — `print-queue-job-{id}` tile visible; screenshot.
10. `dry_run_preserved` — verifies `dry_run=1` and `status='queued'` — no
    physical print authorized.

## Hard rules observed

- **No physical print authorized.** The dialog's `dry_run` defaults to `true`,
  the spec asserts the checkbox is checked before submit, and step
  `dry_run_preserved` re-fetches the row after submit to confirm `dry_run=1`
  and `status=queued` (still in queue, never dispatched).
- **Selected printer is NOT S1.** S1 (192.168.0.12) is hardware-locked by
  policy (`safety_policy=locked`, `write_enabled=false`); the spec filters
  to a write-enabled non-S1 printer (`flsun_t1_a`).
- **No mocks.** Backend is the FastAPI server in `hermes3d.api.routes.jobs`;
  persistence is real SQLite at `03_implementation/var/hermes3d.db`.

## Files

- Spec: `03_implementation/ui/tests/e2e/w18-a7-print-queue-workflow.spec.ts`
- Fixture: `04_testing/fixtures/w18_a7_cube_10mm.gcode` (50+ lines of valid
  G-code — referenced by path; the JobCreate model has no artifact column so
  the path is encoded in the job name).
- Audit JSON: `03_implementation/ui/test-results/w18-a7/audit.json`
- Screenshot: `03_implementation/ui/test-results/w18-a7/print-queue-after-submit.png`

## Console / network noise observed

- `consoleErrors`: 0
- `pageErrors`: 0
- `networkFailures`: 1 — `GET http://127.0.0.1:8765/api/events/stream` aborted
  with `net::ERR_ABORTED`. This is the SSE/event-stream connection torn down
  when Playwright closed the page; the backend never returned an error code.
  Not a finding.

## Out of scope (NOT part of this audit)

- **Starting a physical print.** Forbidden by the brief and by `dry_run=true`.
- **Slicer artifact attachment.** The current `JobCreate` schema has no
  `artifact_path` column; the fixture path is encoded in the job name. A
  follow-up PR could add an `artifacts` row link and `artifact_path` to
  `JobCreate` so the UI surfaces the real file reference instead of stashing
  it in the name string.
- **Repair / retry / rollback flows.** Those are covered by other W18 lanes
  and the existing job-detail tests in `tests/e2e`.
