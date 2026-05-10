from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = IMPLEMENTATION_ROOT / "proof" / "LOCAL_TOOLING_AUDIT.json"

TOOLS = {
    "prusaslicer_cli": {
        "path": "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_3mf", "export_stl", "info"],
    },
    "orcaslicer_cli": {
        "path": "C:/Program Files/OrcaSlicer/orca-slicer.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_3mf", "export_stl"],
    },
    "flsun_slicer_cli": {
        "path": "C:/FlsunSlicer2.0/FlsunSlicer.exe",
        "args": ["--help"],
        "capabilities": ["slice", "scale", "rotate", "load_settings", "load_filaments"],
    },
    "openscad_cli": {
        "path": "C:/Program Files/OpenSCAD/openscad.exe",
        "args": ["--version"],
        "capabilities": ["scad_to_stl", "scad_to_3mf", "render_png"],
    },
    "blender_cli": {
        "path": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
        "args": ["--version"],
        "capabilities": ["headless_blender_cli", "python_scene_worker", "mesh_convert"],
    },
    "curaengine_cli": {
        "path": "C:/Program Files/UltiMaker Cura 5.12.1/CuraEngine.exe",
        "args": ["help"],
        "capabilities": ["slice_to_gcode", "profile_engine", "mesh_to_gcode_cli"],
    },
    "bambustudio_windows": {
        "path": "C:/Program Files/Bambu Studio/bambu-studio.exe",
        "args": [],
        "capabilities": ["desktop_slicer_launcher", "project_workspace"],
        "no_execute": True,
    },
    "ultimaker_cura_windows": {
        "path": "C:/Program Files/UltiMaker Cura 5.12.1/UltiMaker-Cura.exe",
        "args": [],
        "capabilities": ["desktop_slicer_launcher", "profile_workspace"],
        "no_execute": True,
    },
    "pronsole_windows": {
        "path": "G:/Github/apps/Pronsole.exe",
        "args": [],
        "capabilities": ["serial_console_app"],
        "no_execute": True,
    },
    "pronterface_windows": {
        "path": "G:/Github/apps/Pronterface.exe",
        "args": [],
        "capabilities": ["serial_gui_app"],
        "no_execute": True,
    },
}


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "apps_root": "G:/Github/apps",
        "tools": {name: audit_tool(config) for name, config in TOOLS.items()},
        "policy": {
            "serial_printer_commands": "not_run",
            "physical_printer_writes": "only via guarded Moonraker endpoint and never S1",
        },
    }
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(OUTPUT)
    return 0


def audit_tool(config: dict[str, object]) -> dict[str, object]:
    path = Path(str(config["path"]))
    result: dict[str, object] = {
        "path": str(path),
        "detected": path.is_file(),
        "capabilities": config.get("capabilities", []),
        "executed": False,
        "return_code": None,
        "output_head": [],
    }
    if not path.is_file() or config.get("no_execute"):
        return result
    try:
        proc = subprocess.run(
            [str(path), *list(config.get("args", []))],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result["output_head"] = [f"{type(exc).__name__}: {exc}"]
        return result
    merged = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    result.update(
        {
            "executed": True,
            "return_code": proc.returncode,
            "output_head": head_lines(merged),
        }
    )
    return result


def head_lines(value: str, *, max_lines: int = 25, max_chars: int = 240) -> list[str]:
    lines = value.splitlines()
    return [
        f"{line[:max_chars]}..." if len(line) > max_chars else line for line in lines[:max_lines]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
