import type { TaskDAG } from "../../types/dag";

export const MOCK_PLAN_DAG: TaskDAG = {
  dag_id: "mock-calibration-cube-dag",
  run_id: "mock-plan-preview",
  max_depth: 12,
  max_fanout: 4,
  metadata: {
    planner: "deterministic-template",
    fixture_prompt: "calibration cube",
  },
  nodes: [
    {
      node_id: "gen3d-simulated",
      tool: "gen3d.generate",
      kind: "gen3d.fixture.calibration_cube",
      inputs: {
        prompt: "calibration cube",
        seed: 3201,
      },
      retry_budget: 0,
      gate_set: ["phase3.2.simulated-only"],
      depends_on: [],
    },
  ],
  edges: [],
};
