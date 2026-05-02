"""Local-only FastAPI bridge for Phase 3.1 fleet snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

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
    ledger: OrchestrationLedger | None = None
    supervisor: OfflineSupervisor | None = None
    planner: PlannerAgent | None = None

    def __post_init__(self) -> None:
        if self.ledger is None and self.supervisor is not None:
            self.ledger = self.supervisor.ledger

    def update_last_poll_snapshot(self, printers: Sequence[PrinterSnapshot]) -> None:
        self.last_poll_snapshot = tuple(deepcopy([dict(printer) for printer in printers]))

    def printers(self) -> list[dict[str, object]]:
        return deepcopy([dict(printer) for printer in self.last_poll_snapshot])

    def preview_plan(self, prompt: str) -> dict[str, object]:
        normalized_prompt = " ".join(prompt.strip().split())
        if not normalized_prompt:
            raise HTTPException(status_code=422, detail="prompt is required")
        prompt_sha = stable_sha(normalized_prompt.lower())
        run_id = f"plan-preview-{prompt_sha[:12]}-{uuid4().hex[:8]}"
        supervisor = self._ensure_supervisor()
        planner = self._ensure_planner()
        token = supervisor.issue_token(
            agent_id="bridge.planner.preview",
            tools=frozenset({"planner.plan"}),
        )
        result = planner.plan(
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
        payload = serialize_dag(result.result.value)
        payload["metadata"] = {
            **dict(payload["metadata"]),
            "prompt_sha256": prompt_sha,
        }
        return payload

    def run_summary(self, run_id: str) -> dict[str, object]:
        if self.ledger is None:
            raise HTTPException(status_code=404, detail="run not found")
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

    def provider_health(self) -> dict[str, object]:
        if self.ledger is None:
            return {"providers": []}
        from hermes3d.gateways.providers import load_probe_policy

        probe_policy = load_probe_policy()
        threshold = datetime.now(UTC) - timedelta(minutes=probe_policy.probe_freshness_minutes)
        providers: list[dict[str, object]] = []
        for provider_id in sorted(probe_policy.providers.keys()):
            most_recent = self._most_recent_probe(provider_id)
            if most_recent is None:
                providers.append(
                    {
                        "provider_id": provider_id,
                        "status": "idle",
                        "last_probe_utc": None,
                        "http_status": None,
                        "latency_ms": None,
                        "stale": False,
                    }
                )
                continue
            event_time = datetime.fromisoformat(most_recent.ts_utc.replace("Z", "+00:00"))
            is_stale = event_time < threshold
            parsed = _parse_probe_event(most_recent.message)
            if is_stale:
                status = "amber"
            elif most_recent.verdict == "pass":
                status = "green"
            else:
                status = "red"
            providers.append(
                {
                    "provider_id": provider_id,
                    "status": status,
                    "last_probe_utc": most_recent.ts_utc,
                    "http_status": parsed.get("http_status"),
                    "latency_ms": parsed.get("latency_ms"),
                    "stale": is_stale,
                }
            )
        return {"providers": providers}

    def _most_recent_probe(self, provider_id: str):
        needle = f"provider={provider_id} "
        for event in reversed(self.ledger.events()):
            if event.tool == "provider.probe" and needle in event.message:
                return event
        return None

    def _ensure_ledger(self) -> OrchestrationLedger:
        if self.ledger is None:
            self.ledger = OrchestrationLedger(Path("var") / "orchestration" / "ledger.sqlite")
        return self.ledger

    def _ensure_supervisor(self) -> OfflineSupervisor:
        if self.supervisor is None:
            self.supervisor = OfflineSupervisor(ledger=self._ensure_ledger())
        return self.supervisor

    def _ensure_planner(self) -> PlannerAgent:
        if self.planner is None:
            self.planner = PlannerAgent(
                supervisor=self._ensure_supervisor(),
                ledger=self._ensure_ledger(),
            )
        return self.planner


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

    @app.get("/api/providers/health")
    async def get_provider_health() -> dict[str, object]:
        return bridge_state.provider_health()

    return app


def _parse_probe_event(message: str) -> dict[str, int | None]:
    """Parse 'provider=X status=N latency_ms=M excerpt=...' into status fields."""

    result: dict[str, int | None] = {"http_status": None, "latency_ms": None}
    for token in message.split():
        if token.startswith("status="):
            try:
                result["http_status"] = int(token.removeprefix("status="))
            except ValueError:
                pass
        elif token.startswith("latency_ms="):
            try:
                result["latency_ms"] = int(token.removeprefix("latency_ms="))
            except ValueError:
                pass
    return result


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
