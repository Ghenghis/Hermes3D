"""Pytest for the gen3d source+runtime verifier proof.

Asserts proof JSON shape and policy invariants. Does NOT re-run the
verifier (that runs as a gate); the test only validates the artifact's
contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROOF_PATH = Path(__file__).resolve().parents[2] / "proof" / "GEN3D_VERIFY_2026-05-06.json"

EXPECTED_PROVIDERS = {
    "comfyui",
    "trellis2",
    "hunyuan3d",
    "triposr",
    "bambustudio_bridge",
}


@pytest.fixture(scope="module")
def proof() -> dict:
    if not PROOF_PATH.is_file():
        pytest.fail(
            f"GEN3D verify proof missing at {PROOF_PATH}; "
            "run python 03_implementation/scripts/verify_gen3d.py"
        )
    return json.loads(PROOF_PATH.read_text(encoding="utf-8"))


def test_proof_top_level_shape(proof: dict) -> None:
    assert proof["lane"] == "H3D-CLAUDE-SOURCE-GEN3D"
    assert proof["$schema"] == "hermes3d://proof/gen3d_verify_v1"
    assert "generated_at_utc" in proof
    assert isinstance(proof["providers"], list)
    assert isinstance(proof["summary"], dict)


def test_proof_policy_forbids_downloads(proof: dict) -> None:
    policy = proof.get("policy") or {}
    assert policy.get("downloads") == "forbidden"
    assert "ls-remote" in str(policy.get("git", "")).lower()
    assert "show" in str(policy.get("pip", "")).lower()
    assert "boolean" in str(policy.get("weights", "")).lower()


def test_proof_covers_all_five_providers(proof: dict) -> None:
    ids = {entry["id"] for entry in proof["providers"]}
    assert ids == EXPECTED_PROVIDERS, (
        f"missing or extra providers; got {ids} expected {EXPECTED_PROVIDERS}"
    )


def test_each_provider_has_required_fields(proof: dict) -> None:
    required = {
        "id",
        "label",
        "kind",
        "schema_path",
        "schema_valid",
        "source_repo",
        "pip_package",
        "weights_cache_dirs",
        "executable_path",
        "repo_reachable",
        "pip_show",
        "weights_present",
        "executable_present",
        "installed",
        "proof_gate_version",
    }
    for entry in proof["providers"]:
        missing = required - entry.keys()
        assert not missing, f"provider {entry.get('id')} missing fields: {missing}"
        assert entry["schema_valid"] is True, f"{entry['id']} schema not parseable"
        assert isinstance(entry["installed"], bool)
        assert entry["proof_gate_version"] == "gen3d-source-runtime-verifier-v1"


def test_summary_counts_consistent(proof: dict) -> None:
    summary = proof["summary"]
    assert summary["total"] == len(proof["providers"])
    installed_ids = {p["id"] for p in proof["providers"] if p["installed"]}
    not_installed_ids = {p["id"] for p in proof["providers"] if not p["installed"]}
    assert set(summary["installed"]) == installed_ids
    assert set(summary["not_installed"]) == not_installed_ids
    assert installed_ids.isdisjoint(not_installed_ids)


def test_repo_reachable_flag_only_set_when_refs_returned(proof: dict) -> None:
    """Honest reachability: 'reachable' implies a ref count >= 1 OR a recorded reason."""
    for entry in proof["providers"]:
        repo_probe = entry["repo_reachable"]
        if repo_probe.get("reachable"):
            assert repo_probe.get("ref_count", 0) >= 1, (
                f"{entry['id']} marked reachable with zero refs"
            )
        else:
            assert "reason" in repo_probe or "return_code" in repo_probe
