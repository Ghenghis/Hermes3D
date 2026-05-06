import type { AgentPersonaId } from "./agent_core";

export type CameraHealth = "configured" | "locked" | "not_configured" | "reachable" | "unreachable" | "unknown";
export type AnomalyStatus = "active" | "dismissed" | "resolved";
export type AgentWatchMode = "off" | "monitor_agent" | AgentPersonaId;
export type GridLayout = "1x1" | "2x2" | "3x3";

/** Per-camera status returned by GET /api/observe/status */
export interface CameraStatus {
  printer_id: string;
  printer_name: string;
  camera_url: string | null;
  health: CameraHealth;
  http_status: number | null;
  response_ms: number | null;
  /** Estimated frames-per-second derived from MJPEG response time. null when offline. */
  estimated_fps: number | null;
  /** True for S1 (192.168.0.12): camera feed is read-only, no control commands allowed. */
  read_only: boolean;
}

export interface ObserveStatusResponse {
  cameras: CameraStatus[];
  online: number;
  total: number;
}

export interface CameraFeed {
  printer_id: string;
  printer_name: string;
  camera_url: string | null;
  health: CameraHealth;
  stream_url: string;
  snapshot_url: string;
  is_locked: boolean;
  printer_locked: boolean;
  camera_kind: "integrated" | "usb_webcam" | "locked" | "external";
  camera_note: string;
  view_settings: CameraViewSettings;
  plate_clearance: BuildPlateClearance | null;
}

export interface AnomalyReport {
  id: string;
  printer_id: string;
  confidence: number;
  description: string;
  snapshot_id: string | null;
  status: AnomalyStatus;
  reported_at: string;
}

export interface ObserveState {
  gridLayout: GridLayout;
  agentWatchMode: AgentWatchMode;
  feeds: CameraFeed[];
  anomalies: AnomalyReport[];
  evidenceCaptureInProgress: Set<string>;
}

export interface BuildPlateClearance {
  printer_id: string;
  printer_name: string;
  state: "clear" | "needs_clearance" | "locked" | "unknown";
  last_job_filename: string | null;
  source: string;
  reason: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  updated_at: string | null;
  camera_url: string | null;
  printer_locked: boolean;
}

export interface CameraViewSettings {
  rotate_deg: 0 | 90 | 180 | 270;
  mirror_x: boolean;
  mirror_y: boolean;
  zoom: number;
  focus_x: number;
  focus_y: number;
  brightness: number;
  contrast: number;
  saturation: number;
  fit: "cover" | "contain";
  feed_mode: "stream" | "snapshot";
  card_size: "compact" | "standard" | "wide" | "large" | "full";
  review_overlay: "none" | "crosshair" | "grid" | "plate_frame";
}
