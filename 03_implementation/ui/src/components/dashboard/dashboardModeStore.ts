/**
 * Dashboard mode store — W6-3 lane.
 *
 * The Dashboard tab supports three presentation modes:
 *
 *  - "simple"   minimal KPI cards + system status (no drawers, no advanced widgets).
 *  - "advanced" full live dashboard: 16 left-rail tabs + KPI grid + Hermes Agents
 *               chat-mirror dock + Action Window button. This is the default.
 *  - "custom"   user-configurable layout. The widget palette is rendered in a
 *               settings drawer; the active layout is persisted to localStorage.
 *
 * The chosen mode is remembered across sessions in localStorage. The mode can
 * also be selected via the URL hash (`#dashboard:simple`, `#dashboard:custom`)
 * or via the `?mode=` query parameter; the store reads both at startup.
 *
 * No UI text or colour is encoded here — only state. UI lives in the
 * `DashboardSimple/Advanced/Custom` components and `DashboardModeSwitcher`.
 *
 * The store is decoupled from the legacy `uiMode` ("full" | "simple") store
 * in `src/app/store.ts`. Code that needs the old, two-state behaviour keeps
 * using `useStore.uiMode`. Code that needs to choose between the three
 * dashboard layouts uses `useDashboardModeStore`.
 */
import { create } from "zustand";

export const DASHBOARD_MODES = ["simple", "advanced", "custom"] as const;
export type DashboardMode = (typeof DASHBOARD_MODES)[number];

const DEFAULT_MODE: DashboardMode = "advanced";

const LS_MODE_KEY = "h3d.dashboard.mode";
export const LS_CUSTOM_LAYOUT_KEY = "h3d.dashboard.custom.layout";

export const DASHBOARD_HASH_PREFIX = "dashboard";

export function isDashboardMode(value: unknown): value is DashboardMode {
  return typeof value === "string" && (DASHBOARD_MODES as readonly string[]).includes(value);
}

/**
 * Parse `?mode=<value>` from a URL search string (without the leading `?`).
 * Returns null when the parameter is missing, empty, or not a valid mode.
 */
export function modeFromQueryString(search: string): DashboardMode | null {
  if (!search) {
    return null;
  }
  const trimmed = search.startsWith("?") ? search.slice(1) : search;
  if (!trimmed) {
    return null;
  }
  for (const part of trimmed.split("&")) {
    const [rawKey, rawValue = ""] = part.split("=");
    if (rawKey === "mode") {
      const candidate = decodeURIComponent(rawValue);
      return isDashboardMode(candidate) ? candidate : null;
    }
  }
  return null;
}

/**
 * Parse a hash like `#dashboard:simple` or `#dashboard/custom`.
 * Returns null if the hash does not address the dashboard or the segment is
 * not a recognised mode.
 */
export function modeFromHash(hash: string): DashboardMode | null {
  const raw = hash.replace(/^#/, "").trim();
  if (!raw) {
    return null;
  }
  // Accept `dashboard:custom`, `dashboard/custom`, `dashboard.custom`.
  const match = raw.match(/^dashboard[:/.](simple|advanced|custom)$/i);
  if (!match) {
    return null;
  }
  const mode = match[1].toLowerCase();
  return isDashboardMode(mode) ? mode : null;
}

/**
 * Read the persisted mode from localStorage. Returns null when storage is
 * unavailable, empty, or contains a stale/invalid value.
 */
export function readPersistedMode(storage: Pick<Storage, "getItem"> | null = safeLocalStorage()): DashboardMode | null {
  if (!storage) {
    return null;
  }
  try {
    const raw = storage.getItem(LS_MODE_KEY);
    return isDashboardMode(raw) ? raw : null;
  } catch {
    return null;
  }
}

function safeLocalStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * Compute the initial dashboard mode using priority:
 *  1. URL `?mode=` query param  (explicit per-load override)
 *  2. URL hash `#dashboard:<mode>`
 *  3. Persisted localStorage value
 *  4. Default ("advanced")
 *
 * Pure: accepts explicit inputs so callers (and unit tests) can supply them.
 */
export function resolveInitialMode(opts: {
  search?: string;
  hash?: string;
  storage?: Pick<Storage, "getItem"> | null;
} = {}): DashboardMode {
  const fromQuery = modeFromQueryString(opts.search ?? (typeof window === "undefined" ? "" : window.location.search));
  if (fromQuery) {
    return fromQuery;
  }
  const fromHash = modeFromHash(opts.hash ?? (typeof window === "undefined" ? "" : window.location.hash));
  if (fromHash) {
    return fromHash;
  }
  const fromStorage = readPersistedMode(opts.storage ?? safeLocalStorage());
  if (fromStorage) {
    return fromStorage;
  }
  return DEFAULT_MODE;
}

type DashboardModeStore = {
  mode: DashboardMode;
  setMode: (mode: DashboardMode) => void;
};

export const useDashboardModeStore = create<DashboardModeStore>((set) => ({
  mode: resolveInitialMode(),
  setMode: (mode) => {
    if (!isDashboardMode(mode)) {
      return;
    }
    const storage = safeLocalStorage();
    if (storage) {
      try {
        storage.setItem(LS_MODE_KEY, mode);
      } catch {
        // ignore quota / disabled storage
      }
    }
    set({ mode });
  },
}));

/**
 * Layout state for the Custom mode. Stored as a flat array of widget ids in
 * the order the user has arranged them. The keys here are widget identifiers,
 * not React refs — keep them stable across renders.
 */
export type CustomWidgetId =
  | "kpi"
  | "fleet"
  | "pipeline"
  | "agents"
  | "resources"
  | "jobs"
  | "proof"
  | "logs"
  | "notifications";

export const ALL_CUSTOM_WIDGETS: ReadonlyArray<CustomWidgetId> = [
  "kpi",
  "fleet",
  "pipeline",
  "agents",
  "resources",
  "jobs",
  "proof",
  "logs",
  "notifications",
];

/**
 * The default Custom layout. Six widgets — chosen to match the reference at
 * `Images-GUI/01-dashboard-modes/custom-dashboard-a.png` which shows a
 * camera/slicer header, KPI + fleet + pipeline + resources + recent jobs
 * cards. Six is the minimum-density spec from the W15-A12 brief
 * ("6-12 placeable widget slots"); users can add the remaining three widgets
 * (proof, logs, notifications) from the palette.
 *
 * Layout reordering follows the React drag-and-drop reference pattern
 * documented at https://docs.dndkit.com/ ; the multi-section dashboard
 * pattern follows Grafana
 * (https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/).
 */
export const DEFAULT_CUSTOM_LAYOUT: ReadonlyArray<CustomWidgetId> = [
  "kpi",
  "fleet",
  "pipeline",
  "agents",
  "resources",
  "jobs",
];

export function readPersistedCustomLayout(
  storage: Pick<Storage, "getItem"> | null = safeLocalStorage(),
): CustomWidgetId[] | null {
  if (!storage) {
    return null;
  }
  try {
    const raw = storage.getItem(LS_CUSTOM_LAYOUT_KEY);
    if (!raw) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return null;
    }
    const filtered = parsed.filter((id): id is CustomWidgetId =>
      typeof id === "string" && (ALL_CUSTOM_WIDGETS as readonly string[]).includes(id),
    );
    return filtered.length > 0 ? filtered : null;
  } catch {
    return null;
  }
}

export function writePersistedCustomLayout(
  layout: readonly CustomWidgetId[],
  storage: Pick<Storage, "setItem"> | null = safeLocalStorage(),
): void {
  if (!storage) {
    return;
  }
  try {
    storage.setItem(LS_CUSTOM_LAYOUT_KEY, JSON.stringify(layout));
  } catch {
    // ignore quota / disabled storage
  }
}
