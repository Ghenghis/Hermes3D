"""Visual evidence harness: render a mesh from 6 fixed angles to PNG.

This is part of the Visual Gate (gate layer F in GATES.md). Rendered images
are recorded in the proof envelope and (separately) compared to golden
references in the visual conformance test suite.

Backend: matplotlib + numpy. Pure CPU. No OpenGL / no display required.
We project triangles onto the camera plane, depth-sort them, and shade by
the dot product of the face normal with the light direction. This is
deterministic across platforms (modulo float-rounding of `~1e-15`), which
is critical for the visual gate to be reproducible.

Output: 800x800 PNG per view, written to the requested directory.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — must be set BEFORE pyplot import
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ViewSpec:
    """One named camera view."""
    name: str
    azimuth_deg: float   # rotation around +Z (yaw), 0 = looking down -Y
    elevation_deg: float  # tilt above horizon (pitch)


# The canonical 6-view set used everywhere in the proof system.
# Order matters: it's part of the schema. Do NOT reorder without bumping
# the visual-evidence schema version in proof_envelope.py.
CANONICAL_VIEWS: tuple[ViewSpec, ...] = (
    ViewSpec("front",     azimuth_deg=0.0,    elevation_deg=10.0),
    ViewSpec("back",      azimuth_deg=180.0,  elevation_deg=10.0),
    ViewSpec("left",      azimuth_deg=270.0,  elevation_deg=10.0),
    ViewSpec("right",     azimuth_deg=90.0,   elevation_deg=10.0),
    ViewSpec("top",       azimuth_deg=0.0,    elevation_deg=89.0),
    ViewSpec("isometric", azimuth_deg=45.0,   elevation_deg=30.0),
)

IMAGE_SIZE_PX = 800
DPI = 100


def _camera_matrix(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    """3x3 rotation that maps world coords to camera-aligned coords.

    Camera looks along +Y (after rotation), with +Z up and +X right.
    """
    az = np.radians(azimuth_deg)
    el = np.radians(elevation_deg)
    # Yaw around Z
    Rz = np.array([
        [np.cos(az), -np.sin(az), 0.0],
        [np.sin(az),  np.cos(az), 0.0],
        [0.0,         0.0,        1.0],
    ])
    # Pitch around X (after yaw)
    Rx = np.array([
        [1.0, 0.0,           0.0],
        [0.0, np.cos(el),    np.sin(el)],
        [0.0, -np.sin(el),   np.cos(el)],
    ])
    return Rx @ Rz


def render_view(
    mesh: trimesh.Trimesh,
    view: ViewSpec,
    output_path: str | Path,
    *,
    background: tuple[float, float, float] = (0.96, 0.96, 0.97),
    base_color: tuple[float, float, float] = (0.32, 0.55, 0.78),
    edge_color: tuple[float, float, float] = (0.10, 0.10, 0.12),
    edge_alpha: float = 0.25,
) -> Path:
    """Render one ViewSpec of `mesh` and write it to `output_path`.

    Returns the resolved Path written.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    R = _camera_matrix(view.azimuth_deg, view.elevation_deg)

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)

    # Center the mesh so the rendering frame doesn't depend on world origin.
    centroid = verts.mean(axis=0)
    centered = verts - centroid

    # Camera-space coordinates: x right, y depth, z up.
    cam = centered @ R.T

    # Project: orthographic. Use (x, z) as image-plane, y as depth.
    tri_pts = cam[faces]                         # (F, 3, 3)
    tri_2d = tri_pts[:, :, [0, 2]]               # (F, 3, 2)
    tri_depth = tri_pts[:, :, 1].mean(axis=1)    # (F,)

    # Lighting: directional, head-on (+y axis = into camera).
    light_dir_world = R.T @ np.array([0.0, -1.0, 0.5])
    light_dir_world /= max(np.linalg.norm(light_dir_world), 1e-12)
    intensity = (normals @ light_dir_world).clip(0.0, 1.0)
    # Wrap with ambient term so back-faces aren't pure black.
    shade = 0.30 + 0.70 * intensity              # (F,)

    base = np.array(base_color, dtype=np.float64)
    face_colors = np.clip(shade[:, None] * base[None, :], 0.0, 1.0)

    # Painter's algorithm: draw far triangles first.
    order = np.argsort(-tri_depth)
    polys = tri_2d[order]
    fcs = face_colors[order]

    fig = plt.figure(figsize=(IMAGE_SIZE_PX / DPI, IMAGE_SIZE_PX / DPI), dpi=DPI)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0))
    ax.set_facecolor(background)
    ax.set_aspect("equal")
    ax.set_axis_off()

    coll = PolyCollection(
        polys,
        facecolors=fcs,
        edgecolors=(edge_color[0], edge_color[1], edge_color[2], edge_alpha),
        linewidths=0.25,
        antialiaseds=True,
    )
    ax.add_collection(coll)

    # Tight bounds with a small margin.
    xs = polys[..., 0]
    zs = polys[..., 1]
    pad = 0.04 * max(float(np.ptp(xs)), float(np.ptp(zs)), 1.0)
    ax.set_xlim(float(xs.min() - pad), float(xs.max() + pad))
    ax.set_ylim(float(zs.min() - pad), float(zs.max() + pad))

    # Title in upper-left so the view is identifiable.
    ax.text(
        0.02, 0.97, f"{view.name}  az={view.azimuth_deg:g}°  el={view.elevation_deg:g}°",
        transform=ax.transAxes, fontsize=10, color=(0.10, 0.10, 0.12),
        verticalalignment="top",
        bbox={"facecolor": "white", "alpha": 0.7, "pad": 3, "edgecolor": "none"},
    )

    fig.savefig(out, dpi=DPI, facecolor=background)
    plt.close(fig)
    return out.resolve()


def render_all_views(
    mesh: trimesh.Trimesh | str | Path,
    output_dir: str | Path,
    *,
    name_prefix: str = "view",
    views: tuple[ViewSpec, ...] = CANONICAL_VIEWS,
) -> list[tuple[str, Path]]:
    """Render every ViewSpec in `views` and return [(view_name, png_path), ...].

    Suitable for direct passing to ``write_proof(..., visual_evidence_paths=...)``.
    """
    if isinstance(mesh, (str, Path)):
        m = trimesh.load(str(mesh), force="mesh")
    else:
        m = mesh

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[str, Path]] = []
    for view in views:
        png = out_dir / f"{name_prefix}_{view.name}.png"
        rendered = render_view(m, view, png)
        results.append((view.name, rendered))
    return results


__all__ = [
    "CANONICAL_VIEWS",
    "ViewSpec",
    "render_all_views",
    "render_view",
]
