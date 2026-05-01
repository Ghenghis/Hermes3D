/**
 * Printer Fleet tab — Phase 2 mock-only per TAB_SPECS.md §7.
 *
 * Full 12-printer table · adapter status per printer · IP/port/USB details ·
 * camera/web UI launch (locked) · maintenance flags. No printer command
 * buttons until adapter detected and safety policy loaded.
 */
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { adapters } from "../api/adapters";
import { MOCK_PRINTERS } from "../data/mock/printers";
import type { Printer, PrinterStatus, PrinterAdapter, PrinterDataSource } from "../types/printer";
import { Camera, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const PRINTER_TONE: Record<PrinterStatus, StatusTone> = {
  online: "green",
  printing: "cyan",
  paused: "amber",
  maintenance: "amber",
  offline: "muted",
  error: "red",
};

const ADAPTER_TONE: Record<PrinterAdapter, StatusTone> = {
  moonraker: "cyan",
  octoprint: "blue",
  printrun: "amber",
  manual: "muted",
};

export function FleetTab() {
  const [printers, setPrinters] = useState<Printer[]>(MOCK_PRINTERS);
  useEffect(() => {
    let mounted = true;
    void adapters.getPrinters().then((nextPrinters) => {
      if (mounted) {
        setPrinters(nextPrinters);
      }
    }).catch(() => undefined);
    return () => {
      mounted = false;
    };
  }, []);

  const adapterCounts = useMemo(
    () =>
      printers.reduce(
        (acc, p) => {
          acc[p.adapter] = (acc[p.adapter] ?? 0) + 1;
          return acc;
        },
        {} as Record<PrinterAdapter, number>,
      ),
    [printers],
  );
  const maintenanceCount = printers.filter((p) => p.maintenance_flag).length;

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="fleet-root">
      <div className="col-span-12 lg:col-span-9">
        <Panel
          id="fleet.table"
          title="PRINTER FLEET (12 UNITS)"
          dense
          status={{ tone: "green", label: `${printers.length} units` }}
          className="h-[600px]"
        >
          <div className="w-full overflow-auto h-full">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-muted text-[10px] uppercase tracking-wide border-b border-border">
                  <th className="text-right py-1.5 px-2 font-medium w-8">#</th>
                  <th className="text-left py-1.5 px-2 font-medium">Printer</th>
                  <th className="text-left py-1.5 px-2 font-medium w-28">IP / USB</th>
                  <th className="text-left py-1.5 px-2 font-medium w-28">Adapter</th>
                  <th className="text-left py-1.5 px-2 font-medium w-24">Status</th>
                  <th className="text-left py-1.5 px-2 font-medium">Current Job</th>
                  <th className="text-right py-1.5 px-2 font-medium w-20">Hot / Bed</th>
                  <th className="text-left py-1.5 px-2 font-medium w-32">Actions</th>
                </tr>
              </thead>
              <tbody>
                {printers.map((p, i) => (
                  <PrinterRow key={p.id} printer={p} index={i + 1} />
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-3 grid grid-cols-1 gap-2.5">
        <Panel
          id="fleet.adapters"
          title="ADAPTERS"
          dense
          status={{ tone: "cyan", label: `${Object.keys(adapterCounts).length} types` }}
          className="h-[200px]"
        >
          <ul className="flex flex-col gap-1.5 h-full overflow-auto text-xs">
            {(Object.keys(adapterCounts) as PrinterAdapter[]).map((a) => (
              <li key={a} className="flex items-center justify-between">
                <StatusBadge tone={ADAPTER_TONE[a]} label={a} />
                <span className="text-muted font-mono text-[11px]">{adapterCounts[a]} units</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel
          id="fleet.maintenance"
          title="MAINTENANCE"
          dense
          status={{
            tone: maintenanceCount > 0 ? "amber" : "green",
            label: `${maintenanceCount} flagged`,
          }}
          className="h-[200px]"
        >
          {maintenanceCount === 0 ? (
            <div className="text-muted text-xs text-center py-6">No maintenance flags. ✓</div>
          ) : (
            <ul className="flex flex-col gap-1.5 h-full overflow-auto text-xs">
              {printers.filter((p) => p.maintenance_flag).map((p) => (
                <li
                  key={p.id}
                  className="flex flex-col gap-0.5 px-2 py-1.5 rounded bg-accent-amber/10 border border-accent-amber/30"
                >
                  <span className="text-fg font-medium">{p.name}</span>
                  <span className="text-muted text-[10px] font-mono">{p.ip ?? "—"}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel
          id="fleet.policy"
          title="SAFETY POLICY"
          dense
          status={{ tone: "green", label: "loaded" }}
          className="h-[170px]"
        >
          <ul className="flex flex-col gap-1 text-xs">
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-green shrink-0" aria-hidden />
              <span className="text-fg">Adapter detection required</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-green shrink-0" aria-hidden />
              <span className="text-fg">Confirmation modal for moves</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-green shrink-0" aria-hidden />
              <span className="text-fg">G-code allowlist scan</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-amber shrink-0" aria-hidden />
              <span className="text-fg">Write-mode disabled (Phase 6)</span>
            </li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function PrinterRow({ printer: p, index }: { printer: Printer; index: number }) {
  const tempLabel = p.temp_hot != null && p.temp_bed != null ? `${p.temp_hot}/${p.temp_bed}°` : "—";
  return (
    <tr className="border-b border-border/30 hover:bg-surface2/50 transition-colors" data-source={p.data_source}>
      <td className="py-1.5 px-2 text-right text-muted font-mono">{index}</td>
      <td className="py-1.5 px-2">
        <div className="flex flex-col leading-tight">
          <span className="text-fg font-medium">{p.name}</span>
          <span className="text-muted text-[10px] flex items-center gap-1">
            {p.model}
            <DataSourceChip source={p.data_source} />
          </span>
        </div>
      </td>
      <td className="py-1.5 px-2 text-muted font-mono text-[11px]">{p.ip ?? "USB"}</td>
      <td className="py-1.5 px-2">
        <StatusBadge tone={ADAPTER_TONE[p.adapter]} label={p.adapter} />
      </td>
      <td className="py-1.5 px-2">
        <StatusBadge tone={PRINTER_TONE[p.status]} label={p.status} />
      </td>
      <td className="py-1.5 px-2">
        <span className="text-fg text-[11px] truncate block max-w-[180px]">
          {p.current_job ?? <span className="text-muted">—</span>}
        </span>
      </td>
      <td className="py-1.5 px-2 text-right text-fg font-mono text-[11px]">{tempLabel}</td>
      <td className="py-1.5 px-2">
        <div className="flex gap-1">
          {p.camera_url && (
            <button
              type="button"
              disabled
              title="locked · adapter phase"
              className="text-muted hover:text-fg p-1 rounded disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="Camera (locked)"
            >
              <Camera size={12} />
            </button>
          )}
          <button
            type="button"
            disabled
            title="locked · adapter phase"
            className="text-muted hover:text-fg p-1 rounded disabled:cursor-not-allowed disabled:opacity-60"
            aria-label="Open web UI (locked)"
          >
            <ExternalLink size={12} />
          </button>
          <LockedAction label="Manage" />
        </div>
      </td>
    </tr>
  );
}

function DataSourceChip({ source }: { source: PrinterDataSource }) {
  const tone = {
    mock: "border-border text-muted",
    live: "border-accent-green/50 text-accent-green",
    error: "border-accent-red/50 text-accent-red",
  }[source];
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
