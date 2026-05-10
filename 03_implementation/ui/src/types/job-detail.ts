import type { ApprovalStatus } from "./approval";
import type { JobStatus } from "./job";

export interface JobStep {
  id: string;
  description: string;
  status: "pending" | "running" | "done" | "failed";
  started_at: string | null;
  completed_at: string | null;
  error?: string | null;
}

export interface JobArtifact {
  id: string;
  name: string;
  kind: "model" | "gcode" | "proof" | "log" | "report";
  url: string;
}

export interface JobEvent {
  id: string;
  type: string;
  description: string;
  timestamp: string;
}

export interface JobApprovalSummary {
  id: string;
  approval_type: "MODEL_APPROVAL" | "PRINT_APPROVAL" | "REPAIR_APPROVAL" | string;
  status: ApprovalStatus;
  requested_at: string;
  decided_at: string | null;
}

export interface JobRollbackTarget {
  id: string;
  label: string | null;
  file_path: string | null;
  evidence_type: string | null;
  gate: string | null;
}

export interface JobTransitionState {
  failed_step_id: string | null;
  failed_step: { id: string | null; name: string | null; status: string | null; error: string | null } | null;
  pending_repair_approval_id: string | null;
  approved_repair_approval_id: string | null;
  rollback_targets: JobRollbackTarget[];
  can_request_repair: boolean;
  can_apply_repair: boolean;
  can_retry: boolean;
  can_rollback: boolean;
  blocker: { gate: string; reason: string };
}

export interface JobTransitionResult {
  job_id: string;
  status: string;
  proof_event_id?: string;
  approval_id?: string;
  target_artifact_id?: string;
  created?: boolean;
  repair?: {
    outcome: string;
    strategy_used: string;
    notes: string;
    suggested_action?: Record<string, unknown>;
  };
  detail?: unknown;
}

export interface JobDetail {
  id: string;
  title: string;
  type: string;
  status: JobStatus | "running" | "done" | "waiting_approval";
  dry_run: boolean;
  printer_id: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  steps: JobStep[];
  artifacts: JobArtifact[];
  events: JobEvent[];
  approvals: JobApprovalSummary[];
  transition_state: JobTransitionState | null;
}
