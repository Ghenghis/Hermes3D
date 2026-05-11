"""W17 — /api/health/services on the GUI bridge.

The ``ServiceHealthPage`` React component (``components/health/
ServiceHealthPage.tsx``) consumes ``GET /api/health/services`` against
the GUI bridge on port 8765. The standalone print-farm
:mod:`hermes3d.api.server` already exposes the endpoint via
:func:`hermes3d.api.health.register_health_routes`, but the GUI bridge
:func:`hermes3d.api.app.create_gui_app` did not — W17 audit (A1 +
Codex) confirmed the bridge returns 404, leaving the Service Health
tab permanently empty.

This module bridges the gap by reusing the existing probe machinery:

- :data:`hermes3d.core.health.probe.KNOWN_SERVICES` — the static
  catalogue (MCP/LLM/modeling/api).
- :func:`hermes3d.core.health.probe.moonraker_specs_from_config` —
  per-printer Moonraker specs derived from
  ``03_implementation/config/printers.toml``.
- :func:`hermes3d.api.health.results_to_payload` — the serialiser the
  React :file:`types/serviceHealth.ts` types already match.

The honest-blocked path is preserved: if **zero** probe specs are
registered (e.g. catalogue trimmed to nothing in a future refactor),
the response carries ``accepted=False`` + ``reason="no_health_probes_registered"``
so the UI renders an explicit empty state instead of inventing rows.

References:
- FastAPI bigger applications / routers pattern:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- W15-A20 honest-blocked envelope contract (see ``skills.py``,
  ``connectors.py``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from hermes3d.api.health import results_to_payload
from hermes3d.core.health import (
    KNOWN_SERVICES,
    moonraker_specs_from_config,
    probe_all,
)

router = APIRouter()


@router.get("/api/health/services")
def list_service_health() -> dict[str, Any]:
    """Return TCP/HTTP probe results for every registered service.

    The response shape matches :func:`hermes3d.api.health.results_to_payload`
    exactly so :file:`ui/src/types/serviceHealth.ts` and
    :file:`ui/src/api/adapters.live.ts` continue to work without
    modification:

        {
          "accepted": bool,
          "status": "ready" | "blocked",
          "reason": str | null,
          "results": [ ServiceHealthEntry, ... ]
        }

    Honest empty: when there are zero registered probes (catalogue
    trimmed + no printers.toml on disk), we surface
    ``accepted=False`` + ``reason="no_health_probes_registered"`` and
    ``results: []``. The Service Health page renders an explicit empty
    state in that case rather than fabricating rows.
    """
    printer_specs = moonraker_specs_from_config()
    total_specs = len(KNOWN_SERVICES) + len(printer_specs)
    if total_specs == 0:
        return {
            "accepted": False,
            "status": "blocked",
            "reason": "no_health_probes_registered",
            "results": [],
        }
    results = probe_all(extra=printer_specs)
    payload = results_to_payload(results)
    # results_to_payload returns {"results": [...]}. Extend with the
    # honest-blocked envelope tokens so the UI can branch on accepted
    # without recomputing.
    payload.update(
        {
            "accepted": True,
            "status": "ready",
            "reason": None,
        }
    )
    return payload
