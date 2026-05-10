export type ToolchainStageStatus =
  | "ready"
  | "pending"
  | "active"
  | "blocked"
  | "detected"
  | "not_installed"
  | "not_run"
  | "pass"
  | "fail"
  | "warning"
  | "error";

export interface ToolchainEvidence {
  id: string;
  name: string;
  status: ToolchainStageStatus | string;
  detail?: string | null;
  source?: string | null;
  capabilities?: string[];
  path?: string | null;
  repo_url?: string | null;
  module_id?: string | null;
  proof_path?: string | null;
  detected?: boolean;
  executed?: boolean;
  return_code?: number | null;
  priority?: string | null;
  license?: string | null;
  launch_kind?: string | null;
}

export interface ToolchainStage {
  id: string;
  name?: string;
  label?: string;
  status: ToolchainStageStatus | string;
  detail?: string | null;
  source?: string | null;
  capabilities?: string[];
  path?: string | null;
  repo_url?: string | null;
  module_id?: string | null;
  proof_path?: string | null;
}

export interface ToolchainStatus {
  overall: "ready" | "degraded" | "blocked";
  execution_ready?: boolean;
  blockers?: string[];
  supported_templates?: Array<{
    id: string;
    name: string;
    executor?: string;
    outputs?: string[];
    parameters?: string[];
  }>;
  stages: ToolchainStage[];
  tools?: ToolchainEvidence[];
  sources?: ToolchainEvidence[];
  proof_sources?: Record<string, string | null>;
  updated_at: string;
}
