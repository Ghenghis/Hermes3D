/**
 * Blender MCP tab — Phase 2 mock-only per TAB_SPECS.md §5.
 *
 * Provider manager · Blender process status · MCP tool capability checklist ·
 * viewport screenshot placeholder · command/safe execution history · 3MF
 * export proof. All "Connect / Validate / Run smoke / Export 3MF / Rollback"
 * actions locked.
 */
import { Panel } from "../components/layout/Panel";
import { StatusBadge } from "../components/badges/StatusBadge";
import { ProofChip } from "../components/badges/ProofChip";
import { LockedAction } from "../components/badges/LockedAction";
import { Check, Box, X } from "lucide-react";
import { LATEST_BUNDLE } from "../data/mock/proof";

const PROVIDERS = [
  { id: "ahujasid", name: "ahujasid (default)", version: "0.6.1", status: "active" },
  { id: "vxai", name: "VxAI (experimental)", version: "0.3.0-rc4", status: "idle" },
  { id: "official", name: "Blender official MCP", version: "1.0", status: "not_installed" },
];

const TOOLS = [
  { name: "scene.list_objects", available: true },
  { name: "scene.get_object_info", available: true },
  { name: "object.set_transform", available: true },
  { name: "object.create_primitive", available: true },
  { name: "mesh.boolean_operation", available: true },
  { name: "export.glb", available: true },
  { name: "export.3mf", available: true },
  { name: "render.viewport_screenshot", available: true },
  { name: "io.import_stl", available: true },
  { name: "io.import_obj", available: false },
];

const HISTORY = [
  { ts: "10:42:18Z", cmd: "scene.list_objects()", result: "12 objects" },
  { ts: "10:41:55Z", cmd: "object.set_transform('Cube', loc=[0,0,0])", result: "ok" },
  { ts: "10:41:30Z", cmd: "export.3mf(path='out/frame-bracket-v3.3mf')", result: "ok · 18420 verts" },
  { ts: "10:40:11Z", cmd: "render.viewport_screenshot()", result: "ok · 1024×1024" },
  { ts: "10:39:00Z", cmd: "scene.get_object_info('Bracket')", result: "dims [42.1, 28.4, 12.0] mm" },
];

export function BlenderMCPTab() {
  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="blender-mcp-root">
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="blender.providers"
          title="PROVIDER MANAGER"
          dense
          status={{ tone: "green", label: "ahujasid active" }}
          className="h-[260px]"
        >
          <ul className="flex flex-col gap-1.5 h-full overflow-auto text-xs">
            {PROVIDERS.map((p) => (
              <li
                key={p.id}
                className={[
                  "px-2 py-1.5 rounded border",
                  p.status === "active"
                    ? "bg-surface2 border-accent-cyan/40"
                    : "bg-surface2/30 border-border",
                ].join(" ")}
              >
                <div className="flex items-center justify-between">
                  <span className="text-fg font-medium truncate">{p.name}</span>
                  <StatusBadge
                    tone={p.status === "active" ? "green" : p.status === "idle" ? "muted" : "amber"}
                    label={p.status}
                  />
                </div>
                <div className="text-muted text-[10px] font-mono mt-0.5">v{p.version}</div>
              </li>
            ))}
            <div className="mt-1 flex justify-end gap-1.5">
              <LockedAction label="Connect" />
              <LockedAction label="Rollback" />
            </div>
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="blender.process"
          title="BLENDER PROCESS"
          dense
          status={{ tone: "green", label: "running" }}
          className="h-[260px]"
        >
          <div className="grid grid-cols-2 gap-2 h-full text-xs">
            <KV k="State" v={<StatusBadge tone="green" label="running" />} />
            <KV k="Version" v="Blender 4.2.3" />
            <KV k="PID" v={<span className="font-mono">14820</span>} />
            <KV k="Uptime" v="00:42:18" />
            <KV k="MCP Bridge" v={<StatusBadge tone="green" label="connected" />} />
            <KV k="Heartbeat" v={<span className="font-mono text-[11px]">10:42:30Z</span>} />
            <div className="col-span-2 flex flex-wrap gap-1.5 mt-1">
              <LockedAction label="Run smoke test" />
              <LockedAction label="Validate tools" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="blender.viewport"
          title="VIEWPORT SCREENSHOT"
          dense
          status={{ tone: "muted", label: "1024×1024" }}
          className="h-[260px]"
        >
          <div className="h-full w-full bg-gradient-to-br from-surface2 to-bg border border-accent-cyan/20 rounded flex items-center justify-center relative overflow-hidden">
            <svg
              viewBox="0 0 100 100"
              className="w-full h-full max-h-[170px] text-accent-cyan drop-shadow-[0_0_4px_rgba(34,211,238,0.4)]"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.5"
              strokeLinejoin="round"
            >
              <polygon points="50,15 85,30 85,75 50,90 15,75 15,30" />
              <line x1="50" y1="15" x2="50" y2="90" strokeOpacity="0.5" />
              <line x1="15" y1="30" x2="85" y2="75" strokeOpacity="0.3" />
              <line x1="85" y1="30" x2="15" y2="75" strokeOpacity="0.3" />
              <circle cx="50" cy="50" r="2" fill="currentColor" />
            </svg>
            <div className="absolute bottom-1.5 right-1.5 text-muted text-[9px] font-mono">
              frame-bracket-v3
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-7">
        <Panel
          id="blender.tools"
          title="TOOL CAPABILITY CHECKLIST"
          dense
          status={{
            tone: "green",
            label: `${TOOLS.filter((t) => t.available).length}/${TOOLS.length} available`,
          }}
          className="h-[230px]"
        >
          <ul className="grid grid-cols-2 gap-x-3 gap-y-1 h-full overflow-auto text-xs">
            {TOOLS.map((t) => (
              <li key={t.name} className="flex items-center gap-2">
                {t.available ? (
                  <Check size={12} className="text-accent-green shrink-0" />
                ) : (
                  <X size={12} className="text-accent-red shrink-0" />
                )}
                <span className="text-fg font-mono truncate flex-1">{t.name}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="blender.export"
          title="3MF EXPORT PROOF"
          dense
          status={{ tone: "green", label: "verified" }}
          headerExtra={<ProofChip status="verified" />}
          className="h-[230px]"
        >
          <div className="flex flex-col gap-2 h-full text-xs">
            <KV k="Last Export" v={<span className="font-mono text-[11px]">frame-bracket-v3.3mf</span>} />
            <KV k="Bundle" v={<span className="font-mono text-accent-cyan text-[11px]">{LATEST_BUNDLE.id}</span>} />
            <KV k="SHA-256" v={<span className="font-mono text-[10px] truncate block">{LATEST_BUNDLE.sha256.slice(0, 32)}…</span>} />
            <KV k="Built" v={<span className="font-mono text-[11px]">{LATEST_BUNDLE.ts_utc}</span>} />
            <div className="mt-auto flex justify-end gap-1.5">
              <LockedAction label="Re-export" />
              <LockedAction label="Download bundle" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12">
        <Panel
          id="blender.history"
          title="COMMAND HISTORY (SAFE EXECUTION)"
          dense
          status={{ tone: "cyan", label: `${HISTORY.length} entries` }}
          headerExtra={<Box size={11} className="text-muted" />}
          className="h-[180px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-[11px]">
            {HISTORY.map((h, i) => (
              <li
                key={i}
                className="flex items-start gap-2 px-1 py-0.5 border-b border-border/30 last:border-0"
              >
                <span className="text-muted font-mono text-[10px] shrink-0">{h.ts}</span>
                <span className="text-fg font-mono flex-1 truncate">{h.cmd}</span>
                <span className="text-accent-green text-[10px] truncate shrink-0">→ {h.result}</span>
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
      <span className="text-fg text-[12px] truncate">{v}</span>
    </div>
  );
}
