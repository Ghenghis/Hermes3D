/**
 * Settings tab — Phase 2 mock-only per TAB_SPECS.md §13.
 *
 * Sections: AI providers · Blender MCP providers · external repo registry ·
 * slicers · printer adapters · dock/undock · OTA · safety · theme. All Save
 * actions locked — Phase 6 wires the config-diff + validation pipeline.
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { LockedAction } from "../components/badges/LockedAction";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import {
  Bot,
  Box,
  Cog,
  Download,
  Layers as LayersIcon,
  Layout,
  Palette,
  Printer as PrinterIcon,
  ShieldCheck,
  Wrench,
} from "lucide-react";

type SectionKey =
  | "ai_providers"
  | "blender_mcp"
  | "repo_registry"
  | "slicers"
  | "printer_adapters"
  | "dock_undock"
  | "ota"
  | "safety"
  | "theme";

const SECTIONS: { key: SectionKey; label: string; Icon: typeof Bot }[] = [
  { key: "ai_providers",     label: "AI Providers",      Icon: Bot },
  { key: "blender_mcp",      label: "Blender MCP",       Icon: Box },
  { key: "repo_registry",    label: "External Repo Registry", Icon: Wrench },
  { key: "slicers",          label: "Slicers",           Icon: LayersIcon },
  { key: "printer_adapters", label: "Printer Adapters",  Icon: PrinterIcon },
  { key: "dock_undock",      label: "Dock / Undock",     Icon: Layout },
  { key: "ota",              label: "OTA / Update Policy", Icon: Download },
  { key: "safety",           label: "Safety Policy",     Icon: ShieldCheck },
  { key: "theme",            label: "Theme",             Icon: Palette },
];

const KEYS_BY_SECTION: Record<SectionKey, { k: string; v: string; tone: StatusTone }[]> = {
  ai_providers: [
    { k: "Default model", v: "ollama/llama3.1:8b", tone: "cyan" },
    { k: "Coder model", v: "ollama/qwen2.5-coder:14b", tone: "cyan" },
    { k: "Reviewer model", v: "anthropic/claude-haiku-4-5", tone: "cyan" },
    { k: "Cloud fallback", v: "openai/gpt-4o-mini", tone: "muted" },
  ],
  blender_mcp: [
    { k: "Active provider", v: "ahujasid v0.6.1", tone: "green" },
    { k: "Experimental", v: "VxAI v0.3.0-rc4", tone: "muted" },
    { k: "Bridge port", v: "9876 (loopback)", tone: "cyan" },
    { k: "Auto-reconnect", v: "enabled", tone: "green" },
  ],
  repo_registry: [
    { k: "Validator", v: "registry_validator.py", tone: "green" },
    { k: "Last validation", v: "2026-05-01T08:14:31Z", tone: "green" },
    { k: "Status", v: "all entries verified", tone: "green" },
    { k: "Schema", v: "external_repos_registry.schema.json", tone: "muted" },
  ],
  slicers: [
    { k: "Default", v: "PrusaSlicer 2.8.1", tone: "cyan" },
    { k: "FLSUN Slicer", v: "1.4.2", tone: "muted" },
    { k: "OrcaSlicer", v: "2.1.1", tone: "muted" },
    { k: "Cura", v: "5.8.0", tone: "muted" },
  ],
  printer_adapters: [
    { k: "Moonraker", v: "v0.9.0 · 8 units", tone: "cyan" },
    { k: "OctoPrint", v: "v1.10.3 · 2 units", tone: "blue" },
    { k: "Printrun", v: "v2.0.0rc8 · 1 unit", tone: "amber" },
    { k: "Manual", v: "1 unit", tone: "muted" },
  ],
  dock_undock: [
    { k: "Default mode", v: "docked", tone: "cyan" },
    { k: "Allow undocked", v: "yes", tone: "green" },
    { k: "Allow fullscreen", v: "CSS-only overlay", tone: "cyan" },
    { k: "External launch", v: "locked in Phase 2", tone: "amber" },
  ],
  ota: [
    { k: "Channel", v: "stable", tone: "cyan" },
    { k: "Auto-check", v: "weekly", tone: "muted" },
    { k: "Auto-apply", v: "manual confirm only", tone: "amber" },
    { k: "Last check", v: "2026-04-30T22:00:00Z", tone: "muted" },
  ],
  safety: [
    { k: "Confirmation modals", v: "required for moves", tone: "green" },
    { k: "G-code allowlist", v: "enabled", tone: "green" },
    { k: "G-code denylist", v: "enabled", tone: "green" },
    { k: "Write-mode", v: "DISABLED until Phase 6", tone: "amber" },
    { k: "Proof on every action", v: "enabled", tone: "green" },
  ],
  theme: [
    { k: "Mode", v: "dark (default)", tone: "cyan" },
    { k: "Accent", v: "cyan #22d3ee", tone: "cyan" },
    { k: "Density", v: "dense (Dashboard)", tone: "cyan" },
    { k: "Light theme", v: "not available in Phase 2", tone: "muted" },
  ],
};

export function SettingsTab() {
  const [section, setSection] = useState<SectionKey>("ai_providers");
  const rows = KEYS_BY_SECTION[section];
  const sectionMeta = SECTIONS.find((s) => s.key === section)!;
  const Icon = sectionMeta.Icon;

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="settings-root">
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="settings.sections"
          title="SECTIONS"
          dense
          status={{ tone: "muted", label: `${SECTIONS.length} groups` }}
          className="h-[460px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {SECTIONS.map((s) => {
              const SectionIcon = s.Icon;
              return (
                <li key={s.key}>
                  <button
                    type="button"
                    onClick={() => setSection(s.key)}
                    className={[
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded border-l-2 text-left",
                      section === s.key
                        ? "bg-surface2 border-accent-cyan text-fg"
                        : "border-transparent text-muted hover:bg-surface2/60 hover:text-fg",
                    ].join(" ")}
                  >
                    <SectionIcon size={14} className="shrink-0" />
                    <span className="truncate">{s.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-9">
        <Panel
          id="settings.detail"
          title={sectionMeta.label.toUpperCase()}
          dense
          status={{ tone: "cyan", label: "config" }}
          headerExtra={<Cog size={11} className="text-muted" />}
          className="h-[460px]"
        >
          <div className="flex flex-col gap-3 h-full text-xs">
            <div className="flex items-center gap-2 text-muted">
              <Icon size={14} />
              <span className="text-fg font-medium">{sectionMeta.label}</span>
              <span className="text-[10px]">·</span>
              <span className="text-[10px]">visual-only · Phase 6 wires save + validation</span>
            </div>
            <ul className="flex-1 overflow-auto flex flex-col gap-1.5">
              {rows.map((r) => (
                <li
                  key={r.k}
                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
                >
                  <span className="text-muted text-[10px] uppercase tracking-wide w-44 shrink-0 truncate">
                    {r.k}
                  </span>
                  <span className="text-fg font-mono text-[11px] flex-1 truncate">{r.v}</span>
                  <StatusBadge tone={r.tone} label="set" />
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <span className="text-muted text-[10px]">
                Settings changes produce a config diff + validation report before save (Phase 6).
              </span>
              <div className="flex gap-1.5">
                <LockedAction label="Reset section" />
                <LockedAction label="Save changes" hint="locked · Phase 6 wires the validator + writer" />
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
