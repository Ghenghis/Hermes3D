export type AgentActionStatus = "ready" | "partial" | "blocked" | "in_progress" | string;

export interface AgentActionContract {
  id: string;
  label: string;
  tab: string;
  status: AgentActionStatus;
  kind: string;
  risk: "low" | "medium" | "high" | "critical" | string;
  route: string;
  agent_callable: boolean;
  proof_required: boolean;
  approval_required: boolean;
  rollback_required: boolean;
  summary: string;
  blocked_reason: string | null;
  payload_schema?: {
    required?: string[];
    optional?: Record<string, string>;
    safety?: string;
    allowed_transition?: string[];
    allowed_decision?: string[];
  };
}

export interface AgentActionCatalog {
  status: AgentActionStatus;
  summary: string;
  contract_version: string;
  counts: Record<string, number>;
  total: number;
  ready_now: string[];
  blocked_or_partial: string[];
  contracts: AgentActionContract[];
}

export interface AgentActionRunResult {
  action_id: string;
  accepted: boolean;
  status: string;
  reason?: string;
  proof_event_id?: string;
  contract?: AgentActionContract;
  result?: unknown;
}

export interface CodeCliRunner {
  id: string;
  label: string;
  detected: boolean;
  executable: string | null;
  version: string | null;
  version_status: string;
  write_allowed: boolean;
  blocked_reason: string | null;
  policy: string;
}

export interface CodeCliRunnerReadiness {
  status: string;
  count: number;
  detected: number;
  runners: CodeCliRunner[];
  policy: {
    write_runs_allowed: boolean;
    reason: string;
    allowed_now: string[];
  };
}

export interface FolderIndexDoc {
  path: string;
  sha256: string;
  size_bytes: number;
}

export interface AgentE2EReadiness {
  status: string;
  ready: boolean;
  summary: string;
  blocked_reasons: string[];
  programming?: unknown;
  provider_teams?: unknown;
  folder_index: {
    status: string;
    loaded: FolderIndexDoc[];
    missing: string[];
    target_roots: string[];
    provider_context_files?: string[];
    required: string[];
  };
  cli_runners: CodeCliRunnerReadiness;
  next_required_steps: string[];
}

export interface AgentE2EJobRequest {
  task_id: string;
  title: string;
  files: string[];
  objective: string;
  target_branch?: string;
  role_chain?: string[];
  cli_worker?: string;
  release_on_finish?: boolean;
}

export interface AgentE2EJobResult {
  status: string;
  accepted: boolean;
  task_id?: string;
  title?: string;
  files?: string[];
  blocked_reasons?: string[];
  mcp_evidence?: unknown;
  folder_index?: unknown;
  coding_pass?: unknown;
  review_pass?: unknown;
  next_required_steps?: string[];
}
