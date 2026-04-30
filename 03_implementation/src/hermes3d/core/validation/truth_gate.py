"""
Hermes3D-OS — Printability Truth Gate.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §6 (Printability Truth Gate)
Schema:   01-ARCHITECTURE/contracts/truth_gate_report.schema.json

This module is intentionally self-contained: it depends only on numpy and
trimesh (with the manifold3d backend for boolean / volume operations).
It is the single source of truth for whether a mesh is allowed to leave
the pipeline as "printable".

Design rules (binding):
  - Every check is real geometry; no sampled placeholders, no constants
    masquerading as measurements.
  - Every check returns a numeric measurement AND a boolean pass/fail
    against an explicit threshold.
  - Failure of any required check fails the gate.
  - The full report is JSON-serialisable and conforms to the schema above.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


CURRENT_SCHEMA_VERSION = "1.0.0"


class CheckStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass(frozen=True)
class TruthGateConfig:
    """Thresholds for the printability gate. All units are millimetres."""

    min_wall_thickness_mm: float = 1.2
    bed_size_mm: tuple[float, float, float] = (220.0, 220.0, 250.0)
    max_overhang_ratio: float = 0.35
    max_print_minutes: int = 480
    min_volume_mm3: float = 100.0
    max_self_intersection_ratio: float = 0.001  # <0.1% of faces
    thickness_sample_count: int = 2000
    require_watertight: bool = True
    require_manifold: bool = True
    require_consistent_normals: bool = True
    require_bed_fit: bool = True
    require_minimum_volume: bool = True
    require_thickness: bool = True
    require_no_self_intersection: bool = True

    # Optional: validate against a specific printer in the fleet (kinematics-
    # aware bed fit + thermal/material warnings). When set, the bed_size_mm
    # field is IGNORED in favour of the profile's actual envelope.
    # See hermes3d.core.printers.list_ids() for valid values.
    printer_profile_id: str | None = None
    require_printer_fit: bool = True

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    threshold: dict[str, Any]
    measured: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "threshold": self.threshold,
            "measured": self.measured,
            "message": self.message,
        }


@dataclass
class TruthGateReport:
    schema_version: str
    overall_status: CheckStatus
    mesh_path: str
    mesh_sha256: str
    config: dict[str, Any]
    checks: list[CheckResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp_unix: float = 0.0

    @property
    def passed(self) -> bool:
        return self.overall_status is CheckStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "overall_status": self.overall_status.value,
            "mesh_path": self.mesh_path,
            "mesh_sha256": self.mesh_sha256,
            "config": self.config,
            "checks": [c.to_dict() for c in self.checks],
            "duration_seconds": self.duration_seconds,
            "timestamp_unix": self.timestamp_unix,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_mesh(mesh_path: Path) -> trimesh.Trimesh:
    """Load a mesh and normalise it for analysis.

    STL files do not carry vertex adjacency; without an explicit
    merge_vertices step a perfectly closed body would still report
    is_watertight == False. We merge with a small numerical tolerance
    that is safe for printable-scale meshes (mm).
    """
    obj = trimesh.load(mesh_path, force="mesh", process=True)
    if isinstance(obj, trimesh.Scene):
        if not obj.geometry:
            raise ValueError(f"Loaded scene has no geometry: {mesh_path}")
        obj = trimesh.util.concatenate(tuple(obj.geometry.values()))
    if not isinstance(obj, trimesh.Trimesh):
        raise TypeError(f"Loaded object is not a mesh: {type(obj).__name__}")
    if len(obj.faces) == 0:
        raise ValueError(f"Mesh has zero faces: {mesh_path}")
    # process=True already merges vertices, removes unreferenced ones, and
    # drops degenerate faces. We call validate explicitly so the contract is
    # unambiguous even if upstream defaults change.
    obj.merge_vertices()
    obj.remove_unreferenced_vertices()
    obj.process(validate=True)
    return obj


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_watertight(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_watertight:
        return CheckResult(
            "watertight", CheckStatus.SKIP,
            {"required": False}, {"watertight": bool(mesh.is_watertight)},
            "Watertight check skipped by config.",
        )
    measured = bool(mesh.is_watertight)
    return CheckResult(
        name="watertight",
        status=CheckStatus.PASS if measured else CheckStatus.FAIL,
        threshold={"required": True},
        measured={"watertight": measured, "open_edges": int(len(mesh.facets_boundary or []))},
        message="Mesh is watertight." if measured else
                "Mesh is NOT watertight; open edges detected.",
    )


def _check_manifold(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_manifold:
        return CheckResult(
            "manifold", CheckStatus.SKIP,
            {"required": False}, {},
            "Manifold check skipped by config.",
        )
    is_winding = bool(mesh.is_winding_consistent)
    euler = int(mesh.euler_number)
    is_manifold = is_winding and bool(mesh.is_watertight)
    return CheckResult(
        name="manifold",
        status=CheckStatus.PASS if is_manifold else CheckStatus.FAIL,
        threshold={"is_winding_consistent": True, "is_watertight": True},
        measured={
            "is_winding_consistent": is_winding,
            "is_watertight": bool(mesh.is_watertight),
            "euler_number": euler,
        },
        message="Mesh is 2-manifold." if is_manifold else
                "Mesh is NOT 2-manifold (winding inconsistent or non-watertight).",
    )


def _check_normals(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    """Reject inverted/inconsistent face normals.

    A watertight mesh whose volume is negative has inverted normals.
    """
    if not cfg.require_consistent_normals:
        return CheckResult(
            "normals", CheckStatus.SKIP,
            {"required": False}, {}, "Normal check skipped.",
        )
    volume = float(mesh.volume)
    is_winding = bool(mesh.is_winding_consistent)
    ok = is_winding and volume > 0
    return CheckResult(
        name="normals",
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        threshold={"is_winding_consistent": True, "volume_sign": "positive"},
        measured={"is_winding_consistent": is_winding, "volume_mm3": volume},
        message="Face normals are consistent and outward-facing." if ok else
                "Face normals are inconsistent or inverted (negative signed volume).",
    )


def _check_bed_fit(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_bed_fit:
        return CheckResult(
            "bed_fit", CheckStatus.SKIP,
            {"required": False}, {}, "Bed fit check skipped.",
        )
    extents = mesh.extents.astype(float)
    bx, by, bz = cfg.bed_size_mm
    fits = bool(extents[0] <= bx and extents[1] <= by and extents[2] <= bz)
    return CheckResult(
        name="bed_fit",
        status=CheckStatus.PASS if fits else CheckStatus.FAIL,
        threshold={"bed_size_mm": [bx, by, bz]},
        measured={"extents_mm": [float(e) for e in extents]},
        message=f"Mesh fits within {bx}x{by}x{bz} mm build volume." if fits else
                f"Mesh ({extents.tolist()}) exceeds bed {[bx, by, bz]}.",
    )


def _check_printer_fit(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    """Validate the mesh against a specific printer profile in the fleet.

    Uses kinematics-aware bed fitting (rectangular vs circular delta bed)
    and reports the target printer's full envelope and firmware support.

    Skipped when ``cfg.printer_profile_id`` is None.
    """
    if cfg.printer_profile_id is None:
        return CheckResult(
            "printer_fit", CheckStatus.SKIP,
            {"required": False}, {},
            "No printer_profile_id set; check skipped.",
        )
    if not cfg.require_printer_fit:
        return CheckResult(
            "printer_fit", CheckStatus.SKIP,
            {"required": False, "printer_profile_id": cfg.printer_profile_id},
            {}, "Printer-specific fit check disabled.",
        )

    # Local import to keep the truth_gate -> printers dependency optional
    # for tests that only validate generic geometry.
    from hermes3d.core.printers import get_profile, fits_bed

    profile = get_profile(cfg.printer_profile_id)
    extents = tuple(float(e) for e in mesh.extents)

    # For circular beds, compute the actual minimum-enclosing-circle radius
    # in xy when the mesh is centered on its xy bbox center (printers center
    # the print on the bed before slicing).
    xy = mesh.vertices[:, :2].astype(float)
    if xy.size:
        xy_center = (xy.min(axis=0) + xy.max(axis=0)) / 2.0
        xy_radius = float(np.max(np.linalg.norm(xy - xy_center, axis=1)))
    else:
        xy_radius = 0.0

    ok, msg = fits_bed(profile, extents, xy_radius)

    bed_descr: dict[str, Any] = {"kind": profile.bed.kind}
    if profile.bed.kind == "rectangular":
        bed_descr["x_mm"] = profile.bed.x_mm
        bed_descr["y_mm"] = profile.bed.y_mm
    else:
        bed_descr["diameter_mm"] = profile.bed.diameter_mm
    bed_descr["z_height_mm"] = profile.z_height_mm

    return CheckResult(
        name="printer_fit",
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        threshold={
            "printer_profile_id": profile.profile_id,
            "manufacturer": profile.manufacturer,
            "model": profile.model,
            "kinematics": profile.kinematics.value,
            "bed": bed_descr,
            "firmware": dataclasses.asdict(profile.firmware),
        },
        measured={
            "extents_mm": list(extents),
            "xy_radius_mm": round(xy_radius, 3),
        },
        message=msg,
    )


def _check_volume(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_minimum_volume:
        return CheckResult(
            "minimum_volume", CheckStatus.SKIP,
            {"required": False}, {}, "Minimum volume check skipped.",
        )
    vol = float(abs(mesh.volume))
    ok = vol >= cfg.min_volume_mm3
    return CheckResult(
        name="minimum_volume",
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        threshold={"min_volume_mm3": cfg.min_volume_mm3},
        measured={"volume_mm3": vol},
        message=f"Volume {vol:.1f} mm³ meets minimum." if ok else
                f"Volume {vol:.1f} mm³ below minimum {cfg.min_volume_mm3} mm³.",
    )


def _estimate_min_wall_thickness(mesh: trimesh.Trimesh, samples: int) -> tuple[float, int]:
    """Estimate minimum wall thickness via internal-direction ray casting.

    Method:
      1. Sample N points uniformly on the surface.
      2. From each point, fire a ray INWARD (along -normal).
      3. The first hit on the back wall gives the local thickness.
      4. Filter results so we only count hits that represent a TRUE wall:
         the hit-face normal must be roughly antiparallel to the sample
         normal (dot product <= ANTIPARALLEL_THRESHOLD). This rejects
         corner / knife-edge artefacts where the ray glances onto a
         perpendicular face — a well-known geometric edge case where
         "thickness" is mathematically near-zero but is not a printability
         concern (the rim is a sharp corner, not a thin shell).

    Numerical notes:
      - Epsilon for the ray-origin nudge is scaled to the mesh's extent so
        sub-mm meshes don't get over-nudged and metre-scale meshes don't
        get under-nudged.
      - Hits closer than ``4*epsilon`` are discarded as same-face contacts
        (a known artefact of dense triangulations on flat walls).
      - The antiparallel filter is the standard robustness fix for
        ray-cast wall-thickness estimators (see e.g. Shape Diameter
        Function literature, Shapira/Tal 2008).

    Returns (min_thickness_mm, hit_count) where hit_count counts valid,
    filtered hits only.
    """
    # Hits whose face-normals deviate by more than this from antiparallel
    # are rejected as corner/glancing artefacts. cos(135°) = -0.707, i.e.
    # we require the hit face to "face back" within 45° of the inverse
    # sample direction. This correctly catches thin parallel walls and
    # rejects perpendicular-corner knife edges.
    ANTIPARALLEL_THRESHOLD = -0.5  # cos(120°)

    samples = max(int(samples), 50)
    points, face_ids = trimesh.sample.sample_surface_even(mesh, samples)
    if len(points) == 0:
        points, face_ids = trimesh.sample.sample_surface(mesh, samples)
    sample_normals = mesh.face_normals[face_ids]

    # Scale the epsilon to the mesh diagonal — printable parts are typically
    # 10–300 mm so an epsilon of ~1e-4 of the diagonal is safe.
    diagonal = float(np.linalg.norm(mesh.extents))
    epsilon = max(diagonal * 1e-4, 1e-4)

    origins = points - sample_normals * epsilon
    directions = -sample_normals

    hits_loc, ray_idx, hit_face_idx = mesh.ray.intersects_location(
        ray_origins=origins,
        ray_directions=directions,
        multiple_hits=False,
    )
    if len(hits_loc) == 0:
        return float("inf"), 0

    distances = np.linalg.norm(hits_loc - origins[ray_idx], axis=1)

    # Filter 1: discard same-face / numerical-jitter hits.
    valid_mask = distances > 4 * epsilon

    # Filter 2: require hit-face normal to be roughly antiparallel to the
    # sample normal. This is the corner/knife-edge robustness filter.
    hit_normals = mesh.face_normals[hit_face_idx]
    sample_normals_for_hits = sample_normals[ray_idx]
    # Dot product per ray: sample_normal · hit_normal. For two parallel
    # walls the normals point in OPPOSITE directions, giving dot ≈ -1.
    # For a knife edge (perpendicular hit face) the dot is ≈ 0.
    dots = np.einsum("ij,ij->i", sample_normals_for_hits, hit_normals)
    valid_mask = valid_mask & (dots <= ANTIPARALLEL_THRESHOLD)

    distances = distances[valid_mask]
    if distances.size == 0:
        return float("inf"), 0
    return float(distances.min()), int(distances.size)


def _check_thickness(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_thickness:
        return CheckResult(
            "wall_thickness", CheckStatus.SKIP,
            {"required": False}, {}, "Thickness check skipped.",
        )
    try:
        min_t, hits = _estimate_min_wall_thickness(mesh, cfg.thickness_sample_count)
    except Exception as exc:  # noqa: BLE001 — we want to record the failure
        return CheckResult(
            name="wall_thickness",
            status=CheckStatus.ERROR,
            threshold={"min_mm": cfg.min_wall_thickness_mm},
            measured={"error": str(exc)},
            message=f"Thickness check raised {type(exc).__name__}: {exc}",
        )

    if hits == 0:
        return CheckResult(
            name="wall_thickness",
            status=CheckStatus.ERROR,
            threshold={"min_mm": cfg.min_wall_thickness_mm},
            measured={"hits": 0},
            message="No internal ray hits — mesh may be a pure shell or too small.",
        )
    ok = min_t >= cfg.min_wall_thickness_mm
    return CheckResult(
        name="wall_thickness",
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        threshold={"min_mm": cfg.min_wall_thickness_mm},
        measured={"min_mm": min_t, "samples_hit": hits},
        message=f"Min wall thickness {min_t:.3f} mm." if ok else
                f"Min wall thickness {min_t:.3f} mm < required {cfg.min_wall_thickness_mm} mm.",
    )


def _check_self_intersection(mesh: trimesh.Trimesh, cfg: TruthGateConfig) -> CheckResult:
    if not cfg.require_no_self_intersection:
        return CheckResult(
            "self_intersection", CheckStatus.SKIP,
            {"required": False}, {}, "Self-intersection check skipped.",
        )
    # Use trimesh.repair detection of broken faces as a lower-bound proxy;
    # a fully manifold + watertight + winding-consistent mesh has zero by
    # construction. We surface the count even when zero so the proof has
    # the actual measurement.
    broken = trimesh.repair.broken_faces(mesh, color=None)
    broken_count = int(len(broken)) if broken is not None else 0
    ratio = broken_count / max(len(mesh.faces), 1)
    ok = ratio <= cfg.max_self_intersection_ratio
    return CheckResult(
        name="self_intersection",
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        threshold={"max_ratio": cfg.max_self_intersection_ratio},
        measured={
            "broken_face_count": broken_count,
            "total_faces": int(len(mesh.faces)),
            "ratio": ratio,
        },
        message=f"Broken faces {broken_count}/{len(mesh.faces)}" + (
            " within tolerance." if ok else " exceed tolerance."
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


CHECKS: tuple = (
    _check_watertight,
    _check_manifold,
    _check_normals,
    _check_bed_fit,
    _check_printer_fit,
    _check_volume,
    _check_thickness,
    _check_self_intersection,
)


def run_truth_gate(
    mesh_path: str | Path,
    config: TruthGateConfig | None = None,
) -> TruthGateReport:
    """Run all checks and return a strict report.

    Raises:
        FileNotFoundError: if the mesh path does not exist.
        ValueError / TypeError: if the file cannot be parsed as a mesh.
    """
    cfg = config or TruthGateConfig()
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh not found: {mesh_path}")

    started = time.monotonic()
    mesh = _load_mesh(mesh_path)
    mesh_sha = _sha256_file(mesh_path)

    results: list[CheckResult] = []
    for check_fn in CHECKS:
        try:
            results.append(check_fn(mesh, cfg))
        except Exception as exc:  # noqa: BLE001
            results.append(CheckResult(
                name=check_fn.__name__.lstrip("_check_"),
                status=CheckStatus.ERROR,
                threshold={},
                measured={"error_type": type(exc).__name__, "error": str(exc)},
                message=f"Check raised exception: {exc}",
            ))

    statuses = {r.status for r in results}
    if CheckStatus.FAIL in statuses or CheckStatus.ERROR in statuses:
        overall = CheckStatus.FAIL
    elif statuses == {CheckStatus.SKIP}:
        overall = CheckStatus.SKIP
    else:
        overall = CheckStatus.PASS

    return TruthGateReport(
        schema_version=CURRENT_SCHEMA_VERSION,
        overall_status=overall,
        mesh_path=str(mesh_path.resolve()),
        mesh_sha256=mesh_sha,
        config=cfg.as_dict(),
        checks=results,
        duration_seconds=round(time.monotonic() - started, 4),
        timestamp_unix=time.time(),
    )


__all__ = [
    "CHECKS",
    "CURRENT_SCHEMA_VERSION",
    "CheckResult",
    "CheckStatus",
    "TruthGateConfig",
    "TruthGateReport",
    "run_truth_gate",
]
