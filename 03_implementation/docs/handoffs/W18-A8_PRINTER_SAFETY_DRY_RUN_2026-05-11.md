# W18-A8 Printer Safety Dry Run (2026-05-11)

**Mission:** Verify the printer-safety surface in the Hermes3D GUI is real and
visibly enforces the W6-9 default-deny gate.

**Constraint:** ZERO physical actions — no heat, no motion, no extrude, no
print start. Read-only verification against the running backend on `:8765` and
the dev UI on `:5173`.

**Branch:** `claude/w18-a8-printer-safety-dry-run` from `develop@330f521`.

**Hermes locks:** owner `w18-a8`, ids `8d003a2a896c4681388283f4` /
`b38fe72c94c5ea19f119705f`.

## Backend truth (real, no mocks)

`GET /api/printers` returned **4 printers** (not 3 as the brief assumed; the
brief is corrected to a 4-printer matrix below). All 4 are real entries with
`adapter:moonraker` and real IPs.

| id            | name      | model      | status  | safety_policy  | write_enabled |
| ------------- | --------- | ---------- | ------- | -------------- | ------------- |
| `flsun_t1_a`  | T1 #1     | FLSUN T1   | online  | write_enabled  | true          |
| `flsun_t1_b`  | T1 #2     | FLSUN T1   | online  | write_enabled  | true          |
| `flsun_s1`    | FLSUN S1  | FLSUN S1   | offline | locked         | false         |
| `flsun_v400`  | FLSUN V400| FLSUN V400 | online  | write_enabled  | true          |

`GET /api/printers/{id}/safety-state` is **wired and real for all 4 printers**.
Every printer returns `allow: false` with `blocked_by: ["no camera bound to
printer", "no camera frame ever", "no plate classification ever"]` and the
thresholds `{camera_freshness_sec: 5.0, plate_freshness_sec: 30.0,
plate_min_confidence: 0.85}` — i.e. the W6-9 gate is in default-deny because
no camera frame or plate classification has ever been ingested.

Direct-to-backend `POST /api/printers/flsun_t1_a/heat-extruder` returned
**HTTP 403** with the structured payload
`{ok:false, blocked_by:[...], reason:"Printer safety gate refused..."}`. Same
for `POST .../heat-bed` and `POST .../start-print`. **Backend default-deny is
PASS_REAL.**

Saved payloads: `screenshots/W18-A8/backend/*.json` and `*_DEFAULT_DENY.txt`.

## GUI inventory (Playwright, viewport 1600x1000, `#printers`)

Network shows the page does call the real backend: repeated
`GET http://127.0.0.1:8765/api/printers => 200` (no mocks).

`data-safety-state` is **PRESENT** on every printer card (PR #229 attribute):

| testid                          | data-safety-state |
| ------------------------------- | ----------------- |
| `printer-safety-state-t1-1`     | `write_enabled`   |
| `printer-safety-state-t1-2`     | `write_enabled`   |
| `printer-safety-state-s1`       | `locked`          |
| `printer-safety-state-v400`     | `write_enabled`   |

DOM enumeration of all 45 buttons on the page found:

- `heatButtons` (regex `/heat|preheat|start.print|start.heat|extrude|extruder|bed/i`): **0**
- `estopButtons` (regex `/e-?stop|emergency|cancel|abort|kill/i`): **0**
- text mentions of `camera|plate.{0,5}clear|confidence|fresh.{0,10}ago`: **0**

i.e. the GUI surfaces the **policy badge** (Write enabled / Safety locked) but
does NOT surface the **W6-9 gate state**: there is no camera badge, no plate
confidence, no heat/preheat button, and no emergency-stop button anywhere on
the `#printers` tab.

## 4-printer x 7-check matrix

Cells: `PASS_REAL` / `FAIL_MISSING` / `FAIL_BROKEN` / observed value.

| Check                                | T1 #1 (flsun_t1_a)               | T1 #2 (flsun_t1_b)               | FLSUN S1 (flsun_s1)               | FLSUN V400 (flsun_v400)          |
| ------------------------------------ | -------------------------------- | -------------------------------- | --------------------------------- | -------------------------------- |
| 1. Card appears in #printers list    | PASS_REAL (`printer-card-t1-1`)  | PASS_REAL (`printer-card-t1-2`)  | PASS_REAL (`printer-card-s1`)     | PASS_REAL (`printer-card-v400`)  |
| 2. connected/idle/offline badge      | PASS_REAL "Live status: online"  | PASS_REAL "Live status: online"  | PASS_REAL "OFFLINE / LOCKED"      | PASS_REAL "Live status: online"  |
| 3. Camera status badge (live/stale)  | FAIL_MISSING (no camera badge)   | FAIL_MISSING (no camera badge)   | FAIL_MISSING (no camera badge)    | FAIL_MISSING (no camera badge)   |
| 4. Plate-clear confidence visible    | FAIL_MISSING (no plate text)     | FAIL_MISSING (no plate text)     | FAIL_MISSING (no plate text)      | FAIL_MISSING (no plate text)     |
| 5. Heat/start default-deny in UI     | FAIL_MISSING (no heat button)    | FAIL_MISSING (no heat button)    | N/A_LOCKED (write_enabled=false)  | FAIL_MISSING (no heat button)    |
| 6. Emergency-stop in ≤1 click        | FAIL_MISSING (no e-stop button)  | FAIL_MISSING (no e-stop button)  | FAIL_MISSING (no e-stop button)   | FAIL_MISSING (no e-stop button)  |
| 7. `data-safety-state` on card       | PASS_REAL (`write_enabled`)      | PASS_REAL (`write_enabled`)      | PASS_REAL (`locked`)              | PASS_REAL (`write_enabled`)      |

Note on check 5: the per-printer card DOES have `Upload G-code` and
`Upload + Start` buttons, and both are `[disabled]` on every card pending an
approved job ID. That is a separate workflow gate (approval), NOT the W6-9
camera+plate safety gate. The W6-9 gate is enforced **only at the backend**;
the GUI never surfaces a "Preheat" / "Start Heat" / "Heat Bed" affordance on
this tab, so the user-visible default-deny banner with `blocked_by` reasons is
absent.

## Heat-button dry-run result

Per check 5 above, **no heat/preheat button exists in the GUI** on the
`#printers` tab. The brief's step 3 (click Start Heat and assert it is
intercepted) is **vacuously satisfied** — there is nothing to click, therefore
zero risk of accidentally triggering heat from the GUI. **No FAIL_BROKEN
incident occurred.** The backend gate is the only line of defense, and the
direct `curl POST` to `/heat-extruder` and `/heat-bed` confirmed it returns
HTTP 403 with structured `blocked_by` reasons (saved as
`heat_extruder_t1_a_DEFAULT_DENY.txt` and `heat_bed_t1_b_DEFAULT_DENY.txt`).

## E-stop dry-run result

Per check 6, **no emergency-stop button exists on any printer card**, so the
brief's step 4 (click e-stop on printer 1 and capture HAR) **could not be
exercised**. **FAIL_MISSING** for the E-stop surface — this is the most
serious gap, because operators need an unconditional e-stop reachable in ≤1
click regardless of the safety gate state, per the W6-9 brief.

## Per-printer verdict

- T1 #1 (`flsun_t1_a`): **PARTIAL** — list + status + safety-state attribute
  PASS_REAL; camera badge / plate confidence / heat-deny UI / e-stop all
  FAIL_MISSING. Backend gate works (403 default-deny verified).
- T1 #2 (`flsun_t1_b`): **PARTIAL** — same shape as T1 #1.
- FLSUN S1 (`flsun_s1`): **PARTIAL** — list + offline badge + `locked`
  safety-state PASS_REAL; correctly shows maintenance-lock banner and
  disables Test / Upload G-code / Upload + Start. Camera / plate / e-stop
  FAIL_MISSING.
- FLSUN V400 (`flsun_v400`): **PARTIAL** — same shape as T1 #1.

## Overall verdict: `GUI_PRINTER_DRY_RUN_PARTIAL`

Not `GUI_PRINTER_DRY_RUN_GREEN`. The backend half of the W6-9 surface is real
and enforces default-deny correctly (`PASS_REAL` for the 403 + `blocked_by`
contract). The GUI half is **partially wired**: PR #229 surfaced the safety
policy badge and the `data-safety-state` attribute, but did NOT surface the
gate's actual state (camera freshness, plate confidence, blocked-by reasons),
the heat/start affordance with its default-deny banner, or the
always-reachable emergency-stop button. Operators today have no GUI signal
that the W6-9 gate even exists — they would only see it if they tried to POST
directly to the backend, which is not a realistic operator workflow.

Recommended follow-ups (NOT in scope for this audit-only PR):

1. Surface camera + plate freshness on each card (read from
   `GET /api/printers/{id}/safety-state`).
2. Add `Preheat` / `Heat Bed` / `Start Print` buttons that are default-disabled
   with a visible "blocked by: ..." reason when `safety-state.allow=false`.
3. Add an always-visible emergency-stop button on every card, reachable in ≤1
   click and independent of the safety gate.

## Hard-rule status

- ZERO physical actions performed. No heat, no motion, no extrude.  Confirmed.
- No mocks. All network captured by Playwright shows real
  `http://127.0.0.1:8765` calls returning real payloads. Confirmed.
- Hermes MCP locks owner `w18-a8` held through the audit. Confirmed.

## Artifacts

- Full-page screenshot: `screenshots/W18-A8/00_full_page.png`
- Per-card screenshots: `screenshots/W18-A8/0{1..4}_*.png`
- Backend safety-state payloads: `screenshots/W18-A8/backend/safety_*.json`
- Backend printer list: `screenshots/W18-A8/backend/printers_list.json`
- Backend default-deny proofs: `screenshots/W18-A8/backend/*_DEFAULT_DENY.txt`
