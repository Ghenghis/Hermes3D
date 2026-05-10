/**
 * PluginCard — single plugin tile with Config / Logs / Activate buttons.
 *
 * Pure presentation; receives a Plugin + endpoint-open callback +
 * activate callback. Lifted out of `tabs/Plugins.tsx` (Wave 15 / Agent
 * 16) for reuse and testability.
 *
 * Honest-blocked: Activate is disabled when `plugin.configured` is false;
 * tooltip surfaces `plugin.reason` from the live `/api/plugins` API.
 *
 * Sources consulted:
 *   - VS Code Extensions Marketplace card UI:
 *     https://code.visualstudio.com/api/references/extension-guidelines#extension-presentation
 *   - WAI-ARIA APG "Button" tooltip pattern:
 *     https://www.w3.org/WAI/ARIA/apg/patterns/button/
 */
import type { Plugin } from "../../types/plugin";

interface PluginCardProps {
  plugin: Plugin;
  onOpenEndpoint: (plugin: Plugin, kind: "config" | "logs") => void | Promise<void>;
  onActivate: (plugin: Plugin) => void | Promise<void>;
}

export function PluginCard({ plugin, onOpenEndpoint, onActivate }: PluginCardProps) {
  return (
    <section
      data-testid={`plugin-card-${plugin.id}`}
      className="rounded border border-border bg-surface p-4"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-fg">{plugin.display}</h3>
        <span className={`rounded px-2 py-1 text-xs ${stateClass(plugin.state)}`}>{plugin.state}</span>
      </div>
      <p className="mt-2 min-h-12 text-sm text-muted">
        {plugin.description || "No description returned by plugin API."}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => void onOpenEndpoint(plugin, "config")}
          data-testid={`plugin-config-${plugin.id}`}
          className="rounded border border-border px-2 py-1 text-xs text-fg"
        >
          Config
        </button>
        <button
          type="button"
          onClick={() => void onOpenEndpoint(plugin, "logs")}
          data-testid={`plugin-logs-${plugin.id}`}
          className="rounded border border-border px-2 py-1 text-xs text-fg"
        >
          Logs
        </button>
        {plugin.state === "READY" ? (
          <button
            type="button"
            disabled={!plugin.configured}
            title={plugin.configured ? "Activate this configured plugin." : plugin.reason ?? "Plugin is not configured."}
            onClick={() => void onActivate(plugin)}
            data-testid={`plugin-activate-${plugin.id}`}
            className="rounded bg-accent-blue px-2 py-1 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
          >
            Activate
          </button>
        ) : (
          <button
            type="button"
            disabled
            title={plugin.state === "ACTIVE" ? "Plugin is already ACTIVE." : "No install endpoint is exposed for PLANNED plugins."}
            className="rounded border border-border px-2 py-1 text-xs text-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            {plugin.state === "ACTIVE" ? "Active" : "Install unavailable"}
          </button>
        )}
      </div>
    </section>
  );
}

function stateClass(state: Plugin["state"]) {
  if (state === "ACTIVE") return "bg-green-900/50 text-green-300";
  if (state === "READY") return "bg-amber-900/50 text-amber-200";
  return "bg-surface2 text-muted";
}
