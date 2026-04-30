# Desk Organizer — Acceptance Criteria

> Pass / fail rules for the 48-cell acceptance run. The CI job
> `layer_b_smoke_and_acceptance` enforces every rule below.

---

## A. Coverage

| Rule | Pass when |
|------|-----------|
| **A1: Variant coverage** | Every one of the 4 canonical variants is run |
| **A2: Printer coverage** | Every one of the 12 printers in `printer_profiles.FLEET` is scored against every variant |
| **A3: Cell count** | The summary reports exactly 48 cells (4 × 12), no more, no fewer |
| **A4: No skipped cells** | Zero cells with status `error` or `crash`. Cells where the printer is incompatible report status `infeasible` with reasons, not `error` |

---

## B. Geometry

For every variant, the generated STL must satisfy:

| Rule | Pass when |
|------|-----------|
| **B1: Watertight** | `mesh_analyzer.analyze_mesh_file(stl).is_watertight == True` |
| **B2: Solid volume** | `mesh_analyzer.analyze_mesh_file(stl).is_volume == True` |
| **B3: Bounded triangles** | `triangle_count > 0` and `triangle_count < 50_000` |
| **B4: Overhang within tolerance** | `overhang_pct < 5%` at the 50° threshold |
| **B5: No critical risk flags** | `risk_flags` does not contain `non_watertight`, `nan_vertex`, or `inverted_normal` |

Any violation crashes the runner with a non-zero exit code. There is
no "warn and continue" — geometry generation is foundational.

---

## C. Dispatch decisions

| Rule | Pass when |
|------|-----------|
| **C1: `fits` matches geometry** | A printer is reported as fitting iff `fits_bed(printer, bbox_xy) and z_height >= bbox_z`. The runner cross-validates this against `core.printers.printer_profiles.fits_bed()` |
| **C2: `eligible` matches material capability** | A printer is reported eligible iff its profile satisfies the material's requirements (`MATERIAL_CAPABILITY`) |
| **C3: Selected printer is feasible** | If `selected_printer_id` is not None, the corresponding candidate must have `fits == True and eligible == True` |
| **C4: At least one feasible printer for compact + standard** | Both variants must have ≥1 feasible printer; if not, the test fails (this would mean the fleet itself has regressed) |
| **C5: Wide variant excludes Prusa MK3S+** | The MK3S+ has a 250×210 bed; it cannot fit a 350×280 part. The runner asserts the candidate is reported infeasible |
| **C6: Tall variant excludes Prusa MK3S+** | The MK3S+ has a 210 mm Z; it cannot fit a 320 mm tall part |

---

## D. Proof envelopes

| Rule | Pass when |
|------|-----------|
| **D1: One envelope per cell** | After the run, exactly 48 per-cell `proof.json` files exist under `var/acceptance-results/<utc>/` |
| **D2: One summary envelope** | `summary.json` and `summary.proof.json` exist at the top level of the run |
| **D3: All envelopes verify** | `proof-collect.{sh,ps1}` reports `verified=49, failed=0` (48 cells + 1 summary) |
| **D4: Canonical JSON** | Every envelope's `signature.value` re-derives correctly from the canonical-JSON encoding of the doc minus `signature` |
| **D5: Signature scheme is HMAC-SHA256** | `signature.algorithm == "HMAC-SHA256"` |
| **D6: Inputs are content-addressed** | `inputs.mesh_sha256` matches `sha256sum` of the generated STL byte-for-byte |

---

## E. Performance

| Rule | Pass when |
|------|-----------|
| **E1: Wall-clock time** | The full 48-cell run completes in <30 seconds on a workstation. (CI budget: <60 seconds.) |
| **E2: Memory bound** | Peak RSS during the run does not exceed 1 GB |
| **E3: No filesystem leakage** | The run creates files only under `var/acceptance-results/` and `var/proofs/` (and a single tmp dir cleaned on success) |

E1 and E2 are advisory in v5 — they're recorded in the summary but do
not fail the build. v5.1 promotes E1 to hard.

---

## F. Determinism

| Rule | Pass when |
|------|-----------|
| **F1: Same inputs → same STL** | Running the runner twice with the same parameters produces byte-identical STLs (same SHA-256) |
| **F2: Same inputs → same dispatch decision** | The selected printer for a (variant, fleet, strategy) tuple is identical across runs |
| **F3: Different proof signatures by run** | Each run produces a different `produced_at` timestamp and therefore a different signature, but the underlying decision is identical |

F3 is the contract: **decisions are reproducible; envelopes are
unique**. This is what lets us audit-trail without making the system
look like it's "doing the same thing each time."

---

## G. Honesty

| Rule | Pass when |
|------|-----------|
| **G1: Manifest matches reality** | `python 00-CONTRACT/_generate_manifest.py` after the run produces zero `unmentioned` files |
| **G2: Honesty diff clean** | `python scripts/honesty_diff.py` reports `drift=0` |
| **G3: No forbidden patterns** | `python scripts/forbidden_pattern_scan.py` reports `[OK] no forbidden patterns found.` |

Failing any of these means the kit is misrepresenting itself, which
is a contract-level violation — fail loudly.

---

## H. Failure modes the test specifically protects against

This list is non-exhaustive but representative. Each item corresponds
to a real failure pattern observed during kit development:

1. **Cached STL regression**: a previous test run's STL was
   accidentally reused after a parameter change. → guarded by F1
   (`mesh_sha256` recorded in the proof envelope).
2. **Silent dispatcher drift**: a refactor changed which printer
   "auto" selects without anyone noticing. → guarded by C1–C6
   (per-cell candidate reasoning recorded).
3. **Stub return**: a function returned a hard-coded "selected"
   string. → guarded by C1 + the forbidden-pattern scan + G3.
4. **Truth-gate bypass**: someone added an early-return that
   skipped a gate. → guarded by D1 (every gate's decision is part of
   the envelope).
5. **Signature scheme regression**: someone changed HMAC-SHA256 to
   plain SHA-256. → guarded by D4 + D5.

---

## I. What "passing" looks like

A successful run prints:

```
[acceptance] 48 cells in 6.7s, 0 errors
[acceptance] feasible matrix:
            compact standard wide tall
flsun_qqs_pro    ✓     ✓      ·    ✓
flsun_t1_a       ✓     ✓      ·    ✓
flsun_t1_b       ✓     ✓      ·    ✓
flsun_super_racer ✓    ✓      ·    ✓
flsun_s1         ✓     ✓      ·    ✓
flsun_v400       ✓     ✓      ·    ✓
creality_cr10s   ✓     ✓      ·    ✓
creality_cr6_max ✓     ✓      ✓    ✓
prusa_mk3s       ✓     ✓      ·    ·
sovol_sv01       ✓     ✓      ·    ·
tronxy_d01_pro   ✓     ✓      ·    ✓
tronxy_x5sa_pro  ✓     ✓      ·    ✓
[acceptance] summary signed: a3f1e8c2d4...
[acceptance] proof verifier: 49/49 OK
```

When you see that on a fresh clone of the kit on a fresh machine,
the kit's contract is intact.
