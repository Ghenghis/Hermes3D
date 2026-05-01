/** System snapshot mock — anchored to the canonical reference host. */
import type { SystemSnapshot } from "../../types/system";

export const MOCK_SYSTEM_SNAPSHOT: SystemSnapshot = {
  ts_utc: "2026-05-01T10:42:30Z",
  edition: "desktop_gpu_worker",
  system_status: "OK",
  security_status: "Locked",
  gpu_detected_pct: 100,
  gpu_name: "NVIDIA GeForce RTX 3090 Ti",
  vram_used_gb: 5.9,
  vram_total_gb: 24.0,
  cpu_pct: 23,
  ram_pct: 41,
  gpu_util_pct: 56,
};
