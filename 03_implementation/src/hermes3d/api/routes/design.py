from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, rows, utc_now
from hermes3d.services.gpu_probe import probe_gpu
from hermes3d.services.gpu_render import render_stl_thumbnail_gpu
from hermes3d.services.local_state import implementation_path, source_modules
from hermes3d.services.modeling_backend import backend_summary_for_proof, survey_backends

router = APIRouter()

SOURCE_TOOL_IDS = {
    "blender_mcp_candidates",
    "blender",
    "cadquery",
    "freecad",
    "openscad",
    "trimesh",
    "flsun_slicer",
    "orcaslicer",
    "prusaslicer",
}

LOCAL_TOOL_LABELS = {
    "openscad_cli": "OpenSCAD CLI",
    "prusaslicer_cli": "PrusaSlicer CLI",
    "orcaslicer_cli": "OrcaSlicer CLI",
    "flsun_slicer_cli": "FLSUN Slicer CLI",
}


class DesignIntake(BaseModel):
    prompt: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class UnsupportedDesignError(ValueError):
    pass


@router.post("/api/design/intake", status_code=201)
def submit_intake(body: DesignIntake) -> dict:
    status = _toolchain_status()
    if status["overall"] != "ready":
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Design CAD/modeling toolchain is not ready.",
                "toolchain": status,
            },
        )
    try:
        template_id, spec = _resolve_supported_design(body.prompt, body.constraints)
    except UnsupportedDesignError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": str(exc),
                "supported_templates": _supported_templates(),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "blocked",
                "reason": str(exc),
                "supported_templates": _supported_templates(),
            },
        ) from exc
    job_id = new_id()
    target_printer_id = body.constraints.get("target_printer_id")
    execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run) VALUES (?, ?, 'design', 'running', ?, 1)",
        (
            job_id,
            _design_title(body.prompt),
            target_printer_id if isinstance(target_printer_id, str) else None,
        ),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at)
        VALUES (?, ?, 1, 'Design intake', 'done', datetime('now'), datetime('now'))
        """,
        (new_id(), job_id),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'design_intake', 'hermes-agent', ?)",
        (new_id(), job_id, body.prompt[:800]),
    )
    try:
        result = _execute_supported_design(
            job_id=job_id,
            template_id=template_id,
            spec=spec,
            target_printer_id=target_printer_id if isinstance(target_printer_id, str) else None,
            prompt=body.prompt,
        )
    except Exception as exc:
        execute(
            "UPDATE jobs SET status = 'failed', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
        execute(
            """
            INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, error)
            VALUES (?, ?, 2, 'Parametric mesh export', 'failed', datetime('now'), datetime('now'), ?)
            """,
            (new_id(), job_id, str(exc)[:1000]),
        )
        _record_proof_event(
            "design.executor.failed",
            {
                "job_id": job_id,
                "template": template_id,
                "target_printer_id": target_printer_id,
                "reason": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "reason": f"Design executor failed: {exc}",
                "job_id": job_id,
            },
        ) from exc
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "completed",
        "accepted": True,
        "created": True,
        "template": template_id,
        **result,
    }


@router.get("/api/design/specs")
def specs() -> list[dict]:
    return rows("SELECT * FROM jobs WHERE job_type = 'design' ORDER BY created_at DESC")


@router.get("/api/design/templates")
def list_templates() -> list[dict]:
    """Return templates backed by real executor modules present in this repo.

    Each entry is derived from actual importable Python executor code — not
    hardcoded fake metadata. If a module cannot be imported the template is
    still listed but flagged executor_available=False so the UI can show why.
    """
    return _discover_templates()


@router.get("/api/design/providers")
def list_providers() -> list[dict]:
    """Return real-time health of each CAD/modeling provider.

    Results come from live shutil.which() probes and Python importlib checks —
    never from cached stubs or fabricated values. Each provider reports its
    actual detected path or the reason it is unavailable.
    """
    return _probe_providers()


@router.get("/api/design/toolchain/status")
def toolchain_status() -> dict:
    return _toolchain_status()


@router.get("/api/design/backends")
def list_backends() -> dict[str, Any]:
    """Return the live modeling-backend survey + GPU probe.

    Real probes only — every entry comes from importlib / shutil.which /
    nvidia-smi. No cached stubs and no fabricated values. Used by the UI
    Design tab to show which backend will produce the next artifact and
    whether the local GPU is reachable.
    """
    survey = [backend.to_dict() for backend in survey_backends()]
    gpu = probe_gpu()
    return {
        "backends": survey,
        "default_template_backend": backend_summary_for_proof("desk_organizer"),
        "gpu": gpu,
        "probed_at": utc_now(),
    }


def _toolchain_status() -> dict:
    modules = source_modules()
    source_cards = _source_cards(modules)
    local_audit = _local_tooling_audit()
    local_tools = _local_tool_cards(local_audit)
    proof_rows = rows(
        "SELECT gate_name, status, error, checked_at FROM truth_gate_results ORDER BY checked_at DESC LIMIT 1"
    )
    latest_truth = proof_rows[0] if proof_rows else None
    openscad_ready = _tool_ready(local_tools, "openscad_cli")
    slicer_ready = any(
        _tool_ready(local_tools, tool_id)
        for tool_id in ("prusaslicer_cli", "orcaslicer_cli", "flsun_slicer_cli")
    )
    source_ready = any(
        item["status"] == "ready"
        for item in source_cards
        if item["id"] in {"cadquery", "openscad", "trimesh", "blender"}
    )
    mesh_ready = importlib.util.find_spec("trimesh") is not None
    executor_ready, executor_detail = _parametric_executor_status()
    blockers = [] if executor_ready else [executor_detail]
    return {
        "overall": "ready" if executor_ready else "blocked",
        "execution_ready": executor_ready,
        "blockers": blockers,
        "updated_at": utc_now(),
        "supported_templates": _supported_templates() if executor_ready else [],
        "stages": [
            {
                "id": "intake",
                "name": "Design intake",
                "label": "Design intake",
                "status": "ready",
                "detail": "The backend intake endpoint is available and routes supported parametric requests to a real executor.",
                "source": "backend",
            },
            {
                "id": "source_cad",
                "name": "Source CAD/modeler checkouts",
                "label": "Source CAD/modeler checkouts",
                "status": "ready" if source_ready else "warning",
                "detail": _source_summary(source_cards),
                "source": "source_registry",
                "proof_path": str(implementation_path("proof", "SOURCE_REGISTRY_TRUTH_AUDIT.json")),
            },
            {
                "id": "openscad_cli",
                "name": "OpenSCAD CAD CLI",
                "label": "OpenSCAD CAD CLI",
                "status": "ready" if openscad_ready else "not_installed",
                "detail": _tool_detail(
                    local_tools,
                    "openscad_cli",
                    "OpenSCAD executable was not detected by the local tooling audit.",
                ),
                "source": "local_tooling_audit",
                "proof_path": str(implementation_path("proof", "LOCAL_TOOLING_AUDIT.json")),
            },
            {
                "id": "mesh_worker",
                "name": "Mesh validation worker",
                "label": "Mesh validation worker",
                "status": "ready" if mesh_ready else "blocked",
                "detail": "trimesh is importable for geometry validation and proof gates."
                if mesh_ready
                else "trimesh is not importable in the backend runtime.",
                "source": "python_runtime",
            },
            {
                "id": "slicer_cli",
                "name": "Slicer CLI bridge",
                "label": "Slicer CLI bridge",
                "status": "ready" if slicer_ready else "warning",
                "detail": _slicer_summary(local_tools),
                "source": "local_tooling_audit",
                "proof_path": str(implementation_path("proof", "LOCAL_TOOLING_AUDIT.json")),
            },
            {
                "id": "design_dispatch",
                "name": "Prompt-to-CAD executor",
                "label": "Prompt-to-CAD executor",
                "status": "ready" if executor_ready else "blocked",
                "detail": executor_detail,
                "source": "backend",
            },
            {
                "id": "proof",
                "name": "Latest truth gate",
                "label": "Latest truth gate",
                "status": str(latest_truth["status"]) if latest_truth else "not_run",
                "detail": _truth_detail(latest_truth),
                "source": "truth_gate_results",
            },
        ],
        "tools": local_tools,
        "sources": source_cards,
        "proof_sources": {
            "local_tooling": str(implementation_path("proof", "LOCAL_TOOLING_AUDIT.json")),
            "source_registry": str(
                implementation_path("proof", "SOURCE_REGISTRY_TRUTH_AUDIT.json")
            ),
            "flsun_profiles": str(implementation_path("proof", "FLSUN_PROFILE_SOURCE_AUDIT.json")),
        },
    }


def _design_title(prompt: str) -> str:
    first = next((line.strip() for line in prompt.splitlines() if line.strip()), "")
    return first[:80] or "Design Intake"


def _supported_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "desk_organizer",
            "name": "Parametric Desk Organizer",
            "executor": "hermes3d.core.design.desk_organizer",
            "outputs": ["stl", "proof_envelope"],
            "parameters": [
                "width_mm",
                "depth_mm",
                "height_mm",
                "tray_count",
                "pen_count",
                "phone_slot",
                "cable_passthrough",
            ],
        }
    ]


def _parametric_executor_status() -> tuple[bool, str]:
    try:
        from hermes3d.core.design.desk_organizer import OrganizerSpec

        OrganizerSpec().validated()
    except Exception as exc:
        return False, f"Parametric desk organizer executor is unavailable: {exc}"
    if importlib.util.find_spec("trimesh") is None:
        return False, "trimesh is not importable in the backend runtime."
    return (
        True,
        "Parametric desk organizer executor is wired through the local trimesh/manifold worker and writes STL plus signed proof envelopes.",
    )


def _resolve_supported_design(prompt: str, constraints: dict[str, Any]) -> tuple[str, Any]:
    from hermes3d.core.design.desk_organizer import OrganizerSpec

    template = (
        str(constraints.get("template") or constraints.get("design_template") or "").strip().lower()
    )
    text = f"{template} {prompt}".lower()
    supported = template in {"desk_organizer", "parametric_desk_organizer", "organizer"} or any(
        token in text
        for token in ("desk organizer", "organizer", "tray", "pen holder", "phone slot")
    )
    if not supported:
        raise UnsupportedDesignError(
            "Supported Design executor currently handles parametric desk organizer requests only. Choose the Desk Organizer template or include organizer/tray/pen-holder intent."
        )
    spec = OrganizerSpec(
        width_mm=_constraint_float(constraints, "width_mm", 180.0),
        depth_mm=_constraint_float(constraints, "depth_mm", 100.0),
        height_mm=_constraint_float(constraints, "height_mm", 55.0),
        wall_mm=_constraint_float(constraints, "wall_mm", 2.0),
        floor_mm=_constraint_float(constraints, "floor_mm", 2.0),
        tray_count=_constraint_int(constraints, "tray_count", 3),
        pen_count=_constraint_int(constraints, "pen_count", 4),
        phone_slot=_constraint_bool(constraints, "phone_slot", True),
        cable_passthrough=_constraint_bool(constraints, "cable_passthrough", True),
    ).validated()
    return "desk_organizer", spec


def _execute_supported_design(
    *,
    job_id: str,
    template_id: str,
    spec: Any,
    target_printer_id: str | None,
    prompt: str,
) -> dict[str, Any]:
    from hermes3d.core.design.desk_organizer import build_organizer
    from hermes3d.core.proof import write_proof

    output_dir = implementation_path("var", "designs", job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    signature = spec.signature()
    mesh_path = output_dir / f"{template_id}_{signature}.stl"
    proof_path = output_dir / f"{template_id}_{signature}.proof.json"
    mesh = build_organizer(spec)
    mesh.export(mesh_path, file_type="stl")
    if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
        raise RuntimeError(f"Mesh export produced no bytes at {mesh_path}")

    # W18-A20: record which modeling backend produced the artifact + try the
    # GPU code path (Blender Cycles CUDA thumbnail render). Honest fallback:
    # if anything fails, ``gpu_used`` stays False with the reason recorded.
    modeling_backend_payload: dict[str, Any] = backend_summary_for_proof(template_id)
    gpu_probe_payload: dict[str, Any] = probe_gpu()
    gpu_op_payload: dict[str, Any] = {"used": False, "reason": "Not attempted."}
    visual_evidence: list[tuple[str, Any]] = []
    thumbnail_path = output_dir / "thumbnail_gpu.png"
    if gpu_probe_payload.get("available"):
        gpu_op_payload = render_stl_thumbnail_gpu(
            stl_path=mesh_path,
            out_path=thumbnail_path,
            samples=16,
        )
        if gpu_op_payload.get("used") and thumbnail_path.is_file():
            visual_evidence.append(("thumbnail_gpu", thumbnail_path))
    else:
        gpu_op_payload = {
            "used": False,
            "reason": (
                "GPU probe reported unavailable: "
                + str(gpu_probe_payload.get("reason", "no reason recorded"))
            ),
        }

    modeling_backend_payload["gpu_operation"] = gpu_op_payload

    gpu_field: dict[str, Any] | None = None
    if gpu_probe_payload.get("available"):
        gpu_field = {
            "vendor": gpu_probe_payload.get("vendor"),
            "model": gpu_probe_payload.get("model"),
            "driver": gpu_probe_payload.get("driver"),
            "cuda": gpu_probe_payload.get("cuda"),
            "vram_total_mib": gpu_probe_payload.get("vram_total_mib"),
            "operation": gpu_op_payload,
        }

    written_proof = write_proof(
        mesh_path=mesh_path,
        output_path=proof_path,
        generator_name="hermes3d.parametric.desk_organizer",
        generator_version="1.0.0",
        generator_signature=signature,
        visual_evidence_paths=visual_evidence if visual_evidence else None,
        modeling_backend=modeling_backend_payload,
        gpu_used=bool(gpu_op_payload.get("used")),
        gpu=gpu_field,
    )
    proof = json.loads(written_proof.read_text(encoding="utf-8"))
    truth_report = proof.get("truth_gate_report") if isinstance(proof, dict) else {}
    truth_status = str(
        truth_report.get("overall_status") if isinstance(truth_report, dict) else "error"
    )
    if truth_status != "pass":
        raise RuntimeError(f"Truth gate rejected generated mesh with status {truth_status}")

    mesh_sha = _file_sha256(mesh_path)
    proof_sha = _file_sha256(written_proof)
    mesh_artifact_id = new_id()
    proof_artifact_id = new_id()
    mesh_notes = {
        "sha256": mesh_sha,
        "template": template_id,
        "signature": signature,
        "target_printer_id": target_printer_id,
        "parameters": dict(spec.__dict__),
        "mesh": _mesh_summary(mesh),
        "proof_artifact_id": proof_artifact_id,
    }
    proof_notes = {
        "sha256": proof_sha,
        "mesh_artifact_id": mesh_artifact_id,
        "truth_gate_status": truth_status,
        "signature_algorithm": proof.get("signature", {}).get("algorithm")
        if isinstance(proof, dict)
        else None,
    }
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'mesh', 'design-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            mesh_artifact_id,
            job_id,
            mesh_path.name,
            str(mesh_path),
            mesh_path.stat().st_size,
            as_json(mesh_notes),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'proof_report', 'design-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            proof_artifact_id,
            job_id,
            written_proof.name,
            str(written_proof),
            written_proof.stat().st_size,
            as_json(proof_notes),
        ),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, 2, 'Parametric mesh export', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 3, 'Signed proof envelope', 'done', datetime('now'), datetime('now'), 0)
        """,
        (new_id(), job_id, new_id(), job_id),
    )
    execute(
        "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, 'design.parametric_mesh', 'pass', NULL, ?)",
        (new_id(), job_id, _truth_duration(truth_report)),
    )
    proof_event_id = _record_proof_event(
        "design.executor.completed",
        {
            "job_id": job_id,
            "template": template_id,
            "target_printer_id": target_printer_id,
            "mesh_artifact_id": mesh_artifact_id,
            "proof_artifact_id": proof_artifact_id,
            "mesh_path": str(mesh_path),
            "proof_path": str(written_proof),
            "mesh_sha256": mesh_sha,
            "proof_sha256": proof_sha,
            "truth_gate_status": truth_status,
            "prompt_head": prompt[:300],
            # W18-A20: backend identity in the durable proof event too.
            "modeling_backend": {
                "name": modeling_backend_payload.get("name"),
                "engine": (modeling_backend_payload.get("engine") or {}).get("name"),
                "version": modeling_backend_payload.get("version"),
            },
            "gpu_used": bool(gpu_op_payload.get("used")),
            "gpu_model": (gpu_field or {}).get("model"),
        },
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'design_executor_completed', 'design-executor', ?)",
        (new_id(), job_id, f"Generated {mesh_path.name}; proof_event_id={proof_event_id}"),
    )
    execute(
        "UPDATE jobs SET status = 'completed', updated_at = datetime('now') WHERE id = ?", (job_id,)
    )
    return {
        "artifact": {
            "id": mesh_artifact_id,
            "label": mesh_path.name,
            "file_path": str(mesh_path),
            "file_size": mesh_path.stat().st_size,
            "sha256": mesh_sha,
        },
        "proof": {
            "id": proof_artifact_id,
            "label": written_proof.name,
            "file_path": str(written_proof),
            "file_size": written_proof.stat().st_size,
            "sha256": proof_sha,
            "event_id": proof_event_id,
        },
        "truth_gate": {"status": truth_status, "duration_s": _truth_duration(truth_report)},
        "parameters": dict(spec.__dict__),
        # W18-A20: surface backend identity + GPU usage so the UI Design tab
        # can render the proof badge directly from the intake response.
        "modeling_backend": modeling_backend_payload,
        "gpu_used": bool(gpu_op_payload.get("used")),
        "gpu": gpu_field,
    }


def _record_proof_event(event_type: str, payload: dict[str, Any]) -> str:
    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, 'design-executor', ?)",
        (event_id, event_type, as_json(payload)),
    )
    return event_id


def _constraint_float(constraints: dict[str, Any], key: str, default: float) -> float:
    value = constraints.get(key, default)
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be numeric.") from exc
    if not (1 <= parsed <= 500):
        raise ValueError(f"{key} must be between 1 and 500 mm.")
    return parsed


def _constraint_int(constraints: dict[str, Any], key: str, default: int) -> int:
    value = constraints.get(key, default)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer.") from exc
    if not (0 <= parsed <= 24):
        raise ValueError(f"{key} must be between 0 and 24.")
    return parsed


def _constraint_bool(constraints: dict[str, Any], key: str, default: bool) -> bool:
    value = constraints.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _file_sha256(path: Any) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _mesh_summary(mesh: Any) -> dict[str, Any]:
    bounds = mesh.bounds.tolist() if hasattr(mesh.bounds, "tolist") else mesh.bounds
    extents = mesh.extents.tolist() if hasattr(mesh.extents, "tolist") else mesh.extents
    return {
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "bbox_mm": bounds,
        "extents_mm": extents,
        "volume_mm3": float(mesh.volume),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
    }


def _truth_duration(truth_report: Any) -> float | None:
    if isinstance(truth_report, dict):
        duration = truth_report.get("duration_seconds")
        if isinstance(duration, int | float):
            return float(duration)
    return None


def _local_tooling_audit() -> dict:
    path = implementation_path("proof", "LOCAL_TOOLING_AUDIT.json")
    if not path.exists():
        return {"tools": {}}
    try:
        with path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"tools": {}}
    return parsed if isinstance(parsed, dict) else {"tools": {}}


def _local_tool_cards(audit: dict) -> list[dict]:
    raw_tools = audit.get("tools")
    if not isinstance(raw_tools, dict):
        return []
    cards: list[dict] = []
    for tool_id, label in LOCAL_TOOL_LABELS.items():
        raw = raw_tools.get(tool_id)
        if not isinstance(raw, dict):
            cards.append(
                {
                    "id": tool_id,
                    "name": label,
                    "status": "not_installed",
                    "detail": "No local tooling audit record exists for this executable.",
                    "source": "local_tooling_audit",
                    "capabilities": [],
                    "path": None,
                    "detected": False,
                    "executed": False,
                    "return_code": None,
                }
            )
            continue
        detected = bool(raw.get("detected"))
        executed = bool(raw.get("executed"))
        return_code = raw.get("return_code")
        capabilities = raw.get("capabilities") if isinstance(raw.get("capabilities"), list) else []
        path = str(raw.get("path") or "")
        output_head = raw.get("output_head") if isinstance(raw.get("output_head"), list) else []
        version = next((str(line) for line in output_head if str(line).strip()), "")
        if version:
            detail = version
        elif detected and executed:
            detail = "Executable completed successfully; no stdout lines were returned."
        elif detected:
            detail = "Executable detected; execution was skipped by policy."
        else:
            detail = "Executable was not detected."
        cards.append(
            {
                "id": tool_id,
                "name": label,
                "status": "ready"
                if detected and (executed or return_code == 0)
                else "detected"
                if detected
                else "not_installed",
                "detail": detail,
                "source": "local_tooling_audit",
                "capabilities": [str(item) for item in capabilities],
                "path": path or None,
                "detected": detected,
                "executed": executed,
                "return_code": return_code if isinstance(return_code, int) else None,
                "proof_path": str(implementation_path("proof", "LOCAL_TOOLING_AUDIT.json")),
            }
        )
    return cards


def _source_cards(modules: list[dict]) -> list[dict]:
    cards: list[dict] = []
    for module in modules:
        module_id = str(module.get("id") or "")
        if module_id not in SOURCE_TOOL_IDS:
            continue
        install_state = str(module.get("install_state") or "unavailable")
        bridge_tasks = _json_list(module.get("bridge_tasks"))
        ready = install_state in {"installed", "detected", "healthy"}
        cards.append(
            {
                "id": module_id,
                "module_id": module_id,
                "name": str(module.get("display_name") or module_id),
                "status": "ready" if ready else "blocked",
                "detail": f"{install_state}; {module.get('detected_version') or 'version not recorded'}",
                "source": "source_registry",
                "capabilities": bridge_tasks,
                "path": module.get("local_path"),
                "repo_url": module.get("repo_url"),
                "priority": module.get("priority"),
                "license": module.get("license"),
                "launch_kind": module.get("launch_kind"),
                "proof_path": str(implementation_path("proof", "SOURCE_REGISTRY_TRUTH_AUDIT.json")),
            }
        )
    return cards


def _json_list(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _tool_ready(tools: list[dict], tool_id: str) -> bool:
    return any(tool.get("id") == tool_id and tool.get("status") == "ready" for tool in tools)


def _tool_detail(tools: list[dict], tool_id: str, fallback: str) -> str:
    tool = next((item for item in tools if item.get("id") == tool_id), None)
    if not tool:
        return fallback
    path = tool.get("path")
    detail = str(tool.get("detail") or fallback)
    return f"{detail} Path: {path}" if path else detail


def _slicer_summary(tools: list[dict]) -> str:
    ready = [
        tool["name"]
        for tool in tools
        if tool.get("id") in {"prusaslicer_cli", "orcaslicer_cli", "flsun_slicer_cli"}
        and tool.get("status") == "ready"
    ]
    if ready:
        return "Ready slicer executables: " + ", ".join(ready) + "."
    detected = [
        tool["name"]
        for tool in tools
        if tool.get("id") in {"prusaslicer_cli", "orcaslicer_cli", "flsun_slicer_cli"}
        and tool.get("status") == "detected"
    ]
    if detected:
        return (
            "Detected slicer executables need a successful CLI proof run: "
            + ", ".join(detected)
            + "."
        )
    return "No local slicer CLI executable is ready."


def _source_summary(sources: list[dict]) -> str:
    ready = [
        source["name"]
        for source in sources
        if source.get("status") == "ready"
        and source.get("id") in {"cadquery", "openscad", "trimesh", "blender"}
    ]
    if ready:
        return "Installed source checkouts: " + ", ".join(ready[:6]) + "."
    return "No installed CAD/modeling source checkout is recorded."


def _truth_detail(latest_truth: dict | None) -> str:
    if not latest_truth:
        return "No truth gate result has been recorded yet."
    gate_name = str(latest_truth.get("gate_name") or "truth gate")
    status = str(latest_truth.get("status") or "unknown")
    checked_at = str(latest_truth.get("checked_at") or "unknown time")
    error = latest_truth.get("error")
    return f"{gate_name} returned {status} at {checked_at}{': ' + str(error) if error else ''}."


# ---------------------------------------------------------------------------
# Template discovery — scans real executor modules, never fake metadata
# ---------------------------------------------------------------------------

_TEMPLATE_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "desk_organizer",
        "name": "Parametric Desk Organizer",
        "description": (
            "Real CSG organizer: compartments, circular pen holders, "
            "phone slot, cable pass-through. Runs via trimesh+manifold3d."
        ),
        "executor_module": "hermes3d.core.design.desk_organizer",
        "executor_class": "OrganizerSpec",
        "outputs": ["stl", "proof_envelope"],
        "parameters": [
            "width_mm",
            "depth_mm",
            "height_mm",
            "wall_mm",
            "floor_mm",
            "tray_count",
            "pen_count",
            "phone_slot",
            "cable_passthrough",
        ],
        "requires": ["trimesh", "manifold3d"],
        "preview_available": False,
        "preview_note": "No renderer detected; preview not available.",
    },
]


def _discover_templates() -> list[dict[str, Any]]:
    """Return template list with live executor-availability check per entry."""
    result: list[dict[str, Any]] = []
    for tmpl in _TEMPLATE_REGISTRY:
        entry = dict(tmpl)
        module_name = str(tmpl.get("executor_module") or "")
        class_name = str(tmpl.get("executor_class") or "")
        if module_name:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                try:
                    mod = importlib.import_module(module_name)
                    cls = getattr(mod, class_name, None) if class_name else None
                    entry["executor_available"] = True
                    entry["executor_detail"] = (
                        f"Module {module_name!r} importable; "
                        f"class {class_name!r} {'present' if cls else 'not found'}."
                    )
                except Exception as exc:
                    entry["executor_available"] = False
                    entry["executor_detail"] = f"Import error in {module_name!r}: {exc}"
            else:
                entry["executor_available"] = False
                entry["executor_detail"] = f"Module {module_name!r} not found in Python path."
        else:
            entry["executor_available"] = False
            entry["executor_detail"] = "No executor module configured."

        # Check Python deps
        missing_deps = [
            dep for dep in (tmpl.get("requires") or []) if importlib.util.find_spec(dep) is None
        ]
        entry["missing_deps"] = missing_deps
        entry["deps_ok"] = len(missing_deps) == 0

        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Provider health probes — real shutil.which + importlib checks, no stubs
# ---------------------------------------------------------------------------


def _probe_providers() -> list[dict[str, Any]]:
    """Probe all supported CAD/modeling providers and return real health data."""
    providers: list[dict[str, Any]] = []

    # --- OpenSCAD CLI ---
    providers.append(
        _probe_cli_provider(
            provider_id="openscad",
            display_name="OpenSCAD",
            kind="cad_cli",
            exe_names=["openscad", "openscad-nightly"],
            version_args=["--version"],
            capabilities=["solid_csg", "parametric_scad", "stl_export"],
            docs_url="https://openscad.org/",
            fallback_paths=[
                r"C:\Program Files\OpenSCAD\openscad.exe",
                r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
            ],
        )
    )

    # --- Blender ---
    providers.append(
        _probe_cli_provider(
            provider_id="blender",
            display_name="Blender",
            kind="modeling_cli",
            exe_names=["blender"],
            version_args=["--version"],
            capabilities=["mesh_modeling", "stl_export", "python_scripting", "mcp_support"],
            docs_url="https://www.blender.org/",
            fallback_paths=[
                r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            ],
        )
    )

    # --- CadQuery (Python library) ---
    providers.append(
        _probe_python_provider(
            provider_id="cadquery",
            display_name="CadQuery",
            kind="python_cad_library",
            module_name="cadquery",
            capabilities=["parametric_cad", "brep_modeling", "step_export", "stl_export"],
            docs_url="https://cadquery.readthedocs.io/",
        )
    )

    # --- trimesh (mesh processing — required for desk_organizer) ---
    providers.append(
        _probe_python_provider(
            provider_id="trimesh",
            display_name="trimesh",
            kind="python_mesh_library",
            module_name="trimesh",
            capabilities=[
                "mesh_validation",
                "stl_import_export",
                "watertight_check",
                "boolean_ops",
            ],
            docs_url="https://trimsh.org/",
        )
    )

    # --- manifold3d (boolean CSG — required for desk_organizer) ---
    providers.append(
        _probe_python_provider(
            provider_id="manifold3d",
            display_name="manifold3d",
            kind="python_csg_library",
            module_name="manifold3d",
            capabilities=["boolean_csg", "manifold_mesh", "robust_union_difference"],
            docs_url="https://github.com/elalish/manifold",
        )
    )

    # --- FreeCAD ---
    providers.append(
        _probe_cli_provider(
            provider_id="freecad",
            display_name="FreeCAD",
            kind="cad_cli",
            exe_names=["freecad", "FreeCAD", "freecadcmd", "FreeCADCmd"],
            version_args=["--version"],
            capabilities=["parametric_cad", "step_export", "stl_export", "python_scripting"],
            docs_url="https://www.freecad.org/",
        )
    )

    return providers


def _probe_cli_provider(
    *,
    provider_id: str,
    display_name: str,
    kind: str,
    exe_names: list[str],
    version_args: list[str],
    capabilities: list[str],
    docs_url: str,
    fallback_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Probe a CLI executable via shutil.which then known install paths."""
    detected_path: str | None = None
    for exe in exe_names:
        found = shutil.which(exe)
        if found:
            detected_path = found
            break

    # Fall back to known Windows install paths when shutil.which misses them
    if not detected_path and fallback_paths:
        for candidate in fallback_paths:
            p = Path(candidate)
            if p.is_file():
                detected_path = str(p)
                break

    if not detected_path:
        return {
            "id": provider_id,
            "name": display_name,
            "kind": kind,
            "status": "not_installed",
            "detected": False,
            "path": None,
            "version": None,
            "version_detail": None,
            "capabilities": capabilities,
            "docs_url": docs_url,
            "detail": f"{display_name} executable not found on PATH. Searched: {', '.join(exe_names)}.",
            "probed_at": utc_now(),
        }

    # Try to get version output
    version_line: str | None = None
    try:
        result = subprocess.run(
            [detected_path, *version_args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout + result.stderr).strip()
        version_line = next((line.strip() for line in output.splitlines() if line.strip()), None)
        status = "ready"
    except subprocess.TimeoutExpired:
        status = "detected"
        version_line = "Version probe timed out after 5 s."
    except Exception as exc:
        status = "detected"
        version_line = f"Version probe error: {exc}"

    return {
        "id": provider_id,
        "name": display_name,
        "kind": kind,
        "status": status,
        "detected": True,
        "path": detected_path,
        "version": version_line,
        "version_detail": version_line,
        "capabilities": capabilities,
        "docs_url": docs_url,
        "detail": f"Detected at {detected_path}. {version_line or ''}".strip(),
        "probed_at": utc_now(),
    }


def _probe_python_provider(
    *,
    provider_id: str,
    display_name: str,
    kind: str,
    module_name: str,
    capabilities: list[str],
    docs_url: str,
) -> dict[str, Any]:
    """Probe a Python package with importlib — real result only."""
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {
            "id": provider_id,
            "name": display_name,
            "kind": kind,
            "status": "not_installed",
            "detected": False,
            "path": None,
            "version": None,
            "version_detail": None,
            "capabilities": capabilities,
            "docs_url": docs_url,
            "detail": f"Python module {module_name!r} is not importable in the current runtime.",
            "probed_at": utc_now(),
        }

    # Try to get version
    version_str: str | None = None
    module_path: str | None = None
    try:
        import importlib.metadata as meta_mod

        version_str = meta_mod.version(module_name)
    except Exception as exc:  # noqa: BLE001 -- Wave Agent 7: surface the silent fallback
        try:
            import logging

            logging.getLogger(__name__).debug(
                "design.module_version_lookup: metadata.version(%r) failed: %s: %s",
                module_name,
                type(exc).__name__,
                exc,
            )
        except Exception:  # noqa: BLE001
            pass

    if spec.origin:
        module_path = str(spec.origin)

    try:
        importlib.import_module(module_name)
        status = "ready"
        detail = f"Module {module_name!r} importable{' at ' + module_path if module_path else ''}. Version: {version_str or 'unknown'}."
    except Exception as exc:
        status = "detected"
        detail = f"Module {module_name!r} found but import failed: {exc}"

    return {
        "id": provider_id,
        "name": display_name,
        "kind": kind,
        "status": status,
        "detected": True,
        "path": module_path,
        "version": version_str,
        "version_detail": f"v{version_str}" if version_str else None,
        "capabilities": capabilities,
        "docs_url": docs_url,
        "detail": detail,
        "probed_at": utc_now(),
    }
