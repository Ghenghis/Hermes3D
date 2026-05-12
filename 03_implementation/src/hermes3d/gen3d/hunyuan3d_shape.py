"""Hunyuan3D 2.1 shape runner using the local ComfyUI installation.

This module is intentionally runnable as a subprocess. Hermes3D's API process
should not import multi-GB model weights into the web server just to dispatch a
generation request.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_COMFYUI_ROOT = Path(os.environ.get("HERMES3D_COMFYUI_ROOT", r"G:\Github\ComfyUI"))
DEFAULT_MODEL_CKPT = Path(
    os.environ.get(
        "HERMES3D_HUNYUAN3D_CKPT",
        str(DEFAULT_COMFYUI_ROOT / "models" / "hunyuan3d" / "hunyuan3d-dit-v2-1" / "model.fp16.ckpt"),
    )
)
DEFAULT_CONFIG = Path(
    os.environ.get(
        "HERMES3D_HUNYUAN3D_CONFIG",
        str(DEFAULT_COMFYUI_ROOT / "models" / "hunyuan3d" / "hunyuan3d-dit-v2-1" / "config.yaml"),
    )
)
DEFAULT_WRAPPER_ROOT = Path(
    os.environ.get(
        "HERMES3D_HUNYUAN3D_WRAPPER_ROOT",
        str(DEFAULT_COMFYUI_ROOT / "custom_nodes" / "ComfyUI-Hunyuan3DWrapper"),
    )
)


def run_hunyuan3d_shape(
    *,
    input_image: Path,
    output_mesh: Path,
    proof_json: Path | None = None,
    steps: int = 30,
    guidance_scale: float = 5.0,
    octree_resolution: int = 256,
    target_size_mm: float | None = None,
    seed: int = 3201,
    device: str = "cuda",
    model_ckpt: Path = DEFAULT_MODEL_CKPT,
    config_path: Path = DEFAULT_CONFIG,
    comfyui_root: Path = DEFAULT_COMFYUI_ROOT,
    wrapper_root: Path = DEFAULT_WRAPPER_ROOT,
) -> dict[str, Any]:
    started = time.monotonic()
    evidence: dict[str, Any] = {
        "status": "started",
        "engine": "hunyuan3d-2.1-shape",
        "input_image": str(input_image),
        "output_mesh": str(output_mesh),
        "steps": steps,
        "guidance_scale": guidance_scale,
        "octree_resolution": octree_resolution,
        "target_size_mm": target_size_mm,
        "seed": seed,
        "device": device,
        "comfyui_root": str(comfyui_root),
        "wrapper_root": str(wrapper_root),
        "model_ckpt": str(model_ckpt),
        "config_path": str(config_path),
    }
    try:
        _validate_runtime_paths(
            input_image=input_image,
            model_ckpt=model_ckpt,
            config_path=config_path,
            comfyui_root=comfyui_root,
            wrapper_root=wrapper_root,
        )
        _configure_import_paths(comfyui_root=comfyui_root, wrapper_root=wrapper_root)

        import torch
        import trimesh
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
        from PIL import Image

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false.")

        image = Image.open(input_image).convert("RGBA")
        output_mesh.parent.mkdir(parents=True, exist_ok=True)
        generator = _make_generator(torch=torch, device=device, seed=seed)

        if device == "cuda":
            torch.cuda.empty_cache()
            gpu_name = torch.cuda.get_device_name(0)
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            evidence["gpu_before"] = {
                "name": gpu_name,
                "free_bytes": int(free_bytes),
                "total_bytes": int(total_bytes),
            }

        load_started = time.monotonic()
        pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_single_file(
            config_path=str(config_path),
            ckpt_path=str(model_ckpt),
            device=device,
            dtype=torch.float16,
        )
        evidence["load_duration_s"] = round(time.monotonic() - load_started, 3)

        generation_started = time.monotonic()
        outputs = pipeline(
            image=image,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
            octree_resolution=octree_resolution,
            output_type="trimesh",
            enable_pbar=True,
        )
        mesh = outputs[0]
        scale_factor = _scale_mesh_to_target_mm(mesh, target_size_mm)
        if scale_factor is not None:
            evidence["scale_factor"] = scale_factor
        mesh.export(output_mesh, file_type=_mesh_file_type(output_mesh))
        evidence["generation_duration_s"] = round(time.monotonic() - generation_started, 3)

        if device == "cuda":
            free_bytes, total_bytes = torch.cuda.mem_get_info(0)
            evidence["gpu_after"] = {
                "name": torch.cuda.get_device_name(0),
                "free_bytes": int(free_bytes),
                "total_bytes": int(total_bytes),
                "max_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
                "max_reserved_bytes": int(torch.cuda.max_memory_reserved(0)),
            }
            pipeline.to("cpu")
            del pipeline
            torch.cuda.empty_cache()

        loaded_mesh = trimesh.load(str(output_mesh), force="mesh", process=True)
        evidence.update(
            {
                "status": "completed",
                "output_exists": output_mesh.is_file(),
                "output_bytes": output_mesh.stat().st_size,
                "mesh": {
                    "vertices": int(len(loaded_mesh.vertices)),
                    "faces": int(len(loaded_mesh.faces)),
                    "is_watertight": bool(loaded_mesh.is_watertight),
                    "extents": [float(v) for v in loaded_mesh.extents],
                    "volume": float(loaded_mesh.volume),
                },
            }
        )
        return evidence
    except Exception as exc:
        evidence.update(
            {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        raise
    finally:
        evidence["duration_s"] = round(time.monotonic() - started, 3)
        if proof_json is not None:
            proof_json.parent.mkdir(parents=True, exist_ok=True)
            proof_json.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")


def _validate_runtime_paths(
    *,
    input_image: Path,
    model_ckpt: Path,
    config_path: Path,
    comfyui_root: Path,
    wrapper_root: Path,
) -> None:
    missing = [
        ("input_image", input_image, input_image.is_file()),
        ("model_ckpt", model_ckpt, model_ckpt.is_file()),
        ("config_path", config_path, config_path.is_file()),
        ("comfyui_root", comfyui_root, (comfyui_root / "main.py").is_file()),
        ("wrapper_root", wrapper_root, (wrapper_root / "hy3dshape").is_dir()),
    ]
    failures = [f"{label}: {path}" for label, path, ok in missing if not ok]
    if failures:
        raise FileNotFoundError("Missing Hunyuan3D runtime path(s): " + "; ".join(failures))


def _configure_import_paths(*, comfyui_root: Path, wrapper_root: Path) -> None:
    import_paths = [
        str(wrapper_root / "hy3dshape"),
        str(wrapper_root),
        str(comfyui_root),
    ]
    for candidate in reversed(import_paths):
        if candidate in sys.path:
            sys.path.remove(candidate)
        sys.path.insert(0, candidate)
    torch_lib = comfyui_root / ".venv" / "Lib" / "site-packages" / "torch" / "lib"
    if torch_lib.is_dir():
        os.environ["PATH"] = str(torch_lib) + os.pathsep + os.environ.get("PATH", "")


def _make_generator(*, torch: Any, device: str, seed: int) -> Any:
    generator_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
    return torch.Generator(device=generator_device).manual_seed(seed)


def _scale_mesh_to_target_mm(mesh: Any, target_size_mm: float | None) -> float | None:
    if target_size_mm is None:
        return None
    extents = [float(v) for v in mesh.extents]
    max_extent = max(extents) if extents else 0.0
    if max_extent <= 0:
        raise ValueError("Generated mesh has zero extent and cannot be scaled.")
    scale_factor = float(target_size_mm) / max_extent
    mesh.apply_scale(scale_factor)
    mesh.apply_translation(-mesh.bounds[0])
    return scale_factor


def _mesh_file_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"glb", "obj", "ply", "stl", "3mf", "dae"}:
        return suffix
    return "glb"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Hunyuan3D 2.1 shape generation.")
    parser.add_argument("--input", required=True, type=Path, help="RGBA input image path.")
    parser.add_argument("--output", required=True, type=Path, help="Output mesh path.")
    parser.add_argument("--proof-json", type=Path, help="Optional JSON evidence path.")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance-scale", type=float, default=5.0)
    parser.add_argument("--octree-resolution", type=int, default=256)
    parser.add_argument("--target-size-mm", type=float)
    parser.add_argument("--seed", type=int, default=3201)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--model-ckpt", type=Path, default=DEFAULT_MODEL_CKPT)
    parser.add_argument("--config-path", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--comfyui-root", type=Path, default=DEFAULT_COMFYUI_ROOT)
    parser.add_argument("--wrapper-root", type=Path, default=DEFAULT_WRAPPER_ROOT)
    args = parser.parse_args(argv)

    try:
        evidence = run_hunyuan3d_shape(
            input_image=args.input,
            output_mesh=args.output,
            proof_json=args.proof_json,
            steps=args.steps,
            guidance_scale=args.guidance_scale,
            octree_resolution=args.octree_resolution,
            target_size_mm=args.target_size_mm,
            seed=args.seed,
            device=args.device,
            model_ckpt=args.model_ckpt,
            config_path=args.config_path,
            comfyui_root=args.comfyui_root,
            wrapper_root=args.wrapper_root,
        )
    except Exception as exc:
        print(f"Hunyuan3D shape generation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
