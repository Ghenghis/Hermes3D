export interface LearningConfig {
  enabled: boolean;
  active: boolean;
  mode: "idle-research-reporting" | "disabled" | "active";
  idle_minutes: number;
  reports_directory: string;
  next_topic: string | null;
  runner_status?: "ready" | "not_configured" | "unreachable" | string;
  reason?: string | null;
}

export interface ReportMeta {
  id: string;
  filename: string;
  title: string;
  created_at: string;
  size_bytes: number;
  preview_url: string;
}

export interface LearningMode {
  mode: "idle-research-reporting" | "disabled" | "active";
  cadence: "idle" | "operator-triggered";
  reportsDirectory: string;
  nextTopic: string | null;
  agents: string[];
  safetyScope: string;
  scope: string;
}

export interface ResearchReport {
  id: string;
  filename: string;
  title: string;
  createdAt: string;
  sizeBytes: number;
  previewUrl: string;
}

export type IdleCandidateStatus = "queued" | "blocked" | "ready_for_review" | "approved" | "rejected" | "completed";

export interface IdleWorkbenchBlocker {
  type: string;
  id: string | null;
  label: string;
  status: string;
  reason: string;
}

export interface IdleWorkbenchCandidate {
  id: string;
  title: string;
  kind: string;
  agent_id: string;
  status: IdleCandidateStatus;
  risk_level: string;
  summary: string;
  source: string;
  source_url: string | null;
  target_tab: string | null;
  target_files: string[];
  branch_ref: string | null;
  gate_status: Record<string, unknown>;
  proof_event_ids: string[];
  approval_id: string | null;
  blocked_reason: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface IdleWorkbenchState {
  status: string;
  review_policy: string;
  blockers: IdleWorkbenchBlocker[];
  candidates: IdleWorkbenchCandidate[];
  automation?: IdleAutomationReadiness;
  daily_prompt: {
    question: string;
    last_candidate_at: string | null;
    suggested_kinds: string[];
  };
}

export interface IdleAutomationCapability {
  kind: string;
  label: string;
  agent_id: string;
  queue_enabled: boolean;
  execution_status: "ready" | "blocked" | string;
  missing: string[];
  proof_required: boolean;
  safety_scope: string;
}

export interface IdleAutomationReadiness {
  runner_status: "ready" | "not_configured" | string;
  runner_reason: string | null;
  agent_runtime_status: "ready" | "not_configured" | string;
  agent_runtime_reason: string | null;
  capabilities: IdleAutomationCapability[];
}

export interface IdleCandidateCreateRequest {
  title: string;
  summary: string;
  kind: string;
  agent_id?: string;
  risk_level?: string;
  source?: string;
  source_url?: string | null;
  target_tab?: string | null;
  target_files?: string[];
  branch_ref?: string | null;
  created_by?: string;
}

export interface IdleCandidateMutationResult {
  accepted: boolean;
  status: string;
  reason?: string | null;
  decision?: string;
  approval_id?: string | null;
  proof_event_id?: string | null;
  candidate?: IdleWorkbenchCandidate | null;
  blockers?: IdleWorkbenchBlocker[];
  report?: {
    filename: string;
    path: string;
    size_bytes: number;
    sha256: string;
  } | null;
  artifact_id?: string | null;
}
