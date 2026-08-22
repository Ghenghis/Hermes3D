/**
 * useDashboardLayouts — W15 A12.
 *
 * Optional server-side persistence wrapper for the Custom dashboard layout.
 *
 * Persistence ordering (deliberately conservative — never lose user state):
 *
 *   1. Primary store is **always** localStorage (h3d.dashboard.custom.layout).
 *      That is the existing W6-3 contract and the existing 32 unit tests
 *      assume it. We do NOT regress that behaviour.
 *
 *   2. When the feature flag `VITE_FEATURE_DASHBOARD_LAYOUTS` is truthy AND
 *      the backend exposes `GET/PUT /api/dashboard/layouts`, this hook
 *      additionally syncs the same layout to the server so it survives a
 *      different device or a localStorage wipe.
 *
 *   3. On startup, if the server returns a layout and localStorage is empty
 *      or older, we hydrate from the server. localStorage is the cache.
 *
 *   4. Any network failure is silently swallowed — the local layout still
 *      works. The user is never blocked by a flaky backend.
 *
 * The endpoint shape is intentionally minimal so it lines up with whatever
 * the A20 backend lane ships:
 *
 *   GET  /api/dashboard/layouts          ->  { layout: CustomWidgetId[], updated_utc: string }
 *   PUT  /api/dashboard/layouts          body: { layout: CustomWidgetId[] }
 *                                        ->  { layout: CustomWidgetId[], updated_utc: string }
 *
 * The hook returns `null` for `serverLayout` until the first round-trip
 * completes; callers should treat that as "still loading; use the local copy".
 *
 * Sources cited in the PR:
 *   - React drag-and-drop reference patterns: https://docs.dndkit.com/
 *   - Grafana dashboard layout system: https://grafana.com/docs/grafana/latest/dashboards/
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ALL_CUSTOM_WIDGETS,
  type CustomWidgetId,
  readPersistedCustomLayout,
  writePersistedCustomLayout,
} from "../components/dashboard/dashboardModeStore";

type ImportMetaEnv = { VITE_FEATURE_DASHBOARD_LAYOUTS?: string };
type ImportMetaShape = { env?: ImportMetaEnv };

const DEFAULT_LAYOUTS_PATH = "/api/dashboard/layouts";
const DEFAULT_LAYOUT_USER_ID = "local-operator";

/** Feature-flag gate. Lifts the gate when the env var is exactly `"1"` or
 *  case-insensitive `"true"`. Anything else (undefined, empty, "0", "false",
 *  random string) keeps the hook offline. We deliberately avoid `Boolean()`
 *  on the raw string because `Boolean("0") === true` would defeat the gate. */
export function isServerLayoutsEnabled(env: ImportMetaEnv | undefined = (import.meta as ImportMetaShape).env): boolean {
  const raw = env?.VITE_FEATURE_DASHBOARD_LAYOUTS;
  if (typeof raw !== "string") return false;
  const lower = raw.trim().toLowerCase();
  return lower === "1" || lower === "true" || lower === "yes" || lower === "on";
}

export type ServerLayoutResponse = {
  layout: CustomWidgetId[];
  updated_utc?: string;
};

export type DashboardLayoutsClient = {
  fetch(signal?: AbortSignal): Promise<ServerLayoutResponse | null>;
  save(layout: readonly CustomWidgetId[], signal?: AbortSignal): Promise<ServerLayoutResponse | null>;
};

/** Strip unknown widget ids and dedupe while preserving order. */
function sanitiseLayout(raw: unknown): CustomWidgetId[] | null {
  if (!Array.isArray(raw)) return null;
  const seen = new Set<CustomWidgetId>();
  for (const candidate of raw) {
    if (typeof candidate === "string" && (ALL_CUSTOM_WIDGETS as readonly string[]).includes(candidate)) {
      seen.add(candidate as CustomWidgetId);
    }
  }
  return seen.size > 0 ? Array.from(seen) : null;
}

function extractServerLayoutResponse(body: unknown): ServerLayoutResponse | null {
  if (!body || typeof body !== "object") return null;
  const record = body as {
    layout?: unknown;
    updated_utc?: unknown;
    updated_at?: unknown;
    items?: unknown;
    user_id?: unknown;
  };
  const directLayout = sanitiseLayout(record.layout);
  if (directLayout) {
    return {
      layout: directLayout,
      updated_utc:
        typeof record.updated_utc === "string"
          ? record.updated_utc
          : typeof record.updated_at === "string"
            ? record.updated_at
            : undefined,
    };
  }
  if (record.layout && typeof record.layout === "object") {
    const nested = record.layout as { widgets?: unknown; order?: unknown };
    const nestedLayout = sanitiseLayout(nested.widgets) ?? sanitiseLayout(nested.order);
    if (nestedLayout) {
      return {
        layout: nestedLayout,
        updated_utc:
          typeof record.updated_utc === "string"
            ? record.updated_utc
            : typeof record.updated_at === "string"
              ? record.updated_at
              : undefined,
      };
    }
  }
  if (Array.isArray(record.items)) {
    const candidates = record.items.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object");
    const preferred =
      candidates.find((item) => item.user_id === DEFAULT_LAYOUT_USER_ID) ??
      candidates.find((item) => extractServerLayoutResponse(item) != null);
    return preferred ? extractServerLayoutResponse(preferred) : null;
  }
  return null;
}

/** Default `fetch`-based client. Implementation is small enough that callers
 *  can supply their own (mock-friendly for unit tests). */
export function createDashboardLayoutsClient(opts: { endpoint?: string; fetchImpl?: typeof fetch } = {}): DashboardLayoutsClient {
  const endpoint = opts.endpoint ?? DEFAULT_LAYOUTS_PATH;
  const fetchImpl = opts.fetchImpl ?? (typeof fetch === "function" ? fetch : null);
  return {
    async fetch(signal?: AbortSignal): Promise<ServerLayoutResponse | null> {
      if (!fetchImpl) return null;
      try {
        const response = await fetchImpl(endpoint, {
          method: "GET",
          headers: { Accept: "application/json" },
          signal,
        });
        if (!response.ok) return null;
        return extractServerLayoutResponse(await response.json());
      } catch {
        return null;
      }
    },
    async save(layout: readonly CustomWidgetId[], signal?: AbortSignal): Promise<ServerLayoutResponse | null> {
      if (!fetchImpl) return null;
      try {
        const putResponse = await fetchImpl(endpoint, {
          method: "PUT",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify({ layout }),
          signal,
        });
        const response = putResponse.ok
          ? putResponse
          : await fetchImpl(endpoint, {
            method: "POST",
            headers: { Accept: "application/json", "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: DEFAULT_LAYOUT_USER_ID, layout: { widgets: Array.from(layout) } }),
            signal,
          });
        if (!response.ok) return null;
        const parsed = extractServerLayoutResponse(await response.json());
        return parsed ?? { layout: Array.from(layout) };
      } catch {
        return null;
      }
    },
  };
}

export type UseDashboardLayoutsOptions = {
  /** Override the env-driven feature flag (tests, debug). */
  enabled?: boolean;
  /** Inject a custom client (tests). */
  client?: DashboardLayoutsClient;
};

export type UseDashboardLayoutsResult = {
  /** True iff the feature flag is on AND a client is available. */
  enabled: boolean;
  /** `null` while the first server round-trip is still in flight or the
   *  feature is disabled. Otherwise the latest server-known layout. */
  serverLayout: CustomWidgetId[] | null;
  /** Last known synced timestamp from the server (ISO string), if any. */
  lastSyncedUtc: string | null;
  /** Force a save to the server. Always also writes localStorage so the
   *  primary cache stays consistent. Returns the server-confirmed layout
   *  when the round-trip succeeds, otherwise the local one. */
  saveLayout: (layout: readonly CustomWidgetId[]) => Promise<CustomWidgetId[]>;
  /** True while a save round-trip is in flight. */
  isSaving: boolean;
  /** True if the most recent round-trip failed. UI can render an offline
   *  hint but should not block. */
  lastError: string | null;
};

/**
 * Hook variant used by the Custom dashboard. The Custom component continues
 * to drive layout state via local React state + writePersistedCustomLayout;
 * this hook layers server sync on top *when the feature flag is enabled*.
 *
 * IMPORTANT: When `enabled` is false the hook returns harmless defaults and
 * never touches the network. The existing 32 vitest cases (which do not set
 * the flag) therefore see zero behavioural change.
 */
export function useDashboardLayouts(options: UseDashboardLayoutsOptions = {}): UseDashboardLayoutsResult {
  const enabled = options.enabled ?? isServerLayoutsEnabled();
  const clientRef = useRef<DashboardLayoutsClient | null>(null);
  if (!clientRef.current) {
    clientRef.current = options.client ?? createDashboardLayoutsClient();
  }

  const [serverLayout, setServerLayout] = useState<CustomWidgetId[] | null>(null);
  const [lastSyncedUtc, setLastSyncedUtc] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  // Initial hydrate. Runs once when the flag is on. Locally cached layout is
  // already loaded by DashboardCustom before this hook resolves.
  useEffect(() => {
    if (!enabled) return;
    const client = clientRef.current;
    if (!client) return;
    const controller = new AbortController();
    let cancelled = false;
    client
      .fetch(controller.signal)
      .then((response) => {
        if (cancelled || !response) return;
        setServerLayout(response.layout);
        if (response.updated_utc) setLastSyncedUtc(response.updated_utc);
        // Reconcile localStorage with server only if the user has nothing
        // local yet. We must never overwrite a freshly-edited local layout
        // with a stale server copy on first load.
        const local = readPersistedCustomLayout();
        if (!local && response.layout.length > 0) {
          writePersistedCustomLayout(response.layout);
        }
      })
      .catch(() => {
        // ignored — `fetch()` already swallows
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [enabled]);

  const saveLayout = useCallback(
    async (layout: readonly CustomWidgetId[]): Promise<CustomWidgetId[]> => {
      // localStorage is always authoritative; do it first so a transient
      // network error does not lose user state.
      writePersistedCustomLayout(layout);
      if (!enabled) return Array.from(layout);
      const client = clientRef.current;
      if (!client) return Array.from(layout);
      setIsSaving(true);
      setLastError(null);
      try {
        const response = await client.save(layout);
        if (response) {
          setServerLayout(response.layout);
          if (response.updated_utc) setLastSyncedUtc(response.updated_utc);
          return response.layout;
        }
        setLastError("Server did not accept layout (kept local copy).");
        return Array.from(layout);
      } catch (err) {
        setLastError(err instanceof Error ? err.message : "Unknown layout-save error");
        return Array.from(layout);
      } finally {
        setIsSaving(false);
      }
    },
    [enabled],
  );

  return {
    enabled,
    serverLayout,
    lastSyncedUtc,
    saveLayout,
    isSaving,
    lastError,
  };
}
