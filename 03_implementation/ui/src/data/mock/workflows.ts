/**
 * Active workflows mock.
 *  - 7-stage standard pipeline: Prompt → 3D Gen → Blender MCP → Mesh QA →
 *    3MF → Slicer → Printer (matches the visual contract Dashboard view).
 *  - 12-stage Dimensional Truth pipeline (per addendum) is exposed on the
 *    Workflows tab behind a "Pipeline Detail" toggle (Task 28b).
 */
import type { PipelineStage } from "../../components/pipeline/WorkflowPipeline";
import type { Workflow } from "../../types/workflow";

export const STANDARD_PIPELINE_TEMPLATE: Omit<PipelineStage, "status">[] = [
  { id: "prompt", label: "Prompt" },
  { id: "gen3d", label: "3D Gen" },
  { id: "blender_mcp", label: "Blender MCP" },
  { id: "mesh_qa", label: "Mesh QA" },
  { id: "3mf", label: "3MF" },
  { id: "slicer", label: "Slicer" },
  { id: "printer", label: "Printer" },
];

/** 12-stage Dimensional Truth Engine pipeline — Phase 2 reserves the shape. */
export const DIMENSIONAL_TRUTH_PIPELINE_TEMPLATE: Omit<PipelineStage, "status">[] = [
  { id: "prompt", label: "Prompt" },
  { id: "vision", label: "Vision" },
  { id: "gen3d", label: "3D" },
  { id: "dimensional", label: "Dim. Accuracy" },
  { id: "mesh_repair", label: "Mesh Repair" },
  { id: "printability", label: "Printability" },
  { id: "slice", label: "Slice" },
  { id: "select_printer", label: "Select Printer" },
  { id: "print", label: "Print" },
  { id: "monitor", label: "Monitor" },
  { id: "recover", label: "Recover" },
  { id: "proof", label: "Proof" },
];

export const MOCK_WORKFLOWS: Workflow[] = [
  {
    id: "wf-001",
    name: "frame-bracket-v3 (operator: alice)",
    status: "active",
    active_stage: 5,
    progress: 71,
    started_utc: "2026-05-01T10:20:14Z",
    stages: STANDARD_PIPELINE_TEMPLATE.map((s, i) => ({
      ...s,
      status: i < 5 ? "done" : i === 5 ? "active" : "pending",
      detail: i === 5 ? "98.2%" : undefined,
    })),
  },
  {
    id: "wf-002",
    name: "spindle-housing (operator: bob)",
    status: "active",
    active_stage: 6,
    progress: 92,
    started_utc: "2026-05-01T09:48:07Z",
    stages: STANDARD_PIPELINE_TEMPLATE.map((s, i) => ({
      ...s,
      status: i < 6 ? "done" : i === 6 ? "active" : "pending",
      detail: i === 6 ? "92%" : undefined,
    })),
  },
  {
    id: "wf-003",
    name: "demo-cube (queued)",
    status: "queued",
    active_stage: 0,
    progress: 0,
    started_utc: "2026-05-01T10:42:00Z",
    stages: STANDARD_PIPELINE_TEMPLATE.map((s) => ({ ...s, status: "pending" })),
  },
];
