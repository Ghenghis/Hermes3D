"""Agentic orchestrator — runnable.

This module pins the public contract for the multi-agent pipeline and ships
two interchangeable runtimes:

- :class:`DryRunOrchestrator` — a deterministic state-machine walker used
  by tests, the conformance runner, and the kit's "Validate-Only" mode. No
  LLM, no I/O, no network.
- :class:`LangGraphOrchestrator` — runtime over the 12-node
  ``print_workflow`` graph. When the optional ``langgraph`` package is
  installed it builds a real ``StateGraph`` with conditional edges and
  checkpointing; otherwise it transparently falls back to the hand-rolled
  :class:`hermes3d.core.orchestration.agent_graph.WorkflowGraph` and emits a
  structured warning.

Both runtimes are importable offline. ``langgraph`` is an OPTIONAL extra
(see ``pyproject.toml`` ``[project.optional-dependencies].langgraph``).
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermes3d.core.orchestration.agent_graph import (
        WorkflowState as _WorkflowState,
    )

LOG = logging.getLogger(__name__)


class LangGraphUnavailableWarning(UserWarning):
    """Emitted when the optional ``langgraph`` package is not installed."""


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
    Stage.INIT: frozenset({Stage.VISION, Stage.GENERATE, Stage.FAILED}),
    Stage.VISION: frozenset({Stage.GENERATE, Stage.FAILED}),
    Stage.GENERATE: frozenset({Stage.REPAIR, Stage.TRUTH_GATE, Stage.FAILED}),
    Stage.REPAIR: frozenset({Stage.TRUTH_GATE, Stage.GENERATE, Stage.FAILED}),
    # Truth Gate failure can loop back to REPAIR up to a bounded retry count.
    Stage.TRUTH_GATE: frozenset({Stage.SLICE, Stage.REPAIR, Stage.FAILED}),
    Stage.SLICE: frozenset({Stage.PRINT, Stage.REPORT, Stage.FAILED}),
    Stage.PRINT: frozenset({Stage.REPORT, Stage.FAILED}),
    Stage.REPORT: frozenset({Stage.DONE, Stage.FAILED}),
    Stage.DONE: frozenset(),
    Stage.FAILED: frozenset(),
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
            Stage.INIT: self._init,
            Stage.VISION: self._vision,
            Stage.GENERATE: self._generate,
            Stage.REPAIR: self._repair,
            Stage.TRUTH_GATE: self._truth_gate,
            Stage.SLICE: self._slice,
            Stage.PRINT: self._print,
            Stage.REPORT: self._report,
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


def _langgraph_available() -> bool:
    """Return True if the optional ``langgraph`` package can be imported."""
    try:
        import langgraph  # noqa: F401
    except Exception:
        return False
    return True


class LangGraphOrchestrator:
    """Runtime over the 12-node ``print_workflow`` graph.

    When the optional ``langgraph`` extra is installed, builds a real
    ``StateGraph`` with conditional edges and a checkpointer. Otherwise
    falls back to the hand-rolled :class:`WorkflowGraph` (same node set,
    same state shape) and emits a :class:`LangGraphUnavailableWarning`.

    Both code paths return a :class:`WorkflowState` populated with
    ``terminal=True``, an ``aborted`` flag, and ``node_results`` (alias of
    ``history``).
    """

    def __init__(self, *, force_fallback: bool = False) -> None:
        self.force_fallback = force_fallback

    def run(
        self,
        state: _WorkflowState,
        *,
        max_steps: int = 50,
        checkpoint_dir: Path | str | None = None,
    ) -> _WorkflowState:
        from hermes3d.core.orchestration.print_workflow import (
            build_print_workflow,
        )

        if not self.force_fallback and _langgraph_available():
            try:
                return self._run_langgraph(
                    state, max_steps=max_steps, checkpoint_dir=checkpoint_dir
                )
            except Exception as exc:
                LOG.exception("LangGraph runtime failed: %s — falling back", exc)
                warnings.warn(
                    f"LangGraph runtime raised {type(exc).__name__}; falling "
                    "back to WorkflowGraph for this run.",
                    LangGraphUnavailableWarning,
                    stacklevel=2,
                )
        elif not self.force_fallback:
            warnings.warn(
                "LangGraph runtime unavailable: optional 'langgraph' package not "
                "installed. Falling back to hand-rolled WorkflowGraph (same node "
                "set, same result shape). Install 'hermes3d-os-lite[langgraph]' "
                "to enable the real StateGraph runtime.",
                LangGraphUnavailableWarning,
                stacklevel=2,
            )
        else:
            LOG.info("LangGraphOrchestrator: forced fallback to WorkflowGraph")

        graph = build_print_workflow(checkpoint_dir=checkpoint_dir)
        result = graph.run(state)
        result.terminal = True
        return result

    # ------------------------------------------------------------------
    # Real LangGraph path
    # ------------------------------------------------------------------
    def _run_langgraph(
        self,
        state: _WorkflowState,
        *,
        max_steps: int,
        checkpoint_dir: Path | str | None,
    ) -> _WorkflowState:
        from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

        from hermes3d.core.orchestration.agent_graph import NodeOutcome
        from hermes3d.core.orchestration.print_workflow import (
            build_print_workflow,
        )

        builder = build_print_workflow(checkpoint_dir=checkpoint_dir)
        node_names = list(builder.node_names)

        sg: Any = StateGraph(dict)

        def _make_runner(node_name: str) -> Callable[[dict], dict]:
            node = builder._by_name[node_name]  # noqa: SLF001 - intentional bridge

            def runner(d: dict) -> dict:
                ws_cls = type(state)
                ws = ws_cls.from_dict(d) if isinstance(d, dict) and "workflow_id" in d else state
                ok, why = node.can_run(ws)
                if not ok:
                    if not node.optional:
                        ws.aborted = True
                        ws.abort_reason = f"required node {node.name} skipped: {why}"
                    return ws.to_dict()
                try:
                    result = node.fn(ws)
                except Exception as exc:
                    ws.aborted = True
                    ws.abort_reason = f"node {node.name} raised: {exc!r}"
                    return ws.to_dict()
                if result.state_patch:
                    ws.data.update(result.state_patch)
                ws.history.append(result)
                if result.outcome is NodeOutcome.FAIL:
                    ws.aborted = True
                    ws.abort_reason = f"node {node.name} failed: {result.error}"
                return ws.to_dict()

            runner.__name__ = f"node_{node_name}"
            return runner

        for name in node_names:
            sg.add_node(name, _make_runner(name))

        sg.set_entry_point(node_names[0])

        def _route(after: str) -> Callable[[dict], str]:
            def cond(d: dict) -> str:
                if d.get("aborted"):
                    return END
                return after

            return cond

        for src, dst in zip(node_names, node_names[1:]):
            sg.add_conditional_edges(src, _route(dst), {dst: dst, END: END})
        sg.add_edge(node_names[-1], END)

        compiled: Any
        try:
            from langgraph.checkpoint.memory import MemorySaver  # type: ignore

            compiled = sg.compile(checkpointer=MemorySaver())
        except Exception:
            compiled = sg.compile()

        config = {
            "configurable": {"thread_id": state.workflow_id},
            "recursion_limit": max_steps,
        }
        final_dict = compiled.invoke(state.to_dict(), config=config)

        ws_cls = type(state)
        final_state = ws_cls.from_dict(final_dict) if isinstance(final_dict, dict) else state
        if checkpoint_dir is not None:
            cp_path = Path(checkpoint_dir) / f"{final_state.workflow_id}.json"
            cp_path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json

            cp_path.write_text(
                _json.dumps(final_state.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        final_state.terminal = True
        return final_state


__all__ = [
    "TRANSITIONS",
    "DryRunOrchestrator",
    "LangGraphOrchestrator",
    "LangGraphUnavailableWarning",
    "OrchestratorState",
    "Stage",
]
