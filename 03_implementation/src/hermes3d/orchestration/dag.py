"""Pure DAG primitives for Phase 3.2 planner previews."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Mapping

from .types import Err, Ok, Result

MAX_DAG_DEPTH = 12
DEFAULT_FANOUT_CAP = 4
MAX_RETRY_BUDGET = 3


@dataclass(frozen=True)
class TaskNode:
    node_id: str
    tool: str
    kind: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    retry_budget: int = 0
    gate_set: frozenset[str] = field(default_factory=frozenset)
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "gate_set", frozenset(self.gate_set))
        object.__setattr__(self, "depends_on", tuple(self.depends_on))


@dataclass(frozen=True)
class TaskEdge:
    from_node: str
    to_node: str
    condition: str = "success"


@dataclass(frozen=True)
class TaskDAG:
    dag_id: str
    run_id: str
    nodes: tuple[TaskNode, ...]
    edges: tuple[TaskEdge, ...] = ()
    max_depth: int = MAX_DAG_DEPTH
    max_fanout: int = DEFAULT_FANOUT_CAP
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))

    def validate(self) -> Result["TaskDAG"]:
        return validate_dag(self)

    def topological_walk(self) -> Result[tuple[TaskNode, ...]]:
        return topological_walk(self)


def validate_dag(dag: TaskDAG) -> Result[TaskDAG]:
    walk = topological_walk(dag)
    if isinstance(walk, Err):
        return walk
    return Ok(dag, "dag validated")


def topological_walk(dag: TaskDAG) -> Result[tuple[TaskNode, ...]]:
    if dag.max_depth > MAX_DAG_DEPTH:
        return Err("DAGTooDeep", "DAG max_depth cannot exceed 12")
    if dag.max_depth < 1:
        return Err("InvalidDepthCap", "DAG max_depth must be at least 1")
    if dag.max_fanout < 1:
        return Err("InvalidFanoutCap", "DAG max_fanout must be at least 1")

    nodes_by_id = {node.node_id: node for node in dag.nodes}
    if len(nodes_by_id) != len(dag.nodes):
        return Err("DuplicateNode", "DAG node ids must be unique")
    if not nodes_by_id:
        return Err("EmptyDAG", "DAG must contain at least one node")

    for node in dag.nodes:
        if node.retry_budget < 0 or node.retry_budget > MAX_RETRY_BUDGET:
            return Err("InvalidRetryBudget", "node retry_budget is out of bounds")

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in nodes_by_id}
    incoming: dict[str, set[str]] = {node_id: set() for node_id in nodes_by_id}

    for edge in dag.edges:
        missing = [
            node_id
            for node_id in (edge.from_node, edge.to_node)
            if node_id not in nodes_by_id
        ]
        if missing:
            return Err(
                "MissingNodeReference",
                f"edge references missing node(s): {', '.join(sorted(missing))}",
            )
        adjacency[edge.from_node].add(edge.to_node)
        incoming[edge.to_node].add(edge.from_node)

    for node in dag.nodes:
        for dependency in node.depends_on:
            if dependency not in nodes_by_id:
                return Err(
                    "MissingNodeReference",
                    f"node {node.node_id} depends on missing node {dependency}",
                )
            adjacency[dependency].add(node.node_id)
            incoming[node.node_id].add(dependency)

    fanout_errors = [
        node_id for node_id, children in adjacency.items() if len(children) > dag.max_fanout
    ]
    if fanout_errors:
        return Err(
            "FanoutCapExceeded",
            f"node fanout exceeds cap: {', '.join(sorted(fanout_errors))}",
        )

    ready = deque(
        node.node_id for node in dag.nodes if not incoming[node.node_id]
    )
    ordered_ids: list[str] = []
    depth_by_id: dict[str, int] = {node_id: 1 for node_id in ready}
    incoming_remaining = {node_id: set(parents) for node_id, parents in incoming.items()}

    while ready:
        node_id = ready.popleft()
        ordered_ids.append(node_id)

        for child_id in sorted(adjacency[node_id]):
            depth_by_id[child_id] = max(
                depth_by_id.get(child_id, 1),
                depth_by_id[node_id] + 1,
            )
            incoming_remaining[child_id].remove(node_id)
            if not incoming_remaining[child_id]:
                ready.append(child_id)

    if len(ordered_ids) != len(dag.nodes):
        return Err("CycleDetected", "DAG contains a cycle")

    max_observed_depth = max(depth_by_id.values(), default=0)
    if max_observed_depth > dag.max_depth:
        return Err("DAGTooDeep", "DAG exceeds max depth")

    return Ok(tuple(nodes_by_id[node_id] for node_id in ordered_ids), "dag walked")
