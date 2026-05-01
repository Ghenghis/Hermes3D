"""Phase 1 Task 3 — per-type required capability matrix."""
from __future__ import annotations

from hermes3d.registry.capability_matrix import (
    KNOWN_TYPES,
    is_known_type,
    required_capabilities_for_type,
)


def test_slicer_requires_external_and_dock():
    req = required_capabilities_for_type("slicer")
    assert "launch_external" in req
    assert any(c.startswith("dock_") for c in req)


def test_external_web_ui_requires_dock_and_fullscreen():
    req = required_capabilities_for_type("external_web_ui")
    assert any(c.startswith("dock_") for c in req)
    assert any("fullscreen" in c for c in req)


def test_printer_api_exempt_from_dock():
    req = required_capabilities_for_type("printer_api")
    assert not any(c.startswith("dock_") for c in req)


def test_mcp_provider_exempt_from_dock_and_external():
    req = required_capabilities_for_type("mcp_provider")
    assert req == frozenset()


def test_unknown_type_returns_empty_set():
    assert required_capabilities_for_type("nonexistent") == frozenset()
    assert not is_known_type("nonexistent")


def test_known_types_includes_all_locked_categories():
    expected = {
        "external_app",
        "mcp_provider",
        "slicer",
        "printer_control_usb",
        "printer_api",
        "external_web_ui",
        "printer_api_and_web_ui",
    }
    assert expected.issubset(KNOWN_TYPES)


# Task 7 — per-type capability matrix enforcement in the validator
def test_slicer_missing_dock_token_flagged(fixture_path):
    from hermes3d.registry.errors import ErrorCode
    from hermes3d.registry.loader import load_registry
    from hermes3d.registry.validator import validate

    result = validate(load_registry(fixture_path("slicer_missing_dock_token.yaml")))
    assert not result.ok
    pairs = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_slicer", ErrorCode.MISSING_DOCK_CAPABILITY) in pairs


def test_web_ui_missing_fullscreen_flagged(fixture_path):
    from hermes3d.registry.errors import ErrorCode
    from hermes3d.registry.loader import load_registry
    from hermes3d.registry.validator import validate

    result = validate(load_registry(fixture_path("web_ui_missing_fullscreen.yaml")))
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert ErrorCode.MISSING_REQUIRED_FIELD in codes  # missing fullscreen_external token
