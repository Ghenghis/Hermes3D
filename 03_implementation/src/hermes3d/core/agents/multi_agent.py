"""Multi-agent system — Critic / Optimizer / Executor pattern.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §33 (Multi-Agent)

Three composable agents that collaborate on a print decision:

  CriticAgent     — reviews a proposed dispatch decision and either
                     approves it, requests revisions, or rejects with
                     reasons. Pulls from PrintHistory + SkillStore.
  OptimizerAgent  — given a critic's revision request, proposes a
                     modified DispatchRequest (different strategy,
                     different excluded printers, different material).
  ExecutorAgent   — once a decision is approved, sends it through the
                     PrintWorkflow.

The agents communicate via typed messages; one agent's output is
another's input. The loop terminates when the Critic approves OR after
N rounds (default 3).

Each agent is a *pure function* of its inputs and the persistent
SkillStore + PrintHistory. The agents are deterministic (no LLM calls in
the default path) — when an Ollama instance is available, the
CriticAgent can opt into LLM-based critique for richer reasoning.
"""
from __future__ import annotations

import dataclasses
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.agents.dispatcher import (
    DispatchDecision, DispatchRequest, DispatchStrategy, dispatch,
)
from hermes3d.core.farm.print_history import (
    PrintHistory, aggregate_metrics,
)
from hermes3d.core.memory import Skill, SkillKind, SkillStore


log = logging.getLogger(__name__)


class Verdict(str, enum.Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


@dataclass
class CritiqueReport:
    verdict: Verdict
    confidence: float
    reasons: list[str] = field(default_factory=list)
    suggestions: dict[str, Any] = field(default_factory=dict)
    citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["verdict"] = self.verdict.value
        return d


# =============================================================================
# Critic
# =============================================================================


@dataclass
class CriticAgent:
    """Reviews a dispatch decision against history + skills."""

    history: PrintHistory | None = None
    skills: SkillStore | None = None
    # Below this success rate, the critic flags a printer for replacement
    min_acceptable_success_rate: float = 0.6
    # Below this many prints, success rate is too noisy to weigh
    min_evidence_prints: int = 5

    def critique(self, decision: DispatchDecision,
                 request: DispatchRequest) -> CritiqueReport:
        if decision.selected_printer_id is None:
            return CritiqueReport(
                verdict=Verdict.REJECT,
                confidence=1.0,
                reasons=["dispatcher returned no eligible printer"],
            )

        reasons: list[str] = []
        suggestions: dict[str, Any] = {}
        citations: list[str] = []

        # 1. History-based critique: does this printer have a recent
        #    failure pattern with this material?
        if self.history is not None:
            metrics = aggregate_metrics(self.history)
            pa = metrics.per_printer.get(decision.selected_printer_id)
            if pa and pa.total_prints >= self.min_evidence_prints:
                if pa.success_rate < self.min_acceptable_success_rate:
                    reasons.append(
                        f"history: {decision.selected_printer_id} has "
                        f"{pa.success_rate:.1%} success rate over "
                        f"{pa.total_prints} prints — below acceptable threshold"
                    )
                    citations.append(
                        f"PrintHistory[{decision.selected_printer_id}]")
                    # Suggest excluding this printer
                    suggestions["exclude_printer"] = decision.selected_printer_id

        # 2. Skill-based critique: is there a known failure pattern?
        if self.skills is not None:
            failures = self.skills.lookup(
                kind=SkillKind.FAILURE_PATTERN,
                printer_id=decision.selected_printer_id,
                material=request.material,
                min_confidence=0.5,
            )
            for f in failures:
                reasons.append(
                    f"skill: known failure pattern '{f.name}' "
                    f"(confidence {f.confidence:.2f})"
                )
                citations.append(f"Skill[{f.skill_id[:8]}]")
                suggestions.setdefault("flagged_skills", []).append(
                    {"name": f.name, "body": f.body})

            # 3. Skill-based suggestion: is there a parameter override?
            params = self.skills.lookup(
                kind=SkillKind.PARAMETER_OVERRIDE,
                printer_id=decision.selected_printer_id,
                material=request.material,
                min_confidence=0.5,
            )
            if params:
                suggestions["parameter_overrides"] = [
                    {"name": p.name, "body": p.body} for p in params]

        # Verdict
        if reasons:
            # If we have a concrete alternative suggestion, ask for revision;
            # otherwise approve with caveats noted.
            if "exclude_printer" in suggestions:
                verdict = Verdict.REVISE
                confidence = 0.85
            else:
                verdict = Verdict.APPROVE
                confidence = 0.6
                reasons.append("(approved with caveats)")
        else:
            verdict = Verdict.APPROVE
            confidence = 0.95

        return CritiqueReport(
            verdict=verdict,
            confidence=confidence,
            reasons=reasons,
            suggestions=suggestions,
            citations=citations,
        )


# =============================================================================
# Optimizer
# =============================================================================


@dataclass
class OptimizerAgent:
    """Given a critique that asks for revision, propose a new request."""

    def revise(self, original: DispatchRequest,
                critique: CritiqueReport) -> DispatchRequest:
        if critique.verdict is not Verdict.REVISE:
            return original
        excludes = list(original.excluded_printers)
        if (pid := critique.suggestions.get("exclude_printer")):
            if pid not in excludes:
                excludes.append(pid)
        return dataclasses.replace(
            original, excluded_printers=tuple(excludes),
        )


# =============================================================================
# Executor
# =============================================================================


@dataclass
class ExecutorAgent:
    """Runs the actual print workflow given an approved decision."""

    def execute(self, decision: DispatchDecision,
                 request: DispatchRequest, *,
                 dry_run: bool = True,
                 mesh_path: str | None = None,
                 queue_path: str | None = None,
                 ) -> dict[str, Any]:
        if not decision.has_selection:
            return {"executed": False,
                    "reason": "no eligible printer"}
        if mesh_path is None:
            return {
                "executed": False,
                "reason": "executor requires mesh_path to start the workflow",
            }
        from hermes3d.core.orchestration import (
            build_print_workflow, new_state,
        )
        graph = build_print_workflow()
        state = new_state(initial={
            "mesh_path": mesh_path,
            "material": request.material,
            "strategy": request.strategy.value,
            "preferred_printer_id": decision.selected_printer_id,
            "queue_path": queue_path or "./var/queue.json",
            "dry_run": dry_run,
            "auto_orient_enabled": False,
        })
        final = graph.run(state)
        return {
            "executed": True,
            "workflow_id": final.workflow_id,
            "aborted": final.aborted,
            "abort_reason": final.abort_reason,
            "node_count": len(final.history),
        }


# =============================================================================
# Loop
# =============================================================================


@dataclass
class MultiAgentResult:
    """Outcome of a complete critic/optimizer/executor loop."""

    final_decision: DispatchDecision
    rounds: list[dict[str, Any]] = field(default_factory=list)
    approved: bool = False
    executor_result: dict[str, Any] | None = None


def run_multi_agent(*,
                     request: DispatchRequest,
                     history: PrintHistory | None = None,
                     skills: SkillStore | None = None,
                     max_rounds: int = 3,
                     execute: bool = False,
                     mesh_path: str | None = None,
                     queue_path: str | None = None,
                     dry_run: bool = True,
                     ) -> MultiAgentResult:
    """Critic ↔ Optimizer loop, then optional Executor.

    Returns the final decision plus a structured trace of every round.
    """
    critic = CriticAgent(history=history, skills=skills)
    optimizer = OptimizerAgent()

    current_request = request
    rounds: list[dict[str, Any]] = []
    final_decision: DispatchDecision | None = None
    approved = False

    for r in range(max_rounds):
        decision = dispatch(current_request)
        critique = critic.critique(decision, current_request)
        round_record = {
            "round": r,
            "selected": decision.selected_printer_id,
            "verdict": critique.verdict.value,
            "reasons": critique.reasons,
            "suggestions": critique.suggestions,
        }
        rounds.append(round_record)
        final_decision = decision

        if critique.verdict is Verdict.APPROVE:
            approved = True
            break
        if critique.verdict is Verdict.REJECT:
            approved = False
            break
        # REVISE -> let optimizer propose a new request
        current_request = optimizer.revise(current_request, critique)

    executor_result: dict[str, Any] | None = None
    if approved and execute and final_decision is not None:
        executor = ExecutorAgent()
        executor_result = executor.execute(
            final_decision, current_request,
            dry_run=dry_run, mesh_path=mesh_path, queue_path=queue_path,
        )

    return MultiAgentResult(
        final_decision=final_decision,  # type: ignore[arg-type]
        rounds=rounds,
        approved=approved,
        executor_result=executor_result,
    )


__all__ = [
    "CriticAgent",
    "CritiqueReport",
    "ExecutorAgent",
    "MultiAgentResult",
    "OptimizerAgent",
    "Verdict",
    "run_multi_agent",
]
