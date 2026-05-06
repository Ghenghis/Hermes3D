import {
  Bell,
  Bot,
  Box,
  CheckCircle2,
  CircleDot,
  Code2,
  Layers,
  LogOut,
  LucideIcon,
  MessageSquare,
  Printer,
  Settings,
  ShieldCheck,
  Sparkles,
  Upload,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState, type ComponentType, type ReactNode } from "react";
import { PRIMARY_TABS } from "../../app/routes";
import { useStore } from "../../app/store";
import { adapters } from "../../api/adapters";
import { ResizablePane } from "../layout/ResizablePane";
import type { Agent } from "../../types/agent";
import type { Artifact } from "../../types/artifact";
import type { Job } from "../../types/job";
import type { LogEntry } from "../../types/log";
import type { Notification } from "../../types/notification";
import type { Printer as PrinterRow, PrinterStatus } from "../../types/printer";
import type { ProofBundle } from "../../types/proof";
import type { SourceOSModule } from "../../types/source-os";
import type { SystemSnapshot } from "../../types/system";
import type { Workflow as WorkflowRow } from "../../types/workflow";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

type EvidenceEvent = {
  type: string;
  ts_utc: string;
  source?: string;
  message?: string;
};

type SimpleState = {
  printers: PrinterRow[];
  jobs: Job[];
  agents: Agent[];
  workflows: WorkflowRow[];
  logs: LogEntry[];
  notifications: Notification[];
  proof: ProofBundle | null;
  system: SystemSnapshot | null;
  artifacts: Artifact[];
  sourceModules: SourceOSModule[];
};

const EMPTY_STATE: SimpleState = {
  printers: [],
  jobs: [],
  agents: [],
  workflows: [],
  logs: [],
  notifications: [],
  proof: null,
  system: null,
  artifacts: [],
  sourceModules: [],
};

const SIMPLE_NAV = PRIMARY_TABS;

const QUICK_ACTIONS: Array<{ label: string; icon: LucideIcon; tab: string; className: string }> = [
  { label: "New Project", icon: Box, tab: "design", className: "from-blue-600 to-blue-700" },
  { label: "Generate 3D", icon: Sparkles, tab: "gen3d", className: "from-violet-600 to-purple-800" },
  { label: "Upload File", icon: Upload, tab: "artifacts", className: "from-cyan-700 to-teal-800" },
  { label: "Slice & Prepare", icon: Wrench, tab: "source_os", className: "from-amber-700 to-orange-900" },
  { label: "Print Now", icon: Printer, tab: "jobs", className: "from-green-700 to-emerald-900" },
];

const FALLBACK_PIPELINE = [
  { id: "prompt", label: "Prompt / Input", status: "pending" as const, Icon: MessageSquare },
  { id: "gen3d", label: "3D Generation", status: "pending" as const, Icon: Box },
  { id: "blender", label: "Blender MCP", status: "pending" as const, Icon: Code2 },
  { id: "validation", label: "Validation", status: "pending" as const, Icon: ShieldCheck },
  { id: "slicing", label: "Slicing", status: "pending" as const, Icon: Layers },
  { id: "print", label: "Print", status: "pending" as const, Icon: Printer },
];

const PRINTER_TONE: Record<PrinterStatus, string> = {
  online: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  active: "bg-green-500/15 text-green-300 border-green-500/30",
  printing: "bg-green-500/15 text-green-300 border-green-500/30",
  paused: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  maintenance: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  offline: "bg-red-500/15 text-red-300 border-red-500/30",
  error: "bg-red-500/15 text-red-300 border-red-500/30",
};

type SimpleHermesDashboardProps = {
  activeTabId?: string;
  activeLabel?: string;
  Content?: ComponentType;
};

export function SimpleHermesDashboard({ activeTabId = "dashboard", activeLabel = "Dashboard", Content }: SimpleHermesDashboardProps) {
  const setUiMode = useStore((s) => s.setUiMode);
  const setActiveTabId = useStore((s) => s.setActiveTabId);
  const [state, setState] = useState<SimpleState>(EMPTY_STATE);
  const [events, setEvents] = useState<EvidenceEvent[]>([]);
  const dashboardActive = activeTabId === "dashboard";

  const load = async () => {
    const [
      printers,
      jobs,
      agents,
      workflows,
      logs,
      notifications,
      proof,
      system,
      artifacts,
      sourceModules,
    ] = await Promise.all([
      adapters.getPrinters(),
      adapters.getJobs("printing,queued,completed,failed,cancelled"),
      adapters.getAgents(),
      adapters.getActiveWorkflows(),
      adapters.getLogs(),
      adapters.getNotifications(),
      adapters.getLatestProofBundle(),
      adapters.getSystemSnapshot(),
      adapters.getArtifacts(),
      adapters.getSourceOSModules(),
    ]);
    setState({ printers, jobs, agents, workflows, logs, notifications, proof, system, artifacts, sourceModules });
  };

  useEffect(() => {
    void load();
    const refresh = window.setInterval(() => void load(), 8000);
    return () => window.clearInterval(refresh);
  }, []);

  useEffect(() => {
    const stream = new EventSource(`${LIVE_BASE_URL}/api/events/stream`);
    stream.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as EvidenceEvent;
        setEvents((current) => [parsed, ...current].slice(0, 50));
      } catch {
        setEvents((current) => [{
          type: "event",
          ts_utc: new Date().toISOString(),
          message: message.data,
        }, ...current].slice(0, 50));
      }
    };
    return () => stream.close();
  }, []);

  const onlinePrinters = state.printers.filter((printer) => printer.status !== "offline").length;
  const activePrints = state.printers.filter((printer) => printer.status === "printing").length;
  const queuedPrints = state.jobs.filter((job) => job.status === "queued").length;
  const completed = state.jobs.filter((job) => job.status === "completed").length;
  const failed = state.jobs.filter((job) => job.status === "failed").length;
  const successRate = completed + failed > 0 ? Math.round((completed / (completed + failed)) * 1000) / 10 : null;
  const activeWorkflow = state.workflows.find((workflow) => workflow.status === "active") ?? state.workflows[0] ?? null;
  const latestPreview = state.artifacts.find((artifact) => artifact.type === "screenshot" || artifact.type === "photo") ?? null;

  const openSimpleTab = (tab: string) => {
    setActiveTabId(tab);
    setUiMode("simple");
  };

  return (
    <div data-testid="simple-version-root" className="simple-dashboard-root min-h-screen overflow-auto bg-[#050c14] text-[#eef6ff] xl:h-screen xl:overflow-hidden">
      <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(32,130,255,0.15),transparent_28%),radial-gradient(circle_at_70%_20%,rgba(34,197,94,0.08),transparent_30%)] xl:flex xl:h-full xl:min-h-0 xl:flex-col">
        <header className="relative flex min-h-[86px] flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 xl:h-[92px] xl:min-h-0 xl:flex-nowrap xl:px-7 xl:py-0">
          <div className="flex min-w-0 items-center gap-4">
            <HermesMark />
            <div className="flex min-w-0 items-baseline gap-3">
              <span className="truncate text-[22px] font-bold tracking-[0.12em] text-slate-100 sm:text-[27px]">HERMES<span className="text-blue-400">3D OS</span></span>
              <span className="text-[16px] font-semibold text-blue-400">v5.3</span>
            </div>
          </div>
          <div className="order-3 w-full text-center xl:absolute xl:left-1/2 xl:top-6 xl:order-none xl:w-auto xl:-translate-x-1/2">
            <div className="text-[17px] font-bold uppercase tracking-[0.06em] text-slate-100">AI-DRIVEN 3D PRINTING OS</div>
            <div className="mt-1 text-[13px] text-blue-100/80">Design. Verify. Slice. Print. Monitor. Repeat.</div>
          </div>
          <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 sm:gap-3">
            <TopStatus system={state.system} />
            <div className="rounded-md border border-slate-700/80 bg-slate-900/70 px-5 py-3 font-mono text-[13px] text-blue-100">
              {formatClock(state.system?.ts_utc)}
            </div>
            <div className="rounded border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-[12px] font-semibold text-cyan-200">Live API + Proof</div>
            <IconShell title="Open dashboard notifications" onClick={() => openSimpleTab("dashboard")}><Bell size={22} /></IconShell>
            <IconShell title="Open settings" onClick={() => openSimpleTab("settings")}><Settings size={22} /></IconShell>
            <button
              type="button"
              onClick={() => setUiMode("full")}
              className="grid h-12 w-12 place-items-center rounded-full border border-blue-500 bg-blue-600/10 text-blue-300 shadow-[0_0_22px_rgba(59,130,246,0.25)]"
              title="Switch to full Hermes3D OS"
            >
              <LogOut size={20} />
            </button>
          </div>
        </header>

        <div className="flex flex-col gap-5 px-4 pb-5 sm:px-5 xl:h-[calc(100vh-92px)] xl:min-h-0 xl:flex-row">
          <ResizablePane
            storageKey="h3d.simple.leftRail.width"
            defaultWidth={280}
            minWidth={220}
            maxWidth={480}
            label="Simple mode navigation and quick actions"
            dataTestId="simple-side-rail"
            className="flex min-h-0 w-full shrink-0 flex-col gap-3 xl:w-[var(--pane-width)] xl:overflow-auto"
          >
            <SimplePanel className="p-2">
              <nav data-testid="simple-primary-nav" className="flex flex-col gap-1.5">
                {SIMPLE_NAV.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    data-testid={`simple-nav-${item.id}`}
                    aria-current={item.id === activeTabId ? "page" : undefined}
                    onClick={() => openSimpleTab(item.id)}
                    className={[
                      "flex h-[46px] items-center gap-3 rounded-md px-4 text-left text-[14px] transition",
                      item.id === activeTabId
                        ? "border border-blue-500/50 bg-blue-600/70 text-white shadow-[inset_0_0_24px_rgba(59,130,246,0.28)]"
                        : "text-blue-100/90 hover:bg-slate-800/80 hover:text-white",
                    ].join(" ")}
                  >
                    <item.icon size={18} className="shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                ))}
              </nav>
            </SimplePanel>
            <SimplePanel className="p-3">
              <h2 className="mb-3 text-[13px] uppercase tracking-[0.06em] text-blue-100">Quick Actions</h2>
              <div className="flex flex-col gap-2">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    type="button"
                    onClick={() => openSimpleTab(action.tab)}
                    className={`flex h-9 items-center gap-2 rounded-md bg-gradient-to-r px-3 text-left text-[12px] font-medium text-white ${action.className}`}
                  >
                    <action.icon size={15} />
                    {action.label}
                  </button>
                ))}
              </div>
              <div className="mt-3 rounded border border-slate-700/70 bg-slate-950/40 px-3 py-2 text-[11px] text-blue-100/70">
                Source apps: <span className="font-mono text-white">{state.sourceModules.length}</span> registered ·{" "}
                <span className="font-mono text-green-300">{state.sourceModules.filter((module) => ["installed", "detected", "healthy"].includes(module.installState)).length}</span> detected
              </div>
            </SimplePanel>
            <SimplePanel className="mt-auto p-4">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-full border border-blue-400 bg-blue-500/10">
                  <HermesMark small />
                </div>
                <div>
                  <div className="font-semibold text-slate-100">Local Operator</div>
                  <div className="text-[12px] text-blue-100/60">Desktop session</div>
                </div>
              </div>
            </SimplePanel>
          </ResizablePane>

          {dashboardActive ? (
            <main
              data-testid="simple-dashboard-grid"
              className="simple-dashboard-grid grid min-w-0 flex-1 grid-cols-12 gap-3 xl:h-full xl:grid-rows-[90px_minmax(0,2fr)_minmax(0,1.12fr)_minmax(0,0.95fr)] xl:overflow-hidden"
            >
              <KpiStrip
                totalPrinters={state.printers.length}
                onlinePrinters={onlinePrinters}
                activePrints={activePrints}
                queuedPrints={queuedPrints}
                successRate={successRate}
                system={state.system}
              />

              <SimplePanel className="col-span-12 min-h-[360px] p-4 xl:col-span-5 xl:h-full xl:min-h-0">
                <PanelHeader title="Printer Fleet" action="View All" onAction={() => openSimpleTab("printers")} />
                <PrinterFleet printers={state.printers} />
              </SimplePanel>

              <SimplePanel className="col-span-12 min-h-[360px] p-4 xl:col-span-7 xl:h-full xl:min-h-0">
                <PanelHeader title="AI Workflow Pipeline" action="View Details" onAction={() => openSimpleTab("autopilot")} />
                <PipelinePanel workflow={activeWorkflow} preview={latestPreview} />
              </SimplePanel>

              <SimplePanel className="col-span-12 min-h-[240px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Active Agents" />
                <ActiveAgents agents={state.agents} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[240px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Agent Activity (Live)" />
                <ActivityPanel events={events} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[240px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="System Resources" />
                <ResourcePanel system={state.system} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[240px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Recent Jobs" action="View All" onAction={() => openSimpleTab("jobs")} />
                <RecentJobs jobs={state.jobs} printers={state.printers} />
              </SimplePanel>

              <SimplePanel className="col-span-12 min-h-[190px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Proof & Verification (Latest)" />
                <ProofPanel proof={state.proof} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[190px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="System Logs (Latest)" action="View All Logs" onAction={() => openSimpleTab("dashboard")} />
                <LogsPanel logs={state.logs} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[190px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Quick Preview" />
                <PreviewPanel artifact={latestPreview} />
              </SimplePanel>
              <SimplePanel className="col-span-12 min-h-[190px] p-4 sm:col-span-6 xl:col-span-3 xl:h-full xl:min-h-0">
                <PanelHeader title="Notifications" />
                <NotificationsPanel notifications={state.notifications} />
              </SimplePanel>
            </main>
          ) : (
            <main
              data-testid="simple-live-tab-root"
              className="min-h-0 min-w-0 flex-1 overflow-hidden rounded-lg border border-[#1e3854] bg-[#07131f]/88"
            >
              <div className="flex h-12 items-center justify-between border-b border-[#1e3854] px-4">
                <div>
                  <div className="text-[13px] font-bold uppercase tracking-[0.06em] text-white">{activeLabel}</div>
                  <div className="text-[11px] text-blue-100/60">Simple shell · live tab component · backend proof paths</div>
                </div>
                <button type="button" onClick={() => setUiMode("full")} className="rounded border border-slate-600 px-3 py-1 text-[12px] text-blue-100 hover:border-blue-400 hover:text-white">
                  Full
                </button>
              </div>
              <div className="h-[calc(100%-3rem)] overflow-auto p-3">
                {Content ? <Content /> : <EmptyTruth title="Route unavailable" detail="The selected Simple tab is not registered in the live router." />}
              </div>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiStrip({
  totalPrinters,
  onlinePrinters,
  activePrints,
  queuedPrints,
  successRate,
  system,
}: {
  totalPrinters: number;
  onlinePrinters: number;
  activePrints: number;
  queuedPrints: number;
  successRate: number | null;
  system: SystemSnapshot | null;
}) {
  const health = system?.system_status === "OK" ? 100 : system?.system_status === "DEGRADED" ? 75 : system ? 0 : null;
  return (
    <section className="col-span-12 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:h-full xl:grid-cols-5">
      <MetricCard title="Total Printers" value={String(totalPrinters)} detail={`Online: ${onlinePrinters}    Offline: ${Math.max(totalPrinters - onlinePrinters, 0)}`} icon={<Printer size={43} />} data={[totalPrinters]} />
      <MetricCard title="Active Prints" value={String(activePrints)} detail="In Progress" data={[activePrints]} />
      <MetricCard title="Queued Prints" value={String(queuedPrints)} detail="Waiting" amber data={[queuedPrints]} />
      <MetricCard title="Success Rate" value={successRate == null ? "—" : `${successRate}%`} detail="From completed jobs" data={successRate == null ? [] : [successRate]} />
      <MetricCard title="System Health" value={health == null ? "—" : `${health}%`} detail={system?.system_status ?? "Backend unavailable"} icon={<ShieldCheck size={55} />} data={health == null ? [] : [health]} />
    </section>
  );
}

function MetricCard({
  title,
  value,
  detail,
  icon,
  data,
  amber = false,
}: {
  title: string;
  value: string;
  detail: string;
  icon?: ReactNode;
  data: number[];
  amber?: boolean;
}) {
  return (
    <SimplePanel className="h-[122px] p-4 xl:h-full">
      <div className="flex h-full items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[12px] font-semibold uppercase tracking-[0.06em] text-blue-100/80">{title}</div>
          <div className="mt-2 truncate text-[clamp(18px,1.45vw,24px)] font-bold leading-none text-white">{value}</div>
          <div className="mt-2 whitespace-pre-line text-[12px] text-blue-100/70">{detail}</div>
        </div>
        <div className={amber ? "text-amber-400" : "text-green-400"}>
          {icon ?? <MiniSparkline data={data} amber={amber} />}
        </div>
      </div>
    </SimplePanel>
  );
}

function PrinterFleet({ printers }: { printers: PrinterRow[] }) {
  if (printers.length === 0) {
    return <EmptyTruth title="No printers from API" detail="Connect Moonraker printers in Settings." />;
  }
  return (
    <div className="mt-4 min-h-0 flex-1 overflow-auto">
      <table className="w-full min-w-[720px] text-[13px]">
        <thead>
          <tr className="border-b border-slate-700/40 text-left text-[11px] uppercase tracking-[0.06em] text-blue-100/60">
            <th className="w-8 py-2">#</th>
            <th className="py-2">Printer</th>
            <th className="py-2">IP Address</th>
            <th className="py-2">Status</th>
            <th className="py-2">Current Job</th>
            <th className="py-2">Progress</th>
          </tr>
        </thead>
        <tbody>
          {printers.map((printer, index) => (
            <tr key={printer.id} className="border-b border-slate-800/70">
              <td className="py-2 font-mono text-blue-100/80">{index + 1}</td>
              <td className="py-2 font-medium text-white">{printer.name}</td>
              <td className="py-2 font-mono text-blue-100/80">{printer.ip ?? "—"}</td>
              <td className="py-2"><StatusPill status={printer.status} locked={printer.maintenance_flag} /></td>
              <td className="max-w-[180px] truncate py-2 text-blue-100/90">{printer.current_job ?? "—"}</td>
              <td className="py-2"><Progress value={printer.progress ?? 0} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PipelinePanel({ workflow, preview }: { workflow: WorkflowRow | null; preview: Artifact | null }) {
  if (!workflow) {
    return <EmptyTruth title="No active live workflow" detail="Pipeline stages appear after the backend reports an active job or agent workflow." />;
  }
  const stages = workflow.stages?.length
    ? workflow.stages.slice(0, 6).map((stage, index) => ({
      id: stage.id,
      label: stage.label,
      status: stage.status,
      Icon: FALLBACK_PIPELINE[index]?.Icon ?? CircleDot,
    }))
    : FALLBACK_PIPELINE;
  return (
    <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-auto">
      <div className="grid grid-cols-3 items-center gap-2 border-b border-slate-700/50 pb-4 sm:grid-cols-6">
        {stages.map((stage, index) => (
          <div key={stage.id} className="relative flex flex-col items-center gap-2">
            {index > 0 && <span className="absolute right-1/2 top-8 h-px w-full bg-blue-500/70" aria-hidden />}
            <div className={[
              "relative z-10 grid h-16 w-16 place-items-center rounded-full border bg-slate-950/80",
              stage.status === "done" ? "border-green-400 text-green-300 shadow-[0_0_28px_rgba(34,197,94,0.25)]" :
                stage.status === "active" ? "border-blue-400 text-blue-300 shadow-[0_0_28px_rgba(59,130,246,0.25)]" :
                  stage.status === "failed" ? "border-red-400 text-red-300" : "border-slate-600 text-blue-100/70",
            ].join(" ")}>
              <stage.Icon size={31} />
            </div>
            <div className="text-center text-[12px] font-semibold text-slate-100">{stage.label}</div>
            <span className={[
              "rounded px-2 py-0.5 text-[11px]",
              stage.status === "done" ? "bg-green-500/15 text-green-300" :
                stage.status === "active" ? "bg-blue-500/15 text-blue-300" :
                  stage.status === "failed" ? "bg-red-500/15 text-red-300" : "bg-slate-800 text-blue-100/60",
            ].join(" ")}>
              {stage.status}
            </span>
          </div>
        ))}
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 pt-5 xl:grid-cols-[minmax(0,1fr)_minmax(220px,340px)]">
        <div className="min-w-0">
          <div className="mb-4 text-[13px] uppercase tracking-[0.04em] text-blue-100/70">
            Current Project: <span className="text-white">{workflow?.name ?? "No active workflow"}</span>
          </div>
          <ul className="flex flex-col gap-3 text-[12px]">
            {(workflow?.stages ?? []).slice(0, 6).map((stage) => (
              <li key={stage.id} className="flex items-center gap-3 text-blue-100/90">
                <CheckCircle2 size={15} className={stage.status === "failed" ? "text-red-400" : "text-green-400"} />
                <span className="truncate">{stage.label}</span>
                <span className="text-blue-400">{stage.status}</span>
              </li>
            ))}
            {!workflow && <li className="text-blue-100/60">No live workflow events are active.</li>}
          </ul>
        </div>
        <PreviewFrame artifact={preview} />
      </div>
    </div>
  );
}

function ActiveAgents({ agents }: { agents: Agent[] }) {
  if (agents.length === 0) {
    return <EmptyTruth title="No live agents" detail="Agent service returned no personas." />;
  }
  return (
    <ul className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-auto text-[13px]">
      {agents.map((agent) => (
        <li key={agent.id} className="flex items-center gap-3">
          <Bot size={17} className="text-blue-100" />
          <span className="min-w-0 flex-1 truncate text-white">{agent.role}</span>
          <span className={["rounded px-2 py-0.5 text-[11px]", agent.status === "active" ? "bg-green-500/15 text-green-300" : "bg-blue-500/15 text-blue-300"].join(" ")}>
            {agent.status}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ActivityPanel({ events }: { events: EvidenceEvent[] }) {
  if (events.length === 0) {
    return <EmptyTruth title="No stream events" detail="Waiting for the live event stream." />;
  }
  return (
    <ul className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-auto font-mono text-[12px]">
      {events.slice(0, 8).map((event, index) => (
        <li key={`${event.ts_utc}-${index}`} className="grid grid-cols-[58px_1fr] gap-3 text-blue-100/80">
          <span>{timeOnly(event.ts_utc)}</span>
          <span className="truncate"><span className="text-blue-300">{event.source ?? event.type}</span>: {event.message ?? event.type}</span>
        </li>
      ))}
    </ul>
  );
}

function ResourcePanel({ system }: { system: SystemSnapshot | null }) {
  if (!system) {
    return <EmptyTruth title="No system telemetry" detail="System snapshot endpoint is unavailable." />;
  }
  return (
    <div className="mt-3 flex min-h-0 flex-1 flex-col overflow-auto">
      <div className="grid flex-1 grid-cols-3 justify-items-center gap-2">
        <GaugeRing label="CPU Usage" value={system.cpu_pct} color="#3b82f6" />
        <GaugeRing label="RAM Usage" value={system.ram_pct} color="#22c55e" />
        <GaugeRing label="Disk Usage" value={system.disk_pct} color="#fb923c" />
      </div>
      <div className="mt-3 border-t border-slate-700/50 pt-2">
        <div className="mb-1 text-[11px] text-blue-100/60">Network</div>
        <MiniSparkline data={system.network_kbps} />
      </div>
    </div>
  );
}

function RecentJobs({ jobs, printers }: { jobs: Job[]; printers: PrinterRow[] }) {
  if (jobs.length === 0) {
    return <EmptyTruth title="No recent jobs" detail="No jobs have been returned by the queue." />;
  }
  const printerNames = new Map(printers.map((printer) => [printer.id, printer.name]));
  return (
    <ul className="mt-3 flex min-h-0 flex-1 flex-col gap-2 overflow-auto text-[13px]">
      {jobs.slice(0, 7).map((job) => (
        <li key={job.id} className="grid grid-cols-[minmax(0,1fr)_minmax(54px,84px)_minmax(78px,96px)] items-center gap-2">
          <span className="truncate font-medium text-white">{job.name}</span>
          <span className="truncate text-blue-100/70">{job.printer_id ? printerNames.get(job.printer_id) ?? job.printer_id : "—"}</span>
          <Progress value={job.progress} done={job.status === "completed"} />
        </li>
      ))}
    </ul>
  );
}

function ProofPanel({ proof }: { proof: ProofBundle | null }) {
  if (!proof) {
    return <EmptyTruth title="No proof bundle" detail="No latest proof bundle was returned." />;
  }
  return (
    <div className="mt-3 flex min-h-0 flex-1 items-center gap-4 overflow-auto">
      <ShieldCheck size={58} className={proof.verdict === "verified" ? "text-green-400" : "text-amber-400"} />
      <div className="min-w-0">
        <div className={["text-[22px] font-black uppercase tracking-[0.04em]", proof.verdict === "verified" ? "text-green-400" : "text-amber-300"].join(" ")}>
          {proof.verdict}
        </div>
        <div className="mt-2 text-[12px] text-blue-100/80">Bundle: <span className="font-mono">{proof.id}</span></div>
        <div className="text-[12px] text-blue-100/60">{proof.gates.filter((gate) => gate.verdict === "pass").length}/{proof.gates.length} gates passed</div>
      </div>
    </div>
  );
}

function LogsPanel({ logs }: { logs: LogEntry[] }) {
  if (logs.length === 0) {
    return <EmptyTruth title="No logs" detail="No log entries returned." />;
  }
  return (
    <ul className="mt-3 flex min-h-0 flex-1 flex-col gap-1.5 overflow-auto font-mono text-[12px]">
      {logs.slice(0, 6).map((log) => (
        <li key={`${log.ts_utc}-${log.message}`} className="grid grid-cols-[58px_48px_1fr] gap-2">
          <span className="text-blue-100/60">{timeOnly(log.ts_utc)}</span>
          <span className={log.level === "error" ? "text-red-400" : log.level === "warn" ? "text-amber-400" : "text-green-400"}>{log.level.toUpperCase()}</span>
          <span className="truncate text-blue-100/90">{log.message}</span>
        </li>
      ))}
    </ul>
  );
}

function PreviewPanel({ artifact }: { artifact: Artifact | null }) {
  return (
    <div className="mt-3 min-h-0 flex-1 overflow-hidden rounded-md border border-blue-500/40 bg-slate-950">
      <PreviewFrame artifact={artifact} />
    </div>
  );
}

function NotificationsPanel({ notifications }: { notifications: Notification[] }) {
  if (notifications.length === 0) {
    return <EmptyTruth title="No notifications" detail="Notification inbox is empty." />;
  }
  return (
    <ul className="mt-3 flex min-h-0 flex-1 flex-col gap-3 overflow-auto text-[13px]">
      {notifications.slice(0, 4).map((notification) => (
        <li key={notification.id} className="grid grid-cols-[18px_1fr_52px] items-center gap-3">
          <CircleDot size={14} className={notification.severity === "error" ? "text-red-400" : notification.severity === "warn" ? "text-amber-400" : notification.severity === "success" ? "text-green-400" : "text-blue-400"} />
          <span className="truncate text-blue-100/90">{notification.title}</span>
          <span className="text-right text-[11px] text-blue-100/50">{timeOnly(notification.ts_utc)}</span>
        </li>
      ))}
    </ul>
  );
}

function PreviewFrame({ artifact }: { artifact: Artifact | null }) {
  if (!artifact) {
    return (
      <div className="grid h-full min-h-[72px] place-items-center bg-[linear-gradient(135deg,rgba(15,23,42,0.9),rgba(2,6,23,0.9))] text-center text-[12px] text-blue-100/60">
        <div>
          <Box className="mx-auto mb-2 text-blue-300/60" size={34} />
          No live preview artifact
        </div>
      </div>
    );
  }
  return <img src={artifact.downloadUrl} alt={artifact.name} className="h-full w-full object-cover" />;
}

function SimplePanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`flex min-h-0 flex-col overflow-hidden rounded-lg border border-[#1e3854] bg-[#07131f]/88 shadow-[inset_0_1px_0_rgba(148,163,184,0.06),0_0_28px_rgba(15,23,42,0.25)] ${className}`}>
      {children}
    </section>
  );
}

function PanelHeader({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return (
    <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-700/50 pb-3">
      <h2 className="text-[14px] font-bold uppercase tracking-[0.04em] text-white">{title}</h2>
      {action && (
        <button type="button" onClick={onAction} className="rounded border border-slate-600 px-3 py-1 text-[12px] text-blue-100 hover:border-blue-400 hover:text-white">
          {action}
        </button>
      )}
    </div>
  );
}

function TopStatus({ system }: { system: SystemSnapshot | null }) {
  const online = system?.system_status === "OK";
  return (
    <div className="flex items-center gap-3 rounded-md border border-slate-700/80 bg-slate-900/70 px-4 py-3 text-[13px]">
      <span>System Status</span>
      <span className={["rounded-md px-2 py-1 text-[12px] font-bold", online ? "bg-green-500/20 text-green-300" : "bg-amber-500/20 text-amber-300"].join(" ")}>
        {online ? "ONLINE" : system?.system_status ?? "UNAVAILABLE"}
      </span>
    </div>
  );
}

function StatusPill({ status, locked }: { status: PrinterStatus; locked: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-semibold ${PRINTER_TONE[status]}`}>
      <CircleDot size={10} />
      {locked ? "Locked" : status.replace("_", " ")}
    </span>
  );
}

function Progress({ value, done = false }: { value: number; done?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-slate-700">
        <div className={done ? "h-full rounded-full bg-green-400" : "h-full rounded-full bg-green-500"} style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
      </div>
      <span className="w-9 text-right font-mono text-[12px] text-white">{done ? "Done" : `${value}%`}</span>
    </div>
  );
}

function GaugeRing({ label, value, color }: { label: string; value: number; color: string }) {
  const degrees = Math.max(0, Math.min(value, 100)) * 3.6;
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div className="text-[11px] text-blue-100/70">{label}</div>
      <div className="grid h-16 w-16 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${degrees}deg, #1e293b ${degrees}deg)` }}>
        <div className="grid h-12 w-12 place-items-center rounded-full bg-[#07131f] text-[15px] font-semibold text-white">{value}%</div>
      </div>
    </div>
  );
}

function MiniSparkline({ data, amber = false }: { data: number[]; amber?: boolean }) {
  const points = useMemo(() => sparkPoints(data), [data]);
  const stroke = amber ? "#f59e0b" : "#22c55e";
  return (
    <svg viewBox="0 0 120 44" className="h-12 w-32">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function sparkPoints(data: number[]): string {
  const values = data.length > 1 ? data : [0, data[0] ?? 0, data[0] ?? 0];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values.map((value, index) => {
    const x = (index / Math.max(values.length - 1, 1)) * 120;
    const y = 40 - ((value - min) / span) * 32;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function IconShell({ children, title, onClick }: { children: ReactNode; title: string; onClick: () => void }) {
  return (
    <button type="button" title={title} onClick={onClick} className="grid h-11 w-11 place-items-center rounded-md text-blue-100 hover:bg-slate-800/70 hover:text-white">
      {children}
    </button>
  );
}

function HermesMark({ small = false }: { small?: boolean }) {
  const size = small ? 28 : 46;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <path d="M32 8 18 18l7 7 7-8 7 8 7-7L32 8Z" fill="#2563eb" />
      <path d="M13 17 4 13l8 16 14 7-2-10-11-9Z" fill="#38bdf8" />
      <path d="M51 17 60 13l-8 16-14 7 2-10 11-9Z" fill="#1d4ed8" />
      <path d="M29 25h6v28l-3 4-3-4V25Z" fill="#93c5fd" />
      <path d="M20 39 6 31l7 17 14 7-7-16ZM44 39l14-8-7 17-14 7 7-16Z" fill="#0ea5e9" />
    </svg>
  );
}

function EmptyTruth({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex min-h-[72px] flex-1 items-center justify-center text-center">
      <div>
        <div className="font-semibold text-white">{title}</div>
        <div className="mt-1 max-w-[260px] text-[12px] text-blue-100/60">{detail}</div>
      </div>
    </div>
  );
}

function formatClock(iso?: string): string {
  if (!iso) return "--:--:--";
  const time = iso.split("T")[1] ?? "";
  return time.slice(0, 8) || "--:--:--";
}

function timeOnly(iso: string): string {
  return iso.split("T")[1]?.slice(0, 8) ?? "";
}
