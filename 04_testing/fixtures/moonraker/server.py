"""FastAPI Moonraker fixture with deterministic read-only responses."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response


def create_app(*, oversized_server_info: bool = False) -> FastAPI:
    app = FastAPI(title="Hermes3D Moonraker Fixture")

    @app.get("/printer/info")
    def printer_info() -> dict[str, object]:
        return {
            "result": {
                "hostname": "fixture-printer-01",
                "state": "ready",
                "state_message": "Printer is ready",
            }
        }

    @app.get("/printer/objects/query")
    def objects_query() -> dict[str, object]:
        return {
            "result": {
                "status": {
                    "print_stats": {"state": "standby", "filename": ""},
                    "virtual_sdcard": {"progress": 0.0},
                    "extruder": {"temperature": 24.0, "target": 0.0},
                    "heater_bed": {"temperature": 23.5, "target": 0.0},
                }
            }
        }

    @app.get("/server/info")
    def server_info() -> Response:
        if oversized_server_info:
            return Response(
                content=b'{"result":{"blob":"' + (b"x" * (256 * 1024)) + b'"}}',
                media_type="application/json",
            )
        return JSONResponse(
            {
                "result": {
                    "hostname": "fixture-printer-01",
                    "klippy_state": "ready",
                    "moonraker_version": "fixture-3.1",
                }
            }
        )

    return app
