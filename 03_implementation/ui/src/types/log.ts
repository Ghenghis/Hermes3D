/**
 * Unified log entry consumed by the Dashboard's "System Logs (Latest)" panel
 * and (later) the dedicated System Logs tab. Mirrors a subset of the kit's
 * Phase-3 evidence-log envelope — Phase 2 ships mock entries only.
 */

export type LogLevel = "info" | "warn" | "error" | "debug";

export interface LogEntry {
  ts_utc: string;
  level: LogLevel;
  source: string;
  message: string;
}
