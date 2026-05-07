"""Slicer CLI verifier tests.

All tests are read-only (--version / --help / metadata only).
NEVER slices a model. NEVER sends data to a printer.

Tests use the SLICERS_VERIFY_2026-05-06.json proof file as ground truth,
and also run live probes when the executables are present.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add the scripts directory to path so we can import verify_slicers
# tests/source_lab/ -> tests/ -> 03_implementation/ -> (worktree root)
_IMPL_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _IMPL_ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from verify_slicers import _PROBES, _extract_version, _resolve_exe, probe_slicer, run_all_probes  # noqa: E402

_PROOF_FILE = _IMPL_ROOT / "proof" / "SLICERS_VERIFY_2026-05-06.json"


# ---------------------------------------------------------------------------
# Unit tests — logic only, no filesystem required
# ---------------------------------------------------------------------------


def test_probes_table_completeness() -> None:
    """All required slicers are registered."""
    ids = {p["id"] for p in _PROBES}
    required = {"prusaslicer", "orcaslicer", "flsun_slicer", "curaengine", "superslicer", "slic3r", "bambustudio"}
    assert required.issubset(ids), f"Missing probe entries: {required - ids}"


def test_probes_no_destructive_args() -> None:
    """No probe may contain slicing or output flags."""
    forbidden = {
        "--export-gcode", "--gcode", "-g", "--slice", "--export-sla",
        "--output", "-o", "--gcode-output-folder", "slice",
    }
    for entry in _PROBES:
        args_lower = {str(a).lower() for a in entry.get("args") or []}
        bad = args_lower & forbidden
        assert not bad, f"Probe {entry['id']} has destructive arg(s): {bad}"


def test_extract_version_prusaslicer() -> None:
    text = "PrusaSlicer-2.9.5-beta2 based on Slic3r"
    assert _extract_version(text, r"PrusaSlicer[- ]([\d.]+(?:-\w+\d*)?)") == "2.9.5-beta2"


def test_extract_version_curaengine() -> None:
    text = "Cura_SteamEngine version 5.12.1\nCopyright (C) 2024"
    assert _extract_version(text, r"Cura_SteamEngine version ([\d.]+)") == "5.12.1"


def test_extract_version_flsun() -> None:
    text = "FlsunSlicer-2.0.4.0:\nUsage: flsun-slicer"
    assert _extract_version(text, r"FlsunSlicer[- ]([\d.]+(?:\.\w+)?)") == "2.0.4.0"


def test_extract_version_no_match() -> None:
    assert _extract_version("nothing here", r"PrusaSlicer[- ]([\d.]+)") is None


def test_extract_version_empty_pattern() -> None:
    assert _extract_version("PrusaSlicer-2.9", "") is None


def test_resolve_exe_missing() -> None:
    """Non-existent paths return None."""
    result = _resolve_exe(["C:/does/not/exist/slicer.exe", "does_not_exist_on_path_xyz123"])
    assert result is None


def test_probe_slicer_not_found_structure() -> None:
    """probe_slicer returns correct schema for a not-found slicer."""
    fake_entry = {
        "id": "test_not_found",
        "label": "TestSlicer",
        "candidates": ["C:/does/not/exist.exe"],
        "args": ["--help"],
        "version_re": r"TestSlicer ([\d.]+)",
        "timeout_s": 5,
    }
    result = probe_slicer(fake_entry)
    assert result["id"] == "test_not_found"
    assert result["name"] == "TestSlicer"
    assert result["status"] == "not_found"
    assert result["version"] is None
    assert result["exe_path"] is None
    assert isinstance(result["output_head"], list)


def test_run_all_probes_structure() -> None:
    """run_all_probes returns correct top-level schema."""
    report = run_all_probes()
    assert "generated_at_utc" in report
    assert "policy" in report
    assert "probe_version" in report
    assert "summary" in report
    assert "slicers" in report
    summary = report["summary"]
    assert "total" in summary
    assert "found" in summary
    assert "not_found" in summary
    assert summary["total"] == summary["found"] + summary["not_found"]


def test_run_all_probes_count() -> None:
    """Total probe count matches _PROBES length."""
    report = run_all_probes()
    assert report["summary"]["total"] == len(_PROBES)


def test_run_all_probes_each_result_has_required_keys() -> None:
    """Every slicer result has the required keys."""
    required_keys = {"id", "name", "status", "version", "exe_path", "return_code", "output_head", "note"}
    report = run_all_probes()
    for slicer in report["slicers"]:
        missing = required_keys - set(slicer.keys())
        assert not missing, f"Slicer {slicer.get('id')} missing keys: {missing}"


def test_run_all_probes_status_values() -> None:
    """All status values are either 'found' or 'not_found'."""
    report = run_all_probes()
    for slicer in report["slicers"]:
        assert slicer["status"] in ("found", "not_found"), (
            f"Unexpected status '{slicer['status']}' for {slicer.get('id')}"
        )


# ---------------------------------------------------------------------------
# Proof file tests — verify the recorded proof is valid
# ---------------------------------------------------------------------------


def test_proof_file_exists() -> None:
    """The proof file must be present."""
    assert _PROOF_FILE.exists(), f"Proof file missing: {_PROOF_FILE}"


def test_proof_file_is_valid_json() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_proof_file_schema() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    assert "generated_at_utc" in data
    assert "policy" in data
    assert "probe_version" in data
    assert "summary" in data
    assert "slicers" in data
    assert isinstance(data["slicers"], list)


def test_proof_file_no_slicing_policy() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    assert "never slices" in data["policy"].lower()
    assert "never sends to printer" in data["policy"].lower()


def test_proof_file_task_id() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    assert data.get("task_id") == "H3D-CLAUDE-SOURCE-SLICERS"


def test_proof_file_all_slicers_present() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    ids_in_proof = {s["id"] for s in data["slicers"]}
    required = {"prusaslicer", "orcaslicer", "flsun_slicer", "curaengine", "superslicer", "slic3r", "bambustudio"}
    assert required.issubset(ids_in_proof), f"Missing from proof: {required - ids_in_proof}"


def test_proof_file_found_slicers_have_exe_path() -> None:
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    for slicer in data["slicers"]:
        if slicer["status"] == "found":
            assert slicer["exe_path"] is not None, f"{slicer['id']} is 'found' but exe_path is None"


# ---------------------------------------------------------------------------
# Live integration tests — skipped if executable not present
# ---------------------------------------------------------------------------


def _live_params() -> list[tuple[str, str]]:
    """Return (id, exe_path) for slicers that are actually installed."""
    if not _PROOF_FILE.exists():
        return []
    data = json.loads(_PROOF_FILE.read_text(encoding="utf-8"))
    return [
        (s["id"], s["exe_path"])
        for s in data["slicers"]
        if s["status"] == "found" and s["exe_path"] and Path(s["exe_path"]).is_file()
    ]


@pytest.mark.parametrize("slicer_id,exe_path", _live_params())
def test_live_probe_installed_slicer(slicer_id: str, exe_path: str) -> None:
    """Live probe for each installed slicer — must report found."""
    entry = next((p for p in _PROBES if p["id"] == slicer_id), None)
    if entry is None:
        pytest.skip(f"No probe entry for {slicer_id}")
    result = probe_slicer(entry)
    assert result["status"] == "found", (
        f"{slicer_id} is installed at {exe_path} but live probe returned status={result['status']}"
    )


@pytest.mark.parametrize("slicer_id,exe_path", _live_params())
def test_live_probe_no_slice_output(slicer_id: str, exe_path: str) -> None:
    """Probe output must not contain G-code markers (safety guard)."""
    entry = next((p for p in _PROBES if p["id"] == slicer_id), None)
    if entry is None:
        pytest.skip(f"No probe entry for {slicer_id}")
    result = probe_slicer(entry)
    combined = "\n".join(result.get("output_head") or [])
    gcode_markers = {";LAYER:", "G28 ", "M104 ", "T0\n", "; generated by"}
    for marker in gcode_markers:
        assert marker.lower() not in combined.lower(), (
            f"Probe for {slicer_id} produced G-code-like output — policy violation"
        )
