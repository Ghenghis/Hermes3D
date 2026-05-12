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

import os
import threading
import time
from typing import Any

from fastapi import APIRouter

from hermes3d.api.health import results_to_payload
from hermes3d.core.health import (
    KNOWN_SERVICES,
    moonraker_specs_from_config,
    probe_all,
)

router = APIRouter()


# W21-P0-C: in-memory TTL cache for /api/health/services.
# The parallel probe pool runs against its full PROBE_ALL_DEADLINE_S
# budget (~3.5 s) whenever ANY catalogued service is slow or unreachable.
# Dashboard cold-start was therefore pinned at ~3.5 s on this endpoint;
# the Pass-2 audit measured 3.577 s and flagged it as a P0.
# Caching here means: pay the budget ONCE every CACHE_TTL_S, and serve
# repeat callers (the React Service Health page poll loop, multiple
# tabs, etc.) from memory in <1 ms.
#
# Mutex serialises concurrent cold-start probes (thundering herd):
# the first caller pays the probe cost, the rest wait on the lock and
# then read the freshly-populated cache.
#
# Override TTL via env: HERMES3D_HEALTH_SERVICES_CACHE_TTL_S
# Force a fresh probe via query param: ?fresh=1
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}


def _cache_ttl_s() -> float:
    """Read TTL from env at call-time so tests + operators can override live."""
    raw = os.environ.get("HERMES3D_HEALTH_SERVICES_CACHE_TTL_S", "15.0")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 15.0


def _build_payload() -> dict[str, Any]:
    """Run the actual probe + envelope. Separated so the cache layer can
    call it without duplicating the honest-blocked branch."""
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
    payload.update(
        {
            "accepted": True,
            "status": "ready",
            "reason": None,
        }
    )
    return payload


@router.get("/api/health/services")
def list_service_health(fresh: int = 0) -> dict[str, Any]:
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

    Caching (W21-P0-C): results are cached for HERMES3D_HEALTH_SERVICES_
    CACHE_TTL_S seconds (default 15 s). Pass ``?fresh=1`` to bypass the
    cache for a real-time probe. The cache lives in process memory only;
    a backend restart clears it. The lock serialises concurrent cold-
    start callers so we never pay the probe cost more than once per TTL.
    """
    ttl = _cache_ttl_s()
    now = time.monotonic()
    if not fresh and ttl > 0 and _CACHE["payload"] is not None and (now - _CACHE["ts"]) < ttl:
        # Fast path — cache hit, no lock acquisition needed.
        return _CACHE["payload"]
    # Slow path / cache miss / forced fresh — serialise concurrent callers.
    with _CACHE_LOCK:
        # Re-check after acquiring the lock: another caller may have
        # populated the cache while we waited.
        now = time.monotonic()
        if not fresh and ttl > 0 and _CACHE["payload"] is not None and (now - _CACHE["ts"]) < ttl:
            return _CACHE["payload"]
        payload = _build_payload()
        _CACHE["payload"] = payload
        _CACHE["ts"] = time.monotonic()
        return payload
