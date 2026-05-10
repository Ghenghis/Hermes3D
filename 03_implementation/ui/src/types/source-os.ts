import type { ProofBundle } from "./proof";

export type InstallState =
  | "unavailable"
  | "source_available"
  | "downloading"
  | "installing"
  | "installed"
  | "detected"
  | "healthy"
  | "degraded"
  | "failed"
  | "rollback_available";

export type LaunchKind =
  | "catalog_reference"
  | "desktop_app"
  | "desktop_or_cli"
  | "service"
  | "service_reference"
  | "source_reference"
  | "cli_worker"
  | "cli_or_python_worker"
  | "firmware_source"
  | "hardware_reference"
  | "python_worker"
  | "gpu_worker"
  | "web_app"
  | "web_app_reference"
  | "npm_package"
  | "rust_library"
  | "reference"
  | "rust_library_reference"
  | "touch_ui_reference"
  | "unknown";

export interface BridgeTask {
  id: string;
  name: string;
  status: "pending" | "running" | "pass" | "fail" | "skipped";
  last_run_at: string | null;
  last_run_log: string | null;
  duration_ms: number | null;
}

export type DispatchGateStatus = "locked" | "pending" | "approved" | "rejected" | "unknown" | "not_configured";

export interface DispatchGate {
  id: string;
  required_approvals: number;
  current_approver: string | null;
  status: DispatchGateStatus;
}

export interface SourceOSProvider {
  id: string;
  moduleId: string;
  display: string;
  kind: string;
  repo: string | null;
  installCommand: string | null;
  verifyCommands: string[];
  capabilities: string[];
  license: string | null;
  state: string;
  notes: string | null;
}

export interface SourceOSModule {
  id: string;
  display: string;
  priority: string;
  license: string;
  section: string;
  repo: string | null;
  localPath: string | null;
  installState: InstallState;
  installProgress: number;
  detectedVersion: string | null;
  health: "unknown" | "healthy" | "degraded" | "failed";
  launchKind: LaunchKind | null;
  bridgeTasks: BridgeTask[];
  proofs: ProofBundle[];
  dispatchGates: DispatchGate[];
  providers: SourceOSProvider[];
  activeProvider: string | null;
  runtime: SourceModuleRuntime;
}

export interface SourceModuleCliSignal {
  kind: string;
  source: string;
  name: string;
  command: string;
}

export interface SourceModuleCliSurfaceRecord {
  module_id: string;
  display: string;
  section: string;
  launch_kind: string;
  install_state: string;
  agent_execution_tier: string;
  cli_surface_status: string;
  agent_enabled: boolean;
  runtime_status: string;
  verifier: string | null;
  verifier_kind: string | null;
  proof_gate_version: string | null;
  path: string | null;
  source_signals: SourceModuleCliSignal[];
  next_action: string;
}

export interface SourceModuleCliSurfaceAudit {
  status: string;
  count: number;
  proof_source: string | null;
  summary: {
    agent_enabled_cli: number;
    candidate_needs_verifier: number;
    no_local_cli_signal: number;
    by_cli_surface_status?: Record<string, number>;
    agent_enabled_cli_modules?: string[];
    candidate_needs_verifier_modules?: string[];
  };
  records: SourceModuleCliSurfaceRecord[];
}

export interface SourceModuleRuntime {
  status: "ready" | "source_ready" | "setup_required" | "not_installed" | "blocked" | string;
  label: string;
  kind: string | null;
  verifier: string | null;
  path: string | null;
  detected: boolean;
  executed: boolean;
  return_code: number | null;
  capabilities: string[];
  reason: string | null;
  setup_steps: string[];
  proof_source: string | null;
  output_head: string[];
}

export interface SourceModuleUpdateRecord {
  module_id: string;
  display: string | null;
  section: string | null;
  repo: string | null;
  local_path: string | null;
  install_state: string | null;
  detected_version: string | null;
  git_ready: boolean;
  source_update_supported: boolean;
  reason: string | null;
  current: {
    commit: string | null;
    branch: string | null;
    exact_tag: string | null;
    nearest_tag: string | null;
    upstream: string | null;
    remote: string | null;
  };
  dirty: boolean;
  dirty_entries: string[];
  cached_behind_count: number | null;
  latest_backup: SourceModuleBackup | null;
  backup_available: boolean;
  latest_check: SourceModuleUpdateCheck | null;
  deep_checked: boolean;
  update_action: "blocked" | "deep_check_required" | "check_ready" | string;
  safety: string;
}

export interface SourceModuleUpdateReadiness {
  status: string;
  strategy: string;
  section: string | null;
  deep: boolean;
  count: number;
  ready_for_update_check: number;
  blocked: number;
  outdated_cached: number;
  dirty: number;
  records: SourceModuleUpdateRecord[];
}

export interface SourceModuleRuntimeSetupRecord {
  module_id: string;
  display: string | null;
  section: string | null;
  repo: string | null;
  local_path: string | null;
  launch_kind: string | null;
  install_state: string | null;
  runtime_status: string;
  runtime_label: string | null;
  verifier: string | null;
  runner_status: "runtime_ready" | "runner_not_registered" | "source_install_available" | "runtime_repair_required" | "blocked" | string;
  next_action: string;
  source_install_supported: boolean;
  runtime_ready: boolean;
  agent_can_execute_setup_now: boolean;
  agent_setup_gate: string;
  setup_steps: string[];
  reason: string | null;
  proof_source: string | null;
}

export interface SourceModuleRuntimeSetupQueue {
  accepted: boolean;
  status: string;
  section: string | null;
  count: number;
  counts: {
    runtime_ready: number;
    source_ready: number;
    runner_not_registered: number;
    source_install_available: number;
    runtime_repair_required: number;
    blocked: number;
  };
  execution_mode: string;
  agent_gate: string;
  records: SourceModuleRuntimeSetupRecord[];
  proof_event_id: string | null;
}

export interface SourceModuleBackup {
  backup_id: string;
  module_id: string;
  commit: string;
  branch: string | null;
  exact_tag: string | null;
  nearest_tag: string | null;
  dirty: boolean;
  bundle_path: string;
  dirty_zip_path: string | null;
  created_at: string;
}

export interface SourceModuleUpdateCheck {
  module_id: string;
  status: "current" | "outdated" | "blocked" | string;
  current_commit: string | null;
  remote_commit: string | null;
  branch: string | null;
  remote_ref: string | null;
  backup_available: boolean;
  checked_at: string;
  proof_event_id?: string;
}
