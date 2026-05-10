export interface PrinterLock {
  printer_id: string;
  locked: boolean;
  reason: string | null;
  locked_by: string | null;
  locked_at: string | null;
}

export interface TestResult {
  printer_id: string;
  ok: boolean;
  message: string;
  latency_ms: number | null;
}

export interface GcodeUploadResult {
  printer_id: string;
  accepted: boolean;
  uploaded: boolean;
  started: boolean;
  status?: string;
  reason?: string;
  detail?: unknown;
  moonraker_url?: string;
  item_path?: string;
  gcode_path?: string;
  gcode_sha256?: string;
  gcode_bytes?: number;
  bounds_passed?: boolean;
  used_fallback_bounds?: boolean;
  klippy_state?: string;
}
