"""Phase 1 Task 1 — typed dataclasses for registry entries."""
from __future__ import annotations

from hermes3d.registry.types import AdapterSpec, ToolEntry, VersionPolicy


def test_tool_entry_minimal_construction():
    entry = ToolEntry(
        key="example",
        name="Example",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(channel="stable", manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["example --version"], "expected": "version"},
        adapter=AdapterSpec(
            mode="external_process",
            capabilities=("detect", "launch_external"),
        ),
        repo="https://github.com/example/example",
        license="MIT",
        tested_versions=("1.0.0",),
    )
    assert entry.key == "example"
    assert entry.adapter.mode == "external_process"
    assert "detect" in entry.adapter.capabilities


def test_version_policy_has_resolution():
    assert VersionPolicy(channel="stable", manual_select=True).has_resolution()
    assert VersionPolicy(pin="1.2.3").has_resolution()
    assert VersionPolicy(locked="1.2.3").has_resolution()
    assert not VersionPolicy().has_resolution()


def test_reference_url_prefers_repo_then_source_then_homepage():
    entry = ToolEntry(
        key="x",
        name="X",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["x"], "expected": "v"},
        adapter=AdapterSpec(mode="external_process", capabilities=("detect",)),
        repo="https://example.com/r",
        source="https://example.com/s",
        homepage="https://example.com/h",
        license="MIT",
        tested_versions=("1.0.0",),
    )
    assert entry.reference_url() == "https://example.com/r"

    no_repo = ToolEntry(
        key="x",
        name="X",
        type="external_app",
        required=True,
        os_support=("windows",),
        version_policy=VersionPolicy(manual_select=True),
        install={"method": "binary"},
        verify={"commands": ["x"], "expected": "v"},
        adapter=AdapterSpec(mode="external_process", capabilities=("detect",)),
        source="https://example.com/s",
        homepage="https://example.com/h",
        license="MIT",
        tested_versions=("1.0.0",),
    )
    assert no_repo.reference_url() == "https://example.com/s"
