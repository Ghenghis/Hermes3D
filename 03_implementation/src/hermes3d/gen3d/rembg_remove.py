"""Background-removal helper for Hermes3D Gen3D.

This module is intentionally runnable as a subprocess. The desktop backend can
stay on its lightweight Python runtime while rembg/onnxruntime/CUDA live in the
ComfyUI runtime that already contains the model weights.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any


def remove_background(
    *,
    input_image: Path,
    output_png: Path,
    proof_json: Path | None = None,
    requested_model: str = "bria-rmbg",
) -> dict[str, Any]:
    started = time.monotonic()
    evidence: dict[str, Any] = {
        "status": "started",
        "engine": "rembg",
        "input_image": str(input_image),
        "output_png": str(output_png),
        "requested_model": requested_model,
        "python": os.sys.executable,
    }
    try:
        import rembg
        from PIL import Image

        session, model_name, providers = _new_session(rembg, requested_model)
        source = Image.open(input_image).convert("RGBA")
        removed = (
            rembg.remove(source, session=session) if session is not None else rembg.remove(source)
        )
        if isinstance(removed, bytes):
            result = Image.open(BytesIO(removed)).convert("RGBA")
        else:
            result = removed.convert("RGBA")

        output_png.parent.mkdir(parents=True, exist_ok=True)
        result.save(output_png)
        alpha = _alpha_stats(result)
        if alpha["foreground_pixels"] == 0:
            raise RuntimeError("Background removal produced no foreground pixels.")
        if alpha["transparent_pixels"] == 0:
            raise RuntimeError(
                "Background removal produced no transparent pixels; background is still present."
            )
        evidence.update(
            {
                "status": "completed",
                "model": model_name,
                "providers": providers,
                "alpha": alpha,
                "output_exists": output_png.is_file(),
                "output_bytes": output_png.stat().st_size,
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


def _new_session(
    rembg_module: Any, requested_model: str
) -> tuple[Any | None, str | None, list[str] | None]:
    candidates = [requested_model]
    for fallback in ("birefnet-general", "isnet-general-use", "u2net"):
        if fallback not in candidates:
            candidates.append(fallback)

    new_session = getattr(rembg_module, "new_session", None)
    if not callable(new_session):
        return None, None, None

    last_error: Exception | None = None
    for model_name in candidates:
        try:
            session = new_session(model_name)
            providers = None
            inner_session = getattr(session, "inner_session", None)
            if inner_session is not None and hasattr(inner_session, "get_providers"):
                providers = list(inner_session.get_providers())
            return session, model_name, providers
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return None, None, None


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove image background with rembg.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proof-json", type=Path)
    parser.add_argument("--model", default=os.environ.get("HERMES3D_REMBG_MODEL", "bria-rmbg"))
    args = parser.parse_args(argv)
    try:
        remove_background(
            input_image=args.input,
            output_png=args.output,
            proof_json=args.proof_json,
            requested_model=args.model,
        )
    except Exception as exc:
        print(f"rembg background removal failed: {type(exc).__name__}: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
