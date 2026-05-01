/** 10 agents per `TAB_SPECS.md` §2 roster. */
import type { Agent } from "../../types/agent";

export const MOCK_AGENTS: Agent[] = [
  { id: "agent-planner", role: "Planner", status: "active", task_count: 3, last_activity_utc: "2026-05-01T10:42:18Z", model_provider: "ollama/llama3.1:8b" },
  { id: "agent-implementer", role: "Implementer", status: "active", task_count: 5, last_activity_utc: "2026-05-01T10:42:55Z", model_provider: "ollama/qwen2.5-coder:14b" },
  { id: "agent-blender", role: "BlenderModeler", status: "idle", task_count: 0, last_activity_utc: "2026-05-01T10:38:02Z", model_provider: "blender-mcp/ahujasid" },
  { id: "agent-meshqa", role: "MeshQA", status: "active", task_count: 2, last_activity_utc: "2026-05-01T10:42:11Z", model_provider: "trimesh+rtree" },
  { id: "agent-slicerqa", role: "SlicerQA", status: "idle", task_count: 0, last_activity_utc: "2026-05-01T10:35:47Z", model_provider: "prusa-slicer/2.8.1" },
  { id: "agent-printer", role: "PrinterControl", status: "paused", task_count: 1, last_activity_utc: "2026-05-01T10:30:09Z", model_provider: "moonraker/0.9.0" },
  { id: "agent-repair", role: "Repair", status: "idle", task_count: 0, last_activity_utc: "2026-05-01T09:54:33Z", model_provider: "ollama/llama3.1:8b" },
  { id: "agent-reviewer", role: "Reviewer", status: "active", task_count: 1, last_activity_utc: "2026-05-01T10:41:50Z", model_provider: "ollama/qwen2.5-coder:14b" },
  { id: "agent-releaser", role: "Releaser", status: "idle", task_count: 0, last_activity_utc: "2026-05-01T09:09:06Z", model_provider: "ollama/llama3.1:8b" },
  { id: "agent-auditor", role: "Auditor", status: "active", task_count: 1, last_activity_utc: "2026-05-01T10:42:30Z", model_provider: "ollama/llama3.1:8b" },
];
