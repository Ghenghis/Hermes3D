/**
 * Dashboard tab — Phase 2 Tasks 19-26 (CP4 correction pass).
 *
 * Faithful recreation of the dense dark layout in `Hermes3D.png`:
 *
 *   Row 1   5 KPI cards   Total Printers · Active Prints · Queued · Success · Health
 *   Row 2   Fleet (col-7) | Pipeline + preview (col-5)
 *   Row 3   Active Agents | Agent Activity (Live) | System Resources | Recent Jobs
 *   Row 4   Proof & Verification | System Logs | Quick Preview | Notifications
 *   Row 5   Dimensional Truth Engine (compact strip)
 *
 * Renders live API snapshots through `AdapterAPI`.
 */
import {
  Activity,
  AlertTriangle,
  Box,
  Check,
  CheckCircle2,
  CircleDot,
  ExternalLink,
  Info,
  Layers,
  ListOrdered,
  Printer as PrinterIcon,
  ShieldCheck,
  Sliders,
  Sparkles,
  XCircle,
} from "lucide-react";
import { Panel } from "../components/layout/Panel";
import { WhileAwayBanner } from "../components/dashboard/WhileAwayBanner";
import { KpiCard } from "../components/cards/KpiCard";
import { ResourceGauge } from "../components/charts/ResourceGauge";
import { Sparkline } from "../components/charts/Sparkline";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { ProofChip } from "../components/badges/ProofChip";
import { useStore } from "../app/store";
import { adapters } from "../api/adapters";
import type { Printer, PrinterDataSource, PrinterStatus } from "../types/printer";
import type { Job } from "../types/job";
import type { Agent } from "../types/agent";
import type { LogEntry, LogLevel } from "../types/log";
import type { Notification, NotificationSeverity } from "../types/notification";
import type { Workflow } from "../types/workflow";
import type { ProofBundle } from "../types/proof";
import type { SystemSnapshot } from "../types/system";
import type { DimensionalAccuracyReport } from "../types/dimensional";
import { tokens } from "../styles/tokens";
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const PRINTER_TONE: Record<PrinterStatus, StatusTone> = {
  online: "green",
  active: "green",
  printing: "cyan",
  paused: "amber",
  maintenance: "amber",
  offline: "muted",
  error: "red",
};

const PRINTER_LABEL: Record<PrinterStatus, string> = {
  online: "Online",
  active: "Active",
  printing: "Printing",
  paused: "Paused",
  maintenance: "Maint.",
  offline: "Offline",
  error: "Error",
};

const JOB_TONE: Record<Job["status"], StatusTone> = {
  queued: "muted",
  printing: "cyan",
  completed: "green",
  failed: "red",
  cancelled: "muted",
  rolled_back: "amber",
};

const LOG_TONE: Record<LogLevel, { dot: string; text: string }> = {
  info:  { dot: "bg-accent-cyan",  text: "text-accent-cyan" },
  warn:  { dot: "bg-accent-amber", text: "text-accent-amber" },
  error: { dot: "bg-accent-red",   text: "text-accent-red" },
  debug: { dot: "bg-muted",        text: "text-muted" },
};

const NOTIF_VISUAL: Record<NotificationSeverity, { Icon: typeof Info; tone: string }> = {
  info:    { Icon: Info,           tone: "text-accent-cyan" },
  success: { Icon: CheckCircle2,   tone: "text-accent-green" },
  warn:    { Icon: AlertTriangle,  tone: "text-accent-amber" },
  error:   { Icon: XCircle,        tone: "text-accent-red" },
};

type DashboardPipelineStage = {
  id: string;
  label: string;
  Icon: typeof Sparkles;
  status: "complete" | "active" | "pending" | "failed";
  detail?: string;
};

/** Icon-only lookup for pipeline stage nodes — status comes from live API, never from this table. */
const PIPELINE_STAGE_ICONS: Array<{ id: string; label: string; Icon: typeof Sparkles }> = [
  { id: "prompt",    label: "Prompt / Input", Icon: Sparkles    },
  { id: "gen3d",     label: "3D Generation",  Icon: Box         },
  { id: "blender",   label: "Blender MCP",    Icon: Layers      },
  { id: "validate",  label: "Validation",     Icon: ShieldCheck },
  { id: "slice",     label: "Slicing",        Icon: Sliders     },
  { id: "print",     label: "Print",          Icon: PrinterIcon },
];

type EvidenceEvent = {
  type: string;
  ts_utc: string;
  source?: string;
  message?: string;
};

export function Dashboard() {
  const setActiveTabId = useStore((s) => s.setActiveTabId);
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [latestProof, setLatestProof] = useState<ProofBundle | null>(null);
  const [systemSnapshot, setSystemSnapshot] = useState<SystemSnapshot | null>(null);
  const [dimensionalReports, setDimensionalReports] = useState<DimensionalAccuracyReport[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [events, setEvents] = useState<EvidenceEvent[]>([]);
  const [eventStreamStatus, setEventStreamStatus] = useState<"connecting" | "streaming" | "unreachable">("connecting");
  useEffect(() => {
    let mounted = true;
    void Promise.allSettled([
      adapters.getPrinters(),
      adapters.getJobs("printing,queued,running"),
      adapters.getAgents(),
      adapters.getActiveWorkflows(),
      adapters.getLatestProofBundle(),
      adapters.getSystemSnapshot(),
      adapters.getDimensionalReports(),
      adapters.getLogs(),
      adapters.getNotifications(),
    ]).then((results) => {
      if (!mounted) {
        return;
      }
      setSettledValue(results[0], setPrinters);
      setSettledValue(results[1], setJobs);
      setSettledValue(results[2], setAgents);
      setSettledValue(results[3], setWorkflows);
      setSettledValue(results[4], setLatestProof);
      setSettledValue(results[5], setSystemSnapshot);
      setSettledValue(results[6], setDimensionalReports);
      setSettledValue(results[7], setLogs);
      setSettledValue(results[8], setNotifications);
    });
    return () => {
      mounted = false;
    };
  }, []);
  useEffect(() => {
    const stream = new EventSource(`${LIVE_BASE_URL}/api/events/stream`);
    stream.onopen = () => setEventStreamStatus("streaming");
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
    stream.onerror = () => setEventStreamStatus("unreachable");
    return () => stream.close();
  }, []);

  const totalPrinters = printers.length;
  const onlinePrinters = printers.filter((p) => p.status !== "offline").length;
  const offlinePrinters = totalPrinters - onlinePrinters;
  const activePrints = printers.filter((p) => p.status === "printing").length;
  const queuedJobs = jobs.filter((j) => j.status === "queued").length;
  const completedJobs = jobs.filter((j) => j.status === "completed").length;
  const failedJobs = jobs.filter((j) => j.status === "failed").length;
  const successRate = completedJobs + failedJobs > 0
    ? Math.round((completedJobs / (completedJobs + failedJobs)) * 1000) / 10
    : null;
  const activeWorkflow = workflows.find((w) => w.status === "active") ?? workflows[0] ?? null;
  const activeAgents = agents.filter((a) => a.status === "active").length;
  const unreadNotifications = notifications.filter((n) => !n.read).length;
  const systemTone: StatusTone = systemSnapshot
    ? (systemSnapshot.system_status === "OK" ? "green" : systemSnapshot.system_status === "DEGRADED" ? "amber" : "red")
    : "muted";
  const systemHealthPct = systemSnapshot
    ? (systemSnapshot.system_status === "OK" ? 100 : systemSnapshot.system_status === "DEGRADED" ? 75 : 0)
    : null;

  return (
    <div className="dashboard-grid" data-testid="dashboard-root">
      <WhileAwayBanner notifications={notifications} />

      {/* ── Row 1 ─ 5 KPI cards ──────────────────────────────────────────── */}
      <div className="col-span-12 grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <KpiCard
          label="Total Printers"
          value={totalPrinters}
          delta={{ value: `${onlinePrinters} online · ${offlinePrinters} offline`, tone: "green" }}
          icon={<PrinterIcon size={20} />}
          chart={<Sparkline data={flatSparkline(totalPrinters)} />}
        />
        <KpiCard
          label="Active Prints"
          value={activePrints}
          delta={{ value: "running now", tone: "muted" }}
          icon={<Activity size={20} />}
          chart={<Sparkline data={flatSparkline(activePrints)} color={tokens.chartColors.cyan} />}
        />
        <KpiCard
          label="Queued Prints"
          value={queuedJobs}
          delta={{ value: "in print queue", tone: "muted" }}
          icon={<ListOrdered size={20} />}
          chart={<Sparkline data={flatSparkline(queuedJobs)} color={tokens.chartColors.amber} />}
        />
        <KpiCard
          label="Success Rate"
          value={successRate == null ? "—" : `${successRate}%`}
          delta={{ value: successRate == null ? "no completed jobs" : "from live jobs", tone: successRate == null ? "muted" : "green" }}
          icon={<Sparkles size={20} />}
          chart={successRate == null ? undefined : <Sparkline data={flatSparkline(successRate)} color={tokens.chartColors.green} />}
        />
        <KpiCard
          label="System Health"
          value={systemSnapshot?.system_status ?? "Unavailable"}
          delta={{ value: systemSnapshot?.gpu_name ?? "backend unavailable", tone: systemTone }}
          icon={<ShieldCheck size={20} />}
          chart={systemHealthPct == null ? undefined : <Sparkline data={flatSparkline(systemHealthPct)} color={tokens.chartColors.green} />}
        />
      </div>

      {/* ── Row 2 ─ Printer Fleet (col-7) + Workflow Pipeline + Preview (col-5) ─ */}
      <div className="col-span-12 min-h-0 lg:col-span-7">
        <Panel
          id="dashboard.fleet"
          title="PRINTER FLEET"
          status={{ tone: "green", label: `${totalPrinters} units` }}
          headerExtra={
            <button
              type="button"
              onClick={() => setActiveTabId("printers")}
              className="text-accent-cyan hover:text-accent-blue text-xs font-medium flex items-center gap-1 px-2 py-0.5 rounded hover:bg-surface2 transition-colors"
            >
              View All <ExternalLink size={11} />
            </button>
          }
          dense
          className="h-full min-h-0"
        >
          <FleetTable printers={printers} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 lg:col-span-5">
        <Panel
          id="dashboard.pipeline"
          title="AI WORKFLOW PIPELINE"
          status={{ tone: activeWorkflow ? "cyan" : "muted", label: activeWorkflow ? "active" : "none" }}
          headerExtra={
            <span className="text-muted text-xs truncate max-w-[180px]">{activeWorkflow?.name ?? "No active workflow"}</span>
          }
          dense
          className="h-full min-h-0"
        >
          <PipelinePanel workflow={activeWorkflow} />
        </Panel>
      </div>

      {/* ── Row 3 ─ Active Agents | Agent Activity | Resources | Recent Jobs ─ */}
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.agents.active"
          title="ACTIVE AGENTS"
          status={{
            tone: "green",
            label: `${activeAgents}/${agents.length}`,
          }}
          dense
          className="h-full min-h-0"
        >
          <ActiveAgentsList agents={agents} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.agents.activity"
          title="AGENT ACTIVITY (LIVE)"
          status={{ tone: eventStreamStatus === "unreachable" ? "amber" : "cyan", label: eventStreamStatus }}
          dense
          className="h-full min-h-0"
        >
          <AgentActivityLog events={events} streamStatus={eventStreamStatus} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.resources"
          title="SYSTEM RESOURCES"
          status={{ tone: systemTone, label: systemSnapshot?.system_status ?? "unavailable" }}
          dense
          className="h-full min-h-0"
        >
          <ResourcePanel snapshot={systemSnapshot} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.jobs"
          title="RECENT JOBS"
          status={{ tone: "muted", label: `${jobs.length} total` }}
          dense
          className="h-full min-h-0"
        >
          <RecentJobs printers={printers} jobs={jobs} />
        </Panel>
      </div>

      {/* ── Row 4 ─ Proof | Logs | Quick Preview | Notifications ─────────── */}
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.proof"
          title="PROOF & VERIFICATION"
          status={{ tone: latestProof ? "green" : "muted", label: latestProof ? "LATEST" : "none" }}
          headerExtra={<ProofChip status={latestProof?.verdict === "verified" ? "verified" : "pending"} />}
          dense
          className="h-full min-h-0"
        >
          <ProofPanel bundle={latestProof} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.logs"
          title="SYSTEM LOGS"
          status={{ tone: "cyan", label: "LATEST" }}
          headerExtra={<span className="text-muted text-xs">{logs.length} recent</span>}
          dense
          className="h-full min-h-0"
        >
          <LogsPanel logs={logs} />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.preview"
          title="QUICK PREVIEW"
          status={{ tone: "muted", label: "STL · 3MF" }}
          dense
          className="h-full min-h-0"
        >
          <QuickPreview />
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.notifications"
          title="NOTIFICATIONS"
          status={{
            tone: unreadNotifications > 0 ? "amber" : "muted",
            label: `${unreadNotifications} unread`,
          }}
          dense
          className="h-full min-h-0"
        >
          <NotificationsPanel notifications={notifications} />
        </Panel>
      </div>

      <div className="sr-only" aria-live="polite">
        Dimensional Truth Engine reports loaded: {dimensionalReports.length}
      </div>
    </div>
  );
}

function setSettledValue<T>(
  result: PromiseSettledResult<T>,
  setter: Dispatch<SetStateAction<T>>,
) {
  if (result.status === "fulfilled") {
    setter(result.value);
  }
}

function flatSparkline(value: number): number[] {
  return [value, value, value];
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Printer Fleet — numbered, IP, progress bars                         *
 * ────────────────────────────────────────────────────────────────────────── */
function FleetTable({ printers }: { printers: Printer[] }) {
  if (printers.length === 0) {
    return <EmptyPanelState title="No live printers" detail="The printer API returned an empty fleet." />;
  }

  return (
    <div className="w-full overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-surface z-10">
          <tr className="text-muted text-[10px] uppercase tracking-wide border-b border-border">
            <th className="text-right py-1.5 px-2 font-medium w-8">#</th>
            <th className="text-left py-1.5 px-2 font-medium">Printer</th>
            <th className="text-left py-1.5 px-2 font-medium w-28">IP Address</th>
            <th className="text-left py-1.5 px-2 font-medium w-24">Status</th>
            <th className="text-left py-1.5 px-2 font-medium">Current Job</th>
            <th className="text-left py-1.5 px-2 font-medium w-32">Progress</th>
          </tr>
        </thead>
        <tbody>
          {printers.map((p, i) => (
            <tr
              key={p.id}
              className="border-b border-border/30 hover:bg-surface2/50 transition-colors"
              data-source={p.data_source}
            >
              <td className="py-1.5 px-2 text-right text-muted font-mono tabular-nums">{i + 1}</td>
              <td className="py-1.5 px-2">
                <div className="flex flex-col leading-tight">
                  <span className="text-fg font-medium">{p.name}</span>
                  <span className="text-muted text-[10px] flex items-center gap-1">
                    {p.model}
                    <DataSourceChip source={p.data_source} />
                  </span>
                </div>
              </td>
              <td className="py-1.5 px-2 text-muted font-mono text-[11px]">{p.ip ?? "—"}</td>
              <td className="py-1.5 px-2">
                <StatusBadge tone={PRINTER_TONE[p.status]} label={PRINTER_LABEL[p.status]} />
              </td>
              <td className="py-1.5 px-2">
                <span className="text-fg text-[11px] truncate block max-w-[160px]">
                  {p.current_job ?? <span className="text-muted">—</span>}
                </span>
              </td>
              <td className="py-1.5 px-2">
                <FleetProgressBar value={p.progress} status={p.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DataSourceChip({ source }: { source: PrinterDataSource }) {
  const tone = {
    live: "border-accent-green/50 text-accent-green",
    degraded: "border-accent-amber/50 text-accent-amber",
    error: "border-accent-red/50 text-accent-red",
    policy: "border-amber-500/50 text-amber-300",
    config: "border-border text-muted",
  }[source] ?? "border-border text-muted";
  return (
    <span
      data-source={source}
      className={`px-1 py-px rounded border text-[8px] uppercase leading-none ${tone}`}
      title={`data source: ${source}`}
    >
      {source}
    </span>
  );
}

function FleetProgressBar({ value, status }: { value: number | null; status: PrinterStatus }) {
  if (value == null) {
    return <span className="text-muted text-[11px]">—</span>;
  }
  const tone =
    status === "printing" ? "bg-accent-cyan" : status === "online" || status === "active" ? "bg-accent-green" : "bg-muted";
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-1.5 bg-surface2 rounded-full overflow-hidden">
        <div className={`h-full ${tone} rounded-full`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-fg text-[11px] font-mono tabular-nums w-8 text-right">{value}%</span>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: AI Workflow Pipeline — large icons + project log + preview          *
 * ────────────────────────────────────────────────────────────────────────── */
function PipelinePanel({ workflow }: { workflow: Workflow | null }) {
  if (!workflow) {
    return <EmptyPanelState title="No active workflow" detail="Live workflows will appear here after the backend starts one." />;
  }

  const stages = workflow.stages.length > 0
    ? workflow.stages.map((stage, index): DashboardPipelineStage => ({
      id: stage.id,
      label: stage.label,
      Icon: PIPELINE_STAGE_ICONS[index]?.Icon ?? CircleDot,
      status: stage.status === "done" ? "complete" : stage.status === "active" ? "active" : stage.status === "failed" ? "failed" : "pending",
      detail: stage.detail,
    }))
    : [];
  const stageSummary = workflow.stages.length > 0
    ? `stage ${Math.min(workflow.active_stage + 1, workflow.stages.length)}/${workflow.stages.length}`
    : "stage telemetry unavailable";
  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-3 xl:grid-cols-3">
      <div className="flex min-w-0 flex-col gap-3 xl:col-span-2">
        <div className="min-h-[72px] rounded-md border border-border/60 bg-bg/20 p-2">
          {stages.length > 0 ? (
            <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1">
              {stages.map((stage, i) => (
                <PipelineStageNode key={stage.id} stage={stage} isLast={i === stages.length - 1} />
              ))}
            </div>
          ) : (
            <EmptyPanelState title="No stage telemetry" detail="This live workflow has not reported stage events yet." />
          )}
        </div>
        <div className="border-t border-border pt-2">
          <div className="text-muted text-[10px] uppercase tracking-wide mb-1">Current Job</div>
          <div className="text-fg text-xs font-medium truncate">{workflow.name}</div>
          <div className="h-1.5 bg-surface2 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-accent-cyan rounded-full"
              style={{ width: `${workflow.progress}%` }}
            />
          </div>
          <div className="text-muted text-[10px] mt-1 font-mono tabular-nums">
            {workflow.progress}% · {stageSummary}
          </div>
        </div>
        <div className="border-t border-border pt-2 flex-1 overflow-auto min-h-0">
          <div className="text-muted text-[10px] uppercase tracking-wide mb-1">Stage Status</div>
          {stages.length > 0 ? (
            <ul className="flex flex-col gap-1 text-[11px]">
              {stages.map((stage) => (
                <StageStatusRow key={stage.id} stage={stage} />
              ))}
            </ul>
          ) : (
            <EmptyPanelState title="No stage rows" detail="The workflow API returned no stage records for this job." />
          )}
        </div>
      </div>
      <div className="min-w-0 rounded-md border border-border/60 bg-bg/20">
        <EmptyPanelState title="No workflow preview" detail="No live preview artifact is attached to this workflow." />
      </div>
    </div>
  );
}

function PipelineStageNode({
  stage,
  isLast,
}: {
  stage: DashboardPipelineStage;
  isLast: boolean;
}) {
  const visual =
    stage.status === "complete"
      ? { ring: "ring-accent-green/70", text: "text-accent-green", Indicator: Check }
      : stage.status === "active"
        ? { ring: "ring-accent-cyan/80 shadow-glow", text: "text-accent-cyan", Indicator: CircleDot }
        : stage.status === "failed"
          ? { ring: "ring-accent-red/70", text: "text-accent-red", Indicator: CircleDot }
          : { ring: "ring-border", text: "text-muted", Indicator: CircleDot };
  return (
    <div className="flex flex-col items-center gap-1 min-w-0 flex-1 relative">
      <div
        className={`h-10 w-10 rounded-full bg-surface2 flex items-center justify-center ring-2 ${visual.ring}`}
      >
        <stage.Icon size={18} className={visual.text} />
      </div>
      <div className="text-fg text-[10px] font-medium leading-tight text-center truncate w-full px-0.5">
        {stage.label}
      </div>
      <div className={`text-[9px] uppercase tracking-wide ${visual.text}`}>{stage.status}</div>
      {!isLast && (
        <div
          className={`absolute top-5 left-1/2 right-[-50%] h-px ${
            stage.status === "complete" ? "bg-accent-green/50" : stage.status === "active" ? "bg-accent-cyan/50" : "bg-border"
          }`}
          aria-hidden
        />
      )}
    </div>
  );
}

function StageStatusRow({ stage }: { stage: DashboardPipelineStage }) {
  const dotClass = {
    complete: "bg-accent-green",
    active: "bg-accent-cyan",
    failed: "bg-accent-red",
    pending: "bg-muted",
  }[stage.status];
  const textClass = {
    complete: "text-accent-green",
    active: "text-accent-cyan",
    failed: "text-accent-red",
    pending: "text-muted",
  }[stage.status];
  return (
    <li className="flex items-center gap-2">
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} aria-hidden />
      <span className="text-fg truncate flex-1">{stage.label}</span>
      {stage.detail && <span className="text-muted truncate max-w-[120px]">{stage.detail}</span>}
      <span className={`font-mono shrink-0 ${textClass}`}>{stage.status}</span>
    </li>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Active Agents (left of mid row)                                     *
 * ────────────────────────────────────────────────────────────────────────── */
function ActiveAgentsList({ agents }: { agents: Agent[] }) {
  if (agents.length === 0) {
    return <EmptyPanelState title="No live agents" detail="The agents API returned no registered agents." />;
  }

  return (
    <ul className="flex flex-col gap-1 h-full overflow-auto">
      {agents.map((a) => (
        <li key={a.id} className="flex items-center gap-2 text-xs py-1">
          <span
            className={[
              "h-2 w-2 rounded-full shrink-0",
              a.status === "active"
                ? "bg-accent-green"
                : a.status === "paused"
                  ? "bg-accent-amber"
                  : a.status === "error"
                    ? "bg-accent-red"
                    : "bg-muted",
            ].join(" ")}
            aria-hidden
          />
          <span className="text-fg flex-1 truncate">{a.role}</span>
          <span className="text-muted text-[10px] uppercase tracking-wide shrink-0">
            {a.status}
          </span>
          <span className="text-muted text-[10px] font-mono w-5 text-right shrink-0">
            {a.task_count}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Agent Activity (Live)                                               *
 * ────────────────────────────────────────────────────────────────────────── */
function AgentActivityLog({ events, streamStatus }: { events: EvidenceEvent[]; streamStatus: "connecting" | "streaming" | "unreachable" }) {
  if (events.length > 0) {
    return (
      <ul className="flex flex-col gap-1.5 h-full overflow-auto">
        {events.map((event, index) => (
          <li key={`${event.ts_utc}-${index}`} className="flex items-start gap-2 text-xs">
            <StatusBadge tone="cyan" label={event.type} />
            <div className="flex min-w-0 flex-1 flex-col leading-tight">
              <span className="truncate font-medium text-fg">{event.message ?? event.source ?? "Evidence event"}</span>
              <span className="truncate font-mono text-[10px] text-muted">
                {event.ts_utc.split("T")[1]?.slice(0, 8) ?? ""}Z · live SSE
              </span>
            </div>
          </li>
        ))}
      </ul>
    );
  }
  if (streamStatus === "unreachable") {
    return <EmptyPanelState title="Event stream unavailable" detail="Backend SSE stream is unreachable; live activity is blocked." />;
  }
  return <EmptyPanelState title="No live activity" detail={streamStatus === "connecting" ? "Connecting to backend SSE events." : "Waiting for backend SSE events."} />;
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: System Resources — CPU/RAM/Disk gauges + network sparkline          *
 * ────────────────────────────────────────────────────────────────────────── */
function ResourcePanel({ snapshot }: { snapshot: SystemSnapshot | null }) {
  if (!snapshot) {
    return <EmptyPanelState title="System telemetry unavailable" detail="The system snapshot API did not return data." />;
  }

  const network = snapshot.network_kbps.length > 0 ? snapshot.network_kbps : [0];
  return (
    <div className="flex flex-col h-full gap-2">
      <div className="grid grid-cols-3 gap-1 flex-1">
        <ResourceGauge value={snapshot.cpu_pct} label="CPU" />
        <ResourceGauge value={snapshot.ram_pct} label="RAM" />
        <ResourceGauge value={snapshot.disk_pct} label="DISK" />
      </div>
      <div className="border-t border-border pt-1.5">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-muted">
          <span>Network</span>
          <span className="font-mono tabular-nums text-fg">
            {network[network.length - 1]} kbps
          </span>
        </div>
        <div className="h-8">
          <Sparkline data={network} color={tokens.chartColors.cyan} />
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Recent Jobs — name + printer + progress + done/check                *
 * ────────────────────────────────────────────────────────────────────────── */
function RecentJobs({ printers, jobs }: { printers: Printer[]; jobs: Job[] }) {
  const visibleJobs = jobs.slice(0, 5);
  if (visibleJobs.length === 0) {
    return <EmptyPanelState title="No recent jobs" detail="The jobs API returned no queued or printing jobs." />;
  }

  const printerNameById = new Map(printers.map((p) => [p.id, p.name]));
  return (
    <ul className="flex flex-col gap-1.5 h-full overflow-auto">
      {visibleJobs.map((j) => {
        const isDone = j.status === "completed";
        const tone = JOB_TONE[j.status];
        return (
          <li
            key={j.id}
            className="flex flex-col gap-1 text-xs py-1 border-b border-border/30 last:border-0"
          >
            <div className="flex items-center gap-2 min-w-0">
              {isDone ? (
                <CheckCircle2 size={13} className="text-accent-green shrink-0" />
              ) : (
                <span
                  className={[
                    "h-1.5 w-1.5 rounded-full shrink-0",
                    tone === "cyan" ? "bg-accent-cyan" : tone === "red" ? "bg-accent-red" : "bg-muted",
                  ].join(" ")}
                  aria-hidden
                />
              )}
              <span className="text-fg truncate flex-1 font-mono text-[11px]">{j.name}</span>
              <span className="text-muted text-[10px] shrink-0">
                {j.printer_id ? printerNameById.get(j.printer_id) ?? j.printer_id : "—"}
              </span>
            </div>
            <div className="flex items-center gap-2 ml-5">
              <div className="flex-1 h-1 bg-surface2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    isDone ? "bg-accent-green" : tone === "cyan" ? "bg-accent-cyan" : tone === "red" ? "bg-accent-red" : "bg-muted"
                  }`}
                  style={{ width: `${j.progress}%` }}
                />
              </div>
              <span className="text-muted text-[10px] font-mono w-8 text-right shrink-0">
                {isDone ? "Done" : `${j.progress}%`}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Proof & Verification (LATEST)                                       *
 * ────────────────────────────────────────────────────────────────────────── */
function ProofPanel({ bundle }: { bundle: ProofBundle | null }) {
  if (!bundle) {
    return <EmptyPanelState title="No proof bundle" detail="The proof API has not returned a latest bundle." />;
  }

  const passCount = bundle.gates.filter((g) => g.verdict === "pass").length;
  return (
    <div className="flex flex-col gap-2 h-full text-xs">
      <div className="flex flex-col leading-tight">
        <span className="text-muted text-[10px] uppercase tracking-wide">Bundle</span>
        <span className="font-mono text-accent-cyan truncate">{bundle.id}</span>
      </div>
      <div className="grid grid-cols-2 gap-1 leading-tight">
        <KV k="Branch" v={<span className="font-mono text-fg text-[11px] truncate block">{bundle.branch}</span>} />
        <KV k="Commit" v={<span className="font-mono text-fg text-[11px]">{bundle.commit.slice(0, 10)}</span>} />
        <KV k="Files" v={<span className="text-fg text-[11px]">{bundle.files_count}</span>} />
        <KV k="Size" v={<span className="text-fg text-[11px]">{(bundle.size_bytes / 1024).toFixed(1)} KB</span>} />
      </div>
      <div className="flex-1 overflow-auto border-t border-border pt-1.5">
        <div className="text-muted text-[10px] uppercase tracking-wide mb-1">
          Gates · {passCount}/{bundle.gates.length} pass
        </div>
        <ul className="flex flex-col gap-0.5">
          {bundle.gates.slice(0, 6).map((g) => (
            <li key={g.layer} className="flex items-center gap-1.5 text-[10px]">
              <span
                className={[
                  "h-1.5 w-1.5 rounded-full shrink-0",
                  g.verdict === "pass"
                    ? "bg-accent-green"
                    : g.verdict === "fail"
                      ? "bg-accent-red"
                      : "bg-muted",
                ].join(" ")}
                aria-hidden
              />
              <span className="text-fg truncate flex-1">{g.layer}</span>
              <span className="text-muted shrink-0">{g.duration_s != null ? `${g.duration_s}s` : "—"}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: System Logs (Latest)                                                *
 * ────────────────────────────────────────────────────────────────────────── */
function LogsPanel({ logs }: { logs: LogEntry[] }) {
  if (logs.length === 0) {
    return <EmptyPanelState title="No live logs" detail="The logs API returned no entries." />;
  }

  return (
    <ul className="flex flex-col gap-1 h-full overflow-auto">
      {logs.map((log, i) => {
        const tone = LOG_TONE[log.level];
        return (
          <li
            key={`${log.ts_utc}-${i}`}
            className="flex items-start gap-1.5 text-[11px] py-0.5 border-b border-border/30 last:border-0"
          >
            <span className={`h-1.5 w-1.5 rounded-full mt-1 shrink-0 ${tone.dot}`} aria-hidden />
            <span className="text-muted font-mono text-[10px] shrink-0 mt-0.5">
              {log.ts_utc.split("T")[1]?.slice(0, 5) ?? ""}
            </span>
            <span className={`uppercase text-[9px] tracking-wide shrink-0 mt-0.5 ${tone.text}`}>
              {log.level}
            </span>
            <span className="text-fg truncate flex-1">{log.message}</span>
          </li>
        );
      })}
    </ul>
  );
}

function QuickPreview() {
  return <EmptyPanelState title="No model preview" detail="No live preview artifact was returned by the backend." />;
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Notifications                                                       *
 * ────────────────────────────────────────────────────────────────────────── */
function NotificationsPanel({ notifications }: { notifications: Notification[] }) {
  if (notifications.length === 0) {
    return <EmptyPanelState title="No notifications" detail="The live notification inbox is empty." />;
  }

  return (
    <ul className="flex flex-col gap-1.5 h-full overflow-auto">
      {notifications.map((n) => {
        const v = NOTIF_VISUAL[n.severity];
        return (
          <li
            key={n.id}
            className={`flex items-start gap-2 text-[11px] p-1.5 rounded ${
              n.read ? "" : "bg-surface2/60 border border-border/60"
            }`}
          >
            <v.Icon size={13} className={`${v.tone} shrink-0 mt-0.5`} />
            <div className="flex flex-col min-w-0 flex-1 leading-tight">
              <span className="text-fg font-medium truncate">{n.title}</span>
              <span className="text-muted truncate">{n.message}</span>
            </div>
            <span className="text-muted font-mono text-[10px] shrink-0 mt-0.5">
              {n.ts_utc.split("T")[1]?.slice(0, 5) ?? ""}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Helpers                                                                    *
 * ────────────────────────────────────────────────────────────────────────── */
function EmptyPanelState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-xs">
      <div className="font-medium text-fg">{title}</div>
      <div className="max-w-[280px] text-muted">{detail}</div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex flex-col min-w-0 leading-tight">
      <span className="text-muted text-[9px] uppercase tracking-wide">{k}</span>
      <span className="text-[11px] truncate">{v}</span>
    </div>
  );
}
