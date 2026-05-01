"""Per-`type` required adapter capabilities.

Source of truth for "what capability tokens must each tool category declare?".

Derived from:
- 03_implementation/adapter_registry/README.md §1 (taxonomy) + §5 (capability flags)
- 01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md §6 work-items
- User-locked rule: every UI-bearing tool must be supportable in BOTH docked AND
  external (full-app) modes.

Any token starting with "dock_" satisfies the "must dock" requirement (e.g.
dock_if_supported, dock_if_allowed); the validator accepts any of these for
flexibility while keeping the user's contract intact.
"""

from __future__ import annotations

_REQUIRED: dict[str, frozenset[str]] = {
    "external_app": frozenset({"launch_external", "dock_if_supported"}),
    "mcp_provider": frozenset(),  # provider, no UI surface
    "slicer": frozenset({"launch_external", "dock_if_allowed"}),
    "printer_control_usb": frozenset({"launch_external", "dock_if_allowed"}),
    "printer_api": frozenset(),  # headless API, no UI
    "external_web_ui": frozenset({"dock_if_allowed", "fullscreen_external"}),
    "printer_api_and_web_ui": frozenset({"dock_if_allowed"}),
}

KNOWN_TYPES: frozenset[str] = frozenset(_REQUIRED.keys())


def required_capabilities_for_type(tool_type: str) -> frozenset[str]:
    """Return the required capability tokens for a given tool type.

    Returns an empty frozenset for unknown types (validator handles the
    UNKNOWN_TYPE warning separately).
    """
    return _REQUIRED.get(tool_type, frozenset())


def is_known_type(tool_type: str) -> bool:
    return tool_type in KNOWN_TYPES
