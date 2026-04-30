"""End-to-end acceptance runner for the desk-organizer test case.

This is the binding executable acceptance test for the contract kit. Run::

    python 04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py

It:
  1. Builds all 4 acceptance variants of the parametric desk organizer
  2. For each variant, runs Truth Gate (no specific printer, generic check)
  3. For each variant, validates against every fleet printer where it fits
  4. For each (variant, printer) pair that passes, renders 6 views and
     produces a signed proof envelope
  5. Writes a summary report (markdown + json) to ./var/acceptance-results/

Exit code:
  0  every required combination passed
  1  at least one required combination failed
  2  setup error (missing dependency, etc.)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Make the kit importable without installing the package
HERE = Path(__file__).resolve().parent
KIT_ROOT = HERE.parent
SRC = KIT_ROOT / "02-SCAFFOLDING" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _emoji(ok: bool) -> str:
    return "✅" if ok else "❌"


def main() -> int:
    try:
        from hermes3d.core.design.desk_organizer import (
            OrganizerSpec, acceptance_variants, build_organizer,
        )
        from hermes3d.core.printers import (
            FLEET, fits_bed, get_profile,
        )
        from hermes3d.core.proof.proof_envelope import write_proof
        from hermes3d.core.validation.truth_gate import (
            TruthGateConfig, run_truth_gate, CheckStatus,
        )
        from hermes3d.core.visual.render import render_all_views
    except Exception as exc:  # noqa: BLE001
        print(f"Setup error: cannot import hermes3d modules: {exc}",
              file=sys.stderr)
        return 2

    # Proof key resolution is handled centrally by core.proof.proof_envelope:
    # HERMES3D_PROOF_KEY when set, otherwise the documented dev default
    # (b"hermes3d-default-proof-key-not-secret") with a WARNING log.
    # The acceptance runner does NOT override it — that would create a
    # second default and break the conformance runner's verifier.

    out_root = KIT_ROOT / "var" / "acceptance-results"
    out_root.mkdir(parents=True, exist_ok=True)
    started_unix = time.time()
    results: list[dict] = []

    print(f"Hermes3D-OS Lite — Acceptance Runner")
    print(f"  output dir: {out_root}")
    print()

    variants = list(acceptance_variants())
    fleet_size = len(FLEET)
    grand_pass = grand_fail = grand_xfail = 0

    for variant_name, spec in variants:
        print(f"━━━ Variant: {variant_name} "
              f"({spec.width_mm:.0f}×{spec.depth_mm:.0f}×{spec.height_mm:.0f} mm)")
        # Build mesh once
        mesh = build_organizer(spec)
        variant_dir = out_root / variant_name
        variant_dir.mkdir(exist_ok=True)
        stl_path = variant_dir / f"{variant_name}.stl"
        mesh.export(stl_path)

        # Generic Truth Gate (no printer)
        generic_report = run_truth_gate(stl_path, TruthGateConfig())
        generic_ok = generic_report.passed
        print(f"  generic Truth Gate: {_emoji(generic_ok)}  "
              f"{generic_report.overall_status.value}")
        if not generic_ok:
            grand_fail += 1
            for c in generic_report.checks:
                if c.status == CheckStatus.FAIL:
                    print(f"    fail: {c.name}: {c.message}")
            results.append({
                "variant": variant_name, "printer": "(generic)",
                "outcome": "fail", "reason": "generic Truth Gate failed",
            })
            continue

        # Render once per variant — same mesh, same views
        render_dir = variant_dir / "views"
        rendered = render_all_views(mesh, render_dir, name_prefix=variant_name)

        for profile in FLEET:
            # Pre-flight bbox check using simple math (saves work when too big)
            radius = max(spec.width_mm, spec.depth_mm) / 2.0
            extents = (spec.width_mm, spec.depth_mm, spec.height_mm)
            fits, _ = fits_bed(profile, extents, radius)
            if not fits:
                # Expected failure — record as xfail and skip
                grand_xfail += 1
                results.append({
                    "variant": variant_name,
                    "printer": profile.profile_id,
                    "outcome": "xfail",
                    "reason": "geometrically too large for bed",
                })
                print(f"  {profile.profile_id:25s}  xfail (won't fit)")
                continue

            cfg = TruthGateConfig(printer_profile_id=profile.profile_id)
            rep = run_truth_gate(stl_path, cfg)
            ok = rep.passed
            outcome = "pass" if ok else "fail"

            # Sign proof envelope on success
            proof_path: Path | None = None
            if ok:
                proof_path = variant_dir / f"proof-{profile.profile_id}.json"
                write_proof(
                    mesh_path=stl_path,
                    output_path=proof_path,
                    truth_gate_report=rep,
                    visual_evidence_paths=rendered,
                    generator_name="desk_organizer",
                    generator_version="1.0.0",
                    generator_signature=spec.signature(),
                )

            results.append({
                "variant": variant_name,
                "printer": profile.profile_id,
                "outcome": outcome,
                "reason": rep.overall_status.value,
                "proof_path": str(proof_path) if proof_path else None,
            })
            if ok:
                grand_pass += 1
                print(f"  {profile.profile_id:25s}  {_emoji(True)} pass    "
                      f"-> {proof_path.name if proof_path else ''}")
            else:
                grand_fail += 1
                fail = next((c for c in rep.checks
                             if c.status == CheckStatus.FAIL), None)
                why = fail.message if fail else "(unknown)"
                print(f"  {profile.profile_id:25s}  {_emoji(False)} fail    {why}")

    duration = time.time() - started_unix

    summary = {
        "timestamp_unix": started_unix,
        "duration_seconds": round(duration, 2),
        "variants_tested": [v for v, _ in variants],
        "fleet_size": fleet_size,
        "totals": {
            "pass": grand_pass,
            "fail": grand_fail,
            "xfail": grand_xfail,
            "expected_pass": len(variants) * fleet_size - grand_xfail,
        },
        "results": results,
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# Acceptance Run Summary\n",
        f"- Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(started_unix))}",
        f"- Duration: {duration:.2f} s",
        f"- Variants: {len(variants)}",
        f"- Printers in fleet: {fleet_size}",
        "",
        f"**Pass:** {grand_pass}  **Fail:** {grand_fail}  "
        f"**xfail (geometric):** {grand_xfail}",
        "",
        "| Variant | Printer | Outcome | Reason |",
        "|---|---|---|---|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['variant']} | {r['printer']} | {r['outcome']} | {r['reason']} |"
        )
    (out_root / "summary.md").write_text("\n".join(md_lines), encoding="utf-8")

    print()
    print(f"Done in {duration:.1f} s")
    print(f"  pass={grand_pass}  fail={grand_fail}  xfail={grand_xfail}")
    print(f"  summary -> {out_root / 'summary.json'}")
    print(f"  summary -> {out_root / 'summary.md'}")
    return 0 if grand_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
