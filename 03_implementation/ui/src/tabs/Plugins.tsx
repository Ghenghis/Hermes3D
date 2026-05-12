import { useCallback, useEffect, useState } from "react";
import { adapters } from "../api/adapters";
import { ResizablePane } from "../components/layout/ResizablePane";
import { PluginList } from "../components/plugins/PluginList";
import { PANEL_POLL_MS, usePollingEffect } from "../hooks/_useQuery";
import type { Plugin } from "../types/plugin";
import type { SourceModuleRuntimeSetupQueue, SourceModuleUpdateReadiness } from "../types/source-os";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

type PluginPanel = {
  title: string;
  body: string;
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

export function PluginsTab() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [panel, setPanel] = useState<PluginPanel | null>(null);
  const [readiness, setReadiness] = useState<SourceModuleUpdateReadiness | null>(null);
  const [readinessBusy, setReadinessBusy] = useState(false);
  const [setupQueue, setSetupQueue] = useState<SourceModuleRuntimeSetupQueue | null>(null);
  const [setupBusy, setSetupBusy] = useState(false);

  const load = () => void adapters.getPlugins().then((next) => setPlugins(next.map(normalizePlugin)));
  const loadReadiness = (deep = false) => {
    setReadinessBusy(true);
    void adapters.getModuleUpdateReadiness(deep)
      .then(setReadiness)
      .finally(() => setReadinessBusy(false));
  };
  const loadSetupQueue = () => {
    void adapters.getModuleRuntimeSetupQueue().then(setSetupQueue);
  };
  const planSetupQueue = () => {
    setSetupBusy(true);
    void adapters.planModuleRuntimeSetupQueue()
      .then((next) => {
        setSetupQueue(next);
        setPanel({
          title: "Source app setup queue planned",
          body: setupQueuePanelBody(next),
        });
      })
      .catch((error) => {
        setPanel({
          title: "Source app setup queue blocked",
          body: errorMessage(error),
        });
      })
      .finally(() => setSetupBusy(false));
  };

  useEffect(() => {
    loadReadiness(false);
    loadSetupQueue();
    // Readiness and the setup queue change rarely (operator action +
    // bg backups) — one-shot mount is fine for them; do NOT re-poll
    // and clobber the operator's view if they're mid-action.
  }, []);

  // W21-MVP-5: poll the plugin list itself so install_state /
  // activation toggles surface without a manual reload after the
  // operator (or another tab) flips a plugin. Reuses ``load`` so the
  // normalisation pipeline stays identical.
  const refreshPlugins = useCallback(async () => {
    const next = await adapters.getPlugins();
    setPlugins(next.map(normalizePlugin));
  }, []);
  usePollingEffect(refreshPlugins, PANEL_POLL_MS, [refreshPlugins]);

  const activate = async (plugin: Plugin) => {
    if (!plugin.configured) {
      setPanel({
        title: `${plugin.display} activation blocked`,
        body: plugin.reason ?? "Plugin is not configured; open Config and save the required local settings first.",
      });
      return;
    }
    if (!window.confirm(`Activate ${plugin.display}? This will start the plugin service.`)) {
      return;
    }
    try {
      const next = normalizePlugin(await adapters.activatePlugin(plugin.id));
      if (next.state !== "ACTIVE" || !next.configured) {
        setPanel({
          title: `${plugin.display} activation blocked`,
          body: next.reason ?? `Backend returned state ${next.state}; plugin is not active.`,
        });
        return;
      }
      await adapters.emitProofEvent("plugins.plugin.state.changed", { plugin_id: plugin.id, state: "ACTIVE" });
      setPanel({ title: `${plugin.display} activated`, body: JSON.stringify(next, null, 2) });
      load();
    } catch (error) {
      setPanel({ title: `${plugin.display} activation blocked`, body: errorMessage(error) });
    }
  };

  const openPluginEndpoint = async (plugin: Plugin, kind: "config" | "logs") => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/plugins/${encodeURIComponent(plugin.id)}/${kind}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const body = await response.text();
      setPanel({
        title: `${plugin.display} ${kind}`,
        body: response.ok ? body : `${kind} request failed: ${body || response.statusText}`,
      });
      if (response.ok) {
        await adapters.emitProofEvent(`plugins.plugin.${kind}.opened`, { plugin_id: plugin.id, accepted: true });
      }
    } catch {
      setPanel({
        title: `${plugin.display} ${kind}`,
        body: `${kind} request failed: backend API is unreachable at ${LIVE_BASE_URL}.`,
      });
    }
  };

  return (
    <div data-testid="plugins-root" className="flex min-h-[calc(100vh-6.5rem)] min-w-0 flex-col gap-3 lg:flex-row">
      <div className="grid min-h-0 min-w-0 flex-1 content-start gap-3 overflow-auto sm:grid-cols-2 md:grid-cols-3">
        <section className="rounded border border-border bg-surface p-3 text-xs sm:col-span-2 md:col-span-3" data-testid="plugins-update-readiness">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-fg">Source App Update Readiness</h3>
              <p className="mt-1 text-[11px] text-muted">Read-only source checkout summary. Apply updates from Source OS after backup, proof gates, and rollback metadata.</p>
            </div>
            <button
              type="button"
              disabled={readinessBusy}
              onClick={() => loadReadiness(true)}
              className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {readinessBusy ? "Checking" : "Deep Check"}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <ReadinessPill label="apps" value={readiness?.count ?? 0} />
            <ReadinessPill label="ready" value={readiness?.ready_for_update_check ?? 0} tone="green" />
            <ReadinessPill label="blocked" value={readiness?.blocked ?? 0} tone={(readiness?.blocked ?? 0) > 0 ? "amber" : "muted"} />
            <ReadinessPill label="dirty" value={readiness?.dirty ?? 0} tone={(readiness?.dirty ?? 0) > 0 ? "amber" : "muted"} />
            <ReadinessPill label="cached behind" value={readiness?.outdated_cached ?? 0} tone={(readiness?.outdated_cached ?? 0) > 0 ? "cyan" : "muted"} />
            <span className="rounded bg-surface2 px-2 py-1 text-[10px] uppercase text-muted">{readiness?.deep ? "deep" : "lightweight"}</span>
          </div>
          <div className="mt-3 border-t border-border/70 pt-3" data-testid="plugins-runtime-setup-queue">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <h4 className="text-[11px] font-semibold uppercase text-fg">Runtime Setup Queue</h4>
                <p className="mt-0.5 text-[11px] text-muted">
                  Plan-only source app setup; no install/build runner executes until the backend registers a safe verifier.
                </p>
              </div>
              <button
                type="button"
                disabled={setupBusy}
                onClick={() => planSetupQueue()}
                className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                {setupBusy ? "Planning" : "Plan Setup Queue"}
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <ReadinessPill label="apps" value={setupQueue?.count ?? 0} />
              <ReadinessPill label="runtime ready" value={setupQueue?.counts.runtime_ready ?? 0} tone="green" />
              <ReadinessPill label="needs runner" value={setupQueue?.counts.runner_not_registered ?? 0} tone={(setupQueue?.counts.runner_not_registered ?? 0) > 0 ? "amber" : "muted"} />
              <ReadinessPill label="install ready" value={setupQueue?.counts.source_install_available ?? 0} tone={(setupQueue?.counts.source_install_available ?? 0) > 0 ? "cyan" : "muted"} />
              <ReadinessPill label="blocked" value={setupQueue?.counts.blocked ?? 0} tone={(setupQueue?.counts.blocked ?? 0) > 0 ? "amber" : "muted"} />
              <span className="rounded bg-surface2 px-2 py-1 text-[10px] uppercase text-muted">{setupQueue?.execution_mode ?? "not loaded"}</span>
            </div>
          </div>
        </section>
        <PluginList
          plugins={plugins}
          onOpenEndpoint={(plugin, kind) => openPluginEndpoint(plugin, kind)}
          onActivate={(plugin) => activate(plugin)}
        />
      </div>
      <ResizablePane
        storageKey="h3d.plugins.apiPanel.width"
        defaultWidth={420}
        minWidth={280}
        maxWidth={720}
        side="left"
        label="Plugin API panel"
        role="complementary"
        ariaLabel="Plugin API panel"
        dataTestId="plugins-side-rail"
        className="flex min-h-0 w-full shrink-0 flex-col rounded border border-border bg-surface p-4 lg:w-[var(--pane-width)]"
      >
        <h2 className="font-semibold text-fg">{panel?.title ?? "Plugin API Panel"}</h2>
        <pre className="mt-3 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded bg-bg/70 p-3 text-xs text-muted">
          {panel?.body ?? "Select Settings or Logs to read the live backend endpoint."}
        </pre>
      </ResizablePane>
    </div>
  );
}

function ReadinessPill({ label, value, tone = "muted" }: { label: string; value: number; tone?: "green" | "amber" | "cyan" | "muted" }) {
  const toneClass = {
    green: "bg-green-950/70 text-green-300",
    amber: "bg-amber-950/70 text-amber-200",
    cyan: "bg-cyan-950/70 text-cyan-200",
    muted: "bg-surface2 text-muted",
  }[tone];
  return <span className={`rounded px-2 py-1 text-[10px] uppercase ${toneClass}`}>{value} {label}</span>;
}

function normalizePlugin(plugin: Plugin & { name?: string }): Plugin {
  return {
    ...plugin,
    display: plugin.display ?? plugin.name ?? plugin.id,
    description: plugin.description ?? "",
    state: plugin.state ?? "PLANNED",
    dependencies: plugin.dependencies ?? [],
    configSchema: plugin.configSchema ?? null,
    healthUrl: plugin.healthUrl ?? null,
    installVia: plugin.installVia ?? "none",
    sourceOsModuleId: plugin.sourceOsModuleId ?? null,
    configured: plugin.configured ?? plugin.state === "ACTIVE",
    status: plugin.status,
    reason: plugin.reason ?? null,
  };
}

function setupQueuePanelBody(queue: SourceModuleRuntimeSetupQueue): string {
  const lines = [
    `status: ${queue.status}`,
    `apps: ${queue.count}`,
    `runtime_ready: ${queue.counts.runtime_ready}`,
    `runner_not_registered: ${queue.counts.runner_not_registered}`,
    `source_install_available: ${queue.counts.source_install_available}`,
    `runtime_repair_required: ${queue.counts.runtime_repair_required}`,
    `blocked: ${queue.counts.blocked}`,
    `execution_mode: ${queue.execution_mode}`,
    `proof_event_id: ${queue.proof_event_id ?? "read-only status only"}`,
    `gate: ${queue.agent_gate}`,
  ];
  return lines.join("\n");
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the request.";
}
