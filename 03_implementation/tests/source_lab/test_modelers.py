"""Pytest for the source-modelers verifier proof.

Lane H3D-CLAUDE-SOURCE-MODELERS.
Asserts proof JSON shape and policy invariants. Does NOT re-run the
verifier (that runs as a gate); the test only validates the artifact's
contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROOF_PATH = (
    Path(__file__).resolve().parents[2]
    / "proof"
    / "MODELERS_VERIFY_2026-05-06.json"
)

EXPECTED_MODELERS = {
    "blender",
    "openscad",
    "freecad",
    "cadquery",
    "build123d",
    "trimesh",
}

CLI_MODELERS = {"blender", "openscad", "freecad"}
PYTHON_MODELERS = {"cadquery", "build123d", "trimesh"}

REQUIRED_FIELDS_COMMON = {
    "id",
    "label",
    "kind",
    "schema_path",
    "schema_valid",
    "installed",
    "status",
    "proof_gate_version",
}

REQUIRED_FIELDS_CLI = REQUIRED_FIELDS_COMMON | {"executable_found", "version_probe", "help_probe"}
REQUIRED_FIELDS_PYTHON = REQUIRED_FIELDS_COMMON | {"pip_probes"}


@pytest.fixture(scope="module")
def proof() -> dict:
    if not PROOF_PATH.is_file():
        pytest.fail(
            f"MODELERS verify proof missing at {PROOF_PATH}; "
            "run: python 03_implementation/scripts/verify_modelers.py"
        )
    return json.loads(PROOF_PATH.read_text(encoding="utf-8"))


def test_proof_top_level_shape(proof: dict) -> None:
    assert proof["$schema"] == "hermes3d://proof/modelers_verify_v1"
    assert proof["lane"] == "H3D-CLAUDE-SOURCE-MODELERS"
    assert "generated_at_utc" in proof
    assert isinstance(proof["modelers"], list)
    assert isinstance(proof["summary"], dict)


def test_proof_policy_forbids_downloads(proof: dict) -> None:
    policy = proof.get("policy") or {}
    assert policy.get("downloads") == "forbidden", "policy must declare downloads forbidden"
    assert "version" in str(policy.get("cli", "")).lower() or "probe" in str(
        policy.get("cli", "")
    ).lower(), "cli policy must mention version or probe"
    assert "show" in str(policy.get("pip", "")).lower(), "pip policy must mention 'show'"


def test_proof_covers_all_six_modelers(proof: dict) -> None:
    ids = {entry["id"] for entry in proof["modelers"]}
    assert ids == EXPECTED_MODELERS, (
        f"missing or extra modelers;\n  got:      {sorted(ids)}\n  expected: {sorted(EXPECTED_MODELERS)}"
    )


def test_each_modeler_has_required_fields(proof: dict) -> None:
    for entry in proof["modelers"]:
        mid = entry.get("id", "<unknown>")
        kind = entry.get("kind", "")
        if kind == "cli":
            required = REQUIRED_FIELDS_CLI
        else:
            required = REQUIRED_FIELDS_PYTHON
        missing = required - entry.keys()
        assert not missing, f"modeler '{mid}' missing fields: {missing}"
        assert entry["schema_valid"] is True, f"'{mid}' schema not parseable"
        assert isinstance(entry["installed"], bool), f"'{mid}' installed must be bool"
        assert entry["proof_gate_version"] == "modelers-source-runtime-verifier-v1"


def test_status_is_honest(proof: dict) -> None:
    """status='found' must match installed=True and vice-versa."""
    for entry in proof["modelers"]:
        mid = entry["id"]
        if entry["installed"]:
            assert entry["status"] == "found", (
                f"'{mid}' installed=True but status='{entry['status']}'"
            )
        else:
            assert entry["status"] != "found", (
                f"'{mid}' installed=False but status='{entry['status']}'"
            )


def test_cli_modelers_have_version_probe(proof: dict) -> None:
    for entry in proof["modelers"]:
        if entry["id"] in CLI_MODELERS:
            vp = entry.get("version_probe") or {}
            assert "found" in vp, f"'{entry['id']}' version_probe missing 'found' key"
            assert isinstance(vp["found"], bool)
            # If installed, version_probe.found must be True
            if entry["installed"]:
                assert vp["found"] is True, (
                    f"'{entry['id']}' installed=True but version_probe.found=False"
                )


def test_python_modelers_have_pip_probes(proof: dict) -> None:
    for entry in proof["modelers"]:
        if entry["id"] in PYTHON_MODELERS:
            pip_probes = entry.get("pip_probes") or []
            assert isinstance(pip_probes, list), f"'{entry['id']}' pip_probes must be list"
            assert len(pip_probes) >= 1, f"'{entry['id']}' pip_probes must have at least one entry"
            for probe in pip_probes:
                assert "package" in probe, f"'{entry['id']}' pip_probe missing 'package'"
                assert "installed" in probe, f"'{entry['id']}' pip_probe missing 'installed'"
                assert isinstance(probe["installed"], bool)


def test_summary_counts_consistent(proof: dict) -> None:
    summary = proof["summary"]
    assert summary["total"] == len(proof["modelers"]), "summary.total mismatch"
    found_ids = {m["id"] for m in proof["modelers"] if m["installed"]}
    not_found_ids = {m["id"] for m in proof["modelers"] if not m["installed"]}
    assert set(summary["found"]) == found_ids, "summary.found mismatch"
    assert set(summary["not_found"]) == not_found_ids, "summary.not_found mismatch"
    assert found_ids.isdisjoint(not_found_ids), "found and not_found must be disjoint"


def test_trimesh_probes_companion_packages(proof: dict) -> None:
    """trimesh entry must probe numpy-stl and open3d alongside trimesh."""
    trimesh_entry = next((m for m in proof["modelers"] if m["id"] == "trimesh"), None)
    assert trimesh_entry is not None, "trimesh entry missing from proof"
    pip_probes = trimesh_entry.get("pip_probes") or []
    pkgs = {p["package"] for p in pip_probes}
    assert "trimesh" in pkgs, "trimesh must be probed"
    assert "numpy-stl" in pkgs, "numpy-stl must be probed alongside trimesh"
    assert "open3d" in pkgs, "open3d must be probed alongside trimesh"
