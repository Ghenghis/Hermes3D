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
 * No real APIs, no adapter calls, no subprocesses — every value flows from
 * `src/data/mock/*`. Phase 3 swaps the mock layer behind `AdapterAPI`.
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
import { KpiCard } from "../components/cards/KpiCard";
import { ResourceGauge } from "../components/charts/ResourceGauge";
import { Sparkline } from "../components/charts/Sparkline";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { ProofChip } from "../components/badges/ProofChip";
import { useStore } from "../app/store";
import { MOCK_PRINTERS } from "../data/mock/printers";
import { MOCK_AGENTS } from "../data/mock/agents";
import { MOCK_WORKFLOWS } from "../data/mock/workflows";
import { MOCK_JOBS } from "../data/mock/jobs";
import { LATEST_BUNDLE } from "../data/mock/proof";
import { MOCK_SYSTEM_SNAPSHOT } from "../data/mock/system";
import { MOCK_DIMENSIONAL_REPORTS } from "../data/mock/dimensional";
import { MOCK_LOGS } from "../data/mock/logs";
import { MOCK_NOTIFICATIONS } from "../data/mock/notifications";
import type { PrinterStatus } from "../types/printer";
import type { Job } from "../types/job";
import type { Agent } from "../types/agent";
import type { LogLevel } from "../types/log";
import type { NotificationSeverity } from "../types/notification";
import { tokens } from "../styles/tokens";

const PRINTER_TONE: Record<PrinterStatus, StatusTone> = {
  online: "green",
  printing: "cyan",
  paused: "amber",
  maintenance: "amber",
  offline: "muted",
  error: "red",
};

const PRINTER_LABEL: Record<PrinterStatus, string> = {
  online: "Online",
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
};

const AGENT_TONE: Record<Agent["status"], StatusTone> = {
  active: "green",
  idle: "muted",
  paused: "amber",
  error: "red",
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

const PIPELINE_STAGES: { id: string; label: string; Icon: typeof Sparkles; status: "complete" | "active" | "pending" }[] = [
  { id: "prompt",    label: "Prompt / Input", Icon: Sparkles,      status: "complete" },
  { id: "gen3d",     label: "3D Generation",  Icon: Box,           status: "complete" },
  { id: "blender",   label: "Blender MCP",    Icon: Layers,        status: "complete" },
  { id: "validate",  label: "Validation",     Icon: ShieldCheck,   status: "complete" },
  { id: "slice",     label: "Slicing",        Icon: Sliders,       status: "complete" },
  { id: "print",     label: "Print",          Icon: PrinterIcon,   status: "active" },
];

export function Dashboard() {
  const setActiveTabId = useStore((s) => s.setActiveTabId);

  const totalPrinters = MOCK_PRINTERS.length;
  const onlinePrinters = MOCK_PRINTERS.filter((p) => p.status !== "offline").length;
  const offlinePrinters = totalPrinters - onlinePrinters;
  const activePrints = MOCK_PRINTERS.filter((p) => p.status === "printing").length;
  const queuedJobs = MOCK_JOBS.filter((j) => j.status === "queued").length;
  const sys = MOCK_SYSTEM_SNAPSHOT;
  const activeWorkflow = MOCK_WORKFLOWS.find((w) => w.status === "active") ?? MOCK_WORKFLOWS[0];

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="dashboard-root">
      {/* ── Row 1 ─ 5 KPI cards ──────────────────────────────────────────── */}
      <div className="col-span-12 grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <KpiCard
          label="Total Printers"
          value={totalPrinters}
          delta={{ value: `${onlinePrinters} online · ${offlinePrinters} offline`, tone: "green" }}
          icon={<PrinterIcon size={20} />}
          chart={<Sparkline data={[10, 11, 12, 12, 11, 12, 12]} />}
        />
        <KpiCard
          label="Active Prints"
          value={activePrints}
          delta={{ value: "running now", tone: "muted" }}
          icon={<Activity size={20} />}
          chart={<Sparkline data={[1, 2, 2, 3, 3, 2, activePrints]} color={tokens.chartColors.cyan} />}
        />
        <KpiCard
          label="Queued Prints"
          value={queuedJobs}
          delta={{ value: "in print queue", tone: "muted" }}
          icon={<ListOrdered size={20} />}
          chart={<Sparkline data={[2, 3, 4, 4, 5, 5, queuedJobs]} color={tokens.chartColors.amber} />}
        />
        <KpiCard
          label="Success Rate"
          value="98.2%"
          delta={{ value: "+0.3% vs 24h", tone: "green" }}
          icon={<Sparkles size={20} />}
          chart={
            <Sparkline data={[97.1, 97.4, 97.6, 98.0, 97.9, 98.1, 98.2]} color={tokens.chartColors.green} />
          }
        />
        <KpiCard
          label="System Health"
          value="100%"
          delta={{ value: sys.gpu_name ?? "GPU OK", tone: "green" }}
          icon={<ShieldCheck size={20} />}
          chart={<Sparkline data={[98, 99, 100, 100, 100, 100, 100]} color={tokens.chartColors.green} />}
        />
      </div>

      {/* ── Row 2 ─ Printer Fleet (col-7) + Workflow Pipeline + Preview (col-5) ─ */}
      <div className="col-span-12 lg:col-span-7">
        <Panel
          id="dashboard.fleet"
          title="PRINTER FLEET"
          status={{ tone: "green", label: `${totalPrinters} units` }}
          headerExtra={
            <button
              type="button"
              onClick={() => setActiveTabId("fleet")}
              className="text-accent-cyan hover:text-accent-blue text-xs font-medium flex items-center gap-1 px-2 py-0.5 rounded hover:bg-surface2 transition-colors"
            >
              View All <ExternalLink size={11} />
            </button>
          }
          dense
          className="h-[300px]"
        >
          <FleetTable />
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="dashboard.pipeline"
          title="AI WORKFLOW PIPELINE"
          status={{ tone: "cyan", label: "active" }}
          headerExtra={
            <span className="text-muted text-xs truncate max-w-[180px]">{activeWorkflow.name}</span>
          }
          dense
          className="h-[300px]"
        >
          <PipelinePanel />
        </Panel>
      </div>

      {/* ── Row 3 ─ Active Agents | Agent Activity | Resources | Recent Jobs ─ */}
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.agents.active"
          title="ACTIVE AGENTS"
          status={{
            tone: "green",
            label: `${MOCK_AGENTS.filter((a) => a.status === "active").length}/${MOCK_AGENTS.length}`,
          }}
          dense
          className="h-[230px]"
        >
          <ActiveAgentsList />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.agents.activity"
          title="AGENT ACTIVITY (LIVE)"
          status={{ tone: "cyan", label: "streaming" }}
          dense
          className="h-[230px]"
        >
          <AgentActivityLog />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.resources"
          title="SYSTEM RESOURCES"
          status={{ tone: "green", label: sys.system_status }}
          dense
          className="h-[230px]"
        >
          <ResourcePanel />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.jobs"
          title="RECENT JOBS"
          status={{ tone: "muted", label: `${MOCK_JOBS.length} total` }}
          dense
          className="h-[230px]"
        >
          <RecentJobs />
        </Panel>
      </div>

      {/* ── Row 4 ─ Proof | Logs | Quick Preview | Notifications ─────────── */}
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.proof"
          title="PROOF & VERIFICATION"
          status={{ tone: "green", label: "LATEST" }}
          headerExtra={<ProofChip status={LATEST_BUNDLE.verdict === "verified" ? "verified" : "pending"} />}
          dense
          className="h-[220px]"
        >
          <ProofPanel />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.logs"
          title="SYSTEM LOGS"
          status={{ tone: "cyan", label: "LATEST" }}
          headerExtra={<span className="text-muted text-xs">{MOCK_LOGS.length} recent</span>}
          dense
          className="h-[220px]"
        >
          <LogsPanel />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.preview"
          title="QUICK PREVIEW"
          status={{ tone: "muted", label: "STL · 3MF" }}
          dense
          className="h-[220px]"
        >
          <QuickPreview />
        </Panel>
      </div>
      <div className="col-span-12 sm:col-span-6 lg:col-span-3">
        <Panel
          id="dashboard.notifications"
          title="NOTIFICATIONS"
          status={{
            tone: MOCK_NOTIFICATIONS.some((n) => !n.read) ? "amber" : "muted",
            label: `${MOCK_NOTIFICATIONS.filter((n) => !n.read).length} unread`,
          }}
          dense
          className="h-[220px]"
        >
          <NotificationsPanel />
        </Panel>
      </div>

      {/* ── Row 5 ─ Dimensional Truth Engine (compact strip) ─────────────── */}
      <div className="col-span-12">
        <Panel
          id="dashboard.dimensional"
          title="DIMENSIONAL TRUTH ENGINE"
          status={{ tone: "amber", label: "phase 6 pending" }}
          headerExtra={<span className="text-muted text-xs">UI-standards reservation · live in Phase 6</span>}
          dense
          className="h-[85px]"
        >
          <DimensionalStrip />
        </Panel>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Printer Fleet — numbered, IP, progress bars                         *
 * ────────────────────────────────────────────────────────────────────────── */
function FleetTable() {
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
          {MOCK_PRINTERS.map((p, i) => (
            <tr key={p.id} className="border-b border-border/30 hover:bg-surface2/50 transition-colors">
              <td className="py-1.5 px-2 text-right text-muted font-mono tabular-nums">{i + 1}</td>
              <td className="py-1.5 px-2">
                <div className="flex flex-col leading-tight">
                  <span className="text-fg font-medium">{p.name}</span>
                  <span className="text-muted text-[10px]">{p.model}</span>
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

function FleetProgressBar({ value, status }: { value: number | null; status: PrinterStatus }) {
  if (value == null) {
    return <span className="text-muted text-[11px]">—</span>;
  }
  const tone =
    status === "printing" ? "bg-accent-cyan" : status === "online" ? "bg-accent-green" : "bg-muted";
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
function PipelinePanel() {
  const wf = MOCK_WORKFLOWS.find((w) => w.status === "active") ?? MOCK_WORKFLOWS[0];
  return (
    <div className="grid grid-cols-3 gap-3 h-full">
      <div className="col-span-2 flex flex-col gap-3 min-w-0">
        {/* Stage row with large circular icons */}
        <div className="flex items-center justify-between gap-1">
          {PIPELINE_STAGES.map((stage, i) => (
            <PipelineStageNode key={stage.id} stage={stage} isLast={i === PIPELINE_STAGES.length - 1} />
          ))}
        </div>
        <div className="border-t border-border pt-2">
          <div className="text-muted text-[10px] uppercase tracking-wide mb-1">Current Job</div>
          <div className="text-fg text-xs font-medium truncate">{wf.name}</div>
          <div className="h-1.5 bg-surface2 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-accent-cyan rounded-full"
              style={{ width: `${wf.progress}%` }}
            />
          </div>
          <div className="text-muted text-[10px] mt-1 font-mono tabular-nums">
            {wf.progress}% · stage {wf.active_stage + 1}/{wf.stages.length}
          </div>
        </div>
        <div className="border-t border-border pt-2 flex-1 overflow-auto min-h-0">
          <div className="text-muted text-[10px] uppercase tracking-wide mb-1">Project Timeline</div>
          <ul className="flex flex-col gap-1 text-[11px]">
            <TimelineRow label="Print started · T1 #1" time="10:20:14Z" tone="cyan" />
            <TimelineRow label="Slice complete · 0.2mm PLA" time="10:18:02Z" tone="green" />
            <TimelineRow label="3MF validated · mesh OK" time="10:16:47Z" tone="green" />
            <TimelineRow label="Blender MCP export · 3MF" time="10:14:22Z" tone="green" />
            <TimelineRow label="3D generated · TRELLIS" time="10:11:08Z" tone="green" />
          </ul>
        </div>
      </div>
      <div className="col-span-1 min-w-0">
        <PreviewBox label="Active model" />
      </div>
    </div>
  );
}

function PipelineStageNode({
  stage,
  isLast,
}: {
  stage: (typeof PIPELINE_STAGES)[number];
  isLast: boolean;
}) {
  const visual =
    stage.status === "complete"
      ? { ring: "ring-accent-green/70", text: "text-accent-green", Indicator: Check }
      : stage.status === "active"
        ? { ring: "ring-accent-cyan/80 shadow-glow", text: "text-accent-cyan", Indicator: CircleDot }
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
            stage.status === "complete" ? "bg-accent-green/50" : "bg-border"
          }`}
          aria-hidden
        />
      )}
    </div>
  );
}

function TimelineRow({
  label,
  time,
  tone,
}: {
  label: string;
  time: string;
  tone: "cyan" | "green" | "amber";
}) {
  const dotClass =
    tone === "cyan" ? "bg-accent-cyan" : tone === "green" ? "bg-accent-green" : "bg-accent-amber";
  return (
    <li className="flex items-center gap-2">
      <span className={`h-1.5 w-1.5 rounded-full ${dotClass}`} aria-hidden />
      <span className="text-fg truncate flex-1">{label}</span>
      <span className="text-muted font-mono shrink-0">{time}</span>
    </li>
  );
}

/** Stylized dark wireframe placeholder — Phase 6 wires real STL/3MF preview. */
function PreviewBox({ label }: { label: string }) {
  return (
    <div className="h-full w-full bg-gradient-to-br from-surface2 to-bg border border-accent-cyan/20 rounded-lg p-2 flex flex-col items-center justify-between overflow-hidden relative">
      <div className="absolute inset-0 pointer-events-none" aria-hidden>
        {/* Subtle grid backdrop */}
        <svg viewBox="0 0 100 100" className="w-full h-full opacity-10" preserveAspectRatio="none">
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#22d3ee" strokeWidth="0.3" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid)" />
        </svg>
        {/* Corner brackets */}
        <CornerBracket pos="tl" />
        <CornerBracket pos="tr" />
        <CornerBracket pos="bl" />
        <CornerBracket pos="br" />
      </div>
      <div className="text-accent-cyan/80 text-[9px] uppercase tracking-wider z-10">{label}</div>
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full max-h-[120px] text-accent-cyan z-10 drop-shadow-[0_0_4px_rgba(34,211,238,0.4)]"
        fill="none"
        stroke="currentColor"
        strokeWidth="0.6"
        strokeLinejoin="round"
      >
        {/* Wireframe cube — front + top + side faces */}
        <polygon points="25,35 75,35 75,82 25,82" stroke="currentColor" />
        <polygon points="25,35 45,18 95,18 75,35" stroke="currentColor" />
        <polygon points="75,35 95,18 95,65 75,82" stroke="currentColor" />
        {/* Hidden edges */}
        <line x1="25" y1="35" x2="45" y2="18" />
        <line x1="45" y1="18" x2="45" y2="65" stroke="currentColor" strokeOpacity="0.25" strokeDasharray="1,1" />
        <line x1="45" y1="65" x2="25" y2="82" stroke="currentColor" strokeOpacity="0.25" strokeDasharray="1,1" />
        <line x1="45" y1="65" x2="95" y2="65" stroke="currentColor" strokeOpacity="0.25" strokeDasharray="1,1" />
      </svg>
      <div className="text-fg/90 text-[10px] font-mono z-10">frame-bracket-v3</div>
    </div>
  );
}

function CornerBracket({ pos }: { pos: "tl" | "tr" | "bl" | "br" }) {
  const positions = {
    tl: "top-1 left-1 border-l border-t",
    tr: "top-1 right-1 border-r border-t",
    bl: "bottom-1 left-1 border-l border-b",
    br: "bottom-1 right-1 border-r border-b",
  } as const;
  return <div className={`absolute h-2 w-2 border-accent-cyan/70 ${positions[pos]}`} />;
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Active Agents (left of mid row)                                     *
 * ────────────────────────────────────────────────────────────────────────── */
function ActiveAgentsList() {
  return (
    <ul className="flex flex-col gap-1 h-full overflow-auto">
      {MOCK_AGENTS.map((a) => (
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
function AgentActivityLog() {
  // Sort newest-first, deterministic on mock timestamps.
  const sorted = [...MOCK_AGENTS].sort((a, b) =>
    b.last_activity_utc.localeCompare(a.last_activity_utc),
  );
  return (
    <ul className="flex flex-col gap-1.5 h-full overflow-auto">
      {sorted.map((a) => (
        <li key={a.id} className="flex items-start gap-2 text-xs">
          <StatusBadge tone={AGENT_TONE[a.status]} label={a.status} />
          <div className="flex flex-col min-w-0 flex-1 leading-tight">
            <span className="text-fg truncate font-medium">{a.role}</span>
            <span className="text-muted text-[10px] truncate font-mono">
              {a.last_activity_utc.split("T")[1]?.slice(0, 8) ?? ""}Z · {a.model_provider}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: System Resources — CPU/RAM/Disk gauges + network sparkline          *
 * ────────────────────────────────────────────────────────────────────────── */
function ResourcePanel() {
  const sys = MOCK_SYSTEM_SNAPSHOT;
  return (
    <div className="flex flex-col h-full gap-2">
      <div className="grid grid-cols-3 gap-1 flex-1">
        <ResourceGauge value={sys.cpu_pct} label="CPU" />
        <ResourceGauge value={sys.ram_pct} label="RAM" />
        <ResourceGauge value={sys.disk_pct} label="DISK" />
      </div>
      <div className="border-t border-border pt-1.5">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-muted">
          <span>Network</span>
          <span className="font-mono tabular-nums text-fg">
            {sys.network_kbps[sys.network_kbps.length - 1]} kbps
          </span>
        </div>
        <div className="h-8">
          <Sparkline data={sys.network_kbps} color={tokens.chartColors.cyan} />
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Recent Jobs — name + printer + progress + done/check                *
 * ────────────────────────────────────────────────────────────────────────── */
function RecentJobs() {
  const jobs = MOCK_JOBS.slice(0, 7);
  const printerNameById = new Map(MOCK_PRINTERS.map((p) => [p.id, p.name]));
  return (
    <ul className="flex flex-col gap-1.5 h-full overflow-auto">
      {jobs.map((j) => {
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
function ProofPanel() {
  const b = LATEST_BUNDLE;
  const passCount = b.gates.filter((g) => g.verdict === "pass").length;
  return (
    <div className="flex flex-col gap-2 h-full text-xs">
      <div className="flex flex-col leading-tight">
        <span className="text-muted text-[10px] uppercase tracking-wide">Bundle</span>
        <span className="font-mono text-accent-cyan truncate">{b.id}</span>
      </div>
      <div className="grid grid-cols-2 gap-1 leading-tight">
        <KV k="Branch" v={<span className="font-mono text-fg text-[11px] truncate block">{b.branch}</span>} />
        <KV k="Commit" v={<span className="font-mono text-fg text-[11px]">{b.commit.slice(0, 10)}</span>} />
        <KV k="Files" v={<span className="text-fg text-[11px]">{b.files_count}</span>} />
        <KV k="Size" v={<span className="text-fg text-[11px]">{(b.size_bytes / 1024).toFixed(1)} KB</span>} />
      </div>
      <div className="flex-1 overflow-auto border-t border-border pt-1.5">
        <div className="text-muted text-[10px] uppercase tracking-wide mb-1">
          Gates · {passCount}/{b.gates.length} pass
        </div>
        <ul className="flex flex-col gap-0.5">
          {b.gates.slice(0, 6).map((g) => (
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
function LogsPanel() {
  return (
    <ul className="flex flex-col gap-1 h-full overflow-auto">
      {MOCK_LOGS.map((log, i) => {
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

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Quick Preview (3D model placeholder)                                *
 * ────────────────────────────────────────────────────────────────────────── */
function QuickPreview() {
  return (
    <div className="h-full flex flex-col gap-1.5">
      <div className="flex-1 bg-gradient-to-br from-surface2 to-bg border border-accent-cyan/20 rounded-lg flex items-center justify-center overflow-hidden relative">
        <div className="absolute inset-0 pointer-events-none" aria-hidden>
          <svg viewBox="0 0 100 100" className="w-full h-full opacity-10" preserveAspectRatio="none">
            <defs>
              <pattern id="grid-preview" width="8" height="8" patternUnits="userSpaceOnUse">
                <path d="M 8 0 L 0 0 0 8" fill="none" stroke="#22d3ee" strokeWidth="0.3" />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#grid-preview)" />
          </svg>
          <CornerBracket pos="tl" />
          <CornerBracket pos="tr" />
          <CornerBracket pos="bl" />
          <CornerBracket pos="br" />
        </div>
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full max-h-[140px] text-accent-cyan z-10 drop-shadow-[0_0_5px_rgba(34,211,238,0.45)]"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.6"
          strokeLinejoin="round"
        >
          {/* Wireframe hexagonal prism */}
          <polygon points="50,12 78,28 78,72 50,88 22,72 22,28" stroke="currentColor" />
          <line x1="50" y1="12" x2="50" y2="88" stroke="currentColor" strokeOpacity="0.5" />
          <line x1="22" y1="28" x2="78" y2="72" stroke="currentColor" strokeOpacity="0.35" />
          <line x1="78" y1="28" x2="22" y2="72" stroke="currentColor" strokeOpacity="0.35" />
          <line x1="50" y1="12" x2="22" y2="72" stroke="currentColor" strokeOpacity="0.3" />
          <line x1="50" y1="12" x2="78" y2="72" stroke="currentColor" strokeOpacity="0.3" />
          <line x1="50" y1="88" x2="22" y2="28" stroke="currentColor" strokeOpacity="0.3" />
          <line x1="50" y1="88" x2="78" y2="28" stroke="currentColor" strokeOpacity="0.3" />
          <circle cx="50" cy="50" r="1.5" fill="currentColor" />
        </svg>
      </div>
      <div className="flex items-center justify-between text-[11px] px-0.5">
        <div className="flex flex-col leading-tight min-w-0">
          <span className="text-fg font-medium truncate">frame-bracket-v3.3mf</span>
          <span className="text-muted font-mono text-[10px]">42.1 × 28.4 × 12.0 mm</span>
        </div>
        <Box size={13} className="text-accent-cyan/70 shrink-0" />
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Notifications                                                       *
 * ────────────────────────────────────────────────────────────────────────── */
function NotificationsPanel() {
  return (
    <ul className="flex flex-col gap-1.5 h-full overflow-auto">
      {MOCK_NOTIFICATIONS.map((n) => {
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
 * Strip: Dimensional Truth Engine (compact, below main grid)                 *
 * ────────────────────────────────────────────────────────────────────────── */
function DimensionalStrip() {
  const r = MOCK_DIMENSIONAL_REPORTS[0];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 h-full text-[11px]">
      <DimChip
        label="Scale / Unit"
        value={`${r.scale.scale_factor.toFixed(2)}× ${r.scale.unit}`}
        sub={r.scale.confirmed_by ? `confirmed · ${r.scale.confirmed_by}` : "awaiting confirm"}
        tone={r.scale.confirmed_by ? "green" : "amber"}
      />
      <DimChip
        label="Measurement Changes"
        value={r.changes.length === 0 ? "None requested" : `${r.changes.length} requested`}
        sub={r.changes[0] ? `${r.changes[0].axis} → ${r.changes[0].to_mm}mm` : "—"}
        tone="muted"
      />
      <DimChip
        label="Printability"
        value={r.printability}
        sub="Phase 6 trimesh checks"
        tone={r.printability === "pass" ? "green" : r.printability === "fail" ? "red" : "amber"}
      />
      <DimChip
        label="Mesh Repair"
        value={r.mesh_repair.applied ? "applied" : "not yet"}
        sub={r.mesh_repair.notes}
        tone={r.mesh_repair.applied ? "green" : "muted"}
      />
      <DimChip
        label="Visual Fidelity"
        value={r.fidelity ? `${r.fidelity.score}% · ${r.fidelity.method}` : "phase4_pending"}
        sub="SSIM + human eyeball"
        tone="muted"
      />
      <DimChip
        label="Before / After"
        value={r.before_after ? "Δ recorded" : "awaiting print + scan"}
        sub={r.proof_bundle_ref ? `proof: ${r.proof_bundle_ref}` : "no proof yet"}
        tone="muted"
      />
    </div>
  );
}

function DimChip({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  sub: React.ReactNode;
  tone: "green" | "red" | "amber" | "muted";
}) {
  const toneClass = {
    green: "border-accent-green/40",
    red: "border-accent-red/40",
    amber: "border-accent-amber/40",
    muted: "border-border",
  }[tone];
  const dotClass = {
    green: "bg-accent-green",
    red: "bg-accent-red",
    amber: "bg-accent-amber",
    muted: "bg-muted",
  }[tone];
  return (
    <div className={`flex items-center gap-2 px-2 py-1.5 rounded-md bg-surface2/40 border ${toneClass} min-w-0`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dotClass}`} aria-hidden />
      <div className="flex flex-col min-w-0 leading-tight">
        <span className="text-muted text-[9px] uppercase tracking-wide">{label}</span>
        <span className="text-fg text-[11px] truncate">{value}</span>
        <span className="text-muted text-[9px] truncate">{sub}</span>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Helpers                                                                    *
 * ────────────────────────────────────────────────────────────────────────── */
function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex flex-col min-w-0 leading-tight">
      <span className="text-muted text-[9px] uppercase tracking-wide">{k}</span>
      <span className="text-[11px] truncate">{v}</span>
    </div>
  );
}
