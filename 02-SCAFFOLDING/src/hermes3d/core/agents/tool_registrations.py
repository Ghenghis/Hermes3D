"""
Built-in tool registrations for Hermes3D-OS Lite.

Registers high-level operations into the global ``tool_registry`` so they can be
called uniformly from:

- The Telegram / Discord remote-control bridge
- The MCP server (api/mcp_server.py)
- The LangGraph adapter and multi-agent orchestrator
- The Gradio "Tool Registry Browser" tab

Every shim below is a thin, JSON-serialisable wrapper around an already-tested
core module. ``register_builtin_tools()`` is idempotent; calling it twice is a
no-op for tools that already exist in the registry.

Path conventions match the rest of the codebase (api/server.py, cli/__main__.py,
supervisor/daemon.py): the queue, spool tracker, and skill store all default to
``./var/<name>.json`` and can be overridden via ``HERMES3D_QUEUE``,
``HERMES3D_SPOOLS``, ``HERMES3D_SKILLS`` environment variables.
"""

from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from typing import Any

from .tool_registry import ToolRegistry, ToolSpec, tool_registry

# ---------------------------------------------------------------------------
# Default storage locations (match api/server.py + cli/__main__.py)
# ---------------------------------------------------------------------------


def _queue_path() -> str:
    return os.environ.get("HERMES3D_QUEUE", "./var/queue.json")


def _spools_path() -> str:
    return os.environ.get("HERMES3D_SPOOLS", "./var/spools.json")


def _skills_path() -> str:
    return os.environ.get("HERMES3D_SKILLS", "./var/skills.json")


def _sha256_of_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        # Caller is allowed to enqueue against a not-yet-uploaded mesh
        # by supplying mesh_sha256 explicitly. We never silently fabricate.
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Shims (each returns a JSON-serialisable dict)
# ---------------------------------------------------------------------------


def _tool_fleet_status(include_offline: bool = True,
                        timeout_s: float = 2.5) -> dict[str, Any]:
    """Return a snapshot of every printer in the fleet.

    Composes static profile data with a live Moonraker reachability probe.
    """
    from ..agents.job_queue import JobQueue
    from ..farm.dashboard import collect_fleet_status
    from ..farm.spool_tracker import SpoolTracker

    queue: JobQueue | None
    try:
        queue = JobQueue(_queue_path())
    except Exception:  # noqa: BLE001 - missing/corrupt queue files are non-fatal here
        queue = None
    try:
        spool_tracker = SpoolTracker(_spools_path())
    except Exception:  # noqa: BLE001
        spool_tracker = None

    entries = collect_fleet_status(
        queue=queue, spool_tracker=spool_tracker, timeout_s=float(timeout_s)
    )
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not include_offline and not entry.reachable:
            continue
        out.append(
            {
                "printer_id": entry.profile_id,
                "manufacturer": entry.manufacturer,
                "model": entry.model,
                "kinematics": entry.kinematics,
                "bed": entry.bed_descr,
                "z_height_mm": entry.z_height_mm,
                "moonraker_url": entry.moonraker_url,
                "reachable": entry.reachable,
                "klippy_state": entry.klippy_state,
                "moonraker_version": entry.moonraker_version,
                "active_job_id": entry.active_job_id,
                "active_job_state": entry.active_job_state,
                "loaded_spool_id": entry.loaded_spool_id,
                "loaded_spool_label": entry.loaded_spool_label,
                "loaded_spool_remaining_g": entry.loaded_spool_remaining_g,
                "error": entry.error,
            }
        )
    return {"count": len(out), "printers": out}


def _tool_dispatch(
    *,
    stl_x_mm: float,
    stl_y_mm: float,
    stl_z_mm: float,
    material: str,
    strategy: str = "auto",
    quality: str = "normal",
    layer_height_mm: float = 0.2,
) -> dict[str, Any]:
    """Run the dispatcher for a part with the given bbox and material."""
    from ..agents.dispatcher import DispatchRequest, DispatchStrategy, dispatch

    try:
        strat = DispatchStrategy(strategy)
    except ValueError as exc:
        valid = [s.value for s in DispatchStrategy]
        raise ValueError(
            f"unknown strategy {strategy!r}. valid: {valid}"
        ) from exc

    extents = (float(stl_x_mm), float(stl_y_mm), float(stl_z_mm))
    # Worst-case enclosing-circle radius for a centered bbox
    xy_radius = math.hypot(extents[0], extents[1]) / 2.0

    req = DispatchRequest(
        mesh_extents_mm=extents,
        mesh_xy_radius_mm=xy_radius,
        material=str(material).upper(),
        layer_height_mm=float(layer_height_mm),
        quality_level=str(quality),
        strategy=strat,
    )
    decision = dispatch(req)
    return {
        "selected_printer_id": decision.selected_printer_id,
        "rationale": decision.rationale,
        "strategy_used": decision.strategy_used.value,
        "candidates": [
            {
                "printer_id": c.printer_id,
                "score": round(c.score, 4),
                "fits": c.fits,
                "eligible": c.eligible,
                "reasons": list(c.reasons),
                "blockers": list(c.blockers),
            }
            for c in decision.candidates
        ],
    }


def _tool_queue_add(
    *,
    mesh_path: str,
    material: str = "PLA",
    quality_level: str = "normal",
    layer_height_mm: float = 0.2,
    requested_strategy: str = "auto",
    notes: str = "",
    mesh_sha256: str | None = None,
) -> dict[str, Any]:
    """Enqueue a job. If ``mesh_sha256`` is omitted, hashed from disk."""
    from ..agents.job_queue import JobQueue

    sha = mesh_sha256 or _sha256_of_file(mesh_path)
    if not sha:
        return {
            "ok": False,
            "error": (
                f"mesh_path {mesh_path!r} does not exist and no mesh_sha256 "
                "was supplied; refusing to enqueue an un-hashable job."
            ),
        }

    q = JobQueue(_queue_path())
    job = q.enqueue(
        mesh_path=str(mesh_path),
        mesh_sha256=sha,
        material=str(material).upper(),
        quality_level=str(quality_level),
        layer_height_mm=float(layer_height_mm),
        requested_strategy=str(requested_strategy),
        notes=str(notes),
    )
    return {
        "ok": True,
        "job_id": job.job_id,
        "state": job.state.value,
        "mesh_sha256": job.mesh_sha256,
        "material": job.material,
    }


def _tool_queue_status(state: str | None = None) -> dict[str, Any]:
    """Return a summary of the job queue, optionally filtered by state."""
    from ..agents.job_queue import JobQueue, JobState

    q = JobQueue(_queue_path())
    state_filter: JobState | None = None
    if state:
        try:
            state_filter = JobState(state)
        except ValueError as exc:
            valid = [s.value for s in JobState]
            raise ValueError(
                f"unknown state {state!r}. valid: {valid}"
            ) from exc

    jobs = q.list(state=state_filter)
    by_state: dict[str, int] = {}
    items = []
    for j in jobs:
        by_state[j.state.value] = by_state.get(j.state.value, 0) + 1
        items.append(
            {
                "job_id": j.job_id,
                "mesh_path": j.mesh_path,
                "material": j.material,
                "state": j.state.value,
                "target_printer_id": j.target_printer_id,
                "quality_level": j.quality_level,
            }
        )
    return {"total": len(jobs), "by_state": by_state, "jobs": items}


def _tool_spool_list(material: str | None = None,
                     printer_id: str | None = None) -> dict[str, Any]:
    """List filament spools, optionally filtered by material or printer."""
    from ..farm.spool_tracker import SpoolTracker

    t = SpoolTracker(_spools_path())
    spools = t.list(printer_id=printer_id, material=material)
    return {
        "count": len(spools),
        "spools": [
            {
                "spool_id": s.spool_id,
                "material": s.material,
                "color": s.color,
                "color_hex": s.color_hex,
                "vendor": s.vendor,
                "diameter_mm": s.diameter_mm,
                "initial_grams": round(s.initial_grams, 1),
                "remaining_grams": round(s.remaining_grams, 1),
                "percent_remaining": round(s.percent_remaining, 1),
                "loaded_on_printer": s.loaded_on_printer,
            }
            for s in spools
        ],
    }


def _tool_estimate_cost(
    *,
    printer_id: str,
    material: str,
    filament_g: float,
    duration_hours: float,
    price_per_kg_usd: float | None = None,
    price_per_kwh_usd: float | None = None,
) -> dict[str, Any]:
    """Estimate dollar cost: filament + power, with sensible defaults."""
    from ..farm.cost_estimator import estimate_cost

    est = estimate_cost(
        printer_id=str(printer_id),
        material=str(material).upper(),
        filament_g=float(filament_g),
        duration_hours=float(duration_hours),
        price_per_kg_usd=price_per_kg_usd,
        price_per_kwh_usd=price_per_kwh_usd,
    )
    return {
        "printer_id": est.printer_id,
        "material": est.material,
        "filament_g": est.filament_g,
        "duration_hours": est.duration_hours,
        "filament_cost_usd": est.filament_cost_usd,
        "energy_kwh": est.energy_kwh,
        "energy_cost_usd": est.energy_cost_usd,
        "total_cost_usd": est.total_cost_usd,
        "price_per_kg_usd": est.price_per_kg_usd,
        "price_per_kwh_usd": est.price_per_kwh_usd,
        "typical_wattage": est.typical_wattage,
        "notes": list(est.notes),
    }


def _tool_calibration_macro(*, kind: str = "input_shaper") -> dict[str, Any]:
    """Return the calibration macro that *would* be sent for the given kind.

    This shim is intentionally read-only — actually firing the macro requires
    a Moonraker URL and is handled by ``run_calibration()`` (NOT exposed via
    the registry, because it has live-hardware side effects).
    """
    from ..agents.calibration import CalibrationKind, get_macro_for

    try:
        ckind = CalibrationKind(kind)
    except ValueError as exc:
        valid = [k.value for k in CalibrationKind]
        raise ValueError(
            f"unknown calibration kind {kind!r}. valid: {valid}"
        ) from exc

    return {"kind": ckind.value, "macro": get_macro_for(ckind)}


def _tool_mesh_analyze(*, mesh_path: str) -> dict[str, Any]:
    """Analyse an STL/OBJ: bbox, watertightness, overhangs, risk flags."""
    from ..agents.mesh_analyzer import analyze_mesh_file

    rep = analyze_mesh_file(str(mesh_path))
    return {
        "mesh_path": str(mesh_path),
        "bbox_mm": [round(v, 3) for v in rep.bbox_mm],
        "volume_mm3": round(rep.volume_mm3, 3),
        "surface_area_mm2": round(rep.surface_area_mm2, 3),
        "triangle_count": rep.triangle_count,
        "is_watertight": rep.is_watertight,
        "is_volume": rep.is_volume,
        "overhang_area_mm2": round(rep.overhang_area_mm2, 3),
        "overhang_pct": round(rep.overhang_pct, 3),
        "overhang_threshold_deg": rep.overhang_threshold_deg,
        "first_layer_area_mm2": round(rep.first_layer_area_mm2, 3),
        "support_volume_estimate_mm3": round(rep.support_volume_estimate_mm3, 3),
        "bridge_count_estimate": rep.bridge_count_estimate,
        "longest_bridge_mm": round(rep.longest_bridge_mm, 3),
        "height_to_min_xy_aspect": round(rep.height_to_min_xy_aspect, 3),
        "com_xy_offset_mm": round(rep.com_xy_offset_mm, 3),
        "thin_wall_face_count": rep.thin_wall_face_count,
        "risk_flags": list(rep.risk_flags),
    }


def _tool_failure_forecast(
    *,
    printer_id: str,
    material: str,
) -> dict[str, Any]:
    """Predict failure probability for a candidate print configuration.

    Reads PrintHistory from the conventional location if available; pulls
    skills from the SkillStore. Both signals are optional — the predictor
    falls back to baseline rates without them.
    """
    from ..intelligence.failure_predictor import predict_failure
    from ..memory.skill_store import SkillStore

    history = None
    try:
        from ..farm.print_history import PrintHistory  # type: ignore[attr-defined]
        history_path = os.environ.get(
            "HERMES3D_PRINT_HISTORY", "./var/print_history.json"
        )
        if Path(history_path).exists():
            history = PrintHistory(history_path)
    except Exception:  # noqa: BLE001 - history is optional
        history = None

    skills: SkillStore | None
    try:
        skills_path = _skills_path()
        if Path(skills_path).exists():
            skills = SkillStore(skills_path)
        else:
            skills = None
    except Exception:  # noqa: BLE001
        skills = None

    pred = predict_failure(
        printer_id=str(printer_id),
        material=str(material).upper(),
        history=history,
        skills=skills,
    )
    return {
        "printer_id": pred.printer_id,
        "material": pred.material,
        "failure_probability": round(pred.failure_probability, 4),
        "confidence": pred.confidence,  # string: low/medium/high
        "components": {k: round(v, 4) for k, v in pred.components.items()},
        "citations": list(pred.citations),
    }


def _tool_skill_lookup(
    *,
    kind: str,
    printer_id: str | None = None,
    material: str | None = None,
    quality_level: str | None = None,
    min_confidence: float = 0.0,
    limit: int = 10,
) -> dict[str, Any]:
    """Search the long-term skill memory store."""
    from ..memory.skill_store import SkillKind, SkillStore

    try:
        skill_kind = SkillKind(kind)
    except ValueError as exc:
        valid = [k.value for k in SkillKind]
        raise ValueError(
            f"unknown skill kind {kind!r}. valid: {valid}"
        ) from exc

    skills_path = _skills_path()
    if not Path(skills_path).exists():
        return {"count": 0, "skills": [], "note": "no skill store at this path yet"}

    store = SkillStore(skills_path)
    matches = store.lookup(
        kind=skill_kind,
        printer_id=printer_id,
        material=material,
        quality_level=quality_level,
        min_confidence=float(min_confidence),
    )
    matches = matches[: int(limit)]
    return {
        "count": len(matches),
        "skills": [
            {
                "skill_id": s.skill_id,
                "kind": s.skill_kind.value,
                "name": s.name,
                "scope": s.scope.to_dict(),
                "confidence": round(s.confidence, 3),
                "evidence_count": s.evidence_count,
                "source": s.source,
                "notes": s.notes,
            }
            for s in matches
        ],
    }


def _tool_help() -> dict[str, Any]:
    """List every registered tool with a short description."""
    return tool_registry.manifest()


# ---------------------------------------------------------------------------
# Spec table (declarative)
# ---------------------------------------------------------------------------

_BUILTINS: list[dict[str, Any]] = [
    {
        "name": "fleet_status",
        "description": (
            "Snapshot every printer in the fleet (online state, klippy state, "
            "active job, loaded spool)."
        ),
        "category": "fleet",
        "tags": ("fleet", "status", "moonraker"),
        "parameters": {
            "include_offline": {
                "type": "boolean",
                "default": True,
                "description": "Include printers that are unreachable.",
            },
            "timeout_s": {
                "type": "number",
                "default": 2.5,
                "description": "Per-printer Moonraker probe timeout.",
            },
        },
        "handler": _tool_fleet_status,
    },
    {
        "name": "dispatch",
        "description": (
            "Pick the best printer(s) for a part using the dispatcher "
            "(strategies: auto/fastest/quality/largest_bed/smallest_fit/"
            "least_busy/delta_prefer/cartesian_prefer)."
        ),
        "category": "agentic",
        "tags": ("dispatcher", "selection"),
        "parameters": {
            "stl_x_mm": {"type": "number", "description": "Bounding-box X (mm)."},
            "stl_y_mm": {"type": "number", "description": "Bounding-box Y (mm)."},
            "stl_z_mm": {"type": "number", "description": "Bounding-box Z (height, mm)."},
            "material": {
                "type": "string",
                "description": "Material code (PLA, PETG, ABS, ASA, PC, TPU, PA-CF, ...).",
            },
            "strategy": {"type": "string", "default": "auto"},
            "quality": {"type": "string", "default": "normal"},
            "layer_height_mm": {"type": "number", "default": 0.2},
        },
        "handler": _tool_dispatch,
    },
    {
        "name": "queue_add",
        "description": "Enqueue a print job. Computes mesh_sha256 from disk if not supplied.",
        "category": "queue",
        "tags": ("queue", "job"),
        "parameters": {
            "mesh_path": {"type": "string"},
            "material": {"type": "string", "default": "PLA"},
            "quality_level": {"type": "string", "default": "normal"},
            "layer_height_mm": {"type": "number", "default": 0.2},
            "requested_strategy": {"type": "string", "default": "auto"},
            "notes": {"type": "string", "default": ""},
            "mesh_sha256": {"type": "string", "default": None},
        },
        "handler": _tool_queue_add,
    },
    {
        "name": "queue_status",
        "description": "Summarise the job queue, optionally filtered by state.",
        "category": "queue",
        "tags": ("queue", "status"),
        "parameters": {
            "state": {
                "type": "string",
                "default": None,
                "description": (
                    "Filter by state name (queued, validated, dispatched, "
                    "sliced, uploaded, printing, succeeded, failed, cancelled)."
                ),
            }
        },
        "handler": _tool_queue_status,
    },
    {
        "name": "spool_list",
        "description": "List filament spools and their remaining grams.",
        "category": "fleet",
        "tags": ("filament", "spool"),
        "parameters": {
            "material": {"type": "string", "default": None},
            "printer_id": {"type": "string", "default": None},
        },
        "handler": _tool_spool_list,
    },
    {
        "name": "estimate_cost",
        "description": "Estimate the dollar cost of a print (filament + power).",
        "category": "fleet",
        "tags": ("cost", "estimate"),
        "parameters": {
            "printer_id": {"type": "string"},
            "material": {"type": "string"},
            "filament_g": {"type": "number"},
            "duration_hours": {"type": "number"},
            "price_per_kg_usd": {"type": "number", "default": None},
            "price_per_kwh_usd": {"type": "number", "default": None},
        },
        "handler": _tool_estimate_cost,
    },
    {
        "name": "calibration_macro",
        "description": (
            "Return the Klipper macro that would be issued for a given "
            "calibration kind. Read-only — does NOT fire the macro."
        ),
        "category": "agentic",
        "tags": ("calibration",),
        "parameters": {
            "kind": {
                "type": "string",
                "default": "input_shaper",
                "description": (
                    "One of: pressure_advance, input_shaper, flow_ratio, "
                    "shaper_autocalibrate, bed_mesh."
                ),
            }
        },
        "handler": _tool_calibration_macro,
    },
    {
        "name": "mesh_analyze",
        "description": (
            "Analyse an STL/OBJ file: bbox, watertightness, overhang area, "
            "bridges, thin walls, risk flags."
        ),
        "category": "agentic",
        "tags": ("mesh", "stl", "analysis"),
        "parameters": {"mesh_path": {"type": "string"}},
        "handler": _tool_mesh_analyze,
    },
    {
        "name": "failure_forecast",
        "description": (
            "Estimate failure probability for a printer/material combination "
            "by blending PrintHistory and SkillStore signals."
        ),
        "category": "intelligence",
        "tags": ("prediction", "risk"),
        "parameters": {
            "printer_id": {"type": "string"},
            "material": {"type": "string"},
        },
        "handler": _tool_failure_forecast,
    },
    {
        "name": "skill_lookup",
        "description": "Search the long-term skill memory store by kind and scope.",
        "category": "memory",
        "tags": ("skills", "memory"),
        "parameters": {
            "kind": {
                "type": "string",
                "description": (
                    "One of: parameter_override, printer_quirk, "
                    "material_quirk, scheduling_pref, user_preference, "
                    "failure_pattern."
                ),
            },
            "printer_id": {"type": "string", "default": None},
            "material": {"type": "string", "default": None},
            "quality_level": {"type": "string", "default": None},
            "min_confidence": {"type": "number", "default": 0.0},
            "limit": {"type": "integer", "default": 10},
        },
        "handler": _tool_skill_lookup,
    },
    {
        "name": "help",
        "description": "List every registered tool with a short description.",
        "category": "meta",
        "tags": ("help", "introspection"),
        "parameters": {},
        "handler": _tool_help,
    },
]


def register_builtin_tools(registry: ToolRegistry | None = None) -> list[str]:
    """Idempotently register every built-in tool. Returns names registered now."""
    # NB: must check `is None` explicitly; an empty ToolRegistry is falsy because
    # of its __len__ implementation, so `registry or tool_registry` would
    # silently fall back to the singleton.
    reg = tool_registry if registry is None else registry
    registered: list[str] = []
    for spec in _BUILTINS:
        if spec["name"] in reg:
            continue
        reg.register(
            ToolSpec(
                name=spec["name"],
                description=spec["description"],
                parameters=dict(spec["parameters"]),
                handler=spec["handler"],
                category=spec["category"],
                tags=tuple(spec["tags"]),
            )
        )
        registered.append(spec["name"])
    return registered


def builtin_names() -> list[str]:
    """Return the names of every built-in tool."""
    return [spec["name"] for spec in _BUILTINS]


def is_builtin(name: str) -> bool:
    """Return True iff ``name`` is one of the built-in tool names."""
    return name in builtin_names()


__all__ = [
    "register_builtin_tools",
    "builtin_names",
    "is_builtin",
]
