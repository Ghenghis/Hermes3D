"""LangGraph-style orchestration brain.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §30 (Orchestration Brain)

Composes the existing agents into a single, replayable, stateful
workflow graph. Each node is a function ``state -> state`` that mutates
a typed ``WorkflowState`` blob; edges declare which node runs next.
Checkpoints are persisted between nodes so a workflow can be paused,
inspected, and resumed.

Design notes:
  - Pure-Python — no LangGraph/LangChain dependency. Their full library
    is fine but heavy; for our use case (linear pipeline with branches +
    persistence) a 200-line state machine is sufficient and matches the
    user's "Docker-first, local-first" preference.
  - Each node is idempotent and resumable. If the workflow crashes
    between two nodes, the same input rebuilt from the checkpoint
    produces the same output.
  - The graph is declarative: nodes register an `expected_inputs` set,
    and the runner refuses to run a node when prereqs are missing.

Built-in graph: PrintWorkflow
    enqueue -> validate -> repair_if_needed -> auto_orient -> dispatch
       -> preflight -> slice -> analyze_gcode -> upload -> start
       -> monitor -> record_history
"""
from __future__ import annotations

import dataclasses
import enum
import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


log = logging.getLogger(__name__)


class NodeOutcome(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"     # prerequisites missing — non-fatal
    RETRY = "retry"   # transient error — runner re-attempts


@dataclass
class NodeResult:
    """Outcome of a single node execution."""

    node_name: str
    outcome: NodeOutcome
    started_unix: float
    ended_unix: float
    state_patch: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.ended_unix - self.started_unix)


@dataclass
class WorkflowState:
    """Mutable state passed through every node.

    Treat it like a Python dict — nodes write fields they're responsible
    for. The runner persists the full state after every node.
    """

    workflow_id: str
    created_unix: float
    data: dict[str, Any] = field(default_factory=dict)
    history: list[NodeResult] = field(default_factory=list)
    aborted: bool = False
    abort_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "created_unix": self.created_unix,
            "data": self.data,
            "history": [
                {
                    **dataclasses.asdict(h),
                    "outcome": h.outcome.value,
                }
                for h in self.history
            ],
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "WorkflowState":
        s = cls(
            workflow_id=d["workflow_id"],
            created_unix=d["created_unix"],
            data=dict(d.get("data", {})),
            aborted=bool(d.get("aborted", False)),
            abort_reason=d.get("abort_reason"),
        )
        for h in d.get("history", []):
            s.history.append(NodeResult(
                node_name=h["node_name"],
                outcome=NodeOutcome(h["outcome"]),
                started_unix=h["started_unix"],
                ended_unix=h["ended_unix"],
                state_patch=h.get("state_patch", {}),
                error=h.get("error"),
                notes=list(h.get("notes", [])),
            ))
        return s


# =============================================================================
# Node descriptor
# =============================================================================


NodeFn = Callable[[WorkflowState], NodeResult]


@dataclass(frozen=True)
class GraphNode:
    name: str
    fn: NodeFn
    expected_inputs: tuple[str, ...] = ()
    description: str = ""
    optional: bool = False    # if True, SKIP doesn't abort the workflow

    def can_run(self, state: WorkflowState) -> tuple[bool, str | None]:
        missing = [k for k in self.expected_inputs if k not in state.data]
        if missing:
            return False, f"missing inputs: {missing}"
        return True, None


# =============================================================================
# Graph runner
# =============================================================================


class WorkflowGraph:
    """A linear graph with optional skips. Branches are encoded by nodes
    that conditionally write to ``state.data['next_node']`` (see
    :meth:`run`)."""

    def __init__(self, name: str, *, checkpoint_dir: Path | str | None = None,
                 ) -> None:
        self.name = name
        self._nodes: list[GraphNode] = []
        self._by_name: dict[str, GraphNode] = {}
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None

    def add_node(self, node: GraphNode) -> "WorkflowGraph":
        if node.name in self._by_name:
            raise ValueError(f"duplicate node: {node.name}")
        self._nodes.append(node)
        self._by_name[node.name] = node
        return self

    @property
    def node_names(self) -> tuple[str, ...]:
        return tuple(n.name for n in self._nodes)

    # ---- Persistence -------------------------------------------------------

    def _checkpoint_path(self, workflow_id: str) -> Path | None:
        if self.checkpoint_dir is None:
            return None
        return self.checkpoint_dir / f"{workflow_id}.json"

    def _save_checkpoint(self, state: WorkflowState) -> None:
        path = self._checkpoint_path(state.workflow_id)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True),
                        encoding="utf-8")
        tmp.replace(path)

    def load_checkpoint(self, workflow_id: str) -> WorkflowState | None:
        path = self._checkpoint_path(workflow_id)
        if path is None or not path.exists():
            return None
        return WorkflowState.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )

    # ---- Execution ---------------------------------------------------------

    def run(self, state: WorkflowState, *,
             stop_after: str | None = None,
             max_retries_per_node: int = 1,
             ) -> WorkflowState:
        """Run nodes top to bottom. Honour aborts and conditional branches.

        A node may write ``state.data['next_node']`` to jump; otherwise
        nodes execute in declaration order.
        """
        # Determine which nodes have already run from the history
        completed = {h.node_name for h in state.history
                     if h.outcome is NodeOutcome.PASS}

        idx = 0
        while idx < len(self._nodes):
            if state.aborted:
                log.info("workflow %s aborted: %s",
                          state.workflow_id, state.abort_reason)
                break

            node = self._nodes[idx]
            if node.name in completed:
                idx += 1
                continue

            # Honour explicit jump from prior node
            jump = state.data.pop("next_node", None)
            if jump is not None and jump in self._by_name:
                node = self._by_name[jump]
                idx = self._nodes.index(node)

            ok, why = node.can_run(state)
            if not ok:
                outcome = NodeOutcome.SKIP
                result = NodeResult(
                    node_name=node.name, outcome=outcome,
                    started_unix=time.time(), ended_unix=time.time(),
                    error=why, notes=[f"skipped: {why}"],
                )
                state.history.append(result)
                self._save_checkpoint(state)
                if not node.optional:
                    state.aborted = True
                    state.abort_reason = (
                        f"required node {node.name} skipped: {why}"
                    )
                idx += 1
                continue

            # Run with retries
            attempts = 0
            while True:
                attempts += 1
                started = time.time()
                try:
                    result = node.fn(state)
                except Exception as exc:  # noqa: BLE001
                    result = NodeResult(
                        node_name=node.name, outcome=NodeOutcome.FAIL,
                        started_unix=started, ended_unix=time.time(),
                        error=f"{type(exc).__name__}: {exc}",
                        notes=[traceback.format_exc()[-1000:]],
                    )
                if (result.outcome is NodeOutcome.RETRY
                        and attempts <= max_retries_per_node):
                    log.info("retrying node %s (attempt %d)",
                              node.name, attempts + 1)
                    continue
                break

            # Apply state patch
            if result.state_patch:
                state.data.update(result.state_patch)
            state.history.append(result)
            self._save_checkpoint(state)

            if result.outcome is NodeOutcome.FAIL:
                state.aborted = True
                state.abort_reason = (
                    f"node {node.name} failed: {result.error}"
                )

            if stop_after is not None and node.name == stop_after:
                break

            idx += 1

        return state


def new_workflow_id() -> str:
    return f"wf-{uuid.uuid4().hex[:12]}"


def new_state(workflow_id: str | None = None,
               initial: dict[str, Any] | None = None) -> WorkflowState:
    return WorkflowState(
        workflow_id=workflow_id or new_workflow_id(),
        created_unix=time.time(),
        data=dict(initial or {}),
    )


__all__ = [
    "GraphNode",
    "NodeFn",
    "NodeOutcome",
    "NodeResult",
    "WorkflowGraph",
    "WorkflowState",
    "new_state",
    "new_workflow_id",
]
