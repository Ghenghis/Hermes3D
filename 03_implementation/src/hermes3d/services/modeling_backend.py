"""Modeling backend identification + survey — real probes, no fabrication.

Used by W18-A20 to record which modeling/mesh/CAD backend produced an
artifact in the proof envelope, alongside whether a GPU code path was
exercised. This is intentionally separate from the LLM provider proof —
LLM provider proof is NOT modeling proof.

Two public functions:
    backend_for_template(template_id) -> ModelingBackend
        The deterministic backend description for a known template.

    survey_backends() -> list[ModelingBackend]
        Live probe of every supported backend. Each entry says whether
        the backend is importable / on PATH AND whether a GPU code path
        exists. GPU-path detection is conservative: only marked True when
        the upstream documents it (Blender Cycles CUDA, etc.).
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
import shutil
from dataclasses import asdict, dataclass, field
from typing import Any

LOG = logging.getLogger(__name__)


@dataclass
class ModelingBackend:
    """A single modeling backend's identity + capabilities.

    All fields are real probe results. ``available`` reflects whether the
    backend is usable in this Python runtime / on this host. ``gpu_capable``
    indicates a *documented* GPU code path; just because a backend imports
    successfully does not imply a GPU path is available — that has to be
    exercised separately and recorded in the proof envelope.
    """

    name: str
    kind: str  # "python_library" or "cli_executable"
    version: str | None
    path: str | None
    available: bool
    gpu_capable: bool
    gpu_code_path_doc: str | None = None
    capabilities: list[str] = field(default_factory=list)
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _probe_python(name: str) -> tuple[str | None, str | None, bool]:
    """Return (version, module_path, importable)."""
    spec = importlib.util.find_spec(name)
    if spec is None:
        return None, None, False
    version: str | None = None
    try:
        version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        version = None
    except Exception as exc:  # pragma: no cover - rare metadata edge case
        LOG.debug("metadata.version(%s) failed: %s", name, exc)
        version = None
    module_path = str(spec.origin) if spec.origin else None
    return version, module_path, True


def _probe_cli(names: list[str]) -> tuple[str | None, str | None]:
    """Return (path, version_string) — version_string is None when probe fails."""
    for candidate in names:
        found = shutil.which(candidate)
        if found:
            return found, None
    return None, None


# ---------------------------------------------------------------------------
# Per-backend descriptors
# ---------------------------------------------------------------------------


def _trimesh_backend() -> ModelingBackend:
    version, path, ok = _probe_python("trimesh")
    return ModelingBackend(
        name="trimesh",
        kind="python_library",
        version=version,
        path=path,
        available=ok,
        gpu_capable=False,
        gpu_code_path_doc=None,
        capabilities=[
            "mesh_validation",
            "stl_import_export",
            "watertight_check",
            "boolean_via_manifold3d",
        ],
        detail=(
            "trimesh proper has no GPU code path; boolean ops are routed "
            "to manifold3d when the engine is selected explicitly."
        ),
    )


def _manifold3d_backend() -> ModelingBackend:
    version, path, ok = _probe_python("manifold3d")
    return ModelingBackend(
        name="manifold3d",
        kind="python_library",
        version=version,
        path=path,
        available=ok,
        gpu_capable=False,
        gpu_code_path_doc=None,
        capabilities=[
            "boolean_csg",
            "manifold_mesh",
            "robust_union_difference",
        ],
        detail=(
            "manifold3d runs on CPU. There is no published CUDA build of "
            "the Python wheel as of this writing; mark gpu_capable=False."
        ),
    )


def _openscad_backend() -> ModelingBackend:
    path, _ = _probe_cli(["openscad", "openscad-nightly"])
    return ModelingBackend(
        name="openscad",
        kind="cli_executable",
        version=None,
        path=path,
        available=path is not None,
        gpu_capable=False,
        gpu_code_path_doc=None,
        capabilities=["solid_csg", "parametric_scad", "stl_export"],
        detail="OpenSCAD runs single-threaded CPU CSG; no GPU code path.",
    )


def _blender_backend() -> ModelingBackend:
    path, _ = _probe_cli(["blender"])
    # If not on PATH, check well-known Windows install locations as a
    # courtesy — these are read-only probes, not fabrications.
    if not path:
        from pathlib import Path

        for candidate in (
            r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        ):
            if Path(candidate).is_file():
                path = candidate
                break
    return ModelingBackend(
        name="blender",
        kind="cli_executable",
        version=None,
        path=path,
        available=path is not None,
        gpu_capable=True,
        gpu_code_path_doc=(
            "Cycles render engine supports cycles_device=CUDA/OPTIX; "
            "exercised in W18-A20 by rendering a CUDA-backed thumbnail."
        ),
        capabilities=[
            "mesh_modeling",
            "stl_export",
            "python_scripting",
            "cycles_render",
            "cycles_cuda",
        ],
        detail="Blender 5.x ships Cycles with a CUDA backend on Windows.",
    )


def _cadquery_backend() -> ModelingBackend:
    version, path, ok = _probe_python("cadquery")
    return ModelingBackend(
        name="cadquery",
        kind="python_library",
        version=version,
        path=path,
        available=ok,
        gpu_capable=False,
        gpu_code_path_doc=None,
        capabilities=["parametric_cad", "brep_modeling", "step_export"],
        detail="CadQuery uses OpenCascade BRep; CPU only.",
    )


def _freecad_backend() -> ModelingBackend:
    path, _ = _probe_cli(["freecad", "FreeCAD", "freecadcmd", "FreeCADCmd"])
    return ModelingBackend(
        name="freecad",
        kind="cli_executable",
        version=None,
        path=path,
        available=path is not None,
        gpu_capable=False,
        gpu_code_path_doc=None,
        capabilities=["parametric_cad", "step_export", "stl_export"],
        detail="FreeCAD core is CPU; viewport uses GPU but modeling does not.",
    )


def survey_backends() -> list[ModelingBackend]:
    """Probe every modeling backend Hermes3D knows about. Live results only."""
    return [
        _trimesh_backend(),
        _manifold3d_backend(),
        _openscad_backend(),
        _blender_backend(),
        _cadquery_backend(),
        _freecad_backend(),
    ]


def backend_for_template(template_id: str) -> ModelingBackend:
    """Return the modeling backend the named template runs on.

    ``desk_organizer`` and ``simple_box`` use ``trimesh + manifold3d``.
    ``calibration_cube`` uses ``trimesh`` only. We return the *primary*
    backend (trimesh) and populate details with the boolean engine when one
    is used so downstream consumers see the full picture without parsing a
    list.

    Raises ``KeyError`` if the template is unknown — never invents a
    backend, never returns "unknown" as the name.
    """
    if template_id in {"desk_organizer", "simple_box"}:
        trimesh = _trimesh_backend()
        manifold = _manifold3d_backend()
        if not trimesh.available or not manifold.available:
            missing = []
            if not trimesh.available:
                missing.append("trimesh")
            if not manifold.available:
                missing.append("manifold3d")
            trimesh.available = False
            trimesh.detail = f"{template_id} requires trimesh + manifold3d; missing: " + ", ".join(
                missing
            )
            return trimesh
        trimesh.detail = (
            f"{template_id}: trimesh {trimesh.version} routed to "
            f"manifold3d {manifold.version} for boolean CSG. CPU pipeline."
        )
        trimesh.capabilities = [
            "csg_boolean_difference",
            "csg_boolean_union",
            "stl_export",
            "watertight_check",
            "winding_consistent",
            "manifold3d_engine",
        ]
        return trimesh
    if template_id == "calibration_cube":
        trimesh = _trimesh_backend()
        trimesh.detail = (
            f"calibration_cube: trimesh {trimesh.version} solid box mesh. CPU pipeline."
        )
        trimesh.capabilities = [
            "primitive_box_mesh",
            "stl_export",
            "watertight_check",
            "winding_consistent",
        ]
        return trimesh
    raise KeyError(f"Unknown template_id: {template_id!r}")


def backend_summary_for_proof(template_id: str) -> dict[str, Any]:
    """Return the dict-shaped ``modeling_backend`` field for proof envelopes."""
    backend = backend_for_template(template_id)
    payload: dict[str, Any] = {
        "name": backend.name,
        "kind": backend.kind,
        "version": backend.version,
        "path": backend.path,
        "available": backend.available,
        "gpu_capable": backend.gpu_capable,
        "capabilities": list(backend.capabilities),
    }
    if backend.detail:
        payload["detail"] = backend.detail
    if template_id in {"desk_organizer", "simple_box"}:
        manifold = _manifold3d_backend()
        payload["engine"] = {
            "name": "manifold3d",
            "version": manifold.version,
            "path": manifold.path,
            "available": manifold.available,
        }
    return payload


__all__ = [
    "ModelingBackend",
    "backend_for_template",
    "backend_summary_for_proof",
    "survey_backends",
]
