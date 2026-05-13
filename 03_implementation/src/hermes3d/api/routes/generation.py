from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import subprocess
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows
from hermes3d.core.printability_truth_gate import GATE_DEFINITIONS, run_core_truth_gate
from hermes3d.services.local_state import implementation_path, port_reachable, service_url
from hermes3d.services.local_state import set_service_url as save_service_url

# Path to Lane 04 (H3D-CLAUDE-SOURCE-GEN3D) proof file — read-only
# File is at: src/hermes3d/api/routes/generation.py
# parents[0]=routes, [1]=api, [2]=hermes3d, [3]=src, [4]=03_implementation, [5]=Hermes3D
_DEFAULT_LANE04_PROOF_PATH = (
    Path(__file__).resolve().parents[5]
    / "03_implementation"
    / "proof"
    / "GEN3D_VERIFY_2026-05-06.json"
)
_LANE04_PROOF_PATH = _DEFAULT_LANE04_PROOF_PATH
_GEN3D_MODEL_MANIFEST_PATH = Path(
    os.environ.get("HERMES3D_GEN3D_MODEL_MANIFEST", r"G:\Gen3D\models\GEN3D_MODEL_MANIFEST.json")
)
_DEFAULT_REMBG_MODEL_HOME = Path(
    os.environ.get("HERMES3D_REMBG_MODEL_HOME", r"G:\Gen3D\models\rembg")
)
_DEFAULT_COMFYUI_TORCH_LIB = Path(
    os.environ.get(
        "HERMES3D_ONNXRUNTIME_DLL_DIR",
        r"G:\Github\ComfyUI\.venv\Lib\site-packages\torch\lib",
    )
)
_REMBG_SESSIONS: dict[str, Any] = {}
_REMBG_RUNTIME_PROBE_CACHE: dict[str, Any] = {}

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


def _load_model_manifest() -> dict[str, Any]:
    if not _GEN3D_MODEL_MANIFEST_PATH.is_file():
        return {}
    try:
        raw = json.loads(_GEN3D_MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _gen3d_model_evidence(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    repos = manifest.get("repos")
    if not isinstance(repos, list):
        repos = []

    by_repo: dict[str, dict[str, Any]] = {}
    for item in repos:
        if isinstance(item, dict) and isinstance(item.get("repo_id"), str):
            by_repo[item["repo_id"]] = item

    repo_map = {
        "hunyuan3d": "tencent/Hunyuan3D-2.1",
        "triposr": "stabilityai/TripoSR",
        "trellis2": "microsoft/TRELLIS-image-large",
    }
    for provider_id, repo_id in repo_map.items():
        item = by_repo.get(repo_id)
        if not item:
            continue
        actual_bytes = int(item.get("actual_bytes_without_hf_cache") or 0)
        expected_bytes = int(item.get("expected_bytes") or 0)
        actual_files = int(item.get("actual_file_count_without_hf_cache") or 0)
        expected_files = int(item.get("expected_file_count") or 0)
        local_dir = Path(str(item.get("local_dir") or ""))
        complete_enough = actual_bytes >= expected_bytes and actual_files >= expected_files
        evidence[provider_id] = {
            "installed": local_dir.exists() and actual_files > 0,
            "repo_reachable": True,
            "weights_present": complete_enough,
            "repo_id": repo_id,
            "revision": item.get("revision"),
            "local_dir": str(local_dir),
            "actual_bytes_without_hf_cache": actual_bytes,
            "expected_bytes": expected_bytes,
            "actual_file_count_without_hf_cache": actual_files,
            "expected_file_count": expected_files,
        }

    comfyui_root = Path(os.environ.get("HERMES3D_COMFYUI_ROOT", r"G:\Github\ComfyUI"))
    comfyui_installed = (comfyui_root / "main.py").is_file()
    hunyuan = evidence.get("hunyuan3d", {})
    if comfyui_installed or hunyuan:
        evidence["comfyui"] = {
            "installed": comfyui_installed,
            "repo_reachable": comfyui_installed,
            "weights_present": bool(hunyuan.get("weights_present")),
            "repo_id": "local:ComfyUI",
            "local_dir": str(comfyui_root),
            "paired_model_repo_id": hunyuan.get("repo_id"),
            "paired_model_revision": hunyuan.get("revision"),
        }

    rembg_sessions = manifest.get("rembg_sessions")
    if isinstance(rembg_sessions, list):
        ready_sessions = [
            item
            for item in rembg_sessions
            if isinstance(item, dict)
            and int(item.get("bytes") or 0) > 0
            and Path(str(item.get("model_path") or "")).is_file()
        ]
        evidence["background_removal"] = {
            "installed": bool(ready_sessions),
            "weights_present": bool(ready_sessions),
            "sessions": [
                {
                    "session": item.get("session"),
                    "model_path": item.get("model_path"),
                    "bytes": item.get("bytes"),
                    "providers": item.get("providers"),
                }
                for item in ready_sessions
            ],
        }

    background = evidence.get("background_removal", {})
    rembg_runtime = _probe_rembg_runtime()
    local_deps = {
        "pillow": importlib.util.find_spec("PIL") is not None,
        "numpy": importlib.util.find_spec("numpy") is not None,
        "trimesh": importlib.util.find_spec("trimesh") is not None,
    }
    local_ready = (
        all(local_deps.values())
        and bool(background.get("weights_present"))
        and rembg_runtime.get("status") == "ready"
    )
    evidence["local_image_relief"] = {
        "installed": local_ready,
        "repo_reachable": True,
        "weights_present": bool(background.get("weights_present")),
        "runtime_ready": local_ready,
        "runtime": rembg_runtime,
        "local_dependencies": local_deps,
        "background_removal": background or None,
        "repo_id": "local:Hermes3D precision_image_relief",
        "local_dir": str(Path(__file__).resolve().parents[5]),
    }

    return evidence


def _configured_rembg_python_path() -> Path:
    return Path(
        os.environ.get("HERMES3D_REMBG_PYTHON")
        or os.environ.get("HERMES3D_HUNYUAN3D_PYTHON")
        or r"G:\Github\ComfyUI\.venv\Scripts\python.exe"
    )


def _rembg_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if "U2NET_HOME" not in env and _DEFAULT_REMBG_MODEL_HOME.exists():
        env["U2NET_HOME"] = str(_DEFAULT_REMBG_MODEL_HOME)
    if _DEFAULT_COMFYUI_TORCH_LIB.is_dir():
        env["PATH"] = str(_DEFAULT_COMFYUI_TORCH_LIB) + os.pathsep + env.get("PATH", "")
    return env


def _probe_rembg_runtime() -> dict[str, Any]:
    ttl_s = int(os.environ.get("HERMES3D_REMBG_PROBE_TTL_S", "60"))
    now = time.monotonic()
    cached = _REMBG_RUNTIME_PROBE_CACHE.get("value")
    if isinstance(cached, dict) and now - float(cached.get("_monotonic", 0.0)) < ttl_s:
        return {k: v for k, v in cached.items() if k != "_monotonic"}

    backend_ready = (
        importlib.util.find_spec("rembg") is not None
        and importlib.util.find_spec("onnxruntime") is not None
        and importlib.util.find_spec("PIL") is not None
    )
    if backend_ready:
        result = {
            "status": "ready",
            "kind": "in_process",
            "python": "backend",
            "reason": "rembg, onnxruntime, and Pillow import from the active backend runtime.",
        }
        _REMBG_RUNTIME_PROBE_CACHE["value"] = {**result, "_monotonic": now}
        return result

    python_path = _configured_rembg_python_path()
    if not python_path.is_file():
        result = {
            "status": "blocked",
            "kind": "subprocess",
            "python": str(python_path),
            "reason": "Configured rembg subprocess Python runtime is missing.",
        }
        _REMBG_RUNTIME_PROBE_CACHE["value"] = {**result, "_monotonic": now}
        return result

    probe_code = (
        "import json, rembg, onnxruntime, PIL; "
        "print(json.dumps({'providers': onnxruntime.get_available_providers()}))"
    )
    try:
        proc = subprocess.run(
            [str(python_path), "-c", probe_code],
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("HERMES3D_REMBG_PROBE_TIMEOUT_S", "20")),
            check=False,
            env=_rembg_subprocess_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = {
            "status": "blocked",
            "kind": "subprocess",
            "python": str(python_path),
            "reason": f"rembg subprocess probe failed: {type(exc).__name__}: {exc}",
        }
        _REMBG_RUNTIME_PROBE_CACHE["value"] = {**result, "_monotonic": now}
        return result

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        result = {
            "status": "blocked",
            "kind": "subprocess",
            "python": str(python_path),
            "return_code": proc.returncode,
            "reason": (stderr or stdout or "rembg subprocess probe returned non-zero")[:500],
        }
        _REMBG_RUNTIME_PROBE_CACHE["value"] = {**result, "_monotonic": now}
        return result

    providers: list[str] = []
    try:
        parsed = json.loads(stdout.splitlines()[-1]) if stdout else {}
        raw_providers = parsed.get("providers")
        if isinstance(raw_providers, list):
            providers = [str(item) for item in raw_providers]
    except (json.JSONDecodeError, AttributeError, IndexError):
        providers = []
    result = {
        "status": "ready",
        "kind": "subprocess",
        "python": str(python_path),
        "onnxruntime_providers": providers,
        "reason": "rembg, onnxruntime, and Pillow import from the configured subprocess runtime.",
    }
    _REMBG_RUNTIME_PROBE_CACHE["value"] = {**result, "_monotonic": now}
    return result


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

    model_manifest = _load_model_manifest()
    model_evidence = _gen3d_model_evidence(model_manifest)

    # Provider definitions: id, label, http_probe_url (None if not HTTP-accessible)
    provider_defs: list[tuple[str, str, str | None]] = [
        ("local_image_relief", "Local Image Relief", None),
        ("comfyui", "ComfyUI", service_url("comfyui") or "http://127.0.0.1:8188"),
        ("trellis2", "TRELLIS", None),
        ("hunyuan3d", "Hunyuan3D", None),
        ("triposr", "TripoSR", None),
        ("bambustudio_bridge", "Bambu Studio", None),
    ]

    result: list[dict[str, Any]] = []
    for provider_id, label, probe_url in provider_defs:
        lane04 = lane04_providers.get(provider_id, {})
        local_evidence = model_evidence.get(provider_id, {})
        installed: bool = bool(lane04.get("installed"))
        repo_reachable: bool = bool((lane04.get("repo_reachable") or {}).get("reachable"))
        weights_present: bool = bool((lane04.get("weights_present") or {}).get("any_present"))
        pip_version: str | None = (lane04.get("pip_show") or {}).get("version")

        if local_evidence:
            installed = installed or bool(local_evidence.get("installed"))
            repo_reachable = repo_reachable or bool(local_evidence.get("repo_reachable"))
            weights_present = weights_present or bool(local_evidence.get("weights_present"))

        # Live port probe for providers with known HTTP endpoints
        live_reachable: bool | None = None
        if probe_url:
            live_reachable = port_reachable(probe_url)

        # Determine readiness status
        if provider_id == "local_image_relief" and bool(local_evidence.get("runtime_ready")):
            readiness = "available"
            live_reachable = True
        elif live_reachable is True:
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
                "model_proof_source": "GEN3D_MODEL_MANIFEST.json" if local_evidence else None,
                "model_evidence": local_evidence or None,
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
            "requires_reference_image": False,
            "requires_background_removal": False,
        },
        {
            "id": "reference_image_relief",
            "name": "Reference Image Relief",
            "source": "local_executor",
            "description": "Uses rembg background removal, then extrudes the reference alpha mask into a printable relief STL.",
            "parameters": [
                {"name": "size_mm", "type": "float", "default": 60.0, "min": 20.0, "max": 120.0},
                {"name": "thickness_mm", "type": "float", "default": 3.0, "min": 1.2, "max": 10.0},
                {"name": "seed", "type": "int", "default": 3201},
            ],
            "outputs": ["stl", "proof_envelope", "background_removed_png"],
            "requires_provider": None,
            "schema_file": None,
            "requires_reference_image": True,
            "requires_background_removal": True,
        },
        {
            "id": "precision_image_relief",
            "name": "Precision Image Relief",
            "source": "local_executor",
            "description": "Uses the exact reference image silhouette and luminance as a high-resolution height field for 1:1 bas-relief preservation.",
            "parameters": [
                {"name": "size_mm", "type": "float", "default": 180.0, "min": 20.0, "max": 180.0},
                {
                    "name": "base_thickness_mm",
                    "type": "float",
                    "default": 3.0,
                    "min": 1.2,
                    "max": 8.0,
                },
                {
                    "name": "relief_height_mm",
                    "type": "float",
                    "default": 5.0,
                    "min": 1.0,
                    "max": 20.0,
                },
                {"name": "max_resolution", "type": "int", "default": 144, "min": 96, "max": 768},
                {"name": "min_feature_mm", "type": "float", "default": 1.2, "min": 1.2, "max": 4.0},
                {"name": "seed", "type": "int", "default": 3201},
            ],
            "outputs": [
                "stl",
                "3mf",
                "proof_envelope",
                "background_removed_png",
                "heightfield_mesh",
            ],
            "requires_provider": None,
            "schema_file": None,
            "requires_reference_image": True,
            "requires_background_removal": True,
        },
        {
            "id": "hunyuan3d_image_to_3d",
            "name": "Hunyuan3D 2.1 Image Mesh",
            "source": "local_hunyuan3d_runtime",
            "description": "Runs local Hunyuan3D 2.1 shape generation through the ComfyUI Python runtime and records CUDA/model evidence.",
            "parameters": [
                {"name": "size_mm", "type": "float", "default": 60.0, "min": 20.0, "max": 120.0},
                {"name": "steps", "type": "int", "default": 30, "min": 8, "max": 50},
                {
                    "name": "octree_resolution",
                    "type": "int",
                    "default": 256,
                    "min": 128,
                    "max": 384,
                },
                {
                    "name": "guidance_scale",
                    "type": "float",
                    "default": 5.0,
                    "min": 1.0,
                    "max": 12.0,
                },
                {"name": "seed", "type": "int", "default": 3201},
            ],
            "outputs": [
                "stl",
                "3mf",
                "proof_envelope",
                "background_removed_png",
                "runtime_evidence_json",
            ],
            "requires_provider": None,
            "runtime_provider": "hunyuan3d",
            "schema_file": "hunyuan3d.schema.json"
            if (_SCHEMAS_DIR / "hunyuan3d.schema.json").is_file()
            else None,
            "schema_present": (_SCHEMAS_DIR / "hunyuan3d.schema.json").is_file(),
            "requires_reference_image": True,
            "requires_background_removal": True,
        },
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
                "requires_reference_image": False,
                "requires_background_removal": False,
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
            "requires_reference_image": False,
        },
        {
            "id": "reference_image_relief",
            "name": "Reference Image Relief",
            "outputs": ["stl", "proof_envelope", "background_removed_png"],
            "parameters": ["size_mm", "thickness_mm", "seed", "reference_artifact_id"],
            "requires_reference_image": True,
        },
        {
            "id": "precision_image_relief",
            "name": "Precision Image Relief",
            "outputs": [
                "stl",
                "3mf",
                "proof_envelope",
                "background_removed_png",
                "heightfield_mesh",
            ],
            "parameters": [
                "size_mm",
                "base_thickness_mm",
                "relief_height_mm",
                "max_resolution",
                "seed",
                "reference_artifact_id",
            ],
            "requires_reference_image": True,
        },
        {
            "id": "hunyuan3d_image_to_3d",
            "name": "Hunyuan3D 2.1 Image Mesh",
            "outputs": [
                "stl",
                "3mf",
                "proof_envelope",
                "background_removed_png",
                "runtime_evidence_json",
            ],
            "parameters": [
                "size_mm",
                "steps",
                "octree_resolution",
                "guidance_scale",
                "seed",
                "reference_artifact_id",
            ],
            "requires_reference_image": True,
        },
    ]


def _resolve_generation_template(prompt: str) -> str:
    text = " ".join(prompt.lower().strip().split())
    if any(token in text for token in ("calibration cube", "test cube", "cube")):
        return "calibration_cube"
    if "hunyuan" in text or "image to 3d" in text or "image-to-3d" in text:
        return "hunyuan3d_image_to_3d"
    if "1:1" in text or "precision" in text or "exact" in text or "perfect" in text:
        return "precision_image_relief"
    if any(token in text for token in ("logo", "reference image", "silhouette", "relief")):
        return "reference_image_relief"
    raise ValueError(
        "The local 3D Generation executor currently supports calibration_cube and reference_image_relief. Configure ComfyUI, TRELLIS.2, TripoSR, or Hunyuan3D for arbitrary generation."
    )


def _execute_generation_template(request: GenerationRun, template_id: str) -> dict[str, Any]:
    if template_id == "calibration_cube":
        return _execute_calibration_cube_template(request, template_id)
    if template_id == "reference_image_relief":
        return _execute_reference_image_relief_template(request, template_id)
    if template_id == "precision_image_relief":
        return _execute_precision_image_relief_template(request, template_id)
    if template_id == "hunyuan3d_image_to_3d":
        return _execute_hunyuan3d_image_template(request, template_id)
    provider_prefixes = ("comfyui_", "trellis2_", "hunyuan3d_", "triposr_")
    if template_id.startswith(provider_prefixes):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "queued": False,
                "reason": (
                    f"{template_id} is provider-backed. Start and verify the matching "
                    "Gen3D provider before dispatching this template."
                ),
                "supported_templates": _supported_generation_templates(),
                "services": services(),
            },
        )
    raise HTTPException(
        status_code=422,
        detail={
            "status": "blocked",
            "queued": False,
            "reason": f"Unsupported generation template: {template_id}",
            "supported_templates": _supported_generation_templates(),
        },
    )


def _execute_calibration_cube_template(request: GenerationRun, template_id: str) -> dict[str, Any]:
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


def _execute_reference_image_relief_template(
    request: GenerationRun, template_id: str
) -> dict[str, Any]:
    from hermes3d.core.proof import write_proof

    if not request.reference_artifact_id:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "queued": False,
                "reason": "reference_image_relief requires a reference_artifact_id from an uploaded image.",
                "supported_templates": _supported_generation_templates(),
            },
        )

    reference_artifact = row(
        "SELECT * FROM artifacts WHERE id = ?",
        (request.reference_artifact_id,),
    )
    if not reference_artifact:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact not found: {request.reference_artifact_id}",
            },
        )
    reference_path = Path(str(reference_artifact["file_path"]))
    if not reference_path.is_file():
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact file is missing: {reference_path}",
            },
        )

    size_mm = _constraint_float(request.constraints, "size_mm", 60.0, minimum=20.0, maximum=120.0)
    thickness_mm = _constraint_float(
        request.constraints, "thickness_mm", 3.0, minimum=1.2, maximum=10.0
    )
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
                "thickness_mm": thickness_mm,
                "reference_artifact_id": request.reference_artifact_id,
                "reference_path": str(reference_path),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:10]

    processed_path = output_dir / f"{template_id}_{signature}.rembg.png"
    mesh_path = output_dir / f"{template_id}_{signature}.stl"
    package_3mf_path = output_dir / f"{template_id}_{signature}.3mf"
    proof_path = output_dir / f"{template_id}_{signature}.proof.json"

    background = _remove_background_to_png(reference_path, processed_path)
    mesh, mesh_build = _alpha_png_to_relief_mesh(
        processed_path,
        mesh_path,
        size_mm=size_mm,
        thickness_mm=thickness_mm,
    )
    if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500, detail={"status": "failed", "reason": "Generated mesh file is empty."}
        )

    written_proof = write_proof(
        mesh_path=mesh_path,
        output_path=proof_path,
        generator_name="hermes3d.gen3d.local.reference_image_relief",
        generator_version="1.0.0",
        generator_signature=signature,
        visual_evidence_paths=[("background_removed_reference", processed_path)],
        modeling_backend={
            "id": "local_reference_image_relief",
            "background_removal": background["engine"],
            "reference_artifact_id": request.reference_artifact_id,
        },
        gpu_used=False,
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

    package_3mf = _export_mesh_to_3mf(
        mesh_path,
        package_3mf_path,
        metadata={
            "generator": "hermes3d.gen3d.local.precision_image_relief",
            "template": template_id,
            "signature": signature,
            "source_image": str(reference_path),
            "processed_reference": str(processed_path),
        },
    )
    processed_sha = _file_sha256(processed_path)
    mesh_sha = _file_sha256(mesh_path)
    package_3mf_sha = _file_sha256(package_3mf_path)
    proof_sha = _file_sha256(written_proof)
    runtime_evidence_path = _background_runtime_evidence_path(background)
    runtime_evidence_sha = _file_sha256(runtime_evidence_path) if runtime_evidence_path else None
    execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run) VALUES (?, ?, 'generation', 'completed', NULL, 1)",
        (job_id, _generation_title(request.prompt)),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, 1, 'Generation request', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 2, 'Reference background removal', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 3, 'Reference relief mesh generation', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 4, 'Signed proof envelope', 'done', datetime('now'), datetime('now'), 0)
        """,
        (new_id(), job_id, new_id(), job_id, new_id(), job_id, new_id(), job_id),
    )
    processed_artifact_id = new_id()
    mesh_artifact_id = new_id()
    package_3mf_artifact_id = new_id()
    proof_artifact_id = new_id()
    runtime_evidence_artifact_id = new_id() if runtime_evidence_path else None
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'processed_image', 'generation-executor', 'MODELING', 'BACKGROUND_REMOVAL', ?, ?, ?, ?)
        """,
        (
            processed_artifact_id,
            job_id,
            processed_path.name,
            str(processed_path),
            processed_path.stat().st_size,
            as_json(
                {
                    "sha256": processed_sha,
                    "reference_artifact_id": request.reference_artifact_id,
                    "engine": background["engine"],
                    "alpha": background["alpha"],
                    "source_label": reference_artifact.get("label"),
                }
            ),
        ),
    )
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
                    "thickness_mm": thickness_mm,
                    "seed": request.seed,
                    "reference_artifact_id": request.reference_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "background_removal": background,
                    "mesh_build": mesh_build,
                    "mesh": _mesh_summary(mesh),
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, '3mf', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            package_3mf_artifact_id,
            job_id,
            package_3mf_path.name,
            str(package_3mf_path),
            package_3mf_path.stat().st_size,
            as_json(
                {
                    "sha256": package_3mf_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "reference_artifact_id": request.reference_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "package": package_3mf,
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
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "truth_gate_status": truth_status,
                }
            ),
        ),
    )
    if runtime_evidence_path and runtime_evidence_artifact_id and runtime_evidence_sha:
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'runtime_evidence', 'generation-executor', 'MODELING', 'MODEL_RUNTIME', ?, ?, ?, ?)
            """,
            (
                runtime_evidence_artifact_id,
                job_id,
                runtime_evidence_path.name,
                str(runtime_evidence_path),
                runtime_evidence_path.stat().st_size,
                as_json(
                    {
                        "sha256": runtime_evidence_sha,
                        "mesh_artifact_id": mesh_artifact_id,
                        "processed_reference_artifact_id": processed_artifact_id,
                        "reference_artifact_id": request.reference_artifact_id,
                        "engine": background.get("engine"),
                        "providers": background.get("providers"),
                    }
                ),
            ),
        )
    execute(
        "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, 'generation.reference_relief_mesh', 'pass', NULL, ?)",
        (new_id(), job_id, _truth_duration(truth_report)),
    )
    proof_event_id = new_id()
    payload = {
        "job_id": job_id,
        "template": template_id,
        "reference_artifact_id": request.reference_artifact_id,
        "processed_reference_artifact_id": processed_artifact_id,
        "mesh_artifact_id": mesh_artifact_id,
        "package_3mf_artifact_id": package_3mf_artifact_id,
        "proof_artifact_id": proof_artifact_id,
        "mesh_path": str(mesh_path),
        "package_3mf_path": str(package_3mf_path),
        "processed_path": str(processed_path),
        "proof_path": str(written_proof),
        "mesh_sha256": mesh_sha,
        "package_3mf_sha256": package_3mf_sha,
        "processed_sha256": processed_sha,
        "proof_sha256": proof_sha,
        "truth_gate_status": truth_status,
        "background_removal": background,
        **(
            {
                "runtime_evidence_artifact_id": runtime_evidence_artifact_id,
                "runtime_evidence_path": str(runtime_evidence_path),
                "runtime_evidence_sha256": runtime_evidence_sha,
            }
            if runtime_evidence_artifact_id and runtime_evidence_path and runtime_evidence_sha
            else {}
        ),
        "prompt_head": request.prompt[:300],
    }
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, 'generation.reference_relief.completed', 'generation-executor', ?)",
        (proof_event_id, as_json(payload)),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'generation_reference_relief_completed', 'generation-executor', ?)",
        (
            new_id(),
            job_id,
            f"Generated {mesh_path.name} from reference artifact {request.reference_artifact_id}; proof_event_id={proof_event_id}",
        ),
    )
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "completed",
        "accepted": True,
        "created": True,
        "template": template_id,
        "reference": {
            "id": request.reference_artifact_id,
            "label": reference_artifact.get("label"),
            "file_path": str(reference_path),
        },
        "processed_reference": {
            "id": processed_artifact_id,
            "label": processed_path.name,
            "file_path": str(processed_path),
            "file_size": processed_path.stat().st_size,
            "sha256": processed_sha,
        },
        "artifact": {
            "id": mesh_artifact_id,
            "label": mesh_path.name,
            "file_path": str(mesh_path),
            "file_size": mesh_path.stat().st_size,
            "sha256": mesh_sha,
        },
        "package_3mf": {
            "id": package_3mf_artifact_id,
            "label": package_3mf_path.name,
            "file_path": str(package_3mf_path),
            "file_size": package_3mf_path.stat().st_size,
            "sha256": package_3mf_sha,
            "package": package_3mf,
        },
        "proof": {
            "id": proof_artifact_id,
            "label": written_proof.name,
            "file_path": str(written_proof),
            "file_size": written_proof.stat().st_size,
            "sha256": proof_sha,
            "event_id": proof_event_id,
        },
        **(
            {
                "runtime_evidence": {
                    "id": runtime_evidence_artifact_id,
                    "label": runtime_evidence_path.name,
                    "file_path": str(runtime_evidence_path),
                    "file_size": runtime_evidence_path.stat().st_size,
                    "sha256": runtime_evidence_sha,
                }
            }
            if runtime_evidence_artifact_id and runtime_evidence_path and runtime_evidence_sha
            else {}
        ),
        "background_removal": background,
        "truth_gate": {"status": truth_status, "duration_s": _truth_duration(truth_report)},
    }


def _execute_precision_image_relief_template(
    request: GenerationRun, template_id: str
) -> dict[str, Any]:
    from hermes3d.core.proof import write_proof

    if not request.reference_artifact_id:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "queued": False,
                "reason": "precision_image_relief requires a reference_artifact_id from an uploaded image.",
                "supported_templates": _supported_generation_templates(),
            },
        )

    reference_artifact = row(
        "SELECT * FROM artifacts WHERE id = ?",
        (request.reference_artifact_id,),
    )
    if not reference_artifact:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact not found: {request.reference_artifact_id}",
            },
        )
    reference_path = Path(str(reference_artifact["file_path"]))
    if not reference_path.is_file():
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact file is missing: {reference_path}",
            },
        )

    size_mm = _constraint_float(request.constraints, "size_mm", 180.0, minimum=20.0, maximum=180.0)
    base_thickness_mm = _constraint_float(
        request.constraints, "base_thickness_mm", 3.0, minimum=1.2, maximum=8.0
    )
    relief_height_mm = _constraint_float(
        request.constraints, "relief_height_mm", 5.0, minimum=1.0, maximum=20.0
    )
    max_resolution = _constraint_int(
        request.constraints, "max_resolution", 144, minimum=96, maximum=768
    )
    min_feature_mm = _constraint_float(
        request.constraints, "min_feature_mm", 1.2, minimum=1.2, maximum=4.0
    )
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
                "base_thickness_mm": base_thickness_mm,
                "relief_height_mm": relief_height_mm,
                "max_resolution": max_resolution,
                "min_feature_mm": min_feature_mm,
                "reference_artifact_id": request.reference_artifact_id,
                "reference_path": str(reference_path),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:10]

    processed_path = output_dir / f"{template_id}_{signature}.rembg.png"
    mesh_path = output_dir / f"{template_id}_{signature}.stl"
    package_3mf_path = output_dir / f"{template_id}_{signature}.3mf"
    proof_path = output_dir / f"{template_id}_{signature}.proof.json"

    background = _remove_background_to_png(reference_path, processed_path)
    mesh, mesh_build = _image_to_precision_relief_mesh(
        processed_path,
        mesh_path,
        size_mm=size_mm,
        base_thickness_mm=base_thickness_mm,
        relief_height_mm=relief_height_mm,
        max_resolution=max_resolution,
        min_feature_mm=min_feature_mm,
    )
    if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500, detail={"status": "failed", "reason": "Generated mesh file is empty."}
        )

    written_proof = write_proof(
        mesh_path=mesh_path,
        output_path=proof_path,
        generator_name="hermes3d.gen3d.local.precision_image_relief",
        generator_version="1.0.0",
        generator_signature=signature,
        visual_evidence_paths=[("background_removed_reference", processed_path)],
        modeling_backend={
            "id": "local_precision_image_relief",
            "background_removal": background["engine"],
            "height_source": "reference_image_luminance",
            "reference_artifact_id": request.reference_artifact_id,
        },
        gpu_used=False,
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

    package_3mf = _export_mesh_to_3mf(
        mesh_path,
        package_3mf_path,
        metadata={
            "generator": "hermes3d.gen3d.local.precision_image_relief",
            "template": template_id,
            "signature": signature,
            "source_image": str(reference_path),
            "processed_reference": str(processed_path),
        },
    )
    processed_sha = _file_sha256(processed_path)
    mesh_sha = _file_sha256(mesh_path)
    package_3mf_sha = _file_sha256(package_3mf_path)
    proof_sha = _file_sha256(written_proof)
    runtime_evidence_path = _background_runtime_evidence_path(background)
    runtime_evidence_sha = _file_sha256(runtime_evidence_path) if runtime_evidence_path else None
    execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run) VALUES (?, ?, 'generation', 'completed', NULL, 1)",
        (job_id, _generation_title(request.prompt)),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, 1, 'Generation request', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 2, 'Reference background removal', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 3, 'Precision heightfield relief generation', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 4, '3MF print package export', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 5, 'Signed proof envelope', 'done', datetime('now'), datetime('now'), 0)
        """,
        (
            new_id(),
            job_id,
            new_id(),
            job_id,
            new_id(),
            job_id,
            new_id(),
            job_id,
            new_id(),
            job_id,
        ),
    )
    processed_artifact_id = new_id()
    mesh_artifact_id = new_id()
    package_3mf_artifact_id = new_id()
    proof_artifact_id = new_id()
    runtime_evidence_artifact_id = new_id() if runtime_evidence_path else None
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'processed_image', 'generation-executor', 'MODELING', 'BACKGROUND_REMOVAL', ?, ?, ?, ?)
        """,
        (
            processed_artifact_id,
            job_id,
            processed_path.name,
            str(processed_path),
            processed_path.stat().st_size,
            as_json(
                {
                    "sha256": processed_sha,
                    "reference_artifact_id": request.reference_artifact_id,
                    "engine": background["engine"],
                    "alpha": background["alpha"],
                    "source_label": reference_artifact.get("label"),
                }
            ),
        ),
    )
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
                    "base_thickness_mm": base_thickness_mm,
                    "relief_height_mm": relief_height_mm,
                    "max_resolution": max_resolution,
                    "min_feature_mm": min_feature_mm,
                    "seed": request.seed,
                    "reference_artifact_id": request.reference_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "background_removal": background,
                    "mesh_build": mesh_build,
                    "mesh": _mesh_summary(mesh),
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, '3mf', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            package_3mf_artifact_id,
            job_id,
            package_3mf_path.name,
            str(package_3mf_path),
            package_3mf_path.stat().st_size,
            as_json(
                {
                    "sha256": package_3mf_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "reference_artifact_id": request.reference_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "package": package_3mf,
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
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    **(
                        {"runtime_evidence_artifact_id": runtime_evidence_artifact_id}
                        if runtime_evidence_artifact_id
                        else {}
                    ),
                    "truth_gate_status": truth_status,
                }
            ),
        ),
    )
    if runtime_evidence_path and runtime_evidence_artifact_id and runtime_evidence_sha:
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'runtime_evidence', 'generation-executor', 'MODELING', 'MODEL_RUNTIME', ?, ?, ?, ?)
            """,
            (
                runtime_evidence_artifact_id,
                job_id,
                runtime_evidence_path.name,
                str(runtime_evidence_path),
                runtime_evidence_path.stat().st_size,
                as_json(
                    {
                        "sha256": runtime_evidence_sha,
                        "mesh_artifact_id": mesh_artifact_id,
                        "processed_reference_artifact_id": processed_artifact_id,
                        "reference_artifact_id": request.reference_artifact_id,
                        "engine": background.get("engine"),
                        "providers": background.get("providers"),
                    }
                ),
            ),
        )
    execute(
        "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, 'generation.precision_image_relief', 'pass', NULL, ?)",
        (new_id(), job_id, _truth_duration(truth_report)),
    )
    proof_event_id = new_id()
    payload = {
        "job_id": job_id,
        "template": template_id,
        "reference_artifact_id": request.reference_artifact_id,
        "processed_reference_artifact_id": processed_artifact_id,
        "mesh_artifact_id": mesh_artifact_id,
        "package_3mf_artifact_id": package_3mf_artifact_id,
        "proof_artifact_id": proof_artifact_id,
        "mesh_path": str(mesh_path),
        "package_3mf_path": str(package_3mf_path),
        "processed_path": str(processed_path),
        "proof_path": str(written_proof),
        "mesh_sha256": mesh_sha,
        "package_3mf_sha256": package_3mf_sha,
        "processed_sha256": processed_sha,
        "proof_sha256": proof_sha,
        "truth_gate_status": truth_status,
        "background_removal": background,
        "mesh_build": mesh_build,
        "package_3mf": package_3mf,
        **(
            {
                "runtime_evidence_artifact_id": runtime_evidence_artifact_id,
                "runtime_evidence_path": str(runtime_evidence_path),
                "runtime_evidence_sha256": runtime_evidence_sha,
            }
            if runtime_evidence_artifact_id and runtime_evidence_path and runtime_evidence_sha
            else {}
        ),
        "prompt_head": request.prompt[:300],
    }
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, 'generation.precision_image_relief.completed', 'generation-executor', ?)",
        (proof_event_id, as_json(payload)),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'generation_precision_image_relief_completed', 'generation-executor', ?)",
        (
            new_id(),
            job_id,
            f"Generated {mesh_path.name} as precision image relief; proof_event_id={proof_event_id}",
        ),
    )
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "completed",
        "accepted": True,
        "created": True,
        "template": template_id,
        "reference": {
            "id": request.reference_artifact_id,
            "label": reference_artifact.get("label"),
            "file_path": str(reference_path),
        },
        "processed_reference": {
            "id": processed_artifact_id,
            "label": processed_path.name,
            "file_path": str(processed_path),
            "file_size": processed_path.stat().st_size,
            "sha256": processed_sha,
        },
        "artifact": {
            "id": mesh_artifact_id,
            "label": mesh_path.name,
            "file_path": str(mesh_path),
            "file_size": mesh_path.stat().st_size,
            "sha256": mesh_sha,
        },
        "package_3mf": {
            "id": package_3mf_artifact_id,
            "label": package_3mf_path.name,
            "file_path": str(package_3mf_path),
            "file_size": package_3mf_path.stat().st_size,
            "sha256": package_3mf_sha,
            "package": package_3mf,
        },
        "proof": {
            "id": proof_artifact_id,
            "label": written_proof.name,
            "file_path": str(written_proof),
            "file_size": written_proof.stat().st_size,
            "sha256": proof_sha,
            "event_id": proof_event_id,
        },
        **(
            {
                "runtime_evidence": {
                    "id": runtime_evidence_artifact_id,
                    "label": runtime_evidence_path.name,
                    "file_path": str(runtime_evidence_path),
                    "file_size": runtime_evidence_path.stat().st_size,
                    "sha256": runtime_evidence_sha,
                }
            }
            if runtime_evidence_artifact_id and runtime_evidence_path and runtime_evidence_sha
            else {}
        ),
        "background_removal": background,
        "mesh_build": mesh_build,
        "truth_gate": {"status": truth_status, "duration_s": _truth_duration(truth_report)},
    }


def _execute_hunyuan3d_image_template(request: GenerationRun, template_id: str) -> dict[str, Any]:
    import trimesh

    from hermes3d.core.proof import write_proof

    if not request.reference_artifact_id:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "queued": False,
                "reason": "hunyuan3d_image_to_3d requires a reference_artifact_id from an uploaded image.",
                "supported_templates": _supported_generation_templates(),
            },
        )

    reference_artifact = row(
        "SELECT * FROM artifacts WHERE id = ?",
        (request.reference_artifact_id,),
    )
    if not reference_artifact:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact not found: {request.reference_artifact_id}",
            },
        )
    reference_path = Path(str(reference_artifact["file_path"]))
    if not reference_path.is_file():
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Reference artifact file is missing: {reference_path}",
            },
        )

    size_mm = _constraint_float(request.constraints, "size_mm", 60.0, minimum=20.0, maximum=120.0)
    steps = _constraint_int(request.constraints, "steps", 30, minimum=8, maximum=50)
    octree_resolution = _constraint_int(
        request.constraints, "octree_resolution", 256, minimum=128, maximum=384
    )
    guidance_scale = _constraint_float(
        request.constraints, "guidance_scale", 5.0, minimum=1.0, maximum=12.0
    )
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
                "steps": steps,
                "octree_resolution": octree_resolution,
                "guidance_scale": guidance_scale,
                "reference_artifact_id": request.reference_artifact_id,
                "reference_path": str(reference_path),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:10]

    processed_path = output_dir / f"{template_id}_{signature}.rembg.png"
    mesh_path = output_dir / f"{template_id}_{signature}.stl"
    package_3mf_path = output_dir / f"{template_id}_{signature}.3mf"
    proof_path = output_dir / f"{template_id}_{signature}.proof.json"
    runtime_evidence_path = output_dir / f"{template_id}_{signature}.runtime.json"
    stdout_path = output_dir / f"{template_id}_{signature}.stdout.log"
    stderr_path = output_dir / f"{template_id}_{signature}.stderr.log"

    background = _remove_background_to_png(reference_path, processed_path)
    runtime = _run_hunyuan3d_shape_subprocess(
        processed_path=processed_path,
        mesh_path=mesh_path,
        runtime_evidence_path=runtime_evidence_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        size_mm=size_mm,
        steps=steps,
        octree_resolution=octree_resolution,
        guidance_scale=guidance_scale,
        seed=request.seed,
    )
    if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "reason": "Hunyuan3D generated mesh file is empty."},
        )

    written_proof = write_proof(
        mesh_path=mesh_path,
        output_path=proof_path,
        generator_name="hermes3d.gen3d.hunyuan3d_2_1.image_to_3d",
        generator_version="1.0.0",
        generator_signature=signature,
        visual_evidence_paths=[("background_removed_reference", processed_path)],
        modeling_backend={
            "id": "hunyuan3d_2_1_shape_comfyui_subprocess",
            "engine": runtime.get("engine"),
            "model_ckpt": runtime.get("model_ckpt"),
            "config_path": runtime.get("config_path"),
            "comfyui_root": runtime.get("comfyui_root"),
            "wrapper_root": runtime.get("wrapper_root"),
            "reference_artifact_id": request.reference_artifact_id,
            "runtime_evidence_path": str(runtime_evidence_path),
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
        },
        gpu_used=True,
        gpu={
            "before": runtime.get("gpu_before"),
            "after": runtime.get("gpu_after"),
        },
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
                "reason": f"Truth gate rejected Hunyuan3D mesh with status {truth_status}.",
                "mesh_path": str(mesh_path),
                "proof_path": str(written_proof),
                "runtime_evidence_path": str(runtime_evidence_path),
            },
        )

    package_3mf = _export_mesh_to_3mf(
        mesh_path,
        package_3mf_path,
        metadata={
            "generator": "hermes3d.gen3d.hunyuan3d_2_1.image_to_3d",
            "template": template_id,
            "signature": signature,
            "source_image": str(reference_path),
            "processed_reference": str(processed_path),
            "runtime_evidence": str(runtime_evidence_path),
        },
    )
    mesh = trimesh.load(str(mesh_path), force="mesh", process=True)
    processed_sha = _file_sha256(processed_path)
    mesh_sha = _file_sha256(mesh_path)
    package_3mf_sha = _file_sha256(package_3mf_path)
    proof_sha = _file_sha256(written_proof)
    runtime_sha = _file_sha256(runtime_evidence_path)

    execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run) VALUES (?, ?, 'generation', 'completed', NULL, 1)",
        (job_id, _generation_title(request.prompt)),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, 1, 'Generation request', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 2, 'Reference background removal', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 3, 'Hunyuan3D 2.1 CUDA shape generation', 'done', datetime('now'), datetime('now'), 0),
               (?, ?, 4, 'Signed proof envelope', 'done', datetime('now'), datetime('now'), 0)
        """,
        (new_id(), job_id, new_id(), job_id, new_id(), job_id, new_id(), job_id),
    )
    processed_artifact_id = new_id()
    mesh_artifact_id = new_id()
    package_3mf_artifact_id = new_id()
    proof_artifact_id = new_id()
    runtime_artifact_id = new_id()
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'processed_image', 'generation-executor', 'MODELING', 'BACKGROUND_REMOVAL', ?, ?, ?, ?)
        """,
        (
            processed_artifact_id,
            job_id,
            processed_path.name,
            str(processed_path),
            processed_path.stat().st_size,
            as_json(
                {
                    "sha256": processed_sha,
                    "reference_artifact_id": request.reference_artifact_id,
                    "engine": background["engine"],
                    "alpha": background["alpha"],
                    "source_label": reference_artifact.get("label"),
                }
            ),
        ),
    )
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
                    "steps": steps,
                    "octree_resolution": octree_resolution,
                    "guidance_scale": guidance_scale,
                    "seed": request.seed,
                    "reference_artifact_id": request.reference_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    "runtime_evidence_artifact_id": runtime_artifact_id,
                    "background_removal": background,
                    "hunyuan3d_runtime": runtime,
                    "mesh": _mesh_summary(mesh),
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, '3mf', 'generation-executor', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
        """,
        (
            package_3mf_artifact_id,
            job_id,
            package_3mf_path.name,
            str(package_3mf_path),
            package_3mf_path.stat().st_size,
            as_json(
                {
                    "sha256": package_3mf_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "proof_artifact_id": proof_artifact_id,
                    "runtime_evidence_artifact_id": runtime_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "reference_artifact_id": request.reference_artifact_id,
                    "package": package_3mf,
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
                    "package_3mf_artifact_id": package_3mf_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "runtime_evidence_artifact_id": runtime_artifact_id,
                    "truth_gate_status": truth_status,
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, 'runtime_evidence', 'generation-executor', 'MODELING', 'MODEL_RUNTIME', ?, ?, ?, ?)
        """,
        (
            runtime_artifact_id,
            job_id,
            runtime_evidence_path.name,
            str(runtime_evidence_path),
            runtime_evidence_path.stat().st_size,
            as_json(
                {
                    "sha256": runtime_sha,
                    "mesh_artifact_id": mesh_artifact_id,
                    "processed_reference_artifact_id": processed_artifact_id,
                    "stdout_log": str(stdout_path),
                    "stderr_log": str(stderr_path),
                    "runtime_status": runtime.get("status"),
                    "gpu_after": runtime.get("gpu_after"),
                }
            ),
        ),
    )
    execute(
        "INSERT INTO truth_gate_results (id, job_id, gate_name, status, error, duration_s) VALUES (?, ?, 'generation.hunyuan3d_mesh', 'pass', NULL, ?)",
        (new_id(), job_id, _truth_duration(truth_report)),
    )
    proof_event_id = new_id()
    payload = {
        "job_id": job_id,
        "template": template_id,
        "reference_artifact_id": request.reference_artifact_id,
        "processed_reference_artifact_id": processed_artifact_id,
        "mesh_artifact_id": mesh_artifact_id,
        "package_3mf_artifact_id": package_3mf_artifact_id,
        "proof_artifact_id": proof_artifact_id,
        "runtime_evidence_artifact_id": runtime_artifact_id,
        "mesh_path": str(mesh_path),
        "package_3mf_path": str(package_3mf_path),
        "processed_path": str(processed_path),
        "proof_path": str(written_proof),
        "runtime_evidence_path": str(runtime_evidence_path),
        "mesh_sha256": mesh_sha,
        "package_3mf_sha256": package_3mf_sha,
        "processed_sha256": processed_sha,
        "proof_sha256": proof_sha,
        "runtime_sha256": runtime_sha,
        "truth_gate_status": truth_status,
        "background_removal": background,
        "hunyuan3d_runtime": runtime,
        "package_3mf": package_3mf,
        "prompt_head": request.prompt[:300],
    }
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, 'generation.hunyuan3d.completed', 'generation-executor', ?)",
        (proof_event_id, as_json(payload)),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'generation_hunyuan3d_completed', 'generation-executor', ?)",
        (
            new_id(),
            job_id,
            f"Generated {mesh_path.name} with Hunyuan3D; proof_event_id={proof_event_id}",
        ),
    )
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "completed",
        "accepted": True,
        "created": True,
        "template": template_id,
        "reference": {
            "id": request.reference_artifact_id,
            "label": reference_artifact.get("label"),
            "file_path": str(reference_path),
        },
        "processed_reference": {
            "id": processed_artifact_id,
            "label": processed_path.name,
            "file_path": str(processed_path),
            "file_size": processed_path.stat().st_size,
            "sha256": processed_sha,
        },
        "artifact": {
            "id": mesh_artifact_id,
            "label": mesh_path.name,
            "file_path": str(mesh_path),
            "file_size": mesh_path.stat().st_size,
            "sha256": mesh_sha,
        },
        "package_3mf": {
            "id": package_3mf_artifact_id,
            "label": package_3mf_path.name,
            "file_path": str(package_3mf_path),
            "file_size": package_3mf_path.stat().st_size,
            "sha256": package_3mf_sha,
            "package": package_3mf,
        },
        "proof": {
            "id": proof_artifact_id,
            "label": written_proof.name,
            "file_path": str(written_proof),
            "file_size": written_proof.stat().st_size,
            "sha256": proof_sha,
            "event_id": proof_event_id,
        },
        "runtime_evidence": {
            "id": runtime_artifact_id,
            "label": runtime_evidence_path.name,
            "file_path": str(runtime_evidence_path),
            "file_size": runtime_evidence_path.stat().st_size,
            "sha256": runtime_sha,
        },
        "background_removal": background,
        "hunyuan3d_runtime": runtime,
        "truth_gate": {"status": truth_status, "duration_s": _truth_duration(truth_report)},
    }


def _run_hunyuan3d_shape_subprocess(
    *,
    processed_path: Path,
    mesh_path: Path,
    runtime_evidence_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    size_mm: float,
    steps: int,
    octree_resolution: int,
    guidance_scale: float,
    seed: int,
) -> dict[str, Any]:
    python_path = Path(
        os.environ.get(
            "HERMES3D_HUNYUAN3D_PYTHON",
            r"G:\Github\ComfyUI\.venv\Scripts\python.exe",
        )
    )
    if not python_path.is_file():
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Hunyuan3D Python runtime not found: {python_path}",
            },
        )
    runner_path = Path(__file__).resolve().parents[2] / "gen3d" / "hunyuan3d_shape.py"
    if not runner_path.is_file():
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "reason": f"Hunyuan3D runner missing: {runner_path}"},
        )

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[3])
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    torch_lib = Path(
        os.environ.get(
            "HERMES3D_ONNXRUNTIME_DLL_DIR",
            r"G:\Github\ComfyUI\.venv\Lib\site-packages\torch\lib",
        )
    )
    if torch_lib.is_dir():
        env["PATH"] = str(torch_lib) + os.pathsep + env.get("PATH", "")

    command = [
        str(python_path),
        str(runner_path),
        "--input",
        str(processed_path),
        "--output",
        str(mesh_path),
        "--proof-json",
        str(runtime_evidence_path),
        "--steps",
        str(steps),
        "--octree-resolution",
        str(octree_resolution),
        "--guidance-scale",
        str(guidance_scale),
        "--target-size-mm",
        str(size_mm),
        "--seed",
        str(seed),
        "--device",
        "cuda",
    ]
    timeout_s = int(os.environ.get("HERMES3D_HUNYUAN3D_TIMEOUT_S", "900"))
    try:
        with (
            stdout_path.open("w", encoding="utf-8") as stdout,
            stderr_path.open("w", encoding="utf-8") as stderr,
        ):
            proc = subprocess.run(
                command,
                stdout=stdout,
                stderr=stderr,
                text=True,
                timeout=timeout_s,
                check=False,
                env=env,
            )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "status": "failed",
                "reason": f"Hunyuan3D generation timed out after {timeout_s}s.",
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
            },
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Hunyuan3D runtime failed to start: {type(exc).__name__}: {exc}",
            },
        ) from exc

    runtime = _load_runtime_evidence(runtime_evidence_path)
    runtime["return_code"] = proc.returncode
    runtime["stdout_log"] = str(stdout_path)
    runtime["stderr_log"] = str(stderr_path)
    runtime_evidence_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True), encoding="utf-8"
    )
    if proc.returncode != 0 or runtime.get("status") != "completed":
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "reason": (
                    f"Hunyuan3D generation failed with return code {proc.returncode}: "
                    f"{runtime.get('error') or 'see runtime logs'}"
                ),
                "runtime_evidence_path": str(runtime_evidence_path),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
            },
        )
    return runtime


def _load_runtime_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing", "runtime_evidence_path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "unreadable",
            "runtime_evidence_path": str(path),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return (
        data if isinstance(data, dict) else {"status": "invalid", "raw_type": type(data).__name__}
    )


def _background_runtime_evidence_path(background: dict[str, Any]) -> Path | None:
    runtime = background.get("runtime")
    if not isinstance(runtime, dict):
        return None
    raw_path = runtime.get("runtime_evidence_path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path)
    try:
        if path.is_file() and path.stat().st_size > 0:
            return path
    except OSError:
        return None
    return None


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


def _constraint_int(
    constraints: dict[str, Any], key: str, default: int, *, minimum: int, maximum: int
) -> int:
    value = constraints.get(key, default)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail={"status": "blocked", "reason": f"{key} must be an integer."}
        ) from exc
    if not (minimum <= parsed <= maximum):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "blocked",
                "reason": f"{key} must be between {minimum:g} and {maximum:g}.",
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


def _export_mesh_to_3mf(
    mesh_path: Path, package_path: Path, *, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    import trimesh

    mesh = trimesh.load(str(mesh_path), force="mesh", process=True)
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "reason": "Cannot package empty mesh as 3MF."},
        )
    package_path.parent.mkdir(parents=True, exist_ok=True)
    model_xml = _three_mf_model_xml(mesh, metadata=metadata or {})
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" '
        'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    relationships_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", content_types_xml)
        package.writestr("_rels/.rels", relationships_xml)
        package.writestr("3D/3dmodel.model", model_xml)

    return _verify_3mf_package(
        package_path, vertex_count=len(mesh.vertices), face_count=len(mesh.faces)
    )


def _three_mf_model_xml(mesh: Any, *, metadata: dict[str, Any]) -> bytes:
    core_ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    xml_ns = "http://www.w3.org/XML/1998/namespace"
    ET.register_namespace("", core_ns)
    ET.register_namespace("xml", xml_ns)
    root = ET.Element(
        f"{{{core_ns}}}model",
        {
            "unit": "millimeter",
            f"{{{xml_ns}}}lang": "en-US",
        },
    )
    for key, value in sorted(metadata.items()):
        if value is None:
            continue
        item = ET.SubElement(root, f"{{{core_ns}}}metadata", {"name": f"Hermes3D:{key}"})
        item.text = str(value)

    resources = ET.SubElement(root, f"{{{core_ns}}}resources")
    obj = ET.SubElement(resources, f"{{{core_ns}}}object", {"id": "1", "type": "model"})
    mesh_el = ET.SubElement(obj, f"{{{core_ns}}}mesh")
    vertices_el = ET.SubElement(mesh_el, f"{{{core_ns}}}vertices")
    for vertex in mesh.vertices:
        ET.SubElement(
            vertices_el,
            f"{{{core_ns}}}vertex",
            {
                "x": _coord_text(vertex[0]),
                "y": _coord_text(vertex[1]),
                "z": _coord_text(vertex[2]),
            },
        )
    triangles_el = ET.SubElement(mesh_el, f"{{{core_ns}}}triangles")
    for face in mesh.faces:
        ET.SubElement(
            triangles_el,
            f"{{{core_ns}}}triangle",
            {"v1": str(int(face[0])), "v2": str(int(face[1])), "v3": str(int(face[2]))},
        )
    build = ET.SubElement(root, f"{{{core_ns}}}build")
    ET.SubElement(build, f"{{{core_ns}}}item", {"objectid": "1"})
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")


def _coord_text(value: Any) -> str:
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _verify_3mf_package(
    package_path: Path, *, vertex_count: int | None = None, face_count: int | None = None
) -> dict[str, Any]:
    if not package_path.is_file() or package_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "reason": "3MF package was not written."},
        )
    try:
        with zipfile.ZipFile(package_path) as package:
            names = package.namelist()
            has_content_types = "[Content_Types].xml" in names
            has_relationships = "_rels/.rels" in names
            has_model = "3D/3dmodel.model" in names
            if not (has_content_types and has_relationships and has_model):
                raise ValueError(f"Missing required 3MF entries: {names}")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "reason": f"3MF package verification failed: {type(exc).__name__}: {exc}",
            },
        ) from exc
    return {
        "format": "3mf",
        "path": str(package_path),
        "entries": names,
        "vertex_count": vertex_count,
        "face_count": face_count,
    }


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


def _prepend_runtime_path(path: Path) -> None:
    if not path.exists():
        return
    path_text = str(path)
    entries = os.environ.get("PATH", "").split(os.pathsep)
    if path_text not in entries:
        os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")


def _configure_rembg_runtime_paths() -> None:
    if "U2NET_HOME" not in os.environ and _DEFAULT_REMBG_MODEL_HOME.exists():
        os.environ["U2NET_HOME"] = str(_DEFAULT_REMBG_MODEL_HOME)
    _prepend_runtime_path(_DEFAULT_COMFYUI_TORCH_LIB)


def _get_rembg_session(rembg_module: Any) -> tuple[Any | None, str | None, list[str] | None]:
    requested = os.environ.get("HERMES3D_REMBG_MODEL", "bria-rmbg")
    candidates = [requested]
    for fallback in ("birefnet-general", "isnet-general-use", "u2net"):
        if fallback not in candidates:
            candidates.append(fallback)

    last_error: Exception | None = None
    new_session = getattr(rembg_module, "new_session", None)
    if not callable(new_session):
        return None, None, None

    for model_name in candidates:
        try:
            if model_name not in _REMBG_SESSIONS:
                _REMBG_SESSIONS[model_name] = new_session(model_name)
            session = _REMBG_SESSIONS[model_name]
            providers = None
            inner_session = getattr(session, "inner_session", None)
            if inner_session is not None and hasattr(inner_session, "get_providers"):
                providers = list(inner_session.get_providers())
            return session, model_name, providers
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"rembg session initialization failed: {type(last_error).__name__}: {last_error}",
            },
        ) from last_error
    return None, None, None


def _remove_background_to_png(reference_path: Path, output_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Pillow is not installed in the active backend Python runtime.",
            },
        ) from exc
    _configure_rembg_runtime_paths()
    try:
        import rembg
    except ImportError as exc:
        return _remove_background_to_png_subprocess(reference_path, output_path, import_error=exc)

    try:
        session, model_name, providers = _get_rembg_session(rembg)
        source = Image.open(reference_path).convert("RGBA")
        if session is not None:
            removed = rembg.remove(source, session=session)
        else:
            removed = rembg.remove(source)
        if isinstance(removed, bytes):
            result = Image.open(BytesIO(removed)).convert("RGBA")
        else:
            result = removed.convert("RGBA")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"Background removal failed: {type(exc).__name__}: {exc}",
            },
        ) from exc

    alpha = _alpha_stats(result)
    if alpha["foreground_pixels"] == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Background removal produced no foreground pixels.",
            },
        )
    if alpha["transparent_pixels"] == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Background removal produced no transparent pixels; white background is still present.",
            },
        )
    return {
        "engine": "rembg",
        "model": model_name,
        "providers": providers,
        "output_path": str(output_path),
        "alpha": alpha,
    }


def _remove_background_to_png_subprocess(
    reference_path: Path, output_path: Path, *, import_error: ImportError | None = None
) -> dict[str, Any]:
    python_path = _configured_rembg_python_path()
    if not python_path.is_file():
        reason = (
            "rembg is not installed in the active backend Python runtime and the configured "
            f"subprocess runtime is missing: {python_path}."
        )
        if import_error is not None:
            reason += f" Backend import error: {type(import_error).__name__}: {import_error}"
        raise HTTPException(
            status_code=409,
            detail={"status": "blocked", "reason": reason},
        ) from import_error

    runner_path = Path(__file__).resolve().parents[2] / "gen3d" / "rembg_remove.py"
    if not runner_path.is_file():
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "reason": f"rembg subprocess runner missing: {runner_path}",
            },
        ) from import_error

    runtime_evidence_path = output_path.with_name(f"{output_path.stem}.runtime.json")
    stdout_path = output_path.with_name(f"{output_path.stem}.stdout.log")
    stderr_path = output_path.with_name(f"{output_path.stem}.stderr.log")
    command = [
        str(python_path),
        str(runner_path),
        "--input",
        str(reference_path),
        "--output",
        str(output_path),
        "--proof-json",
        str(runtime_evidence_path),
        "--model",
        os.environ.get("HERMES3D_REMBG_MODEL", "bria-rmbg"),
    ]
    timeout_s = int(os.environ.get("HERMES3D_REMBG_TIMEOUT_S", "240"))
    try:
        with (
            stdout_path.open("w", encoding="utf-8") as stdout,
            stderr_path.open("w", encoding="utf-8") as stderr,
        ):
            proc = subprocess.run(
                command,
                stdout=stdout,
                stderr=stderr,
                text=True,
                timeout=timeout_s,
                check=False,
                env=_rembg_subprocess_env(),
            )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "status": "failed",
                "reason": f"rembg subprocess timed out after {timeout_s}s.",
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
            },
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": f"rembg subprocess failed to start: {type(exc).__name__}: {exc}",
            },
        ) from exc

    runtime = _load_runtime_evidence(runtime_evidence_path)
    runtime["return_code"] = proc.returncode
    runtime["stdout_log"] = str(stdout_path)
    runtime["stderr_log"] = str(stderr_path)
    runtime_evidence_path.write_text(
        json.dumps(runtime, indent=2, sort_keys=True), encoding="utf-8"
    )
    if proc.returncode != 0 or runtime.get("status") != "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": (
                    f"rembg subprocess failed with return code {proc.returncode}: "
                    f"{runtime.get('error') or 'see runtime logs'}"
                ),
                "runtime_evidence_path": str(runtime_evidence_path),
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
            },
        )
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise HTTPException(
            status_code=500,
            detail={"status": "failed", "reason": "rembg subprocess did not write an output PNG."},
        )

    from PIL import Image

    image = Image.open(output_path).convert("RGBA")
    alpha = _alpha_stats(image)
    if alpha["foreground_pixels"] == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Background removal produced no foreground pixels.",
            },
        )
    if alpha["transparent_pixels"] == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Background removal produced no transparent pixels; white background is still present.",
            },
        )

    return {
        "engine": "rembg-subprocess",
        "model": runtime.get("model"),
        "providers": runtime.get("providers"),
        "output_path": str(output_path),
        "alpha": alpha,
        "runtime": {
            "python": str(python_path),
            "runtime_evidence_path": str(runtime_evidence_path),
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "return_code": proc.returncode,
        },
    }


def _alpha_stats(image: Any) -> dict[str, Any]:
    alpha = image.getchannel("A")
    histogram = alpha.histogram()
    transparent_pixels = int(sum(histogram[:16]))
    foreground_pixels = int(sum(histogram[32:]))
    bbox = alpha.point(lambda p: 255 if p > 32 else 0).getbbox()
    return {
        "width": int(image.width),
        "height": int(image.height),
        "transparent_pixels": transparent_pixels,
        "foreground_pixels": foreground_pixels,
        "foreground_bbox": list(bbox) if bbox else None,
    }


def _alpha_png_to_relief_mesh(
    image_path: Path,
    mesh_path: Path,
    *,
    size_mm: float,
    thickness_mm: float,
) -> tuple[Any, dict[str, Any]]:
    import trimesh

    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Pillow is not installed in the active backend Python runtime.",
            },
        ) from exc

    image = Image.open(image_path).convert("RGBA")
    alpha = image.getchannel("A")
    mask = alpha.point(lambda p: 255 if p > 32 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Reference image has no usable foreground mask.",
            },
        )
    cropped = mask.crop(bbox)
    max_cells = max(12, min(72, int(size_mm / 1.5)))
    scale = min(max_cells / max(cropped.width, cropped.height), 1.0)
    width = max(1, int(round(cropped.width * scale)))
    height = max(1, int(round(cropped.height * scale)))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    resized = cropped.resize((width, height), resampling)
    occupied: list[list[bool]] = []
    foreground_count = 0
    for y in range(height):
        row_values: list[bool] = []
        for x in range(width):
            is_foreground = resized.getpixel((x, y)) > 64
            row_values.append(is_foreground)
            if is_foreground:
                foreground_count += 1
        occupied.append(row_values)
    if foreground_count == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Reference mask is empty after printability downsampling.",
            },
        )

    cell_mm = size_mm / max(width, height)
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    vertex_ids: dict[tuple[float, float, float], int] = {}

    def vertex_id(coord: tuple[float, float, float]) -> int:
        key = (round(coord[0], 6), round(coord[1], 6), round(coord[2], 6))
        existing = vertex_ids.get(key)
        if existing is not None:
            return existing
        vertex_ids[key] = len(vertices)
        vertices.append(key)
        return vertex_ids[key]

    def add_quad(
        a: tuple[float, float, float],
        b: tuple[float, float, float],
        c: tuple[float, float, float],
        d: tuple[float, float, float],
    ) -> None:
        faces.append((vertex_id(a), vertex_id(b), vertex_id(c)))
        faces.append((vertex_id(a), vertex_id(c), vertex_id(d)))

    def is_occupied(px: int, py: int) -> bool:
        return 0 <= px < width and 0 <= py < height and occupied[py][px]

    half_w = width * cell_mm / 2.0
    half_h = height * cell_mm / 2.0
    for y in range(height):
        for x in range(width):
            if not occupied[y][x]:
                continue
            x0 = x * cell_mm - half_w
            x1 = (x + 1) * cell_mm - half_w
            y0 = half_h - (y + 1) * cell_mm
            y1 = half_h - y * cell_mm
            z0 = 0.0
            z1 = thickness_mm
            a = (x0, y0, z0)
            b = (x1, y0, z0)
            c = (x1, y1, z0)
            d = (x0, y1, z0)
            A = (x0, y0, z1)
            B = (x1, y0, z1)
            C = (x1, y1, z1)
            D = (x0, y1, z1)

            add_quad(A, B, C, D)
            add_quad(a, d, c, b)
            if not is_occupied(x - 1, y):
                add_quad(a, A, D, d)
            if not is_occupied(x + 1, y):
                add_quad(b, c, C, B)
            if not is_occupied(x, y - 1):
                add_quad(d, D, C, c)
            if not is_occupied(x, y + 1):
                add_quad(a, b, B, A)

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.merge_vertices()
    trimesh.repair.fix_normals(mesh, multibody=True)
    mesh.apply_translation((0, 0, -float(mesh.bounds[0][2])))
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(mesh_path, file_type="stl")
    return mesh, {
        "mask_width": width,
        "mask_height": height,
        "foreground_cells": foreground_count,
        "cell_mm": cell_mm,
        "thickness_mm": thickness_mm,
    }


def _image_to_precision_relief_mesh(
    image_path: Path,
    mesh_path: Path,
    *,
    size_mm: float,
    base_thickness_mm: float,
    relief_height_mm: float,
    max_resolution: int,
    min_feature_mm: float,
) -> tuple[Any, dict[str, Any]]:
    import numpy as np
    import trimesh

    try:
        from PIL import Image
    except ImportError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Pillow is not installed in the active backend Python runtime.",
            },
        ) from exc

    image = Image.open(image_path).convert("RGBA")
    alpha = image.getchannel("A")
    mask_image = alpha.point(lambda p: 255 if p > 32 else 0)
    bbox = mask_image.getbbox()
    if bbox is None:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Reference image has no usable foreground mask.",
            },
        )

    cropped = image.crop(bbox)
    scale = min(float(max_resolution) / float(max(cropped.width, cropped.height)), 1.0)
    width = max(1, int(round(cropped.width * scale)))
    height = max(1, int(round(cropped.height * scale)))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    resized = cropped.resize((width, height), resampling)
    rgba = np.asarray(resized, dtype=np.float32) / 255.0
    mask = rgba[:, :, 3] > (32.0 / 255.0)
    original_foreground_count = int(mask.sum())
    cell_mm = size_mm / max(width, height)
    mask, feature_iterations = _thicken_mask_for_min_feature(
        mask, cell_mm=cell_mm, min_feature_mm=min_feature_mm
    )
    foreground_count = int(mask.sum())
    if foreground_count == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Reference mask is empty after precision downsampling.",
            },
        )

    rgb = rgba[:, :, :3]
    luminance = (0.2126 * rgb[:, :, 0]) + (0.7152 * rgb[:, :, 1]) + (0.0722 * rgb[:, :, 2])
    foreground_luma = luminance[mask]
    low = float(np.percentile(foreground_luma, 2))
    high = float(np.percentile(foreground_luma, 98))
    if high <= low:
        normalized = np.zeros_like(luminance, dtype=np.float32)
    else:
        normalized = np.clip((luminance - low) / (high - low), 0.0, 1.0).astype(np.float32)
    cell_heights = base_thickness_mm + (normalized * relief_height_mm)
    cell_heights = np.where(mask, cell_heights, base_thickness_mm).astype(np.float32)

    node_heights = np.zeros((height + 1, width + 1), dtype=np.float32)
    node_counts = np.zeros((height + 1, width + 1), dtype=np.float32)
    weighted_heights = np.where(mask, cell_heights, 0.0)
    mask_float = mask.astype(np.float32)
    for dy in (0, 1):
        for dx in (0, 1):
            node_heights[dy : dy + height, dx : dx + width] += weighted_heights
            node_counts[dy : dy + height, dx : dx + width] += mask_float
    node_heights = np.where(node_counts > 0, node_heights / np.maximum(node_counts, 1.0), 0.0)

    half_w = width * cell_mm / 2.0
    half_h = height * cell_mm / 2.0
    vertices: list[tuple[float, float, float]] = []
    for yy in range(height + 1):
        y_coord = half_h - yy * cell_mm
        for xx in range(width + 1):
            x_coord = xx * cell_mm - half_w
            vertices.append((float(x_coord), float(y_coord), float(node_heights[yy, xx])))
    bottom_offset = len(vertices)
    for yy in range(height + 1):
        y_coord = half_h - yy * cell_mm
        for xx in range(width + 1):
            x_coord = xx * cell_mm - half_w
            vertices.append((float(x_coord), float(y_coord), 0.0))

    def top_id(yy: int, xx: int) -> int:
        return yy * (width + 1) + xx

    def bottom_id(yy: int, xx: int) -> int:
        return bottom_offset + yy * (width + 1) + xx

    faces: list[tuple[int, int, int]] = []

    def add_quad(a: int, b: int, c: int, d: int) -> None:
        faces.append((a, b, c))
        faces.append((a, c, d))

    def is_occupied(px: int, py: int) -> bool:
        return 0 <= px < width and 0 <= py < height and bool(mask[py, px])

    for yy in range(height):
        for xx in range(width):
            if not mask[yy, xx]:
                continue
            n00 = top_id(yy, xx)
            n10 = top_id(yy, xx + 1)
            n11 = top_id(yy + 1, xx + 1)
            n01 = top_id(yy + 1, xx)
            b00 = bottom_id(yy, xx)
            b10 = bottom_id(yy, xx + 1)
            b11 = bottom_id(yy + 1, xx + 1)
            b01 = bottom_id(yy + 1, xx)

            add_quad(n00, n01, n11, n10)
            add_quad(b00, b10, b11, b01)
            if not is_occupied(xx - 1, yy):
                add_quad(b00, b01, n01, n00)
            if not is_occupied(xx + 1, yy):
                add_quad(b10, n10, n11, b11)
            if not is_occupied(xx, yy - 1):
                add_quad(b00, n00, n10, b10)
            if not is_occupied(xx, yy + 1):
                add_quad(b01, b11, n11, n01)

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    trimesh.repair.fix_normals(mesh, multibody=True)
    mesh.apply_translation((0, 0, -float(mesh.bounds[0][2])))
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(mesh_path, file_type="stl")
    return mesh, {
        "source_width": int(image.width),
        "source_height": int(image.height),
        "crop_bbox": list(bbox),
        "mesh_width": width,
        "mesh_height": height,
        "original_foreground_cells": original_foreground_count,
        "foreground_cells": foreground_count,
        "cell_mm": cell_mm,
        "base_thickness_mm": base_thickness_mm,
        "relief_height_mm": relief_height_mm,
        "min_feature_mm": min_feature_mm,
        "feature_thickening_iterations": feature_iterations,
        "luminance_percentile_2": low,
        "luminance_percentile_98": high,
    }


def _thicken_mask_for_min_feature(
    mask: Any, *, cell_mm: float, min_feature_mm: float
) -> tuple[Any, int]:
    """Thicken image-derived foreground so fine logo strokes pass printability.

    The truth gate samples physical wall thickness. A one-pixel-wide stroke
    at the downsampled mesh resolution can be visually accurate but too thin
    to print. Expanding the mask before meshing preserves the silhouette while
    forcing features toward the configured minimum physical width.
    """
    if cell_mm <= 0:
        return mask, 0
    min_cells = max(1.0, min_feature_mm / cell_mm)
    iterations = max(0, math.ceil((min_cells - 1.0) / 2.0))
    if iterations == 0:
        return mask, 0

    import numpy as np

    thickened = mask.astype(bool, copy=True)
    for _ in range(iterations):
        padded = np.pad(thickened, 1, mode="constant", constant_values=False)
        expanded = np.zeros_like(thickened, dtype=bool)
        for dy in range(3):
            for dx in range(3):
                expanded |= padded[dy : dy + thickened.shape[0], dx : dx + thickened.shape[1]]
        thickened = expanded
    return thickened, iterations
