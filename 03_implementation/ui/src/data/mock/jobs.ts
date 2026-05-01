/** Recent jobs mock — 15 entries, status mix per visual contract. */
import type { Job } from "../../types/job";

export const MOCK_JOBS: Job[] = [
  { id: "job-100", name: "frame-bracket-v3.gcode", status: "printing", printer_id: "t1-1", started_utc: "2026-05-01T10:20:14Z", eta_utc: "2026-05-01T11:03:00Z", progress: 47, proof_ref: null },
  { id: "job-099", name: "demo-cube.gcode", status: "printing", printer_id: "sim-21", started_utc: "2026-05-01T10:34:02Z", eta_utc: "2026-05-01T10:51:00Z", progress: 18, proof_ref: null },
  { id: "job-098", name: "spindle-housing.gcode", status: "printing", printer_id: "sim-25", started_utc: "2026-05-01T09:48:07Z", eta_utc: "2026-05-01T10:46:00Z", progress: 92, proof_ref: null },
  { id: "job-097", name: "vase-mode-test.gcode", status: "completed", printer_id: "t1-2", started_utc: "2026-05-01T08:15:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-a3b9" },
  { id: "job-096", name: "calibration-cube.gcode", status: "completed", printer_id: "v400", started_utc: "2026-05-01T07:42:11Z", eta_utc: null, progress: 100, proof_ref: "bundle-c2f1" },
  { id: "job-095", name: "tolerance-fit-A.gcode", status: "completed", printer_id: "t1-1", started_utc: "2026-05-01T06:30:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-d8e2" },
  { id: "job-094", name: "tolerance-fit-B.gcode", status: "failed", printer_id: "sim-23", started_utc: "2026-05-01T05:55:00Z", eta_utc: null, progress: 14, proof_ref: null },
  { id: "job-093", name: "bracket-hex-keyed.gcode", status: "completed", printer_id: "t1-2", started_utc: "2026-05-01T04:10:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-f4a7" },
  { id: "job-092", name: "wall-thickness-probe.gcode", status: "completed", printer_id: "v400", started_utc: "2026-05-01T03:22:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-91bc" },
  { id: "job-091", name: "support-overhang-45.gcode", status: "cancelled", printer_id: "sim-22", started_utc: "2026-04-30T22:48:00Z", eta_utc: null, progress: 8, proof_ref: null },
  { id: "job-090", name: "ironing-pass-validation.gcode", status: "completed", printer_id: "t1-1", started_utc: "2026-04-30T20:15:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-7c3d" },
  { id: "job-089", name: "minimal-stl-fingertip.gcode", status: "completed", printer_id: "t1-2", started_utc: "2026-04-30T18:00:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-2e1f" },
  { id: "job-088", name: "bridge-test-25mm.gcode", status: "completed", printer_id: "v400", started_utc: "2026-04-30T15:30:00Z", eta_utc: null, progress: 100, proof_ref: "bundle-3a8e" },
  { id: "job-087", name: "retraction-tower.gcode", status: "queued", printer_id: null, started_utc: "2026-05-01T10:42:00Z", eta_utc: null, progress: 0, proof_ref: null },
  { id: "job-086", name: "stringing-test.gcode", status: "queued", printer_id: null, started_utc: "2026-05-01T10:42:30Z", eta_utc: null, progress: 0, proof_ref: null },
];
