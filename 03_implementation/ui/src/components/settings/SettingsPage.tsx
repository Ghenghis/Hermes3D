/**
 * Settings landing page backed by the local GUI API.
 *
 * Hosts the four canonical subtabs:
 *   - Providers     · LLM endpoint config (read-only `llm_policy.yaml` view)
 *   - Printers      · 12-printer fleet from `printers.toml` + optional health
 *   - Environment   · env-var presence with values redacted to [set]/[not set]
 *   - About         · version, license, links to GitHub + docs
 *
 * The provider chain itself and the service-health endpoint are owned by
 * other tracks; this page only consumes their public shapes (and gracefully
 * degrades when they're not yet shipped).
 *
 * Subtab routing is internal `useState` — we MUST NOT introduce
 * react-router; the universal shell uses the TABS pattern only.
 */
import { useState } from "react";
import { Bot, Cog, Cpu, Info, Map, Printer as PrinterIcon, Terminal } from "lucide-react";
import { Panel } from "../layout/Panel";
import { ResizablePane } from "../layout/ResizablePane";
import { useStore } from "../../app/store";
import { ProvidersSubtab } from "./ProvidersSubtab";
import { PrintersSubtab } from "./PrintersSubtab";
import { EnvironmentSubtab } from "./EnvironmentSubtab";
import { AboutSubtab } from "./AboutSubtab";
import { AgentConfigSection } from "./AgentConfigSection";

type SubtabKey = "providers" | "agents" | "printers" | "environment" | "about";

const SUBTABS: { key: SubtabKey; label: string; Icon: typeof Cpu; description: string }[] = [
  { key: "providers",   label: "Providers",   Icon: Cpu,         description: "LLM endpoints + policy" },
  { key: "agents",      label: "Agents",      Icon: Bot,         description: "Agent policy preview" },
  { key: "printers",    label: "Printers",    Icon: PrinterIcon, description: "Fleet + health" },
  { key: "environment", label: "Environment", Icon: Terminal,    description: "env-var presence (redacted)" },
  { key: "about",       label: "About",       Icon: Info,        description: "Version + links" },
];

export function SettingsPage() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [active, setActive] = useState<SubtabKey>("providers");
  const meta = SUBTABS.find((s) => s.key === active) ?? SUBTABS[0];

  return (
    <div
      className="flex min-h-[calc(100vh-6.5rem)] min-w-0 flex-col gap-2.5 lg:flex-row"
      data-testid="settings-root"
      data-active-subtab={active}
    >
      <ResizablePane
        storageKey="h3d.settings.subtabRail.width"
        defaultWidth={320}
        minWidth={220}
        maxWidth={540}
        label="Settings sections panel"
        dataTestId="settings-side-rail"
        className="min-h-0 w-full shrink-0 lg:w-[var(--pane-width)]"
      >
        <Panel
          id="settings.subtabs"
          title="SETTINGS"
          dense
          status={{ tone: "muted", label: `${SUBTABS.length} sections` }}
          className="h-full min-h-0"
        >
          <ul
            role="tablist"
            aria-label="Settings sections"
            data-testid="settings-subtablist"
            className="flex flex-col gap-1 h-full overflow-auto text-xs"
          >
            {SUBTABS.map((s) => {
              const Icon = s.Icon;
              const selected = active === s.key;
              return (
                <li key={s.key} role="presentation">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    aria-controls={`settings-panel-${s.key}`}
                    id={`settings-tab-${s.key}`}
                    data-testid={`settings-subtab-${s.key}`}
                    onClick={() => setActive(s.key)}
                    className={[
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded border-l-2 text-left",
                      selected
                        ? "bg-surface2 border-accent-cyan text-fg"
                        : "border-transparent text-muted hover:bg-surface2/60 hover:text-fg",
                    ].join(" ")}
                  >
                    <Icon size={14} className="shrink-0" />
                    <div className="flex flex-col min-w-0">
                      <span className="truncate">{s.label}</span>
                      <span className="text-[10px] text-muted truncate">{s.description}</span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="mt-2 border-t border-border pt-2">
            <button
              type="button"
              onClick={() => setActiveTabId("roadmap")}
              className="flex w-full items-center gap-2 rounded border border-border bg-surface2/40 px-2 py-1.5 text-left text-xs text-muted hover:text-fg"
            >
              <Map size={14} className="shrink-0" />
              <span>Roadmap</span>
            </button>
          </div>
        </Panel>
      </ResizablePane>

      <div className="min-h-0 min-w-0 flex-1">
        <Panel
          id="settings.detail"
          title={meta.label.toUpperCase()}
          dense
          status={{ tone: "cyan", label: "config" }}
          headerExtra={<Cog size={11} className="text-muted" />}
          className="h-full min-h-0"
        >
          <div
            role="tabpanel"
            id={`settings-panel-${active}`}
            aria-labelledby={`settings-tab-${active}`}
            data-testid={`settings-panel-${active}`}
            className="h-full"
          >
            {active === "providers" && <ProvidersSubtab />}
            {active === "agents" && <AgentConfigSection />}
            {active === "printers" && <PrintersSubtab />}
            {active === "environment" && <EnvironmentSubtab />}
            {active === "about" && <AboutSubtab />}
          </div>
        </Panel>
      </div>
    </div>
  );
}
