import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DashboardModeSwitcher } from "../../src/components/dashboard/DashboardModeSwitcher";
import { useDashboardModeStore } from "../../src/components/dashboard/dashboardModeStore";

beforeEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
  useDashboardModeStore.setState({ mode: "advanced" });
});

afterEach(() => {
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem("h3d.dashboard.custom.layout");
});

describe("DashboardModeSwitcher", () => {
  it("renders one radio button per dashboard mode and marks the active one", () => {
    useDashboardModeStore.setState({ mode: "custom" });
    render(<DashboardModeSwitcher />);
    const buttons = screen.getAllByRole("radio");
    expect(buttons).toHaveLength(6);
    const labels = buttons.map((button) => button.textContent);
    expect(labels).toEqual(["Simple", "Advanced", "Factory", "Create", "Inspect", "Custom"]);
    const custom = screen.getByTestId("dashboard-mode-btn-custom");
    expect(custom.getAttribute("aria-checked")).toBe("true");
    expect(custom.dataset.active).toBe("true");
  });

  it("clicking a mode updates the store + localStorage", () => {
    render(<DashboardModeSwitcher />);
    fireEvent.click(screen.getByTestId("dashboard-mode-btn-simple"));
    expect(useDashboardModeStore.getState().mode).toBe("simple");
    expect(window.localStorage.getItem("h3d.dashboard.mode")).toBe("simple");
  });

  it("controlled mode + onChange override the store", () => {
    let captured: string | null = null;
    render(
      <DashboardModeSwitcher
        mode="advanced"
        onChange={(next) => {
          captured = next;
        }}
      />,
    );
    fireEvent.click(screen.getByTestId("dashboard-mode-btn-custom"));
    expect(captured).toBe("custom");
    // Controlled mode must NOT mutate the store.
    expect(useDashboardModeStore.getState().mode).toBe("advanced");
  });

  it("clicking updates the location hash for deep-link survival", () => {
    window.history.replaceState(null, "", "/");
    render(<DashboardModeSwitcher />);
    fireEvent.click(screen.getByTestId("dashboard-mode-btn-custom"));
    expect(window.location.hash).toBe("#dashboard:custom");
  });
});
