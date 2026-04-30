"""REST API server (FastAPI).

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §26 (REST API)

Run with::

    uvicorn hermes3d.api.server:app --host 0.0.0.0 --port 7861

Endpoints:

  GET  /health                              liveness + version
  GET  /fleet                               list all 12 printers
  GET  /fleet/{printer_id}                  get a profile
  GET  /fleet/{printer_id}/state            live Moonraker state
  POST /fleet/probe                         probe all printers, return statuses

  POST /validate                            run Truth Gate on uploaded mesh
  POST /dispatch                            run dispatcher

  POST /queue/jobs                          enqueue a job
  GET  /queue/jobs                          list jobs
  GET  /queue/jobs/{job_id}                 get one job
  POST /queue/jobs/{job_id}/cancel          cancel a job

  GET  /spools                              list spools
  POST /spools                              register a spool
  POST /spools/{spool_id}/load              load a spool on a printer
  POST /spools/{spool_id}/consume           record consumption

  POST /proof/verify                        verify a proof envelope JSON

  GET  /metrics                             aggregated print history metrics
  GET  /metrics/prometheus                  Prometheus-format text exposition

Authentication: a single shared bearer token from HERMES3D_API_TOKEN. If
unset, the server runs in "open" mode and logs a warning. CORS is open to
localhost by default.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import PlainTextResponse, JSONResponse
    from pydantic import BaseModel, Field
    _FASTAPI_AVAILABLE = True
except ImportError:  # FastAPI is optional at install time
    _FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment]


log = logging.getLogger(__name__)


# =============================================================================
# Request/response models — defined at module scope so FastAPI's TypeAdapter
# can resolve them. (Pydantic v2 has trouble with closure-defined models.)
# =============================================================================

if _FASTAPI_AVAILABLE:
    class DispatchBody(BaseModel):
        mesh_extents_mm: list[float]
        mesh_xy_radius_mm: float | None = None
        material: str = "PLA"
        quality_level: str = "normal"
        strategy: str = "auto"
        excluded_printers: list[str] = Field(default_factory=list)
        allowed_printers: list[str] = Field(default_factory=list)

    class JobBody(BaseModel):
        mesh_path: str
        mesh_sha256: str
        material: str
        quality_level: str = "normal"
        layer_height_mm: float = 0.2
        requested_strategy: str = "auto"
        notes: str = ""

    class SpoolBody(BaseModel):
        material: str
        color: str
        color_hex: str
        vendor: str
        initial_grams: float
        diameter_mm: float = 1.75
        notes: str = ""

    class SpoolLoadBody(BaseModel):
        printer_id: str

    class SpoolConsumeBody(BaseModel):
        grams: float
        job_id: str | None = None



# =============================================================================
# Defaults (env-overridable)
# =============================================================================

DEFAULT_QUEUE = os.environ.get("HERMES3D_QUEUE", "./var/queue.json")
DEFAULT_SPOOLS = os.environ.get("HERMES3D_SPOOLS", "./var/spools.json")
DEFAULT_HISTORY = os.environ.get("HERMES3D_HISTORY", "./var/history.jsonl")
DEFAULT_TOKEN = os.environ.get("HERMES3D_API_TOKEN", "")


# =============================================================================
# App factory (so tests can build a fresh app without env coupling)
# =============================================================================


def create_app(*, api_token: str = DEFAULT_TOKEN,
               queue_path: str = DEFAULT_QUEUE,
               spools_path: str = DEFAULT_SPOOLS,
               history_path: str = DEFAULT_HISTORY,
               cors_origins: tuple[str, ...] = ("http://localhost",
                                                  "http://localhost:3000",
                                                  "http://127.0.0.1"),
               ) -> "FastAPI":
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError(
            "FastAPI is not installed. Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Hermes3D-OS Lite REST API",
        version="5.0.0",
        description="Programmatic access to the agentic 3D print pipeline.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if not api_token:
        log.warning("HERMES3D_API_TOKEN unset — API is OPEN (no auth)")

    # Lazy imports — avoid cost at module import time
    from hermes3d.core.printers import FLEET, get_profile
    from hermes3d.core.printers.moonraker_client import probe_fleet, MoonrakerClient
    from hermes3d.core.agents.dispatcher import dispatch as run_dispatch, DispatchRequest, DispatchStrategy
    from hermes3d.core.agents.job_queue import JobQueue, JobState
    from hermes3d.core.farm.spool_tracker import SpoolTracker
    from hermes3d.core.farm.print_history import PrintHistory, aggregate_metrics
    from hermes3d.core.proof.proof_envelope import verify_proof, ProofVerificationError

    queue = JobQueue(queue_path)
    spools = SpoolTracker(spools_path)
    history = PrintHistory(history_path)

    # ---- Auth ----
    def _auth(authorization: str | None) -> None:
        if not api_token:
            return  # open mode
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token required")
        if authorization.removeprefix("Bearer ").strip() != api_token:
            raise HTTPException(status_code=403, detail="Invalid token")

    # ---- Endpoints ----
    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True, "version": "5.0.0",
            "ts_unix": time.time(),
            "fleet_size": len(FLEET),
        }

    @app.get("/fleet")
    def fleet() -> list[dict[str, Any]]:
        from dataclasses import asdict
        return [
            {
                "profile_id": p.profile_id,
                "manufacturer": p.manufacturer,
                "model": p.model,
                "kinematics": p.kinematics.value,
                "bed": asdict(p.bed),
                "z_height_mm": p.z_height_mm,
                "hotend_max_c": p.hotend_max_c,
                "bed_max_c": p.bed_max_c,
                "enclosed": p.enclosed,
                "direct_drive": p.direct_drive,
                "moonraker_url_default": p.moonraker_url_default,
            }
            for p in FLEET
        ]

    @app.get("/fleet/{printer_id}")
    def fleet_one(printer_id: str) -> dict[str, Any]:
        try:
            p = get_profile(printer_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown printer")
        from dataclasses import asdict
        d = {k: v for k, v in asdict(p).items()}
        d["kinematics"] = p.kinematics.value
        return d

    @app.get("/fleet/{printer_id}/state")
    def fleet_state(printer_id: str,
                     authorization: str | None = Header(default=None)
                     ) -> dict[str, Any]:
        _auth(authorization)
        p = get_profile(printer_id)
        client = MoonrakerClient(p.moonraker_url_default, timeout_s=2.5)
        try:
            return client.printer_state()
        except Exception as exc:  # noqa: BLE001
            return {"reachable": False, "error": str(exc)}

    @app.post("/fleet/probe")
    def fleet_probe(authorization: str | None = Header(default=None)
                     ) -> list[dict[str, Any]]:
        _auth(authorization)
        return probe_fleet(timeout_s=2.5)

    @app.post("/dispatch")
    def dispatch_endpoint(body: DispatchBody = Body(...),
                           authorization: str | None = Header(default=None)
                           ) -> dict[str, Any]:
        _auth(authorization)
        try:
            strategy = DispatchStrategy(body.strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown strategy")
        req = DispatchRequest(
            mesh_extents_mm=body.mesh_extents_mm,
            mesh_xy_radius_mm=body.mesh_xy_radius_mm,
            material=body.material,
            quality_level=body.quality_level,
            strategy=strategy,
            excluded_printers=tuple(body.excluded_printers),
            allowed_printers=tuple(body.allowed_printers),
        )
        decision = run_dispatch(req)
        return {
            "selected_printer_id": decision.selected_printer_id,
            "rationale": decision.rationale,
            "candidates": [
                {
                    "printer_id": c.printer_id,
                    "score": c.score,
                    "fits": c.fits,
                    "eligible": c.eligible,
                    "reasons": list(c.reasons),
                    "blockers": list(c.blockers),
                }
                for c in decision.candidates
            ],
        }

    @app.post("/queue/jobs")
    def enqueue_job(body: JobBody = Body(...),
                     authorization: str | None = Header(default=None)
                     ) -> dict[str, Any]:
        _auth(authorization)
        j = queue.enqueue(
            mesh_path=body.mesh_path,
            mesh_sha256=body.mesh_sha256,
            material=body.material,
            quality_level=body.quality_level,
            layer_height_mm=body.layer_height_mm,
            requested_strategy=body.requested_strategy,
            notes=body.notes,
        )
        return j.to_dict()

    @app.get("/queue/jobs")
    def list_jobs(state: str | None = None,
                   authorization: str | None = Header(default=None)
                   ) -> list[dict[str, Any]]:
        _auth(authorization)
        jstate = JobState(state) if state else None
        return [j.to_dict() for j in queue.list(state=jstate)]

    @app.get("/queue/jobs/{job_id}")
    def get_job(job_id: str,
                 authorization: str | None = Header(default=None)
                 ) -> dict[str, Any]:
        _auth(authorization)
        try:
            return queue.get(job_id).to_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

    @app.post("/queue/jobs/{job_id}/cancel")
    def cancel_job(job_id: str,
                    authorization: str | None = Header(default=None)
                    ) -> dict[str, Any]:
        _auth(authorization)
        try:
            j = queue.transition_job(job_id, JobState.CANCELLED,
                                       reason="cancelled via API")
            return j.to_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.get("/spools")
    def list_spools_(authorization: str | None = Header(default=None)
                      ) -> list[dict[str, Any]]:
        _auth(authorization)
        return [s.to_dict() for s in spools.list()]

    @app.post("/spools")
    def add_spool(body: SpoolBody = Body(...),
                   authorization: str | None = Header(default=None)
                   ) -> dict[str, Any]:
        _auth(authorization)
        s = spools.add(material=body.material, color=body.color,
                        color_hex=body.color_hex, vendor=body.vendor,
                        diameter_mm=body.diameter_mm,
                        initial_grams=body.initial_grams, notes=body.notes)
        return s.to_dict()

    @app.post("/spools/{spool_id}/load")
    def load_spool(spool_id: str, body: SpoolLoadBody = Body(...),
                     authorization: str | None = Header(default=None)
                     ) -> dict[str, Any]:
        _auth(authorization)
        s = spools.load_on_printer(spool_id, body.printer_id)
        return s.to_dict()

    @app.post("/spools/{spool_id}/consume")
    def consume_spool(spool_id: str, body: SpoolConsumeBody = Body(...),
                       authorization: str | None = Header(default=None)
                       ) -> dict[str, Any]:
        _auth(authorization)
        s = spools.consume(spool_id, body.grams, job_id=body.job_id)
        return s.to_dict()

    @app.post("/proof/verify")
    def proof_verify(payload: dict[str, Any] = Body(...),
                       authorization: str | None = Header(default=None)
                       ) -> dict[str, Any]:
        _auth(authorization)
        path = payload.get("proof_path")
        if not path or not Path(path).exists():
            raise HTTPException(status_code=400, detail="proof_path missing or not found")
        try:
            env = verify_proof(path,
                                check_files=bool(payload.get("check_files", True)))
            return {"verified": True, "schema_version": env.schema_version,
                    "mesh_sha256": env.mesh.get("sha256")}
        except ProofVerificationError as exc:
            return JSONResponse(status_code=400,
                                  content={"verified": False,
                                            "error": str(exc)})

    @app.get("/metrics")
    def metrics(authorization: str | None = Header(default=None)
                  ) -> dict[str, Any]:
        _auth(authorization)
        m = aggregate_metrics(history)
        return {
            "total_prints": m.total_prints,
            "total_print_hours": round(m.total_print_hours, 2),
            "total_filament_kg": round(m.total_filament_kg, 3),
            "per_printer": {
                pid: {
                    "total_prints": pa.total_prints,
                    "successful": pa.successful,
                    "failed": pa.failed,
                    "cancelled": pa.cancelled,
                    "success_rate": round(pa.success_rate, 3),
                    "total_print_minutes": round(pa.total_print_minutes, 1),
                    "total_filament_grams": round(pa.total_filament_grams, 1),
                }
                for pid, pa in m.per_printer.items()
            },
            "per_material": {
                mat: {
                    "total_prints": ma.total_prints,
                    "successful": ma.successful,
                    "total_filament_grams": round(ma.total_filament_grams, 1),
                }
                for mat, ma in m.per_material.items()
            },
        }

    @app.get("/metrics/prometheus", response_class=PlainTextResponse)
    def metrics_prom() -> str:
        m = aggregate_metrics(history)
        lines = [
            "# HELP hermes3d_total_prints Total prints recorded",
            "# TYPE hermes3d_total_prints counter",
            f"hermes3d_total_prints {m.total_prints}",
            "# HELP hermes3d_total_print_hours Total print hours",
            "# TYPE hermes3d_total_print_hours counter",
            f"hermes3d_total_print_hours {m.total_print_hours:.2f}",
            "# HELP hermes3d_total_filament_kg Total filament consumed (kg)",
            "# TYPE hermes3d_total_filament_kg counter",
            f"hermes3d_total_filament_kg {m.total_filament_kg:.3f}",
            "# HELP hermes3d_printer_success_rate Success rate by printer",
            "# TYPE hermes3d_printer_success_rate gauge",
        ]
        for pid, pa in m.per_printer.items():
            lines.append(
                f'hermes3d_printer_success_rate{{printer="{pid}"}} '
                f'{pa.success_rate:.3f}'
            )
            lines.append(
                f'hermes3d_printer_total_prints{{printer="{pid}"}} '
                f'{pa.total_prints}'
            )
        return "\n".join(lines) + "\n"

    return app


# Default app for `uvicorn hermes3d.api.server:app`
if _FASTAPI_AVAILABLE:
    try:
        app = create_app()
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to create default API app: %s", exc)
        app = None  # type: ignore[assignment]
else:
    app = None  # type: ignore[assignment]


__all__ = ["app", "create_app"]
