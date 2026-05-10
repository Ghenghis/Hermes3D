/**
 * System snapshot consumed by TopBar + Dashboard's resource panel.
 * Mirrors a subset of `hermes3d.env.types.EnvReport` plus runtime-resource
 * percentages that env-detect doesn't capture (Phase 4 worker telemetry).
 */
import type { Edition } from "./edition";

export interface SystemSnapshot {
  ts_utc: string;
  edition: Edition;
  /** "OK" | "DEGRADED" | "ERROR" — high-level system status. */
  system_status: "OK" | "DEGRADED" | "ERROR";
  /** "Locked" | "Open" — security policy state. */
  security_status: "Locked" | "Open";
  /** GPU detection percent (100 = present + ready). */
  gpu_detected_pct: number;
  gpu_name: string | null;
  vram_used_gb: number | null;
  vram_total_gb: number | null;
  /** Live resource percentages (0-100). */
  cpu_pct: number;
  ram_pct: number;
  gpu_util_pct: number;
  /** Primary disk usage percent (0-100). */
  disk_pct: number;
  /** Recent network throughput sparkline samples (kbps), oldest → newest. */
  network_kbps: number[];
}

/** Per-service URL overrides and global settings, used by the Settings tab. */
export interface AppSettings {
  theme: "midnight" | "alloy" | "ember" | "forest";
  ports: Record<string, number>;
  printerUrls: Record<string, string>;
  serviceUrls: Record<string, string>;
}

/** Readiness check entry for the Autopilot / Dashboard readiness panel. */
export interface ReadinessCheck {
  id: string;
  label: string;
  status: "pass" | "fail" | "pending" | "skipped";
  detail: string | null;
}

export type RuntimeReadinessStatus = "ready" | "partial" | "blocked" | "locked" | string;

export interface RuntimeReadinessRow {
  id: string;
  label: string;
  category: string;
  status: RuntimeReadinessStatus;
  source: string;
  reason: string;
  required_env: string[];
  proof: string;
}

export interface RuntimeReadiness {
  updated_at: string;
  summary: {
    total: number;
    ready: number;
    partial: number;
    blocked: number;
    locked: number;
  };
  runtimes: RuntimeReadinessRow[];
}

export interface RuntimeIdentity {
  status: "fresh" | "stale" | string;
  fresh: boolean;
  ts_utc: string;
  pid: number;
  cwd: string;
  backend_source: string;
  repo_root: string;
  branch: string;
  commit: string;
  dirty: boolean;
  agent_workbench_required_routes: string[];
  missing_agent_workbench_routes: string[];
  route_count: number;
}
