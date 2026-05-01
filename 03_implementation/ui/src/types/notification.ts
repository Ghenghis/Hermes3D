/**
 * Notification consumed by the Dashboard's "Notifications" panel and the
 * TopBar bell badge. Severity drives the colored dot in the bell + chip tone.
 */

export type NotificationSeverity = "info" | "success" | "warn" | "error";

export interface Notification {
  id: string;
  ts_utc: string;
  severity: NotificationSeverity;
  title: string;
  message: string;
  /** false = unread (drives the bell badge dot). */
  read: boolean;
}
