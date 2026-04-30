"""Mesh geometric analyzer.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §40 (Mesh Analyzer)

Provides rich geometric metrics that an agentic system can reason
about when picking slicing parameters or supports:

  - overhang_area_mm2(mesh, threshold_deg)   — sum of face areas with
                                                 a normal angle from +Z
                                                 exceeding ``threshold``
  - bridge_edges(mesh, max_span_mm)          — edges that span gaps
                                                 (rough heuristic)
  - support_volume_estimate(mesh, threshold) — *very* rough volume of
                                                 a support cone needed
                                                 under each overhang
                                                 face
  - first_layer_area_mm2(mesh)               — bed contact area for
                                                 warping risk
  - aspect_ratios(mesh)                      — height / shortest XY ext
  - thin_walls_estimate(mesh, min_thickness) — heuristic count of
                                                 too-thin features
                                                 (uses bbox slab test)
  - center_of_mass_offset(mesh)              — XY offset of COM from
                                                 bed-projection centroid

These are *heuristics*. They aren't a substitute for the slicer's
support generator — they're for high-level decisions like "this mesh
has a lot of overhangs, prefer a printer with good cooling" or "this
mesh is tall and thin, prefer a CoreXY for stability."
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import trimesh


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_OVERHANG_THRESHOLD_DEG = 50.0  # Klipper's typical "needs support" angle
THIN_WALL_DEFAULT_MIN_MM = 0.8  # 2 perimeters at 0.4mm nozzle
BRIDGE_MAX_SPAN_DEFAULT_MM = 25.0


@dataclass
class MeshAnalysis:
    """Geometric report for an STL/OBJ mesh."""

    bbox_mm: tuple[float, float, float]
    volume_mm3: float
    surface_area_mm2: float
    triangle_count: int
    is_watertight: bool
    is_volume: bool
    overhang_area_mm2: float = 0.0
    overhang_pct: float = 0.0
    overhang_threshold_deg: float = DEFAULT_OVERHANG_THRESHOLD_DEG
    first_layer_area_mm2: float = 0.0
    support_volume_estimate_mm3: float = 0.0
    bridge_count_estimate: int = 0
    longest_bridge_mm: float = 0.0
    height_to_min_xy_aspect: float = 0.0  # tall-thin heuristic
    com_xy_offset_mm: float = 0.0
    thin_wall_face_count: int = 0
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# =============================================================================
# Helpers
# =============================================================================


def _ensure_z_up(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Translate mesh so its lowest Z = 0 (resting on bed)."""
    out = mesh.copy()
    minz = float(out.vertices[:, 2].min())
    out.apply_translation((0, 0, -minz))
    return out


def _overhang_face_mask(
    mesh: trimesh.Trimesh, threshold_deg: float, bed_mask: np.ndarray | None = None
) -> np.ndarray:
    """Faces that need support material.

    Definition: a face needs support when its overhang angle from the
    build plate exceeds ``threshold_deg``. Geometrically, that means the
    face normal points down past the threshold:

        nz < -sin(threshold_deg)

    A vertical wall (nz = 0) needs no support. A 45° outward-leaning
    surface (nz ≈ -0.707) needs support if threshold ≤ 45°.

    Bed-contact faces are explicitly excluded — they're touching the
    build plate, not overhanging anything.
    """
    threshold_rad = math.radians(threshold_deg)
    nz_cutoff = -math.sin(threshold_rad)
    nz = mesh.face_normals[:, 2]
    overhang = nz < nz_cutoff
    if bed_mask is not None:
        overhang &= ~bed_mask
    return overhang


def _bed_contact_mask(mesh: trimesh.Trimesh, z_tolerance_mm: float = 0.5) -> np.ndarray:
    """Faces whose centroid Z is within ``z_tolerance_mm`` of the lowest
    point AND whose normal points down."""
    centroids = mesh.triangles.mean(axis=1)
    minz = float(mesh.vertices[:, 2].min())
    return ((centroids[:, 2] - minz) < z_tolerance_mm) & (mesh.face_normals[:, 2] < -0.95)


# =============================================================================
# Public API
# =============================================================================


def analyze_mesh(
    mesh: trimesh.Trimesh,
    *,
    overhang_threshold_deg: float = DEFAULT_OVERHANG_THRESHOLD_DEG,
    thin_wall_min_mm: float = THIN_WALL_DEFAULT_MIN_MM,
) -> MeshAnalysis:
    """Return a comprehensive geometric report on the mesh.

    Mesh is normalized to bed (lowest Z = 0). Original is not mutated.
    """
    m = _ensure_z_up(mesh)
    extents = tuple(float(e) for e in m.extents)

    # Areas — order matters: compute bed mask first, then exclude it
    # from the overhang set.
    bed_mask = _bed_contact_mask(m)
    overhang_mask = _overhang_face_mask(m, overhang_threshold_deg, bed_mask)

    areas = m.area_faces
    total_area = float(areas.sum())
    overhang_area = float(areas[overhang_mask].sum())
    overhang_pct = overhang_area / total_area if total_area else 0.0
    bed_area = float(areas[bed_mask].sum())

    # Support volume estimate: each overhang triangle drops a cone to
    # the bed. We approximate by area * height / 3 (the cone-volume
    # formula projected straight down). It's crude but useful.
    centroids = m.triangles.mean(axis=1)
    support_vol = 0.0
    if overhang_mask.any():
        heights = centroids[overhang_mask, 2]
        ohang_areas = areas[overhang_mask]
        # cone V = A*h/3
        support_vol = float((ohang_areas * heights / 3.0).sum())

    # Bridge estimate: a "bridge" is an overhang face with at least one
    # XY-edge that spans more than the configured cap. Bed-contact is
    # already excluded from overhang_mask above.
    bridge_count = 0
    longest_bridge = 0.0
    if overhang_mask.any():
        tris = m.triangles[overhang_mask]
        edges_xy = np.stack(
            [
                tris[:, 0, :2] - tris[:, 1, :2],
                tris[:, 1, :2] - tris[:, 2, :2],
                tris[:, 2, :2] - tris[:, 0, :2],
            ],
            axis=1,
        )
        edge_lengths = np.linalg.norm(edges_xy, axis=2)
        max_edge_per_tri = edge_lengths.max(axis=1)
        bridges = max_edge_per_tri > BRIDGE_MAX_SPAN_DEFAULT_MM
        bridge_count = int(bridges.sum())
        if bridges.any():
            longest_bridge = float(max_edge_per_tri[bridges].max())

    # Tall-thin heuristic
    z = extents[2]
    min_xy = min(extents[0], extents[1])
    aspect = z / max(0.001, min_xy)

    # COM offset from bed-projection centroid
    com_xy_offset = 0.0
    if m.is_volume:
        com = m.center_mass
        bed_proj_centroid = m.vertices[:, :2].mean(axis=0)
        com_xy_offset = float(np.linalg.norm(com[:2] - bed_proj_centroid))

    # Thin-wall face count: faces whose smallest edge is < min_thickness.
    # This is a lower bound on thin features.
    edges = np.stack(
        [
            m.triangles[:, 0] - m.triangles[:, 1],
            m.triangles[:, 1] - m.triangles[:, 2],
            m.triangles[:, 2] - m.triangles[:, 0],
        ],
        axis=1,
    )
    edge_norms = np.linalg.norm(edges, axis=2)
    min_edge_per_tri = edge_norms.min(axis=1)
    thin = min_edge_per_tri < thin_wall_min_mm
    thin_wall_count = int(thin.sum())

    # Risk flags
    flags: list[str] = []
    if overhang_pct > 0.30:
        flags.append(
            f"high-overhang: {overhang_pct:.0%} of faces overhanging "
            f"(threshold {overhang_threshold_deg}°)"
        )
    elif overhang_pct > 0.15:
        flags.append(f"moderate-overhang: {overhang_pct:.0%} of faces overhanging")
    if aspect > 4.0:
        flags.append(
            f"tall-thin: H/min(XY) ratio = {aspect:.1f} — risk of toppling on cartesian printers"
        )
    if bed_area < max(50.0, 0.05 * total_area):
        flags.append(
            f"low-bed-contact: only {bed_area:.0f}mm² touching the bed — "
            f"adhesion failure is likely, consider a brim or different orientation"
        )
    if com_xy_offset > min(extents[0], extents[1]) * 0.4:
        flags.append(
            f"off-center-mass: COM is {com_xy_offset:.1f}mm from "
            f"bed-projection centroid — print may tip"
        )
    if longest_bridge > BRIDGE_MAX_SPAN_DEFAULT_MM:
        flags.append(f"long-bridge: longest unsupported span ~{longest_bridge:.1f}mm")
    if thin_wall_count > 50:
        flags.append(
            f"thin-features: {thin_wall_count} triangles with edges < {thin_wall_min_mm}mm"
        )

    return MeshAnalysis(
        bbox_mm=extents,
        volume_mm3=float(m.volume) if m.is_volume else 0.0,
        surface_area_mm2=total_area,
        triangle_count=int(len(m.faces)),
        is_watertight=bool(m.is_watertight),
        is_volume=bool(m.is_volume),
        overhang_area_mm2=overhang_area,
        overhang_pct=round(overhang_pct, 4),
        overhang_threshold_deg=overhang_threshold_deg,
        first_layer_area_mm2=bed_area,
        support_volume_estimate_mm3=round(support_vol, 2),
        bridge_count_estimate=bridge_count,
        longest_bridge_mm=round(longest_bridge, 2),
        height_to_min_xy_aspect=round(aspect, 2),
        com_xy_offset_mm=round(com_xy_offset, 2),
        thin_wall_face_count=thin_wall_count,
        risk_flags=flags,
    )


def analyze_mesh_file(path: str) -> MeshAnalysis:
    """Convenience wrapper: load and analyze."""
    return analyze_mesh(trimesh.load_mesh(path, force="mesh"))


__all__ = [
    "BRIDGE_MAX_SPAN_DEFAULT_MM",
    "DEFAULT_OVERHANG_THRESHOLD_DEG",
    "MeshAnalysis",
    "THIN_WALL_DEFAULT_MIN_MM",
    "analyze_mesh",
    "analyze_mesh_file",
]
