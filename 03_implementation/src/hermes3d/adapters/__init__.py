"""Hermes3D adapter shell — Protocol + skeletons (Phase 1, detect-only).

Phase 3 will implement read-only methods (validate/healthcheck/status/open_*).
Phase 6 will implement write methods (dry_run/execute) behind the
dry_run_token + Confirmation envelope per ADR-008.

Importing this package side-effect-imports every skeleton module so the
`@register` decorators fire and `all_registered()` returns the full catalog.
None of the adapter modules invoke external tools at import time.
"""

from . import (  # noqa: F401  -- side-effect imports populate the default registry
    blender,
    blender_mcp,
    cura,
    flsun_slicer,
    fluidd,
    mainsail,
    moonraker,
    octoprint,
    orca_slicer,
    printrun,
    prusa_slicer,
)
