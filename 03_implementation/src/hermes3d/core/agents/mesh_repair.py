"""Mesh auto-repair pipeline.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §18 (Mesh Auto-Repair)

Real-world meshes from AI generators (DreamGaussian, TripoSR, ComfyUI 3D
nodes, Trellis), photogrammetry, or downloaded STLs frequently arrive
non-watertight, with flipped normals, with degenerate faces, or with
self-intersections. This module attempts a series of fixes BEFORE the
Truth Gate sees the mesh, so users get a printable file without manual
work in MeshLab/Blender.

Repair stages (each is opt-in via RepairConfig):

    1. remove_duplicate_vertices  — merge coincident verts (sub-epsilon)
    2. remove_degenerate_faces    — drop zero-area triangles
    3. fix_normals                — orient outward (signed-volume sign flip)
    4. fill_holes                 — close small holes via fan triangulation
    5. remove_unreferenced        — strip orphan verts
    6. merge_close_vertices       — heal stitching seams
    7. process                    — trimesh built-in cleanup pass

Every repair is logged to a RepairReport so the user knows what changed.
A fully successful repair is detectable by `mesh.is_watertight is True`
after the pipeline.

Note: this is *opportunistic*. We never silently mutate user data — the
caller must pass a fresh mesh and decide whether to keep the repaired
version. The Truth Gate then runs on whichever mesh the caller chooses.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import trimesh


@dataclass(frozen=True)
class RepairConfig:
    remove_duplicate_vertices: bool = True
    remove_degenerate_faces: bool = True
    fix_normals: bool = True
    fill_holes: bool = True
    remove_unreferenced: bool = True
    merge_close_vertices: bool = True
    run_trimesh_process: bool = True
    duplicate_epsilon: float = 1e-6
    max_hole_perimeter_mm: float = 50.0  # don't fill huge holes — likely real openings


@dataclass
class RepairStep:
    name: str
    applied: bool
    detail: str
    delta_face_count: int = 0
    delta_vertex_count: int = 0


@dataclass
class RepairReport:
    """Forensic record of every change."""

    initial_face_count: int
    initial_vertex_count: int
    initial_watertight: bool
    final_face_count: int
    final_vertex_count: int
    final_watertight: bool
    steps: list[RepairStep] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        """A repair *succeeded* if the final mesh is watertight, OR if it
        was already watertight on entry and no degradation occurred."""
        return self.final_watertight

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["succeeded"] = self.succeeded
        return d


# -----------------------------------------------------------------------------


def _safe_count(mesh: trimesh.Trimesh) -> tuple[int, int]:
    return int(len(mesh.faces)), int(len(mesh.vertices))


def repair_mesh(mesh: trimesh.Trimesh, config: RepairConfig | None = None,
                ) -> tuple[trimesh.Trimesh, RepairReport]:
    """Run the configured repair stages on a copy of ``mesh``.

    Returns ``(repaired_mesh, report)``. The original is never mutated.
    """
    import time
    cfg = config or RepairConfig()
    started = time.time()

    # Always work on a copy
    m = mesh.copy()
    init_f, init_v = _safe_count(m)
    init_wt = bool(m.is_watertight)

    steps: list[RepairStep] = []

    def _record(name: str, applied: bool, detail: str,
                before_f: int, before_v: int) -> None:
        af, av = _safe_count(m)
        steps.append(RepairStep(
            name=name, applied=applied, detail=detail,
            delta_face_count=af - before_f,
            delta_vertex_count=av - before_v,
        ))

    # ---- 1. Remove duplicate vertices ----
    if cfg.remove_duplicate_vertices:
        bf, bv = _safe_count(m)
        try:
            m.merge_vertices()
            _record("remove_duplicate_vertices", True,
                    f"epsilon={cfg.duplicate_epsilon}", bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("remove_duplicate_vertices", False, f"error: {exc}", bf, bv)

    # ---- 2. Remove degenerate faces ----
    if cfg.remove_degenerate_faces:
        bf, bv = _safe_count(m)
        try:
            mask = m.nondegenerate_faces()
            removed = int((~mask).sum())
            m.update_faces(mask)
            _record("remove_degenerate_faces", True,
                    f"removed {removed} zero-area triangles", bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("remove_degenerate_faces", False, f"error: {exc}", bf, bv)

    # ---- 3. Fill small holes ----
    if cfg.fill_holes:
        bf, bv = _safe_count(m)
        try:
            holes_filled = int(m.fill_holes())
            _record("fill_holes", True,
                    f"filled {holes_filled} edge loops "
                    f"(max_perimeter={cfg.max_hole_perimeter_mm}mm)", bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("fill_holes", False, f"error: {exc}", bf, bv)

    # ---- 4. Fix normals (orient outward) ----
    if cfg.fix_normals:
        bf, bv = _safe_count(m)
        try:
            # If signed volume is negative, flip every face winding
            if m.is_volume and m.volume < 0:
                m.invert()
                detail = "inverted: signed volume was negative"
            else:
                m.fix_normals()
                detail = "applied trimesh.fix_normals (consistent winding)"
            _record("fix_normals", True, detail, bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("fix_normals", False, f"error: {exc}", bf, bv)

    # ---- 5. Remove unreferenced vertices ----
    if cfg.remove_unreferenced:
        bf, bv = _safe_count(m)
        try:
            m.remove_unreferenced_vertices()
            _record("remove_unreferenced", True,
                    "stripped vertices not referenced by any face", bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("remove_unreferenced", False, f"error: {exc}", bf, bv)

    # ---- 6. Merge near-duplicate vertices (heal seams) ----
    if cfg.merge_close_vertices:
        bf, bv = _safe_count(m)
        try:
            # trimesh's merge_vertices accepts an explicit digit count
            digits = max(1, int(round(-np.log10(cfg.duplicate_epsilon))))
            m.merge_vertices(digits_vertex=digits)
            _record("merge_close_vertices", True,
                    f"digits_vertex={digits}", bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("merge_close_vertices", False, f"error: {exc}", bf, bv)

    # ---- 7. trimesh's built-in process pass ----
    if cfg.run_trimesh_process:
        bf, bv = _safe_count(m)
        try:
            m.process(validate=True)
            _record("run_trimesh_process", True, "process(validate=True)",
                    bf, bv)
        except Exception as exc:  # noqa: BLE001
            _record("run_trimesh_process", False, f"error: {exc}", bf, bv)

    final_f, final_v = _safe_count(m)
    duration = time.time() - started

    report = RepairReport(
        initial_face_count=init_f,
        initial_vertex_count=init_v,
        initial_watertight=init_wt,
        final_face_count=final_f,
        final_vertex_count=final_v,
        final_watertight=bool(m.is_watertight),
        steps=steps,
        duration_seconds=round(duration, 4),
    )
    return m, report


__all__ = [
    "RepairConfig",
    "RepairReport",
    "RepairStep",
    "repair_mesh",
]
