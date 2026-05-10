/**
 * Notification consumed by the Dashboard's "Notifications" panel and the
 * TopBar bell badge. Severity drives the colored dot in the bell + chip tone.
 */

export type NotificationSeverity = "info" | "success" | "warn" | "error";
export type NotificationPriority = "low" | "medium" | "high" | "critical";
export type NotificationType =
  | "INFO"
  | "SUCCESS"
  | "WARNING"
  | "ACTION_REQUIRED"
  | "ANOMALY_DETECTED"
  | "PRINT_COMPLETE"
  | "AGENT_BLOCKED"
  | "WHILE_AWAY_ESCALATION";

export interface Notification {
  id: string;
  ts_utc: string;
  severity: NotificationSeverity;
  title: string;
  message: string;
  /** false = unread (drives the bell badge dot). */
  read: boolean;
  type?: NotificationType;
  priority?: NotificationPriority;
  body?: string;
  source_agent_id?: string | null;
  source_tab?: string | null;
  action_url?: string | null;
  action_label?: string | null;
  created_at?: string;
  read_at?: string | null;
  dismissed_at?: string | null;
}

export interface UnreadCount {
  total: number;
  by_tab: Record<string, number>;
}
