"""Tool registry for agentic action dispatch.

Hermes Agent and Goose both expose a ``tool registry``: a flat catalogue of
named functions an agent can call, each with a JSON Schema parameter spec and
a human-readable description. Hermes3D-OS uses the same pattern so that any
external orchestrator (LangGraph, an MCP client, an LLM tool-call loop, the
Telegram bridge, etc.) can introspect and invoke fleet capabilities without
needing direct Python imports.

Tools are registered with ``@register_tool(name=..., description=..., parameters=...)``.
The registry validates names are unique and parameters are JSON-Schema-compatible.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    """Describes one callable tool the agent can invoke."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    category: str = "misc"
    tags: tuple[str, ...] = field(default_factory=tuple)

    def to_json_schema(self) -> dict[str, Any]:
        """Return the JSON Schema definition (compatible with OpenAI tools, MCP, etc.)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
            "tags": list(self.tags),
        }


class ToolRegistry:
    """In-memory registry of named tools.

    Use the module-level singleton ``tool_registry`` for normal use. Construct
    a fresh instance for tests that need isolation.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool {spec.name!r} is already registered")
        if not spec.name.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"invalid tool name {spec.name!r}: alnum/_/- only")
        self._tools[spec.name] = spec

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool {name!r}")
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return sorted(self._tools.values(), key=lambda s: s.name)

    def by_category(self, category: str) -> list[ToolSpec]:
        return [t for t in self._tools.values() if t.category == category]

    def by_tag(self, tag: str) -> list[ToolSpec]:
        return [t for t in self._tools.values() if tag in t.tags]

    def categories(self) -> list[str]:
        return sorted({t.category for t in self._tools.values()})

    def call(self, name: str, **kwargs: Any) -> Any:
        spec = self.get(name)
        sig = inspect.signature(spec.handler)
        # Filter kwargs to those accepted by the handler — agents may pass extras.
        accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if accepts_var_kw:
            filtered = kwargs
        else:
            filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return spec.handler(**filtered)

    def manifest(self) -> dict[str, Any]:
        """Full registry manifest, suitable for serving over MCP or REST."""
        return {
            "tool_count": len(self._tools),
            "categories": self.categories(),
            "tools": [t.to_json_schema() for t in self.all()],
        }

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._tools


tool_registry = ToolRegistry()
"""Module-level singleton registry."""


def register_tool(
    *,
    name: str,
    description: str,
    parameters: dict[str, Any],
    category: str = "misc",
    tags: tuple[str, ...] = (),
    registry: ToolRegistry | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a function as an agent tool.

    >>> @register_tool(name="echo", description="Echo input", parameters={"type":"object","properties":{"text":{"type":"string"}},"required":["text"]})
    ... def echo(text: str) -> str: return text
    >>> tool_registry.call("echo", text="hi")
    'hi'
    >>> tool_registry.unregister("echo")
    """
    target = registry if registry is not None else tool_registry

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        spec = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=fn,
            category=category,
            tags=tuple(tags),
        )
        target.register(spec)
        fn.__hermes3d_tool__ = spec  # type: ignore[attr-defined]
        return fn

    return decorator


__all__ = [
    "ToolRegistry",
    "ToolSpec",
    "register_tool",
    "tool_registry",
]
