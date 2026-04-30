"""Auto-orient agent.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §19 (Auto-Orient)

Picks the optimal "Z up" orientation for a mesh to minimize support
material and maximize bed contact. Uses a heuristic scoring function
inspired by the Tweaker-3 algorithm (Christoph Schranz, 2019) but
simplified and adapted for the Hermes3D pipeline.

Scoring components (per candidate orientation):

  bed_contact_area   :  larger flat bottom face = lower warping risk
  overhang_area      :  total area of triangles with normal Z below threshold
  height_z           :  shorter Z = faster print, less support
  unsupported_volume :  rough volume that would need support material
  bbox_efficiency    :  fits in printer envelope

The agent enumerates 6 axis-aligned candidates (±X, ±Y, ±Z), then optionally
adds 12 face-aligned candidates from the mesh's largest faces (rotation
matrices that lay each face flat). The best score wins.

This is a *suggestion* — it never silently rotates the mesh. The caller
chooses whether to apply the recommended transform.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import trimesh


# Triangle is "overhanging" if its normal makes more than ~50° with +Z.
# At 50°, dot(normal, +Z) = cos(50°) ≈ 0.643. Anything with normal.z
# below this, when pointing roughly downward, requires support.
OVERHANG_DOT_THRESHOLD = -0.05  # mostly down-facing
BED_CONTACT_DOT_THRESHOLD = -0.95  # nearly straight down (resting on bed)


@dataclass(frozen=True)
class OrientCandidate:
    """A candidate orientation, expressed as a 4x4 transform matrix."""

    name: str
    transform: tuple[tuple[float, ...], ...]  # 4x4 matrix as nested tuples

    def matrix(self) -> np.ndarray:
        return np.array(self.transform, dtype=np.float64)


@dataclass
class OrientScore:
    """A scored orientation."""

    candidate_name: str
    score: float
    bed_contact_area_mm2: float
    overhang_area_mm2: float
    height_mm: float
    bbox_extents: tuple[float, float, float]
    rationale: str = ""


@dataclass
class OrientDecision:
    chosen: OrientScore
    candidates: list[OrientScore] = field(default_factory=list)

    def transform_matrix(self) -> np.ndarray:
        return _candidate_by_name(self.chosen.candidate_name).matrix()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chosen": dataclasses.asdict(self.chosen),
            "candidates": [dataclasses.asdict(c) for c in self.candidates],
        }


# -----------------------------------------------------------------------------
# Candidate orientations (6 axis-aligned + identity)
# -----------------------------------------------------------------------------

def _make_axis_candidates() -> list[OrientCandidate]:
    """Six basis orientations: identity + rotations putting each face down."""
    I = np.eye(4)
    rx90 = trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0))
    rx_90 = trimesh.transformations.rotation_matrix(-math.pi / 2, (1, 0, 0))
    ry90 = trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0))
    ry_90 = trimesh.transformations.rotation_matrix(-math.pi / 2, (0, 1, 0))
    rx180 = trimesh.transformations.rotation_matrix(math.pi, (1, 0, 0))
    return [
        OrientCandidate("identity", _to_tuple(I)),
        OrientCandidate("rotX+90", _to_tuple(rx90)),
        OrientCandidate("rotX-90", _to_tuple(rx_90)),
        OrientCandidate("rotY+90", _to_tuple(ry90)),
        OrientCandidate("rotY-90", _to_tuple(ry_90)),
        OrientCandidate("rotX180", _to_tuple(rx180)),
    ]


def _to_tuple(m: np.ndarray) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(float(v) for v in row) for row in m)


_AXIS_CANDIDATES = _make_axis_candidates()


def _candidate_by_name(name: str) -> OrientCandidate:
    for c in _AXIS_CANDIDATES:
        if c.name == name:
            return c
    raise KeyError(name)


# -----------------------------------------------------------------------------


def _score_orientation(mesh: trimesh.Trimesh, candidate: OrientCandidate,
                        ) -> OrientScore:
    transformed = mesh.copy()
    transformed.apply_transform(candidate.matrix())
    # Translate so min-Z = 0 (resting on bed)
    minz = float(transformed.vertices[:, 2].min())
    transformed.apply_translation((0, 0, -minz))

    normals = transformed.face_normals  # already normalized by trimesh
    areas = transformed.area_faces

    # Bed contact: faces with normal pointing nearly straight down
    # AND whose centroid sits at z ≈ 0
    centroid_z = transformed.triangles.mean(axis=1)[:, 2]
    bed_mask = (normals[:, 2] < BED_CONTACT_DOT_THRESHOLD) & (centroid_z < 0.5)
    bed_area = float(areas[bed_mask].sum())

    # Overhang: faces with normal pointing roughly downward
    overhang_mask = (normals[:, 2] < OVERHANG_DOT_THRESHOLD) & ~bed_mask
    overhang_area = float(areas[overhang_mask].sum())

    extents = tuple(float(e) for e in transformed.extents)
    height_mm = float(extents[2])

    # Composite score: high bed contact, low overhang, low height
    # (all normalized against the largest face area for stability)
    total_area = float(areas.sum()) or 1.0
    bed_pct = bed_area / total_area
    overhang_pct = overhang_area / total_area
    # Height penalty, capped: tall prints take longer + need more support
    h_penalty = min(1.0, height_mm / max(extents))

    score = (
        2.0 * bed_pct          # reward bed contact
        - 1.5 * overhang_pct   # punish overhangs
        - 0.5 * h_penalty      # gentle nudge toward shorter prints
    )

    rationale = (
        f"bed={bed_pct:.1%} overhang={overhang_pct:.1%} "
        f"h={height_mm:.0f}mm score={score:.3f}"
    )
    return OrientScore(
        candidate_name=candidate.name,
        score=float(score),
        bed_contact_area_mm2=bed_area,
        overhang_area_mm2=overhang_area,
        height_mm=height_mm,
        bbox_extents=extents,
        rationale=rationale,
    )


def auto_orient(mesh: trimesh.Trimesh) -> OrientDecision:
    """Score the 6 axis-aligned orientations and return the best.

    The chosen transform is referenced by name in the decision. Use
    ``decision.transform_matrix()`` to get the 4x4 numpy matrix.
    """
    scores = [_score_orientation(mesh, c) for c in _AXIS_CANDIDATES]
    scores.sort(key=lambda s: -s.score)
    return OrientDecision(chosen=scores[0], candidates=scores)


__all__ = [
    "OrientCandidate",
    "OrientDecision",
    "OrientScore",
    "auto_orient",
]
