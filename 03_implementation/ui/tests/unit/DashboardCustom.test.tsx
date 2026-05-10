import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/adapters", () => ({
  adapters: {
    getPrinters: vi.fn().mockResolvedValue([]),
    getJobs: vi.fn().mockResolvedValue([]),
    getAgents: vi.fn().mockResolvedValue([]),
    getActiveWorkflows: vi.fn().mockResolvedValue([]),
    getLatestProofBundle: vi.fn().mockResolvedValue(null),
    getSystemSnapshot: vi.fn().mockResolvedValue(null),
    getLogs: vi.fn().mockResolvedValue([]),
    getNotifications: vi.fn().mockResolvedValue([]),
  },
}));

// Recharts pulls in a heavy DOM dependency tree; stub the gauge + sparkline
// so the test focuses on the layout state.
vi.mock("../../src/components/charts/ResourceGauge", () => ({
  ResourceGauge: ({ label, value }: { label: string; value: number }) => (
    <div data-testid={`gauge-${label}`}>{value}</div>
  ),
}));
vi.mock("../../src/components/charts/Sparkline", () => ({
  Sparkline: () => <div data-testid="sparkline" />,
}));

import { DashboardCustom } from "../../src/components/dashboard/DashboardCustom";
import {
  DEFAULT_CUSTOM_LAYOUT,
  LS_CUSTOM_LAYOUT_KEY,
} from "../../src/components/dashboard/dashboardModeStore";

beforeEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
});

afterEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
  vi.clearAllMocks();
});

describe("DashboardCustom", () => {
  it("renders the default layout when no localStorage layout is present", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    for (const widgetId of DEFAULT_CUSTOM_LAYOUT) {
      expect(screen.getByTestId(`dashboard-custom-widget-${widgetId}`)).toBeTruthy();
    }
  });

  it("opens the palette when Edit Layout is clicked", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    expect(screen.queryByTestId("dashboard-custom-palette")).toBeNull();
    fireEvent.click(screen.getByTestId("dashboard-custom-edit-btn"));
    expect(screen.getByTestId("dashboard-custom-palette")).toBeTruthy();
  });

  it("removing a widget persists the new layout to localStorage", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    fireEvent.click(screen.getByTestId("dashboard-custom-remove-jobs"));
    await waitFor(() => {
      expect(screen.queryByTestId("dashboard-custom-widget-jobs")).toBeNull();
    });
    const persisted = window.localStorage.getItem(LS_CUSTOM_LAYOUT_KEY);
    expect(persisted).toBeTruthy();
    const parsed = JSON.parse(persisted as string);
    expect(parsed).not.toContain("jobs");
  });

  it("adding a widget from the palette appends it to the grid", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    fireEvent.click(screen.getByTestId("dashboard-custom-edit-btn"));
    // "logs" is not in the default layout so it should appear in the palette.
    const addBtn = await screen.findByTestId("dashboard-custom-add-logs");
    fireEvent.click(addBtn);
    await waitFor(() => {
      expect(screen.getByTestId("dashboard-custom-widget-logs")).toBeTruthy();
    });
  });

  it("Reset returns the layout to the default order", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    // First remove a widget, then reset.
    fireEvent.click(screen.getByTestId("dashboard-custom-remove-fleet"));
    await waitFor(() => expect(screen.queryByTestId("dashboard-custom-widget-fleet")).toBeNull());
    fireEvent.click(screen.getByTestId("dashboard-custom-reset-btn"));
    await waitFor(() => {
      for (const widgetId of DEFAULT_CUSTOM_LAYOUT) {
        expect(screen.getByTestId(`dashboard-custom-widget-${widgetId}`)).toBeTruthy();
      }
    });
  });
});
