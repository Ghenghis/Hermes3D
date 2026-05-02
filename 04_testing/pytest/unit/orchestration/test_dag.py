"""Phase 3.2-B pure DAG validation tests."""

from __future__ import annotations

from hermes3d.orchestration import Err, Ok, TaskDAG, TaskEdge, TaskNode


def _node(node_id: str, *, depends_on: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(
        node_id=node_id,
        tool="planner.plan" if node_id == "plan" else "gen3d.generate",
        kind=node_id,
        depends_on=depends_on,
    )


def test_valid_dag_construction():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(
            _node("plan"),
            _node("generate", depends_on=("plan",)),
        ),
        edges=(TaskEdge(from_node="plan", to_node="generate"),),
    )

    result = dag.validate()

    assert isinstance(result, Ok)
    assert result.value is dag


def test_topological_order_respects_edges_and_dependencies():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(
            _node("package", depends_on=("generate",)),
            _node("plan"),
            _node("generate"),
        ),
        edges=(TaskEdge(from_node="plan", to_node="generate"),),
    )

    result = dag.topological_walk()

    assert isinstance(result, Ok)
    assert [node.node_id for node in result.value] == ["plan", "generate", "package"]


def test_cycle_detection_returns_cycle_detected():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(_node("a"), _node("b")),
        edges=(
            TaskEdge(from_node="a", to_node="b"),
            TaskEdge(from_node="b", to_node="a"),
        ),
    )

    result = dag.topological_walk()

    assert isinstance(result, Err)
    assert result.code == "CycleDetected"


def test_depth_cap_allows_twelve_and_rejects_thirteen():
    twelve_nodes = tuple(_node(f"n-{index}") for index in range(12))
    twelve_edges = tuple(
        TaskEdge(from_node=f"n-{index}", to_node=f"n-{index + 1}") for index in range(11)
    )
    valid = TaskDAG(
        dag_id="dag-valid",
        run_id="run-1",
        nodes=twelve_nodes,
        edges=twelve_edges,
    )

    thirteen_nodes = tuple(_node(f"n-{index}") for index in range(13))
    thirteen_edges = tuple(
        TaskEdge(from_node=f"n-{index}", to_node=f"n-{index + 1}") for index in range(12)
    )
    invalid = TaskDAG(
        dag_id="dag-invalid",
        run_id="run-1",
        nodes=thirteen_nodes,
        edges=thirteen_edges,
    )

    assert isinstance(valid.topological_walk(), Ok)

    result = invalid.topological_walk()
    assert isinstance(result, Err)
    assert result.code == "DAGTooDeep"


def test_declared_depth_cap_cannot_exceed_twelve():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(_node("plan"),),
        max_depth=13,
    )

    result = dag.topological_walk()

    assert isinstance(result, Err)
    assert result.code == "DAGTooDeep"


def test_fanout_cap_enforced():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(
            _node("root"),
            _node("child-a"),
            _node("child-b"),
            _node("child-c"),
        ),
        edges=(
            TaskEdge(from_node="root", to_node="child-a"),
            TaskEdge(from_node="root", to_node="child-b"),
            TaskEdge(from_node="root", to_node="child-c"),
        ),
        max_fanout=2,
    )

    result = dag.topological_walk()

    assert isinstance(result, Err)
    assert result.code == "FanoutCapExceeded"


def test_missing_node_reference_rejected():
    dag = TaskDAG(
        dag_id="dag-1",
        run_id="run-1",
        nodes=(_node("generate", depends_on=("plan",)),),
    )

    result = dag.topological_walk()

    assert isinstance(result, Err)
    assert result.code == "MissingNodeReference"
