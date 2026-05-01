/**
 * Printer Control tab — Phase 2 mock-only per TAB_SPECS.md §9.
 *
 * Printer selector · jog controls · temp controls · G-code console ·
 * EMERGENCY STOP. Per the safety policy:
 *   - All movement and write commands are LOCKED until Phase 6.
 *   - No printer command leaves this UI in Phase 2.
 *   - The big red Emergency Stop is visual-only.
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { MOCK_PRINTERS } from "../data/mock/printers";
import type { PrinterStatus } from "../types/printer";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Home, Lock, Octagon } from "lucide-react";

const PRINTER_TONE: Record<PrinterStatus, StatusTone> = {
  online: "green",
  printing: "cyan",
  paused: "amber",
  maintenance: "amber",
  offline: "muted",
  error: "red",
};

export function PrinterControlTab() {
  const [selectedId, setSelectedId] = useState(MOCK_PRINTERS[0].id);
  const selected = MOCK_PRINTERS.find((p) => p.id === selectedId) ?? MOCK_PRINTERS[0];

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="control-root">
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="control.selector"
          title="PRINTER"
          dense
          status={{ tone: "cyan", label: `${MOCK_PRINTERS.length} units` }}
          className="h-[460px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {MOCK_PRINTERS.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(p.id)}
                  className={[
                    "w-full flex items-center gap-2 px-2 py-1.5 rounded border text-left",
                    p.id === selectedId
                      ? "bg-surface2 border-accent-cyan/40"
                      : "bg-surface2/30 border-border hover:border-accent-cyan/20",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-1.5 w-1.5 rounded-full shrink-0",
                      PRINTER_TONE[p.status] === "green"
                        ? "bg-accent-green"
                        : PRINTER_TONE[p.status] === "cyan"
                          ? "bg-accent-cyan"
                          : PRINTER_TONE[p.status] === "amber"
                            ? "bg-accent-amber"
                            : PRINTER_TONE[p.status] === "red"
                              ? "bg-accent-red"
                              : "bg-muted",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="text-fg flex-1 truncate">{p.name}</span>
                  <StatusBadge tone={PRINTER_TONE[p.status]} label={p.status} />
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="control.jog"
          title={`JOG · ${selected.name}`}
          dense
          status={{ tone: "amber", label: "locked" }}
          headerExtra={<Lock size={11} className="text-accent-amber" />}
          className="h-[300px]"
        >
          <div className="grid grid-cols-2 gap-3 h-full text-xs">
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="text-muted text-[10px] uppercase tracking-wide">XY (mm)</div>
              <div className="grid grid-cols-3 gap-1">
                <div />
                <JogButton><ArrowUp size={14} /></JogButton>
                <div />
                <JogButton><ArrowLeft size={14} /></JogButton>
                <JogButton><Home size={13} /></JogButton>
                <JogButton><ArrowRight size={14} /></JogButton>
                <div />
                <JogButton><ArrowDown size={14} /></JogButton>
                <div />
              </div>
              <div className="flex gap-1 text-[10px] mt-1">
                {[0.1, 1, 10, 100].map((s) => (
                  <span key={s} className="px-1.5 py-0.5 rounded bg-surface2 border border-border text-muted font-mono">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="text-muted text-[10px] uppercase tracking-wide">Z (mm)</div>
              <div className="flex flex-col gap-1">
                <JogButton><ArrowUp size={14} /></JogButton>
                <JogButton><Home size={13} /></JogButton>
                <JogButton><ArrowDown size={14} /></JogButton>
              </div>
              <div className="flex gap-1 text-[10px] mt-1">
                {[0.05, 0.1, 1, 10].map((s) => (
                  <span key={s} className="px-1.5 py-0.5 rounded bg-surface2 border border-border text-muted font-mono">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div className="col-span-2 text-[10px] text-muted text-center border-t border-border pt-2">
              Movement is locked until Phase 6 wires the printer adapter and confirms the safety policy.
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="control.temps"
          title="TEMPERATURES"
          dense
          status={{ tone: "amber", label: "locked" }}
          className="h-[300px]"
        >
          <div className="flex flex-col gap-3 h-full text-xs">
            <TempRow
              label="Hotend"
              actual={selected.temp_hot}
              target={selected.temp_hot != null ? Math.max(selected.temp_hot, 215) : null}
              tone="red"
            />
            <TempRow
              label="Bed"
              actual={selected.temp_bed}
              target={selected.temp_bed != null ? Math.max(selected.temp_bed, 60) : null}
              tone="amber"
            />
            <TempRow label="Chamber" actual={null} target={null} tone="muted" />
            <div className="mt-auto flex flex-wrap gap-1.5">
              <LockedAction label="Set hotend" />
              <LockedAction label="Set bed" />
              <LockedAction label="Cooldown" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="control.gcode"
          title="G-CODE CONSOLE"
          dense
          status={{ tone: "amber", label: "read-only" }}
          className="h-[260px]"
        >
          <div className="flex flex-col gap-2 h-full text-xs">
            <div className="flex-1 bg-bg border border-border rounded p-2 font-mono text-[11px] overflow-auto">
              <div className="text-accent-green">$ M115</div>
              <div className="text-muted">FIRMWARE_NAME:Klipper FIRMWARE_VERSION:v0.12.0</div>
              <div className="text-accent-green">$ M105</div>
              <div className="text-muted">ok T:215.4 /215 B:59.8 /60</div>
              <div className="text-accent-green">$ M114</div>
              <div className="text-muted">X:120.0 Y:120.0 Z:42.30 E:0.000 Count X:9600 Y:9600 Z:8460</div>
              <div className="text-muted opacity-50">— buffer end —</div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted font-mono">$</span>
              <input
                type="text"
                disabled
                placeholder="G-code input locked · adapter phase"
                className="flex-1 bg-surface2/40 border border-border rounded px-2 py-1 text-muted font-mono text-[11px] disabled:cursor-not-allowed"
              />
              <LockedAction label="Send" />
            </div>
            <div className="text-[10px] text-muted">
              Manual G-code requires preview + allowlist/denylist scan + confirmation modal (Phase 6).
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="control.estop"
          title="EMERGENCY STOP"
          dense
          status={{ tone: "red", label: "armed" }}
          className="h-[260px]"
        >
          <div className="h-full flex flex-col items-center justify-center gap-2 text-xs">
            <button
              type="button"
              disabled
              aria-disabled="true"
              title="locked · Phase 6 wires the safety actuator"
              className="h-28 w-28 rounded-full bg-accent-red/15 border-4 border-accent-red text-accent-red flex flex-col items-center justify-center gap-1 cursor-not-allowed shadow-[0_0_30px_rgba(239,68,68,0.25)]"
            >
              <Octagon size={28} />
              <span className="text-[10px] font-bold uppercase">E-STOP</span>
            </button>
            <div className="text-muted text-[10px] text-center max-w-[220px]">
              Cuts heater + motor power. Locked in Phase 2 — Phase 6 wires the actuator to the
              printer adapter.
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function JogButton({ children }: { children: React.ReactNode }) {
  return (
    <button
      type="button"
      disabled
      title="locked · adapter phase"
      className="h-8 w-8 rounded bg-surface2 border border-border text-muted hover:text-fg flex items-center justify-center disabled:cursor-not-allowed disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function TempRow({
  label,
  actual,
  target,
  tone,
}: {
  label: string;
  actual: number | null;
  target: number | null;
  tone: "red" | "amber" | "muted";
}) {
  const barClass = tone === "red" ? "bg-accent-red" : tone === "amber" ? "bg-accent-amber" : "bg-muted";
  const pct = actual != null && target != null && target > 0 ? Math.min(100, (actual / target) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted text-[10px] uppercase tracking-wide w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-surface2 rounded-full overflow-hidden">
        <div className={`h-full ${barClass} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-fg font-mono text-[11px] w-20 text-right shrink-0">
        {actual != null ? `${actual}°` : "—"} / {target != null ? `${target}°` : "—"}
      </span>
    </div>
  );
}
