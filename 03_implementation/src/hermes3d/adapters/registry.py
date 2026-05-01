"""Adapter discovery registry.

Adapters register themselves at import time via the `@register` decorator (or
explicit `AdapterRegistry().register(cls)`). The registry is purely an
in-memory class catalog — it does not invoke `detect()` or any external tool.
That keeps Phase 1 foundation-safe: importing the package never touches the
host's tools, network, or printers.

Phase 3+ work that needs running adapters will call `instantiate(key)` to get
a fresh instance.
"""

from __future__ import annotations

from typing import TypeVar

from .base import SkeletonAdapter

T = TypeVar("T", bound=SkeletonAdapter)


class AdapterRegistry:
    """Catalog of `SkeletonAdapter` subclasses keyed by their `.key`."""

    def __init__(self) -> None:
        self._classes: dict[str, type[SkeletonAdapter]] = {}

    def register(self, cls: type[SkeletonAdapter]) -> type[SkeletonAdapter]:
        if not isinstance(cls, type) or not issubclass(cls, SkeletonAdapter):
            raise TypeError(f"{cls!r} is not a SkeletonAdapter subclass")
        if not cls.key:
            raise ValueError(f"{cls.__name__} must declare a non-empty 'key'")
        if cls.key in self._classes:
            raise ValueError(f"adapter '{cls.key}' is already registered")
        self._classes[cls.key] = cls
        return cls

    def by_key(self, key: str) -> type[SkeletonAdapter]:
        return self._classes[key]

    def all(self) -> tuple[type[SkeletonAdapter], ...]:
        """Stable order — sorted by key for reproducibility in proof bundles."""
        return tuple(self._classes[k] for k in sorted(self._classes))

    def instantiate(self, key: str) -> SkeletonAdapter:
        return self.by_key(key)()


# Module-global default registry. Adapters registered with `@register` end up
# here. Tests that need isolation should construct their own `AdapterRegistry()`.
_DEFAULT_REGISTRY = AdapterRegistry()


def register(cls: type[T]) -> type[T]:
    """Decorator: add a SkeletonAdapter subclass to the default registry."""
    _DEFAULT_REGISTRY.register(cls)
    return cls


def all_registered() -> tuple[type[SkeletonAdapter], ...]:
    """All adapter classes currently registered in the default registry."""
    return _DEFAULT_REGISTRY.all()
