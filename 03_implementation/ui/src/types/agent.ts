/**
 * Agent roster per `TAB_SPECS.md` §2 (Planner, Implementer, BlenderModeler,
 * MeshQA, SlicerQA, PrinterControl, Repair, Reviewer, Releaser, Auditor).
 */

export type AgentStatus = "idle" | "active" | "paused" | "error";

export type AgentRole = string;

export interface Agent {
  id: string;
  role: AgentRole;
  status: AgentStatus;
  /** Number of tasks currently assigned. */
  task_count: number;
  /** ISO 8601 UTC timestamp of last activity. */
  last_activity_utc: string;
  /** e.g. "ollama/llama3.1:8b" or "openai/gpt-4o-mini" */
  model_provider: string;
}
