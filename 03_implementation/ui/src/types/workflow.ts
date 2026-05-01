/**
 * Workflow types — stage status mirrors the kit's Phase-3 workflow result
 * envelope. Two stage shapes:
 *   - Standard 7-stage: Prompt → 3D Gen → Blender MCP → Mesh QA → 3MF → Slicer → Printer
 *   - Dimensional Truth 12-stage: Prompt → Vision → 3D → Dimensional Accuracy →
 *     Mesh Repair → Printability → Slice → Select Printer → Print → Monitor →
 *     Recover → Proof  (per Dimensional Truth Engine addendum)
 */
import type { PipelineStage } from "../components/pipeline/WorkflowPipeline";

export type WorkflowStatus = "active" | "completed" | "failed" | "queued";

export interface Workflow {
  id: string;
  name: string;
  status: WorkflowStatus;
  stages: PipelineStage[];
  /** Active stage index (0-based) for the visualization. */
  active_stage: number;
  /** Overall percent complete (0-100). */
  progress: number;
  started_utc: string;
}
