"""LangGraph adapter.

Hermes3D-OS ships its own ``WorkflowGraph`` (deliberate: deterministic, atomic
checkpointing, no extra deps). But several power users want to run the same
print pipeline inside LangGraph for inter-op with their existing agent stacks.

This adapter exports a hermes3d ``WorkflowGraph`` as a LangGraph-compatible
``StateGraph`` blueprint **as Python source** (not a live object) so the user
can paste it into their LangGraph project. We don't import ``langgraph`` at
runtime — the local fleet remains zero-extra-dep.

The exporter accepts any ``WorkflowGraph`` and produces a ``str`` of Python.
"""

from __future__ import annotations

import textwrap

from hermes3d.core.orchestration.agent_graph import WorkflowGraph


def to_langgraph_source(graph: WorkflowGraph, *, function_name: str = "build_pipeline") -> str:
    """Render a ``WorkflowGraph`` as a self-contained LangGraph blueprint.

    The output is a Python module string the user can drop into their
    LangGraph environment. Each node becomes a callable that delegates to the
    ``hermes3d`` agentic functions at runtime, preserving exact behaviour
    parity. The hermes3d ``WorkflowGraph`` is linear; this adapter chains the
    LangGraph nodes in the same order and wires the last one to ``END``.
    """
    node_names = list(graph.node_names)
    if not node_names:
        raise ValueError("graph has no nodes to export")

    # Build callable wrappers. Each wrapper looks the node up by name from the
    # original print_workflow and re-runs its function with the LangGraph state.
    wrappers: list[str] = []
    for name in node_names:
        wrappers.append(_render_wrapper(name))

    add_node_lines = [
        f'    workflow.add_node("{name}", node_{_safe_id(name)})' for name in node_names
    ]

    # Linear edge wiring.
    edge_lines: list[str] = []
    for src, dst in zip(node_names, node_names[1:]):
        edge_lines.append(f'    workflow.add_edge("{src}", "{dst}")')
    edge_lines.append(f'    workflow.add_edge("{node_names[-1]}", END)')

    body = textwrap.dedent(
        f'''
        """Auto-generated LangGraph adapter for hermes3d WorkflowGraph "{graph.name}".

        Regenerate via:

            from hermes3d.core.orchestration.langgraph_adapter import to_langgraph_source
            from hermes3d.core.orchestration.print_workflow import build_print_workflow
            print(to_langgraph_source(build_print_workflow()))
        """
        from typing import Any, TypedDict

        from langgraph.graph import StateGraph, END  # requires ``pip install langgraph``

        from hermes3d.core.orchestration.agent_graph import WorkflowState


        class HermesState(TypedDict, total=False):
            workflow_id: str
            data: dict[str, Any]
            errors: list[str]


        '''
    ).strip()
    body += "\n\n\n"
    body += "\n\n\n".join(wrappers)
    body += "\n\n\n"
    body += textwrap.dedent(
        f"""
        def {function_name}() -> StateGraph:
            workflow = StateGraph(HermesState)
        """
    ).strip()
    body += "\n"
    body += "\n".join(add_node_lines)
    body += "\n"
    body += f'    workflow.set_entry_point("{node_names[0]}")\n'
    body += "\n".join(edge_lines)
    body += "\n    return workflow\n"
    return body


def _safe_id(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_").lower()


def _render_wrapper(name: str) -> str:
    safe = _safe_id(name)
    return textwrap.dedent(
        f'''
        def node_{safe}(state: HermesState) -> dict[str, Any]:
            """Wrapper that delegates to hermes3d node {name!r}."""
            from hermes3d.core.orchestration.print_workflow import build_print_workflow
            graph = build_print_workflow()
            node = graph._by_name[{name!r}]  # noqa: SLF001 - intentional bridge
            ws = WorkflowState(
                workflow_id=state.get("workflow_id", "langgraph"),
                data=dict(state.get("data") or {{}}),
                errors=list(state.get("errors") or []),
            )
            result = node.fn(ws)
            ws.data.update(result.outputs or {{}})
            return {{
                "workflow_id": ws.workflow_id,
                "data": dict(ws.data),
                "errors": list(ws.errors),
            }}
        '''
    ).strip()


def export_to_file(
    graph: WorkflowGraph, target_path: str, *, function_name: str = "build_pipeline"
) -> str:
    """Write the rendered source to disk and return the path."""
    src = to_langgraph_source(graph, function_name=function_name)
    with open(target_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    return target_path


__all__ = ["export_to_file", "to_langgraph_source"]
