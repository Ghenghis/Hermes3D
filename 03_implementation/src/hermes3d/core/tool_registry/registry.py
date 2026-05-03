# Pattern adapted from NousResearch/hermes-agent (MIT) — https://github.com/NousResearch/hermes-agent
"""Capability + blast-radius aware tool registry for Hermes3D.

The pattern (singleton registry, decorator-based registration,
package-tree auto-discovery) is taken from Hermes Agent's
``tools/registry.py`` (upstream commit ``457c7b7``). Hermes3D-specific
concerns added on top:

* ``capabilities`` — free-form string tags the planner queries to
  enumerate the available action space (e.g. ``"truth_gate"``,
  ``"slicer.cli"``, ``"moonraker.client"``).
* ``blast_radius`` — quantises the worst-case effect of invoking a tool
  so the delegate-isolation layer can refuse to spawn subagents that
  would touch ``"printer"`` or ``"fleet"`` scoped tools without an
  approval callback in scope.

Threading model: register / lookup / list operations are guarded by an
``RLock`` so MCP-style hot-reloads (a future use case) do not race tool
discovery passes. Reads return stable snapshots.

This is intentionally additive — it does NOT import from or shadow the
existing ``hermes3d.core.agents.tool_registry`` module used by
``api/mcp_server.py``. Both can coexist.
"""

from __future__ import annotations

import enum
import importlib
import inspect
import logging
import pkgutil
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger(__name__)


class BlastRadius(str, enum.Enum):
    """Worst-case scope of a tool invocation.

    Ordered from least to most dangerous so callers can compare with
    ``<``/``<=`` and write rules like
    ``if tool.blast_radius > BlastRadius.LOCAL: require_approval()``.
    """

    NONE = "none"
    LOCAL = "local"
    PRINTER = "printer"
    FLEET = "fleet"

    @property
    def severity(self) -> int:
        return _BLAST_ORDER[self]

    def __lt__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, BlastRadius):
            return self.severity < other.severity
        return NotImplemented

    def __le__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, BlastRadius):
            return self.severity <= other.severity
        return NotImplemented

    def __gt__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, BlastRadius):
            return self.severity > other.severity
        return NotImplemented

    def __ge__(self, other: object) -> bool:  # type: ignore[override]
        if isinstance(other, BlastRadius):
            return self.severity >= other.severity
        return NotImplemented


_BLAST_ORDER = {
    BlastRadius.NONE: 0,
    BlastRadius.LOCAL: 1,
    BlastRadius.PRINTER: 2,
    BlastRadius.FLEET: 3,
}


@dataclass(frozen=True)
class RegisteredTool:
    """Metadata + handler for one registered tool."""

    name: str
    handler: Callable[..., Any]
    capabilities: frozenset[str]
    blast_radius: BlastRadius
    description: str = ""
    tags: frozenset[str] = field(default_factory=frozenset)

    def to_manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": sorted(self.capabilities),
            "blast_radius": self.blast_radius.value,
            "tags": sorted(self.tags),
        }


class CapabilityRegistry:
    """Singleton-friendly registry indexed by name, capability, blast radius.

    Construct your own instance for tests that need isolation; for normal
    use import the module-level :data:`capability_registry`.
    """

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._lock = threading.RLock()
        self._generation: int = 0

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(
        self,
        *,
        name: str,
        handler: Callable[..., Any],
        capabilities: Iterable[str],
        blast_radius: BlastRadius | str = BlastRadius.LOCAL,
        description: str = "",
        tags: Iterable[str] = (),
        replace: bool = False,
    ) -> RegisteredTool:
        """Register a tool. Returns the stored :class:`RegisteredTool`.

        Set ``replace=True`` to allow overwriting an existing entry; the
        default is to refuse, matching upstream Hermes Agent's
        shadowing-rejection rule.
        """
        if not name or not _valid_name(name):
            raise ValueError(
                f"invalid tool name {name!r}: must be alnum/_/-/. and non-empty"
            )
        radius = (
            blast_radius
            if isinstance(blast_radius, BlastRadius)
            else BlastRadius(blast_radius)
        )
        if not description and handler.__doc__:
            doc_lines = handler.__doc__.strip().splitlines()
            description = doc_lines[0] if doc_lines else ""
        spec = RegisteredTool(
            name=name,
            handler=handler,
            capabilities=frozenset(capabilities),
            blast_radius=radius,
            description=description,
            tags=frozenset(tags),
        )
        with self._lock:
            existing = self._tools.get(name)
            if existing is not None and not replace:
                raise ValueError(
                    f"tool {name!r} already registered (use replace=True to override)"
                )
            self._tools[name] = spec
            self._generation += 1
        return spec

    def deregister(self, name: str) -> bool:
        with self._lock:
            removed = self._tools.pop(name, None)
            if removed is not None:
                self._generation += 1
        return removed is not None

    def clear(self) -> None:
        with self._lock:
            self._tools.clear()
            self._generation += 1

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> RegisteredTool:
        with self._lock:
            try:
                return self._tools[name]
            except KeyError as exc:
                raise KeyError(f"unknown tool {name!r}") from exc

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._tools

    def list(self) -> list[RegisteredTool]:
        with self._lock:
            return sorted(self._tools.values(), key=lambda t: t.name)

    def list_names(self) -> list[str]:
        with self._lock:
            return sorted(self._tools.keys())

    def by_capability(self, capability: str) -> list[RegisteredTool]:
        with self._lock:
            return sorted(
                (t for t in self._tools.values() if capability in t.capabilities),
                key=lambda t: t.name,
            )

    def by_blast_radius(self, *, max: BlastRadius) -> list[RegisteredTool]:
        """Return tools whose blast radius is ``<= max``."""
        with self._lock:
            return sorted(
                (t for t in self._tools.values() if t.blast_radius <= max),
                key=lambda t: t.name,
            )

    def manifest(self) -> dict[str, Any]:
        with self._lock:
            tools = sorted(self._tools.values(), key=lambda t: t.name)
            capabilities = sorted({c for t in tools for c in t.capabilities})
            return {
                "generation": self._generation,
                "tool_count": len(tools),
                "capabilities": capabilities,
                "tools": [t.to_manifest() for t in tools],
            }

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def call(self, name: str, **kwargs: Any) -> Any:
        spec = self.get(name)
        sig = inspect.signature(spec.handler)
        accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        filtered = kwargs if accepts_var_kw else {
            k: v for k, v in kwargs.items() if k in sig.parameters
        }
        return spec.handler(**filtered)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def __len__(self) -> int:
        with self._lock:
            return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and self.has(name)


def _valid_name(name: str) -> bool:
    return all(c.isalnum() or c in {"_", "-", "."} for c in name)


# Module-level singleton ----------------------------------------------------

capability_registry = CapabilityRegistry()


def register(
    *,
    name: str,
    capabilities: Iterable[str],
    blast_radius: BlastRadius | str = BlastRadius.LOCAL,
    description: str = "",
    tags: Iterable[str] = (),
    registry: CapabilityRegistry | None = None,
    replace: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: register the wrapped callable as a Hermes3D tool.

    Example::

        @register(
            name="truth_gate.run",
            capabilities={"truth_gate", "validation"},
            blast_radius="local",
        )
        def run_truth_gate(stl_path: str) -> dict: ...
    """
    target = registry if registry is not None else capability_registry

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        spec = target.register(
            name=name,
            handler=fn,
            capabilities=capabilities,
            blast_radius=blast_radius,
            description=description or (fn.__doc__.strip().splitlines()[0] if fn.__doc__ else ""),
            tags=tags,
            replace=replace,
        )
        # Stash the spec so introspection tooling can find it.
        fn.__hermes3d_capability__ = spec  # type: ignore[attr-defined]
        return fn

    return decorator


# Auto-discovery -----------------------------------------------------------


def auto_discover(
    package: str | object,
    *,
    registry: CapabilityRegistry | None = None,
) -> list[str]:
    """Walk a package tree, importing every submodule.

    Mirrors Hermes Agent's ``discover_builtin_tools()`` but uses
    :func:`pkgutil.walk_packages` instead of an AST scan, which is
    sufficient for our smaller tool surface and avoids a second parsing
    pass. Modules that raise on import are logged and skipped — the
    caller still gets a list of successfully-imported module names.

    The ``registry`` arg is accepted for symmetry but the discovery
    process simply triggers each module's ``@register(...)`` decorators
    at import time; pass it only if you've configured a non-default
    registry singleton you want to validate against.
    """
    if isinstance(package, str):
        pkg = importlib.import_module(package)
    else:
        pkg = package

    if not hasattr(pkg, "__path__"):
        raise TypeError(
            f"auto_discover requires a package, got module {pkg.__name__!r}"
        )

    imported: list[str] = []
    for mod_info in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        if mod_info.ispkg:
            continue
        try:
            importlib.import_module(mod_info.name)
            imported.append(mod_info.name)
        except Exception as exc:
            LOG.warning("auto_discover: skipping %s (%s)", mod_info.name, exc)
    if registry is not None:
        LOG.debug(
            "auto_discover: imported %d modules; registry now has %d tools",
            len(imported),
            len(registry),
        )
    return imported


__all__ = [
    "BlastRadius",
    "CapabilityRegistry",
    "RegisteredTool",
    "auto_discover",
    "capability_registry",
    "register",
]
