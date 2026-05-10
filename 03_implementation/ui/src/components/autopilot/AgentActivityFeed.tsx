/**
 * AgentActivityFeed — Wave 15 A14.
 *
 * Display widget for live agent activity. Reads `Agent[]` from
 * `adapters.getAgents()` (which hits `/api/agents`) and surfaces a
 * compact, honest view of which agents are active right now.
 *
 * Strict rules:
 *   - No fake fallback data.
 *   - No write actions — read-only feed.
 */
import { useEffect, useState } from "react";
import { adapters } from "../../api/adapters";
import type { Agent, AgentStatus } from "../../types/agent";

type LoadState = "loading" | "ready" | "error";

export interface AgentActivityFeedProps {
  agents?: Agent[];
}

export function AgentActivityFeed({ agents: propAgents }: AgentActivityFeedProps = {}) {
  const [agents, setAgents] = useState<Agent[]>(propAgents ?? []);
  const [state, setState] = useState<LoadState>(propAgents ? "ready" : "loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (propAgents) {
      setAgents(propAgents);
      setState("ready");
      return;
    }
    let mounted = true;
    const load = () => {
      adapters
        .getAgents()
        .then((next) => {
          if (!mounted) {
            return;
          }
          setAgents(next);
          setState("ready");
          setErrorMsg(null);
        })
        .catch((error) => {
          if (!mounted) {
            return;
          }
          setState("error");
          setErrorMsg(error instanceof Error ? error.message : "agents API unreachable");
        });
    };
    load();
    const timer = window.setInterval(load, 20_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [propAgents]);

  // Sort: active first, then paused, then idle, then error.
  const sorted = [...agents].sort((a, b) => statusWeight(a.status) - statusWeight(b.status));
  const activeCount = agents.filter((a) => a.status === "active").length;

  return (
    <section
      id="autopilot.agent_activity"
      data-testid="autopilot-agent-activity"
      className="flex min-h-0 flex-col rounded border border-border bg-surface p-4"
    >
      <header className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">AGENT ACTIVITY</h2>
          <p className="text-xs text-muted">Live agent roster from /api/agents.</p>
        </div>
        <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted" data-testid="autopilot-agent-activity-count">
          {state === "loading" ? "loading…" : `${activeCount}/${agents.length} active`}
        </span>
      </header>
      <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
        {state === "error" && (
          <div className="rounded border border-amber-700/60 bg-amber-950/30 p-3 text-xs text-amber-100">
            Blocked: agents endpoint unreachable. {errorMsg ?? ""}
          </div>
        )}
        {state === "ready" && agents.length === 0 && (
          <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
            No agents returned by the live agents API.
          </div>
        )}
        {sorted.map((agent) => (
          <article
            key={agent.id}
            data-testid="autopilot-agent-activity-row"
            data-agent-id={agent.id}
            data-agent-status={agent.status}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded border border-border bg-bg/40 px-3 py-2 text-sm"
          >
            <span
              aria-label={`status ${agent.status}`}
              className={`h-2 w-2 rounded-full ${statusDot(agent.status)}`}
            />
            <div className="min-w-0">
              <div className="truncate font-medium text-fg">{agent.role}</div>
              <div className="truncate text-xs text-muted">
                {agent.task_count} task{agent.task_count === 1 ? "" : "s"} ·{" "}
                <span className="font-mono">{agent.model_provider || "—"}</span>
              </div>
            </div>
            <span className="rounded bg-surface2 px-2 py-1 text-[10px] uppercase text-muted">
              {agent.last_activity_utc
                ? new Date(agent.last_activity_utc).toLocaleTimeString()
                : "—"}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function statusWeight(status: AgentStatus): number {
  if (status === "active") return 0;
  if (status === "paused") return 1;
  if (status === "idle") return 2;
  return 3; // error
}

function statusDot(status: AgentStatus): string {
  if (status === "active") return "bg-accent-green";
  if (status === "paused") return "bg-amber-400";
  if (status === "error") return "bg-red-500";
  return "bg-muted";
}
