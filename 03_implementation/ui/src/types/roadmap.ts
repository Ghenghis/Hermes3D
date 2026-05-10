export type RoadmapState = "not_started" | "in_progress" | "done";

export interface RoadmapItem {
  number: number;
  description: string;
  complete: boolean;
  completedAt: string | null;
  triggeredByEvent: string | null;
  state?: RoadmapState;
}

export interface RoadmapTabCompletionItem {
  tab: string;
  label: string;
  state: RoadmapState;
  summary: string;
}

export interface RoadmapWorkPackage {
  id: string;
  title: string;
  tabs: string[];
  state: "next" | "active" | "done";
  summary: string;
  acceptance: string[];
}

export interface RoadmapReference {
  label: string;
  url: string;
}

export interface SourceRuntimeActionPlan {
  path: string;
  exists: boolean;
  generated_at_utc: string | null;
  source_backed_apps: number;
  runtime_ready: number;
  runner_gaps: number;
  verified_agent_cli: number;
  cli_candidates: number;
  rule: string;
}

export interface AgentOperatorContract {
  state: string;
  summary: string;
  ready_now: string[];
  missing: string[];
  blocked_now: string[];
  acceptance: string[];
}

export interface RoadmapTabCompletion {
  updated_at: string;
  roadmap_path: string;
  source_runtime_action_plan?: SourceRuntimeActionPlan;
  agent_operator_contract?: AgentOperatorContract;
  contract: string[];
  tabs: RoadmapTabCompletionItem[];
  next_packages: RoadmapWorkPackage[];
  references: RoadmapReference[];
}
