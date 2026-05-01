/** Notifications mock — Dashboard panel + TopBar bell badge. */
import type { Notification } from "../../types/notification";

export const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: "notif-001",
    ts_utc: "2026-05-01T10:42:31Z",
    severity: "info",
    title: "T1 #1 progress 47%",
    message: "frame-bracket-v3.gcode — ETA 11:03 UTC",
    read: false,
  },
  {
    id: "notif-002",
    ts_utc: "2026-05-01T10:39:14Z",
    severity: "warn",
    title: "FLSUN S1 unreachable",
    message: "Maintenance flag set; adapter probe failed at 192.168.0.12",
    read: false,
  },
  {
    id: "notif-003",
    ts_utc: "2026-05-01T10:22:11Z",
    severity: "success",
    title: "Proof bundle verified",
    message: "ce50861d… · 11/11 gates pass",
    read: true,
  },
  {
    id: "notif-004",
    ts_utc: "2026-05-01T10:15:00Z",
    severity: "error",
    title: "Print failed (sim-23)",
    message: "tolerance-fit-B.gcode · layer 14 · thermal runaway",
    read: true,
  },
  {
    id: "notif-005",
    ts_utc: "2026-05-01T08:14:31Z",
    severity: "success",
    title: "Phase 1 merged",
    message: "PR #12 → develop · 211 tests · 0 failures",
    read: true,
  },
];
