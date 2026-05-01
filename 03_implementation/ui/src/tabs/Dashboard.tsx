/**
 * Dashboard tab — Phase 2 Tasks 19-26.
 *
 * Faithful recreation of the dense dark layout in
 * `06_release/UI_FINAL_VISUAL_CONTRACT.png`. Eight panels per the user's
 * Phase-2 spec, all consuming mock data only:
 *
 *   1. System health KPI cards (top strip, 4-up)
 *   2. 12-printer fleet mini-table
 *   3. Active workflow timeline (visual pipeline)
 *   4. Agents running panel (roster + activity log)
 *   5. System resources panel (CPU / RAM / GPU / VRAM gauges)
 *   6. Recent jobs panel
 *   7. Proof bundle status (LATEST)
 *   8. Dimensional Truth Engine placeholder (per addendum)
 *
 * No real APIs, no adapter calls, no subprocesses — every value flows from
 * `src/data/mock/*`. Phase 3 swaps the mock layer behind `AdapterAPI` without
 * touching this file.
 */
import { Activity, Cpu, Printer as PrinterIcon, Sparkles } from "lucide-react";
import { Panel } from "../components/layout/Panel";
import { KpiCard } from "../components/cards/KpiCard";
import { DataTable, type Column } from "../components/tables/DataTable";
import { WorkflowPipeline } from "../components/pipeline/WorkflowPipeline";
import { ResourceGauge } from "../components/charts/ResourceGauge";
import { Sparkline } from "../components/charts/Sparkline";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { ProofChip } from "../components/badges/ProofChip";
import { MOCK_PRINTERS } from "../data/mock/printers";
import { MOCK_AGENTS } from "../data/mock/agents";
import { MOCK_WORKFLOWS } from "../data/mock/workflows";
import { MOCK_JOBS } from "../data/mock/jobs";
import { LATEST_BUNDLE } from "../data/mock/proof";
import { MOCK_SYSTEM_SNAPSHOT } from "../data/mock/system";
import { MOCK_DIMENSIONAL_REPORTS } from "../data/mock/dimensional";
import type { Printer, PrinterStatus } from "../types/printer";
import type { Job } from "../types/job";
import type { Agent } from "../types/agent";
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

export function Dashboard() {
  const totalPrinters = MOCK_PRINTERS.length;
  const printingCount = MOCK_PRINTERS.filter((p) => p.status === "printing").length;
  const activeWorkflows = MOCK_WORKFLOWS.filter((w) => w.status === "active");
  const activeAgents = MOCK_AGENTS.filter((a) => a.status === "active");
  const recentJobs = MOCK_JOBS.slice(0, 8);
  const activeWorkflow = activeWorkflows[0];
  const sys = MOCK_SYSTEM_SNAPSHOT;

  return (
    <div className="grid grid-cols-12 gap-4 auto-rows-min">
      {/* ── Row 1 ─ System Health KPI strip ──────────────────────────────── */}
      <KpiCardWrapper>
        <KpiCard
          label="Total Printers"
          value={totalPrinters}
          delta={{ value: `${printingCount} printing`, tone: "green" }}
          icon={<PrinterIcon size={20} />}
          chart={<Sparkline data={[10, 11, 12, 12, 11, 12, 12]} />}
        />
      </KpiCardWrapper>
      <KpiCardWrapper>
        <KpiCard
          label="Active Workflows"
          value={activeWorkflows.length}
          delta={{ value: "1 queued", tone: "muted" }}
          icon={<Activity size={20} />}
          chart={
            <Sparkline data={[1, 2, 2, 3, 3, 2, 3]} color={tokens.chartColors.green} />
          }
        />
      </KpiCardWrapper>
      <KpiCardWrapper>
        <KpiCard
          label="Avg Success Rate"
          value="98.2%"
          delta={{ value: "+0.3% vs 24h", tone: "green" }}
          icon={<Sparkles size={20} />}
          chart={
            <Sparkline data={[97.1, 97.4, 97.6, 98.0, 97.9, 98.1, 98.2]} color={tokens.chartColors.green} />
          }
        />
      </KpiCardWrapper>
      <KpiCardWrapper>
        <KpiCard
          label="GPU Detected"
          value={`${sys.gpu_detected_pct}%`}
          delta={{ value: sys.gpu_name ?? "GPU info unavailable", tone: "muted" }}
          icon={<Cpu size={20} />}
          chart={<Sparkline data={[40, 52, 48, 60, 55, 58, sys.gpu_util_pct]} />}
        />
      </KpiCardWrapper>

      {/* ── Row 2 ─ Printer Fleet (left, span-7) + Workflow Pipeline (right, span-5) ─ */}
      <div className="col-span-12 lg:col-span-7">
        <Panel
          id="dashboard.fleet"
          title="PRINTER FLEET"
          status={{ tone: "green", label: `${totalPrinters} units` }}
          headerExtra={
            <span className="text-muted text-xs">
              {printingCount} printing · {totalPrinters - printingCount} idle
            </span>
          }
          className="h-[420px]"
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
            activeWorkflow ? (
              <span className="text-muted text-xs truncate max-w-[220px]">{activeWorkflow.name}</span>
            ) : null
          }
          className="h-[420px]"
        >
          {activeWorkflow ? (
            <div className="flex flex-col gap-4 h-full">
              <WorkflowPipeline stages={activeWorkflow.stages} />
              <div className="border-t border-border pt-3">
                <div className="text-muted text-xs uppercase tracking-wide mb-2">Current Job</div>
                <div className="text-fg text-sm font-medium">{activeWorkflow.name}</div>
                <ProgressBar value={activeWorkflow.progress} />
                <div className="text-muted text-xs mt-1">
                  {activeWorkflow.progress}% · stage {activeWorkflow.active_stage + 1} of{" "}
                  {activeWorkflow.stages.length}
                </div>
              </div>
              <div className="border-t border-border pt-3 mt-auto">
                <div className="text-muted text-xs uppercase tracking-wide mb-1">
                  Other Active Workflows
                </div>
                {activeWorkflows.slice(1).map((wf) => (
                  <div key={wf.id} className="flex items-center justify-between text-xs py-1">
                    <span className="text-fg truncate">{wf.name}</span>
                    <span className="text-muted shrink-0 ml-2">{wf.progress}%</span>
                  </div>
                ))}
                {activeWorkflows.length <= 1 && (
                  <div className="text-muted text-xs">No other active workflows.</div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-muted text-sm text-center py-10">No active workflow.</div>
          )}
        </Panel>
      </div>

      {/* ── Row 3 ─ Agents (span-5) + Resources (span-3) + Recent Jobs (span-4) ─ */}
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="dashboard.agents"
          title="AGENTS RUNNING"
          status={{
            tone: "green",
            label: `${activeAgents.length}/${MOCK_AGENTS.length} active`,
          }}
          className="h-[300px]"
        >
          <AgentsRunning />
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="dashboard.resources"
          title="SYSTEM RESOURCES"
          status={{ tone: "green", label: sys.system_status }}
          className="h-[300px]"
        >
          <ResourcePanel />
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="dashboard.jobs"
          title="RECENT JOBS"
          status={{ tone: "muted", label: `${MOCK_JOBS.length} total` }}
          className="h-[300px]"
        >
          <RecentJobs jobs={recentJobs} />
        </Panel>
      </div>

      {/* ── Row 4 ─ Proof bundle (span-6) + Dimensional Truth Engine (span-6) ─ */}
      <div className="col-span-12 lg:col-span-6">
        <Panel
          id="dashboard.proof"
          title="PROOF & VERIFICATION (LATEST)"
          status={{ tone: "green", label: "verified" }}
          headerExtra={<ProofChip status={LATEST_BUNDLE.verdict === "verified" ? "verified" : "pending"} />}
          className="h-[260px]"
        >
          <ProofPanel />
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-6">
        <Panel
          id="dashboard.dimensional"
          title="DIMENSIONAL TRUTH ENGINE"
          status={{ tone: "amber", label: "phase 6 pending" }}
          headerExtra={<span className="text-muted text-xs">UI placeholder · live in Phase 6</span>}
          className="h-[260px]"
        >
          <DimensionalPanel />
        </Panel>
      </div>
    </div>
  );
}

/** Reusable col-span-3 wrapper for the KPI strip. */
function KpiCardWrapper({ children }: { children: React.ReactNode }) {
  return <div className="col-span-12 sm:col-span-6 lg:col-span-3">{children}</div>;
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 bg-surface2 rounded-full mt-2 overflow-hidden">
      <div
        className="h-full bg-accent-cyan rounded-full transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Printer Fleet                                                       *
 * ────────────────────────────────────────────────────────────────────────── */
function FleetTable() {
  const columns: Column<Printer>[] = [
    {
      id: "name",
      header: "Printer",
      render: (p) => (
        <div className="flex flex-col">
          <span className="font-medium text-fg">{p.name}</span>
          <span className="text-muted text-[11px]">{p.model}</span>
        </div>
      ),
    },
    {
      id: "status",
      header: "Status",
      render: (p) => <StatusBadge tone={PRINTER_TONE[p.status]} label={PRINTER_LABEL[p.status]} />,
      width: "w-28",
    },
    {
      id: "adapter",
      header: "Adapter",
      render: (p) => <span className="text-muted text-xs uppercase">{p.adapter}</span>,
      width: "w-24",
    },
    {
      id: "ip",
      header: "IP",
      render: (p) => <span className="text-muted font-mono text-xs">{p.ip ?? "—"}</span>,
      width: "w-28",
    },
    {
      id: "job",
      header: "Job",
      render: (p) => (
        <span className="text-fg text-xs truncate block max-w-[180px]">
          {p.current_job ?? <span className="text-muted">—</span>}
        </span>
      ),
    },
    {
      id: "progress",
      header: "%",
      render: (p) =>
        p.progress != null ? (
          <span className="text-accent-cyan font-semibold text-xs">{p.progress}%</span>
        ) : (
          <span className="text-muted">—</span>
        ),
      width: "w-12",
      align: "right",
    },
  ];
  return <DataTable columns={columns} rows={MOCK_PRINTERS} keyOf={(p) => p.id} />;
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Agents Running (roster + activity log)                              *
 * ────────────────────────────────────────────────────────────────────────── */
function AgentsRunning() {
  const sortedByActivity = [...MOCK_AGENTS].sort((a, b) =>
    b.last_activity_utc.localeCompare(a.last_activity_utc),
  );
  return (
    <div className="grid grid-cols-2 gap-3 h-full">
      <div className="border-r border-border pr-3 overflow-auto">
        <div className="text-muted text-xs uppercase tracking-wide mb-2">Roster</div>
        <div className="grid grid-cols-1 gap-1.5">
          {MOCK_AGENTS.map((a) => (
            <div key={a.id} className="flex items-center gap-2 text-xs">
              <span
                className={[
                  "h-1.5 w-1.5 rounded-full shrink-0",
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
              <span className="text-fg truncate flex-1">{a.role}</span>
              <span className="text-muted text-[11px] shrink-0">{a.task_count}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="overflow-auto">
        <div className="text-muted text-xs uppercase tracking-wide mb-2">Activity Log</div>
        <div className="flex flex-col gap-1.5">
          {sortedByActivity.slice(0, 8).map((a) => (
            <div key={a.id} className="flex items-start gap-2 text-xs">
              <StatusBadge tone={AGENT_TONE[a.status]} label={a.status} />
              <div className="flex flex-col min-w-0 flex-1">
                <span className="text-fg truncate">{a.role}</span>
                <span className="text-muted text-[10px] font-mono truncate">
                  {formatTimeUTC(a.last_activity_utc)} · {a.model_provider}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: System Resources (CPU / RAM / GPU / VRAM)                           *
 * ────────────────────────────────────────────────────────────────────────── */
function ResourcePanel() {
  const sys = MOCK_SYSTEM_SNAPSHOT;
  const used = sys.vram_used_gb;
  const total = sys.vram_total_gb;
  const vramPct = used != null && total != null && total > 0 ? Math.round((used / total) * 100) : 0;
  const vramLabel =
    used != null && total != null
      ? `VRAM ${used.toFixed(1)}/${total}GB`
      : "VRAM (unavailable)";
  return (
    <div className="grid grid-cols-2 gap-2 h-full">
      <ResourceGauge value={sys.cpu_pct} label="CPU" />
      <ResourceGauge value={sys.ram_pct} label="RAM" />
      <ResourceGauge value={sys.gpu_util_pct} label="GPU" />
      <ResourceGauge value={vramPct} label={vramLabel} />
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Recent Jobs                                                         *
 * ────────────────────────────────────────────────────────────────────────── */
function RecentJobs({ jobs }: { jobs: Job[] }) {
  return (
    <div className="flex flex-col gap-1.5 h-full overflow-auto">
      {jobs.map((j) => (
        <div
          key={j.id}
          className="flex items-center gap-2 text-xs py-1 border-b border-border/40 last:border-0"
        >
          <StatusBadge tone={JOB_TONE[j.status]} label={j.status} />
          <span className="text-fg truncate flex-1 font-mono text-[11px]">{j.name}</span>
          <span className="text-muted shrink-0">
            {j.progress != null ? `${j.progress}%` : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Proof & Verification (LATEST)                                       *
 * ────────────────────────────────────────────────────────────────────────── */
function ProofPanel() {
  const b = LATEST_BUNDLE;
  const passCount = b.gates.filter((g) => g.verdict === "pass").length;
  const totalGates = b.gates.length;
  return (
    <div className="flex flex-col gap-3 h-full">
      <div className="grid grid-cols-2 gap-3 text-xs">
        <KV k="Bundle" v={<span className="font-mono text-accent-cyan">{b.id}</span>} />
        <KV k="Branch" v={<span className="font-mono text-fg">{b.branch}</span>} />
        <KV k="Commit" v={<span className="font-mono text-fg">{b.commit.slice(0, 12)}</span>} />
        <KV k="Files" v={<span className="text-fg">{b.files_count} · {(b.size_bytes / 1024).toFixed(1)} KB</span>} />
        <KV k="SHA-256" v={<span className="font-mono text-muted text-[10px] truncate block">{b.sha256.slice(0, 32)}…</span>} />
        <KV k="Built" v={<span className="text-muted">{formatTimeUTC(b.ts_utc)}</span>} />
      </div>
      <div className="flex-1 overflow-auto border-t border-border pt-2">
        <div className="text-muted text-xs uppercase tracking-wide mb-1">
          Gate Matrix · {passCount}/{totalGates} pass
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          {b.gates.map((g) => (
            <div key={g.layer} className="flex items-center gap-2 text-[11px]">
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
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Panel: Dimensional Truth Engine (Phase 6 placeholder)                      *
 * ────────────────────────────────────────────────────────────────────────── */
function DimensionalPanel() {
  const r = MOCK_DIMENSIONAL_REPORTS[0];
  return (
    <div className="grid grid-cols-2 gap-3 h-full text-xs">
      <DimRow
        label="Scale / Unit"
        value={
          <span className="text-fg">
            {r.scale.scale_factor.toFixed(2)}× · {r.scale.unit}
          </span>
        }
        sub={
          r.scale.confirmed_by
            ? `Confirmed by ${r.scale.confirmed_by}`
            : <span className="text-accent-amber">Awaiting operator confirmation</span>
        }
      />
      <DimRow
        label="Measurement Changes"
        value={
          r.changes.length === 0 ? (
            <span className="text-muted">None requested</span>
          ) : (
            <span className="text-fg">{r.changes.length} requested</span>
          )
        }
        sub={
          r.changes[0] ? `${r.changes[0].axis} → ${r.changes[0].to_mm}mm` : "—"
        }
      />
      <DimRow
        label="Printability"
        value={
          <StatusBadge
            tone={r.printability === "pass" ? "green" : r.printability === "fail" ? "red" : "amber"}
            label={r.printability}
          />
        }
        sub="Phase 6 will run trimesh checks"
      />
      <DimRow
        label="Mesh Repair"
        value={
          <StatusBadge
            tone={r.mesh_repair.applied ? "green" : "muted"}
            label={r.mesh_repair.applied ? "applied" : "not yet"}
          />
        }
        sub={r.mesh_repair.notes}
      />
      <DimRow
        label="Visual Fidelity"
        value={
          r.fidelity ? (
            <span className="text-fg">{r.fidelity.score}% · {r.fidelity.method}</span>
          ) : (
            <span className="text-muted">phase4_pending</span>
          )
        }
        sub="SSIM + human eyeball after print + scan"
      />
      <DimRow
        label="Before / After"
        value={
          r.before_after ? (
            <span className="text-fg">Δ recorded</span>
          ) : (
            <span className="text-muted">Awaiting print + scan</span>
          )
        }
        sub={r.proof_bundle_ref ? `Proof: ${r.proof_bundle_ref}` : "No proof yet"}
      />
    </div>
  );
}

function DimRow({
  label,
  value,
  sub,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
}) {
  return (
    <div className="border border-border/60 rounded-lg p-2.5 bg-surface2/40 flex flex-col gap-1 min-w-0">
      <div className="text-muted text-[10px] uppercase tracking-wide">{label}</div>
      <div className="text-fg text-sm leading-tight truncate">{value}</div>
      {sub && (
        <div className="text-muted text-[10px] leading-tight truncate">{sub}</div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────── *
 * Helpers                                                                    *
 * ────────────────────────────────────────────────────────────────────────── */
function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex flex-col min-w-0">
      <span className="text-muted text-[10px] uppercase tracking-wide">{k}</span>
      <span className="text-xs">{v}</span>
    </div>
  );
}

function formatTimeUTC(iso: string): string {
  // Deterministic HH:MM:SS UTC slice — no locale, no Date.now() coupling.
  const t = iso.split("T")[1] ?? "";
  return t.replace("Z", "Z");
}
