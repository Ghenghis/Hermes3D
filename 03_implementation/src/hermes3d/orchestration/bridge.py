"""Local-only FastAPI bridge for Phase 3.1 fleet snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from hermes3d.agents.planner import PlannerAgent
from hermes3d.orchestration.dag import TaskDAG
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.supervisor import OfflineSupervisor, stable_sha
from hermes3d.orchestration.types import Err, PlanRequest

PrinterSnapshot = Mapping[str, object]

LOCAL_CLIENT_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
LOCAL_CORS_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"


class PlanPreviewRequest(BaseModel):
    prompt: str


@dataclass
class BridgeState:
    """Holds the latest orchestrator poll snapshot for the bridge route."""

    last_poll_snapshot: tuple[PrinterSnapshot, ...] = field(default_factory=tuple)
    ledger: OrchestrationLedger = field(
        default_factory=lambda: OrchestrationLedger(
            Path("var") / "orchestration" / "ledger.sqlite"
        )
    )
    supervisor: OfflineSupervisor | None = None
    planner: PlannerAgent | None = None

    def __post_init__(self) -> None:
        if self.supervisor is None:
            self.supervisor = OfflineSupervisor(ledger=self.ledger)
        if self.planner is None:
            self.planner = PlannerAgent(supervisor=self.supervisor)

    def update_last_poll_snapshot(self, printers: Sequence[PrinterSnapshot]) -> None:
        self.last_poll_snapshot = tuple(deepcopy([dict(printer) for printer in printers]))

    def printers(self) -> list[dict[str, object]]:
        return deepcopy([dict(printer) for printer in self.last_poll_snapshot])

    def preview_plan(self, prompt: str) -> dict[str, object]:
        normalized_prompt = " ".join(prompt.strip().split())
        if not normalized_prompt:
            raise HTTPException(status_code=422, detail="prompt is required")
        run_id = f"plan-preview-{stable_sha(normalized_prompt.lower())[:12]}"
        assert self.supervisor is not None
        assert self.planner is not None
        token = self.supervisor.issue_token(
            agent_id="bridge.planner.preview",
            tools=frozenset({"planner.plan"}),
        )
        result = self.planner.plan(
            PlanRequest(
                run_id=run_id,
                agent_id="bridge.planner.preview",
                prompt=normalized_prompt,
            ),
            token=token,
        )
        if isinstance(result.result, Err):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": result.result.code,
                    "message": result.result.message,
                },
            )
        return serialize_dag(result.result.value)

    def run_summary(self, run_id: str) -> dict[str, object]:
        events = self.ledger.events(run_id)
        if not events:
            raise HTTPException(status_code=404, detail="run not found")
        tools: dict[str, int] = {}
        for event in events:
            tools[event.tool] = tools.get(event.tool, 0) + 1
        return {
            "run_id": run_id,
            "event_count": len(events),
            "tools": tools,
            "events": [
                {
                    "ts_utc": event.ts_utc,
                    "agent_id": event.agent_id,
                    "tool": event.tool,
                    "verdict": event.verdict,
                    "message": event.message,
                }
                for event in events
            ],
        }


def create_bridge_app(state: BridgeState | None = None) -> FastAPI:
    bridge_state = state or BridgeState(tuple(fixture_printer_snapshot()))
    app = FastAPI(
        title="Hermes3D Local Fleet Bridge",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=LOCAL_CORS_ORIGIN_REGEX,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["accept", "content-type"],
    )

    @app.middleware("http")
    async def require_local_client(request: Request, call_next):
        client_host = request.client.host if request.client else ""
        if client_host not in LOCAL_CLIENT_HOSTS:
            return JSONResponse({"detail": "local clients only"}, status_code=403)
        return await call_next(request)

    @app.get("/api/printers")
    async def get_printers() -> list[dict[str, object]]:
        return bridge_state.printers()

    @app.post("/api/plan/preview")
    async def post_plan_preview(payload: PlanPreviewRequest) -> dict[str, object]:
        return bridge_state.preview_plan(payload.prompt)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, object]:
        return bridge_state.run_summary(run_id)

    return app


def serialize_dag(dag: TaskDAG) -> dict[str, object]:
    return {
        "dag_id": dag.dag_id,
        "run_id": dag.run_id,
        "max_depth": dag.max_depth,
        "max_fanout": dag.max_fanout,
        "metadata": dict(dag.metadata),
        "nodes": [
            {
                "node_id": node.node_id,
                "tool": node.tool,
                "kind": node.kind,
                "inputs": dict(node.inputs),
                "retry_budget": node.retry_budget,
                "gate_set": sorted(node.gate_set),
                "depends_on": list(node.depends_on),
            }
            for node in dag.nodes
        ],
        "edges": [
            {
                "from_node": edge.from_node,
                "to_node": edge.to_node,
                "condition": edge.condition,
            }
            for edge in dag.edges
        ],
    }


def fixture_printer_snapshot() -> list[dict[str, object]]:
    live = [
        {
            "id": "t1-1",
            "name": "FLSUN T1 #1",
            "model": "FLSUN T1",
            "ip": "192.168.0.10",
            "status": "printing",
            "adapter": "moonraker",
            "temp_hot": 215,
            "temp_bed": 60,
            "progress": 47,
            "current_job": "frame-bracket-v3.gcode",
            "maintenance_flag": False,
            "camera_url": "http://192.168.0.10:8080/?action=stream",
            "data_source": "live",
        },
        {
            "id": "t1-2",
            "name": "FLSUN T1 #2",
            "model": "FLSUN T1",
            "ip": "192.168.0.11",
            "status": "online",
            "adapter": "moonraker",
            "temp_hot": 25,
            "temp_bed": 24,
            "progress": None,
            "current_job": None,
            "maintenance_flag": False,
            "camera_url": "http://192.168.0.11:8080/?action=stream",
            "data_source": "live",
        },
        {
            "id": "s1",
            "name": "FLSUN S1",
            "model": "FLSUN S1",
            "ip": "192.168.0.12",
            "status": "maintenance",
            "adapter": "moonraker",
            "temp_hot": None,
            "temp_bed": None,
            "progress": None,
            "current_job": None,
            "maintenance_flag": True,
            "camera_url": None,
            "data_source": "live",
        },
        {
            "id": "v400",
            "name": "FLSUN V400",
            "model": "FLSUN V400",
            "ip": "192.168.0.34",
            "status": "online",
            "adapter": "moonraker",
            "temp_hot": 24,
            "temp_bed": 23,
            "progress": None,
            "current_job": None,
            "maintenance_flag": False,
            "camera_url": None,
            "data_source": "live",
        },
    ]
    simulated: list[dict[str, object]] = []
    statuses = ["online", "printing", "online", "offline", "online", "printing", "online", "online"]
    adapters = [
        "moonraker",
        "moonraker",
        "octoprint",
        "moonraker",
        "printrun",
        "moonraker",
        "octoprint",
        "manual",
    ]
    jobs = [None, "demo-cube.gcode", None, None, None, "spindle-housing.gcode", None, None]
    progress = [None, 18, None, None, None, 92, None, None]
    for index, suffix in enumerate(("20", "21", "22", "23", "24", "25", "26", "27")):
        simulated.append(
            {
                "id": f"sim-{suffix}",
                "name": f"Sim Printer {index + 1}",
                "model": "FLSUN T1"
                if index % 3 == 0
                else "FLSUN V400"
                if index % 3 == 1
                else "Generic",
                "ip": f"192.168.0.{suffix}",
                "status": statuses[index],
                "adapter": adapters[index],
                "temp_hot": None if index % 4 == 0 else 25 + index * 5,
                "temp_bed": None if index % 4 == 0 else 24 + index * 2,
                "progress": progress[index],
                "current_job": jobs[index],
                "maintenance_flag": False,
                "camera_url": None,
                "data_source": "mock",
            }
        )
    return live + simulated


app = create_bridge_app()
