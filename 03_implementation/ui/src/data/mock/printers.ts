/**
 * 12-printer fleet mock — 4 live (T1#1, T1#2, S1, V400) + 8 simulated.
 * IPs for the 4 live printers match the Phase-0 baseline doc; simulated
 * entries use 192.168.0.20-27.
 */
import type { Printer } from "../../types/printer";

export const MOCK_PRINTERS: Printer[] = [
  {
    id: "t1-1",
    name: "FLSUN T1 #1",
    model: "FLSUN T1",
    ip: "192.168.0.10",
    status: "printing",
    adapter: "moonraker",
    data_source: "mock",
    temp_hot: 215,
    temp_bed: 60,
    progress: 47,
    current_job: "frame-bracket-v3.gcode",
    maintenance_flag: false,
    camera_url: "http://192.168.0.10:8080/?action=stream",
  },
  {
    id: "t1-2",
    name: "FLSUN T1 #2",
    model: "FLSUN T1",
    ip: "192.168.0.11",
    status: "online",
    adapter: "moonraker",
    data_source: "mock",
    temp_hot: 25,
    temp_bed: 24,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: "http://192.168.0.11:8080/?action=stream",
  },
  {
    id: "s1",
    name: "FLSUN S1",
    model: "FLSUN S1",
    ip: "192.168.0.12",
    status: "maintenance",
    adapter: "moonraker",
    data_source: "mock",
    temp_hot: null,
    temp_bed: null,
    progress: null,
    current_job: null,
    maintenance_flag: true,
    camera_url: null,
  },
  {
    id: "v400",
    name: "FLSUN V400",
    model: "FLSUN V400",
    ip: "192.168.0.34",
    status: "online",
    adapter: "moonraker",
    data_source: "mock",
    temp_hot: 24,
    temp_bed: 23,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: null, // USB camera not connected per fleet notes
  },
  // Simulated entries (8) to fill the contract's 12-printer fleet view.
  ...["20", "21", "22", "23", "24", "25", "26", "27"].map(
    (suffix, i): Printer => ({
      id: `sim-${suffix}`,
      name: `Sim Printer ${i + 1}`,
      model: i % 3 === 0 ? "FLSUN T1" : i % 3 === 1 ? "FLSUN V400" : "Generic",
      ip: `192.168.0.${suffix}`,
      status: ["online", "printing", "online", "offline", "online", "printing", "online", "online"][i] as Printer["status"],
      adapter: ["moonraker", "moonraker", "octoprint", "moonraker", "printrun", "moonraker", "octoprint", "manual"][i] as Printer["adapter"],
      data_source: "mock",
      temp_hot: i % 4 === 0 ? null : 25 + i * 5,
      temp_bed: i % 4 === 0 ? null : 24 + i * 2,
      progress: [null, 18, null, null, null, 92, null, null][i],
      current_job: [null, "demo-cube.gcode", null, null, null, "spindle-housing.gcode", null, null][i],
      maintenance_flag: false,
      camera_url: null,
    }),
  ),
];
