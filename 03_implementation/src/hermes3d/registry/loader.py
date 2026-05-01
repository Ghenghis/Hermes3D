"""Parse external_repos_registry.yaml into typed ToolEntry objects.

The kit's `validate_registry.py` baseline operates on raw dicts. This loader
emits `ToolEntry` dataclasses so downstream consumers (validator, adapter
loader, future router) all see the same typed surface.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .types import AdapterSpec, ToolEntry, VersionPolicy


class LoaderError(Exception):
    """File-not-found or top-level YAML structure error."""


def _coerce_version_policy(d: dict) -> VersionPolicy:
    return VersionPolicy(
        pin=d.get("pin"),
        channel=d.get("channel"),
        manual_select=bool(d.get("manual_select", False)),
        locked=d.get("locked"),
    )


def _coerce_adapter(d: dict) -> AdapterSpec:
    caps = d.get("capabilities") or ()
    if not isinstance(caps, (list, tuple)):
        caps = ()
    return AdapterSpec(
        mode=str(d.get("mode", "")),
        capabilities=tuple(str(c) for c in caps),
    )


def _coerce_entry(key: str, raw: dict) -> ToolEntry:
    os_support = raw.get("os_support") or ()
    if not isinstance(os_support, (list, tuple)):
        os_support = ()
    tested = raw.get("tested_versions") or ()
    if not isinstance(tested, (list, tuple)):
        tested = ()
    return ToolEntry(
        key=key,
        name=str(raw.get("name", "")),
        type=str(raw.get("type", "")),
        required=bool(raw.get("required", False)),
        os_support=tuple(str(o) for o in os_support),
        version_policy=_coerce_version_policy(raw.get("version_policy") or {}),
        install=raw.get("install") or {},
        verify=raw.get("verify") or {},
        adapter=_coerce_adapter(raw.get("adapter") or {}),
        license=str(raw.get("license", "")),
        tested_versions=tuple(str(v) for v in tested),
        repo=raw.get("repo"),
        source=raw.get("source"),
        homepage=raw.get("homepage"),
    )


def load_registry(path: Path) -> list[ToolEntry]:
    """Load and parse a registry YAML into a list of `ToolEntry` records.

    Raises:
        LoaderError: file not found or YAML top-level structure invalid.
    """
    if not path.exists():
        raise LoaderError(f"registry not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = (
        data.get("tools") if isinstance(data, dict) and "tools" in data else data
    )
    if not isinstance(tools, dict) or not tools:
        raise LoaderError("registry must contain non-empty 'tools' object")
    return [_coerce_entry(str(k), v) for k, v in tools.items() if isinstance(v, dict)]
