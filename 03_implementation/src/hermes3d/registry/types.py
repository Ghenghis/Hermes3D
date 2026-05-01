"""Typed dataclasses for registry entries.

Backs hermes3d.registry.loader and hermes3d.registry.validator. All entries are
immutable (frozen=True) so they can be safely shared across the validator,
adapter loader, and any future async pipeline without copy semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class VersionPolicy:
    pin: str | None = None
    channel: str | None = None
    manual_select: bool = False
    locked: str | None = None

    def has_resolution(self) -> bool:
        return any((self.pin, self.channel, self.locked)) or self.manual_select


@dataclass(frozen=True)
class AdapterSpec:
    mode: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ToolEntry:
    key: str
    name: str
    type: str
    required: bool
    os_support: tuple[str, ...]
    version_policy: VersionPolicy
    install: Mapping[str, object]
    verify: Mapping[str, object]
    adapter: AdapterSpec
    license: str
    tested_versions: tuple[str, ...] = field(default_factory=tuple)
    repo: str | None = None
    source: str | None = None
    homepage: str | None = None

    def reference_url(self) -> str | None:
        return self.repo or self.source or self.homepage
