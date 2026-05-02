export interface TaskNode {
  node_id: string;
  tool: string;
  kind: string;
  inputs: Record<string, unknown>;
  retry_budget: number;
  gate_set: string[];
  depends_on: string[];
}

export interface TaskEdge {
  from_node: string;
  to_node: string;
  condition: string;
}

export interface TaskDAG {
  dag_id: string;
  run_id: string;
  nodes: TaskNode[];
  edges: TaskEdge[];
  max_depth: number;
  max_fanout: number;
  metadata: { planner_mode?: "llm" | "template" } & Record<string, unknown>;
}
