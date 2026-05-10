export type AutopilotCheckStatus = "ready" | "needs_setup";

export interface AutopilotCheck {
  id: string;
  name: string;
  status: AutopilotCheckStatus;
  detail: string | null;
  fix_target: string | null;
}

export interface GuardrailPolicy {
  id: string;
  name: string;
  enabled: boolean;
  severity: "info" | "warn" | "block";
  description: string;
}
