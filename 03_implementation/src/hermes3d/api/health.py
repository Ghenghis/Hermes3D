"""Service-health REST endpoint helpers.

Implements ``GET /api/health/services`` which the React Service Health
page consumes. We expose the registration as a function so the existing
single-file ``server.py`` can stay in charge of the FastAPI app object —
no APIRouter modules, matching the kit's existing inline pattern.
"""

from __future__ import annotations

from typing import Any, Callable

try:
    from fastapi import FastAPI, Header, HTTPException

    _FASTAPI_AVAILABLE = True
except ImportError:  # FastAPI optional at install time
    _FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]

from hermes3d.core.health import (
    ProbeResult,
    moonraker_specs_from_config,
    probe_all,
)

__all__ = ["register_health_routes", "results_to_payload"]


def results_to_payload(results: list[ProbeResult]) -> dict[str, Any]:
    """Serialise probe results into the JSON shape the UI expects."""
    return {
        "results": [
            {
                "name": r.spec.name,
                "category": r.spec.category,
                "host": r.spec.host,
                "port": r.spec.port,
                "status": r.status.value,
                "detail": r.detail,
                "latency_ms": round(r.latency_ms, 1),
                "probed_at": r.probed_at,
            }
            for r in results
        ]
    }


def register_health_routes(
    app: FastAPI,
    auth_dep: Callable[[str | None], None],
) -> None:
    """Attach ``GET /api/health/services`` to ``app``.

    ``auth_dep`` is the same ``_auth(authorization)`` callable the rest
    of ``server.py`` uses, so the endpoint inherits whatever bearer-token
    policy the server is running with.
    """
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is not installed. Install with: pip install fastapi uvicorn")

    @app.get("/api/health/services")
    def health_services(  # noqa: D401 — FastAPI handler
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth_dep(authorization)
        printer_specs = moonraker_specs_from_config()
        results = probe_all(extra=printer_specs)
        return results_to_payload(results)
