export type AgentPersonaId =
  | "design"
  | "slicer"
  | "printer"
  | "monitor"
  | "learning"
  | "approvals"
  | "logistics"
  | "safety";

export type AgentStatus = "idle" | "thinking" | "acting" | "error" | "offline";
export type MessageType = "TEXT" | "ACTION_PROPOSAL" | "ANOMALY_ALERT" | "STATUS_UPDATE";

export interface AgentPersona {
  id: AgentPersonaId;
  name: string;
  description: string;
  status: AgentStatus;
  context_tab: string;
  locked: boolean;
}

export interface ActionProposal {
  id: string;
  persona_id: AgentPersonaId;
  title: string;
  description: string;
  endpoint: string;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  payload: Record<string, unknown>;
  risk_level: "low" | "medium" | "high" | "critical";
  status: "pending" | "confirmed" | "denied" | "vetoed";
}

export interface ChatMessage {
  id: string;
  persona_id: AgentPersonaId | null;
  role: "user" | "agent" | "system";
  type: MessageType;
  content: string;
  action: ActionProposal | null;
  created_at: string;
}

export interface AgentConfig {
  model_name: string;
  api_base_url: string;
  api_key_configured: boolean;
  temperature: number;
  max_tokens: number;
  safety_filter_enabled: boolean;
  active_personas: AgentPersonaId[];
  notification_email: string | null;
}
