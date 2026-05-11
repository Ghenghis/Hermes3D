"""Blender Cycles CUDA render script for W18-A20.

Invoked by an external orchestrator as:

    blender --background --python this_script.py -- \
        --stl <path-to-stl> --out <path-to-png>

The script:
  - Imports the STL via Blender's mesh.stl_import operator.
  - Configures Cycles for CUDA GPU rendering.
  - Auto-frames camera and adds a 3-light setup.
  - Renders a small thumbnail (640x480, 16 samples) for proof.
  - Prints render time as the last line so the parent script can parse it.

Honest fallback: if Cycles cannot find any CUDA device, the script
**aborts with a clear error** rather than silently rendering on CPU. The
orchestrator must detect this and set ``gpu_used=False`` in the proof.

This file runs inside Blender's bundled Python — DO NOT import Hermes3D
modules here.
"""

import argparse
import math
import sys
import time
from pathlib import Path

import bpy  # type: ignore[import-not-found]


def _parse_argv() -> argparse.Namespace:
    # Blender ignores everything before ``--``; we slice manually so this works
    # both inside and outside Blender.
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    else:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--stl", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    return parser.parse_args(argv)


def _clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _import_stl(stl_path: Path) -> bpy.types.Object:
    # Blender 4.x/5.x uses operator name "wm.stl_import" or "import_mesh.stl"
    # depending on add-on availability. Try both.
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(stl_path))
    else:
        bpy.ops.import_mesh.stl(filepath=str(stl_path))
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if not objs:
        raise RuntimeError("STL import produced no mesh objects.")
    obj = objs[0]
    obj.rotation_euler = (math.radians(75), 0, math.radians(40))
    return obj


def _add_lights() -> None:
    # 3-light setup
    bpy.ops.object.light_add(type="AREA", location=(2, -2, 3))
    key = bpy.context.object
    key.data.energy = 800
    key.data.size = 2

    bpy.ops.object.light_add(type="AREA", location=(-3, -1, 2))
    fill = bpy.context.object
    fill.data.energy = 300
    fill.data.size = 3

    bpy.ops.object.light_add(type="AREA", location=(0, 3, 4))
    rim = bpy.context.object
    rim.data.energy = 500
    rim.data.size = 2


def _add_camera(target: bpy.types.Object) -> None:
    bpy.ops.object.camera_add(location=(0.4, -0.35, 0.3))
    cam = bpy.context.object
    cam.data.lens = 35
    # Point at the object centre
    tx, ty, tz = target.location
    cam_loc = cam.location
    direction = (tx - cam_loc.x, ty - cam_loc.y, tz - cam_loc.z)
    import mathutils  # type: ignore[import-not-found]

    rot_quat = mathutils.Vector(direction).to_track_quat("-Z", "Y")
    cam.rotation_euler = rot_quat.to_euler()
    bpy.context.scene.camera = cam


def _configure_cycles_cuda(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True

    prefs = bpy.context.preferences.addons["cycles"].preferences
    # Available types in Blender 4.x/5.x: NONE, CUDA, OPTIX, HIP, METAL, ONEAPI
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()

    cuda_devices = [d for d in prefs.devices if d.type == "CUDA"]
    if not cuda_devices:
        raise RuntimeError(
            "Cycles found NO CUDA devices. Refusing to silently fall back "
            "to CPU. Set gpu_used=False in the proof if this is honest."
        )
    for device in prefs.devices:
        device.use = device.type == "CUDA"
    scene.cycles.device = "GPU"

    enabled = [(d.name, d.type) for d in prefs.devices if d.use]
    print(f"W18A20-CYCLES-DEVICES: {enabled}", flush=True)


def main() -> None:
    args = _parse_argv()
    stl_path = Path(args.stl).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    _clear_scene()
    obj = _import_stl(stl_path)

    # Normalise scale (organizer is ~180 mm wide; we want it ~0.2 m in render space)
    max_dim = max(obj.dimensions)
    if max_dim > 0:
        scale = 0.2 / max_dim
        obj.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    _add_lights()
    _add_camera(obj)
    _configure_cycles_cuda(args.samples)

    scene = bpy.context.scene
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out_path)

    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    dt = time.perf_counter() - t0

    # Final line — parent script parses this.
    print(f"W18A20-RENDER-OK out={out_path} seconds={dt:.4f}", flush=True)


if __name__ == "__main__":
    main()
