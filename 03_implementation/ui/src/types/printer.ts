/** TypeScript mirror of the printer-row shape rendered in PrinterFleet + Dashboard. */

export type PrinterStatus =
  | "online"
  | "active"
  | "printing"
  | "paused"
  | "maintenance"
  | "offline"
  | "error";

export type PrinterAdapter = "moonraker" | "octoprint" | "printrun" | "manual";
export type PrinterDataSource = "live" | "degraded" | "error" | "policy" | "config";

export interface PrinterSourceRefs {
  official_wiki_url?: string;
  official_setup_topics?: string[];
  flsun_slicer_install?: string;
  source_profile_ini?: string;
  source_profile_ini_detected?: boolean;
  profiles_detected?: Record<string, boolean>;
  installed_profiles?: Record<string, string>;
  safety?: string;
}

export interface Printer {
  id: string;
  name: string;
  model: "FLSUN T1" | "FLSUN S1" | "FLSUN V400" | "Generic";
  ip: string | null;
  status: PrinterStatus;
  adapter: PrinterAdapter;
  data_source: PrinterDataSource;
  /** Hot-end temperature in °C, or null if offline. */
  temp_hot: number | null;
  /** Bed temperature in °C, or null if offline. */
  temp_bed: number | null;
  /** 0-100, or null if not printing. */
  progress: number | null;
  current_job: string | null;
  maintenance_flag: boolean;
  camera_url: string | null;
  moonraker_url?: string | null;
  safety_policy?: "locked" | "read_only" | "write_enabled" | string;
  write_enabled?: boolean;
  onboarded?: boolean;
  status_source?: string;
  source_refs: PrinterSourceRefs;
}

export interface PrinterOnboardRequest {
  id?: string;
  name: string;
  model: Printer["model"];
  moonraker_url: string;
  camera_url?: string;
  actor?: string;
  write_enabled?: boolean;
}

export interface PrinterOnboardProbe {
  name: string;
  ok: boolean;
  required?: boolean;
  http_status?: number | null;
  reason?: string;
  klippy_connected?: boolean;
  klippy_state?: string;
  moonraker_version?: string;
  api_version?: string;
  print_state?: string;
  filename?: string | null;
  progress?: number;
}

export interface PrinterOnboardResult {
  created: boolean;
  printer: Printer | null;
  probe_summary: {
    ok?: boolean;
    required_probes?: string[];
    probes?: PrinterOnboardProbe[];
  } | null;
  proof_event_id?: string | null;
  status?: string;
  reason?: string;
  failed_probe?: string | null;
  detail?: unknown;
}
