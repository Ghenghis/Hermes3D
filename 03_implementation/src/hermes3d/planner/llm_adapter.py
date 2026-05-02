"""Safe adapter between the planner and the bounded LLM gateway."""

from __future__ import annotations

from hermes3d.gateways.llm import LLMCaller, LLMGateway
from hermes3d.orchestration.types import BudgetState, CapabilityToken, Err, Ok, Result


def try_llm_plan(
    prompt: str,
    *,
    token: CapabilityToken,
    budget: BudgetState,
    gateway: LLMGateway,
    caller: LLMCaller | None,
) -> Result[str]:
    """Return raw LLM plan text or a controlled gateway error."""

    try:
        completion = gateway.complete(prompt, token=token, budget=budget, caller=caller)
    except Exception as exc:  # pragma: no cover - defensive wrapper boundary
        return Err("planner_llm_exception", str(exc), recoverable=True)
    if isinstance(completion, Err):
        return completion
    return Ok(completion.value.redacted_text, "LLM planner text returned")
