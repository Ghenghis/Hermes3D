import { create } from "zustand";

export const DOCK_MODES = ["docked", "undocked", "fullscreen"] as const;
export type DockMode = (typeof DOCK_MODES)[number];

export function isDockMode(mode: unknown): mode is DockMode {
  return typeof mode === "string" && DOCK_MODES.includes(mode as DockMode);
}

export function normalizeDockMode(mode: unknown): DockMode {
  return isDockMode(mode) ? mode : "docked";
}

/**
 * Panel dock state machine — three discrete states:
 *   - "docked":     standard inline panel (default)
 *   - "undocked":   floating picture-in-picture mock, rendered with CSS only
 *   - "fullscreen": expanded overlay (Phase 2 ships CSS-only via
 *                   `fixed inset-4 z-40`)
 *
 * No state in Phase 2 launches anything outside React; every transition is
 * store-only and rendered with CSS.
 */
type Store = {
  /** Currently visible tab (matches a `TabDef.id`). */
  activeTabId: string;
  setActiveTabId: (id: string) => void;
  /** Per-panel dock state, keyed by panel id. */
  panelDock: Record<string, DockMode>;
  setPanelDock: (panelId: string, mode: DockMode) => void;
  togglePanelDock: (panelId: string, mode: DockMode) => void;
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
    set((s) => ({ panelDock: { ...s.panelDock, [panelId]: normalizeDockMode(mode) } })),
  togglePanelDock: (panelId, mode) =>
    set((s) => {
      const next = s.panelDock[panelId] === mode ? "docked" : normalizeDockMode(mode);
      return { panelDock: { ...s.panelDock, [panelId]: next } };
    }),
  panelCollapsed: {},
  togglePanelCollapsed: (panelId) =>
    set((s) => ({
      panelCollapsed: { ...s.panelCollapsed, [panelId]: !(s.panelCollapsed[panelId] ?? false) },
    })),
  setPanelCollapsed: (panelId, collapsed) =>
    set((s) => ({ panelCollapsed: { ...s.panelCollapsed, [panelId]: collapsed } })),
}));
