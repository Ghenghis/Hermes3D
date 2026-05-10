"""Source + runtime verifier for Hermes3D 3D-modeler tools.

Lane H3D-CLAUDE-SOURCE-MODELERS. Verifies six modeler tools --
Blender, OpenSCAD, FreeCAD (CLI probes) and CadQuery, build123d,
trimesh (Python-import probes) -- without performing any heavy
operation.  Strict no-download rules:

* CLI tools are probed with subprocess.run(['<exe>', '--version']).
* Python packages are probed with ``pip show <pkg>`` (no install).
* Executable search uses schema-declared ``executable_candidates`` list
  plus ``shutil.which``.
* Additional packages (numpy-stl, open3d) are probed alongside trimesh.

Outputs proof at:
    03_implementation/proof/MODELERS_VERIFY_2026-05-06.json

Exits 0 even if individual probes fail -- "honest not_found" is the
correct answer; the proof JSON encodes the per-modeler truth.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = IMPLEMENTATION_ROOT / "adapter_registry" / "schemas"
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"
PROOF_PATH = PROOF_DIR / "MODELERS_VERIFY_2026-05-06.json"

CLI_TIMEOUT_S = 12
PIP_TIMEOUT_S = 8

# ---------------------------------------------------------------------------
# Modeler registry
# ---------------------------------------------------------------------------

MODELERS: list[dict[str, Any]] = [
    {
        "id": "blender",
        "schema": "blender_bridge.schema.json",
        "label": "Blender",
        "kind": "cli",
        "executable_candidates": [
            "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe",
            "C:/Program Files/Blender Foundation/Blender 4.4/blender.exe",
            "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe",
            "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe",
            "blender",
        ],
        "version_args": ["--version"],
        "version_regex": r"Blender\s+(\d+\.[0-9]+\.?[0-9]*)",
        "help_args": ["--help"],
        "expected_help_substr": "Blender",
    },
    {
        "id": "openscad",
        "schema": "openscad_worker.schema.json",
        "label": "OpenSCAD",
        "kind": "cli",
        "executable_candidates": [
            "C:/Program Files/OpenSCAD/openscad.exe",
            "C:/Program Files/OpenSCAD (Nightly)/openscad.exe",
            "openscad",
        ],
        "version_args": ["--version"],
        "version_regex": r"OpenSCAD\s+version\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
        "help_args": ["--help"],
        "expected_help_substr": "Usage",
    },
    {
        "id": "freecad",
        "schema": "freecad_bridge.schema.json",
        "label": "FreeCAD",
        "kind": "cli",
        "executable_candidates": [
            "C:/Program Files/FreeCAD 1.0/bin/FreeCAD.exe",
            "C:/Program Files/FreeCAD 0.21/bin/FreeCAD.exe",
            "C:/Program Files/FreeCAD 0.20/bin/FreeCAD.exe",
            "FreeCAD",
            "freecad",
        ],
        "version_args": ["--version"],
        "version_regex": r"FreeCAD\s+(\d+\.[0-9]+(?:\.[0-9]+)?)",
        "help_args": ["--help"],
        "expected_help_substr": "FreeCAD",
    },
    {
        "id": "cadquery",
        "schema": "cadquery_worker.schema.json",
        "label": "CadQuery",
        "kind": "python_import",
        "pip_packages": ["cadquery"],
        "import_module": "cadquery",
        "version_attr": "__version__",
        "smoke_expression": "import cadquery as cq; r = cq.Workplane('XY').box(1,1,1); assert r is not None",
    },
    {
        "id": "build123d",
        "schema": "build123d_worker.schema.json",
        "label": "build123d",
        "kind": "python_import",
        "pip_packages": ["build123d"],
        "import_module": "build123d",
        "version_attr": "__version__",
        "smoke_expression": "from build123d import Box; b = Box(1,1,1); assert b is not None",
    },
    {
        "id": "trimesh",
        "schema": "trimesh_worker.schema.json",
        "label": "trimesh + numpy-stl + open3d",
        "kind": "python_import",
        "pip_packages": ["trimesh", "numpy-stl", "open3d"],
        "import_module": "trimesh",
        "version_attr": "__version__",
        "smoke_expression": "import trimesh; m = trimesh.creation.box(extents=(1,1,1)); assert m is not None",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    pip_cmd = _resolve_pip_command()
    results: list[dict[str, Any]] = []
    for modeler in MODELERS:
        if modeler["kind"] == "cli":
            results.append(_verify_cli_modeler(modeler))
        else:
            results.append(_verify_python_modeler(modeler, pip_cmd=pip_cmd))

    proof = {
        "$schema": "hermes3d://proof/modelers_verify_v1",
        "lane": "H3D-CLAUDE-SOURCE-MODELERS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_platform": sys.platform,
        "pip_command": pip_cmd,
        "policy": {
            "downloads": "forbidden",
            "cli": "version + help probe only (no heavy render)",
            "pip": "show only (no install)",
            "import": "pip show + python -c (no side effects)",
        },
        "modelers": results,
        "summary": _summarize(results),
    }
    PROOF_PATH.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
    print(str(PROOF_PATH))
    print(json.dumps(proof["summary"], indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# CLI verifier
# ---------------------------------------------------------------------------


def _verify_cli_modeler(modeler: dict[str, Any]) -> dict[str, Any]:
    schema_path = SCHEMAS_DIR / modeler["schema"]
    schema = _load_schema(schema_path)

    exe = _find_executable(modeler["executable_candidates"])
    if not exe:
        return {
            "id": modeler["id"],
            "label": modeler["label"],
            "kind": "cli",
            "schema_path": _rel(schema_path),
            "schema_valid": schema is not None,
            "executable_found": None,
            "installed": False,
            "status": "not_found",
            "version_probe": {
                "found": False,
                "reason": "executable not found on PATH or known locations",
            },
            "help_probe": {"found": False, "reason": "executable not found"},
            "proof_gate_version": "modelers-source-runtime-verifier-v1",
        }

    version_probe = _probe_version_cli(
        exe=exe,
        args=modeler["version_args"],
        regex=modeler["version_regex"],
    )
    help_probe = _probe_help_cli(
        exe=exe,
        args=modeler.get("help_args", ["--help"]),
        expected_substr=modeler.get("expected_help_substr", ""),
    )
    installed = bool(version_probe.get("found"))

    return {
        "id": modeler["id"],
        "label": modeler["label"],
        "kind": "cli",
        "schema_path": _rel(schema_path),
        "schema_valid": schema is not None,
        "executable_found": exe,
        "installed": installed,
        "status": "found" if installed else "no_version_output",
        "version_probe": version_probe,
        "help_probe": help_probe,
        "proof_gate_version": "modelers-source-runtime-verifier-v1",
    }


def _find_executable(candidates: list[str]) -> str | None:
    # Check each candidate path and PATH via shutil.which
    for candidate in candidates:
        p = Path(candidate)
        if p.is_absolute():
            if p.is_file():
                return str(p)
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _probe_version_cli(
    exe: str,
    args: list[str],
    regex: str,
) -> dict[str, Any]:
    cmd = [exe, *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"found": False, "reason": "timeout", "timeout_s": CLI_TIMEOUT_S}
    except OSError as exc:
        return {"found": False, "reason": f"OSError: {exc}"}

    combined = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(regex, combined, re.IGNORECASE)
    version = m.group(1) if m else None
    return {
        "found": bool(version),
        "version": version,
        "return_code": proc.returncode,
        "stdout_head": _head_lines(proc.stdout or ""),
        "stderr_head": _head_lines(proc.stderr or ""),
    }


def _probe_help_cli(
    exe: str,
    args: list[str],
    expected_substr: str,
) -> dict[str, Any]:
    cmd = [exe, *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "timeout_s": CLI_TIMEOUT_S}
    except OSError as exc:
        return {"ok": False, "reason": f"OSError: {exc}"}

    combined = (proc.stdout or "") + (proc.stderr or "")
    contains = expected_substr.lower() in combined.lower() if expected_substr else True
    return {
        "ok": contains,
        "return_code": proc.returncode,
        "contains_expected_substr": contains,
        "expected_substr": expected_substr,
        "output_head": _head_lines(combined),
    }


# ---------------------------------------------------------------------------
# Python-import verifier
# ---------------------------------------------------------------------------


def _verify_python_modeler(
    modeler: dict[str, Any],
    pip_cmd: list[str] | None,
) -> dict[str, Any]:
    schema_path = SCHEMAS_DIR / modeler["schema"]
    schema = _load_schema(schema_path)

    pip_probes: list[dict[str, Any]] = []
    for pkg in modeler.get("pip_packages", []):
        pip_probes.append({"package": pkg, **_probe_pip_show(pkg, pip_cmd=pip_cmd)})

    primary_pkg = modeler.get("pip_packages", [None])[0]
    primary_probe = next((p for p in pip_probes if p["package"] == primary_pkg), {})
    installed = bool(primary_probe.get("installed"))

    smoke_result: dict[str, Any] | None = None
    if installed and modeler.get("smoke_expression"):
        smoke_result = _probe_python_smoke(modeler["smoke_expression"])

    return {
        "id": modeler["id"],
        "label": modeler["label"],
        "kind": "python_import",
        "schema_path": _rel(schema_path),
        "schema_valid": schema is not None,
        "installed": installed,
        "status": "found" if installed else "not_found",
        "pip_probes": pip_probes,
        "smoke_probe": smoke_result,
        "proof_gate_version": "modelers-source-runtime-verifier-v1",
    }


def _probe_pip_show(package: str, *, pip_cmd: list[str] | None) -> dict[str, Any]:
    if not pip_cmd:
        return {"installed": False, "reason": "no pip command available"}
    cmd = [*pip_cmd, "show", package]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PIP_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"installed": False, "reason": "timeout", "timeout_s": PIP_TIMEOUT_S}
    except OSError as exc:
        return {"installed": False, "reason": f"OSError: {exc}"}

    output = proc.stdout or ""
    version: str | None = None
    location: str | None = None
    for line in output.splitlines():
        if line.lower().startswith("version:"):
            version = line.split(":", 1)[1].strip()
        elif line.lower().startswith("location:"):
            location = line.split(":", 1)[1].strip()
    return {
        "installed": proc.returncode == 0 and bool(version),
        "return_code": proc.returncode,
        "version": version,
        "location": location,
    }


def _probe_python_smoke(expression: str) -> dict[str, Any]:
    """Run a smoke expression with ``python -c`` and report pass/fail."""
    cmd = [sys.executable, "-c", expression]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout"}
    except OSError as exc:
        return {"ok": False, "reason": f"OSError: {exc}"}
    return {
        "ok": proc.returncode == 0,
        "return_code": proc.returncode,
        "stderr_head": _head_lines(proc.stderr or ""),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_pip_command() -> list[str] | None:
    candidates: list[list[str]] = [[sys.executable, "-m", "pip"]]
    pip_path = shutil.which("pip")
    if pip_path:
        candidates.append([pip_path])
    for cmd in candidates:
        try:
            proc = subprocess.run(
                [*cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=PIP_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return cmd
    return None


def _load_schema(schema_path: Path) -> dict[str, Any] | None:
    if not schema_path.is_file():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(IMPLEMENTATION_ROOT))
    except ValueError:
        return str(p)


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    found = [r["id"] for r in results if r.get("installed")]
    not_found = [r["id"] for r in results if not r.get("installed")]
    return {
        "total": len(results),
        "found": found,
        "not_found": not_found,
    }


def _head_lines(value: str, *, max_lines: int = 6, max_chars: int = 240) -> list[str]:
    lines = value.splitlines()
    return [
        line if len(line) <= max_chars else f"{line[:max_chars]}..." for line in lines[:max_lines]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
