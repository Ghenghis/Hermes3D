"""FastAPI application for the Hermes3D GUI backend."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hermes3d.api.routes import (
    agent_updates,
    agents,
    approvals,
    artifacts,
    autonomous,
    autopilot,
    code_operator,
    design,
    desktop_compat,
    desktop_updates,
    events,
    generation,
    jobs,
    learning,
    modules,
    notifications,
    observe,
    plugins,
    ports,
    printer_safety,
    printers,
    roadmap,
    settings,
    source_os,
    system,
    update_center,
    voice,
)
from hermes3d.db.init import init_db


def create_gui_app() -> FastAPI:
    app = FastAPI(title="Hermes3D GUI API", version="0.7.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://127.0.0.1",
        ],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        init_db()

    @app.middleware("http")
    async def _optional_api_auth(request: Request, call_next):
        token = _api_token()
        if not _api_auth_required() or not token or request.method == "OPTIONS" or request.url.path in {"/health"}:
            return await call_next(request)
        header = request.headers.get("authorization", "")
        supplied = header.removeprefix("Bearer ").strip() if header.lower().startswith("bearer ") else ""
        if not supplied or not hmac.compare_digest(supplied, token):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "status": "unauthorized",
                        "reason": "Hermes3D GUI API auth is enabled; provide a valid bearer token.",
                    }
                },
            )
        return await call_next(request)

    for route_module in [
        modules,
        jobs,
        approvals,
        artifacts,
        plugins,
        voice,
        learning,
        roadmap,
        design,
        generation,
        printers,
        printer_safety,
        settings,
        system,
        ports,
        autopilot,
        code_operator,
        events,
        agents,
        agent_updates,
        desktop_compat,
        desktop_updates,
        update_center,
        autonomous,
        notifications,
        observe,
        source_os,
    ]:
        app.include_router(route_module.router)

    return app


def _api_token() -> str:
    return os.environ.get("HERMES3D_API_TOKEN") or os.environ.get("HERMES3D_API_KEY") or ""


def _api_auth_required() -> bool:
    return os.environ.get("HERMES3D_REQUIRE_API_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}


app = create_gui_app()
