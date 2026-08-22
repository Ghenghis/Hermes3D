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

const WORKBENCH_LAYOUT_KEY = "h3d.operatorWorkbench.layout.custom";
const WORKBENCH_SAVED_LAYOUTS_KEY = "h3d.operatorWorkbench.savedLayouts.custom";
const WORKBENCH_ACTION_TAB_KEY = "h3d.operatorWorkbench.actionTab.custom";
const DEFAULT_CUSTOM_WORKBENCH = ["action", "modeler", "slicerApps", "slicer", "cameras", "printerConsole", "agents"];

function clearCustomWorkbenchStorage() {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
  window.localStorage.removeItem(WORKBENCH_LAYOUT_KEY);
  window.localStorage.removeItem(WORKBENCH_SAVED_LAYOUTS_KEY);
  window.localStorage.removeItem(WORKBENCH_ACTION_TAB_KEY);
}

beforeEach(() => {
  clearCustomWorkbenchStorage();
});

afterEach(() => {
  clearCustomWorkbenchStorage();
  vi.clearAllMocks();
});

describe("DashboardCustom", () => {
  it("renders the custom workbench layout when no localStorage layout is present", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    expect(screen.getByText("Custom Workbench")).toBeTruthy();
    for (const widgetId of DEFAULT_CUSTOM_WORKBENCH) {
      expect(screen.getByTestId(`operator-widget-${widgetId}`)).toBeTruthy();
    }
  });

  it("opens the card editor when Cards is clicked", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    expect(screen.queryByTestId("operator-workbench-layout-editor")).toBeNull();
    fireEvent.click(screen.getByTestId("operator-workbench-cards-btn"));
    expect(screen.getByTestId("operator-workbench-layout-editor")).toBeTruthy();
  });

  it("removing a card persists the new workbench layout to localStorage", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    fireEvent.click(screen.getByTestId("operator-widget-remove-slicer"));
    await waitFor(() => {
      expect(screen.queryByTestId("operator-widget-slicer")).toBeNull();
    });
    const persisted = window.localStorage.getItem(WORKBENCH_LAYOUT_KEY);
    expect(persisted).toBeTruthy();
    const parsed = JSON.parse(persisted as string);
    expect(parsed.order).not.toContain("slicer");
  });

  it("adding a card from the editor appends it to the workbench", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    fireEvent.click(screen.getByTestId("operator-workbench-cards-btn"));
    const addBtn = await screen.findByTestId("operator-card-add-jobs");
    fireEvent.click(addBtn);
    await waitFor(() => {
      expect(screen.getByTestId("operator-widget-jobs")).toBeTruthy();
    });
  });

  it("Reset returns the workbench to the default custom order", async () => {
    render(<DashboardCustom />);
    await screen.findByTestId("dashboard-root");
    fireEvent.click(screen.getByTestId("operator-widget-remove-slicer"));
    await waitFor(() => expect(screen.queryByTestId("operator-widget-slicer")).toBeNull());
    fireEvent.click(screen.getByTestId("operator-workbench-reset-btn"));
    await waitFor(() => {
      for (const widgetId of DEFAULT_CUSTOM_WORKBENCH) {
        expect(screen.getByTestId(`operator-widget-${widgetId}`)).toBeTruthy();
      }
    });
  });
});
