# Pattern adapted from NousResearch/hermes-agent (MIT) — https://github.com/NousResearch/hermes-agent
"""Hermes3D capability-aware tool registry (additive extension).

This module ports the *pattern* used by Hermes Agent's
``tools/registry.py`` (singleton registry, decorator-based registration,
auto-discovery of tool modules) and extends it with two Hermes3D-specific
concerns:

* ``capabilities`` — declarative tags such as ``"truth_gate"``,
  ``"slicer.cli"``, ``"moonraker.client"`` that the planner / dispatcher
  uses to filter the available action space when assembling a plan.
* ``blast_radius`` — one of ``"none"``, ``"local"``, ``"printer"``,
  ``"fleet"``. Sub-agents and the delegate-isolation layer use this to
  gate which tools they may invoke without an approval callback.

The existing ``hermes3d.core.agents.tool_registry`` module keeps the
agent-tool catalogue used today by ``api/mcp_server.py``; this new
``hermes3d.core.tool_registry`` package is **additive** — it does not
import from, or replace, that module. Callers that want both can import
both side by side.
"""

from hermes3d.core.tool_registry.registry import (
    BlastRadius,
    CapabilityRegistry,
    RegisteredTool,
    auto_discover,
    capability_registry,
    register,
)

__all__ = [
    "BlastRadius",
    "CapabilityRegistry",
    "RegisteredTool",
    "auto_discover",
    "capability_registry",
    "register",
]
