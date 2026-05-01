"""Phase 1 Task 4 — YAML loader returns typed ToolEntry list."""
from __future__ import annotations

import pytest

from hermes3d.registry.loader import LoaderError, load_registry


def test_load_minimal_returns_one_tool(fixture_path):
    entries = load_registry(fixture_path("valid_minimal.yaml"))
    assert len(entries) == 1
    e = entries[0]
    assert e.key == "example"
    assert e.name == "Example"
    assert e.type == "external_app"
    assert e.required is True
    assert e.os_support == ("windows",)
    assert e.adapter.mode == "external_process"
    assert "launch_external" in e.adapter.capabilities
    assert "dock_if_supported" in e.adapter.capabilities
    assert e.license == "MIT"
    assert e.tested_versions == ("1.0.0", "1.1.0")
    assert e.repo == "https://github.com/example/example"
    assert e.version_policy.channel == "stable"
    assert e.version_policy.manual_select is True
    assert e.version_policy.has_resolution()


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_registry(tmp_path / "nonexistent.yaml")


def test_load_empty_tools_object_raises(tmp_path):
    bad = tmp_path / "empty.yaml"
    bad.write_text("tools: {}\n", encoding="utf-8")
    with pytest.raises(LoaderError, match="non-empty"):
        load_registry(bad)


def test_load_malformed_top_level_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not_a_dict_here\n", encoding="utf-8")
    with pytest.raises(LoaderError):
        load_registry(bad)
