/**
 * Dashboard Simple mode — W6-3 lane.
 *
 * Contract (from `Images-GUI/01-dashboard-modes/simple-dashboard-*.png`):
 *  - Header strip with the active mode switcher (rendered by parent).
 *  - 4-6 KPI cards in a single row at the top (Total Printers, Active Prints,
 *    Queued, Success Rate, System Health).
 *  - One large central "System Status" hero card summarising backend health.
 *  - No drawers, no Action Window, no Hermes Agents chat-mirror dock — those
 *    only appear in Advanced + Custom.
 *
 * Live data: pulls from the same `adapters` API as the existing Dashboard.
 * Empty/blocked panels render explicit truthful empty states; nothing is
 * fabricated.
 */
import { Activity, ListOrdered, Printer as PrinterIcon, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { adapters } from "../../api/adapters";
import type { Job } from "../../types/job";
import type { Printer } from "../../types/printer";
import type { SystemSnapshot } from "../../types/system";

type SimpleSnapshot = {
  printers: Printer[];
  jobs: Job[];
  system: SystemSnapshot | null;
};

const EMPTY: SimpleSnapshot = { printers: [], jobs: [], system: null };
const SIMPLE_REFRESH_INTERVAL_MS = 5_000;

export function DashboardSimple() {
  const [snapshot, setSnapshot] = useState<SimpleSnapshot>(EMPTY);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      void Promise.allSettled([
        adapters.getPrinters(),
        adapters.getJobs("printing,queued,completed,failed,cancelled"),
        adapters.getSystemSnapshot(),
      ]).then((results) => {
        if (!mounted) return;
        const [printersResult, jobsResult, systemResult] = results;
        setSnapshot({
          printers: printersResult.status === "fulfilled" ? printersResult.value : [],
          jobs: jobsResult.status === "fulfilled" ? jobsResult.value : [],
          system: systemResult.status === "fulfilled" ? systemResult.value : null,
        });
        setLoaded(true);
      });
    };
    load();
    const timer = window.setInterval(() => {
      if (!document.hidden) load();
    }, SIMPLE_REFRESH_INTERVAL_MS);
    const onSettingsChanged = () => load();
    window.addEventListener("hermes3d:settings-changed", onSettingsChanged);
    return () => {
      mounted = false;
      window.clearInterval(timer);
      window.removeEventListener("hermes3d:settings-changed", onSettingsChanged);
    };
  }, []);

  const livePrinters = snapshot.printers.filter(isLivePrinter);
  const hiddenPrinters = snapshot.printers.length - livePrinters.length;
  const totalPrinters = livePrinters.length;
  const onlinePrinters = livePrinters.filter((p) => p.status !== "offline").length;
  const activePrints = livePrinters.filter((p) => p.status === "printing").length;
  const queued = snapshot.jobs.filter((job) => job.status === "queued").length;
  const completed = snapshot.jobs.filter((job) => job.status === "completed").length;
  const failed = snapshot.jobs.filter((job) => job.status === "failed").length;
  const successRate = completed + failed > 0
    ? Math.round((completed / (completed + failed)) * 1000) / 10
    : null;
  const sysStatus = snapshot.system?.system_status ?? null;
  const sysGpu = snapshot.system?.gpu_name ?? null;

  return (
    <div
      className="dashboard-simple-grid grid h-full min-h-0 grid-cols-12 gap-3"
      data-testid="dashboard-root"
      data-dashboard-mode="simple"
    >
      {/* KPI strip */}
      <section className="col-span-12 grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
        <KpiTile
          icon={<PrinterIcon size={20} className="text-accent-cyan" />}
          label="Total Printers"
          value={String(totalPrinters)}
          detail={`${onlinePrinters} online${hiddenPrinters > 0 ? ` · ${hiddenPrinters} hidden` : ""}`}
        />
        <KpiTile
          icon={<Activity size={20} className="text-accent-green" />}
          label="Active Prints"
          value={String(activePrints)}
          detail="Running now"
        />
        <KpiTile
          icon={<ListOrdered size={20} className="text-accent-amber" />}
          label="Queued"
          value={String(queued)}
          detail="In print queue"
        />
        <KpiTile
          icon={<Sparkles size={20} className="text-accent-green" />}
          label="Success Rate"
          value={successRate == null ? "—" : `${successRate}%`}
          detail={successRate == null ? "No completed jobs" : "From completed jobs"}
        />
        <KpiTile
          icon={<ShieldCheck size={20} className={sysStatus === "OK" ? "text-accent-green" : "text-accent-amber"} />}
          label="System Health"
          value={sysStatus ?? "—"}
          detail={sysGpu ?? (snapshot.system ? "GPU unknown" : "Backend unavailable")}
        />
      </section>

      {/* Hero status card — mirrors Images-GUI/01-dashboard-modes/simple-dashboard-a.png:
          a single large System Status panel with a SIMPLE MODE badge top-right and a
          live 4-col mini-stat strip (RAM/Disk/GPU detect/GPU util) along the bottom. */}
      <section
        className="col-span-12 flex flex-col items-stretch justify-between gap-3 rounded-card border border-border bg-surface p-5 lg:col-span-8"
        data-testid="dashboard-simple-hero"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-muted text-[11px] uppercase tracking-wide">System Status</div>
            <div className="mt-1 text-2xl font-bold text-fg">
              {sysStatus ?? (loaded ? "Backend Unavailable" : "Loading…")}
            </div>
            <p className="mt-2 max-w-[640px] text-sm text-muted">
              Simple mode keeps the live metrics that matter most. Switch to Advanced for the
              full panel layout, or Custom to design your own.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span
              data-testid="dashboard-simple-mode-badge"
              className="rounded border border-accent-blue/40 bg-accent-blue/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent-blue"
            >
              Simple Mode
            </span>
            <div className="rounded-md border border-border bg-surface2 px-3 py-2 text-xs">
              <div className="text-muted">CPU</div>
              <div className="font-mono text-fg">{snapshot.system ? `${snapshot.system.cpu_pct}%` : "—"}</div>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-2.5">
          <MiniStat label="RAM" value={snapshot.system ? `${snapshot.system.ram_pct}%` : "—"} />
          <MiniStat label="Disk" value={snapshot.system ? `${snapshot.system.disk_pct}%` : "—"} />
          <MiniStat label="GPU detect" value={snapshot.system ? `${snapshot.system.gpu_detected_pct}%` : "—"} />
          <MiniStat label="GPU util" value={snapshot.system ? `${snapshot.system.gpu_util_pct}%` : "—"} />
        </div>
      </section>

      {/* Right side: compact summary */}
      <aside
        className="col-span-12 flex min-h-0 flex-col gap-3 lg:col-span-4"
        data-testid="dashboard-simple-summary"
      >
        <div className="rounded-card border border-border bg-surface p-4">
          <div className="text-muted text-[11px] uppercase tracking-wide">Live Snapshot</div>
          <ul className="mt-2 flex flex-col gap-2 text-xs">
            <SummaryRow label="Edition" value={snapshot.system?.edition ?? "—"} />
            <SummaryRow label="Security" value={snapshot.system?.security_status ?? "—"} />
            <SummaryRow label="Sources" value={snapshot.system ? "Live API" : "Backend unavailable"} />
            <SummaryRow label="Total jobs" value={String(snapshot.jobs.length)} />
          </ul>
        </div>
        <div className="rounded-card border border-border bg-surface p-4 text-xs text-muted">
          Simple mode is read-only. Use Advanced for queue control, agents, or proof
          inspection. The mode switcher is in the top-right header.
        </div>
      </aside>
    </div>
  );
}

function KpiTile({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div
      data-testid={`dashboard-simple-kpi-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
      className="flex items-center gap-3 rounded-card border border-border bg-surface px-3 py-3"
    >
      <div className="rounded-md bg-surface2 p-2">{icon}</div>
      <div className="min-w-0">
        <div className="text-muted text-[10px] uppercase tracking-wide">{label}</div>
        <div className="text-fg text-lg font-semibold leading-tight">{value}</div>
        <div className="text-muted text-[11px] truncate">{detail}</div>
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-surface2 px-3 py-2 text-xs">
      <div className="text-muted text-[10px] uppercase tracking-wide">{label}</div>
      <div className="mt-1 font-mono text-fg">{value}</div>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className="text-fg font-medium truncate">{value}</span>
    </li>
  );
}

function isLivePrinter(printer: Printer): boolean {
  return !printer.maintenance_flag
    && printer.status !== "disabled"
    && printer.status !== "maintenance";
}
