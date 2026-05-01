/**
 * Agents tab — Phase 2 mock-only per TAB_SPECS.md §2.
 *
 * Roster · selected agent details · live activity log · model/provider
 * selector · action row (all dangerous actions locked).
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { MOCK_AGENTS } from "../data/mock/agents";
import type { Agent } from "../types/agent";

const AGENT_TONE: Record<Agent["status"], StatusTone> = {
  active: "green",
  idle: "muted",
  paused: "amber",
  error: "red",
};

const PROVIDER_OPTIONS = [
  "ollama/llama3.1:8b",
  "ollama/qwen2.5-coder:14b",
  "openai/gpt-4o-mini",
  "anthropic/claude-haiku-4-5",
  "blender-mcp/ahujasid",
];

export function AgentsTab() {
  const [selectedId, setSelectedId] = useState<string>(MOCK_AGENTS[0].id);
  const selected = MOCK_AGENTS.find((a) => a.id === selectedId) ?? MOCK_AGENTS[0];

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="agents-root">
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="agents.roster"
          title="AGENT ROSTER"
          dense
          status={{
            tone: "green",
            label: `${MOCK_AGENTS.filter((a) => a.status === "active").length}/${MOCK_AGENTS.length}`,
          }}
          className="h-[480px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto">
            {MOCK_AGENTS.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(a.id)}
                  className={[
                    "w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors text-left",
                    a.id === selectedId
                      ? "bg-surface2 border border-accent-cyan/40"
                      : "border border-transparent hover:bg-surface2/60",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-2 w-2 rounded-full shrink-0",
                      a.status === "active"
                        ? "bg-accent-green"
                        : a.status === "paused"
                          ? "bg-accent-amber"
                          : a.status === "error"
                            ? "bg-accent-red"
                            : "bg-muted",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="text-fg flex-1 truncate font-medium">{a.role}</span>
                  <span className="text-muted text-[10px] uppercase">{a.status}</span>
                  <span className="text-muted text-[10px] font-mono w-6 text-right">{a.task_count}</span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-7 grid grid-cols-1 gap-2.5">
        <Panel
          id="agents.detail"
          title={`SELECTED · ${selected.role.toUpperCase()}`}
          dense
          status={{ tone: AGENT_TONE[selected.status], label: selected.status }}
          className="h-[230px]"
        >
          <div className="grid grid-cols-2 gap-3 h-full text-xs">
            <KV k="Role" v={selected.role} />
            <KV k="Status" v={<StatusBadge tone={AGENT_TONE[selected.status]} label={selected.status} />} />
            <KV k="Tasks Assigned" v={String(selected.task_count)} />
            <KV k="Model / Provider" v={<span className="font-mono">{selected.model_provider}</span>} />
            <KV
              k="Last Activity"
              v={<span className="font-mono text-[11px]">{selected.last_activity_utc}</span>}
            />
            <KV k="Agent ID" v={<span className="font-mono text-[11px]">{selected.id}</span>} />
            <div className="col-span-2 mt-1 flex flex-wrap gap-1.5">
              <LockedAction label="Pause" />
              <LockedAction label="Resume" />
              <LockedAction label="Retry" />
              <LockedAction label="Handoff" />
              <LockedAction label="Request Proof" />
            </div>
          </div>
        </Panel>
        <div className="grid grid-cols-2 gap-2.5">
          <Panel
            id="agents.activity"
            title="LIVE TASK LOG"
            dense
            status={{ tone: "cyan", label: "streaming" }}
            className="h-[240px]"
          >
            <ul className="flex flex-col gap-1 h-full overflow-auto text-[11px]">
              {[...MOCK_AGENTS]
                .sort((a, b) => b.last_activity_utc.localeCompare(a.last_activity_utc))
                .map((a) => (
                  <li key={a.id} className="flex items-start gap-2 py-0.5">
                    <span
                      className={[
                        "h-1.5 w-1.5 rounded-full mt-1 shrink-0",
                        a.status === "active" ? "bg-accent-green" : a.status === "paused" ? "bg-accent-amber" : a.status === "error" ? "bg-accent-red" : "bg-muted",
                      ].join(" ")}
                      aria-hidden
                    />
                    <span className="text-muted font-mono text-[10px] shrink-0">
                      {a.last_activity_utc.split("T")[1]?.slice(0, 8)}
                    </span>
                    <span className="text-fg flex-1 truncate">
                      <span className="font-medium">{a.role}</span> · {a.model_provider}
                    </span>
                  </li>
                ))}
            </ul>
          </Panel>
          <Panel
            id="agents.provider"
            title="MODEL / PROVIDER"
            dense
            status={{ tone: "muted", label: "selector" }}
            className="h-[240px]"
          >
            <div className="flex flex-col gap-1 h-full overflow-auto text-xs">
              {PROVIDER_OPTIONS.map((p) => (
                <div
                  key={p}
                  className={[
                    "flex items-center gap-2 px-2 py-1.5 rounded border",
                    p === selected.model_provider
                      ? "bg-surface2 border-accent-cyan/40"
                      : "border-border bg-surface2/30",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-1.5 w-1.5 rounded-full",
                      p === selected.model_provider ? "bg-accent-cyan" : "bg-muted",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="text-fg font-mono flex-1 truncate">{p}</span>
                  {p === selected.model_provider && (
                    <span className="text-accent-cyan text-[10px] uppercase">active</span>
                  )}
                </div>
              ))}
              <div className="mt-1 flex justify-end">
                <LockedAction label="Apply selection" />
              </div>
            </div>
          </Panel>
        </div>
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
