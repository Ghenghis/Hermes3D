# W18-A8 Artifact / File / Proof Real Endpoint Audit

**Status:** PASS_REAL
**Verdict gate:** `GUI_ARTIFACT_PROOF_GREEN`
**Branch:** `claude/w18-a8-artifact-file-proof`
**Spec:** `03_implementation/ui/tests/e2e/w18-a8-artifact-file-proof.spec.ts`
**Config:** `03_implementation/ui/playwright.w18-a8.config.ts`
**Audit JSON:** `03_implementation/ui/test-results/w18-a8/audit.json`
**Hermes locks owner:** `w18-a8`
**Task ID:** `W18-A8-ARTIFACT-FILE-PROOF-2026-05-11`
**Run UTC:** `2026-05-11T11:03:30.279Z`
**Live backend audited:** `http://127.0.0.1:8765` (FastAPI — hermes3d.api.routes.artifacts + .system)
**Live frontend audited:** `http://localhost:5173` (Vite SPA)

## TL;DR

The Hermes3D artifact and proof endpoints are wired end-to-end from the live
GUI to real backend storage on disk. The audit drove the live `#artifacts`
and `#proof` tabs, observed the SPA's own network traffic, and round-tripped
a labelled probe through POST `/api/artifacts` + GET `/api/artifacts/{id}/download`.
All 21 audit steps returned `PASS_REAL`. No printer-control endpoint was
called. The note in the operator brief about a `/api/files/*` surface is
resolved: the real artifact surface lives at `/api/artifacts/*` and the real
proof surface lives at `/api/proof/*` — there is no separate `/api/files`
endpoint in the backend.

## Scope discipline (printer freeze observed)

- **No** `/api/printers/{id}/*` write methods called.
- **No** `/api/jobs` submission. The W18-A7 job-lane PASS_REAL remains
  untouched.
- **No** G-code, M-code, jog, home, or heat command.
- **Pinned verdicts unchanged:**
  - `GUI_PHYSICAL_PRINT_GREEN = OUT_OF_SCOPE_BY_OPERATOR`
  - `GUI_PRINTER_DRY_RUN_GREEN = OUT_OF_SCOPE_BY_OPERATOR`

The only mutating call this audit issued was `POST /api/artifacts` with a
self-labelled `W18-A8-PROBE-{timestamp}` body, plus `POST /api/proof/events`
with `type=w18_a8_audit`. Both are pure server-side persistence and have no
hardware effect.

## Result summary

| Field | Value |
| --- | --- |
| Verdict | `PASS_REAL` |
| Steps total | 21 |
| Steps PASS_REAL | 21 |
| Steps PARTIAL/FAIL | 0 |
| Probe label | `W18-A8-PROBE-2026-05-11T11-03-23-407Z` |
| Probe artifact id | `c656750c810c445587c5d0e3c927108b` |
| Probe sha256 (POST body == GET download == disk) | `5f8e42d520e1766469965c7993e9491096a2ec4f16c600340ca3e4f2b6f486ec` |
| Probe on-disk path | `G:\Github\Hermes3D\03_implementation\var\artifacts\c656750c810c445587c5d0e3c927108b_artifact.bin` |
| Proof event id | `bb904f8a43874bfb938b1105561ae2d3` |
| Proof file probed | `ACTIVE_UI_NO_FAKE_SWEEP.md` (37 635 bytes) |
| Proof file sha256 (backend == GUI 'View' link == on-disk) | `15d5a79c3f6400c5f127c2027873e7f7ea959d6ce597bac4fcacf3d34e5c1d2c` |
| Proof manifest size (live) | 38 files / 4 978 010 bytes |
| Console errors | 0 |
| Page errors | 0 |
| Unexpected 404/5xx on artifact/proof | 0 |

## Audit-step table

| # | Step | Status | Reason / proof |
| - | --- | --- | --- |
| 1 | `backend_health` | PASS_REAL | `GET /api/system/snapshot` -> 200 (edition `desktop_gpu_worker`, DB exists). |
| 2 | `backend_artifacts_list` | PASS_REAL | `GET /api/artifacts/list` -> 200; 38 files; shape `{proof_dir, file_count, total_size_bytes, files[]}`. |
| 3 | `backend_artifacts_rows` | PASS_REAL | `GET /api/artifacts` -> 200; array of 4 rows from SQLite `artifacts` table. |
| 4 | `ui_calls_artifacts_list` | PASS_REAL | Live SPA at `#artifacts` issued `GET /api/artifacts/list` -> 200 (observed via `page.on("response")`). |
| 5 | `ui_calls_artifacts_rows` | PASS_REAL | Live SPA issued `GET /api/artifacts` -> 200. |
| 6 | `screenshot_artifacts_tab` | PASS_REAL | Captured `01-artifacts-tab-loaded.png` (162 075 bytes). |
| 7 | `backend_proof_fetch` | PASS_REAL | Direct `GET /api/artifacts/proof/ACTIVE_UI_NO_FAKE_SWEEP.md` -> 200; 37 635 bytes; sha256 verified. |
| 8 | `ui_proof_view_link` | PASS_REAL | Proof-bundles section 'View' link href = `/api/artifacts/proof/ACTIVE_UI_NO_FAKE_SWEEP.md`; fetched bytes match backend sha256. |
| 9 | `proof_envelope_on_disk` | PASS_REAL | `03_implementation/proof/ACTIVE_UI_NO_FAKE_SWEEP.md` exists, same size, same sha256. |
| 10 | `post_artifact` | PASS_REAL | `POST /api/artifacts?label=W18-A8-PROBE-…` -> 201; id `c656750c…`; row in SQLite. |
| 11 | `download_round_trip` | PASS_REAL | `GET /api/artifacts/c656750c…/download` -> 200; bytes (and sha256) match POST body. |
| 12 | `post_artifact_on_disk` | PASS_REAL | Uploaded body persisted at `var/artifacts/c656750c…_artifact.bin`; size + sha256 match POST body. |
| 13 | `artifact_appears_in_list` | PASS_REAL | Re-fetched `GET /api/artifacts`; probe row present with correct `label`. |
| 14 | `screenshot_after_post` | PASS_REAL | Captured `02-artifacts-tab-after-post.png`. |
| 15 | `backend_proof_bundles` | PASS_REAL | `GET /api/proof/bundles` -> 200; array (initial 54 rows). |
| 16 | `ui_calls_proof_bundles` | PASS_REAL | Live SPA at `#proof` issued `GET /api/proof/bundles` -> 200. |
| 17 | `ui_proof_detail_open` | PASS_REAL | `proof-bundle-local-audit-evidence-1` clicked; `proof-detail` panel visible. |
| 18 | `screenshot_proof_tab` | PASS_REAL | Captured `03-proof-tab-detail.png`. |
| 19 | `post_proof_event` | PASS_REAL | `POST /api/proof/events {type:"w18_a8_audit", source_agent:"w18-a8-audit", payload:{…}}` -> 201; id `bb904f8a…`; `recorded:true`, `proof_kind:"audit_event"`. |
| 20 | `event_visible_in_bundles` | PASS_REAL | `GET /api/proof/bundles?limit=200` grew from 54 to 204 after the POST — new event is readable back. |
| 21 | `console_network_clean` | PASS_REAL | 0 console errors, 0 page errors, 0 unexpected 404/5xx on artifact/proof endpoints. |

## Network audit (filtered to artifact/proof surfaces only)

Captured from `page.on("response")` while the SPA loaded `#artifacts` and
`#proof`. All hits are GET 200 to the real `127.0.0.1:8765` backend; nothing
was mocked or stubbed.

| URL | Method | Status |
| --- | --- | --- |
| `/api/proof/bundles` | GET | 200 |
| `/api/proof/bundles` | GET | 200 |
| `/api/artifacts` | GET | 200 |
| `/api/artifacts/list` | GET | 200 |
| `/api/system/snapshot` | GET | 200 |
| `/api/system/snapshot` | GET | 200 |
| `/api/proof/bundles` | GET | 200 |

## Evidence file inventory

| File | Size (bytes) | sha256 |
| --- | --- | --- |
| `03_implementation/ui/test-results/w18-a8/audit.json` | 9 669 | `877bd0502fdf6f167a8b0b484fafc00ca3ad13aab1ee3c6ff0ecea3d1e4c1108` |
| `03_implementation/ui/test-results/w18-a8/01-artifacts-tab-loaded.png` | 162 075 | `56e4b80bbb80035ced81d963046b02e00891f9fb3387b97353b6943dd353ea03` |
| `03_implementation/ui/test-results/w18-a8/02-artifacts-tab-after-post.png` | 162 075 | `56e4b80bbb80035ced81d963046b02e00891f9fb3387b97353b6943dd353ea03` |
| `03_implementation/ui/test-results/w18-a8/03-proof-tab-detail.png` | 136 298 | `9c0f8578fe092f51f9e41df02178b451a4a8ea6e7496742407686ed14342c01c` |

Note on screenshots 01 and 02 sharing a sha256: the `#artifacts` tab's React
state for `artifacts[]` is populated once on mount (via
`loadArtifacts()`), and the audit's post-upload re-navigation to `#artifacts`
re-renders the same client-side state because the tab doesn't refetch on
hash re-entry. The newly posted artifact is still proven to exist via direct
`GET /api/artifacts` in step 13 (`artifact_appears_in_list`) and via the
on-disk binary at step 12 (`post_artifact_on_disk`). Both screenshots show
the proof-bundles section in its real loaded state with all 38 files
rendered from `/api/artifacts/list`.

## Console / network noise observed

- `consoleErrors`: 0
- `pageErrors`: 0
- `networkFailures`: 1 — `GET http://127.0.0.1:8765/api/events/stream` aborted
  with `net::ERR_ABORTED` when the test page closed. This is the SSE
  long-poll torn down on page close; the backend never returned an error
  code. Filtered as noise.

## How the proof was produced

The Playwright spec runs in `chromium-w18-a8` against the already-live
stack (FastAPI :8765 + Vite :5173). The dedicated config
`playwright.w18-a8.config.ts` has no `webServer` block, so the audit
exercises whatever real stack is running. The spec uses no mocks, no route
stubs, no fixtures other than its own randomly-generated probe body.

Steps that involve the GUI use:

- `page.on("response")` to record every backend response the page issues,
  later asserting that `/api/artifacts/list`, `/api/artifacts`, and
  `/api/proof/bundles` were really called by the SPA itself (not just by
  the spec's `APIRequestContext`). This is what makes the verdict
  `PASS_REAL` instead of a backend-only pass.
- `data-testid` selectors: `artifacts-root`, `proof-bundles`, `proof-root`,
  `proof-bundle-{id}`, `proof-detail`.
- The proof "View" link is an `<a target="_blank">` whose href is
  asserted to be `/api/artifacts/proof/{filename}`; the spec then fetches
  the same URL via `APIRequestContext` and compares bytes to the direct
  backend fetch to prove the GUI link is wired to the same backend route.

Steps that exercise the backend directly use Playwright's
`request: APIRequestContext` against the live `127.0.0.1:8765` backend.

## Reproduction

```powershell
# Backend (already running for this audit, started elsewhere):
#   FastAPI on http://127.0.0.1:8765
#   Vite on   http://localhost:5173

Set-Location G:\Github\Hermes3D\.claude\worktrees\w18-a8\03_implementation\ui
$env:LIVE_BASE_URL = 'http://127.0.0.1:8765'
npx playwright test --config=playwright.w18-a8.config.ts --reporter=list
```

Expected output:

```
Running 1 test using 1 worker
[W18-A8] verdict=PASS_REAL steps=21 -> .../test-results/w18-a8/audit.json
  ok 1 [chromium-w18-a8] › tests\e2e\w18-a8-artifact-file-proof.spec.ts:108:1 › W18-A8 — real artifact / proof endpoints are wired end-to-end (6.7s)
  1 passed (7.9s)
```

## Hermes evidence chain

- Lock acquired: `lock.acquired` ev_24d1055ee244193b — owner `w18-a8`, files
  (handoff md + playwright config + spec).
- Heartbeats sent during execution.
- Gate passed: `gate.passed` ev_2b2bf7aa236bcda3 — verdict `PASS_REAL`,
  steps 21/21.
- `hermes_run_gate gateId=git-status` run on the worktree returned
  `exit_code=0` (`gate_git-status_1778497459248`) — confirms the worktree
  is in a clean, reportable state (only the 2 new untracked W18-A8 files
  present at gate time, since the handoff md was added afterward).

## Hard rules observed

- No mocks of `/api/artifacts/*` or `/api/proof/*`.
- No `test.skip`, no conditional skip blocks. The spec fails fast on any
  missing surface.
- No printer-control API calls anywhere in the spec.
- Every major UI state has a screenshot.
- The audit JSON is hash-chained back to the Hermes evidence ledger via
  the `gate.passed` evidence entry.

## Out of scope (NOT part of this audit)

- **Starting a physical print or dispatching to a printer.** Operator
  freeze. The pinned verdicts `GUI_PHYSICAL_PRINT_GREEN` and
  `GUI_PRINTER_DRY_RUN_GREEN` remain `OUT_OF_SCOPE_BY_OPERATOR`.
- **Job submission.** That lane is W18-A7 PASS_REAL and untouched.
- **Signed proof bundles / sigstore signing.** `/api/proof/events`
  explicitly returns `verified:false` and `reason:"Recorded as local
  audit evidence only; not a signed proof bundle."` — the audit asserts
  that contract honestly rather than claiming bundles are signed.
- **Bulk artifact deletion or schema migration.** Read + create only.

## Files touched by this lane

- `03_implementation/docs/handoffs/W18-A8_ARTIFACT_FILE_PROOF_2026-05-11.md` (this file)
- `03_implementation/ui/playwright.w18-a8.config.ts` (new dedicated config)
- `03_implementation/ui/tests/e2e/w18-a8-artifact-file-proof.spec.ts` (new audit spec)

Generated artifacts (untracked by intent — produced by the run):

- `03_implementation/ui/test-results/w18-a8/audit.json`
- `03_implementation/ui/test-results/w18-a8/01-artifacts-tab-loaded.png`
- `03_implementation/ui/test-results/w18-a8/02-artifacts-tab-after-post.png`
- `03_implementation/ui/test-results/w18-a8/03-proof-tab-detail.png`
- `03_implementation/var/artifacts/c656750c810c445587c5d0e3c927108b_artifact.bin` (probe — labelled, identifiable, safe to leave or to garbage-collect)

## Confirmation

No printer hardware touched. Pinned verdicts unchanged.
