/**
 * Slicing tab — Phase 2 mock-only per TAB_SPECS.md §6.
 *
 * File queue · slicer selector · profile selector per printer · slice output
 * cards · validation results. All "Launch external slicer / Dry-run slice /
 * Import-export profile" actions locked.
 */
import { Panel } from "../components/layout/Panel";
import { StatusBadge } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { Layers, FileBox } from "lucide-react";
import { MOCK_PRINTERS } from "../data/mock/printers";

const QUEUE = [
  { id: "f-01", name: "frame-bracket-v3.stl", size_kb: 412, status: "queued" },
  { id: "f-02", name: "spindle-housing.obj", size_kb: 1024, status: "queued" },
  { id: "f-03", name: "calibration-cube.3mf", size_kb: 56, status: "sliced" },
  { id: "f-04", name: "demo-cube.stl", size_kb: 12, status: "sliced" },
];

const SLICERS = [
  { id: "flsun", name: "FLSUN Slicer", version: "1.4.2", active: false },
  { id: "prusa", name: "PrusaSlicer", version: "2.8.1", active: true },
  { id: "orca", name: "OrcaSlicer", version: "2.1.1", active: false },
  { id: "cura", name: "Cura", version: "5.8.0", active: false },
];

const SLICE_OUTPUTS = [
  {
    id: "out-001",
    file: "calibration-cube.gcode",
    profile: "FLSUN-T1-PLA",
    layers: 250,
    duration_min: 18,
    weight_g: 4.1,
    validated: true,
  },
  {
    id: "out-002",
    file: "demo-cube.gcode",
    profile: "FLSUN-T1-PLA",
    layers: 80,
    duration_min: 6,
    weight_g: 1.2,
    validated: true,
  },
];

export function SlicingTab() {
  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="slicing-root">
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="slicing.queue"
          title="FILE QUEUE"
          dense
          status={{ tone: "cyan", label: `${QUEUE.length} files` }}
          className="h-[280px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {QUEUE.map((f) => (
              <li
                key={f.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded bg-surface2/40 border border-border"
              >
                <FileBox size={13} className="text-muted shrink-0" />
                <span className="text-fg font-mono truncate flex-1">{f.name}</span>
                <span className="text-muted text-[10px] font-mono shrink-0">
                  {f.size_kb} KB
                </span>
                <StatusBadge tone={f.status === "sliced" ? "green" : "muted"} label={f.status} />
              </li>
            ))}
            <div className="mt-1 flex justify-end gap-1.5">
              <LockedAction label="Add file" />
              <LockedAction label="Dry-run slice" />
            </div>
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="slicing.slicer"
          title="SLICER"
          dense
          status={{ tone: "cyan", label: SLICERS.find((s) => s.active)?.name ?? "—" }}
          className="h-[280px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {SLICERS.map((s) => (
              <li
                key={s.id}
                className={[
                  "flex items-center gap-2 px-2 py-1.5 rounded border",
                  s.active ? "bg-surface2 border-accent-cyan/40" : "bg-surface2/30 border-border",
                ].join(" ")}
              >
                <span
                  className={[
                    "h-1.5 w-1.5 rounded-full shrink-0",
                    s.active ? "bg-accent-cyan" : "bg-muted",
                  ].join(" ")}
                  aria-hidden
                />
                <div className="flex-1 min-w-0 leading-tight">
                  <div className="text-fg font-medium truncate">{s.name}</div>
                  <div className="text-muted text-[10px] font-mono">v{s.version}</div>
                </div>
              </li>
            ))}
            <div className="mt-1">
              <LockedAction label="Launch (docked)" hint="locked · Phase 6 wires real slicer launch" />
            </div>
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="slicing.profiles"
          title="PROFILES"
          dense
          status={{ tone: "muted", label: `${MOCK_PRINTERS.length} printers` }}
          className="h-[280px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {MOCK_PRINTERS.slice(0, 6).map((p) => (
              <li
                key={p.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded bg-surface2/40 border border-border"
              >
                <Layers size={12} className="text-muted shrink-0" />
                <div className="flex-1 min-w-0 leading-tight">
                  <div className="text-fg truncate">{p.name}</div>
                  <div className="text-muted text-[10px] font-mono">{p.model}-PLA-0.2mm</div>
                </div>
                <StatusBadge tone="green" label="loaded" />
              </li>
            ))}
            <div className="mt-1 flex justify-end gap-1.5">
              <LockedAction label="Import" />
              <LockedAction label="Export" />
            </div>
          </ul>
        </Panel>
      </div>
      <div className="col-span-12">
        <Panel
          id="slicing.outputs"
          title="SLICE OUTPUTS"
          dense
          status={{ tone: "green", label: `${SLICE_OUTPUTS.length} ready` }}
          className="h-[260px]"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 h-full overflow-auto">
            {SLICE_OUTPUTS.map((o) => (
              <div key={o.id} className="bg-surface2/40 border border-border rounded p-2.5 flex flex-col gap-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-fg font-mono font-medium truncate">{o.file}</span>
                  <StatusBadge tone={o.validated ? "green" : "amber"} label={o.validated ? "validated" : "pending"} />
                </div>
                <div className="grid grid-cols-3 gap-2 text-[11px]">
                  <KV k="Profile" v={<span className="font-mono">{o.profile}</span>} />
                  <KV k="Layers" v={String(o.layers)} />
                  <KV k="ETA" v={`${o.duration_min} min`} />
                  <KV k="Weight" v={`${o.weight_g.toFixed(1)} g`} />
                  <KV k="Validation" v={<span className="text-accent-green">G-code OK</span>} />
                  <KV k="Allowlist" v={<span className="text-accent-green">passed</span>} />
                </div>
                <div className="flex flex-wrap gap-1.5 mt-auto">
                  <LockedAction label="Send to printer" hint="locked · Phase 6 wires printer adapters" />
                  <LockedAction label="Re-slice" />
                </div>
              </div>
            ))}
          </div>
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
