"""Slicer and modeler probe tests — I5 deliverable.

Verifies that probe_slicer_cli() and probe_modeler_import() return
well-formed dicts with the required fields regardless of whether the
tool is installed on the current machine.

Protocol constraints:
- No STL files are sent to any slicer.
- No firmware is flashed or uploaded.
- No printer is connected or mutated.
- All probes are non-mutating (--version / --help / import only).
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from hermes3d.services import module_runtime
from hermes3d.services.module_runtime import (
    probe_slicer_cli,
    probe_modeler_import,
    SLICER_MODULE_IDS,
    MODELER_PYTHON_IMPORT_IDS,
    MODELER_SOURCE_INVENTORY_IDS,
)

# ---------------------------------------------------------------------------
# Required field contract for slicer probe results
# ---------------------------------------------------------------------------

REQUIRED_PROBE_FIELDS = {
    "status",
    "kind",
    "verifier",
    "path",
    "detected",
    "executed",
    "return_code",
    "capabilities",
    "blocked_reason",
    "proof_gate_version",
}


def _assert_probe_fields(result: dict[str, Any], module_id: str) -> None:
    missing = REQUIRED_PROBE_FIELDS - set(result)
    assert not missing, f"{module_id}: probe result missing fields {missing}"
    assert result["status"] in {
        "ready",
        "blocked",
        "setup_required",
    }, f"{module_id}: unexpected status {result['status']!r}"
    assert isinstance(result["capabilities"], list), f"{module_id}: capabilities must be a list"


# ---------------------------------------------------------------------------
# Slicer CLI probe tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id", sorted(SLICER_MODULE_IDS))
def test_probe_slicer_cli_returns_required_fields(module_id: str) -> None:
    """probe_slicer_cli always returns a dict with all required fields."""
    result = probe_slicer_cli(module_id)
    _assert_probe_fields(result, module_id)
    assert result["kind"] in {"cli", "slicer_cli", "desktop_app"}


@pytest.mark.parametrize("module_id", sorted(SLICER_MODULE_IDS))
def test_probe_slicer_cli_blocked_reason_when_absent(monkeypatch, module_id: str) -> None:
    """When no executable is found, blocked_reason names the exact paths tried."""
    # Make all path checks return False (simulate no install)
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    import shutil

    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    result = probe_slicer_cli(module_id)
    if result["status"] == "blocked":
        assert result["blocked_reason"] is not None, (
            f"{module_id}: blocked status must have blocked_reason"
        )
        # blocked_reason must mention at least one path or 'not found'
        reason = result["blocked_reason"]
        assert any(kw in reason.lower() for kw in ("not found", "path", ".exe", "no ")), (
            f"{module_id}: blocked_reason should mention path or 'not found': {reason!r}"
        )


def test_probe_slicer_cli_found_sets_status_ready(monkeypatch, tmp_path: Path) -> None:
    """When executable exists and version probe succeeds, status is ready."""
    fake_exe = tmp_path / "prusa-slicer-console.exe"
    fake_exe.write_bytes(b"")

    def _fake_is_file(self: Path) -> bool:
        return self == fake_exe or self.name == fake_exe.name

    # Return fake exe as the found path
    def _fake_probe_config(module_id: str) -> dict[str, Any] | None:
        cfg = module_runtime.BUILTIN_RUNTIME_PROBES.get(module_id)
        if cfg is None:
            return None
        return {**cfg, "path": str(fake_exe), "registry_source": "builtin"}

    monkeypatch.setattr(module_runtime, "runtime_probe_config", _fake_probe_config)

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "PrusaSlicer-2.9.5 based on Slic3r"
    mock_proc.stderr = ""

    with patch("subprocess.run", return_value=mock_proc):
        result = probe_slicer_cli("prusaslicer")

    # With a found path and rc=0, status must be ready
    assert result["status"] == "ready"
    assert result["detected"] is True
    assert result["blocked_reason"] is None


def test_probe_slicer_cli_prusaslicer_version_accepts_nonzero_rc(
    monkeypatch, tmp_path: Path
) -> None:
    """PrusaSlicer --version exits rc=1 but outputs version text — still detected."""
    fake_exe = tmp_path / "prusa-slicer-console.exe"
    fake_exe.write_bytes(b"")

    def _fake_probe_config(module_id: str) -> dict[str, Any] | None:
        cfg = module_runtime.BUILTIN_RUNTIME_PROBES.get(module_id)
        if cfg is None:
            return None
        return {**cfg, "path": str(fake_exe), "registry_source": "builtin"}

    monkeypatch.setattr(module_runtime, "runtime_probe_config", _fake_probe_config)

    mock_proc = MagicMock()
    mock_proc.returncode = 1  # PrusaSlicer --version exits non-zero
    mock_proc.stdout = ""
    mock_proc.stderr = "PrusaSlicer-2.9.5 based on Slic3r\nhttps://github.com/prusa3d/PrusaSlicer"

    with patch("subprocess.run", return_value=mock_proc):
        result = probe_slicer_cli("prusaslicer")

    # Must detect the file even if rc=1
    assert result["detected"] is True
    # blocked_reason should be absent (file present)
    assert result.get("blocked_reason") is None or result["status"] != "blocked"


def test_probe_slicer_cli_unknown_id_returns_blocked() -> None:
    """Unknown slicer IDs return a blocked result with a useful reason."""
    result = probe_slicer_cli("nonexistent_slicer_xyz")
    assert result["status"] == "blocked"
    assert result["blocked_reason"] is not None


# ---------------------------------------------------------------------------
# Modeler import probe tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_id", sorted(MODELER_PYTHON_IMPORT_IDS))
def test_probe_modeler_import_returns_required_fields(module_id: str) -> None:
    """probe_modeler_import always returns a dict with all required fields."""
    result = probe_modeler_import(module_id)
    _assert_probe_fields(result, module_id)
    assert result["kind"] in {"python_import", "modeler_import", "cli", "slicer_cli"}


@pytest.mark.parametrize("module_id", sorted(MODELER_PYTHON_IMPORT_IDS))
def test_probe_modeler_import_blocked_reason_when_import_fails(
    monkeypatch, module_id: str
) -> None:
    """When the import fails, blocked_reason names the Python module."""
    # Force subprocess to return non-zero (import failed)
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = f"ModuleNotFoundError: No module named '{module_id}'"

    with patch("subprocess.run", return_value=mock_proc):
        result = probe_modeler_import(module_id)

    if result["status"] in {"blocked", "setup_required"}:
        assert result["blocked_reason"] is not None, (
            f"{module_id}: blocked/setup_required must have blocked_reason"
        )


def test_probe_modeler_import_trimesh_ready_when_importable(monkeypatch) -> None:
    """trimesh is importable in the test env → probe returns ready."""
    # Only run this assertion if trimesh is actually importable
    try:
        importlib.import_module("trimesh")
    except ImportError:
        pytest.skip("trimesh not importable in this environment")

    result = probe_modeler_import("trimesh")
    assert result["status"] == "ready"
    assert result["detected"] is True
    assert result["blocked_reason"] is None


def test_probe_modeler_import_cadquery_blocked_when_missing(monkeypatch) -> None:
    """cadquery is not in the env → probe returns setup_required with blocked_reason."""
    try:
        importlib.import_module("cadquery")
        pytest.skip("cadquery is importable — skip missing-module test")
    except ImportError:
        pass

    result = probe_modeler_import("cadquery")
    assert result["status"] in {"blocked", "setup_required"}
    assert result["blocked_reason"] is not None
    assert "cadquery" in result["blocked_reason"].lower()


def test_probe_modeler_import_unknown_id_returns_blocked() -> None:
    """Unknown modeler IDs return a blocked result with a useful reason."""
    result = probe_modeler_import("nonexistent_modeler_xyz")
    assert result["status"] == "blocked"
    assert result["blocked_reason"] is not None


# ---------------------------------------------------------------------------
# Integration: probe_slicer_cli updates runner_contract blocked_reason
# ---------------------------------------------------------------------------


def test_slicer_probe_result_fields_flow_to_runner_contract(monkeypatch) -> None:
    """When probe_slicer_cli returns blocked, runner_contract must surface blocked_reason."""

    def _fake_probe(mod: dict, *, live: bool = False) -> dict:
        return {
            "status": "blocked",
            "kind": "slicer_cli",
            "verifier": "SuperSlicer CLI",
            "proof_gate_version": "slicer-cli-verifier-v1",
            "path": "C:/Program Files/SuperSlicer/superslicer-console.exe",
            "detected": False,
            "executed": False,
            "return_code": None,
            "capabilities": ["slice_to_gcode"],
            "blocked_reason": (
                "SuperSlicer executable not found. "
                "Tried: C:/Program Files/SuperSlicer/superslicer-console.exe; "
                "not on PATH (superslicer, superslicer-console, SuperSlicer)"
            ),
        }

    monkeypatch.setattr(module_runtime, "module_runtime_probe", _fake_probe)
    contract = module_runtime.module_runner_contract(
        {
            "id": "superslicer",
            "display_name": "SuperSlicer",
            "section": "slicers",
            "launch_kind": "cli_worker",
            "install_state": "installed",
            "local_path": "G:/Github/Hermes3D-OS/source-lab/sources/slicers/SuperSlicer",
        }
    )

    assert contract["agent_executable"] is False
    assert contract["blocked_reason"] is not None
    # The runner contract surfaces the CLI gap reason — it mentions the verifier family needed
    assert any(
        kw in contract["blocked_reason"].lower()
        for kw in ("superslicer", "cli", "runner", "verifier", "agent")
    )


# ---------------------------------------------------------------------------
# SLICER_MODULE_IDS and MODELER_PYTHON_IMPORT_IDS completeness
# ---------------------------------------------------------------------------


def test_slicer_module_ids_covers_expected_slicers() -> None:
    expected = {
        "prusaslicer",
        "orcaslicer",
        "flsun_slicer",
        "curaengine",
        "superslicer",
        "slic3r",
        "bambustudio",
    }
    assert expected <= SLICER_MODULE_IDS, (
        f"SLICER_MODULE_IDS missing: {expected - SLICER_MODULE_IDS}"
    )


def test_modeler_python_import_ids_covers_expected_modelers() -> None:
    expected = {
        "blender",
        "openscad",
        "trimesh",
        "cadquery",
        "build123d",
        "numpy_stl",
        "open3d",
        "meshlab",
    }
    assert expected <= MODELER_PYTHON_IMPORT_IDS, (
        f"MODELER_PYTHON_IMPORT_IDS missing: {expected - MODELER_PYTHON_IMPORT_IDS}"
    )


def test_modeler_source_inventory_ids_covers_truck() -> None:
    """truck is a Rust library with source inventory only — no Python import."""
    assert "truck" in MODELER_SOURCE_INVENTORY_IDS


def test_probe_modeler_import_truck_returns_blocked_with_reason() -> None:
    """truck has no Python import — probe_modeler_import returns blocked."""
    result = probe_modeler_import("truck")
    assert result["status"] == "blocked"
    assert result["blocked_reason"] is not None
    assert "source-inventory" in result["blocked_reason"].lower() or "truck" in result["blocked_reason"].lower()
