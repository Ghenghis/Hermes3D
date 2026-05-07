"""Source OS module runtime verifier registry.

The registry is deliberately conservative: source checkout proof is separate
from runtime readiness. A module becomes runtime-ready only when a registered,
non-destructive verifier proves the local runtime path or launch bridge.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
LOCAL_TOOLING_AUDIT_PATH = IMPLEMENTATION_ROOT / "proof" / "LOCAL_TOOLING_AUDIT.json"
SOURCE_REGISTRY_AUDIT_PATH = Path("03_implementation/proof/SOURCE_REGISTRY_TRUTH_AUDIT.json")
SECRET_RE = re.compile(
    r"(?i)(https?://)([^/@\s]+@)|([?&](?:token|key|api_key|access_token)=)[^&\s]+"
)

BUILTIN_RUNTIME_PROBES: dict[str, dict[str, Any]] = {
    "prusaslicer": {
        "tool_key": "prusaslicer_cli",
        "label": "PrusaSlicer CLI",
        "path": "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_3mf", "export_stl", "info"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "orcaslicer": {
        "tool_key": "orcaslicer_cli",
        "label": "OrcaSlicer CLI",
        "path": "C:/Program Files/OrcaSlicer/orca-slicer.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_3mf", "export_stl"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "flsun_slicer": {
        "tool_key": "flsun_slicer_cli",
        "label": "FLSUN Slicer CLI",
        "path": "C:/FlsunSlicer2.0/FlsunSlicer.exe",
        "args": ["--help"],
        "capabilities": ["slice", "scale", "rotate", "load_settings", "load_filaments"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "openscad": {
        "tool_key": "openscad_cli",
        "label": "OpenSCAD CLI",
        "path": "C:/Program Files/OpenSCAD/openscad.exe",
        "args": ["--version"],
        "capabilities": ["scad_to_stl", "scad_to_3mf", "render_png"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "printrun": {
        "tool_key": "pronterface_windows",
        "label": "Printrun Windows launcher",
        "path": "G:/Github/apps/Pronterface.exe",
        "args": [],
        "capabilities": ["serial_gui_app"],
        "kind": "desktop_app",
        "execute": False,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "bambustudio": {
        "tool_key": "bambustudio_windows",
        "label": "Bambu Studio Windows launcher",
        "path": "C:/Program Files/Bambu Studio/bambu-studio.exe",
        "args": [],
        "capabilities": ["desktop_slicer_launcher", "project_workspace"],
        "kind": "desktop_app",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "desktop-launcher-metadata-v1",
    },
    "blender": {
        "tool_key": "blender_cli",
        "label": "Blender CLI",
        "path": "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
        "args": ["--version"],
        "capabilities": ["headless_blender_cli", "python_scene_worker", "mesh_convert"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "agent-cli-verifier-v1",
    },
    "curaengine": {
        "tool_key": "curaengine_cli",
        "label": "CuraEngine CLI",
        "path": "C:/Program Files/UltiMaker Cura 5.12.1/CuraEngine.exe",
        "args": ["help"],
        "capabilities": ["slice_to_gcode", "profile_engine", "mesh_to_gcode_cli"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "agent-cli-verifier-v1",
    },
    "superslicer": {
        "tool_key": "superslicer_cli",
        "label": "SuperSlicer CLI",
        "path": "C:/Program Files/SuperSlicer/superslicer-console.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_3mf", "export_stl", "info"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "slic3r": {
        "tool_key": "slic3r_cli",
        "label": "Slic3r CLI",
        "path": "C:/Program Files/Slic3r/slic3r-console.exe",
        "args": ["--help"],
        "capabilities": ["slice_to_gcode", "export_stl", "info"],
        "kind": "cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "runtime-verifier-v1",
    },
    "strec3d": {
        "tool_key": "source_inventory",
        "label": "Strec3D source inventory",
        "path": "",
        "args": ["README.md", "CMakeLists.txt"],
        "capabilities": [
            "structural_infill_reference",
            "desktop_preprocessor_source",
            "cmake_build_reference",
        ],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
        "notes": "README documents a GUI preprocessing workflow; no safe CLI runner is registered.",
    },
    "cura": {
        "tool_key": "ultimaker_cura_windows",
        "label": "UltiMaker Cura Windows launcher",
        "path": "C:/Program Files/UltiMaker Cura 5.12.1/UltiMaker-Cura.exe",
        "args": [],
        "capabilities": ["desktop_slicer_launcher", "profile_workspace"],
        "kind": "desktop_app",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "desktop-launcher-metadata-v1",
    },
    "blender_mcp_candidates": {
        "tool_key": "python_source_import",
        "label": "Blender MCP source import",
        "path": str(
            IMPLEMENTATION_ROOT / "source-lab" / "sources" / "orchestration" / "blender-mcp"
        ),
        "args": ["blender_mcp.server", "src"],
        "capabilities": ["mcp_server_source", "blender_python_bridge", "provider_candidate"],
        "kind": "python_source_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-source-import-verifier-v1",
        "notes": "Imports the source package only; does not start MCP server or connect to Blender.",
    },
    "hermes_agent": {
        "tool_key": "hermes_agent_source_cli",
        "label": "Hermes Agent source CLI",
        "path": "G:/Github/hermes-agent-fresh",
        "args": ["hermes_cli.main", "--help"],
        "capabilities": ["agent_cli", "mcp_management", "session_management", "self_update_cli"],
        "kind": "python_module_cli",
        "execute": True,
        "timeout_s": 12,
        "proof_gate_version": "python-module-cli-verifier-v1",
        "notes": "Runs the source CLI help path only; does not start chat, ACP, gateway, or dashboard.",
    },
    "awesome_extruders": {
        "tool_key": "source_inventory",
        "label": "Awesome Extruders source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["catalog_index", "hardware_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "boxturtle": {
        "tool_key": "source_inventory",
        "label": "BoxTurtle source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["hardware_reference", "configuration_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "enraged_rabbit_project": {
        "tool_key": "source_inventory",
        "label": "EnragedRabbitProject source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["hardware_reference", "configuration_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "awesome_3d_printing": {
        "tool_key": "source_inventory",
        "label": "Awesome 3D Printing source inventory",
        "path": "",
        "args": ["readme.md"],
        "capabilities": ["catalog_index", "research_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "truck": {
        "tool_key": "source_inventory",
        "label": "Truck source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["rust_cad_reference", "source_inventory"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "botqueue": {
        "tool_key": "source_inventory",
        "label": "BotQueue source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["service_reference", "queue_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "fdm_monster": {
        "tool_key": "local_http_health",
        "label": "FDM Monster local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_FDM_MONSTER_URL", "/", "fdm"],
        "default_url": "http://127.0.0.1:4000",
        "setup_steps": [
            "Use HERMES3D_SOURCE_FDM_MONSTER_URL=http://127.0.0.1:4000 unless the local service is assigned a different private port.",
            "From the FDM Monster source checkout, install/build/start the server with its documented Node workflow.",
        ],
        "capabilities": ["print_farm_service_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private FDM Monster URL; does not start or mutate the service.",
    },
    "fluidd": {
        "tool_key": "local_http_health",
        "label": "Fluidd local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_FLUIDD_URL", "/", "fluidd"],
        "default_url": "http://127.0.0.1:8083",
        "setup_steps": [
            "Use HERMES3D_SOURCE_FLUIDD_URL=http://127.0.0.1:8083 for the Hermes3D local Fluidd service.",
            "Fluidd's container default is port 80/8080 and its preview default can conflict with other local apps, so bind a dedicated local port for Hermes3D.",
        ],
        "capabilities": ["moonraker_web_ui_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private Fluidd URL; does not start or mutate the web app.",
    },
    "mainsail": {
        "tool_key": "local_http_health",
        "label": "Mainsail local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_MAINSAIL_URL", "/", "mainsail"],
        "default_url": "http://127.0.0.1:4173",
        "setup_steps": [
            "Use HERMES3D_SOURCE_MAINSAIL_URL=http://127.0.0.1:4173 for the local Mainsail preview service.",
            "From the Mainsail source checkout, run the documented preview/dev workflow without printer mutation.",
        ],
        "capabilities": ["moonraker_web_ui_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private Mainsail URL; does not start or mutate the web app.",
    },
    "octofarm": {
        "tool_key": "local_http_health",
        "label": "OctoFarm local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_OCTOFARM_URL", "/", "octofarm"],
        "default_url": "http://127.0.0.1:4001",
        "setup_steps": [
            "Use HERMES3D_SOURCE_OCTOFARM_URL=http://127.0.0.1:4001 because OctoFarm and FDM Monster both default to port 4000.",
            "Start OctoFarm with OCTOFARM_PORT=4001 from its source checkout after dependencies are installed.",
        ],
        "capabilities": ["print_farm_service_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private OctoFarm URL; does not start or mutate the service.",
    },
    "octoprint": {
        "tool_key": "local_http_health",
        "label": "OctoPrint local version API",
        "path": "",
        "args": ["HERMES3D_SOURCE_OCTOPRINT_URL", "/api/version", "server"],
        "default_url": "http://127.0.0.1:5000",
        "setup_steps": [
            "Use HERMES3D_SOURCE_OCTOPRINT_URL=http://127.0.0.1:5000 for OctoPrint's documented local default.",
            "Start OctoPrint with a local-only host binding before running this read-only version probe.",
        ],
        "capabilities": ["octoprint_version_api", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private OctoPrint version endpoint; does not upload, print, or mutate state.",
    },
    "manyfold": {
        "tool_key": "local_http_health",
        "label": "Manyfold local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_MANYFOLD_URL", "/", "manyfold"],
        "default_url": "http://127.0.0.1:3214",
        "setup_steps": [
            "Use HERMES3D_SOURCE_MANYFOLD_URL=http://127.0.0.1:3214 for Manyfold's documented local default.",
            "From the Manyfold source checkout, run bin/dev to set up and start the app.",
        ],
        "capabilities": ["model_library_service_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private Manyfold URL; does not start, import, or mutate the library.",
    },
    "open_filament_database": {
        "tool_key": "local_http_health",
        "label": "Open Filament Database local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_OPEN_FILAMENT_DATABASE_URL", "/", "filament"],
        "default_url": "http://127.0.0.1:3000",
        "setup_steps": [
            "Use HERMES3D_SOURCE_OPEN_FILAMENT_DATABASE_URL=http://127.0.0.1:3000 because the documented default 5173 is reserved for Hermes3D UI.",
            "From the Open Filament Database source checkout, run ofd.bat webui --port 3000.",
        ],
        "capabilities": ["material_database_service_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private material database URL; does not write material records.",
    },
    "kirimoto_gridspace": {
        "tool_key": "local_http_health",
        "label": "Kiri:Moto / GridSpace local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_KIRIMOTO_GRIDSPACE_URL", "/", "grid"],
        "default_url": "http://127.0.0.1:8081/kiri",
        "setup_steps": [
            "Use HERMES3D_SOURCE_KIRIMOTO_GRIDSPACE_URL=http://127.0.0.1:8081/kiri; do not use 8080 while GitLab owns that port.",
            "Start Kiri:Moto/GridSpace with a host-port remap such as 8081:8080 or an equivalent local-only dev port.",
        ],
        "capabilities": ["browser_slicer_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private Kiri:Moto or GridSpace URL; does not slice or upload files.",
    },
    "comfyui": {
        "tool_key": "local_http_health",
        "label": "ComfyUI local system stats",
        "path": "",
        "args": ["HERMES3D_SOURCE_COMFYUI_URL", "/system_stats", "system"],
        "default_url": "http://127.0.0.1:8188",
        "setup_steps": [
            "Use HERMES3D_SOURCE_COMFYUI_URL=http://127.0.0.1:8188 for ComfyUI's documented local default.",
            "From the ComfyUI source checkout, start it on 127.0.0.1:8188 before running the system-stats probe.",
        ],
        "capabilities": ["generation_service_health", "read_only_http_probe", "system_stats"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only ComfyUI's configured local/private system stats endpoint; does not enqueue generation work.",
    },
    "comfyui_trellis_wrapper": {
        "tool_key": "local_http_health",
        "label": "ComfyUI TRELLIS wrapper local health",
        "path": "",
        "args": ["HERMES3D_SOURCE_COMFYUI_TRELLIS_WRAPPER_URL", "/", "trellis"],
        "default_url": "http://127.0.0.1:8188",
        "setup_steps": [
            "Use HERMES3D_SOURCE_COMFYUI_TRELLIS_WRAPPER_URL=http://127.0.0.1:8188 only after TRELLIS wrapper/custom-node support is installed in the local ComfyUI runtime.",
            "Confirm the running ComfyUI instance exposes TRELLIS wrapper UI or health text before accepting this verifier.",
        ],
        "capabilities": ["trellis_wrapper_service_health", "read_only_http_probe"],
        "kind": "local_http_health",
        "execute": True,
        "timeout_s": 3,
        "proof_gate_version": "local-http-health-verifier-v1",
        "notes": "Reads only a configured local/private wrapper health page; does not submit ComfyUI or TRELLIS jobs.",
    },
    "langchain": {
        "tool_key": "source_inventory",
        "label": "LangChain source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["agent_orchestration_reference", "source_inventory"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "langgraph": {
        "tool_key": "source_inventory",
        "label": "LangGraph source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["agent_orchestration_reference", "workflow_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "klipperscreen": {
        "tool_key": "source_inventory",
        "label": "KlipperScreen source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["touch_ui_reference", "klipper_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "kiln": {
        "tool_key": "source_inventory",
        "label": "Kiln source inventory",
        "path": "",
        "args": ["README.md"],
        "capabilities": ["web_app_reference", "agent_eval_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "comfyui_frontend": {
        "tool_key": "source_inventory",
        "label": "ComfyUI Frontend source inventory",
        "path": "",
        "args": ["README.md", "package.json"],
        "capabilities": ["web_app_reference", "generation_ui_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "box_stl_generator": {
        "tool_key": "source_inventory",
        "label": "3D Box Generator source inventory",
        "path": "",
        "args": ["README.md", "package.json"],
        "capabilities": ["web_app_reference", "parametric_generator_reference"],
        "kind": "source_inventory",
        "execute": False,
        "timeout_s": 1,
        "proof_gate_version": "source-inventory-v1",
    },
    "model_context_protocol": {
        "tool_key": "node_package",
        "label": "Model Context Protocol SDK package",
        "path": "node",
        "args": ["@modelcontextprotocol/sdk"],
        "capabilities": ["mcp_sdk", "tool_protocol_reference"],
        "kind": "node_package",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "node-package-verifier-v1",
    },
    "manifold": {
        "tool_key": "python_import",
        "label": "Manifold Python import",
        "path": sys.executable,
        "args": ["manifold3d"],
        "capabilities": ["manifold_mesh_library", "boolean_geometry"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "trimesh": {
        "tool_key": "python_import",
        "label": "Trimesh Python import",
        "path": sys.executable,
        "args": ["trimesh"],
        "capabilities": ["mesh_load", "mesh_repair", "mesh_analysis"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "meshlab": {
        "tool_key": "python_import",
        "label": "MeshLab pymeshlab Python bridge",
        "path": sys.executable,
        "args": ["pymeshlab"],
        "capabilities": ["mesh_load", "mesh_filter_pipeline", "mesh_repair_reference"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
        "notes": "Verifies the installed pymeshlab bridge only; MeshLab desktop/meshlabserver CLI remains disabled until a bounded CLI path is registered.",
    },
    "cadquery": {
        "tool_key": "python_import",
        "label": "CadQuery Python import",
        "path": sys.executable,
        "args": ["cadquery"],
        "capabilities": ["parametric_cad_worker", "step_stl_export"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "open3d": {
        "tool_key": "python_import",
        "label": "Open3D Python import",
        "path": sys.executable,
        "args": ["open3d"],
        "capabilities": ["point_cloud_processing", "mesh_io", "geometry_analysis"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "build123d": {
        "tool_key": "python_import",
        "label": "build123d Python import",
        "path": sys.executable,
        "args": ["build123d"],
        "capabilities": ["parametric_cad_worker", "solid_modeling"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "numpy_stl": {
        "tool_key": "python_import",
        "label": "numpy-stl Python import",
        "path": sys.executable,
        "args": ["stl"],
        "capabilities": ["stl_load", "stl_transform", "mesh_measurement"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
    },
    "pymesh": {
        "tool_key": "python_import",
        "label": "PyMesh/pymeshfix Python import",
        "path": sys.executable,
        "args": ["pymeshfix"],
        "capabilities": ["mesh_repair", "mesh_cleanup", "watertightness_reference"],
        "kind": "python_import",
        "execute": True,
        "timeout_s": 5,
        "proof_gate_version": "python-import-verifier-v1",
        "notes": "The local checkout points at pymeshfix; this verifier intentionally checks pymeshfix rather than pretending full PyMesh is installed.",
    },
    "moonraker": {
        "tool_key": "moonraker_fleet",
        "label": "Moonraker fleet read-only API",
        "path": "",
        "args": ["/server/info", "3"],
        "capabilities": ["moonraker_readonly_api", "fleet_status_probe"],
        "kind": "moonraker_fleet",
        "execute": True,
        "timeout_s": 2,
        "proof_gate_version": "moonraker-fleet-verifier-v1",
    },
    "klipper": {
        "tool_key": "moonraker_fleet",
        "label": "Klipper fleet read-only API",
        "path": "",
        "args": ["/printer/info", "3"],
        "capabilities": ["klipper_readonly_state", "fleet_status_probe"],
        "kind": "moonraker_fleet",
        "execute": True,
        "timeout_s": 2,
        "proof_gate_version": "moonraker-fleet-verifier-v1",
    },
    "firmware_klipper": {
        "tool_key": "moonraker_fleet",
        "label": "Klipper firmware fleet read-only API",
        "path": "",
        "args": ["/printer/info", "3"],
        "capabilities": ["klipper_firmware_readonly_state", "fleet_status_probe"],
        "kind": "moonraker_fleet",
        "execute": True,
        "timeout_s": 2,
        "proof_gate_version": "moonraker-fleet-verifier-v1",
    },
}

CLI_PREFERRED_LAUNCH_KINDS = {"cli_worker", "cli_or_python_worker", "desktop_or_cli"}
CLI_POSSIBLE_LAUNCH_KINDS = {
    "desktop_app",
    "python_worker",
    "gpu_worker",
    "service",
    "web_app",
    "npm_package",
}
AGENT_EXECUTABLE_VERIFIER_KINDS = {"cli", "python_module_cli"}
SERVICE_START_RUNNERS: dict[str, dict[str, Any]] = {
    "fdm_monster": {
        "command": ["npm", "run", "start"],
        "command_family": "node_service",
        "port": 4000,
        "notes": "Start only after dependencies are installed and the app is bound to the configured local/private URL.",
    },
    "fluidd": {
        "command": ["npm", "run", "serve", "--", "--host", "127.0.0.1", "--port", "8083"],
        "command_family": "node_web_preview",
        "port": 8083,
        "notes": "Use a dedicated local preview port so Fluidd does not collide with other local apps.",
    },
    "mainsail": {
        "command": ["npm", "run", "serve", "--", "--host", "127.0.0.1", "--port", "4173"],
        "command_family": "node_web_preview",
        "port": 4173,
        "notes": "Start a local-only preview before the read-only health proof can pass.",
    },
    "octofarm": {
        "command": ["npm", "run", "start"],
        "command_family": "node_service",
        "port": 4001,
        "env": {"OCTOFARM_PORT": "4001"},
        "notes": "OctoFarm can need backing services; this runner only preflights the local service boundary.",
    },
    "octoprint": {
        "command": ["octoprint", "serve", "--host=127.0.0.1", "--port=5000"],
        "command_family": "python_service_cli",
        "port": 5000,
        "notes": "Requires a configured OctoPrint Python environment; no printer upload/print commands are exposed.",
    },
    "manyfold": {
        "command": ["bin/dev"],
        "command_family": "rails_service",
        "port": 3214,
        "notes": "Manyfold's app setup may run database migrations; this contract does not execute those steps automatically.",
    },
    "open_filament_database": {
        "command": ["ofd.bat", "webui", "--port", "3000"],
        "command_family": "material_database_service",
        "port": 3000,
        "notes": "Use the local web UI only; material record writes require a separate approval/proof gate.",
    },
    "kirimoto_gridspace": {
        "command": ["docker", "compose", "up", "--no-build"],
        "command_family": "container_web_app",
        "port": 8081,
        "notes": "Requires a host-port remap such as 8081:8080; the runner does not build images.",
    },
    "comfyui": {
        "command": [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        "command_family": "python_gpu_service",
        "port": 8188,
        "notes": "GPU/model-cache startup is high cost; generation queues remain separate from health startup.",
    },
    "comfyui_trellis_wrapper": {
        "command": [],
        "command_family": "comfyui_extension",
        "port": 8188,
        "blocked_reason": "The TRELLIS wrapper is not a standalone service; install/enable it inside a verified ComfyUI runtime.",
        "notes": "Verify through the running ComfyUI instance before any TRELLIS wrapper action is exposed.",
    },
}


def module_runtime_probe(mod: dict[str, Any], *, live: bool = False) -> dict[str, Any]:
    module_id = str(mod["id"])
    probe = runtime_probe_config(module_id)
    if probe:
        return _safe_runtime_probe(probe, mod, live=live)
    return _source_runtime_state(mod)


def module_setup_steps(mod: dict[str, Any]) -> list[str]:
    launch_kind = str(mod.get("launch_kind") or "unknown")
    local_path = str(mod.get("local_path") or "")
    if launch_kind in {"npm_package", "web_app"}:
        return [
            f"Open or build the source checkout at {local_path}.",
            "Run the module's package manager install/build commands from its README.",
            "Register a safe verifier for this module before marking runtime ready.",
        ]
    if launch_kind in {"python_worker", "cli_or_python_worker", "gpu_worker"}:
        return [
            f"Open the source checkout at {local_path}.",
            "Create or select the module's Python environment and install its declared requirements.",
            "Register a safe verifier for this module before marking runtime ready.",
        ]
    if launch_kind in {"desktop_app", "desktop_or_cli", "cli_worker"}:
        return [
            f"Open the source checkout at {local_path}.",
            "Install or locate the desktop/CLI executable.",
            "Register the executable path so Verify can probe it.",
        ]
    if launch_kind == "firmware_source":
        return [
            f"Open the firmware source checkout at {local_path}.",
            "Register a read-only version/build verifier before any firmware work is considered ready.",
            "Keep firmware flashing locked behind explicit user approval and printer-specific proof gates.",
        ]
    if launch_kind in {
        "catalog_reference",
        "hardware_reference",
        "source_reference",
        "service_reference",
        "web_app_reference",
        "reference",
        "rust_library_reference",
        "touch_ui_reference",
    }:
        return [
            f"Open the source/reference checkout at {local_path}.",
            "Register a read-only index, documentation, or health verifier for this module family.",
            "Keep this row source-ready until a real adapter or reference parser writes proof.",
        ]
    return [
        f"Source checkout is present at {local_path}.",
        "Add a module-specific verifier or adapter before treating this as a runnable Hermes3D app.",
    ]


def registered_runtime_probe_ids() -> list[str]:
    available, index = _runtime_verifier_index()
    if available and index:
        return sorted(index)
    return sorted(BUILTIN_RUNTIME_PROBES)


def module_runner_contract(mod: dict[str, Any]) -> dict[str, Any]:
    """Return the Hermes Agent runner contract for a Source OS module.

    The contract is intentionally separate from runtime detection. A local
    checkout, README command, or desktop launcher can prove source presence, but
    only a registered non-destructive verifier can make the module executable
    by Hermes Agents.
    """

    runtime = module_runtime_probe(mod, live=False)
    launch_kind = str(mod.get("launch_kind") or "unknown")
    runtime_status = str(runtime.get("status") or "blocked")
    verifier_kind = str(runtime.get("kind") or launch_kind)
    executed = bool(runtime.get("executed"))
    agent_executable = (
        runtime_status == "ready" and verifier_kind in AGENT_EXECUTABLE_VERIFIER_KINDS and executed
    )
    runner_status = _runner_status(runtime=runtime, mod=mod, agent_executable=agent_executable)
    required_family = _required_verifier_family(launch_kind, verifier_kind, runner_status)
    blocked_reason = _runner_blocked_reason(
        runtime=runtime, runner_status=runner_status, required_family=required_family
    )
    return {
        "module_id": str(mod.get("id") or ""),
        "display": str(mod.get("display_name") or mod.get("id") or ""),
        "section": str(mod.get("section") or ""),
        "launch_kind": launch_kind,
        "install_state": str(mod.get("install_state") or "unknown"),
        "runtime_status": runtime_status,
        "runtime_ready": runtime_status == "ready",
        "agent_executable": agent_executable,
        "runner_status": runner_status,
        "verifier": runtime.get("verifier"),
        "verifier_kind": verifier_kind,
        "proof_gate_version": runtime.get("proof_gate_version"),
        "path": runtime.get("path") or mod.get("local_path") or "",
        "executed": executed,
        "return_code": runtime.get("return_code"),
        "capabilities": list(runtime.get("capabilities") or []),
        "safe_actions": _safe_runner_actions(runtime, agent_executable=agent_executable),
        "required_verifier_family": required_family,
        "acceptance_gate": _runner_acceptance_gate(
            str(mod.get("id") or "module"), runner_status, required_family
        ),
        "blocked_reason": blocked_reason,
        "setup_steps": []
        if agent_executable
        else (runtime.get("setup_steps") or module_setup_steps(mod))[:6],
        "proof_required": True,
        "mutation_allowed": False,
        "policy": "Hermes Agents may run only registered non-destructive verifiers here; setup/install/update remains plan-only until a runner is registered with backup, smoke, proof, and rollback gates.",
    }


def module_runner_contracts(modules: list[dict[str, Any]]) -> dict[str, Any]:
    contracts = [module_runner_contract(mod) for mod in modules]
    by_status: dict[str, int] = {}
    by_section: dict[str, int] = {}
    for contract in contracts:
        status = str(contract["runner_status"])
        section = str(contract["section"] or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        if not contract["agent_executable"]:
            by_section[section] = by_section.get(section, 0) + 1
    return {
        "status": "ready",
        "count": len(contracts),
        "agent_executable": sum(1 for contract in contracts if contract["agent_executable"]),
        "runner_gaps": sum(
            1
            for contract in contracts
            if contract["runner_status"].endswith("_gap")
            or contract["runner_status"]
            in {
                "runner_not_registered",
                "runtime_repair_required",
                "source_install_available",
                "blocked",
            }
        ),
        "by_runner_status": dict(sorted(by_status.items())),
        "by_gap_section": dict(sorted(by_section.items())),
        "contracts": contracts,
        "rule": "No Source OS row is Hermes Agent executable unless this contract has agent_executable=true and a non-destructive verifier proof gate.",
    }


def module_service_start_runner_contract(
    mod: dict[str, Any], *, live_probe: bool = False
) -> dict[str, Any]:
    """Return the bounded setup/start contract for a service/web Source OS row.

    This is a preflight contract, not an arbitrary command launcher. It records
    the known start family, local URL guard, checkout presence, command
    availability, and port state so Hermes Agents can plan safely without
    falsely marking a service ready.
    """

    module_id = str(mod.get("id") or "")
    probe = runtime_probe_config(module_id)
    runner = SERVICE_START_RUNNERS.get(module_id)
    if not runner or not probe or probe.get("kind") != "local_http_health":
        return {
            "module_id": module_id,
            "display": str(mod.get("display_name") or module_id),
            "status": "unsupported",
            "start_preflight_passed": False,
            "runtime_ready": False,
            "agent_can_execute_start_now": False,
            "mutation_allowed": False,
            "blocked_reason": "No safe local service/web start runner is registered for this Source OS row.",
            "execution_mode": "unsupported",
        }

    args = [str(item) for item in probe.get("args") or []]
    env_name = args[0].strip() if args else ""
    default_url = str(probe.get("default_url") or "").strip()
    private_values = _private_runtime_env()
    configured_url = (os.environ.get(env_name) or private_values.get(env_name) or "").strip()
    local_path_value = str(mod.get("local_path") or "")
    local_path = Path(local_path_value) if local_path_value else None
    source_checkout_present = bool(local_path and local_path.is_dir())
    runtime = (
        module_runtime_probe(mod, live=False)
        if live_probe
        else {
            "status": "unchecked",
            "reason": None,
            "return_code": None,
            "proof_gate_version": probe.get("proof_gate_version")
            or "local-http-health-verifier-v1",
        }
    )
    runtime_status = str(runtime.get("status") or "blocked")
    port_state = _local_service_port_state(configured_url or default_url)
    command = [str(item) for item in runner.get("command") or []]
    command_available = _service_start_command_available(command, local_path)
    blockers: list[str] = []
    if not env_name:
        blockers.append("The verifier metadata has no local/private URL environment binding.")
    if not configured_url:
        blockers.append(f"{env_name} is not configured in process env or G:/private/.env.")
    elif not _is_local_private_url(configured_url):
        blockers.append(
            f"{env_name} must point to localhost, a private LAN address, or a .local host."
        )
    if not source_checkout_present:
        blockers.append("The configured local source checkout path is missing.")
    if runner.get("blocked_reason"):
        blockers.append(str(runner["blocked_reason"]))
    if command and not command_available:
        blockers.append(f"Start command executable is not available yet: {command[0]}.")
    if port_state["status"] == "listening" and runtime_status != "ready":
        blockers.append(
            "The configured port is already in use, but the read-only health verifier did not pass."
        )

    runtime_ready = runtime_status == "ready"
    preflight_passed = not blockers and not runtime_ready
    status = (
        "already_running_verified"
        if runtime_ready
        else "ready_to_start"
        if preflight_passed
        else "setup_required"
    )
    return {
        "module_id": module_id,
        "display": str(mod.get("display_name") or module_id),
        "section": str(mod.get("section") or ""),
        "launch_kind": str(mod.get("launch_kind") or ""),
        "status": status,
        "runtime_ready": runtime_ready,
        "runtime_status": runtime_status,
        "runtime_reason": runtime.get("reason"),
        "start_preflight_passed": preflight_passed,
        "agent_can_execute_start_now": False,
        "mutation_allowed": False,
        "execution_mode": "preflight_and_proof_only_until_process_supervisor_is_enabled",
        "env_name": env_name,
        "configured_url": _redact_text(configured_url) if configured_url else "",
        "default_url": default_url,
        "url_guard": "local_private_only",
        "local_path": local_path_value,
        "source_checkout_present": source_checkout_present,
        "runner": {
            "command_family": runner.get("command_family"),
            "command_preview": command,
            "command_available": command_available,
            "port": runner.get("port"),
            "env": dict(runner.get("env") or {}),
            "notes": runner.get("notes"),
        },
        "port_state": port_state,
        "safe_actions": ["verify", "setup_plan", "start_runner_preflight"],
        "blocked_reasons": blockers,
        "blocked_reason": "; ".join(blockers) if blockers else None,
        "acceptance_gate": f"`/api/modules/{module_id}/runtime/verify` must return ready after startup before this service is marked runtime-ready.",
    }


def runtime_probe_config(module_id: str) -> dict[str, Any] | None:
    available, index = _runtime_verifier_index()
    if available and index:
        return index.get(module_id)
    probe = BUILTIN_RUNTIME_PROBES.get(module_id)
    return {**probe, "registry_source": "builtin"} if probe else None


def _safe_runtime_probe(
    probe: dict[str, Any], mod: dict[str, Any], *, live: bool
) -> dict[str, Any]:
    if probe.get("kind") == "source_inventory":
        return _source_inventory_probe(probe, mod)
    if probe.get("kind") == "python_import":
        return _python_import_probe(probe)
    if probe.get("kind") == "python_source_import":
        return _python_source_import_probe(probe)
    if probe.get("kind") == "python_module_cli":
        return _python_module_cli_probe(probe)
    if probe.get("kind") == "node_package":
        return _node_package_probe(probe)
    if probe.get("kind") == "moonraker_fleet":
        return _moonraker_fleet_probe(probe)
    if probe.get("kind") == "local_http_health":
        return _local_http_health_probe(probe)
    path_value = str(probe.get("path") or "")
    path = Path(path_value) if path_value else None
    audit = _local_tooling_record(str(probe.get("tool_key") or ""))
    detected = bool(path and path.is_file()) or bool(audit.get("detected"))
    executed = False
    return_code = audit.get("return_code")
    output_head = _head_lines([str(item) for item in audit.get("output_head") or []])
    if live and detected and probe.get("execute"):
        proc = _run_runtime_command(
            path,
            [str(arg) for arg in probe.get("args") or []],
            timeout=int(probe.get("timeout_s") or 12),
        )
        executed = True
        return_code = proc.returncode
        output_head = _head_lines(
            _redact_text(
                (proc.stdout or "")
                + ("\n" if proc.stdout and proc.stderr else "")
                + (proc.stderr or "")
            )
        )
    elif audit:
        executed = bool(audit.get("executed"))
    status = (
        "ready"
        if detected and (not probe.get("execute") or return_code == 0)
        else "blocked"
        if not detected
        else "setup_required"
    )
    label = (
        "Runtime ready"
        if status == "ready"
        else "Runtime setup needed"
        if status == "setup_required"
        else "Runtime missing"
    )
    return {
        "status": status,
        "label": label,
        "kind": probe.get("kind"),
        "verifier": probe.get("label"),
        "path": path_value,
        "detected": detected,
        "executed": executed,
        "return_code": return_code,
        "capabilities": list(probe.get("capabilities") or []),
        "reason": None
        if status == "ready"
        else f"{probe.get('label')} was not verified at {path_value}.",
        "setup_steps": []
        if status == "ready"
        else [
            f"Install or repair {probe.get('label')} at {path_value}.",
            "Run Verify again from Source OS.",
        ],
        "proof_source": str(LOCAL_TOOLING_AUDIT_PATH)
        if audit
        else "local filesystem executable metadata"
        if detected
        else None,
        "output_head": output_head,
        "registry_source": probe.get("registry_source") or "builtin",
        "proof_gate_version": probe.get("proof_gate_version") or "runtime-verifier-v1",
    }


def _source_inventory_probe(probe: dict[str, Any], mod: dict[str, Any]) -> dict[str, Any]:
    path_value = str(probe.get("path") or mod.get("local_path") or "")
    root = Path(path_value) if path_value else None
    expected = [str(item) for item in probe.get("args") or ["README.md"]]
    found: list[str] = []
    missing: list[str] = []
    if root and root.is_dir():
        for item in expected:
            match = _find_case_insensitive_child(root, item)
            if match:
                found.append(str(match.relative_to(root)))
            else:
                missing.append(item)
    else:
        missing = expected
    top_level = _top_level_inventory(root)
    ready = bool(root and root.is_dir()) and not missing
    setup_steps = (
        [
            "Source inventory is verified; keep this row reference-only until a real adapter or runner is implemented.",
            "If execution is required, add a bounded verifier that proves a non-destructive CLI, API, or desktop bridge.",
        ]
        if ready
        else [f"Restore required source files in {path_value}.", "Run Verify again from Source OS."]
    )
    return {
        "status": "ready" if ready else "source_ready",
        "label": "Source inventory ready" if ready else "Source inventory incomplete",
        "kind": probe.get("kind"),
        "verifier": probe.get("label"),
        "path": path_value,
        "detected": bool(root and root.is_dir()),
        "executed": False,
        "return_code": 0 if ready else None,
        "capabilities": list(probe.get("capabilities") or []),
        "reason": None
        if ready
        else f"{probe.get('label')} is missing required source files: {', '.join(missing)}.",
        "setup_steps": setup_steps,
        "proof_source": str(SOURCE_REGISTRY_AUDIT_PATH),
        "output_head": [
            f"expected={','.join(expected)}",
            f"found={','.join(found)}",
            f"top_level={','.join(top_level[:20])}",
        ],
        "registry_source": probe.get("registry_source") or "builtin",
        "proof_gate_version": probe.get("proof_gate_version") or "source-inventory-v1",
    }


def _python_import_probe(probe: dict[str, Any]) -> dict[str, Any]:
    module_name = str((probe.get("args") or [""])[0] or "").strip()
    timeout = int(probe.get("timeout_s") or 5)
    code = (
        "import importlib, json\n"
        f"module_name = {module_name!r}\n"
        "module = importlib.import_module(module_name)\n"
        "print(json.dumps({'module': module_name, 'version': str(getattr(module, '__version__', 'unknown'))}))\n"
    )
    proc = _run_checked_command([sys.executable, "-c", code], timeout=timeout)
    return _metadata_probe_response(
        probe,
        ready=proc.returncode == 0,
        detected=True,
        path_value=sys.executable,
        return_code=proc.returncode,
        output=_redact_text(
            (proc.stdout or "")
            + ("\n" if proc.stdout and proc.stderr else "")
            + (proc.stderr or "")
        ),
        missing_reason=f"Python module {module_name} is not importable in the Hermes3D backend runtime.",
        repair_steps=[
            f"Install or select a Hermes3D Python runtime that can import {module_name}.",
            "Run Verify again from Source OS after the environment is configured.",
        ],
    )


def _python_source_import_probe(probe: dict[str, Any]) -> dict[str, Any]:
    args = [str(item) for item in probe.get("args") or []]
    module_name = args[0].strip() if args else ""
    root = Path(str(probe.get("path") or ""))
    path_entries = [root, *[(root / extra) for extra in args[1:]]]
    existing_paths = [str(path) for path in path_entries if path.exists()]
    timeout = int(probe.get("timeout_s") or 5)
    if not module_name or not root.is_dir():
        return _metadata_probe_response(
            probe,
            ready=False,
            detected=root.is_dir(),
            path_value=str(root),
            return_code=1,
            output="source import verifier is missing module name or source path",
            missing_reason="Python source import verifier is not fully configured.",
            repair_steps=[
                "Configure the source root and import module for this verifier.",
                "Run Verify again from Source OS after the verifier is repaired.",
            ],
            proof_source="Hermes3D source checkout import probe",
        )
    code = (
        "import importlib, json, sys\n"
        f"paths = {existing_paths!r}\n"
        "sys.path[:0] = paths\n"
        f"module_name = {module_name!r}\n"
        "module = importlib.import_module(module_name)\n"
        "print(json.dumps({'module': module_name, 'has_main': hasattr(module, 'main'), 'file': str(getattr(module, '__file__', ''))}))\n"
    )
    proc = _run_checked_command([sys.executable, "-c", code], timeout=timeout)
    return _metadata_probe_response(
        probe,
        ready=proc.returncode == 0,
        detected=True,
        path_value=str(root),
        return_code=proc.returncode,
        output=_redact_text(
            (proc.stdout or "")
            + ("\n" if proc.stdout and proc.stderr else "")
            + (proc.stderr or "")
        ),
        missing_reason=f"Python source module {module_name} is not importable from {root}.",
        repair_steps=[
            f"Install or repair dependencies needed to import {module_name} from {root}.",
            "Run Verify again from Source OS after the source environment is configured.",
        ],
        proof_source="Hermes3D source checkout import probe",
    )


def _python_module_cli_probe(probe: dict[str, Any]) -> dict[str, Any]:
    args = [str(item) for item in probe.get("args") or []]
    module_name = args[0].strip() if args else ""
    cli_args = args[1:]
    root = Path(str(probe.get("path") or ""))
    timeout = int(probe.get("timeout_s") or 12)
    if not module_name or not root.is_dir():
        return _metadata_probe_response(
            probe,
            ready=False,
            detected=root.is_dir(),
            path_value=str(root),
            return_code=1,
            output="python module CLI verifier is missing module name or source path",
            missing_reason="Python module CLI verifier is not fully configured.",
            repair_steps=[
                "Configure the source root and import module for this verifier.",
                "Run Verify again from Source OS after the verifier is repaired.",
            ],
            proof_source="Hermes3D source CLI smoke probe",
        )
    path_entries = [root]
    src_path = root / "src"
    if src_path.is_dir():
        path_entries.append(src_path)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [
            *(str(path) for path in path_entries),
            *([existing_pythonpath] if existing_pythonpath else []),
        ]
    )
    proc = _run_checked_command(
        [sys.executable, "-m", module_name, *cli_args],
        timeout=timeout,
        env=env,
    )
    return _metadata_probe_response(
        probe,
        ready=proc.returncode == 0,
        detected=True,
        path_value=str(root),
        return_code=proc.returncode,
        output=_redact_text(
            (proc.stdout or "")
            + ("\n" if proc.stdout and proc.stderr else "")
            + (proc.stderr or "")
        ),
        missing_reason=f"Python module CLI {module_name} did not pass the bounded smoke command.",
        repair_steps=[
            f"Install or repair dependencies needed to run python -m {module_name} {' '.join(cli_args)} from {root}.",
            "Run Verify again from Source OS after the source CLI environment is configured.",
        ],
        proof_source="Hermes3D source CLI smoke probe",
    )


def _node_package_probe(probe: dict[str, Any]) -> dict[str, Any]:
    package_name = str((probe.get("args") or [""])[0] or "").strip()
    timeout = int(probe.get("timeout_s") or 5)
    node_path = shutil.which("node")
    if not node_path:
        return _metadata_probe_response(
            probe,
            ready=False,
            detected=False,
            path_value="node",
            return_code=127,
            output="node executable not found",
            missing_reason="Node.js is not available on PATH for this package verifier.",
            repair_steps=[
                "Install or expose Node.js on PATH for the Hermes3D backend runtime.",
                "Run Verify again from Source OS after Node.js is available.",
            ],
        )
    code = (
        "const pkgName = process.argv[1];\n"
        "const path = require.resolve(pkgName + '/package.json');\n"
        "const pkg = require(path);\n"
        "console.log(JSON.stringify({ package: pkgName, version: String(pkg.version || 'unknown'), path }));\n"
    )
    proc = _run_checked_command([node_path, "-e", code, package_name], timeout=timeout)
    return _metadata_probe_response(
        probe,
        ready=proc.returncode == 0,
        detected=True,
        path_value=node_path,
        return_code=proc.returncode,
        output=_redact_text(
            (proc.stdout or "")
            + ("\n" if proc.stdout and proc.stderr else "")
            + (proc.stderr or "")
        ),
        missing_reason=f"Node package {package_name} is not resolvable in the Hermes3D backend Node runtime.",
        repair_steps=[
            f"Install or expose {package_name} to the Hermes3D backend Node runtime.",
            "Run Verify again from Source OS after the package is configured.",
        ],
    )


def _metadata_probe_response(
    probe: dict[str, Any],
    *,
    ready: bool,
    detected: bool,
    path_value: str,
    return_code: int | None,
    output: str,
    missing_reason: str,
    repair_steps: list[str],
    proof_source: str = "Hermes3D backend runtime metadata probe",
) -> dict[str, Any]:
    return {
        "status": "ready" if ready else "setup_required",
        "label": "Runtime ready" if ready else "Runtime setup needed",
        "kind": probe.get("kind"),
        "verifier": probe.get("label"),
        "path": path_value,
        "detected": detected,
        "executed": True,
        "return_code": return_code,
        "capabilities": list(probe.get("capabilities") or []),
        "reason": None if ready else missing_reason,
        "setup_steps": [] if ready else repair_steps,
        "proof_source": proof_source,
        "output_head": _head_lines(output),
        "registry_source": probe.get("registry_source") or "builtin",
        "proof_gate_version": probe.get("proof_gate_version") or "metadata-verifier-v1",
    }


def _moonraker_fleet_probe(probe: dict[str, Any]) -> dict[str, Any]:
    args = [str(item) for item in probe.get("args") or []]
    endpoint = args[0] if args else "/server/info"
    min_success = _safe_int(args[1] if len(args) > 1 else None, default=1)
    timeout = int(probe.get("timeout_s") or 2)
    printers = _configured_moonraker_printers()
    probe_rows = _probe_moonraker_endpoint(printers, endpoint=endpoint, timeout=timeout)
    successes = [row for row in probe_rows if row["ok"]]
    ready = len(successes) >= min_success
    output = [
        f"endpoint={endpoint}",
        f"required_successes={min_success}",
        f"successful={len(successes)}",
        *[
            f"{row['id']} {row['url']} -> {'ok' if row['ok'] else 'blocked'} {row.get('state') or row.get('error') or ''}"
            for row in probe_rows
        ],
    ]
    return {
        "status": "ready" if ready else "setup_required",
        "label": "Runtime ready" if ready else "Runtime setup needed",
        "kind": probe.get("kind"),
        "verifier": probe.get("label"),
        "path": "configured Moonraker printer URLs",
        "detected": bool(successes),
        "executed": True,
        "return_code": 0 if ready else 1,
        "capabilities": list(probe.get("capabilities") or []),
        "reason": None
        if ready
        else f"{probe.get('label')} needs {min_success} read-only printer API responses; got {len(successes)}.",
        "setup_steps": []
        if ready
        else [
            "Confirm T1 #1, T1 #2, and V400 are powered on and reachable over Moonraker.",
            "Keep S1 read-only/locked; it is not required for this fleet runtime gate.",
            "Run Verify again from Source OS.",
        ],
        "proof_source": "Hermes3D configured printer Moonraker read-only probe",
        "output_head": _head_lines(output),
        "registry_source": probe.get("registry_source") or "builtin",
        "proof_gate_version": probe.get("proof_gate_version") or "moonraker-fleet-verifier-v1",
    }


def _local_http_health_probe(probe: dict[str, Any]) -> dict[str, Any]:
    args = [str(item) for item in probe.get("args") or []]
    env_name = args[0].strip() if args else ""
    endpoint = args[1].strip() if len(args) > 1 and args[1].strip() else "/"
    expected = args[2].strip().lower() if len(args) > 2 else ""
    default_url = str(probe.get("default_url") or "").strip()
    probe_setup_steps = [
        str(step).strip() for step in (probe.get("setup_steps") or []) if str(step).strip()
    ]
    private_values = _private_runtime_env()
    base_url = (
        os.environ.get(env_name) or private_values.get(env_name) or str(probe.get("path") or "")
    ).strip()
    timeout = int(probe.get("timeout_s") or 3)
    if not env_name:
        return _local_http_health_response(
            probe,
            status="setup_required",
            path_value="local/private URL env",
            detected=False,
            executed=False,
            return_code=None,
            reason="Local HTTP health verifier is missing its environment variable binding.",
            output=["env=missing"],
            setup_steps=[
                "Repair the verifier metadata with an environment variable name for the local/private service URL.",
                "Run Verify again from Source OS.",
            ],
        )
    if not base_url:
        return _local_http_health_response(
            probe,
            status="setup_required",
            path_value=env_name,
            detected=False,
            executed=False,
            return_code=None,
            reason=f"{env_name} is not configured; no local health proof was attempted.",
            output=[
                f"env={env_name}",
                f"default_url={default_url or 'not_declared'}",
                "configured=false",
                "executed=false",
            ],
            setup_steps=(
                [
                    (
                        f"Set {env_name} in G:/private/.env to {default_url}."
                        if default_url
                        else f"Set {env_name} in G:/private/.env to the local/private service URL."
                    )
                ]
                + (
                    probe_setup_steps
                    or [
                        "Start the service outside the verifier; this probe never launches or mutates it."
                    ]
                )
                + ["Run Verify again from Source OS."]
            )[:6],
        )
    if not _is_local_private_url(base_url):
        return _local_http_health_response(
            probe,
            status="setup_required",
            path_value=env_name,
            detected=False,
            executed=False,
            return_code=None,
            reason=f"{env_name} must be an http(s) URL on localhost, a private LAN address, or a .local host.",
            output=[
                f"env={env_name}",
                f"url={_redact_text(base_url)}",
                "guard=blocked_non_local_url",
            ],
            setup_steps=[
                (
                    f"Point {env_name} at a trusted local/private Hermes3D service URL such as {default_url}."
                    if default_url
                    else f"Point {env_name} at a trusted local/private Hermes3D service URL."
                ),
                "Do not use public internet URLs for this Source OS runtime health verifier.",
                "Run Verify again from Source OS.",
            ],
        )
    health_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    try:
        request = urllib.request.Request(
            health_url, method="GET", headers={"Accept": "application/json,text/html,*/*"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            body = response.read(8192).decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return _local_http_health_response(
            probe,
            status="setup_required",
            path_value=env_name,
            detected=False,
            executed=True,
            return_code=1,
            reason=f"{probe.get('label')} did not return a read-only health response from the configured local URL.",
            output=[
                f"env={env_name}",
                f"url={_redact_text(health_url)}",
                f"error={type(exc).__name__}",
            ],
            setup_steps=(
                probe_setup_steps
                or [
                    f"Start or repair the local service configured by {env_name}.",
                    "Confirm the health/version endpoint is reachable with a GET request.",
                ]
            )[:5]
            + ["Run Verify again from Source OS."],
        )
    body_head = _redact_text(body[:500])
    token_ok = not expected or expected in body.lower()
    ready = 200 <= status_code < 400 and token_ok
    return _local_http_health_response(
        probe,
        status="ready" if ready else "setup_required",
        path_value=env_name,
        detected=ready,
        executed=True,
        return_code=0 if ready else 1,
        reason=None
        if ready
        else f"{probe.get('label')} responded but did not satisfy the expected read-only health/version proof.",
        output=[
            f"env={env_name}",
            f"url={_redact_text(health_url)}",
            f"http_status={status_code}",
            f"expected_token={expected or 'none'}",
            f"token_match={'true' if token_ok else 'false'}",
            f"body_head={body_head}",
        ],
        setup_steps=[]
        if ready
        else [
            f"Confirm {env_name} points at the correct local/private app endpoint.",
            "If the app is healthy but this endpoint is wrong, update the bounded verifier endpoint.",
            "Run Verify again from Source OS.",
        ],
    )


def _local_http_health_response(
    probe: dict[str, Any],
    *,
    status: str,
    path_value: str,
    detected: bool,
    executed: bool,
    return_code: int | None,
    reason: str | None,
    output: list[str],
    setup_steps: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "label": "Runtime ready" if status == "ready" else "Runtime setup needed",
        "kind": probe.get("kind"),
        "verifier": probe.get("label"),
        "path": path_value,
        "detected": detected,
        "executed": executed,
        "return_code": return_code,
        "capabilities": list(probe.get("capabilities") or []),
        "reason": reason,
        "setup_steps": setup_steps,
        "proof_source": "Hermes3D local/private read-only HTTP health probe" if executed else None,
        "output_head": _head_lines(output),
        "registry_source": probe.get("registry_source") or "builtin",
        "proof_gate_version": probe.get("proof_gate_version") or "local-http-health-verifier-v1",
    }


def _private_runtime_env() -> dict[str, str]:
    try:
        from hermes3d.services.agent_runtime import private_env

        return private_env()
    except Exception:
        return {}


def _is_local_private_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return address.is_loopback or address.is_private or address.is_link_local


def _local_service_port_state(url_value: str) -> dict[str, Any]:
    if not url_value:
        return {"status": "unknown", "reason": "no_url"}
    try:
        parsed = urllib.parse.urlparse(url_value)
    except ValueError:
        return {"status": "unknown", "reason": "invalid_url"}
    if not parsed.hostname:
        return {"status": "unknown", "reason": "missing_host"}
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname
    if not _is_local_private_url(url_value):
        return {"status": "blocked", "host": host, "port": port, "reason": "non_local_url"}
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return {"status": "listening", "host": host, "port": port}
    except OSError:
        return {"status": "free", "host": host, "port": port}


def _service_start_command_available(command: list[str], local_path: Path | None) -> bool:
    if not command:
        return False
    executable = command[0]
    if shutil.which(executable):
        return True
    if local_path:
        local_candidate = local_path / executable
        if local_candidate.exists():
            return True
        if executable.endswith(".bat") and (local_path / executable).exists():
            return True
    return False


def _configured_moonraker_printers() -> list[dict[str, str]]:
    try:
        from hermes3d.services.local_state import local_printers

        return [
            {
                "id": str(printer.get("id") or ""),
                "name": str(printer.get("name") or printer.get("id") or ""),
                "url": str(printer.get("moonraker_url") or ""),
                "locked": "true" if not printer.get("write_enabled") else "false",
            }
            for printer in local_printers(live=False)
            if printer.get("moonraker_url")
        ]
    except Exception:
        return [
            {"id": "flsun_t1_a", "name": "T1 #1", "url": "http://192.168.0.10", "locked": "false"},
            {"id": "flsun_t1_b", "name": "T1 #2", "url": "http://192.168.0.11", "locked": "false"},
            {"id": "flsun_s1", "name": "FLSUN S1", "url": "http://192.168.0.12", "locked": "true"},
            {
                "id": "flsun_v400",
                "name": "FLSUN V400",
                "url": "http://192.168.0.34",
                "locked": "false",
            },
        ]


def _probe_moonraker_endpoint(
    printers: list[dict[str, str]], *, endpoint: str, timeout: int
) -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(printers)))) as pool:
        futures = {
            pool.submit(
                _read_moonraker_endpoint, printer, endpoint=endpoint, timeout=timeout
            ): printer
            for printer in printers
        }
        return [future.result() for future in as_completed(futures)]


def _read_moonraker_endpoint(
    printer: dict[str, str], *, endpoint: str, timeout: int
) -> dict[str, Any]:
    url = f"{str(printer['url']).rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 0) or 0)
            body = response.read(4096).decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return {**printer, "url": url, "ok": False, "error": type(exc).__name__}
    state = _moonraker_state_from_body(body)
    return {**printer, "url": url, "ok": 200 <= status < 300, "status_code": status, "state": state}


def _moonraker_state_from_body(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "json_unavailable"
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return "result_unavailable"
    for key in ("klippy_state", "state", "state_message", "moonraker_version"):
        if result.get(key):
            return str(result[key])[:80]
    return "ok"


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _find_case_insensitive_child(root: Path, relative: str) -> Path | None:
    candidate = root / relative
    if candidate.exists():
        return candidate
    parts = [part for part in re.split(r"[\\/]+", relative) if part]
    current = root
    for part in parts:
        if not current.is_dir():
            return None
        lower = part.lower()
        match = next((child for child in current.iterdir() if child.name.lower() == lower), None)
        if not match:
            return None
        current = match
    return current if current.exists() else None


def _top_level_inventory(root: Path | None) -> list[str]:
    if not root or not root.is_dir():
        return []
    try:
        return sorted(child.name for child in root.iterdir() if child.name != ".git")[:40]
    except OSError:
        return []


@lru_cache(maxsize=1)
def _runtime_verifier_index() -> tuple[bool, dict[str, dict[str, Any]]]:
    try:
        from hermes3d.db.init import connect, init_db

        init_db()
        conn = connect()
        try:
            result = conn.execute(
                """
                SELECT module_id, label, runner_kind, tool_key, executable_path,
                       args, capabilities, execute, timeout_s, proof_gate_version
                  FROM module_runtime_verifiers
                 WHERE enabled = 1
                 ORDER BY module_id
                """
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return False, {}
    return True, {_module_id_from_row(row): _probe_from_row(row) for row in result}


def _module_id_from_row(row: Any) -> str:
    return str(row["module_id"])


def _probe_from_row(row: Any) -> dict[str, Any]:
    return {
        "tool_key": row["tool_key"],
        "label": row["label"],
        "path": row["executable_path"],
        "args": _json_list(row["args"]),
        "capabilities": _json_list(row["capabilities"]),
        "kind": row["runner_kind"],
        "execute": bool(row["execute"]),
        "timeout_s": int(row["timeout_s"] or 12),
        "proof_gate_version": row["proof_gate_version"] or "runtime-verifier-v1",
        "registry_source": "sqlite",
    }


def _json_list(value: Any) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _source_runtime_state(mod: dict[str, Any]) -> dict[str, Any]:
    local_path = mod.get("local_path")
    install_state = str(mod.get("install_state") or "unavailable")
    launch_kind = str(mod.get("launch_kind") or "unknown")
    if install_state in {"installed", "detected", "healthy"} and local_path:
        return {
            "status": "source_ready",
            "label": "Source ready",
            "kind": launch_kind,
            "verifier": "source checkout",
            "path": str(local_path),
            "detected": True,
            "executed": False,
            "return_code": None,
            "capabilities": [],
            "reason": "Source checkout is present; no safe module-specific runtime verifier is registered yet.",
            "setup_steps": module_setup_steps(mod),
            "proof_source": str(SOURCE_REGISTRY_AUDIT_PATH),
            "output_head": [],
        }
    if install_state == "source_available":
        return {
            "status": "not_installed",
            "label": "Install ready",
            "kind": launch_kind,
            "verifier": "source checkout",
            "path": str(local_path or ""),
            "detected": False,
            "executed": False,
            "return_code": None,
            "capabilities": [],
            "reason": "Source repository is known, but the configured local checkout is not present.",
            "setup_steps": [
                "Run Install from Source OS to clone the configured repository.",
                "Run Verify after install.",
            ],
            "proof_source": None,
            "output_head": [],
        }
    return {
        "status": "blocked",
        "label": "Source blocked",
        "kind": launch_kind,
        "verifier": "source checkout",
        "path": str(local_path or ""),
        "detected": False,
        "executed": False,
        "return_code": None,
        "capabilities": [],
        "reason": "No verified source repository or local checkout is available for this module.",
        "setup_steps": [
            "Add a verified source repository and local checkout path before install or runtime verification."
        ],
        "proof_source": None,
        "output_head": [],
    }


def _runner_status(*, runtime: dict[str, Any], mod: dict[str, Any], agent_executable: bool) -> str:
    if agent_executable:
        return "agent_cli_ready"
    runtime_status = str(runtime.get("status") or "blocked")
    verifier_kind = str(runtime.get("kind") or mod.get("launch_kind") or "unknown")
    proof_gate = str(runtime.get("proof_gate_version") or "")
    launch_kind = str(mod.get("launch_kind") or "unknown")
    if runtime_status == "ready" and (
        proof_gate == "desktop-launcher-metadata-v1" or verifier_kind == "desktop_app"
    ):
        return "launcher_metadata_only"
    if runtime_status == "ready" and verifier_kind in {
        "python_import",
        "python_source_import",
        "node_package",
    }:
        return "metadata_ready_needs_runner"
    if runtime_status == "ready" and verifier_kind in {"local_http_health", "moonraker_fleet"}:
        return "readonly_api_ready"
    if runtime_status == "ready" and verifier_kind == "source_inventory":
        return "source_reference_only"
    if runtime_status == "setup_required":
        return "runtime_repair_required"
    if runtime_status == "not_installed":
        return "source_install_available"
    if runtime_status == "source_ready" and launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        return "cli_runner_gap"
    if runtime_status == "source_ready" and launch_kind in CLI_POSSIBLE_LAUNCH_KINDS:
        return f"{launch_kind}_runner_gap"
    if runtime_status == "source_ready":
        return "runner_not_registered"
    return "blocked"


def _required_verifier_family(launch_kind: str, verifier_kind: str, runner_status: str) -> str:
    if runner_status == "agent_cli_ready":
        return "registered_agent_cli"
    if runner_status == "launcher_metadata_only":
        return "cli_api_or_desktop_bridge_smoke"
    if runner_status == "metadata_ready_needs_runner":
        return "dry_run_worker_smoke"
    if runner_status == "readonly_api_ready":
        return "read_only_api_runner_contract"
    if runner_status == "source_reference_only":
        return "reference_parser_or_adapter_contract"
    if launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        return "cli_version_help_or_dry_run"
    if launch_kind == "python_worker":
        return "python_import_or_module_cli"
    if launch_kind == "npm_package":
        return "node_package_metadata_or_script_help"
    if launch_kind == "service":
        return "local_health_endpoint_or_process_probe"
    if launch_kind == "web_app":
        return "local_http_health_or_route_smoke"
    if launch_kind == "gpu_worker":
        return "dependency_model_cache_gpu_probe"
    if launch_kind == "firmware_source":
        return "read_only_firmware_source_inventory"
    if verifier_kind == "source_inventory":
        return "reference_parser_or_adapter_contract"
    return "module_specific_safe_verifier"


def _runner_blocked_reason(
    *, runtime: dict[str, Any], runner_status: str, required_family: str
) -> str | None:
    if runner_status == "agent_cli_ready":
        return None
    reason = str(runtime.get("reason") or "").strip()
    if reason:
        return reason
    return f"Runner contract needs {required_family} before Hermes Agents can execute this app."


def _safe_runner_actions(runtime: dict[str, Any], *, agent_executable: bool) -> list[str]:
    actions = ["verify", "setup_plan"]
    if agent_executable:
        actions.extend(["version_or_help", "dry_run_smoke_plan"])
    elif runtime.get("status") == "ready":
        actions.append("read_metadata")
    return actions


def _runner_acceptance_gate(module_id: str, runner_status: str, required_family: str) -> str:
    if runner_status == "agent_cli_ready":
        return f"`/api/modules/{module_id}/runtime/verify` returns ready with executed=true and a registered proof gate."
    return f"Register {required_family}; then `/api/modules/{module_id}/runtime/verify` must return ready with proof before any agent execution."


def _local_tooling_record(tool_key: str) -> dict[str, Any]:
    if not LOCAL_TOOLING_AUDIT_PATH.exists():
        return {}
    try:
        audit = json.loads(LOCAL_TOOLING_AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    tools = audit.get("tools") if isinstance(audit, dict) else None
    record = tools.get(tool_key) if isinstance(tools, dict) else None
    return record if isinstance(record, dict) else {}


def _run_runtime_command(
    path: Path | None, args: list[str], *, timeout: int = 12
) -> subprocess.CompletedProcess[str]:
    if path is None:
        return subprocess.CompletedProcess(
            [], 127, stdout="", stderr="runtime verifier path is not configured"
        )
    cmd = [str(path), *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout=str(exc.stdout or ""),
            stderr=f"runtime probe timed out after {timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=str(exc))


def _run_checked_command(
    cmd: list[str], *, timeout: int, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False, env=env
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout=str(exc.stdout or ""),
            stderr=f"runtime probe timed out after {timeout}s",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=str(exc))


def _redact_text(value: str | None) -> str:
    return SECRET_RE.sub(
        lambda match: f"{match.group(1) or match.group(3) or ''}[REDACTED]", value or ""
    )


def _head_lines(value: str | list[str], *, max_lines: int = 25, max_chars: int = 240) -> list[str]:
    lines = value.splitlines() if isinstance(value, str) else [str(item) for item in value]
    trimmed: list[str] = []
    for line in lines[:max_lines]:
        if len(line) > max_chars:
            trimmed.append(f"{line[:max_chars]}...")
        else:
            trimmed.append(line)
    return trimmed
