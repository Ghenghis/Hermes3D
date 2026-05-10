import type { AgentPersonaId } from "./agent_core";

export type AutonomousSessionStatus = "inactive" | "active" | "paused" | "deactivated";
export type SafetyAgentDecision = "approved" | "vetoed" | "not_required";
export type ActionOutcome = "success" | "failed" | "skipped";
export type DeactivatedBy = "operator" | "safety_agent" | "system";

export interface AutonomousStatus {
  status: AutonomousSessionStatus;
  session_id: string | null;
  activated_at: string | null;
  actions_taken: number;
  escalations: number;
  cadence_seconds: number;
}

export interface AutonomousSession {
  id: string;
  activated_at: string;
  deactivated_at: string | null;
  activated_by: string;
  deactivated_by: DeactivatedBy | null;
  cadence_seconds: number;
  actions_taken: number;
  escalations: number;
}

export interface AutonomousAction {
  id: string;
  session_id: string;
  persona_id: AgentPersonaId;
  action_type: string;
  action_payload: unknown;
  safety_agent_status: SafetyAgentDecision;
  veto_reason: string | null;
  outcome: ActionOutcome;
  error_message: string | null;
  created_at: string;
}

export interface Prerequisite {
  name: string;
  passed: boolean;
  message: string;
}

export interface ActivateResponse {
  prerequisites: Prerequisite[];
  all_passed: boolean;
  session_id: string | null;
}
