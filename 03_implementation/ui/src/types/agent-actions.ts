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
  path_source?: string;
  configured_path?: string | null;
  source_path?: string | null;
  required_env_keys?: string[];
  version: string | null;
  version_status: string;
  write_allowed: boolean;
  blocked_reason: string | null;
  policy: string;
}

export interface CodeSandboxReadiness {
  status: string;
  ready: boolean;
  mode: string;
  docker_executable: string | null;
  docker_version: string | null;
  image_configured: boolean;
  image: string | null;
  network_mode: string;
  workspace_mount: string;
  denied_paths: string[];
  allowed_command_families: string[];
  blocked_reasons: string[];
}

export interface CodeCliRunnerReadiness {
  status: string;
  count: number;
  detected: number;
  runners: CodeCliRunner[];
  sandbox?: CodeSandboxReadiness;
  policy: {
    write_runs_allowed: boolean;
    reason: string;
    allowed_now: string[];
  };
}

export interface CodeCliRunnerPreflightResult {
  status: string;
  accepted: boolean;
  runner: CodeCliRunner;
  mcp_evidence?: unknown;
  next_required_steps?: string[];
}

export interface CodeCliRunnerRunRequest {
  runner_id: string;
  task_id: string;
  title: string;
  files: string[];
  objective: string;
  target_branch?: string;
}

export interface CodeCliRunnerRunResult {
  status: string;
  accepted: boolean;
  runner: CodeCliRunner;
  sandbox: CodeSandboxReadiness;
  files: string[];
  target_branch?: string | null;
  blocked_reasons: string[];
  mcp_evidence?: unknown;
  next_required_steps?: string[];
}

export interface FolderIndexDoc {
  path: string;
  sha256: string;
  size_bytes: number;
}

export interface AgentProviderLane {
  id: string;
  status: string;
  api_key_configured: boolean;
  api_key_source?: string | null;
  accepted_api_key_env?: string[];
  base_url_configured: boolean;
  base_url_source?: string | null;
  model_configured: boolean;
  model_source?: string | null;
  base_url_label: string;
  model: string | null;
  auth_scheme: string;
  chat_path: string;
  live_status: string;
  blocked_reason: string | null;
  last_smoke?: unknown;
}

export interface AgentProgrammingReadiness {
  status: string;
  ready: boolean;
  provider_lanes: AgentProviderLane[];
  blocked_reasons: string[];
  [key: string]: unknown;
}

export interface AgentE2EReadiness {
  status: string;
  ready: boolean;
  summary: string;
  blocked_reasons: string[];
  programming: AgentProgrammingReadiness;
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

export interface ProviderSmokeResult {
  status: string;
  accepted: boolean;
  provider_id: string;
  blocked_reasons?: string[];
  provider?: unknown;
  auth_contract?: unknown;
  mcp_evidence?: unknown;
}

export interface ReviewedPatchApplyRequest {
  proposal_id: string;
  task_id: string;
  review_proof_ids: string[];
  reason?: string;
}

export interface ReviewedPatchApplyResult {
  status: string;
  accepted: boolean;
  proposal_id?: string;
  review_proof_ids?: string[];
  apply?: unknown;
  mcp_evidence?: unknown;
}

export interface CodeGateRunRequest {
  gate_id: string;
  cwd?: string;
}

export interface CodeGateRunResult {
  status: string;
  ok: boolean;
  gate_id: string;
  result?: unknown;
}

export interface GitBranchRequest {
  task_id: string;
  branch_name: string;
  base_ref?: string;
  reason?: string;
}

export interface GitStageRequest {
  task_id: string;
  files: string[];
}

export interface GitCommitRequest {
  task_id: string;
  files: string[];
  message: string;
  proof_ids?: string[];
}

export interface GitPushRequest {
  task_id: string;
  remote?: string;
}

export interface GitPullRequestRequest {
  task_id: string;
  base_ref: string;
  title: string;
  body?: string;
  draft?: boolean;
}

/**
 * W18-A25 — single Hermes Agent code/team/smoke task row returned by
 * ``GET /api/agents/tasks``. The shape matches what the FastAPI route
 * extracts from ``proof_events`` (see _agent_tasks endpoint in
 * ``agents.py``). Every field is plain text — no secrets, no
 * provider response bodies.
 */
export interface AgentTaskEntry {
  task_id: string | null;
  team_id: string | null;
  provider_id: string | null;
  title: string;
  kind: "code_team" | "code_provider_smoke" | "code_action" | string;
  action_id: string;
  status: string;
  event_type: string;
  created_utc: string;
  evidence_id: string;
  source_agent: string | null;
}

export interface AgentTasksProviderSmokeLatest {
  provider_id: string;
  status: string;
  task_id: string | null;
  created_utc: string;
  evidence_id: string;
}

export interface AgentTasksFeed {
  tasks: AgentTaskEntry[];
  active_count: number;
  total_count: number;
  limit: number;
  window_days: number;
  provider_smoke_latest: AgentTasksProviderSmokeLatest[];
  schema_version: string;
}
