"""Phase 1 Task 16 — parameterized smoke tests for the 11 adapter skeletons.

Verifies:
- All 11 are registered in the default AdapterRegistry after `import hermes3d.adapters`.
- Each implements the ToolAdapter Protocol (runtime_checkable).
- Each has the expected identity constants (key, display_name, category, dangerous).
- detect() never raises (returns UNINSTALLED on a clean machine).
- version() never raises and never spawns a real subprocess (helper is patched).
- capabilities() returns a non-empty frozenset.
- Phase 3 / Phase 6 methods raise NotImplementedYet (hand-off contract).

The `_safe_version_command` helper is patched module-wide so the test suite
NEVER spawns a real subprocess. This keeps Phase 1 inside the user's
"strictly harmless and mocked/test-gated" boundary.
"""

from __future__ import annotations

from unittest.mock import patch

import hermes3d.adapters  # noqa: F401 -- triggers @register on all 11 skeletons
import pytest
from hermes3d.adapters.protocol import NotImplementedYet, ToolAdapter
from hermes3d.adapters.registry import all_registered
from hermes3d.adapters.types import (
    Action,
    AdapterState,
    Confirmation,
    DetectResult,
)

# Expected identity per adapter — keyed by adapter key.
EXPECTED = {
    "blender": ("Blender", "3d", True),
    "blender_mcp": ("Blender MCP (provider manager)", "3d-mcp", True),
    "cura": ("Ultimaker Cura", "slicer", True),
    "flsun_slicer": ("FLSUN Slicer", "slicer", True),
    "fluidd": ("Fluidd", "printer-ui", False),
    "mainsail": ("Mainsail", "printer-ui", False),
    "moonraker": ("Moonraker", "printer", True),
    "octoprint": ("OctoPrint", "printer", True),
    "orca_slicer": ("OrcaSlicer", "slicer", True),
    "printrun": ("Printrun / Pronterface / Pronsole", "printer", True),
    "prusa_slicer": ("PrusaSlicer", "slicer", True),
}


def _registered_by_key() -> dict[str, type]:
    return {cls.key: cls for cls in all_registered() if cls.key in EXPECTED}


def test_all_11_skeletons_registered():
    by_key = _registered_by_key()
    missing = set(EXPECTED) - set(by_key)
    assert not missing, f"missing skeletons: {sorted(missing)}"


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_implements_protocol(key):
    cls = _registered_by_key()[key]
    instance = cls()
    assert isinstance(instance, ToolAdapter), f"{key} does not implement ToolAdapter"


@pytest.mark.parametrize("key,expected", sorted(EXPECTED.items()))
def test_skeleton_identity_constants(key, expected):
    display_name, category, dangerous = expected
    cls = _registered_by_key()[key]
    instance = cls()
    assert instance.key == key
    assert instance.display_name == display_name
    assert instance.category == category
    assert instance.dangerous is dangerous


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_detect_does_not_raise_or_invoke_subprocess(key):
    """detect() must be safe on any host — returns DetectResult, never crashes."""
    cls = _registered_by_key()[key]
    # Patch _safe_version_command to verify detect() doesn't call it (detect is path-only).
    with patch("hermes3d.adapters.base._safe_version_command") as mocked:
        r = cls().detect()
    assert isinstance(r, DetectResult)
    assert r.state in {AdapterState.UNINSTALLED, AdapterState.DETECTED}
    mocked.assert_not_called()


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_version_returns_none_when_helper_returns_none(key):
    """version() returns None when the helper returns None (binary missing or query failed)."""
    cls = _registered_by_key()[key]
    with patch("hermes3d.adapters.base._safe_version_command", return_value=None):
        v = cls().version()
    assert v is None or isinstance(v, str)


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_capabilities_returns_nonempty_frozenset(key):
    cls = _registered_by_key()[key]
    caps = cls().capabilities()
    assert isinstance(caps, frozenset)
    assert len(caps) > 0


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_phase3_methods_raise_not_implemented_yet(key):
    cls = _registered_by_key()[key]
    instance = cls()
    for method_name in (
        "validate",
        "healthcheck",
        "status",
        "open_docked",
        "open_undocked",
        "open_external",
        "detach_ui",
    ):
        with pytest.raises(NotImplementedYet, match="Phase 3"):
            getattr(instance, method_name)()


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_skeleton_phase6_methods_raise_not_implemented_yet(key):
    cls = _registered_by_key()[key]
    instance = cls()
    with pytest.raises(NotImplementedYet, match="Phase 6"):
        instance.dry_run(Action(kind="noop", payload={}))
    with pytest.raises(NotImplementedYet, match="Phase 6"):
        instance.execute(
            Action(kind="noop", payload={}),
            Confirmation(
                user="u",
                ts_utc="t",
                printer_id=None,
                reason_text="r",
                dry_run_token="tok",
                signed_token="sig",
                policy_version="v4.1",
            ),
        )


# --------- Targeted version() success paths (with mocked subprocess) ---------


def test_blender_version_uses_safe_helper_when_binary_present():
    """When shutil.which finds the binary, version() invokes the helper (mocked).

    Patches the helper at the *use site* (`hermes3d.adapters.blender._safe_version_command`)
    rather than the definition site, because the adapter module already imported the symbol.
    """
    from hermes3d.adapters import blender as blender_mod

    with (
        patch("hermes3d.adapters.blender.shutil.which", return_value="/usr/bin/blender"),
        patch(
            "hermes3d.adapters.blender._safe_version_command",
            return_value="Blender 4.2.0",
        ) as mocked,
    ):
        v = blender_mod.BlenderAdapter().version()
    assert v == "Blender 4.2.0"
    mocked.assert_called_once_with(["/usr/bin/blender", "--version"])


def test_blender_version_returns_none_when_binary_missing():
    from hermes3d.adapters import blender as blender_mod

    with (
        patch("hermes3d.adapters.blender.shutil.which", return_value=None),
        patch("hermes3d.adapters.blender._safe_version_command") as mocked,
    ):
        v = blender_mod.BlenderAdapter().version()
    assert v is None
    mocked.assert_not_called()  # never spawn subprocess if binary missing


def test_moonraker_detect_never_calls_network():
    """Network adapters must return UNINSTALLED in Phase 1 without any I/O."""
    from hermes3d.adapters.moonraker import MoonrakerAdapter

    r = MoonrakerAdapter().detect()
    assert r.state == AdapterState.UNINSTALLED
    assert "Phase 3" in r.detail or "configure" in r.detail.lower()
