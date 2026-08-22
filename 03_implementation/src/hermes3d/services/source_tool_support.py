"""Source-backed support metadata for local slicer/modeler tools.

This module does not claim that a native desktop GUI is a React component.
It records the honest integration contract Hermes3D can support from local
source checkouts: source inventory, installed runtime/CLI launch, and bounded
workflow adapters.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


SOURCE_TOOL_SPECS: dict[str, dict[str, Any]] = {
    "prusaslicer": {
        "label": "PrusaSlicer",
        "supported_type": "source_supported_slicer",
        "family": "prusaslicer",
        "source_candidates": ["G:/Github/apps/PrusaSlicer-master"],
        "upstream_url": "https://github.com/prusa3d/PrusaSlicer",
        "support_modes": ["source_inventory", "installed_gui", "cli_slice_engine", "3mf_stl_gcode_export"],
        "ui_strategy": "native_gui_stream_plus_cli_engine",
        "notes": "Source checkout supports capability mapping; installed PrusaSlicer executable performs real slicing/export.",
    },
    "orcaslicer": {
        "label": "OrcaSlicer",
        "supported_type": "source_supported_slicer",
        "family": "orcaslicer",
        "source_candidates": ["G:/Github/apps/OrcaSlicer-main"],
        "upstream_url": "https://github.com/SoftFever/OrcaSlicer",
        "support_modes": ["source_inventory", "installed_gui", "cli_slice_engine", "3mf_stl_gcode_export"],
        "ui_strategy": "native_gui_stream_plus_cli_engine",
        "notes": "Source checkout supports capability mapping; installed OrcaSlicer executable provides the runtime surface.",
    },
    "flsun_slicer": {
        "label": "FLSUN Slicer",
        "supported_type": "binary_supported_vendor_slicer",
        "family": "prusaslicer_or_orcaslicer_derivative",
        "source_candidates": [
            "G:/Github/apps/FLSUN-Slicer",
            "G:/Github/apps/FlsunSlicer",
            "G:/Github/apps/flsun-slicer",
        ],
        "upstream_url": None,
        "support_modes": ["installed_gui", "desktop_input_bridge", "vendor_profile_runtime"],
        "ui_strategy": "native_gui_stream",
        "notes": "No local FLSUN slicer source checkout was found. Hermes supports the installed vendor binary and maps shared behavior through the Prusa/Orca slicer family.",
    },
    "comfyui": {
        "label": "ComfyUI",
        "supported_type": "source_supported_web_modeler",
        "family": "comfyui",
        "source_candidates": ["G:/Github/ComfyUI", "G:/comfyui", "G:/comfyui-fresh"],
        "upstream_url": "https://github.com/comfyanonymous/ComfyUI",
        "support_modes": ["source_inventory", "web_runtime", "workflow_api", "custom_nodes"],
        "ui_strategy": "local_web_embed_when_server_running",
        "notes": "Source is usable as a real web runtime when ComfyUI is started on the configured local port.",
    },
    "openscad": {
        "label": "OpenSCAD",
        "supported_type": "source_supported_cad_modeler",
        "family": "openscad",
        "source_candidates": ["G:/Github/openscad-studio", "G:/Github/apps/OpenSCAD"],
        "upstream_url": "https://github.com/openscad/openscad",
        "support_modes": ["source_inventory", "installed_gui", "cli_export_engine"],
        "ui_strategy": "native_gui_stream_plus_cli_engine",
        "notes": "Local source candidate is available for OpenSCAD-related tooling; installed OpenSCAD provides the executable runtime.",
    },
    "blender": {
        "label": "Blender",
        "supported_type": "source_supported_modeler",
        "family": "blender",
        "source_candidates": ["G:/Github/apps/blender", "G:/Github/apps/blender-main"],
        "upstream_url": "https://github.com/blender/blender",
        "support_modes": ["source_inventory", "installed_gui", "background_python_engine", "stl_obj_export"],
        "ui_strategy": "native_gui_stream_plus_python_engine",
        "notes": "Source checkout supports capability mapping; installed Blender executes Python/export workflows.",
    },
    "freecad": {
        "label": "FreeCAD",
        "supported_type": "source_supported_cad_modeler",
        "family": "freecad",
        "source_candidates": ["G:/Github/apps/FreeCAD", "G:/Github/FreeCAD"],
        "upstream_url": "https://github.com/FreeCAD/FreeCAD",
        "support_modes": ["source_inventory", "installed_gui", "cli_export_engine"],
        "ui_strategy": "native_gui_stream_plus_cli_engine",
        "notes": "FreeCAD becomes supported when a source checkout and executable runtime are present.",
    },
}


def source_support_record(tool_id: str) -> dict[str, Any]:
    spec = SOURCE_TOOL_SPECS.get(tool_id)
    if not spec:
        return {
            "tool_id": tool_id,
            "label": tool_id,
            "supported_type": "unregistered",
            "source_status": "unregistered",
            "source_found": False,
            "source_path": None,
            "version_tag": None,
            "support_modes": [],
            "ui_strategy": "unregistered",
            "notes": "No source support contract is registered for this tool.",
        }

    candidates = [Path(str(item)) for item in spec.get("source_candidates") or []]
    source_path = next((candidate for candidate in candidates if candidate.exists()), None)
    source_found = source_path is not None
    version_tag = _git_describe(source_path) if source_path else None
    supported_type = str(spec.get("supported_type") or "source_supported_tool")
    source_status = "source_ready" if source_found else "binary_only" if supported_type.startswith("binary_") else "source_missing"
    return {
        "tool_id": tool_id,
        "label": spec.get("label", tool_id),
        "supported_type": supported_type,
        "family": spec.get("family"),
        "source_status": source_status,
        "source_found": source_found,
        "source_path": str(source_path) if source_path else None,
        "source_candidates": [str(candidate) for candidate in candidates],
        "version_tag": version_tag,
        "upstream_url": spec.get("upstream_url"),
        "support_modes": list(spec.get("support_modes") or []),
        "ui_strategy": spec.get("ui_strategy", "source_inventory"),
        "notes": spec.get("notes", ""),
    }


def source_support_records(tool_ids: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    ids = list(tool_ids) if tool_ids is not None else sorted(SOURCE_TOOL_SPECS)
    return [source_support_record(tool_id) for tool_id in ids]


def _git_describe(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    tag = (proc.stdout or "").strip()
    return tag or None
