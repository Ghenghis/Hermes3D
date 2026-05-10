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

/**
 * Settings subtab URL-hash routing (W15-A17).
 *
 * Tabs with nested subtabs encode the selection in the trailing path
 * segment, e.g. `#settings/general`, `#settings/mcp`. The first segment
 * is owned by `tabIdFromHash`; the second segment is owned by the tab
 * itself. This keeps deep links stable across reloads without coupling
 * the subtab list to the global hash table.
 *
 * Note: the helper is intentionally generic over both the tab head and
 * the allowed subtab keys so adjacent tabs (Voice / A18) can adopt the
 * same routing shape without conflicting on `store.ts`. The Voice agent
 * lane is expected to add `voiceSubtabFromHash` next to this helper.
 */
export function subtabFromHash<K extends string>(
  hash: string,
  expectedHead: string,
  allowed: readonly K[],
): K | null {
  const raw = hash.replace(/^#/, "").trim();
  if (!raw) {
    return null;
  }
  // Accept both `settings/general` and the legacy `settings.general` form;
  // colon is reserved for dashboard mode routing.
  const [head, sub] = raw.split(/[/.]/, 2);
  if (head !== expectedHead || !sub) {
    return null;
  }
  const decoded = decodeURIComponent(sub.toLowerCase());
  return (allowed as readonly string[]).includes(decoded) ? (decoded as K) : null;
}

/**
 * Convenience wrapper for the Settings tab. Keeps the rest of the app from
 * having to import the generic helper and the subtab list separately.
 */
export const SETTINGS_SUBTAB_KEYS = [
  "general",
  "providers",
  "agents",
  "mcp",
  "printers",
  "environment",
  "updates",
  "about",
] as const;
export type SettingsSubtabKey = (typeof SETTINGS_SUBTAB_KEYS)[number];

export function settingsSubtabFromHash(hash: string): SettingsSubtabKey | null {
  return subtabFromHash<SettingsSubtabKey>(hash, "settings", SETTINGS_SUBTAB_KEYS);
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
