"""Phase 1 Task 5 — validator with license + structural rules + CLI."""
from __future__ import annotations

from hermes3d.registry.errors import ErrorCode
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import ValidationResult, validate


def test_minimal_valid_passes(fixture_path):
    entries = load_registry(fixture_path("valid_minimal.yaml"))
    result = validate(entries)
    assert isinstance(result, ValidationResult)
    assert result.ok, [e.to_dict() for e in result.errors]
    assert result.checked == 1


def test_missing_license_flagged(fixture_path):
    result = validate(load_registry(fixture_path("missing_license.yaml")))
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert ErrorCode.MISSING_LICENSE in codes


def test_empty_capabilities_flagged(fixture_path):
    result = validate(load_registry(fixture_path("empty_capabilities.yaml")))
    assert not result.ok
    codes = {e.code for e in result.errors}
    assert ErrorCode.EMPTY_CAPABILITIES in codes


def test_validation_result_to_dict_round_trip(fixture_path):
    result = validate(load_registry(fixture_path("missing_license.yaml")))
    d = result.to_dict()
    assert d["ok"] is False
    assert d["checked"] == 1
    assert any(err["code"] == "MISSING_LICENSE" for err in d["errors"])
