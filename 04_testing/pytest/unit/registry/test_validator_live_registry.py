"""Phase 1 Task 9 — gate the live kit registry against the hardened validator.

Skips gracefully if the kit is not present (e.g. running the test suite from a
sparse checkout); fails loudly if the kit is present and the registry has
drifted from the validator's expectations.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate

REPO_ROOT = Path(__file__).resolve().parents[4]
LIVE_REGISTRY = (
    REPO_ROOT
    / "hermes3d_gui_contract_kit_v4.1"
    / "config"
    / "external_repos_registry.yaml"
)


@pytest.mark.skipif(not LIVE_REGISTRY.exists(), reason="kit registry not present in checkout")
def test_live_registry_passes_hardened_validator():
    entries = load_registry(LIVE_REGISTRY)
    result = validate(entries)
    assert result.ok, "live registry FAILED hardened validation:\n" + "\n".join(
        f"- {e.tool_id} [{e.severity}] {e.code.value}: {e.message}"
        for e in result.errors
    )


@pytest.mark.skipif(not LIVE_REGISTRY.exists(), reason="kit registry not present in checkout")
def test_live_registry_has_expected_tool_count():
    entries = load_registry(LIVE_REGISTRY)
    # 10 user-locked tools + Cura provisioning + experimental MCP provider = 12.
    assert len(entries) == 12, f"expected 12 entries, got {len(entries)}"


@pytest.mark.skipif(not LIVE_REGISTRY.exists(), reason="kit registry not present in checkout")
def test_live_registry_covers_all_locked_tools():
    """The 10 user-locked tools must be present (surplus is OK)."""
    locked = {
        "blender",
        "blender_mcp_ahujasid",
        "prusa_slicer",
        "orca_slicer",
        "flsun_slicer",
        "printrun",
        "moonraker",
        "fluidd",
        "mainsail",
        "octoprint",
    }
    keys = {e.key for e in load_registry(LIVE_REGISTRY)}
    missing = locked - keys
    assert not missing, f"locked tools missing from registry: {sorted(missing)}"
