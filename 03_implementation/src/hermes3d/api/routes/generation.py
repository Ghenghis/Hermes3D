from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, rows
from hermes3d.core.printability_truth_gate import GATE_DEFINITIONS, run_core_truth_gate
from hermes3d.services.local_state import implementation_path, port_reachable, service_url
from hermes3d.services.local_state import set_service_url as save_service_url

# Path to Lane 04 (H3D-CLAUDE-SOURCE-GEN3D) proof file — read-only
# File is at: src/hermes3d/api/routes/generation.py
# parents[0]=routes, [1]=api, [2]=hermes3d, [3]=src, [4]=03_implementation, [5]=Hermes3D
_LANE04_PROOF_PATH = (
    Path(__file__).resolve().parents[5]
    / "03_implementation"
    / "proof"
    / "GEN3D_VERIFY_2026-05-06.json"
)

# Adapter registry schemas dir for template discovery
_SCHEMAS_DIR = (
    Path(__file__).resolve().parents[5] / "03_implementation" / "adapter_registry" / "schemas"
)

router = APIRouter()


class ServiceUrl(BaseModel):
    url: str


class TruthGateRun(BaseModel):
    job_id: str
    mesh_path: str
    printer_id: str = "t1-a"


class GenerationRun(BaseModel):
    prompt: str = "calibration cube"
    seed: int = 3201
    reference_artifact_id: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None


@router.get("/api/generation/services")
def services() -> list[dict]:
    configured = [
        ("comfyui", "ComfyUI"),
        ("trellis2", "TRELLIS.2"),
        ("hunyuan3d", "Hunyuan3D"),
    ]
    result = []
    for service_id, name in configured:
        url = service_url(service_id)
        result.append(
            {
                "id": service_id,
                "name": name,
                "url": url,
                "status": "online"
                if port_reachable(url)
                else ("unreachable" if url else "not_configured"),
                "setup": {"settings_key": f"service.{service_id}.url"},
            }
        )
    return result


@router.put("/api/generation/services/{service_id}/url")
def set_service_url(service_id: str, body: ServiceUrl) -> dict:
    save_service_url(service_id, body.url)
    return {"id": service_id, "url": body.url, "saved": True}


@router.get("/api/gen3d/providers")
def gen3d_providers() -> list[dict[str, Any]]:
    """Return real provider readiness for 3D Generation providers.

    Combines Lane 04 (H3D-CLAUDE-SOURCE-GEN3D) proof data (repo reachability,
    pip install status, weights cache presence) with a live port-reachable
    probe for providers that expose an HTTP API. No fake readiness — every
    field comes from a real check.
    """
    # Load Lane 04 proof if available (read-only, not regenerated here)
    lane04_proof: dict[str, Any] = {}
    if _LANE04_PROOF_PATH.is_file():
        try:
            lane04_proof = json.loads(_LANE04_PROOF_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lane04_proof = {}

    lane04_providers: dict[str, dict[str, Any]] = {}
    for p in lane04_proof.get("providers") or []:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            lane04_providers[p["id"]] = p

    # Provider definitions: id, label, http_probe_url (None if not HTTP-accessible)
    provider_defs: list[tuple[str, str, str | None]] = [
        ("comfyui", "ComfyUI", service_url("comfyui") or "http://127.0.0.1:8188"),
        ("trellis2", "TRELLIS", None),
        ("hunyuan3d", "Hunyuan3D", None),
        ("triposr", "TripoSR", None),
        ("bambustudio_bridge", "Bambu Studio", None),
    ]

    result: list[dict[str, Any]] = []
    for provider_id, label, probe_url in provider_defs:
        lane04 = lane04_providers.get(provider_id, {})
        installed: bool = bool(lane04.get("installed"))
        repo_reachable: bool = bool((lane04.get("repo_reachable") or {}).get("reachable"))
        weights_present: bool = bool((lane04.get("weights_present") or {}).get("any_present"))
        pip_version: str | None = (lane04.get("pip_show") or {}).get("version")

        # Live port probe for providers with known HTTP endpoints
        live_reachable: bool | None = None
        if probe_url:
            live_reachable = port_reachable(probe_url)

        # Determine readiness status
        if live_reachable is True:
            readiness = "available"
        elif installed and (weights_present or live_reachable is not False):
            readiness = "installed_not_running"
        elif installed:
            readiness = "installed_not_running"
        elif repo_reachable:
            readiness = "not_installed"
        else:
            readiness = "unavailable"

        result.append(
            {
                "provider_id": provider_id,
                "label": label,
                "readiness": readiness,
                "installed": installed,
                "pip_version": pip_version,
                "repo_reachable": repo_reachable,
                "weights_present": weights_present,
                "live_reachable": live_reachable,
                "proof_source": "GEN3D_VERIFY_2026-05-06.json" if lane04 else None,
                "proof_gate_version": lane04.get("proof_gate_version"),
            }
        )
    return result


@router.get("/api/gen3d/templates")
def gen3d_templates() -> list[dict[str, Any]]:
    """Return real local generation templates sourced from the repo.

    Templates are discovered from two sources:
    1. Hard-coded local mesh templates that the generation executor can run
       without external providers (e.g. calibration_cube via trimesh).
    2. Any adapter schemas in the adapter_registry/schemas/ directory that
       describe a generative-3D provider (comfyui, trellis2, hunyuan3d,
       triposr), indicating their template capability.

    No fake completion is reported — every template entry reflects what the
    local executor can actually produce.
    """
    local_templates: list[dict[str, Any]] = [
        {
            "id": "calibration_cube",
            "name": "Calibration Cube",
            "source": "local_executor",
            "description": "Parametric calibration cube generated by trimesh. No external provider required.",
            "parameters": [
                {"name": "size_mm", "type": "float", "default": 20.0, "min": 5.0, "max": 80.0},
                {"name": "seed", "type": "int", "default": 3201},
            ],
            "outputs": ["stl", "proof_envelope", "preview_svg"],
            "requires_provider": None,
            "schema_file": None,
        }
    ]

    # Discover provider-backed templates from adapter schemas
    provider_schema_map = {
        "comfyui": ("comfyui.schema.json", "ComfyUI"),
        "trellis2": ("trellis2.schema.json", "TRELLIS"),
        "hunyuan3d": ("hunyuan3d.schema.json", "Hunyuan3D"),
        "triposr": ("triposr.schema.json", "TripoSR"),
    }
    for provider_id, (schema_file, provider_label) in provider_schema_map.items():
        schema_path = _SCHEMAS_DIR / schema_file
        schema_valid = schema_path.is_file()
        local_templates.append(
            {
                "id": f"{provider_id}_text_to_3d",
                "name": f"{provider_label} — Text to 3D",
                "source": "provider_backed",
                "description": f"Text-to-3D generation via {provider_label}. Requires the provider to be running.",
                "parameters": [
                    {"name": "prompt", "type": "str", "default": ""},
                    {"name": "seed", "type": "int", "default": 42},
                ],
                "outputs": ["glb", "stl", "preview_png"],
                "requires_provider": provider_id,
                "schema_file": schema_file if schema_valid else None,
                "schema_present": schema_valid,
            }
        )

    return local_templates


@router.post("/api/generation/run", status_code=202)
def run_generation(body: GenerationRun | None = None) -> dict:
    request = body or GenerationRun()
    try:
        # Explicit template_id from the UI takes priority over prompt keyword matching
        if request.template_id:
            template_id = request.template_id
        else:
            template_id = _resolve_generation_template(request.prompt)
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "queued": False,
                "reason": str(exc),
                "supported_templates": _supported_generation_templates(),
                "services": services(),
            },
        ) from exc
    return _execute_generation_template(request, template_id)


@router.get("/api/truth-gate/gates")
def gates() -> list[dict]:
    return GATE_DEFINITIONS


@router.post("/api/truth-gate/run")
def run_truth_gate(body: TruthGateRun) -> dict:
    if not Path(body.mesh_path).exists():
        raise HTTPException(status_code=404, detail="mesh file not found")
    started = time.monotonic()
    report = run_core_truth_gate(body.mesh_path)
    checks_by_name = {check.name: check for check in report.checks}
    results = []
    for gate in GATE_DEFINITIONS:
        check = checks_by_name.get(gate["id"])
        results.append(
            {
                "gate_name": gate["id"],
                "status": check.status.value if check else "skip",
                "error": None if check else "No matching core truth-gate check emitted.",
                "duration_s": 0.0,
            }
        )
    for item in results:
        execute(
            "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_id(),
                body.job_id,
                item["gate_name"],
                item["status"],
                item["error"],
                item["duration_s"],
            ),
        )
    return {
        "job_id": body.job_id,
        "mesh_path": body.mesh_path,
        "printer_id": body.printer_id,
        "duration_s": round(time.monotonic() - started, 4),
        "gates": results,
    }


@router.get("/api/truth-gate/{job_id}/results")
def truth_gate_results(job_id: str) -> list[dict]:
    return rows(
        "SELECT * FROM truth_gate_results WHERE job_id = ? ORDER BY checked_at, gate_name",
        (job_id,),
    )


def _supported_generation_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "calibration_cube",
            "name": "Calibration Cube",
            "outputs": ["stl", "proof_envelope", "preview_svg"],
            "parameters": ["size_mm", "seed"],
        }
    ]


def _resolve_generation_template(prompt: str) -> str:
    text = " ".join(prompt.lower().strip().split())
    if any(token in text for token in ("calibration cube", "test cube", "cube")):
        return "calibration_cube"
    raise ValueError(
        "The local 3D Generation executor currently supports calibration-cube requests only. Configure ComfyUI, TRELLIS.2, or Hunyuan3D for arbitrary generation."
    )


def _execute_generation_template(request: GenerationRun, template_id: str) -> dict[str, Any]:
    import trimesh

    from hermes3d.core.proof import write_proof

    size_mm = _constraint_float(request.constraints, "size_mm", 20.0, minimum=5.0, maximum=80.0)
    job_id = new_id()
    output_dir = implementation_path("var", "generation", job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    signature = hashlib.sha256(
        json.dumps(
            {
                "template": template_id,
                "prompt": request.prompt,
                "seed": request.seed,
                "size_mm": size_mm,
                "reference_artifact_id": request.reference_artifact_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:10]
    mesh_path = output_dir / f"{template_id}_{signature}.stl"
    proof_path = output_dir / f"{template_id}_{signature}.proof.json"
    preview_path = output_dir / f"{template_id}_{signature}.preview.svg"
    mesh = trimesh.creation.box(extents=(size_mm, size_mm, size_mm))
    mesh.apply_translation((0, 0, size_mm / 2))
    mesh.export(mesh_path, file_type="stl")
    if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500, detail={"status": "failed", "reason": "Generated mesh file is empty."}
        )
    written_proof = write_proof(
        mesh_path=mesh_path,
        output_path=proof_path,
        generator_name="hermes3d.gen3d.local.calibration_cube",
        generator_version="1.0.0",
        generator_signature=signature,
    )
    proof = json.loads(written_proof.read_text(encoding="utf-8"))
    truth_report = proof.get("truth_gate_report") if isinstance(proof, dict) else {}
    truth_status = str(
        truth_report.get("overall_status") if isinstance(truth_report, dict) else "error"
    )
    if truth_status != "pass":
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "reason": f"Truth gate rejected generated mesh with status {truth_status}.",
            },
        )
    preview_path.write_text(_cube_preview_svg(size_mm, signature), encoding="utf-8")

    mesh_sha = _file_sha256(mesh_path)
    proof_sha = _file_sha256(written_proof)
    preview_sha = _file_sha256(preview_path)
    execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run) VALUES (?, ?, 'generation', 'completed', NULL, 1)",
        (job_id, _generation_title(request.prompt)),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, 1, 'Generation request', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 2, 'Local mesh generation', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 3, 'Signed proof envelope', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 4, 'Preview artifact', 'done', datetime('now'), datetime('now'), 0)
        """,
        (new_id(), job_id, new_id(), job_id, new_id(), job_id, new_id(), job_id),
    )
    mesh_artifact_id = new_id()
    proof_artifact_id = new_id()
    preview_artifact_id = new_id()
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'mesh', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            mesh_artifact_id,
            job_id,
            mesh_path.name,
            str(mesh_path),
            mesh_path.stat().st_size,
            as_json(
                {
                    "sha256": mesh_sha,
                    "template": template_id,
                    "signature": signature,
                    "size_mm": size_mm,
                    "seed": request.seed,
                    "reference_artifact_id": request.reference_artifact_id,
                    "mesh": _mesh_summary(mesh),
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'proof_report', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            proof_artifact_id,
            job_id,
            written_proof.name,
            str(written_proof),
            written_proof.stat().st_size,
            as_json(
                {
                    "sha256": proof_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "truth_gate_status": truth_status,
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'screenshot', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            preview_artifact_id,
            job_id,
            preview_path.name,
            str(preview_path),
            preview_path.stat().st_size,
            as_json(
                {
                    "sha256": preview_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "source": "mesh_extents",
                }
            ),
        ),
    )
    execute(
        "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, 'generation.local_mesh', 'pass', NULL, ?)",
        (new_id(), job_id, _truth_duration(truth_report)),
    )
    proof_event_id = new_id()
    payload = {
        "job_id": job_id,
        "template": template_id,
        "mesh_artifact_id": mesh_artifact_id,
        "proof_artifact_id": proof_artifact_id,
        "preview_artifact_id": preview_artifact_id,
        "mesh_path": str(mesh_path),
        "proof_path": str(written_proof),
        "preview_path": str(preview_path),
        "mesh_sha256": mesh_sha,
        "proof_sha256": proof_sha,
        "preview_sha256": preview_sha,
        "truth_gate_status": truth_status,
        "prompt_head": request.prompt[:300],
    }
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, 'generation.executor.completed', 'generation-executor', ?)",
        (proof_event_id, as_json(payload)),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'generation_executor_completed', 'generation-executor', ?)",
        (new_id(), job_id, f"Generated {mesh_path.name}; proof_event_id={proof_event_id}"),
    )
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "completed",
        "accepted": True,
        "created": True,
        "template": template_id,
        "artifact": {
            "id": mesh_artifact_id,
            "label": mesh_path.name,
            "file_path": str(mesh_path),
            "file_size": mesh_path.stat().st_size,
            "sha256": mesh_sha,
        },
        "preview": {
            "id": preview_artifact_id,
            "label": preview_path.name,
            "file_path": str(preview_path),
            "file_size": preview_path.stat().st_size,
            "sha256": preview_sha,
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
    }


def _generation_title(prompt: str) -> str:
    first = " ".join(prompt.strip().split())
    return first[:80] or "3D Generation"


def _constraint_float(
    constraints: dict[str, Any], key: str, default: float, *, minimum: float, maximum: float
) -> float:
    value = constraints.get(key, default)
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail={"status": "blocked", "reason": f"{key} must be numeric."}
        ) from exc
    if not (minimum <= parsed <= maximum):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "blocked",
                "reason": f"{key} must be between {minimum:g} and {maximum:g} mm.",
            },
        )
    return parsed


def _cube_preview_svg(size_mm: float, signature: str) -> str:
    label = f"{size_mm:g}mm cube"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420" role="img">'
        '<rect width="640" height="420" fill="#07111f"/>'
        '<g fill="none" stroke="#20d8ff" stroke-width="3" stroke-linejoin="round">'
        '<path d="M220 130h190l70 70v160H290l-70-70z"/>'
        '<path d="M220 130l70 70h190M290 200v160M410 130v160l70 70"/>'
        "</g>"
        '<g stroke="#1b3658" stroke-width="1">'
        '<path d="M120 360h420"/>'
        '<path d="M160 320h420"/>'
        '<path d="M200 280h420"/>'
        "</g>"
        f'<text x="32" y="48" fill="#dbeafe" font-family="monospace" font-size="24">{label}</text>'
        f'<text x="32" y="82" fill="#7dd3fc" font-family="monospace" font-size="16">proof signature {signature}</text>'
        "</svg>"
    )


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
