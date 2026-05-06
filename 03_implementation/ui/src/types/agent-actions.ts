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
