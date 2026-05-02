"""Deterministic template planner for Phase 3.2."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from hermes3d.gateways.budget import fresh_budget_state
from hermes3d.gateways.llm import LLMCaller, LLMGateway, LLMPolicy
from hermes3d.orchestration import (
    CapabilityToken,
    Err,
    OfflineSupervisor,
    Ok,
    PlanRequest,
    PlanResult,
)
from hermes3d.orchestration.dag import TaskDAG, TaskNode
from hermes3d.orchestration.ledger import LedgerEvent, OrchestrationLedger
from hermes3d.orchestration.supervisor import stable_sha
from hermes3d.orchestration.types import BudgetState, PlannerMode, Result
from hermes3d.planner import try_llm_plan

PLANNER_TOOL = "planner.plan"
GEN3D_TOOL = "gen3d.generate"
MAX_LLM_PLAN_BYTES = 4096
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
        ledger: OrchestrationLedger | None = None,
    ) -> None:
        self.supervisor = supervisor
        self.ledger = ledger
        self.registered_tools = (
            supervisor.registered_tools()
            if registered_tools is None
            else frozenset(registered_tools)
        )
        self.llm_attempt_log: list[dict[str, str]] = []

    def plan(
        self,
        request: PlanRequest,
        *,
        token: CapabilityToken | None,
        llm_token: CapabilityToken | None = None,
        budget: BudgetState | None = None,
        gateway: LLMGateway | None = None,
        caller: LLMCaller | None = None,
        policy: LLMPolicy | None = None,
        mode: PlannerMode | None = None,
    ) -> PlanResult:
        selected_mode = _selected_mode(mode=mode, policy=policy, gateway=gateway)
        if selected_mode == "template":
            return self.supervisor.dispatch_plan(request, token=token, handler=self._plan_template)

        return self.supervisor.dispatch_plan(
            request,
            token=token,
            handler=lambda plan_request: self._plan_llm_with_template_fallback(
                plan_request,
                llm_token=llm_token or token,
                budget=budget or fresh_budget_state(),
                gateway=gateway,
                caller=caller,
            ),
        )

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
                "planner_mode": "template",
            },
        )
        unregistered = sorted(
            {
                planned_node.tool
                for planned_node in dag.nodes
                if planned_node.tool not in self.registered_tools
            }
        )
        if unregistered:
            return Err(
                "tool_unregistered",
                f"planner fixture references unregistered tool(s): {', '.join(unregistered)}",
            )
        return Ok(dag, "planner produced deterministic fixture DAG")

    def _plan_llm_with_template_fallback(
        self,
        request: PlanRequest,
        *,
        llm_token: CapabilityToken | None,
        budget: BudgetState,
        gateway: LLMGateway | None,
        caller: LLMCaller | None,
    ) -> Result[TaskDAG]:
        self._active_llm_request = request
        fallback_result = self._template_fallback(request)
        if gateway is None or llm_token is None:
            reason = "gateway_or_token_missing"
            self._log_llm_attempt("fallback", reason)
            self._emit_fallback_ledger(reason=reason, llm_token=llm_token)
            return fallback_result

        llm_result = try_llm_plan(
            request.prompt,
            token=llm_token,
            budget=budget,
            gateway=gateway,
            caller=caller,
        )
        if isinstance(llm_result, Err):
            reason = llm_result.code
            self._log_llm_attempt("fallback", reason)
            self._emit_fallback_ledger(reason=reason, llm_token=llm_token)
            return fallback_result

        accepted = self._validated_llm_plan(request, llm_result.value)
        if isinstance(accepted, Err):
            reason = accepted.message or accepted.code
            self._log_llm_attempt("fallback", reason)
            self._emit_fallback_ledger(reason=reason, llm_token=llm_token)
            return fallback_result

        self._log_llm_attempt("success", "accepted")
        return accepted

    def _template_fallback(self, request: PlanRequest) -> Result[TaskDAG]:
        fallback_result = self._plan_template(request)
        if isinstance(fallback_result, Ok):
            return fallback_result
        return self._plan_template(replace(request, prompt="calibration cube"))

    def _validated_llm_plan(self, request: PlanRequest, plan_text: str) -> Result[TaskDAG]:
        normalized = _normalize_prompt(plan_text)
        if not normalized:
            return Err("planner_output_rejected", "empty")
        if len(plan_text.encode("utf-8")) > MAX_LLM_PLAN_BYTES:
            return Err("planner_output_rejected", "too_large")
        if _contains_forbidden_plan_text(normalized):
            return Err("planner_output_rejected", "forbidden_pattern")
        if normalized not in FIXTURE_PROMPTS:
            return Err("planner_output_rejected", "unknown_template")

        suggested_request = replace(request, prompt=normalized)
        template_result = self._plan_template(suggested_request)
        if isinstance(template_result, Err):
            return template_result

        dag = template_result.value
        llm_metadata = {
            **dag.metadata,
            "planner": "llm-gateway-suggestion",
            "planner_mode": "llm",
            "source_prompt": _normalize_prompt(request.prompt),
        }
        return Ok(
            TaskDAG(
                dag_id=dag.dag_id,
                run_id=dag.run_id,
                nodes=dag.nodes,
                edges=dag.edges,
                max_depth=dag.max_depth,
                max_fanout=dag.max_fanout,
                metadata=llm_metadata,
            ),
            "planner accepted LLM suggestion through deterministic template",
        )

    def _log_llm_attempt(self, result: str, reason: str) -> None:
        self.llm_attempt_log.append(
            {
                "event": "planner.llm_attempt",
                "result": result,
                "reason": reason,
            }
        )

    def _emit_fallback_ledger(self, *, reason: str, llm_token: CapabilityToken | None) -> None:
        if self.ledger is None:
            return
        request = getattr(self, "_active_llm_request", None)
        if request is None:
            run_id = "planner-fallback-unknown"
            prompt = ""
        else:
            run_id = request.run_id
            prompt = request.prompt
        token_id = llm_token.token_id if llm_token is not None else "no_llm_token"
        self.ledger.append(
            LedgerEvent(
                ts_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                run_id=run_id,
                agent_id="planner",
                tool="planner.fallback",
                inputs_sha=stable_sha({"prompt": _normalize_prompt(prompt)}),
                outputs_sha=stable_sha({"fallback": reason}),
                verdict="fail",
                message=f"{reason} token_id={token_id}",
            )
        )


def _normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.strip().lower().split())


def _selected_mode(
    *,
    mode: PlannerMode | None,
    policy: LLMPolicy | None,
    gateway: LLMGateway | None,
) -> PlannerMode:
    if mode is not None:
        return mode
    if policy is not None and policy.default_mode == "llm":
        return "llm"
    if gateway is not None and gateway.policy.default_mode == "llm":
        return "llm"
    return "template"


def _contains_forbidden_plan_text(normalized_text: str) -> bool:
    if normalized_text in UNSAFE_FIXTURE_PROMPTS:
        return True
    if normalized_text in WRITE_CLASS_TOOLS:
        return True
    return any(tool in normalized_text for tool in WRITE_CLASS_TOOLS)
