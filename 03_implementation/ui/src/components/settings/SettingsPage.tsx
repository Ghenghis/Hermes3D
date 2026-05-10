/**
 * Settings landing page backed by the local GUI API.
 *
 * Hosts the eight canonical subtabs:
 *   - General       · theme, language, defaults
 *   - Providers     · LLM endpoint config (read-only `llm_policy.yaml` view)
 *   - Agents        · agent policy preview
 *   - MCP           · active MCP file locks
 *   - Printers      · 12-printer fleet from `printers.toml` + optional health
 *   - Environment   · env-var presence with values redacted to [set]/[not set]
 *   - Updates       · update center, version + rollback
 *   - About         · version, license, links to GitHub + docs
 *
 * Subtab routing (W15-A17): the URL hash is authoritative — visiting
 * `#settings/<sub>` selects the matching subtab; clicking a subtab
 * replaces the hash with `#settings/<sub>`. We use `replaceState` (not
 * `pushState`) so navigating subtabs doesn't pollute browser history.
 * The provider chain itself and the service-health endpoint are owned by
 * other tracks; this page only consumes their public shapes (and gracefully
 * degrades when they're not yet shipped).
 *
 * Subtab routing follows the same `#<tab>/<sub>` pattern AppRegistry uses
 * (`#apps/<id>`). No react-router; the universal shell uses TABS only.
 */
import { useEffect, useState } from "react";
import {
  Bot,
  Cog,
  Cpu,
  Info,
  Lock,
  Map,
  MonitorCog,
  Package,
  Printer as PrinterIcon,
  Terminal,
} from "lucide-react";
import { Panel } from "../layout/Panel";
import { ResizablePane } from "../layout/ResizablePane";
import {
  SETTINGS_SUBTAB_KEYS,
  settingsSubtabFromHash,
  useStore,
  type SettingsSubtabKey,
} from "../../app/store";
import { GeneralSubtab } from "./GeneralSubtab";
import { ProvidersSubtab } from "./ProvidersSubtab";
import { PrintersSubtab } from "./PrintersSubtab";
import { EnvironmentSubtab } from "./EnvironmentSubtab";
import { AboutSubtab } from "./AboutSubtab";
import { AgentConfigSection } from "./AgentConfigSection";
import { UpdateCenterSubtab } from "./UpdateCenterSubtab";
import { McpSubtab } from "./McpSubtab";

type SubtabKey = SettingsSubtabKey;

const SETTINGS_HASH_PREFIX = "settings";
const DEFAULT_SUBTAB: SubtabKey = "general";

const SUBTABS: { key: SubtabKey; label: string; Icon: typeof Cpu; description: string }[] = [
  { key: "general",     label: "General",       Icon: MonitorCog,  description: "Theme, language, defaults" },
  { key: "providers",   label: "Providers",     Icon: Cpu,         description: "LLM endpoints + policy" },
  { key: "agents",      label: "Agents",        Icon: Bot,         description: "Agent policy preview" },
  { key: "mcp",         label: "MCP",           Icon: Lock,        description: "Active MCP file locks" },
  { key: "printers",    label: "Printers",      Icon: PrinterIcon, description: "Fleet + health" },
  { key: "environment", label: "Environment",   Icon: Terminal,    description: "env-var presence (redacted)" },
  { key: "updates",     label: "Update Center", Icon: Package,     description: "Versions, updater, rollback" },
  { key: "about",       label: "About",         Icon: Info,        description: "Version + links" },
];

// Defensive: enforce SUBTABS and SETTINGS_SUBTAB_KEYS stay in sync at
// load time so reorderings here trip a console warning in dev instead of
// silently breaking the URL contract. `import.meta.env.DEV` is the Vite
// compile-time flag; we guard the access so non-Vite consumers (Jest)
// don't choke on the missing import.meta.
const __isDev: boolean =
  typeof import.meta !== "undefined" &&
  (import.meta as { env?: { DEV?: boolean } }).env?.DEV === true;
if (__isDev && SUBTABS.length !== SETTINGS_SUBTAB_KEYS.length) {
  // eslint-disable-next-line no-console
  console.warn(
    `[SettingsPage] SUBTABS (${SUBTABS.length}) and SETTINGS_SUBTAB_KEYS (${SETTINGS_SUBTAB_KEYS.length}) length mismatch`,
  );
}

function readInitialSubtab(): SubtabKey {
  if (typeof window === "undefined") return DEFAULT_SUBTAB;
  return settingsSubtabFromHash(window.location.hash) ?? DEFAULT_SUBTAB;
}

export function SettingsPage() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [active, setActive] = useState<SubtabKey>(readInitialSubtab);

  // Sync the subtab selection FROM the URL hash so deep links and the
  // back/forward buttons select the correct subtab. The interval is a
  // safety-net for environments that swallow hashchange (Playwright on
  // some Firefox builds); 500ms matches App.tsx's tab-level cadence.
  useEffect(() => {
    const sync = () => {
      const next = settingsSubtabFromHash(window.location.hash);
      if (next && next !== active) setActive(next);
    };
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    const timer = window.setInterval(sync, 500);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
      window.clearInterval(timer);
    };
  }, [active]);

  // Sync the URL hash TO the subtab selection. We use replaceState so
  // navigating subtabs doesn't bloat browser history — mirrors the
  // tab-level logic in App.tsx.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const desired = `#${SETTINGS_HASH_PREFIX}/${active}`;
    if (window.location.hash === desired) return;
    // Only rewrite when the head segment is "settings" — never clobber
    // a hash that points at a different tab (the user may have just
    // clicked the sidebar).
    const head = window.location.hash.replace(/^#/, "").split(/[/:.]/, 1)[0];
    if (head && head !== SETTINGS_HASH_PREFIX) return;
    window.history.replaceState(null, "", desired);
  }, [active]);

  const handleSelect = (key: SubtabKey) => {
    setActive(key);
    if (typeof window !== "undefined") {
      const next = `#${SETTINGS_HASH_PREFIX}/${key}`;
      if (window.location.hash !== next) {
        window.history.replaceState(null, "", next);
        // Fire hashchange so AgentChatMirror and any other listeners
        // see the navigation; replaceState alone does not emit it.
        try {
          window.dispatchEvent(new HashChangeEvent("hashchange"));
        } catch {
          /* JSDOM occasionally fails to construct HashChangeEvent */
        }
      }
    }
  };

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
                    onClick={() => handleSelect(s.key)}
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
            {active === "general" && <GeneralSubtab />}
            {active === "providers" && <ProvidersSubtab />}
            {active === "agents" && <AgentConfigSection />}
            {active === "mcp" && <McpSubtab />}
            {active === "printers" && <PrintersSubtab />}
            {active === "environment" && <EnvironmentSubtab />}
            {active === "updates" && <UpdateCenterSubtab />}
            {active === "about" && <AboutSubtab />}
          </div>
        </Panel>
      </div>
    </div>
  );
}
