"""Phase 1 Task 6 — URL shape validation."""

from __future__ import annotations

from hermes3d.registry.errors import ErrorCode
from hermes3d.registry.loader import load_registry
from hermes3d.registry.validator import validate


def test_bad_urls_flagged(fixture_path):
    result = validate(load_registry(fixture_path("bad_url_shape.yaml")))
    assert not result.ok
    pairs = {(e.tool_id, e.code) for e in result.errors}
    assert ("bad_one", ErrorCode.INVALID_URL_SHAPE) in pairs
    assert ("bad_two", ErrorCode.INVALID_URL_SHAPE) in pairs
