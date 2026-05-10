/**
 * Print Queue tab — reuses `GET /api/jobs?status=queued` + `printing` to show
 * the live spool of work waiting on a printer. This is a more focused view
 * than the full Jobs tab (which adds workflow-stage + repair affordances).
 *
 * No mock data; empty queue renders an explicit "No jobs queued" message.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Pause, Play, Printer as PrinterIcon, RefreshCw } from "lucide-react";
import { adapters } from "../api/adapters";
import type { Job, JobStatus } from "../types/job";
import type { Printer } from "../types/printer";

const REFRESH_INTERVAL_MS = 10_000;

const STATUS_CLASS: Record<JobStatus, string> = {
  queued: "border-amber-700/60 bg-amber-950/30 text-amber-200",
  printing: "border-cyan-700/60 bg-cyan-950/30 text-cyan-200",
  completed: "border-green-700/60 bg-green-950/30 text-green-200",
  failed: "border-red-700/60 bg-red-950/30 text-red-200",
  cancelled: "border-border bg-bg/40 text-muted",
  rolled_back: "border-border bg-bg/40 text-muted",
};

export function PrintQueueTab() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [loading, setLoading] = useState(false);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [queued, printing] = await Promise.all([
        adapters.getJobs("queued"),
        adapters.getJobs("printing"),
      ]);
      // De-duplicate by id (in case a job briefly straddles statuses).
      const map = new Map<string, Job>();
      for (const j of [...queued, ...printing]) {
        map.set(j.id, j);
      }
      setJobs(Array.from(map.values()));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load print queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    void adapters.getPrinters().then(setPrinters).catch(() => undefined);
  }, [refresh]);

  useEffect(() => {
    if (paused) return;
    const t = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(t);
  }, [paused, refresh]);

  const printerName = useMemo(
    () => new Map(printers.map((p) => [p.id, p.name])),
    [printers],
  );

  const queued = useMemo(() => (jobs ?? []).filter((j) => j.status === "queued"), [jobs]);
  const printing = useMemo(() => (jobs ?? []).filter((j) => j.status === "printing"), [jobs]);

  return (
    <div data-testid="print-queue-root" className="flex h-full flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-surface p-3">
        <div>
          <h2 className="text-sm font-semibold text-fg">Print Queue</h2>
          <p className="text-xs text-muted">
            Live from <code className="font-mono text-[10px]">GET /api/jobs?status=queued,printing</code>
            {jobs ? ` · ${printing.length} active · ${queued.length} waiting` : ""}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            data-testid="print-queue-refresh"
            className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
          >
            <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setPaused((v) => !v)}
            aria-pressed={paused}
            data-testid="print-queue-pause"
            className={[
              "flex items-center gap-1.5 rounded border px-2 py-1 text-[11px]",
              paused
                ? "border-accent-amber/40 text-accent-amber"
                : "border-border text-muted hover:border-accent-cyan/40 hover:text-fg",
            ].join(" ")}
          >
            {paused ? <Play size={11} /> : <Pause size={11} />}
            {paused ? "Paused" : "Auto 10s"}
          </button>
        </div>
      </header>

      {error && (
        <div role="alert" data-testid="print-queue-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2">
        <Lane title="Printing now" jobs={printing} printerName={printerName} testId="print-queue-lane-printing" />
        <Lane title="Queued" jobs={queued} printerName={printerName} testId="print-queue-lane-queued" />
      </div>
    </div>
  );
}

function Lane({
  title,
  jobs,
  printerName,
  testId,
}: {
  title: string;
  jobs: Job[];
  printerName: Map<string, string>;
  testId: string;
}) {
  return (
    <section data-testid={testId} className="flex min-h-0 flex-col rounded border border-border bg-surface p-3">
      <h3 className="text-xs font-semibold uppercase text-muted">{title}</h3>
      <div className="mt-2 min-h-0 flex-1 overflow-auto">
        {jobs.length === 0 ? (
          <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
            No jobs in this lane.
          </div>
        ) : (
          <ul className="space-y-2">
            {jobs.map((job) => (
              <li
                key={job.id}
                data-testid={`print-queue-job-${job.id}`}
                className={`rounded border px-3 py-2 text-xs ${STATUS_CLASS[job.status] ?? STATUS_CLASS.queued}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="truncate font-semibold">{job.name}</span>
                  <span className="rounded bg-bg/40 px-2 py-0.5 font-mono text-[10px] uppercase">
                    {job.status}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-muted">
                  <span className="flex items-center gap-1">
                    <PrinterIcon size={10} />
                    {job.printer_id ? printerName.get(job.printer_id) ?? job.printer_id : "unassigned"}
                  </span>
                  <span>progress {Math.round(job.progress)}%</span>
                  <span className="font-mono text-[10px]">
                    {new Date(job.started_utc).toLocaleTimeString()}
                  </span>
                  {job.eta_utc && (
                    <span className="font-mono text-[10px]">
                      ETA {new Date(job.eta_utc).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
