import { create } from "zustand";

/**
 * Panel dock state machine — three discrete states:
 *   - "docked":     standard inline panel (default)
 *   - "undocked":   floating window / picture-in-picture (Phase 2 ships
 *                   CSS-only; Phase 3+ may wire a native BrowserWindow)
 *   - "fullscreen": expanded overlay (Phase 2 ships CSS-only via
 *                   `fixed inset-4 z-40`; Phase 3+ may wire a native
 *                   detached window)
 *
 * No state in Phase 2 spawns native windows or external processes — every
 * transition is store-only and rendered via CSS.
 */
export type DockMode = "docked" | "undocked" | "fullscreen";

type Store = {
  /** Currently visible tab (matches a `TabDef.id`). */
  activeTabId: string;
  setActiveTabId: (id: string) => void;
  /** Per-panel dock state, keyed by panel id. */
  panelDock: Record<string, DockMode>;
  setPanelDock: (panelId: string, mode: DockMode) => void;
  /** Per-panel collapsed flag. Collapsed panels hide their body but keep header chrome visible. */
  panelCollapsed: Record<string, boolean>;
  togglePanelCollapsed: (panelId: string) => void;
  setPanelCollapsed: (panelId: string, collapsed: boolean) => void;
};

export const useStore = create<Store>((set) => ({
  activeTabId: "dashboard",
  setActiveTabId: (id) => set({ activeTabId: id }),
  panelDock: {},
  setPanelDock: (panelId, mode) =>
    set((s) => ({ panelDock: { ...s.panelDock, [panelId]: mode } })),
  panelCollapsed: {},
  togglePanelCollapsed: (panelId) =>
    set((s) => ({
      panelCollapsed: { ...s.panelCollapsed, [panelId]: !(s.panelCollapsed[panelId] ?? false) },
    })),
  setPanelCollapsed: (panelId, collapsed) =>
    set((s) => ({ panelCollapsed: { ...s.panelCollapsed, [panelId]: collapsed } })),
}));
