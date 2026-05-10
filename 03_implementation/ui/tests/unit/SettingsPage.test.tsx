/**
 * Unit tests for the W15-A17 SettingsPage URL-addressable subtab routing.
 *
 * Verifies:
 *   - subtab is selected from the initial `#settings/<sub>` hash
 *   - clicking a subtab updates the hash via replaceState
 *   - hashchange events from outside (back/forward) select the matching subtab
 *   - default fallback when the hash is missing or invalid
 */
import { fireEvent, render, screen, act } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { SettingsPage } from "../../src/components/settings/SettingsPage";

function setHash(hash: string): void {
  window.history.replaceState(null, "", hash);
  // jsdom doesn't fire hashchange on replaceState, so we synthesize it.
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

describe("SettingsPage (W15-A17) URL-addressable subtabs", () => {
  beforeEach(() => {
    setHash("#settings");
  });

  it("renders the general subtab when no sub is in the hash", () => {
    render(<SettingsPage />);
    const root = screen.getByTestId("settings-root");
    expect(root.getAttribute("data-active-subtab")).toBe("general");
  });

  it("selects the matching subtab from an initial #settings/<sub> hash", () => {
    setHash("#settings/mcp");
    render(<SettingsPage />);
    const root = screen.getByTestId("settings-root");
    expect(root.getAttribute("data-active-subtab")).toBe("mcp");
  });

  it.each([
    ["#settings/general", "general"],
    ["#settings/providers", "providers"],
    ["#settings/agents", "agents"],
    ["#settings/mcp", "mcp"],
    ["#settings/printers", "printers"],
    ["#settings/environment", "environment"],
    ["#settings/updates", "updates"],
    ["#settings/about", "about"],
  ])("hash %s selects the %s subtab", (hash, sub) => {
    setHash(hash);
    render(<SettingsPage />);
    const root = screen.getByTestId("settings-root");
    expect(root.getAttribute("data-active-subtab")).toBe(sub);
  });

  it("clicking a subtab updates the URL hash", () => {
    render(<SettingsPage />);
    const printersBtn = screen.getByTestId("settings-subtab-printers");
    fireEvent.click(printersBtn);
    expect(window.location.hash).toBe("#settings/printers");
    expect(screen.getByTestId("settings-root").getAttribute("data-active-subtab")).toBe(
      "printers",
    );
  });

  it("responds to external hashchange events", () => {
    render(<SettingsPage />);
    expect(screen.getByTestId("settings-root").getAttribute("data-active-subtab")).toBe(
      "general",
    );
    act(() => {
      setHash("#settings/about");
    });
    expect(screen.getByTestId("settings-root").getAttribute("data-active-subtab")).toBe(
      "about",
    );
  });

  it("ignores invalid subtab names in the hash and falls back to general", () => {
    setHash("#settings/not-a-subtab");
    render(<SettingsPage />);
    expect(screen.getByTestId("settings-root").getAttribute("data-active-subtab")).toBe(
      "general",
    );
  });
});
