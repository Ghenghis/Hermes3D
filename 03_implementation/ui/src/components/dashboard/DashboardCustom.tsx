/**
 * Dashboard Custom mode — W6-3 lane.
 *
 * Contract (from `Images-GUI/01-dashboard-modes/custom-dashboard-*.png`):
 *  - Configurable widget grid. The user picks which widgets are visible from
 *    a side palette (rendered in a settings drawer) and reorders them by
 *    drag-and-drop. Layout state is persisted to localStorage via
 *    `dashboardModeStore.writePersistedCustomLayout`.
 *  - Each widget is a thin live wrapper around an existing data source so we
 *    never invent payloads. Empty/blocked sources render a truthful empty
 *    state.
 *  - Defaults to a sensible 5-widget layout (KPI strip, fleet, pipeline,
 *    resources, jobs) which the user can refine.
 *
 * Drag-and-drop uses native HTML5 events so we do not need to add a new
 * dependency (the project already keeps node_modules lean).
 */
import { Cloud, CloudOff, GripVertical, Plus, Settings as SettingsIcon, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { adapters } from "../../api/adapters";
import { ResourceGauge } from "../charts/ResourceGauge";
import { Sparkline } from "../charts/Sparkline";
import { tokens } from "../../styles/tokens";
import type { Job } from "../../types/job";
import type { Printer } from "../../types/printer";
import type { Agent } from "../../types/agent";
import type { LogEntry } from "../../types/log";
import type { Notification } from "../../types/notification";
import type { ProofBundle } from "../../types/proof";
import type { SystemSnapshot } from "../../types/system";
import type { Workflow } from "../../types/workflow";
import { useDashboardLayouts } from "../../hooks/useDashboardLayouts";
import {
  ALL_CUSTOM_WIDGETS,
  DEFAULT_CUSTOM_LAYOUT,
  type CustomWidgetId,
  readPersistedCustomLayout,
  writePersistedCustomLayout,
} from "./dashboardModeStore";

type CustomState = {
  printers: Printer[];
  jobs: Job[];
  agents: Agent[];
  workflows: Workflow[];
  proof: ProofBundle | null;
  system: SystemSnapshot | null;
  logs: LogEntry[];
  notifications: Notification[];
};

const EMPTY_STATE: CustomState = {
  printers: [],
  jobs: [],
  agents: [],
  workflows: [],
  proof: null,
  system: null,
  logs: [],
  notifications: [],
};

const WIDGET_LABELS: Record<CustomWidgetId, string> = {
  kpi: "KPI Cards",
  fleet: "Printer Fleet",
  pipeline: "Workflow Pipeline",
  agents: "Active Agents",
  resources: "System Resources",
  jobs: "Recent Jobs",
  proof: "Proof & Verification",
  logs: "System Logs",
  notifications: "Notifications",
};

const WIDGET_DESCRIPTIONS: Record<CustomWidgetId, string> = {
  kpi: "Total/active/queued counts and success rate.",
  fleet: "Live printer fleet with status and progress.",
  pipeline: "Active AI workflow stages and progress.",
  agents: "Active agents and their assigned task counts.",
  resources: "CPU / RAM / Disk / Network gauges.",
  jobs: "Most recent jobs from the queue.",
  proof: "Latest proof bundle verdict and gate summary.",
  logs: "Most recent live log entries.",
  notifications: "Live notification feed.",
};

export function DashboardCustom() {
  const [layout, setLayout] = useState<CustomWidgetId[]>(() => {
    const persisted = readPersistedCustomLayout();
    return persisted ?? [...DEFAULT_CUSTOM_LAYOUT];
  });
  const [state, setState] = useState<CustomState>(EMPTY_STATE);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draggingId, setDraggingId] = useState<CustomWidgetId | null>(null);

  // Optional server-side persistence (W15-A12 / A20 wiring). The hook is a
  // no-op when the VITE_FEATURE_DASHBOARD_LAYOUTS flag is not set; localStorage
  // remains the primary cache in all cases.
  const layoutsSync = useDashboardLayouts();

  // Persist on every layout change so refresh is faithful.
  // localStorage is always written (primary cache). When server sync is
  // enabled, also push to the backend; saveLayout swallows network errors.
  useEffect(() => {
    if (layoutsSync.enabled) {
      void layoutsSync.saveLayout(layout);
    } else {
      writePersistedCustomLayout(layout);
    }
  }, [layout, layoutsSync]);

  // When server sync is enabled and a server layout arrives that differs
  // from the locally-held one AND the user has not edited yet this session,
  // adopt the server copy. The localStorage-vs-server reconciliation rule
  // lives in useDashboardLayouts; this effect just plumbs the result.
  useEffect(() => {
    if (!layoutsSync.enabled) return;
    const server = layoutsSync.serverLayout;
    if (!server || server.length === 0) return;
    // Only adopt if local was empty/default at load time.
    const local = readPersistedCustomLayout();
    if (local && local.length > 0) return;
    setLayout(server);
  }, [layoutsSync.enabled, layoutsSync.serverLayout]);

  useEffect(() => {
    let mounted = true;
    void Promise.allSettled([
      adapters.getPrinters(),
      adapters.getJobs("printing,queued,completed,failed,cancelled"),
      adapters.getAgents(),
      adapters.getActiveWorkflows(),
      adapters.getLatestProofBundle(),
      adapters.getSystemSnapshot(),
      adapters.getLogs(),
      adapters.getNotifications(),
    ]).then((results) => {
      if (!mounted) return;
      setState({
        printers: results[0].status === "fulfilled" ? results[0].value : [],
        jobs: results[1].status === "fulfilled" ? results[1].value : [],
        agents: results[2].status === "fulfilled" ? results[2].value : [],
        workflows: results[3].status === "fulfilled" ? results[3].value : [],
        proof: results[4].status === "fulfilled" ? results[4].value : null,
        system: results[5].status === "fulfilled" ? results[5].value : null,
        logs: results[6].status === "fulfilled" ? results[6].value : [],
        notifications: results[7].status === "fulfilled" ? results[7].value : [],
      });
    });
    return () => {
      mounted = false;
    };
  }, []);

  const availableToAdd = useMemo<CustomWidgetId[]>(
    () => ALL_CUSTOM_WIDGETS.filter((id) => !layout.includes(id)),
    [layout],
  );

  const removeWidget = (id: CustomWidgetId) => {
    setLayout((current) => current.filter((widgetId) => widgetId !== id));
  };
  const addWidget = (id: CustomWidgetId) => {
    setLayout((current) => (current.includes(id) ? current : [...current, id]));
  };

  const handleDragStart = (id: CustomWidgetId) => {
    setDraggingId(id);
  };
  const handleDragEnd = () => {
    setDraggingId(null);
  };
  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };
  const handleDrop = (targetId: CustomWidgetId) => {
    if (!draggingId || draggingId === targetId) {
      setDraggingId(null);
      return;
    }
    setLayout((current) => {
      const next = [...current];
      const fromIndex = next.indexOf(draggingId);
      const toIndex = next.indexOf(targetId);
      if (fromIndex < 0 || toIndex < 0) {
        return current;
      }
      next.splice(fromIndex, 1);
      next.splice(toIndex, 0, draggingId);
      return next;
    });
    setDraggingId(null);
  };

  const resetLayout = () => {
    setLayout([...DEFAULT_CUSTOM_LAYOUT]);
  };

  return (
    <div
      className="dashboard-custom-shell relative flex h-full min-h-0 flex-col gap-2"
      data-testid="dashboard-root"
      data-dashboard-mode="custom"
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="text-fg text-sm font-semibold">Custom Layout</div>
          <div className="text-muted text-xs">
            Drag a widget by its handle to reorder. Use the palette to add or remove widgets.
          </div>
        </div>
        <div className="flex items-center gap-2">
          {layoutsSync.enabled && (
            <span
              data-testid="dashboard-custom-sync-indicator"
              title={
                layoutsSync.lastError
                  ? `Layout sync offline: ${layoutsSync.lastError}`
                  : layoutsSync.lastSyncedUtc
                    ? `Last synced ${layoutsSync.lastSyncedUtc}`
                    : layoutsSync.isSaving
                      ? "Syncing layout…"
                      : "Server layout sync enabled"
              }
              className={[
                "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                layoutsSync.lastError
                  ? "border-accent-amber/40 bg-accent-amber/10 text-accent-amber"
                  : "border-accent-green/40 bg-accent-green/10 text-accent-green",
              ].join(" ")}
            >
              {layoutsSync.lastError ? <CloudOff size={11} /> : <Cloud size={11} />}
              {layoutsSync.isSaving ? "Sync…" : layoutsSync.lastError ? "Local" : "Sync"}
            </span>
          )}
          <button
            type="button"
            data-testid="dashboard-custom-reset-btn"
            onClick={resetLayout}
            className="rounded-md border border-border bg-surface px-2.5 py-1 text-[12px] font-medium text-muted hover:bg-surface2 hover:text-fg"
          >
            Reset
          </button>
          <button
            type="button"
            data-testid="dashboard-custom-edit-btn"
            onClick={() => setDrawerOpen((open) => !open)}
            aria-pressed={drawerOpen}
            className="inline-flex items-center gap-1.5 rounded-md border border-accent-blue/40 bg-accent-blue/15 px-2.5 py-1 text-[12px] font-semibold text-accent-blue hover:bg-accent-blue/25"
          >
            <SettingsIcon size={13} />
            Edit Layout
          </button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-12 gap-3">
        <div
          data-testid="dashboard-custom-grid"
          data-widget-count={layout.length}
          className={[
            // Matches Images-GUI/01-dashboard-modes/custom-dashboard-a/b density:
            // 1-col mobile, 2-col tablet, 3-col laptop, 4-col xl (≥1280px).
            "col-span-12 grid auto-rows-min grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
            drawerOpen ? "lg:col-span-9" : "lg:col-span-12",
          ].join(" ")}
        >
          {layout.length === 0 ? (
            <EmptyLayoutState onAdd={() => setDrawerOpen(true)} />
          ) : (
            layout.map((widgetId) => (
              <CustomWidgetSlot
                key={widgetId}
                widgetId={widgetId}
                state={state}
                draggingId={draggingId}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onRemove={removeWidget}
              />
            ))
          )}
        </div>

        {drawerOpen && (
          <aside
            data-testid="dashboard-custom-palette"
            className="col-span-12 lg:col-span-3"
          >
            <div className="rounded-card border border-border bg-surface p-3">
              <div className="flex items-center justify-between">
                <div className="text-fg text-sm font-semibold">Widget Palette</div>
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  className="rounded p-1 text-muted hover:bg-surface2 hover:text-fg"
                  aria-label="Close palette"
                >
                  <X size={14} />
                </button>
              </div>
              <p className="mt-1 text-[11px] text-muted">
                Add widgets from the catalogue below. They will append to the bottom of the
                grid; drag them to reorder. Remove with the trash icon on each card.
              </p>
              <div className="mt-3 flex flex-col gap-1.5">
                {availableToAdd.length === 0 ? (
                  <div className="rounded border border-dashed border-border bg-surface2 p-2 text-center text-[11px] text-muted">
                    All widgets are placed on the grid.
                  </div>
                ) : (
                  availableToAdd.map((widgetId) => (
                    <button
                      key={widgetId}
                      type="button"
                      data-testid={`dashboard-custom-add-${widgetId}`}
                      onClick={() => addWidget(widgetId)}
                      className="flex items-start gap-2 rounded border border-border bg-surface2 p-2 text-left text-[12px] text-fg hover:border-accent-blue/60 hover:bg-accent-blue/10"
                    >
                      <Plus size={14} className="mt-[2px] shrink-0 text-accent-blue" />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium">{WIDGET_LABELS[widgetId]}</div>
                        <div className="text-muted text-[10px]">{WIDGET_DESCRIPTIONS[widgetId]}</div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function EmptyLayoutState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="col-span-full rounded-card border border-dashed border-border bg-surface2/50 p-6 text-center text-sm">
      <div className="text-fg font-semibold">No widgets selected</div>
      <p className="mt-1 text-xs text-muted">
        Custom layout is empty. Open the palette to add widgets.
      </p>
      <button
        type="button"
        onClick={onAdd}
        className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-accent-blue/40 bg-accent-blue/15 px-3 py-1.5 text-[12px] font-semibold text-accent-blue hover:bg-accent-blue/25"
      >
        <Plus size={13} />
        Open Palette
      </button>
    </div>
  );
}

function CustomWidgetSlot({
  widgetId,
  state,
  draggingId,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDrop,
  onRemove,
}: {
  widgetId: CustomWidgetId;
  state: CustomState;
  draggingId: CustomWidgetId | null;
  onDragStart: (id: CustomWidgetId) => void;
  onDragEnd: () => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDrop: (id: CustomWidgetId) => void;
  onRemove: (id: CustomWidgetId) => void;
}) {
  const isDragging = draggingId === widgetId;
  return (
    <div
      data-testid={`dashboard-custom-widget-${widgetId}`}
      data-widget-id={widgetId}
      draggable
      onDragStart={() => onDragStart(widgetId)}
      onDragEnd={onDragEnd}
      onDragOver={onDragOver}
      onDrop={() => onDrop(widgetId)}
      className={[
        "rounded-card border border-border bg-surface p-3 transition-opacity",
        isDragging ? "opacity-50" : "opacity-100",
      ].join(" ")}
    >
      <div className="mb-2 flex items-center justify-between gap-2 border-b border-border pb-1.5">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
          <GripVertical size={13} className="cursor-move text-muted" aria-hidden />
          {WIDGET_LABELS[widgetId]}
        </div>
        <button
          type="button"
          onClick={() => onRemove(widgetId)}
          aria-label={`Remove ${WIDGET_LABELS[widgetId]}`}
          data-testid={`dashboard-custom-remove-${widgetId}`}
          className="rounded p-1 text-muted hover:bg-surface2 hover:text-accent-red"
        >
          <Trash2 size={13} />
        </button>
      </div>
      <div className="min-h-[120px]">
        <CustomWidgetBody widgetId={widgetId} state={state} />
      </div>
    </div>
  );
}

function CustomWidgetBody({ widgetId, state }: { widgetId: CustomWidgetId; state: CustomState }) {
  switch (widgetId) {
    case "kpi":
      return <KpiBody state={state} />;
    case "fleet":
      return <FleetBody printers={state.printers} />;
    case "pipeline":
      return <PipelineBody workflows={state.workflows} />;
    case "agents":
      return <AgentsBody agents={state.agents} />;
    case "resources":
      return <ResourceBody system={state.system} />;
    case "jobs":
      return <JobsBody jobs={state.jobs} printers={state.printers} />;
    case "proof":
      return <ProofBody bundle={state.proof} />;
    case "logs":
      return <LogsBody logs={state.logs} />;
    case "notifications":
      return <NotificationsBody notifications={state.notifications} />;
    default:
      return <Empty title="Unknown widget" detail="This widget id is not registered." />;
  }
}

function KpiBody({ state }: { state: CustomState }) {
  const total = state.printers.length;
  const active = state.printers.filter((p) => p.status === "printing").length;
  const queued = state.jobs.filter((job) => job.status === "queued").length;
  const completed = state.jobs.filter((job) => job.status === "completed").length;
  const failed = state.jobs.filter((job) => job.status === "failed").length;
  const success = completed + failed > 0
    ? Math.round((completed / (completed + failed)) * 1000) / 10
    : null;
  return (
    <div className="grid grid-cols-2 gap-1.5 text-xs">
      <KpiPair label="Printers" value={String(total)} />
      <KpiPair label="Active" value={String(active)} />
      <KpiPair label="Queued" value={String(queued)} />
      <KpiPair label="Success" value={success == null ? "—" : `${success}%`} />
    </div>
  );
}
function KpiPair({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-surface2 px-2 py-1.5">
      <div className="text-muted text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-fg font-semibold">{value}</div>
    </div>
  );
}

function FleetBody({ printers }: { printers: Printer[] }) {
  if (printers.length === 0) {
    return <Empty title="No printers" detail="Printer API returned an empty fleet." />;
  }
  return (
    <ul className="flex flex-col gap-1 text-xs">
      {printers.slice(0, 5).map((p) => (
        <li key={p.id} className="flex items-center justify-between gap-2">
          <span className="truncate text-fg">{p.name}</span>
          <span className="text-muted text-[10px] uppercase">{p.status}</span>
        </li>
      ))}
    </ul>
  );
}

function PipelineBody({ workflows }: { workflows: Workflow[] }) {
  const active = workflows.find((w) => w.status === "active") ?? workflows[0] ?? null;
  if (!active) {
    return <Empty title="No active workflow" detail="Live workflows will appear here." />;
  }
  return (
    <div className="text-xs">
      <div className="text-fg truncate font-medium">{active.name}</div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface2">
        <div className="h-full rounded-full bg-accent-cyan" style={{ width: `${active.progress}%` }} />
      </div>
      <div className="mt-1 font-mono text-[10px] text-muted">{active.progress}% · stage {active.active_stage + 1}/{active.stages.length || "—"}</div>
    </div>
  );
}

function AgentsBody({ agents }: { agents: Agent[] }) {
  if (agents.length === 0) {
    return <Empty title="No live agents" detail="Agents API returned no records." />;
  }
  return (
    <ul className="flex flex-col gap-1 text-xs">
      {agents.slice(0, 5).map((agent) => (
        <li key={agent.id} className="flex items-center justify-between gap-2">
          <span className="truncate text-fg">{agent.role}</span>
          <span className="text-muted text-[10px] uppercase">{agent.status}</span>
        </li>
      ))}
    </ul>
  );
}

function ResourceBody({ system }: { system: SystemSnapshot | null }) {
  if (!system) {
    return <Empty title="System unavailable" detail="System snapshot endpoint returned no data." />;
  }
  return (
    <div className="flex flex-col gap-1.5">
      <div className="grid grid-cols-3 gap-1.5">
        <ResourceGauge value={system.cpu_pct} label="CPU" />
        <ResourceGauge value={system.ram_pct} label="RAM" />
        <ResourceGauge value={system.disk_pct} label="DISK" />
      </div>
      {system.network_kbps.length > 0 && (
        <div className="h-7">
          <Sparkline data={system.network_kbps} color={tokens.chartColors.cyan} />
        </div>
      )}
    </div>
  );
}

function JobsBody({ jobs, printers }: { jobs: Job[]; printers: Printer[] }) {
  if (jobs.length === 0) {
    return <Empty title="No recent jobs" detail="Jobs API returned no records." />;
  }
  const printerNames = new Map(printers.map((p) => [p.id, p.name]));
  return (
    <ul className="flex flex-col gap-1 text-xs">
      {jobs.slice(0, 5).map((job) => (
        <li key={job.id} className="flex items-center justify-between gap-2">
          <span className="truncate text-fg">{job.name}</span>
          <span className="text-muted text-[10px]">
            {job.printer_id ? printerNames.get(job.printer_id) ?? job.printer_id : "—"} · {job.progress}%
          </span>
        </li>
      ))}
    </ul>
  );
}

function ProofBody({ bundle }: { bundle: ProofBundle | null }) {
  if (!bundle) {
    return <Empty title="No proof bundle" detail="Latest proof endpoint returned nothing." />;
  }
  const passCount = bundle.gates.filter((g) => g.verdict === "pass").length;
  return (
    <div className="text-xs">
      <div className="text-fg font-mono truncate">{bundle.id}</div>
      <div className="mt-1 text-muted">
        {bundle.verdict.toUpperCase()} · {passCount}/{bundle.gates.length} gates pass
      </div>
    </div>
  );
}

function LogsBody({ logs }: { logs: LogEntry[] }) {
  if (logs.length === 0) {
    return <Empty title="No live logs" detail="Logs API returned no records." />;
  }
  return (
    <ul className="flex flex-col gap-0.5 text-[11px] font-mono">
      {logs.slice(0, 5).map((log, i) => (
        <li key={`${log.ts_utc}-${i}`} className="truncate text-muted">
          <span className={log.level === "error" ? "text-accent-red" : log.level === "warn" ? "text-accent-amber" : "text-accent-green"}>
            {log.level.toUpperCase()}
          </span>{" "}
          {log.message}
        </li>
      ))}
    </ul>
  );
}

function NotificationsBody({ notifications }: { notifications: Notification[] }) {
  if (notifications.length === 0) {
    return <Empty title="No notifications" detail="Inbox is empty." />;
  }
  return (
    <ul className="flex flex-col gap-1 text-xs">
      {notifications.slice(0, 4).map((notification) => (
        <li key={notification.id} className="truncate text-fg">
          <span className={`mr-1 inline-block h-1.5 w-1.5 rounded-full ${
            notification.severity === "error"
              ? "bg-accent-red"
              : notification.severity === "warn"
                ? "bg-accent-amber"
                : notification.severity === "success"
                  ? "bg-accent-green"
                  : "bg-accent-cyan"
          }`} aria-hidden />
          {notification.title}
        </li>
      ))}
    </ul>
  );
}

function Empty({ title, detail }: { title: string; detail: string }): ReactNode {
  return (
    <div className="flex h-full min-h-[100px] items-center justify-center text-center">
      <div>
        <div className="text-fg text-xs font-medium">{title}</div>
        <div className="text-muted text-[10px]">{detail}</div>
      </div>
    </div>
  );
}
