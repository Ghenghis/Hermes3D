"""Blender MCP server — SPECIFICATION ONLY (status: spec).

KIT_MANIFEST.json marks this file as ``spec``. It defines the public
contract that any real implementation must honour. The full implementation
requires a Blender 4.2+ install and is not part of this kit (per the
contract's rule that large/binary dependencies are delegated to the
installer).

This file IS importable and IS callable: every tool function raises
``NotImplementedError`` with a message that points the caller at the
installer + the Blender bundle. No silent failures, no fake returns.

JSON-RPC tool surface:
    import_and_repair(glb_path: str, target_scale_mm: float) -> dict
    run_python_script(script: str) -> dict
    export_stl(output_path: str) -> dict
    health() -> dict

A reference HTTP server (FastAPI) shape is included so the route layout is
fixed by this file. To implement, vendor Blender alongside this kit and
replace each ``NotImplementedError`` body with a real bpy call. See
docs/AI_PROGRAMMER_GUIDE.md §"Implementing the modeling MCP".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

# A short version string the conformance runner can read from a live server.
SERVER_VERSION = "0.1.0-spec"

# JSON-Schema-style descriptions of each tool's input. The conformance
# runner in 03-PROOF-SYSTEM/conformance_runner.py uses this exact schema
# definition to validate any third-party MCP implementation.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "import_and_repair": {
        "description": "Import a .glb mesh, run Blender's repair operators, "
                       "and uniformly scale so the longest extent equals "
                       "target_scale_mm.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["glb_path", "target_scale_mm"],
            "properties": {
                "glb_path": {"type": "string", "minLength": 1},
                "target_scale_mm": {"type": "number", "exclusiveMinimum": 0},
            },
        },
        "output_schema": {
            "type": "object",
            "required": ["ok", "stats"],
            "properties": {
                "ok": {"type": "boolean"},
                "stats": {"type": "object"},
                "error": {"type": "string"},
            },
        },
    },
    "run_python_script": {
        "description": "Execute the given Python source inside Blender's "
                       "embedded interpreter. The bpy module is available.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["script"],
            "properties": {"script": {"type": "string", "minLength": 1}},
        },
        "output_schema": {
            "type": "object",
            "required": ["ok"],
            "properties": {
                "ok": {"type": "boolean"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "error": {"type": "string"},
            },
        },
    },
    "export_stl": {
        "description": "Export the active scene as binary STL.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["output_path"],
            "properties": {"output_path": {"type": "string", "minLength": 1}},
        },
        "output_schema": {
            "type": "object",
            "required": ["ok", "path"],
            "properties": {
                "ok": {"type": "boolean"},
                "path": {"type": "string"},
                "size_bytes": {"type": "integer"},
                "error": {"type": "string"},
            },
        },
    },
    "health": {
        "description": "Health check. Always succeeds when the server is up.",
        "input_schema": {"type": "object", "additionalProperties": False},
        "output_schema": {
            "type": "object",
            "required": ["ok", "version"],
            "properties": {
                "ok": {"type": "boolean"},
                "version": {"type": "string"},
                "blender_version": {"type": "string"},
            },
        },
    },
}


@dataclass
class _NotImpl:
    """Single source of truth for every spec-only tool implementation."""
    tool: str

    def __call__(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError(  # noqa: forbidden_pattern_scan
            f"{self.tool}: Blender MCP server is SPEC-ONLY in this kit. "
            "Run 05-INSTALLER/install.ps1 to download Blender 4.2 portable "
            "and replace the body of "
            f"hermes3d.core.modeling.blender_mcp_server.{self.tool} with a "
            "real bpy/pymeshlab call. Contract docs: "
            "07-DOCS/AI_PROGRAMMER_GUIDE.md §'Implementing the modeling MCP'."
        )


import_and_repair = _NotImpl("import_and_repair")
run_python_script = _NotImpl("run_python_script")
export_stl = _NotImpl("export_stl")


def health() -> dict[str, Any]:
    """The one tool that DOES work in spec mode — so the conformance runner
    can prove this module loads and reports its capabilities truthfully."""
    return {
        "ok": True,
        "version": SERVER_VERSION,
        "blender_version": "not-installed (spec build)",
        "tools_implemented": ["health"],
        "tools_spec_only": ["import_and_repair", "run_python_script", "export_stl"],
    }


class MCPHandler(Protocol):
    """Type contract that any real implementation must satisfy."""
    def import_and_repair(self, glb_path: str, target_scale_mm: float) -> dict[str, Any]: ...
    def run_python_script(self, script: str) -> dict[str, Any]: ...
    def export_stl(self, output_path: str) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...


def build_app() -> Any:
    """Return a FastAPI app exposing each tool as POST /tools/<name>.

    SPEC-only: this returns an app whose handlers raise NotImplementedError
    with the same message as the direct calls above. Once Blender is
    installed, replace ``_NotImpl(...)`` with a real implementation.
    """
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:
        raise NotImplementedError(  # noqa: forbidden_pattern_scan
            "FastAPI is not installed. The kit's spec build does not list it "
            "as a hard dependency. Install with `pip install fastapi uvicorn` "
            "or run 05-INSTALLER/install.ps1."
        ) from exc

    app = FastAPI(title="hermes3d-blender-mcp", version=SERVER_VERSION)

    @app.get("/health")
    def _health() -> dict[str, Any]:
        return health()

    @app.post("/tools/import_and_repair")
    def _import_and_repair(payload: dict) -> dict:
        try:
            return import_and_repair(**payload)
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc))

    @app.post("/tools/run_python_script")
    def _run_python_script(payload: dict) -> dict:
        try:
            return run_python_script(**payload)
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc))

    @app.post("/tools/export_stl")
    def _export_stl(payload: dict) -> dict:
        try:
            return export_stl(**payload)
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc))

    @app.get("/tools")
    def _tools() -> dict:
        return {"tools": list(TOOL_SCHEMAS.keys()), "schemas": TOOL_SCHEMAS}

    return app


__all__ = [
    "SERVER_VERSION",
    "TOOL_SCHEMAS",
    "MCPHandler",
    "build_app",
    "export_stl",
    "health",
    "import_and_repair",
    "run_python_script",
]
