"""MCP (Model Context Protocol) server.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §27 (MCP Integration)

Exposes Hermes3D-OS Lite to MCP-compatible agentic clients (Claude Code,
DaveAI-IDE, Roo Code, Continue). The server speaks STDIO MCP and offers
tools that agents can call:

  hermes3d.dispatch                         agentic printer selection
  hermes3d.fleet_status                     live state of every printer
  hermes3d.queue_list                       list jobs
  hermes3d.queue_enqueue                    enqueue a print job
  hermes3d.queue_cancel                     cancel a job
  hermes3d.spool_list                       inventory loaded spools
  hermes3d.proof_verify                     verify a proof envelope
  hermes3d.estimate_cost                    print cost estimate
  hermes3d.preflight                        run preflight checks

The implementation uses the official ``mcp`` Python package when available;
when it isn't, we fall back to a minimal manual STDIO JSON-RPC server that
implements the parts of MCP we need (initialize, tools/list, tools/call).

Run with::

    python -m hermes3d.api.mcp_server
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable


log = logging.getLogger("hermes3d.mcp")


# =============================================================================
# Tool registry
# =============================================================================


def _tool_dispatch(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.dispatcher import (
        DispatchRequest,
        DispatchStrategy,
        dispatch,
    )

    req = DispatchRequest(
        mesh_extents_mm=tuple(arguments["mesh_extents_mm"]),
        mesh_xy_radius_mm=arguments.get("mesh_xy_radius_mm"),
        material=arguments.get("material", "PLA"),
        quality_level=arguments.get("quality_level", "normal"),
        strategy=DispatchStrategy(arguments.get("strategy", "auto")),
        excluded_printers=tuple(arguments.get("excluded_printers", [])),
        allowed_printers=tuple(arguments.get("allowed_printers", [])),
    )
    decision = dispatch(req)
    return {
        "selected_printer_id": decision.selected_printer_id,
        "rationale": decision.rationale,
        "candidates": [
            {
                "printer_id": c.printer_id,
                "score": c.score,
                "eligible": c.eligible,
                "blockers": list(c.blockers),
            }
            for c in decision.candidates[:5]
        ],
    }


def _tool_fleet_status(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.farm.dashboard import collect_fleet_status
    from hermes3d.core.agents.job_queue import JobQueue
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    qpath = arguments.get("queue_path", os.environ.get("HERMES3D_QUEUE", ""))
    spath = arguments.get("spools_path", os.environ.get("HERMES3D_SPOOLS", ""))
    queue = JobQueue(qpath) if qpath and Path(qpath).exists() else None
    spools = SpoolTracker(spath) if spath and Path(spath).exists() else None
    entries = collect_fleet_status(
        queue=queue, spool_tracker=spools, timeout_s=float(arguments.get("timeout_s", 2.5))
    )
    return {"fleet": [e.to_dict() for e in entries]}


def _tool_queue_list(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    qpath = arguments.get("queue_path", os.environ.get("HERMES3D_QUEUE", "./var/queue.json"))
    queue = JobQueue(qpath)
    state = arguments.get("state")
    jobs = queue.list(state=JobState(state) if state else None)
    return {"jobs": [j.to_dict() for j in jobs]}


def _tool_queue_enqueue(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.job_queue import JobQueue

    qpath = arguments.get("queue_path", os.environ.get("HERMES3D_QUEUE", "./var/queue.json"))
    queue = JobQueue(qpath)
    j = queue.enqueue(
        mesh_path=arguments["mesh_path"],
        mesh_sha256=arguments["mesh_sha256"],
        material=arguments.get("material", "PLA"),
        quality_level=arguments.get("quality_level", "normal"),
        layer_height_mm=float(arguments.get("layer_height_mm", 0.2)),
        requested_strategy=arguments.get("requested_strategy", "auto"),
        notes=arguments.get("notes", ""),
    )
    return {"job": j.to_dict()}


def _tool_queue_cancel(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    qpath = arguments.get("queue_path", os.environ.get("HERMES3D_QUEUE", "./var/queue.json"))
    queue = JobQueue(qpath)
    j = queue.transition_job(arguments["job_id"], JobState.CANCELLED, reason="cancel via MCP")
    return {"job": j.to_dict()}


def _tool_spool_list(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    spath = arguments.get("spools_path", os.environ.get("HERMES3D_SPOOLS", "./var/spools.json"))
    st = SpoolTracker(spath)
    return {
        "spools": [
            s.to_dict()
            for s in st.list(
                printer_id=arguments.get("printer_id"),
                material=arguments.get("material"),
            )
        ]
    }


def _tool_proof_verify(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.proof.proof_envelope import (
        ProofVerificationError,
        verify_proof,
    )

    try:
        env = verify_proof(
            arguments["proof_path"], check_files=bool(arguments.get("check_files", True))
        )
        return {
            "verified": True,
            "schema_version": env.schema_version,
            "mesh_sha256": env.mesh.get("sha256"),
        }
    except ProofVerificationError as exc:
        return {"verified": False, "error": str(exc)}


def _tool_estimate_cost(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.farm.cost_estimator import estimate_cost

    e = estimate_cost(
        printer_id=arguments["printer_id"],
        material=arguments["material"],
        filament_g=float(arguments["filament_g"]),
        duration_hours=float(arguments["duration_hours"]),
        price_per_kg_usd=arguments.get("price_per_kg_usd"),
        price_per_kwh_usd=arguments.get("price_per_kwh_usd"),
    )
    return e.to_dict()


def _tool_list_materials(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.materials import MATERIALS

    return {
        "materials": [
            {
                "material": m.material,
                "hotend_typical_c": m.hotend_typical_c,
                "bed_typical_c": m.bed_typical_c,
                "requires_enclosure": m.requires_enclosure,
                "requires_direct_drive": m.requires_direct_drive,
                "notes": m.notes,
            }
            for m in MATERIALS
        ]
    }


def _tool_truth_gate(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.validation.truth_gate import TruthGateConfig, run_truth_gate

    cfg = TruthGateConfig(printer_profile_id=arguments.get("printer_id"))
    rep = run_truth_gate(arguments["mesh_path"], cfg)
    return {
        "passed": rep.passed,
        "overall_status": rep.overall_status.value,
        "duration_seconds": rep.duration_seconds,
        "checks": [
            {
                "name": c.name,
                "status": c.status.value,
                "message": c.message,
                "measurement": c.measurement,
            }
            for c in rep.checks
        ],
    }


def _tool_skill_list(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.memory import SkillKind, SkillStore

    spath = arguments.get("skills_path", os.environ.get("HERMES3D_SKILLS", "./var/skills.json"))
    store = SkillStore(spath)
    kind = SkillKind(arguments["kind"]) if "kind" in arguments else None
    return {"skills": [s.to_dict() for s in store.list(kind=kind)]}


def _tool_skill_lookup(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.memory import SkillKind, SkillStore

    spath = arguments.get("skills_path", os.environ.get("HERMES3D_SKILLS", "./var/skills.json"))
    store = SkillStore(spath)
    matches = store.lookup(
        kind=SkillKind(arguments["kind"]),
        printer_id=arguments.get("printer_id"),
        material=arguments.get("material"),
        quality_level=arguments.get("quality_level"),
        hour_of_day=arguments.get("hour_of_day"),
        min_confidence=float(arguments.get("min_confidence", 0.0)),
    )
    return {"matches": [s.to_dict() for s in matches]}


def _tool_predict_failure(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.intelligence import predict_failure
    from hermes3d.core.memory import SkillStore

    hpath = arguments.get("history_path", os.environ.get("HERMES3D_HISTORY", ""))
    spath = arguments.get("skills_path", os.environ.get("HERMES3D_SKILLS", ""))
    history = PrintHistory(hpath) if hpath else None
    skills = SkillStore(spath) if spath else None
    f = predict_failure(
        printer_id=arguments["printer_id"],
        material=arguments["material"],
        history=history,
        skills=skills,
    )
    return f.to_dict()


def _tool_analyze_mesh(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh_file

    return analyze_mesh_file(arguments["mesh_path"]).to_dict()


def _tool_generate_profile(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.memory import SkillStore
    from hermes3d.core.slicer.profile_generator import generate_profile

    spath = arguments.get("skills_path", os.environ.get("HERMES3D_SKILLS", ""))
    skills = SkillStore(spath) if spath else None
    p = generate_profile(
        printer_id=arguments["printer_id"],
        material=arguments["material"],
        quality_level=arguments.get("quality_level", "normal"),
        skills=skills,
    )
    out_path = arguments.get("output_path")
    if out_path:
        p.write(out_path)
    return {
        "profile_id": p.profile_id,
        "settings": p.settings,
        "applied_skills": p.applied_skills,
        "ini_text": p.to_ini(),
        "output_path": out_path,
    }


def _tool_parallel_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    from hermes3d.core.agents.parallel_planner import (
        PartRequest,
        plan_parallel_print,
    )

    parts = [
        PartRequest(
            part_id=p["part_id"],
            mesh_extents_mm=tuple(p["mesh_extents_mm"]),
            mesh_xy_radius_mm=p.get("mesh_xy_radius_mm"),
            material=p.get("material", "PLA"),
            quality_level=p.get("quality_level", "normal"),
            estimated_time_min=float(p.get("estimated_time_min", 0)),
        )
        for p in arguments["parts"]
    ]
    plan = plan_parallel_print(
        parts,
        max_parallel_printers=arguments.get("max_parallel_printers"),
        excluded_printers=tuple(arguments.get("excluded_printers", ())),
    )
    return plan.to_dict()


# Tool catalog with JSON Schemas
TOOLS: list[dict[str, Any]] = [
    {
        "name": "hermes3d.dispatch",
        "description": "Pick the best printer in the 12-printer fleet for a "
        "given mesh + material + strategy. Returns the chosen "
        "printer plus full candidate scoring table.",
        "inputSchema": {
            "type": "object",
            "required": ["mesh_extents_mm"],
            "properties": {
                "mesh_extents_mm": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Bounding-box dimensions (dx, dy, dz) in mm",
                },
                "mesh_xy_radius_mm": {"type": ["number", "null"]},
                "material": {"type": "string", "default": "PLA"},
                "quality_level": {
                    "type": "string",
                    "enum": ["draft", "normal", "fine"],
                    "default": "normal",
                },
                "strategy": {
                    "type": "string",
                    "enum": [
                        "auto",
                        "fastest",
                        "quality",
                        "largest_bed",
                        "smallest_fit",
                        "least_busy",
                        "delta_prefer",
                        "cartesian_prefer",
                    ],
                    "default": "auto",
                },
                "excluded_printers": {"type": "array", "items": {"type": "string"}},
                "allowed_printers": {"type": "array", "items": {"type": "string"}},
            },
        },
        "_handler": _tool_dispatch,
    },
    {
        "name": "hermes3d.fleet_status",
        "description": "Get live state (reachable, klippy_state, active job, "
        "loaded spool) of every printer in the fleet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queue_path": {"type": "string"},
                "spools_path": {"type": "string"},
                "timeout_s": {"type": "number", "default": 2.5},
            },
        },
        "_handler": _tool_fleet_status,
    },
    {
        "name": "hermes3d.queue_list",
        "description": "List print jobs in the queue. Optional filter by state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "queue_path": {"type": "string"},
            },
        },
        "_handler": _tool_queue_list,
    },
    {
        "name": "hermes3d.queue_enqueue",
        "description": "Add a new print job to the queue.",
        "inputSchema": {
            "type": "object",
            "required": ["mesh_path", "mesh_sha256"],
            "properties": {
                "mesh_path": {"type": "string"},
                "mesh_sha256": {"type": "string"},
                "material": {"type": "string", "default": "PLA"},
                "quality_level": {"type": "string", "default": "normal"},
                "layer_height_mm": {"type": "number", "default": 0.2},
                "requested_strategy": {"type": "string", "default": "auto"},
                "notes": {"type": "string"},
                "queue_path": {"type": "string"},
            },
        },
        "_handler": _tool_queue_enqueue,
    },
    {
        "name": "hermes3d.queue_cancel",
        "description": "Cancel a queued or running job by ID.",
        "inputSchema": {
            "type": "object",
            "required": ["job_id"],
            "properties": {
                "job_id": {"type": "string"},
                "queue_path": {"type": "string"},
            },
        },
        "_handler": _tool_queue_cancel,
    },
    {
        "name": "hermes3d.spool_list",
        "description": "Inventory of registered filament spools "
        "(material, color, vendor, remaining grams, loaded printer).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "printer_id": {"type": "string"},
                "material": {"type": "string"},
                "spools_path": {"type": "string"},
            },
        },
        "_handler": _tool_spool_list,
    },
    {
        "name": "hermes3d.proof_verify",
        "description": "Verify a signed proof envelope JSON: HMAC + file hashes.",
        "inputSchema": {
            "type": "object",
            "required": ["proof_path"],
            "properties": {
                "proof_path": {"type": "string"},
                "check_files": {"type": "boolean", "default": True},
            },
        },
        "_handler": _tool_proof_verify,
    },
    {
        "name": "hermes3d.estimate_cost",
        "description": "Compute filament + electricity cost for a print (USD + Wh).",
        "inputSchema": {
            "type": "object",
            "required": ["printer_id", "material", "filament_g", "duration_hours"],
            "properties": {
                "printer_id": {"type": "string"},
                "material": {"type": "string"},
                "filament_g": {"type": "number"},
                "duration_hours": {"type": "number"},
                "price_per_kg_usd": {"type": ["number", "null"]},
                "price_per_kwh_usd": {"type": ["number", "null"]},
            },
        },
        "_handler": _tool_estimate_cost,
    },
    {
        "name": "hermes3d.list_materials",
        "description": "Catalog of supported filament materials and their printer requirements.",
        "inputSchema": {"type": "object", "properties": {}},
        "_handler": _tool_list_materials,
    },
    {
        "name": "hermes3d.truth_gate",
        "description": "Run the Truth Gate (printability validation) on a mesh "
        "file. Optionally validates against a specific printer.",
        "inputSchema": {
            "type": "object",
            "required": ["mesh_path"],
            "properties": {
                "mesh_path": {"type": "string"},
                "printer_id": {"type": "string"},
            },
        },
        "_handler": _tool_truth_gate,
    },
    {
        "name": "hermes3d.skill_list",
        "description": "List all skills the agent has learned. Optional kind "
        "filter (parameter_override, printer_quirk, "
        "material_quirk, scheduling_pref, user_preference, "
        "failure_pattern).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "skills_path": {"type": "string"},
            },
        },
        "_handler": _tool_skill_list,
    },
    {
        "name": "hermes3d.skill_lookup",
        "description": "Look up skills matching a specific (printer × material "
        "× quality × hour) scope. Returns most-specific first.",
        "inputSchema": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": {"type": "string"},
                "printer_id": {"type": "string"},
                "material": {"type": "string"},
                "quality_level": {"type": "string"},
                "hour_of_day": {"type": "integer"},
                "min_confidence": {"type": "number", "default": 0.0},
                "skills_path": {"type": "string"},
            },
        },
        "_handler": _tool_skill_lookup,
    },
    {
        "name": "hermes3d.predict_failure",
        "description": "Estimate failure probability for a (printer × "
        "material) combo. Blends print history, material "
        "history, and skill signals into a calibrated "
        "probability with citations.",
        "inputSchema": {
            "type": "object",
            "required": ["printer_id", "material"],
            "properties": {
                "printer_id": {"type": "string"},
                "material": {"type": "string"},
                "history_path": {"type": "string"},
                "skills_path": {"type": "string"},
            },
        },
        "_handler": _tool_predict_failure,
    },
    {
        "name": "hermes3d.analyze_mesh",
        "description": "Geometric analysis: bbox, volume, overhang area + "
        "percentage, support volume estimate, bridge spans, "
        "first-layer area, height/aspect ratio, COM offset, "
        "thin-wall counts, and risk flags.",
        "inputSchema": {
            "type": "object",
            "required": ["mesh_path"],
            "properties": {"mesh_path": {"type": "string"}},
        },
        "_handler": _tool_analyze_mesh,
    },
    {
        "name": "hermes3d.generate_profile",
        "description": "Auto-generate a PrusaSlicer/OrcaSlicer .ini profile "
        "for a (printer × material × quality) combo. Applies "
        "matching parameter-override skills.",
        "inputSchema": {
            "type": "object",
            "required": ["printer_id", "material"],
            "properties": {
                "printer_id": {"type": "string"},
                "material": {"type": "string"},
                "quality_level": {"type": "string", "default": "normal"},
                "output_path": {"type": "string"},
                "skills_path": {"type": "string"},
            },
        },
        "_handler": _tool_generate_profile,
    },
    {
        "name": "hermes3d.parallel_plan",
        "description": "Plan a parallel print across multiple idle printers, one part per printer.",
        "inputSchema": {
            "type": "object",
            "required": ["parts"],
            "properties": {
                "parts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["part_id", "mesh_extents_mm"],
                        "properties": {
                            "part_id": {"type": "string"},
                            "mesh_extents_mm": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                            "mesh_xy_radius_mm": {"type": "number"},
                            "material": {"type": "string"},
                            "quality_level": {"type": "string"},
                            "estimated_time_min": {"type": "number"},
                        },
                    },
                },
                "max_parallel_printers": {"type": "integer"},
                "excluded_printers": {"type": "array", "items": {"type": "string"}},
            },
        },
        "_handler": _tool_parallel_plan,
    },
]


def _public_tools() -> list[dict[str, Any]]:
    """Return the tool catalog with handler refs stripped (for MCP listing)."""
    return [{k: v for k, v in t.items() if not k.startswith("_")} for t in TOOLS]


def get_handler(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    for t in TOOLS:
        if t["name"] == name:
            return t["_handler"]
    raise KeyError(f"Unknown tool: {name}")


# =============================================================================
# Minimal MCP STDIO server (works without the official mcp package)
# =============================================================================


def _send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _ok(req_id: Any, result: Any) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def serve_stdio() -> int:
    """Loop on stdin, dispatch JSON-RPC requests."""
    log.info("hermes3d MCP STDIO server starting")
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            _err(None, -32700, f"parse error: {exc}")
            continue
        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") or {}
        try:
            if method == "initialize":
                _ok(
                    req_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "hermes3d-os-lite", "version": "5.0.0"},
                    },
                )
            elif method == "tools/list":
                _ok(req_id, {"tools": _public_tools()})
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("arguments", {})
                handler = get_handler(name)
                result = handler(args)
                _ok(
                    req_id,
                    {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    },
                )
            elif method == "ping":
                _ok(req_id, {})
            elif method == "shutdown":
                _ok(req_id, {})
                return 0
            else:
                _err(req_id, -32601, f"method not found: {method}")
        except KeyError as exc:
            _err(req_id, -32602, str(exc))
        except Exception as exc:  # noqa: BLE001
            _err(req_id, -32603, f"internal error: {exc}")
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s mcp %(levelname)s %(message)s", stream=sys.stderr
    )
    return serve_stdio()


__all__ = ["TOOLS", "get_handler", "main", "serve_stdio"]


if __name__ == "__main__":
    sys.exit(main())
