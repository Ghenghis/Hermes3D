/**
 * Unified log entry consumed by the Dashboard's "System Logs (Latest)" panel
 * and (later) the dedicated System Logs tab. Mirrors a subset of the kit's
 * evidence-log envelope.
 */

export type LogLevel = "info" | "warn" | "error" | "debug";

export interface LogEntry {
  ts_utc: string;
  level: LogLevel;
  source: string;
  message: string;
}
