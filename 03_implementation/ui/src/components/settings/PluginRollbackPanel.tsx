/**
 * Plugin Rollback Panel — companion to PluginsTab.
 *
 * Renders a compact panel showing:
 *   - All plugins fetched from GET /api/plugins
 *   - Per-plugin health status (enabled / disabled / error)
 *   - Per-plugin deactivate (rollback) action via POST /api/plugins/{id}/deactivate
 *
 * This component does NOT depend on adapters.ts (locked by another lane).
 * It calls the backend directly with fetch, following the same pattern as
 * EnvironmentSubtab.tsx and Plugins.tsx.
 *
 * Usage: embed inside the Plugins tab or Settings panel as a side-rail.
 * The component is intentionally self-contained so it can be composed anywhere.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, RefreshCw, RotateCcw, XCircle } from "lucide-react";

type HermesImportMeta = ImportMeta & {
  env: { VITE_HERMES3D_BRIDGE_PORT?: string };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

type PluginState = "ACTIVE" | "READY" | "PLANNED";

type PluginRow = {
  id: string;
  display: string;
  description: string;
  state: PluginState;
  configured: boolean;
  status: string;
  reason: string | null;
};

type RollbackResult = {
  ok: boolean;
  message: string;
};

async function fetchPlugins(): Promise<PluginRow[]> {
  const response = await fetch(`${BASE_URL}/api/plugins`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Plugin API returned ${response.status}`);
  }
  const raw = (await response.json()) as Array<Record<string, unknown>>;
  return raw.map((p) => ({
    id: String(p.id ?? ""),
    display: String(p.display ?? p.name ?? p.id ?? ""),
    description: String(p.description ?? ""),
    state: (["ACTIVE", "READY", "PLANNED"].includes(String(p.state)) ? p.state : "PLANNED") as PluginState,
    configured: p.configured === true,
    status: String(p.status ?? "not_configured"),
    reason: typeof p.reason === "string" ? p.reason : null,
  }));
}

async function deactivatePlugin(pluginId: string): Promise<PluginRow> {
  const response = await fetch(
    `${BASE_URL}/api/plugins/${encodeURIComponent(pluginId)}/deactivate`,
    { method: "POST", headers: { Accept: "application/json" }, cache: "no-store" },
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Deactivate failed (${response.status}): ${text}`);
  }
  const p = (await response.json()) as Record<string, unknown>;
  return {
    id: String(p.id ?? ""),
    display: String(p.display ?? p.name ?? p.id ?? ""),
    description: String(p.description ?? ""),
    state: (["ACTIVE", "READY", "PLANNED"].includes(String(p.state)) ? p.state : "PLANNED") as PluginState,
    configured: p.configured === true,
    status: String(p.status ?? "not_configured"),
    reason: typeof p.reason === "string" ? p.reason : null,
  };
}

export function PluginRollbackPanel() {
  const [plugins, setPlugins] = useState<PluginRow[]>([]);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rollbackResults, setRollbackResults] = useState<Record<string, RollbackResult>>({});
  const [rollbackBusy, setRollbackBusy] = useState<Record<string, boolean>>({});

  const load = () => {
    setLoadState("loading");
    setLoadError(null);
    fetchPlugins()
      .then((rows) => {
        setPlugins(rows);
        setLoadState("ready");
      })
      .catch((err: unknown) => {
        setLoadError(err instanceof Error ? err.message : "Plugin API unreachable.");
        setLoadState("error");
      });
  };

  useEffect(() => { load(); }, []);

  const rollback = (plugin: PluginRow) => {
    if (plugin.state !== "ACTIVE") {
      setRollbackResults((prev) => ({
        ...prev,
        [plugin.id]: { ok: false, message: `Plugin is already ${plugin.state} — nothing to roll back.` },
      }));
      return;
    }
    if (!window.confirm(`Deactivate (roll back) "${plugin.display}"? This will set the plugin to READY.`)) {
      return;
    }
    setRollbackBusy((prev) => ({ ...prev, [plugin.id]: true }));
    deactivatePlugin(plugin.id)
      .then((updated) => {
        setPlugins((prev) => prev.map((p) => (p.id === plugin.id ? updated : p)));
        setRollbackResults((prev) => ({
          ...prev,
          [plugin.id]: { ok: true, message: `Deactivated — plugin is now ${updated.state}.` },
        }));
      })
      .catch((err: unknown) => {
        setRollbackResults((prev) => ({
          ...prev,
          [plugin.id]: { ok: false, message: err instanceof Error ? err.message : "Rollback failed." },
        }));
      })
      .finally(() => {
        setRollbackBusy((prev) => ({ ...prev, [plugin.id]: false }));
      });
  };

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="plugin-rollback-panel">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold text-fg">Plugin Health &amp; Rollback</h3>
        <button
          type="button"
          onClick={load}
          disabled={loadState === "loading"}
          className="flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={11} className={loadState === "loading" ? "animate-spin" : ""} />
          {loadState === "loading" ? "Loading…" : "Refresh"}
        </button>
      </div>

      {loadState === "error" && (
        <div className="flex items-center gap-2 rounded border border-red-800/60 bg-red-950/40 px-3 py-2 text-red-300">
          <XCircle size={12} />
          {loadError}
        </div>
      )}

      {plugins.length === 0 && loadState === "ready" && (
        <p className="text-muted">No plugins returned by the backend.</p>
      )}

      <ul className="flex flex-col gap-1.5" data-testid="plugin-rollback-list">
        {plugins.map((plugin) => {
          const result = rollbackResults[plugin.id];
          const busy = rollbackBusy[plugin.id] ?? false;
          return (
            <li
              key={plugin.id}
              className="flex flex-col gap-1 rounded border border-border bg-surface2/30 px-3 py-2"
              data-testid={`plugin-rollback-row-${plugin.id}`}
            >
              <div className="flex items-center gap-2">
                <HealthIcon state={plugin.state} configured={plugin.configured} />
                <span className="flex-1 font-medium text-fg truncate">{plugin.display}</span>
                <span className={`rounded px-1.5 py-0.5 text-[10px] ${stateClass(plugin.state)}`}>
                  {plugin.state}
                </span>
                {plugin.state === "ACTIVE" && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => rollback(plugin)}
                    title="Deactivate (roll back) this plugin"
                    className="flex items-center gap-1 rounded border border-amber-700/60 bg-amber-950/30 px-2 py-0.5 text-[10px] text-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <RotateCcw size={9} className={busy ? "animate-spin" : ""} />
                    {busy ? "Rolling back…" : "Rollback"}
                  </button>
                )}
              </div>

              {!plugin.configured && plugin.reason && (
                <p className="text-[10px] text-amber-300/80">{plugin.reason}</p>
              )}

              {result && (
                <p
                  className={`flex items-center gap-1 text-[10px] ${result.ok ? "text-green-300" : "text-red-300"}`}
                >
                  {result.ok ? <CheckCircle size={10} /> : <AlertTriangle size={10} />}
                  {result.message}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function HealthIcon({ state, configured }: { state: PluginState; configured: boolean }) {
  if (state === "ACTIVE" && configured) return <CheckCircle size={12} className="text-green-400 shrink-0" />;
  if (state === "ACTIVE" && !configured) return <AlertTriangle size={12} className="text-amber-400 shrink-0" />;
  if (state === "READY") return <AlertTriangle size={12} className="text-amber-300 shrink-0" />;
  return <XCircle size={12} className="text-muted shrink-0" />;
}

function stateClass(state: PluginState) {
  if (state === "ACTIVE") return "bg-green-900/50 text-green-300";
  if (state === "READY") return "bg-amber-900/50 text-amber-200";
  return "bg-surface2 text-muted";
}
