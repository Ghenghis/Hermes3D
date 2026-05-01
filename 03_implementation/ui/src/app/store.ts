import { create } from "zustand";

export type DockMode = "docked" | "undocked" | "external";

type Store = {
  /** Currently visible tab (matches a `TabDef.id`). */
  activeTabId: string;
  setActiveTabId: (id: string) => void;
  /** Per-panel dock state, keyed by panel id. Phase 2 uses CSS-only dock/undock — Phase 3+ may wire native windows. */
  panelDock: Record<string, DockMode>;
  setPanelDock: (panelId: string, mode: DockMode) => void;
};

export const useStore = create<Store>((set) => ({
  activeTabId: "dashboard",
  setActiveTabId: (id) => set({ activeTabId: id }),
  panelDock: {},
  setPanelDock: (panelId, mode) =>
    set((s) => ({ panelDock: { ...s.panelDock, [panelId]: mode } })),
}));
