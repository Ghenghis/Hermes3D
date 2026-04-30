"""End-to-end PrintWorkflow — every agent wired into one graph.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §30 (Orchestration Brain)

Composes:

    enqueue                 (job_queue)
    truth_gate              (validation/truth_gate)
    repair_if_needed        (agents/mesh_repair)
    auto_orient             (agents/auto_orient)
    dispatch                (agents/dispatcher)
    preflight               (agents/preflight)
    slice                   (slicer/slicer_runner)
    analyze_gcode           (slicer/gcode_analyzer)
    cost_estimate           (farm/cost_estimator)
    upload                  (printers/moonraker_client)
    start_print             (printers/moonraker_client)
    notify_started          (notifications)
    record_history          (farm/print_history)

Each node is small and idempotent. If a step has already run (recorded
in `state.history`), it's skipped on resume.

Usage::

    from hermes3d.core.orchestration.agent_graph import new_state
    from hermes3d.core.orchestration.print_workflow import build_print_workflow

    graph = build_print_workflow(checkpoint_dir="./var/workflows")
    state = new_state(initial={
        "mesh_path": "/path/to/model.stl",
        "material": "PLA",
        "strategy": "auto",
    })
    final = graph.run(state)
"""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from pathlib import Path

from .agent_graph import (
    GraphNode,
    NodeOutcome,
    NodeResult,
    WorkflowGraph,
    WorkflowState,
)
from .repair_agent import RepairAgent
from .retry_controller import RepairEscalation, RetryBudget, with_retry

_DEFAULT_BUDGET = RetryBudget(max_retries=3)


def _retry_node(fn):
    """Wrap a node fn with a RetryBudget; on RepairEscalation, invoke the
    RepairAgent and surface its result as a FAIL NodeResult.
    """
    wrapped = with_retry(_DEFAULT_BUDGET)(fn)

    @functools.wraps(fn)
    def runner(state: WorkflowState) -> NodeResult:
        try:
            return wrapped(state)
        except RepairEscalation as esc:
            try:
                repair = RepairAgent().repair(esc)
            except Exception as repair_exc:
                log.exception("RepairAgent failed: %s", repair_exc)
                return NodeResult(
                    node_name=getattr(fn, "__name__", "unknown").removeprefix("_node_"),
                    outcome=NodeOutcome.FAIL,
                    started_unix=_now(),
                    ended_unix=_now(),
                    error=f"escalation + repair failure: {esc.cause!r}",
                )
            outcome = NodeOutcome.PASS if repair.outcome == "fixed" else NodeOutcome.FAIL
            return NodeResult(
                node_name=getattr(fn, "__name__", "unknown").removeprefix("_node_"),
                outcome=outcome,
                started_unix=_now(),
                ended_unix=_now(),
                error=None if outcome == NodeOutcome.PASS else repr(esc.cause),
                state_patch={
                    "repair_outcome": repair.outcome,
                    "repair_strategy": repair.strategy_used,
                    "repair_notes": repair.notes,
                    "repair_suggested_action": repair.suggested_action,
                },
                notes=[f"repair: {repair.outcome} via {repair.strategy_used}"],
            )

    return runner


log = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _now() -> float:
    return time.time()


# =============================================================================
# Node implementations
# =============================================================================


def _node_enqueue(state: WorkflowState) -> NodeResult:
    """Persist this workflow as a Job in the queue."""
    from hermes3d.core.agents.job_queue import JobQueue

    started = _now()
    mesh_path = state.data["mesh_path"]
    queue_path = state.data.get("queue_path", "./var/queue.json")
    sha = _sha256_file(mesh_path)
    queue = JobQueue(queue_path)
    job = queue.enqueue(
        mesh_path=str(mesh_path),
        mesh_sha256=sha,
        material=state.data.get("material", "PLA"),
        quality_level=state.data.get("quality_level", "normal"),
        layer_height_mm=float(state.data.get("layer_height_mm", 0.2)),
        requested_strategy=state.data.get("strategy", "auto"),
        notes=state.data.get("notes", ""),
    )
    return NodeResult(
        node_name="enqueue",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={"job_id": job.job_id, "mesh_sha256": sha},
        notes=[f"job_id={job.job_id}"],
    )


def _node_truth_gate(state: WorkflowState) -> NodeResult:
    from hermes3d.core.validation.truth_gate import (
        CheckStatus,
        TruthGateConfig,
        run_truth_gate,
    )

    started = _now()
    cfg = TruthGateConfig(
        printer_profile_id=state.data.get("preferred_printer_id"),
    )
    rep = run_truth_gate(state.data["mesh_path"], cfg)
    patch = {
        "truth_gate_passed": rep.passed,
        "truth_gate_overall": rep.overall_status.value,
    }
    if rep.passed:
        return NodeResult(
            node_name="truth_gate",
            outcome=NodeOutcome.PASS,
            started_unix=started,
            ended_unix=_now(),
            state_patch=patch,
        )
    # Detect specific failures the repair node might be able to fix
    fails = [c.name for c in rep.checks if c.status == CheckStatus.FAIL]
    repairable = {"watertight", "manifold", "normals", "self_intersection"}
    can_repair = any(f in repairable for f in fails)
    if can_repair:
        # Mark for repair, then re-validate
        return NodeResult(
            node_name="truth_gate",
            outcome=NodeOutcome.PASS,
            started_unix=started,
            ended_unix=_now(),
            state_patch={**patch, "needs_repair": True, "repairable_failures": fails},
            notes=[f"truth gate failed but repair is possible: {fails}"],
        )
    return NodeResult(
        node_name="truth_gate",
        outcome=NodeOutcome.FAIL,
        started_unix=started,
        ended_unix=_now(),
        state_patch=patch,
        error=f"unrepairable failures: {fails}",
    )


def _node_repair(state: WorkflowState) -> NodeResult:
    if not state.data.get("needs_repair", False):
        return NodeResult(
            node_name="repair_if_needed",
            outcome=NodeOutcome.SKIP,
            started_unix=_now(),
            ended_unix=_now(),
            notes=["repair not requested by truth_gate"],
        )

    import trimesh

    from hermes3d.core.agents.mesh_repair import RepairConfig, repair_mesh
    from hermes3d.core.validation.truth_gate import (
        TruthGateConfig,
        run_truth_gate,
    )

    started = _now()
    src = trimesh.load_mesh(state.data["mesh_path"], force="mesh")
    fixed, report = repair_mesh(src, RepairConfig())
    if not report.succeeded:
        return NodeResult(
            node_name="repair_if_needed",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error="repair pipeline could not produce a watertight mesh",
            state_patch={"repair_report": report.to_dict()},
        )

    # Save repaired mesh next to the original
    src_path = Path(state.data["mesh_path"])
    repaired_path = src_path.with_name(src_path.stem + ".repaired.stl")
    fixed.export(repaired_path)

    # Re-validate
    cfg = TruthGateConfig(
        printer_profile_id=state.data.get("preferred_printer_id"),
    )
    rep2 = run_truth_gate(repaired_path, cfg)
    if not rep2.passed:
        return NodeResult(
            node_name="repair_if_needed",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error="repaired mesh still fails truth gate",
            state_patch={
                "repair_report": report.to_dict(),
                "repaired_mesh_path": str(repaired_path),
                "truth_gate_overall_after_repair": rep2.overall_status.value,
            },
        )
    return NodeResult(
        node_name="repair_if_needed",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={
            "repair_report": report.to_dict(),
            "mesh_path": str(repaired_path),  # downstream uses the repaired one
            "truth_gate_passed": True,
        },
        notes=[f"mesh repaired: faces {report.initial_face_count} -> {report.final_face_count}"],
    )


def _node_auto_orient(state: WorkflowState) -> NodeResult:
    if not state.data.get("auto_orient_enabled", True):
        return NodeResult(
            node_name="auto_orient",
            outcome=NodeOutcome.SKIP,
            started_unix=_now(),
            ended_unix=_now(),
            notes=["auto-orient disabled by caller"],
        )
    import trimesh

    from hermes3d.core.agents.auto_orient import auto_orient

    started = _now()
    mesh = trimesh.load_mesh(state.data["mesh_path"], force="mesh")
    decision = auto_orient(mesh)
    chosen = decision.chosen
    if chosen.candidate_name == "identity":
        return NodeResult(
            node_name="auto_orient",
            outcome=NodeOutcome.PASS,
            started_unix=started,
            ended_unix=_now(),
            state_patch={"orient_choice": "identity", "orient_score": chosen.score},
            notes=["original orientation already optimal"],
        )
    # Apply transform and re-export
    mesh.apply_transform(decision.transform_matrix())
    minz = float(mesh.vertices[:, 2].min())
    mesh.apply_translation((0, 0, -minz))
    src_path = Path(state.data["mesh_path"])
    oriented_path = src_path.with_name(src_path.stem + ".oriented.stl")
    mesh.export(oriented_path)
    return NodeResult(
        node_name="auto_orient",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={
            "mesh_path": str(oriented_path),
            "orient_choice": chosen.candidate_name,
            "orient_score": chosen.score,
        },
        notes=[f"reoriented via {chosen.candidate_name}: {chosen.rationale}"],
    )


def _node_dispatch(state: WorkflowState) -> NodeResult:
    import trimesh

    from hermes3d.core.agents.dispatcher import (
        DispatchRequest,
        DispatchStrategy,
        dispatch,
    )

    started = _now()
    mesh = trimesh.load_mesh(state.data["mesh_path"], force="mesh")
    extents = tuple(float(e) for e in mesh.extents)
    xy = mesh.vertices[:, :2]
    radius = None
    if xy.size:
        import numpy as np

        center = (xy.min(axis=0) + xy.max(axis=0)) / 2.0
        radius = float(np.max(np.linalg.norm(xy - center, axis=1)))

    req = DispatchRequest(
        mesh_extents_mm=extents,
        mesh_xy_radius_mm=radius,
        material=state.data.get("material", "PLA"),
        quality_level=state.data.get("quality_level", "normal"),
        strategy=DispatchStrategy(state.data.get("strategy", "auto")),
        live_state=state.data.get("live_state", {}),
        excluded_printers=tuple(state.data.get("excluded_printers", ())),
        allowed_printers=tuple(state.data.get("allowed_printers", ())),
    )
    decision = dispatch(req)
    if decision.selected_printer_id is None:
        return NodeResult(
            node_name="dispatch",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error=f"no eligible printer: {decision.rationale[:200]}",
        )
    return NodeResult(
        node_name="dispatch",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={
            "selected_printer_id": decision.selected_printer_id,
            "dispatch_rationale": decision.rationale,
        },
        notes=[f"selected {decision.selected_printer_id}"],
    )


def _node_preflight(state: WorkflowState) -> NodeResult:
    """Currently a soft check — calls preflight without spool/live data
    when those aren't available. The workflow can be made more strict by
    upstream nodes adding those fields."""
    from hermes3d.core.agents.preflight import run_preflight

    started = _now()

    class _TGFacade:
        passed = bool(state.data.get("truth_gate_passed", False))

    rep = run_preflight(
        printer_id=state.data["selected_printer_id"],
        job_id=state.data.get("job_id"),
        truth_gate_report=_TGFacade(),
        live_state=state.data.get("live_state", {}).get(state.data["selected_printer_id"]),
        spool=state.data.get("loaded_spool"),
        required_grams=float(state.data.get("required_grams", 0.0)),
        required_material=state.data.get("material", "PLA"),
        cost_estimate=state.data.get("cost_estimate"),
        budget_usd=state.data.get("budget_usd"),
        gcode_analysis=state.data.get("gcode_analysis"),
    )
    if not rep.passed:
        fails = [c.message for c in rep.checks if c.outcome.value == "fail"]
        return NodeResult(
            node_name="preflight",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error="; ".join(fails),
            state_patch={"preflight_report": rep.to_dict()},
        )
    return NodeResult(
        node_name="preflight",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={"preflight_report": rep.to_dict()},
        notes=[f"{len(rep.checks)} checks passed"]
        + (
            [f"{sum(1 for c in rep.checks if c.outcome.value == 'warn')} warnings"]
            if rep.has_warnings
            else []
        ),
    )


def _node_slice(state: WorkflowState) -> NodeResult:
    from hermes3d.core.slicer.slicer_runner import (
        SlicerError,
        SlicerNotFound,
        slice_mesh,
    )

    started = _now()
    profile = state.data.get("slicer_profile_path")
    out_dir = state.data.get("slice_out_dir") or "./var/sliced"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    try:
        result = slice_mesh(
            stl_path=state.data["mesh_path"],
            profile=profile,
            output_dir=out_dir,
            timeout_seconds=int(state.data.get("slice_timeout_s", 600)),
        )
    except SlicerNotFound as exc:
        # No slicer installed — non-fatal in dry-run mode
        if state.data.get("dry_run", True):
            return NodeResult(
                node_name="slice",
                outcome=NodeOutcome.SKIP,
                started_unix=started,
                ended_unix=_now(),
                notes=[f"no slicer available (dry_run): {exc}"],
            )
        return NodeResult(
            node_name="slice",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error=f"slicer not found: {exc}",
        )
    except SlicerError as exc:
        return NodeResult(
            node_name="slice",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error=str(exc),
        )
    return NodeResult(
        node_name="slice",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={
            "sliced_gcode_path": str(result.gcode_path),
            "slicer_metadata": result.metadata,
        },
    )


def _node_analyze_gcode(state: WorkflowState) -> NodeResult:
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    started = _now()
    a = analyze_gcode(state.data["sliced_gcode_path"])
    return NodeResult(
        node_name="analyze_gcode",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={
            "gcode_analysis": a,
            "estimated_print_time_min": a.estimated_print_time_min,
            "filament_used_g": a.filament_used_g,
            "gcode_risk_flags": list(a.risk_flags),
        },
        notes=([f"{len(a.risk_flags)} risk flags"] if a.risk_flags else []),
    )


def _node_cost_estimate(state: WorkflowState) -> NodeResult:
    from hermes3d.core.farm.cost_estimator import estimate_cost

    started = _now()
    fil = state.data.get("filament_used_g") or 0.0
    dur = (state.data.get("estimated_print_time_min") or 0.0) / 60.0
    if fil == 0.0 and dur == 0.0:
        return NodeResult(
            node_name="cost_estimate",
            outcome=NodeOutcome.SKIP,
            started_unix=started,
            ended_unix=_now(),
            notes=["no filament/time data — cost calc skipped"],
        )
    e = estimate_cost(
        printer_id=state.data["selected_printer_id"],
        material=state.data.get("material", "PLA"),
        filament_g=fil,
        duration_hours=dur,
    )
    return NodeResult(
        node_name="cost_estimate",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={"cost_estimate": e},
        notes=[
            f"${e.total_cost_usd:.2f} (filament ${e.filament_cost_usd} + "
            f"energy ${e.energy_cost_usd})"
        ],
    )


def _node_upload(state: WorkflowState) -> NodeResult:
    """Upload sliced gcode to Moonraker. Skipped if 'dry_run' set."""
    if state.data.get("dry_run", True):
        return NodeResult(
            node_name="upload",
            outcome=NodeOutcome.SKIP,
            started_unix=_now(),
            ended_unix=_now(),
            notes=["dry_run=True — no upload"],
        )
    from hermes3d.core.printers import get_profile
    from hermes3d.core.printers.moonraker_client import MoonrakerClient

    started = _now()
    profile = get_profile(state.data["selected_printer_id"])
    client = MoonrakerClient(
        profile.moonraker_url_default,
        api_key=state.data.get("moonraker_api_key"),
        timeout_s=float(state.data.get("upload_timeout_s", 60.0)),
    )
    try:
        item_path = client.upload_gcode(state.data["sliced_gcode_path"])
    except Exception as exc:
        return NodeResult(
            node_name="upload",
            outcome=NodeOutcome.RETRY,
            started_unix=started,
            ended_unix=_now(),
            error=str(exc),
        )
    return NodeResult(
        node_name="upload",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={"moonraker_item_path": item_path},
    )


def _node_start_print(state: WorkflowState) -> NodeResult:
    if state.data.get("dry_run", True):
        return NodeResult(
            node_name="start_print",
            outcome=NodeOutcome.SKIP,
            started_unix=_now(),
            ended_unix=_now(),
            notes=["dry_run=True — no start"],
        )
    from hermes3d.core.printers import get_profile
    from hermes3d.core.printers.moonraker_client import MoonrakerClient

    started = _now()
    profile = get_profile(state.data["selected_printer_id"])
    client = MoonrakerClient(
        profile.moonraker_url_default, api_key=state.data.get("moonraker_api_key")
    )
    item = state.data.get("moonraker_item_path") or state.data["sliced_gcode_path"]
    try:
        client.start_print(item)
    except Exception as exc:
        return NodeResult(
            node_name="start_print",
            outcome=NodeOutcome.FAIL,
            started_unix=started,
            ended_unix=_now(),
            error=str(exc),
        )
    return NodeResult(
        node_name="start_print",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        state_patch={"print_started_unix": _now()},
    )


def _node_notify_started(state: WorkflowState) -> NodeResult:
    from hermes3d.core.notifications import (
        Notifier,
        event_print_started,
    )

    started = _now()
    n = Notifier()
    if not n.configured_channels:
        return NodeResult(
            node_name="notify_started",
            outcome=NodeOutcome.SKIP,
            started_unix=started,
            ended_unix=_now(),
            notes=["no notification channels configured"],
        )
    filename = Path(state.data.get("sliced_gcode_path", "?")).name
    results = n.notify(
        event_print_started(
            printer_id=state.data["selected_printer_id"],
            job_id=state.data.get("job_id", "?"),
            filename=filename,
        )
    )
    sent = sum(1 for r in results if r.sent)
    return NodeResult(
        node_name="notify_started",
        outcome=NodeOutcome.PASS,
        started_unix=started,
        ended_unix=_now(),
        notes=[f"{sent}/{len(results)} channels delivered"],
    )


# =============================================================================
# Graph builder
# =============================================================================


def build_print_workflow(
    *,
    checkpoint_dir: str | Path | None = None,
) -> WorkflowGraph:
    g = WorkflowGraph("PrintWorkflow", checkpoint_dir=checkpoint_dir)
    g.add_node(
        GraphNode(
            name="enqueue",
            fn=_retry_node(_node_enqueue),
            expected_inputs=("mesh_path",),
            description="Persist a Job in the queue",
        )
    )
    g.add_node(
        GraphNode(
            name="truth_gate",
            fn=_retry_node(_node_truth_gate),
            expected_inputs=("mesh_path",),
            description="Run printability validation",
        )
    )
    g.add_node(
        GraphNode(
            name="repair_if_needed",
            fn=_retry_node(_node_repair),
            expected_inputs=("mesh_path",),
            description="Auto-repair non-watertight or flipped meshes",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="auto_orient",
            fn=_retry_node(_node_auto_orient),
            expected_inputs=("mesh_path",),
            description="Find optimal print orientation",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="dispatch",
            fn=_retry_node(_node_dispatch),
            expected_inputs=("mesh_path",),
            description="Pick the best printer in the fleet",
        )
    )
    g.add_node(
        GraphNode(
            name="preflight",
            fn=_retry_node(_node_preflight),
            expected_inputs=("selected_printer_id",),
            description="Run preflight safety checklist",
        )
    )
    g.add_node(
        GraphNode(
            name="slice",
            fn=_retry_node(_node_slice),
            expected_inputs=("mesh_path", "selected_printer_id"),
            description="Slice mesh to G-code",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="analyze_gcode",
            fn=_retry_node(_node_analyze_gcode),
            expected_inputs=("sliced_gcode_path",),
            description="Parse G-code metadata + raise risk flags",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="cost_estimate",
            fn=_retry_node(_node_cost_estimate),
            expected_inputs=("selected_printer_id",),
            description="Estimate filament + electricity cost",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="upload",
            fn=_retry_node(_node_upload),
            expected_inputs=("sliced_gcode_path", "selected_printer_id"),
            description="Upload G-code to Moonraker",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="start_print",
            fn=_retry_node(_node_start_print),
            expected_inputs=("selected_printer_id",),
            description="Tell Klipper to start the print",
            optional=True,
        )
    )
    g.add_node(
        GraphNode(
            name="notify_started",
            fn=_retry_node(_node_notify_started),
            expected_inputs=("selected_printer_id",),
            description="Send Discord/Slack notification",
            optional=True,
        )
    )
    return g


__all__ = ["build_print_workflow"]
