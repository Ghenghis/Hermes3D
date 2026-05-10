import { create } from "zustand";

export const DOCK_MODES = ["docked", "undocked", "fullscreen"] as const;
export type DockMode = (typeof DOCK_MODES)[number];
export const UI_MODES = ["full", "simple"] as const;
export type UIMode = (typeof UI_MODES)[number];
const TAB_IDS = [
  "source_os",
  "dashboard",
  "autopilot",
  "design",
  "gen3d",
  "jobs",
  "printers",
  "observe",
  "voice",
  "agents",
  "learning",
  "artifacts",
  "approvals",
  "apps",
  "plugins",
  "settings",
  "roadmap",
] as const;
const HASH_TO_TAB: Record<string, string> = {
  sources: "source_os",
  source_os: "source_os",
  source: "source_os",
  dashboard: "dashboard",
  autopilot: "autopilot",
  design: "design",
  gen3d: "gen3d",
  "3d-generation": "gen3d",
  jobs: "jobs",
  printers: "printers",
  observe: "observe",
  voice: "voice",
  agents: "agents",
  learning: "learning",
  artifacts: "artifacts",
  approvals: "approvals",
  apps: "apps",
  plugins: "plugins",
  settings: "settings",
  roadmap: "roadmap",
};
export const TAB_TO_HASH: Record<string, string> = {
  source_os: "sources",
  dashboard: "dashboard",
  autopilot: "autopilot",
  design: "design",
  gen3d: "gen3d",
  jobs: "jobs",
  printers: "printers",
  observe: "observe",
  voice: "voice",
  agents: "agents",
  learning: "learning",
  artifacts: "artifacts",
  approvals: "approvals",
  apps: "apps",
  plugins: "plugins",
  settings: "settings",
  roadmap: "roadmap",
};

export function isDockMode(mode: unknown): mode is DockMode {
  return typeof mode === "string" && DOCK_MODES.includes(mode as DockMode);
}

export function normalizeDockMode(mode: unknown): DockMode {
  return isDockMode(mode) ? mode : "docked";
}

export function tabIdFromHash(hash: string): string | null {
  const raw = hash.replace(/^#/, "").trim();
  if (!raw) {
    return null;
  }
  // Strip an optional `:mode` suffix used by the dashboard mode router
  // (e.g. `#dashboard:simple`) AND support nested hash routes like
  // `#apps/<id>` (W8-2). The first segment selects the tab; trailing
  // mode/path segments are owned by the tab itself.
  const head = raw.split(/[:/.]/, 1)[0] ?? raw;
  const tabId = HASH_TO_TAB[head] ?? head;
  return TAB_IDS.includes(tabId as (typeof TAB_IDS)[number]) ? tabId : null;
}

function initialActiveTabId(): string {
  if (typeof window === "undefined") {
    return "dashboard";
  }
  return tabIdFromHash(window.location.hash) ?? "dashboard";
}

/**
 * Panel dock state machine — three discrete states:
 *   - "docked":     standard inline panel (default)
 *   - "undocked":   floating picture-in-picture panel rendered with CSS
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
  /** Presentation mode. Both modes render the same live backend state. */
  uiMode: UIMode;
  setUiMode: (mode: UIMode) => void;
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
  activeTabId: initialActiveTabId(),
  setActiveTabId: (id) => set({ activeTabId: id }),
  uiMode: "full",
  setUiMode: (mode) => set({ uiMode: UI_MODES.includes(mode) ? mode : "full" }),
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
