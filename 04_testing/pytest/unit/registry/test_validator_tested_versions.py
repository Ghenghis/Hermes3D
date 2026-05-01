"""Phase 1 Task 8 — tested_versions required field rule."""
from __future__ import annotations

from hermes3d.registry.errors import ErrorCode
from hermes3d.registry.types import AdapterSpec, ToolEntry, VersionPolicy
from hermes3d.registry.validator import validate


def _factory(**overrides) -> ToolEntry:
    base = dict(
        key="x",
        name="X",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["x --version"], "expected": "v"},
        adapter=AdapterSpec(
            mode="external_process",
            capabilities=("launch_external", "dock_if_supported"),
        ),
        license="MIT",
        tested_versions=("1.0.0",),
        repo="https://github.com/x/y",
    )
    base.update(overrides)
    return ToolEntry(**base)


def test_empty_tested_versions_flagged():
    result = validate([_factory(tested_versions=())])
    codes = {e.code for e in result.errors}
    assert ErrorCode.EMPTY_TESTED_VERSIONS in codes
    assert not result.ok


def test_with_tested_versions_passes():
    result = validate([_factory(tested_versions=("1.0.0", "2.0.0"))])
    assert result.ok, [e.to_dict() for e in result.errors]


def test_single_tested_version_is_enough():
    result = validate([_factory(tested_versions=("1.0.0",))])
    assert result.ok, [e.to_dict() for e in result.errors]
