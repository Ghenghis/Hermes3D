import { Activity, CheckCircle2, CirclePause, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { Panel } from "../layout/Panel";
import type { Agent } from "../../types/agent";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const AGENT_TONE: Record<Agent["status"], StatusTone> = {
  active: "green",
  idle: "muted",
  paused: "amber",
  error: "red",
};

export function AgentCommandCenter({ agents }: { agents: Agent[] }) {
  const active = agents.filter((agent) => agent.status === "active").length;
  const paused = agents.filter((agent) => agent.status === "paused").length;
  const tasks = agents.reduce((sum, agent) => sum + agent.task_count, 0);
  const [message, setMessage] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min">
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="agents.command.roster"
          title="AGENT COMMAND CENTER"
          dense
          status={{ tone: "green", label: `${active} active` }}
          className="h-[360px]"
        >
          {agents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 h-full overflow-auto">
              {agents.map((agent) => (
                <AgentCard key={agent.id} agent={agent} />
              ))}
            </div>
          ) : (
            <EmptyState title="No live agents" detail="The agents API returned no registered agents." />
          )}
        </Panel>
      </div>

      <div className="col-span-12 lg:col-span-4 grid grid-cols-1 gap-2.5">
        <Panel
          id="agents.command.summary"
          title="CONTROL SUMMARY"
          dense
          status={{ tone: paused > 0 ? "amber" : "green", label: `${tasks} tasks` }}
          className="h-[170px]"
        >
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Metric icon={<Activity size={15} />} label="Active" value={String(active)} />
            <Metric icon={<CirclePause size={15} />} label="Paused" value={String(paused)} />
            <Metric icon={<ShieldCheck size={15} />} label="Guarded" value="policy" />
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {["launch-agent", "pause-all", "approve-write"].map((action) => (
              <button key={action} type="button" onClick={() => void runFleetAction(action, setMessage)} className="rounded border border-border px-2 py-1 text-xs text-fg">
                {action.replace("-", " ")}
              </button>
            ))}
          </div>
          {message && <div className="mt-2 rounded border border-border bg-surface2/40 px-2 py-1 text-[10px] text-muted">{message}</div>}
        </Panel>

        <Panel
          id="agents.command.queue"
          title="RUN QUEUE"
          dense
          status={{ tone: tasks > 0 ? "cyan" : "muted", label: `${tasks} tasks` }}
          className="h-[180px]"
        >
          {agents.some((agent) => agent.task_count > 0) ? (
            <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
              {agents.filter((agent) => agent.task_count > 0).map((agent) => (
                <li key={agent.id} className="flex items-center gap-2 rounded border border-border bg-surface2/40 px-2 py-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent-cyan" aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-fg">{agent.role}</span>
                    <span className="block truncate text-[10px] text-muted">{agent.id}</span>
                  </span>
                  <span className="text-[10px] uppercase text-muted">{agent.task_count} tasks</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No queued agent tasks" detail="Live agents report zero assigned tasks." />
          )}
        </Panel>
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <article className="rounded border border-border bg-surface2/40 p-2 text-xs min-w-0">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-semibold text-fg">{agent.role}</div>
          <div className="truncate font-mono text-[10px] text-muted">{agent.id}</div>
        </div>
        <StatusBadge tone={AGENT_TONE[agent.status]} label={agent.status} />
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div>
          <div className="text-[10px] uppercase text-muted">Tasks</div>
          <div className="font-mono text-fg">{agent.task_count}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase text-muted">Provider</div>
          <div className="truncate font-mono text-fg">{agent.model_provider}</div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[10px] text-muted">
        <CheckCircle2 size={11} className="text-accent-green" />
        <span className="truncate">{agent.last_activity_utc}</span>
      </div>
    </article>
  );
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-xs">
      <div className="font-medium text-fg">{title}</div>
      <div className="max-w-[260px] text-muted">{detail}</div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-surface2/40 p-2">
      <div className="flex items-center gap-1.5 text-muted">
        {icon}
        <span className="truncate text-[10px] uppercase">{label}</span>
      </div>
      <div className="mt-1 text-sm font-semibold text-fg">{value}</div>
    </div>
  );
}

async function runFleetAction(actionId: string, setMessage: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/agents/actions/${encodeURIComponent(actionId)}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "operator requested from agent command center" }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    setMessage(`${response.ok && actionAccepted(payload) ? "Accepted" : "Blocked"}: ${actionSummary(payload, response.statusText)}`);
  } catch {
    setMessage(`Blocked: agents backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

function actionAccepted(payload: unknown): boolean {
  if (!isRecord(payload)) {
    return true;
  }
  if (payload.accepted === false || payload.saved === false || payload.success === false || payload.ok === false) {
    return false;
  }
  return !["not_configured", "blocked", "failed", "error", "unreachable"].includes(String(payload.status ?? ""));
}

function actionSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return fallback || "No response body.";
  }
  return String(payload.reason ?? payload.status ?? fallback);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
