import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { AppSettings } from "../../src/types/settings";

const adaptersMock = vi.hoisted(() => ({
  getSettings: vi.fn<[], Promise<AppSettings>>(),
  saveSettings: vi.fn<[Partial<AppSettings>], Promise<void>>(),
  emitProofEvent: vi.fn(async () => {}),
}));

vi.mock("../../src/api/adapters", () => ({
  adapters: adaptersMock,
}));

import { GeneralSubtab } from "../../src/components/settings/GeneralSubtab";

function makeSettings(): AppSettings {
  return {
    theme: "midnight",
    ports: { bridge: 8765, api: 8000, ui: 5173 },
    printerUrls: {},
    cameraUrls: {},
    serviceUrls: {},
  };
}

beforeEach(() => {
  adaptersMock.getSettings.mockReset();
  adaptersMock.saveSettings.mockReset();
  adaptersMock.emitProofEvent.mockReset();
  adaptersMock.getSettings.mockResolvedValue(makeSettings());
  adaptersMock.saveSettings.mockResolvedValue(undefined);
  adaptersMock.emitProofEvent.mockResolvedValue(undefined);
  // setup.ts installs a fresh localStorage shim per test — nothing more to do.
});

describe("GeneralSubtab", () => {
  it("loads current theme from settings adapter", async () => {
    adaptersMock.getSettings.mockResolvedValueOnce({ ...makeSettings(), theme: "ember" });
    render(<GeneralSubtab />);
    await waitFor(() => {
      const ember = screen.getByTestId("settings-general-theme-ember");
      expect(ember.querySelector("input")).toBeChecked();
    });
  });

  it("save button disabled until a field changes", async () => {
    render(<GeneralSubtab />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-general-save")).toBeDisabled();
    });
    fireEvent.click(screen.getByTestId("settings-general-theme-alloy"));
    await waitFor(() => {
      expect(screen.getByTestId("settings-general-save")).not.toBeDisabled();
    });
  });

  it("persists theme via saveSettings and writes prefs to localStorage", async () => {
    render(<GeneralSubtab />);
    await waitFor(() => screen.getByTestId("settings-general-save"));
    fireEvent.click(screen.getByTestId("settings-general-theme-forest"));
    fireEvent.change(screen.getByTestId("settings-general-language"), {
      target: { value: "es" },
    });
    fireEvent.click(screen.getByTestId("settings-general-save"));
    await waitFor(() => {
      expect(adaptersMock.saveSettings).toHaveBeenCalledWith({ theme: "forest" });
    });
    expect(window.localStorage.getItem("h3d.settings.general.language")).toBe("es");
    await waitFor(() => {
      expect(screen.getByTestId("settings-general-status")).toHaveTextContent(
        "Preferences saved.",
      );
    });
  });

  it("shows an honest error toast on save failure", async () => {
    adaptersMock.saveSettings.mockRejectedValueOnce(new Error("Backend rejected"));
    render(<GeneralSubtab />);
    await waitFor(() => screen.getByTestId("settings-general-save"));
    fireEvent.click(screen.getByTestId("settings-general-theme-ember"));
    fireEvent.click(screen.getByTestId("settings-general-save"));
    await waitFor(() => {
      expect(screen.getByTestId("settings-general-status")).toHaveTextContent(
        "Backend rejected",
      );
    });
  });
});
