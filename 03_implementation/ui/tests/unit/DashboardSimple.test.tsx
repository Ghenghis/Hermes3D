import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Stub the live API adapters BEFORE importing the component so the module
// graph picks up the mock.
vi.mock("../../src/api/adapters", () => ({
  adapters: {
    getPrinters: vi.fn().mockResolvedValue([
      { id: "p1", name: "Bambu X1", model: "X1", ip: "10.0.0.1", status: "printing", current_job: null, progress: 50, data_source: "live", maintenance_flag: false },
      { id: "p2", name: "P1S", model: "P1S", ip: "10.0.0.2", status: "online", current_job: null, progress: 0, data_source: "live", maintenance_flag: false },
    ]),
    getJobs: vi.fn().mockResolvedValue([
      { id: "j1", name: "frame", printer_id: "p1", status: "completed", progress: 100 },
      { id: "j2", name: "panel", printer_id: "p2", status: "queued", progress: 0 },
    ]),
    getSystemSnapshot: vi.fn().mockResolvedValue({
      ts_utc: "2026-05-09T12:00:00.000Z",
      edition: "developer",
      system_status: "OK",
      security_status: "Locked",
      gpu_detected_pct: 100,
      gpu_name: "NVIDIA RTX",
      vram_used_gb: 4,
      vram_total_gb: 24,
      cpu_pct: 23,
      ram_pct: 41,
      gpu_util_pct: 12,
      disk_pct: 58,
      network_kbps: [120, 130, 140],
    }),
  },
}));

import { DashboardSimple } from "../../src/components/dashboard/DashboardSimple";

beforeEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
});

afterEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
  vi.clearAllMocks();
});

describe("DashboardSimple", () => {
  it("renders the dashboard root with mode='simple'", async () => {
    render(<DashboardSimple />);
    const root = await screen.findByTestId("dashboard-root");
    expect(root.dataset.dashboardMode).toBe("simple");
  });

  it("shows all five KPI tiles", async () => {
    render(<DashboardSimple />);
    await screen.findByTestId("dashboard-simple-kpi-total-printers");
    expect(screen.getByTestId("dashboard-simple-kpi-active-prints")).toBeTruthy();
    expect(screen.getByTestId("dashboard-simple-kpi-queued")).toBeTruthy();
    expect(screen.getByTestId("dashboard-simple-kpi-success-rate")).toBeTruthy();
    expect(screen.getByTestId("dashboard-simple-kpi-system-health")).toBeTruthy();
  });

  it("renders the live system status hero once data resolves", async () => {
    render(<DashboardSimple />);
    await waitFor(() => {
      const hero = screen.getByTestId("dashboard-simple-hero");
      expect(hero.textContent).toContain("OK");
    });
  });

  it("does NOT render the advanced action-window button or the custom palette", async () => {
    render(<DashboardSimple />);
    await screen.findByTestId("dashboard-root");
    expect(screen.queryByTestId("dashboard-advanced-action-window-btn")).toBeNull();
    expect(screen.queryByTestId("dashboard-custom-palette")).toBeNull();
  });
});
