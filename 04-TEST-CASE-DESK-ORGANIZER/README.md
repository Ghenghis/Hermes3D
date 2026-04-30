# Test Case — Desk Organizer

> The end-to-end acceptance test that proves Hermes3D-OS Lite can take
> a parametric design through every layer of the system and produce a
> dispatch decision + slicer-ready output for every printer in the
> fleet.

---

## What this test does

The "desk organizer" is a **parametric** physical product — a tray
with adjustable compartments — that exercises every interesting code
path in the kit:

1. The **design generator** (`core.design.desk_organizer`) emits an
   STL from a small parameter object: width × depth × height,
   compartment count × compartment depth, wall thickness.
2. **Mesh analysis** runs on the result (overhang %, watertightness,
   bridge count).
3. **Dispatcher** scores every printer against the part with each of
   four different priority strategies.
4. **Truth gates** vet the proposed dispatch.
5. **Proof envelope** signs the outcome.

The test is parameterised over **4 design variants × 12 printers = 48
cells**. Every cell produces a signed proof envelope under
`var/acceptance-results/<utc>/<printer_id>/<variant>/proof.json`.

The full run completes in **<10 seconds** on the development machine
and in CI.

---

## Variants

| Variant | Width | Depth | Height | Compartments | Walls | Stresses |
|---------|-------|-------|--------|--------------|-------|----------|
| `compact` | 80 | 80 | 30 | 4 | 1.6 | Smallest cartesian + smallest delta |
| `standard` | 200 | 150 | 50 | 6 | 2.0 | Common case — most printers eligible |
| `wide` | 350 | 280 | 60 | 8 | 2.4 | Excludes most deltas; favours CR-6 Max |
| `tall` | 120 | 120 | 320 | 4 | 2.0 | Exercises delta Z-height; fails on short cartesians |

Each variant uses the same single material (`PLA`) and quality
(`normal`) for comparability. The **printer × variant** matrix shows
which printers could (and couldn't) handle which jobs.

---

## How to run

From the kit root:

```bash
# Full run: 4 × 12 = 48 cells
python 04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py

# Single variant
python 04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py --variant tall

# JSON output for downstream processing
python 04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py --json
```

Outputs:

```
var/acceptance-results/<utc>/
├── summary.json                           # 48-cell matrix
├── summary.proof.json                     # signed envelope of summary
├── flsun_qqs_pro/
│   ├── compact/proof.json
│   ├── standard/proof.json
│   ├── wide/proof.json
│   └── tall/proof.json
├── flsun_t1_a/
│   ├── compact/proof.json
│   └── ...
└── ...
```

Each per-cell proof envelope records:

- The variant parameters (width × depth × ...)
- The printer's profile snapshot (id, kinematics, bed shape)
- The `fits` decision (true/false) with reasons
- The dispatcher score
- The HMAC-SHA256 signature

---

## How CI uses it

The CI workflow (`.github/workflows/ci.yml` → `layer_b_smoke_and_acceptance`)
runs the full acceptance suite and uploads `var/acceptance-results/`
as an artifact. The job fails if:

- Any cell crashes (this is a contract violation, not an expected
  outcome).
- The summary proof envelope can't be verified.
- The variant×printer fit matrix differs from the expected matrix in
  `04-TEST-CASE-DESK-ORGANIZER/expected/fit_matrix.json` (when it
  exists).

---

## What this test isn't

- It does **not** drive a real slicer (slicer integration is covered
  by `tests/integration/test_slicer_runner.py`).
- It does **not** upload to a real Moonraker (Moonraker integration is
  covered by `tests/integration/test_moonraker_client.py`).
- It does **not** assert "this print would succeed" — only "the
  dispatch decision is consistent and the proof verifies."

The slicer + Moonraker integrations are best-effort in CI: they skip
when the optional deps aren't installed, with a clear marker in the
test name. This kept the acceptance suite fast and reliable.

---

## Why a desk organizer

The shape was chosen to:

- Be **parametric** — a small change to the inputs produces a
  meaningful change to the geometry.
- Have an **interesting overhang profile** — the compartment dividers
  test the overhang heuristic in `mesh_analyzer`.
- Have a **range of bbox shapes** — from "fits everything" to "fits
  only the largest bed."
- Be **printable in real life** — the variants correspond to a real
  product Dave would print on his farm.

The point of the test isn't the desk organizer per se. It's that the
kit's contract is exercised end-to-end on a non-trivial real artifact,
not a synthetic cube.

---

## See also

- `DESIGN_BRIEF.md` — the original design brief for the parametric model.
- `ACCEPTANCE_CRITERIA.md` — the explicit pass/fail rules.
- `run_acceptance.py` — the runner. ~250 lines, no surprises.
- `00-CONTRACT/TRUTH_AND_PROOF_SYSTEM.md` — the proof envelope format.
