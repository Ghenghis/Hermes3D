"""FastAPI application for the Hermes3D GUI backend."""

from __future__ import annotations

import hmac
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# W21-A4 MVP-1: hydrate operator-managed .env files BEFORE route imports.
# Several routes (agents, system, code_history) read MINIMAX_API_KEY /
# DEEPSEEK_API_KEY at module import time; if we deferred this until
# create_gui_app() those reads would see missing values. The loader is
# idempotent (override=False) so it is safe across multiple imports.
# See docs/handoffs/W21_A4_HERMES_AGENTS_ACTIVATION_AUDIT_2026-05-11.md
# for the audit that justifies this wiring.
from hermes3d.config.env_loader import load_at_startup as _hydrate_env

_hydrate_env()

# E402 is suppressed for the next two imports BECAUSE the hydration call
# above is intentionally ordered before the route imports. Several routes
# read MINIMAX_API_KEY / DEEPSEEK_API_KEY at module-import time, so any
# reorganization that moves these imports above _hydrate_env() will
# silently regress the env-loader contract.
from hermes3d.api.routes import (  # noqa: E402
    agent_queue,
    agent_updates,
    agents,
    approvals,
    apps,
    artifacts,
    autonomous,
    autopilot,
    code_operator,
    connectors,
    dashboard_layouts,
    design,
    desktop_compat,
    desktop_updates,
    events,
    files,
    generation,
    health_services,
    jobs,
    learning,
    mcp_locks,
    modules,
    notifications,
    observe,
    plugins,
    ports,
    printer_safety,
    printers,
    roadmap,
    settings,
    settings_themes,
    skills,
    slicer,
    source_os,
    system,
    update_center,
    voice,
)
from hermes3d.db.init import init_db  # noqa: E402


def create_gui_app() -> FastAPI:
    # BLK-021 fix (2026-05-09, agent W8-11): synchronously initialize the
    # SQLite schema BEFORE wiring routers so the first cold-start request
    # cannot race route handlers against partially-created tables. Earlier
    # behavior relied solely on FastAPI's @app.on_event("startup") hook,
    # which fires asynchronously and does not block request acceptance under
    # uvicorn's standard worker spawn — see W5-3 GUI E2E drill receipt at
    # 03_implementation/docs/handoffs/HERMES_AGENT_V013_GUI_E2E_2026-05-09.md
    # L137-138 and E2E_BLOCKER_REGISTRY_2026-05-09.md row BLK-021. init_db()
    # is itself idempotent + thread-safe per db/init.py BLK-021 fix.
    init_db()

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
        # Defense in depth: re-run init in case the factory ran in a
        # parent process and the worker forked without inheriting the
        # _initialized flag (e.g. multiprocessing spawn on Windows).
        init_db()
        try:
            from hermes3d.services.job_reconciler import retire_stale_dry_run_jobs

            retire_stale_dry_run_jobs()
        except Exception:
            pass  # stale dry-run cleanup is best-effort; never block startup
        # W19-5: idempotent backfill of var/ files not yet in artifacts DB
        try:
            from hermes3d.api.routes.files import reconcile_var_artifacts

            reconcile_var_artifacts()
        except Exception:
            pass  # reconcile is best-effort; never block startup

        # W21-A4 MVP-2: spawn the orchestrator queue poller as a background
        # task. Reads `.hermes3d_orchestrator/tasks/pending/` every
        # HERMES3D_QUEUE_POLL_INTERVAL seconds (default 15s), claims matching
        # tasks for Hermes Agent personas, and heartbeats live claims.
        #
        # Disable with HERMES3D_QUEUE_POLLER_DISABLED=1 (operator override,
        # used in tests that drive the bridge synchronously).
        try:
            import asyncio as _asyncio

            from hermes3d.services import queue_poller

            app.state.queue_poller_task = _asyncio.create_task(
                queue_poller.run_forever(),
                name="hermes3d.queue_poller",
            )
        except Exception:
            # Poller failure must not block backend boot — bridge is still
            # callable via the HTTP routes even if auto-poll is off.
            pass

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        # Cancel the queue poller cleanly on shutdown so a re-run of
        # the dev server does not leak the task.
        #
        # CRITICAL hotfix (W21-A4 regression in #258):
        # asyncio.CancelledError extends BaseException (NOT Exception) in
        # Python 3.8+. A bare `except Exception:` does NOT catch it; the
        # CancelledError propagates out of the shutdown hook into
        # TestClient.__exit__ — causing test_blk021_coldstart_concurrent_
        # first_requests to report "child errored: CancelledError" when
        # the child fork tears down the app. Catch BaseException so the
        # poller cancel is silent.
        import asyncio as _asyncio

        task = getattr(app.state, "queue_poller_task", None)
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except _asyncio.CancelledError:
                pass
            except BaseException:
                # Defense-in-depth: any other shutdown error must not
                # propagate out of the lifespan hook either.
                pass

    @app.middleware("http")
    async def _optional_api_auth(request: Request, call_next):
        token = _api_token()
        if (
            not _api_auth_required()
            or not token
            or request.method == "OPTIONS"
            or request.url.path in {"/health"}
        ):
            return await call_next(request)
        header = request.headers.get("authorization", "")
        supplied = (
            header.removeprefix("Bearer ").strip() if header.lower().startswith("bearer ") else ""
        )
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
        apps,
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
        # W21-A4 MVP-2: orchestrator queue bridge HTTP surface
        # (/api/agents/queue/{status,claim,release,complete,block}).
        agent_queue,
        agent_updates,
        desktop_compat,
        desktop_updates,
        update_center,
        autonomous,
        notifications,
        observe,
        source_os,
        # W15 A20 backend gaps: skill registry, connector registry,
        # theme palette catalog, per-user dashboard layout persistence.
        skills,
        connectors,
        settings_themes,
        dashboard_layouts,
        # W17 — honest-blocked /api/mcp/locks (W17-NEW-A6 finding).
        # Reads real lock state from the orchestrator's .hermes3d_orchestrator/
        # locks/ directory and returns mcp_server_unreachable when absent.
        mcp_locks,
        # W17 backend gaps: honest-blocked file store surface + GUI
        # bridge service-health probe results (FilesTab + ServiceHealth
        # consumers were 404ing in W17-A1 audit).
        files,
        health_services,
        # W18-A12 — wire the slicer through HTTP so the Design tab can drive
        # PrusaSlicer end-to-end. POST /api/slice + GET /api/slice/{job_id}.
        # NEVER dispatches the resulting G-code (operator freeze 2026-05-11).
        slicer,
    ]:
        app.include_router(route_module.router)

    return app


def _api_token() -> str:
    return os.environ.get("HERMES3D_API_TOKEN") or os.environ.get("HERMES3D_API_KEY") or ""


def _api_auth_required() -> bool:
    return os.environ.get("HERMES3D_REQUIRE_API_AUTH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


app = create_gui_app()
