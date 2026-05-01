"""Deterministic template planner for Phase 3.2."""

from __future__ import annotations

from hermes3d.orchestration import (
    CapabilityToken,
    Err,
    OfflineSupervisor,
    Ok,
    PlanRequest,
    PlanResult,
)
from hermes3d.orchestration.dag import TaskDAG, TaskNode
from hermes3d.orchestration.supervisor import stable_sha
from hermes3d.orchestration.types import Result

PLANNER_TOOL = "planner.plan"
GEN3D_TOOL = "gen3d.generate"
WRITE_CLASS_TOOLS = frozenset(
    {
        "printer.write",
        "printer.move",
        "printer.print_start",
        "slicer.execute",
        "blender.execute",
    }
)
FIXTURE_PROMPTS = {
    "calibration cube": {
        "kind": "gen3d.fixture.calibration_cube",
        "seed": 3201,
    },
    "mini vase": {
        "kind": "gen3d.fixture.mini_vase",
        "seed": 3202,
    },
}
UNSAFE_FIXTURE_PROMPTS = {
    "start printer": "printer.print_start",
    "slice and print": "slicer.execute",
}


class PlannerAgent:
    """Maps fixture prompts to deterministic DAGs without external providers."""

    def __init__(
        self,
        *,
        supervisor: OfflineSupervisor,
        registered_tools: frozenset[str] | None = None,
    ) -> None:
        self.supervisor = supervisor
        self.registered_tools = (
            supervisor.registered_tools() if registered_tools is None else frozenset(registered_tools)
        )

    def plan(self, request: PlanRequest, *, token: CapabilityToken | None) -> PlanResult:
        return self.supervisor.dispatch_plan(request, token=token, handler=self._plan_template)

    def _plan_template(self, request: PlanRequest) -> Result[TaskDAG]:
        prompt_key = _normalize_prompt(request.prompt)
        unsafe_tool = UNSAFE_FIXTURE_PROMPTS.get(prompt_key)
        if unsafe_tool is not None or prompt_key in WRITE_CLASS_TOOLS:
            return Err(
                "write_tool_refused",
                "planner template refuses write-class tools",
                recoverable=False,
            )

        fixture = FIXTURE_PROMPTS.get(prompt_key)
        if fixture is None:
            return Err("fixture_prompt_unknown", "planner only accepts fixture prompts")

        node = TaskNode(
            node_id="gen3d-simulated",
            tool=GEN3D_TOOL,
            kind=str(fixture["kind"]),
            inputs={
                "prompt": request.prompt,
                "seed": fixture["seed"],
            },
            retry_budget=0,
            gate_set=frozenset({"phase3.2.simulated-only"}),
        )
        dag = TaskDAG(
            dag_id=stable_sha(
                {
                    "prompt": prompt_key,
                    "tool": node.tool,
                    "seed": fixture["seed"],
                }
            ),
            run_id=request.run_id,
            nodes=(node,),
            edges=(),
            metadata={
                "planner": "deterministic-template",
                "fixture_prompt": prompt_key,
            },
        )
        unregistered = sorted(
            {planned_node.tool for planned_node in dag.nodes if planned_node.tool not in self.registered_tools}
        )
        if unregistered:
            return Err(
                "tool_unregistered",
                f"planner fixture references unregistered tool(s): {', '.join(unregistered)}",
            )
        return Ok(dag, "planner produced deterministic fixture DAG")


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().lower().split())
