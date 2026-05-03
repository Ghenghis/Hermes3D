"""Hermes3D CLI entry point.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §17 (CLI Surface)

Run with::

    python -m hermes3d <command> [...args]

Or after install::

    hermes3d <command> [...args]

Commands:
    fleet probe                         Health-check all 12 printers
    fleet status                        Render dashboard table
    fleet list                          Print profile_id of every printer

    validate <stl> [--printer ID]       Run Truth Gate on a mesh
    validate-fleet <stl>                Run Truth Gate against every printer

    generate organizer [opts]           Generate parametric desk organizer

    dispatch <stl> [--material PLA]     Pick best printer for a part
                  [--strategy auto]

    slice <stl> --printer ID            Slice for one printer
    analyze-gcode <gcode>               G-code metric report

    queue list                          List active jobs
    queue show <job_id>                 Show full job record
    queue cancel <job_id>               Cancel a job

    spool list / add / load / consume   Spool registry CRUD
    proof verify <proof.json>           Verify proof envelope HMAC + files
    doctor [--strict]                   Probe local LLM providers (ADR-015)

The CLI's exit code is 0 on success, 1 on a structured error, 2 on usage
mistakes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def _printers_table_compact() -> str:
    from hermes3d.core.printers import FLEET

    lines = []
    for p in FLEET:
        bed = (
            f"{p.bed.x_mm:.0f}x{p.bed.y_mm:.0f}"
            if p.bed.kind == "rectangular"
            else f"Ø{p.bed.diameter_mm:.0f}"
        )
        lines.append(
            f"  {p.profile_id:25s}  {p.manufacturer:18s}  {p.model:24s}  "
            f"{p.kinematics.value:9s}  {bed:>9s} × {p.z_height_mm:.0f}"
        )
    return "\n".join(lines)


# -- fleet --------------------------------------------------------------------


def cmd_fleet_probe(args: argparse.Namespace) -> int:
    from hermes3d.core.printers.moonraker_client import probe_fleet

    entries = probe_fleet(timeout_s=args.timeout)
    reachable = sum(1 for e in entries if e["reachable"])
    print(f"Probed {len(entries)} printers — reachable: {reachable}")
    print()
    print(f"{'profile_id':25s}  {'reach':6s}  {'klippy':12s}  {'moonraker':14s}  url")
    print("-" * 100)
    for e in entries:
        print(
            f"{e['profile_id']:25s}  "
            f"{'yes' if e['reachable'] else 'no':6s}  "
            f"{(e['klippy_state'] or '-'):12s}  "
            f"{(e['moonraker_version'] or '-'):14s}  "
            f"{e['moonraker_url']}"
        )
    return 0


def cmd_fleet_status(args: argparse.Namespace) -> int:
    from hermes3d.core.agents.job_queue import JobQueue
    from hermes3d.core.farm import collect_fleet_status, render_dashboard_table
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    queue = JobQueue(args.queue) if args.queue and Path(args.queue).exists() else None
    spool = SpoolTracker(args.spools) if args.spools and Path(args.spools).exists() else None
    entries = collect_fleet_status(queue=queue, spool_tracker=spool, timeout_s=args.timeout)
    print(render_dashboard_table(entries))
    return 0


def cmd_fleet_list(args: argparse.Namespace) -> int:
    print("Hermes3D fleet (12 printers):")
    print(_printers_table_compact())
    return 0


# -- validate -----------------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    from hermes3d.core.validation.truth_gate import (
        CheckStatus,
        TruthGateConfig,
        run_truth_gate,
    )

    cfg = TruthGateConfig(printer_profile_id=args.printer)
    rep = run_truth_gate(args.stl, cfg)
    print(f"Truth Gate report — {rep.mesh_path}")
    print(f"  overall: {rep.overall_status.value.upper()}")
    print(f"  duration: {rep.duration_seconds:.2f}s")
    for c in rep.checks:
        marker = {"pass": "✓", "fail": "✗", "skip": "·", "error": "!"}.get(c.status.value, "?")
        print(f"  {marker} {c.name:24s} {c.status.value:5s}  {c.message}")
    if args.json:
        print()
        print(rep.to_json())
    return 0 if rep.overall_status == CheckStatus.PASS else 1


def cmd_validate_fleet(args: argparse.Namespace) -> int:
    from hermes3d.core.printers import list_ids
    from hermes3d.core.validation.truth_gate import (
        CheckStatus,
        TruthGateConfig,
        run_truth_gate,
    )

    fail = 0
    for pid in list_ids():
        cfg = TruthGateConfig(printer_profile_id=pid)
        rep = run_truth_gate(args.stl, cfg)
        marker = "✓" if rep.overall_status == CheckStatus.PASS else "✗"
        if rep.overall_status != CheckStatus.PASS:
            fail += 1
            failed = next((c for c in rep.checks if c.status == CheckStatus.FAIL), None)
            reason = failed.message if failed else "(unknown)"
            print(f"  {marker} {pid:25s} FAIL  {reason}")
        else:
            print(f"  {marker} {pid:25s} pass")
    print()
    print(f"Result: {len(list_ids()) - fail}/{len(list_ids())} printers accept this mesh")
    return 0 if fail == 0 else 1


# -- generate -----------------------------------------------------------------


def cmd_generate_organizer(args: argparse.Namespace) -> int:
    from hermes3d.core.design.desk_organizer import (
        OrganizerSpec,
        export_organizer,
    )

    spec = OrganizerSpec(
        width_mm=args.width,
        depth_mm=args.depth,
        height_mm=args.height,
        tray_count=args.trays,
        pen_count=args.pens,
        phone_slot=not args.no_phone_slot,
        cable_passthrough=not args.no_cable,
    )
    out = Path(args.out)
    export_organizer(spec, out)
    print(f"Wrote {out.resolve()}  (signature={spec.signature()})")
    return 0


# -- dispatch -----------------------------------------------------------------


def cmd_dispatch(args: argparse.Namespace) -> int:
    import trimesh

    from hermes3d.core.agents.dispatcher import (
        DispatchRequest,
        DispatchStrategy,
        dispatch,
    )

    mesh = trimesh.load_mesh(args.stl, force="mesh")
    extents = tuple(float(e) for e in mesh.extents)
    xy = mesh.vertices[:, :2]
    if xy.size:
        import numpy as np

        center = (xy.min(axis=0) + xy.max(axis=0)) / 2.0
        radius = float(np.max(np.linalg.norm(xy - center, axis=1)))
    else:
        radius = None
    req = DispatchRequest(
        mesh_extents_mm=extents,
        mesh_xy_radius_mm=radius,
        material=args.material,
        quality_level=args.quality,
        strategy=DispatchStrategy(args.strategy),
    )
    decision = dispatch(req)
    print(f"Dispatch decision for {args.stl}")
    print(f"  material: {args.material}, strategy: {args.strategy}")
    print(f"  selected: {decision.selected_printer_id or '(none eligible)'}")
    print(f"  rationale: {decision.rationale}")
    print()
    print("Top candidates:")
    for c in decision.candidates[:5]:
        marker = "✓" if c.eligible else "✗"
        print(f"  {marker} {c.printer_id:25s} score={c.score:.3f}  eligible={c.eligible}")
        if c.blockers:
            for b in c.blockers[:2]:
                print(f"        blocker: {b}")
    return 0 if decision.has_selection else 1


# -- slice --------------------------------------------------------------------


def cmd_slice(args: argparse.Namespace) -> int:
    from hermes3d.core.slicer.slicer_runner import SlicerError, slice_mesh

    out_dir = (
        Path(args.out_dir) if args.out_dir else Path(tempfile.mkdtemp(prefix="hermes3d_slice_"))
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = slice_mesh(
            args.stl, profile=args.profile, output_dir=out_dir, timeout_seconds=args.timeout
        )
    except SlicerError as exc:
        print(f"Slice failed: {exc}", file=sys.stderr)
        return 1
    print(f"Sliced to: {result.gcode_path}")
    if result.metadata:
        for k, v in result.metadata.items():
            print(f"  {k}: {v}")
    return 0


# -- analyze-gcode ------------------------------------------------------------


def cmd_analyze_gcode(args: argparse.Namespace) -> int:
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    a = analyze_gcode(args.gcode)
    if args.json:
        print(json.dumps(a.to_dict(), indent=2))
        return 0
    print(f"G-code analysis — {a.path}")
    print(f"  slicer: {a.slicer_name} {a.slicer_version}")
    if a.estimated_print_time_min is not None:
        print(f"  print time: {a.estimated_print_time_min:.1f} min ({a.estimated_print_time_h}h)")
    if a.filament_used_mm:
        print(f"  filament: {a.filament_used_mm:.0f} mm / {a.filament_used_g:.1f} g")
    if a.layer_count:
        print(f"  layers: {a.layer_count} @ {a.layer_height_mm} mm")
    if a.nozzle_temp_c:
        print(f"  temps: nozzle {a.nozzle_temp_c}°C, bed {a.bed_temp_c}°C")
    print(f"  bed mesh loaded: {a.bed_mesh_loaded}, pressure advance: {a.pressure_advance_set}")
    if a.risk_flags:
        print("  RISK FLAGS:")
        for f in a.risk_flags:
            print(f"    ⚠  {f}")
    return 0


# -- queue --------------------------------------------------------------------


def cmd_queue_list(args: argparse.Namespace) -> int:
    from hermes3d.core.agents.job_queue import JobQueue

    q = JobQueue(args.queue)
    jobs = q.list()
    if not jobs:
        print("(empty queue)")
        return 0
    print(f"{len(jobs)} jobs:")
    for j in jobs:
        print(
            f"  {j.job_id[:12]}  {j.state.value:11s}  "
            f"{j.material:6s}  {j.target_printer_id or '-':25s}  "
            f"{Path(j.mesh_path).name}"
        )
    return 0


def cmd_queue_show(args: argparse.Namespace) -> int:
    from hermes3d.core.agents.job_queue import JobQueue

    q = JobQueue(args.queue)
    try:
        j = q.get(args.job_id)
    except KeyError:
        print(f"Job {args.job_id} not found", file=sys.stderr)
        return 1
    print(json.dumps(j.to_dict(), indent=2))
    return 0


def cmd_queue_cancel(args: argparse.Namespace) -> int:
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    q = JobQueue(args.queue)
    j = q.transition_job(args.job_id, JobState.CANCELLED, reason="cancelled via CLI")
    print(f"Cancelled job {j.job_id[:12]}  state={j.state.value}")
    return 0


# -- spool --------------------------------------------------------------------


def cmd_spool_list(args: argparse.Namespace) -> int:
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(args.spools)
    entries = st.list()
    if not entries:
        print("(no spools registered)")
        return 0
    for s in entries:
        loaded = f"on {s.loaded_on_printer}" if s.loaded_on_printer else "shelf"
        print(
            f"  {s.spool_id[:8]}  {s.material:6s}  {s.color:18s}  "
            f"{s.vendor:14s}  {s.remaining_grams:6.1f}/{s.initial_grams:.0f}g "
            f"({s.percent_remaining:5.1f}%)  [{loaded}]"
        )
    return 0


def cmd_spool_add(args: argparse.Namespace) -> int:
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(args.spools)
    s = st.add(
        material=args.material,
        color=args.color,
        color_hex=args.color_hex,
        vendor=args.vendor,
        initial_grams=args.grams,
    )
    print(f"Registered spool {s.spool_id}")
    return 0


def cmd_spool_load(args: argparse.Namespace) -> int:
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(args.spools)
    s = st.load_on_printer(args.spool_id, args.printer)
    print(f"Loaded {s.spool_id[:8]} ({s.material} {s.color}) on {args.printer}")
    return 0


def cmd_spool_consume(args: argparse.Namespace) -> int:
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(args.spools)
    s = st.consume(args.spool_id, args.grams, job_id=args.job_id)
    print(f"Consumed {args.grams}g — remaining {s.remaining_grams}g ({s.percent_remaining:.1f}%)")
    return 0


# -- proof --------------------------------------------------------------------


def cmd_proof_verify(args: argparse.Namespace) -> int:
    from hermes3d.core.proof.proof_envelope import (
        ProofVerificationError,
        verify_proof,
    )

    try:
        env = verify_proof(args.proof_path, check_files=not args.skip_files)
    except ProofVerificationError as exc:
        print(f"VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error reading proof: {exc}", file=sys.stderr)
        return 1
    print("Proof verified ✓")
    print(f"  schema: {env.schema_version}")
    print(f"  generator: {env.generator.get('name')} v{env.generator.get('version')}")
    print(f"  mesh sha256: {env.mesh.get('sha256')[:16]}...")
    print(f"  visual evidence: {len(env.visual_evidence)} file(s)")
    print(f"  signature: {env.signature.get('algorithm')}")
    return 0


# -- doctor (provider reachability) ------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    """Probe local LLM providers and report reachability.

    Per ADR-015, LM Studio is the default provider and Ollama is the
    documented fallback. ``hermes3d doctor`` reports on both so the
    operator can see which path will be taken before running an agent.

    Exit code is 0 when at least one provider in the chain is reachable
    (or when ``--strict`` is omitted), 1 when no provider can be found
    AND ``--strict`` is set.
    """
    from hermes3d.core.llm.lmstudio_client import (
        DEFAULT_BASE_URL as LM_STUDIO_BASE,
    )
    from hermes3d.core.llm.lmstudio_client import (
        LMStudioClient,
    )
    from hermes3d.core.llm.ollama_client import (
        DEFAULT_BASE_URL as OLLAMA_BASE,
    )
    from hermes3d.core.llm.ollama_client import (
        OllamaClient,
    )

    print("hermes3d doctor - local LLM provider reachability")
    print("-" * 60)

    findings: list[tuple[str, bool, str]] = []

    # ---- LM Studio (default) ----------------------------------------
    lms = LMStudioClient()
    print(f"[1] LM Studio (default per ADR-015) — {LM_STUDIO_BASE}")
    if lms.available():
        try:
            models = lms.list_models()
        except Exception as exc:  # noqa: BLE001 - any failure means partial-up
            findings.append(("lm_studio", True, f"reachable; list_models error: {exc}"))
            print("    reachable: yes")
            print(f"    list_models: ERROR — {exc}")
        else:
            findings.append(("lm_studio", True, f"reachable; {len(models)} model(s) loaded"))
            print("    reachable: yes")
            print(
                "    models loaded: "
                + (", ".join(models) if models else "(none — load one in LM Studio's UI)")
            )
    else:
        findings.append(("lm_studio", False, "unreachable — server not running on :1234"))
        print("    reachable: no")
        print("    hint: open LM Studio, click 'Local Server' → 'Start Server'")

    print()

    # ---- Ollama (fallback) ------------------------------------------
    oll = OllamaClient()
    print(f"[2] Ollama (fallback)            — {OLLAMA_BASE}")
    if oll.available():
        try:
            models = oll.list_models()
        except Exception as exc:  # noqa: BLE001
            findings.append(("ollama", True, f"reachable; list_models error: {exc}"))
            print("    reachable: yes")
            print(f"    list_models: ERROR — {exc}")
        else:
            findings.append(("ollama", True, f"reachable; {len(models)} model(s) pulled"))
            print("    reachable: yes")
            print(
                "    models pulled: "
                + (", ".join(models) if models else "(none — run `ollama pull qwen2.5-coder:7b`)")
            )
    else:
        findings.append(("ollama", False, "unreachable — server not running on :11434"))
        print("    reachable: no")
        print("    hint: install Ollama, then `ollama serve`")

    print()
    print("-" * 60)
    reachable = [name for (name, ok, _) in findings if ok]
    if reachable:
        print(f"At least one provider is reachable: {', '.join(reachable)}")
        return 0
    print("No local LLM provider is reachable.")
    if args.strict:
        return 1
    print("(non-strict mode — exit 0 anyway; agentic features will fall back)")
    return 0


# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    DEFAULT_QUEUE = os.environ.get("HERMES3D_QUEUE", "./var/queue.json")
    DEFAULT_SPOOLS = os.environ.get("HERMES3D_SPOOLS", "./var/spools.json")

    p = argparse.ArgumentParser(prog="hermes3d", description="Hermes3D-OS Lite CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # fleet -------------------------------------------------------------
    fleet = sub.add_parser("fleet", help="Print fleet operations")
    fleet_sub = fleet.add_subparsers(dest="fleet_command", required=True)
    fleet_probe = fleet_sub.add_parser("probe", help="Reach all printers")
    fleet_probe.add_argument("--timeout", type=float, default=2.5)
    fleet_probe.set_defaults(func=cmd_fleet_probe)
    fleet_status = fleet_sub.add_parser("status", help="Render dashboard table")
    fleet_status.add_argument("--queue", default=DEFAULT_QUEUE)
    fleet_status.add_argument("--spools", default=DEFAULT_SPOOLS)
    fleet_status.add_argument("--timeout", type=float, default=2.5)
    fleet_status.set_defaults(func=cmd_fleet_status)
    fleet_list = fleet_sub.add_parser("list", help="List all profile ids")
    fleet_list.set_defaults(func=cmd_fleet_list)

    # validate ----------------------------------------------------------
    val = sub.add_parser("validate", help="Truth Gate single mesh")
    val.add_argument("stl")
    val.add_argument("--printer", help="Printer profile_id (optional)")
    val.add_argument("--json", action="store_true", help="Print full JSON report")
    val.set_defaults(func=cmd_validate)

    valf = sub.add_parser("validate-fleet", help="Truth Gate vs every printer in fleet")
    valf.add_argument("stl")
    valf.set_defaults(func=cmd_validate_fleet)

    # generate organizer ------------------------------------------------
    gen = sub.add_parser("generate", help="Procedural generators")
    gen_sub = gen.add_subparsers(dest="gen_command", required=True)
    org = gen_sub.add_parser("organizer", help="Parametric desk organizer")
    org.add_argument("--width", type=float, default=180.0)
    org.add_argument("--depth", type=float, default=100.0)
    org.add_argument("--height", type=float, default=55.0)
    org.add_argument("--trays", type=int, default=3)
    org.add_argument("--pens", type=int, default=4)
    org.add_argument("--no-phone-slot", action="store_true")
    org.add_argument("--no-cable", action="store_true")
    org.add_argument("--out", default="./desk_organizer.stl")
    org.set_defaults(func=cmd_generate_organizer)

    # dispatch ----------------------------------------------------------
    disp = sub.add_parser("dispatch", help="Pick best printer for a mesh")
    disp.add_argument("stl")
    disp.add_argument("--material", default="PLA")
    disp.add_argument("--quality", default="normal", choices=["draft", "normal", "fine"])
    disp.add_argument(
        "--strategy",
        default="auto",
        choices=[
            "auto",
            "fastest",
            "quality",
            "largest_bed",
            "smallest_fit",
            "least_busy",
            "delta_prefer",
            "cartesian_prefer",
        ],
    )
    disp.set_defaults(func=cmd_dispatch)

    # slice -------------------------------------------------------------
    sl = sub.add_parser("slice", help="Slice via PrusaSlicer/OrcaSlicer CLI")
    sl.add_argument("stl")
    sl.add_argument("--profile", help="Path to slicer .ini config")
    sl.add_argument("--out-dir", help="Output directory (default: temp)")
    sl.add_argument("--timeout", type=float, default=600.0)
    sl.set_defaults(func=cmd_slice)

    # analyze-gcode -----------------------------------------------------
    anal = sub.add_parser("analyze-gcode", help="G-code metric report")
    anal.add_argument("gcode")
    anal.add_argument("--json", action="store_true")
    anal.set_defaults(func=cmd_analyze_gcode)

    # queue -------------------------------------------------------------
    qp = sub.add_parser("queue", help="Print job queue")
    qp_sub = qp.add_subparsers(dest="queue_command", required=True)
    ql = qp_sub.add_parser("list")
    ql.add_argument("--queue", default=DEFAULT_QUEUE)
    ql.set_defaults(func=cmd_queue_list)
    qs = qp_sub.add_parser("show")
    qs.add_argument("job_id")
    qs.add_argument("--queue", default=DEFAULT_QUEUE)
    qs.set_defaults(func=cmd_queue_show)
    qc = qp_sub.add_parser("cancel")
    qc.add_argument("job_id")
    qc.add_argument("--queue", default=DEFAULT_QUEUE)
    qc.set_defaults(func=cmd_queue_cancel)

    # spool -------------------------------------------------------------
    sp = sub.add_parser("spool", help="Filament spool registry")
    sp_sub = sp.add_subparsers(dest="spool_command", required=True)
    sl_ = sp_sub.add_parser("list")
    sl_.add_argument("--spools", default=DEFAULT_SPOOLS)
    sl_.set_defaults(func=cmd_spool_list)
    sa = sp_sub.add_parser("add")
    sa.add_argument("--material", required=True)
    sa.add_argument("--color", required=True)
    sa.add_argument("--color-hex", required=True)
    sa.add_argument("--vendor", required=True)
    sa.add_argument("--grams", type=float, required=True)
    sa.add_argument("--spools", default=DEFAULT_SPOOLS)
    sa.set_defaults(func=cmd_spool_add)
    so = sp_sub.add_parser("load")
    so.add_argument("spool_id")
    so.add_argument("printer")
    so.add_argument("--spools", default=DEFAULT_SPOOLS)
    so.set_defaults(func=cmd_spool_load)
    sc = sp_sub.add_parser("consume")
    sc.add_argument("spool_id")
    sc.add_argument("--grams", type=float, required=True)
    sc.add_argument("--job-id")
    sc.add_argument("--spools", default=DEFAULT_SPOOLS)
    sc.set_defaults(func=cmd_spool_consume)

    # proof -------------------------------------------------------------
    pr = sub.add_parser("proof", help="Proof envelope ops")
    pr_sub = pr.add_subparsers(dest="proof_command", required=True)
    pv = pr_sub.add_parser("verify")
    pv.add_argument("proof_path")
    pv.add_argument("--skip-files", action="store_true", help="Skip mesh/visual file re-hashing")
    pv.set_defaults(func=cmd_proof_verify)

    # doctor ------------------------------------------------------------
    doc = sub.add_parser(
        "doctor",
        help="Probe local LLM providers (LM Studio default + Ollama fallback) per ADR-015",
    )
    doc.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when no provider is reachable (default: still exit 0)",
    )
    doc.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args))


if __name__ == "__main__":
    sys.exit(main())
