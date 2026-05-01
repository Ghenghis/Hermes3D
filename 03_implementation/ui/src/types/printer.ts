/** TypeScript mirror of the printer-row shape rendered in PrinterFleet + Dashboard. */

export type PrinterStatus =
  | "online"
  | "printing"
  | "paused"
  | "maintenance"
  | "offline"
  | "error";

export type PrinterAdapter = "moonraker" | "octoprint" | "printrun" | "manual";
export type PrinterDataSource = "mock" | "live" | "error";

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
}
