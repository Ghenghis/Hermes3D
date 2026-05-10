/**
 * Print Queue tab — Phase 2 mock-only per TAB_SPECS.md §8.
 *
 * Queue by priority · printer assignment suggestions · job detail inspector ·
 * pause/cancel/retry (locked). Queue operations are simulated until printer
 * adapter is write-enabled (Phase 6).
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { MOCK_JOBS } from "../data/mock/jobs";
import { MOCK_PRINTERS } from "../data/mock/printers";
import type { Job } from "../types/job";

const JOB_TONE: Record<Job["status"], StatusTone> = {
  queued: "muted",
  printing: "cyan",
  completed: "green",
  failed: "red",
  cancelled: "muted",
  rolled_back: "amber",
};

export function PrintQueueTab() {
  const queue = MOCK_JOBS.filter((j) => j.status === "queued");
  const printing = MOCK_JOBS.filter((j) => j.status === "printing");
  const allActive = [...printing, ...queue];
  const [selectedId, setSelectedId] = useState(allActive[0]?.id ?? MOCK_JOBS[0].id);
  const selected = MOCK_JOBS.find((j) => j.id === selectedId) ?? MOCK_JOBS[0];
  const printerNameById = new Map(MOCK_PRINTERS.map((p) => [p.id, p.name]));
  const idlePrinters = MOCK_PRINTERS.filter((p) => p.status === "online" && !p.maintenance_flag);

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="queue-root">
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="queue.priority"
          title="QUEUE BY PRIORITY"
          dense
          status={{ tone: "cyan", label: `${queue.length} queued · ${printing.length} printing` }}
          className="h-[440px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {allActive.map((j, i) => (
              <li key={j.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(j.id)}
                  className={[
                    "w-full flex items-center gap-2 px-2 py-1.5 rounded border text-left",
                    j.id === selectedId
                      ? "bg-surface2 border-accent-cyan/40"
                      : "bg-surface2/30 border-border hover:border-accent-cyan/20",
                  ].join(" ")}
                >
                  <span className="text-muted font-mono text-[10px] w-5 shrink-0">{i + 1}</span>
                  <StatusBadge tone={JOB_TONE[j.status]} label={j.status} />
                  <span className="text-fg font-mono truncate flex-1">{j.name}</span>
                  <span className="text-muted text-[10px] shrink-0">
                    {j.progress}%
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="queue.detail"
          title="JOB INSPECTOR"
          dense
          status={{ tone: JOB_TONE[selected.status], label: selected.status }}
          className="h-[440px]"
        >
          <div className="grid grid-cols-2 gap-2 text-xs h-full">
            <KV k="Job ID" v={<span className="font-mono">{selected.id}</span>} />
            <KV k="Status" v={<StatusBadge tone={JOB_TONE[selected.status]} label={selected.status} />} />
            <KV k="File" v={<span className="font-mono text-[11px] truncate block">{selected.name}</span>} />
            <KV k="Printer" v={selected.printer_id ? printerNameById.get(selected.printer_id) ?? selected.printer_id : "unassigned"} />
            <KV k="Started" v={<span className="font-mono text-[11px]">{selected.started_utc}</span>} />
            <KV k="ETA" v={selected.eta_utc ? <span className="font-mono text-[11px]">{selected.eta_utc}</span> : "—"} />
            <KV k="Progress" v={`${selected.progress}%`} />
            <KV k="Proof" v={selected.proof_ref ? <span className="font-mono text-[11px]">{selected.proof_ref}</span> : "none"} />
            <div className="col-span-2 mt-auto flex flex-wrap gap-1.5 pt-2 border-t border-border">
              <LockedAction label="Pause" hint="locked · Phase 6 wires printer adapter writes" />
              <LockedAction label="Cancel" />
              <LockedAction label="Retry" />
              <LockedAction label="Reassign printer" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="queue.suggestions"
          title="ASSIGN SUGGESTIONS"
          dense
          status={{ tone: "green", label: `${idlePrinters.length} idle` }}
          className="h-[440px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {idlePrinters.map((p, i) => (
              <li
                key={p.id}
                className="flex flex-col gap-0.5 px-2 py-1.5 rounded bg-surface2/40 border border-border"
              >
                <div className="flex items-center justify-between">
                  <span className="text-fg font-medium truncate">{p.name}</span>
                  <span className="text-muted text-[10px]">#{i + 1}</span>
                </div>
                <div className="text-muted text-[10px] font-mono">{p.ip ?? "USB"} · {p.adapter}</div>
                <div className="mt-0.5">
                  <LockedAction label="Assign" />
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex flex-col min-w-0 leading-tight">
      <span className="text-muted text-[10px] uppercase tracking-wide">{k}</span>
      <span className="text-fg truncate">{v}</span>
    </div>
  );
}
