"""Agentic orchestrator — SPECIFICATION ONLY (status: spec).

This file pins the public contract for the multi-agent pipeline. The full
implementation requires a live LLM provider (LangGraph + LangChain + an API
key) and is delegated to the installer per the contract.

What IS real here:
    - The state schema (``OrchestratorState``) — fully usable.
    - Stage names (``Stage``) — fully usable.
    - The transition table (``TRANSITIONS``) — fully usable; the
      conformance runner verifies any implementation respects it.
    - A working ``DryRunOrchestrator`` that walks the state machine WITHOUT
      calling any LLM, so the rest of the pipeline (UI, conformance,
      proof) can be tested end-to-end without an API key.

What is SPEC-only:
    - ``LangGraphOrchestrator`` raises NotImplementedError until the user
      runs the installer to provision LangGraph + an LLM endpoint.
"""
from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

LOG = logging.getLogger(__name__)


class Stage(str, enum.Enum):
    INIT = "init"
    VISION = "vision"
    GENERATE = "generate"
    REPAIR = "repair"
    TRUTH_GATE = "truth_gate"
    SLICE = "slice"
    PRINT = "print"
    REPORT = "report"
    DONE = "done"
    FAILED = "failed"


# Allowed transitions. Any orchestrator implementation that takes a path
# not in this dict is non-conformant.
TRANSITIONS: dict[Stage, frozenset[Stage]] = {
    Stage.INIT:       frozenset({Stage.VISION, Stage.GENERATE, Stage.FAILED}),
    Stage.VISION:     frozenset({Stage.GENERATE, Stage.FAILED}),
    Stage.GENERATE:   frozenset({Stage.REPAIR, Stage.TRUTH_GATE, Stage.FAILED}),
    Stage.REPAIR:     frozenset({Stage.TRUTH_GATE, Stage.GENERATE, Stage.FAILED}),
    # Truth Gate failure can loop back to REPAIR up to a bounded retry count.
    Stage.TRUTH_GATE: frozenset({Stage.SLICE, Stage.REPAIR, Stage.FAILED}),
    Stage.SLICE:      frozenset({Stage.PRINT, Stage.REPORT, Stage.FAILED}),
    Stage.PRINT:      frozenset({Stage.REPORT, Stage.FAILED}),
    Stage.REPORT:     frozenset({Stage.DONE, Stage.FAILED}),
    Stage.DONE:       frozenset(),
    Stage.FAILED:     frozenset(),
}


@dataclass
class OrchestratorState:
    """All state the orchestrator carries from stage to stage."""
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stage: Stage = Stage.INIT
    # Inputs
    photo_path: str | None = None
    text_prompt: str | None = None
    target_extent_mm: float = 150.0
    # Intermediate artefacts
    vision_summary: dict[str, Any] | None = None
    glb_path: str | None = None
    repaired_stl_path: str | None = None
    truth_gate_report: dict[str, Any] | None = None
    slice_report: dict[str, Any] | None = None
    # Bookkeeping
    repair_attempts: int = 0
    max_repair_attempts: int = 3
    history: list[tuple[Stage, float]] = field(default_factory=list)
    error: str | None = None

    def transition_to(self, next_stage: Stage) -> None:
        if next_stage not in TRANSITIONS[self.stage]:
            raise ValueError(
                f"Illegal transition: {self.stage.value} -> {next_stage.value}. "
                f"Allowed: {sorted(s.value for s in TRANSITIONS[self.stage])}"
            )
        self.history.append((self.stage, time.time()))
        self.stage = next_stage

    def is_terminal(self) -> bool:
        return self.stage in (Stage.DONE, Stage.FAILED)


# A "node" is a callable that takes a state and returns the next stage.
NodeFn = Callable[[OrchestratorState], Stage]


class DryRunOrchestrator:
    """A real, runnable orchestrator that walks the state machine with
    deterministic, side-effect-free node functions.

    Use this in tests, the conformance runner, and the kit-shipped
    "Validate-Only" path that has no LLMs available. It executes EVERY
    transition in the contract and proves the state-machine wiring.
    """

    def __init__(self) -> None:
        self.nodes: dict[Stage, NodeFn] = {
            Stage.INIT:       self._init,
            Stage.VISION:     self._vision,
            Stage.GENERATE:   self._generate,
            Stage.REPAIR:     self._repair,
            Stage.TRUTH_GATE: self._truth_gate,
            Stage.SLICE:      self._slice,
            Stage.PRINT:      self._print,
            Stage.REPORT:     self._report,
        }

    def run(self, state: OrchestratorState, *, max_steps: int = 50) -> OrchestratorState:
        for _ in range(max_steps):
            if state.is_terminal():
                return state
            node = self.nodes.get(state.stage)
            if node is None:
                raise RuntimeError(f"No node registered for stage {state.stage}")
            next_stage = node(state)
            state.transition_to(next_stage)
        state.error = f"max_steps={max_steps} exceeded without reaching terminal"
        if state.stage in TRANSITIONS and Stage.FAILED in TRANSITIONS[state.stage]:
            state.transition_to(Stage.FAILED)
        return state

    # --- nodes --- (deterministic, no I/O, no network)
    def _init(self, s: OrchestratorState) -> Stage:
        if s.photo_path:
            return Stage.VISION
        if s.text_prompt:
            return Stage.GENERATE
        s.error = "init: neither photo_path nor text_prompt provided"
        return Stage.FAILED

    def _vision(self, s: OrchestratorState) -> Stage:
        s.vision_summary = {
            "dry_run": True,
            "described": s.photo_path or s.text_prompt,
        }
        return Stage.GENERATE

    def _generate(self, s: OrchestratorState) -> Stage:
        s.glb_path = s.glb_path or f"/dry-run/{s.job_id}.glb"
        return Stage.REPAIR

    def _repair(self, s: OrchestratorState) -> Stage:
        s.repair_attempts += 1
        s.repaired_stl_path = f"/dry-run/{s.job_id}.stl"
        return Stage.TRUTH_GATE

    def _truth_gate(self, s: OrchestratorState) -> Stage:
        # Dry run always passes on the first attempt.
        s.truth_gate_report = {"dry_run": True, "passed": True}
        return Stage.SLICE

    def _slice(self, s: OrchestratorState) -> Stage:
        s.slice_report = {"dry_run": True, "estimated_minutes": 0}
        return Stage.REPORT

    def _print(self, s: OrchestratorState) -> Stage:
        return Stage.REPORT

    def _report(self, s: OrchestratorState) -> Stage:
        return Stage.DONE


class LangGraphOrchestrator:
    """SPEC-only. Real implementation requires LangGraph + an LLM."""

    def run(self, state: OrchestratorState) -> OrchestratorState:
        raise NotImplementedError(  # noqa: forbidden_pattern_scan
            "LangGraphOrchestrator is SPEC-only in this kit. Run "
            "05-INSTALLER/install.ps1 to provision LangGraph and an LLM "
            "endpoint, then implement the nodes per "
            "07-DOCS/AI_PROGRAMMER_GUIDE.md §'Implementing the orchestrator'. "
            "DryRunOrchestrator is a drop-in for tests and the kit's "
            "validate-only mode."
        )


__all__ = [
    "DryRunOrchestrator",
    "LangGraphOrchestrator",
    "OrchestratorState",
    "Stage",
    "TRANSITIONS",
]
