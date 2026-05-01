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
  /** Primary disk usage percent (0-100). Phase-2 mock; Phase 4 wires real telemetry. */
  disk_pct: number;
  /** Recent network throughput sparkline samples (kbps), oldest → newest. */
  network_kbps: number[];
}
