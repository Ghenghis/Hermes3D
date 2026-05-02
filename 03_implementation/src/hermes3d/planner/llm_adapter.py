"""Wrapper for CP3.3-B LLM planner mode with template fallback.

The existing deterministic PlannerAgent remains unchanged. This adapter chooses
template mode by default and only attempts the offline LLM gateway when policy or
caller explicitly selects mode="llm".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from hermes3d.agents.planner import PlannerAgent
from hermes3d.gateways.llm_gateway import LLMGateway, LLMGatewayContext, LLMPolicy
from hermes3d.orchestration import CapabilityToken, Err, Ok, PlanRequest, PlanResult

PlannerMode = Literal["template", "llm"]


@dataclass
class LLMPlannerAdapter:
    template_planner: PlannerAgent
    gateway: LLMGateway
    policy: LLMPolicy

    @classmethod
    def from_template_planner(
        cls,
        template_planner: PlannerAgent,
        *,
        gateway: LLMGateway | None = None,
    ) -> "LLMPlannerAdapter":
        resolved_gateway = gateway or LLMGateway()
        return cls(
            template_planner=template_planner,
            gateway=resolved_gateway,
            policy=resolved_gateway.policy,
        )

    def plan(
        self,
        request: PlanRequest,
        *,
        token: CapabilityToken | None,
        llm_token: CapabilityToken | None = None,
        mode: PlannerMode | None = None,
        context: LLMGatewayContext | Mapping[str, object] | None = None,
    ) -> PlanResult:
        selected_mode = mode or _planner_mode(self.policy.default_mode)
        if selected_mode == "template":
            return self.template_planner.plan(request, token=token)

        gateway_context = self._context_for(request, llm_token, context)
        completion = self.gateway.complete(request.prompt, gateway_context)
        if isinstance(completion, Err):
            return self.template_planner.plan(request, token=token)

        return self.template_planner.supervisor.dispatch_plan(
            request,
            token=token,
            handler=lambda _request: Ok(completion.value.dag, "planner produced LLM DAG"),
        )

    def _context_for(
        self,
        request: PlanRequest,
        llm_token: CapabilityToken | None,
        context: LLMGatewayContext | Mapping[str, object] | None,
    ) -> LLMGatewayContext:
        if isinstance(context, LLMGatewayContext):
            return context
        merged = dict(context or {})
        return LLMGatewayContext(
            run_id=str(merged.get("run_id", request.run_id)),
            agent_id=str(merged.get("agent_id", request.agent_id)),
            provider=str(merged.get("provider", self.gateway.policy.provider_allowlist[0])),
            token=llm_token,
            registered_tools=frozenset(self.template_planner.registered_tools),
            now_utc=merged.get("now_utc") if "now_utc" in merged else None,
            mock_response=merged.get("mock_response")
            if isinstance(merged.get("mock_response"), str)
            else None,
        )


def _planner_mode(value: str) -> PlannerMode:
    if value == "llm":
        return "llm"
    return "template"
