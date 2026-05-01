/** System logs mock — last ~12 entries for the Dashboard "System Logs (Latest)" card. */
import type { LogEntry } from "../../types/log";

export const MOCK_LOGS: LogEntry[] = [
  { ts_utc: "2026-05-01T10:42:31Z", level: "info",  source: "moonraker", message: "T1 #1 progress 47% on frame-bracket-v3.gcode" },
  { ts_utc: "2026-05-01T10:42:18Z", level: "info",  source: "agent.planner", message: "Plan refined for spindle-housing variant B" },
  { ts_utc: "2026-05-01T10:41:50Z", level: "info",  source: "agent.reviewer", message: "PR #12 review approved (5 gates green)" },
  { ts_utc: "2026-05-01T10:39:14Z", level: "warn",  source: "fleet", message: "FLSUN S1 192.168.0.12 unreachable — maintenance flag set" },
  { ts_utc: "2026-05-01T10:38:02Z", level: "info",  source: "blender_mcp", message: "Provider ahujasid idle; tool capability OK" },
  { ts_utc: "2026-05-01T10:35:47Z", level: "info",  source: "slicer.prusa", message: "Profile 'FLSUN-T1-PLA' loaded for next slice" },
  { ts_utc: "2026-05-01T10:34:02Z", level: "info",  source: "moonraker", message: "sim-21 progress 18% on demo-cube.gcode" },
  { ts_utc: "2026-05-01T10:30:09Z", level: "warn",  source: "agent.printer", message: "PrinterControl paused — awaiting policy gate confirm" },
  { ts_utc: "2026-05-01T10:22:11Z", level: "info",  source: "proof", message: "bundle ce50861d… verified · 11/11 gates pass" },
  { ts_utc: "2026-05-01T10:20:14Z", level: "info",  source: "moonraker", message: "T1 #1 print started · frame-bracket-v3.gcode (eta 11:03)" },
  { ts_utc: "2026-05-01T10:15:00Z", level: "error", source: "fleet.sim-23", message: "Print failed — tolerance-fit-B.gcode (layer 14, thermal runaway sim)" },
  { ts_utc: "2026-05-01T10:00:00Z", level: "info",  source: "system", message: "GPU detected: RTX 3090 Ti · 24 GB VRAM · driver 591.86" },
];
