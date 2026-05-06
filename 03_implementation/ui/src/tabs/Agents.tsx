/**
 * Agents tab.
 *
 * Roster · selected agent details · live activity log · model/provider
 * selector · action row (all dangerous actions locked).
 */
import { useEffect, useState } from "react";
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { AgentCommandCenter } from "../components/agents/AgentCommandCenter";
import { NotificationCenter } from "../components/notifications/NotificationCenter";
import { adapters } from "../api/adapters";
import type { Agent } from "../types/agent";
import type { AgentActionCatalog, AgentActionContract } from "../types/agent-actions";
import type { IdleWorkbenchState } from "../types/learning";
import type { Notification } from "../types/notification";

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

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;
const DEFAULT_WORKBENCH: IdleWorkbenchState = {
  status: "loading",
  review_policy: "Loading idle workbench policy from the local API.",
  blockers: [],
  candidates: [],
  daily_prompt: {
    question: "What should Hermes3D improve while idle?",
    last_candidate_at: null,
    suggested_kinds: [],
  },
};
const RUNNABLE_OPERATOR_ACTIONS = new Set([
  "agents.health.refresh",
  "dashboard.snapshot.refresh",
  "source.modules.refresh",
  "source.verify_all",
  "source.plan_setup_queue",
  "source.update_readiness.refresh",
  "source.runtime_gaps.refresh",
  "source.verifiers.refresh",
  "source.agent_cli_readiness.refresh",
  "source.cli_surface.refresh",
  "settings.runtime_readiness.refresh",
  "providers.health.refresh",
  "learning.idle_workbench.refresh",
  "printers.refresh",
  "observe.cameras.refresh",
  "autopilot.guardrails.refresh",
  "design.toolchain.refresh",
  "generation.services.refresh",
  "jobs.list.refresh",
  "artifacts.list.refresh",
  "approvals.list.refresh",
  "plugins.list.refresh",
  "notifications.list.refresh",
  "proof.bundles.refresh",
  "workflows.list.refresh",
  "voice.catalog.refresh",
  "voice.agents.refresh",
  "roadmap.operator_coverage.refresh",
]);
type PlaywrightProofScope = "observe" | "smoke" | "full";
type PlaywrightProofResult = {
  accepted?: boolean;
  status?: string;
  scope?: string;
  exit_code?: number;
  artifact_id?: string;
  proof_event_id?: string;
  reason?: string;
};

export function AgentsTab() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [workbench, setWorkbench] = useState<IdleWorkbenchState>(DEFAULT_WORKBENCH);
  const [actionCatalog, setActionCatalog] = useState<AgentActionCatalog | null>(null);
  const [workbenchMessage, setWorkbenchMessage] = useState("Idle workbench loading.");
  const [operatorMessage, setOperatorMessage] = useState("Loading Hermes Agent OS coverage.");
  const [operatorBusy, setOperatorBusy] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [proofRunScope, setProofRunScope] = useState<PlaywrightProofScope>("observe");
  const [proofRunBusy, setProofRunBusy] = useState(false);
  const [proofRunMessage, setProofRunMessage] = useState("Hermes Agent Playwright proof runner is ready for observe, smoke, or full UI checks.");
  const [providerDraft, setProviderDraft] = useState("");
  const selected = agents.find((a) => a.id === selectedId) ?? agents[0] ?? null;

  useEffect(() => {
    let mounted = true;
    void Promise.all([adapters.getAgents(), adapters.getNotifications()])
      .then(([nextAgents, nextNotifications]) => {
        if (!mounted) return;
        setAgents(nextAgents);
        setNotifications(nextNotifications);
        setSelectedId((current) => current ?? nextAgents[0]?.id ?? null);
        setLoadState("ready");
      })
      .catch(() => {
        if (!mounted) return;
        setAgents([]);
        setNotifications([]);
        setLoadState("unavailable");
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    void adapters.getIdleWorkbench()
      .then((next) => {
        if (!mounted) return;
        setWorkbench(next);
        setWorkbenchMessage(`${next.candidates.length} candidate${next.candidates.length === 1 ? "" : "s"} · ${next.blockers.length} blocker${next.blockers.length === 1 ? "" : "s"}.`);
      })
      .catch((error) => {
        if (!mounted) return;
        setWorkbench(DEFAULT_WORKBENCH);
        setWorkbenchMessage(`Idle workbench unavailable: ${error instanceof Error ? error.message : "backend error"}`);
      });
    void adapters.getAgentActionCatalog()
      .then((catalog) => {
        if (!mounted) return;
        setActionCatalog(catalog);
        setOperatorMessage(`${catalog.counts.ready ?? 0} ready · ${(catalog.counts.partial ?? 0) + (catalog.counts.blocked ?? 0)} gaps.`);
      })
      .catch((error) => {
        if (!mounted) return;
        setActionCatalog(null);
        setOperatorMessage(`Operator coverage unavailable: ${error instanceof Error ? error.message : "backend error"}`);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (selectedId && !agents.some((agent) => agent.id === selectedId)) {
      setSelectedId(agents[0]?.id ?? null);
    }
  }, [agents, selectedId]);

  const activeAgents = agents.filter((a) => a.status === "active").length;
  const selectedProvider = selected?.model_provider ?? "";

  useEffect(() => {
    setProviderDraft(selectedProvider);
  }, [selectedProvider]);

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="agents-root">
      <div className="col-span-12">
        <AgentCommandCenter agents={agents} />
      </div>
      <div className="col-span-12">
        <Panel
          id="agents.operator-coverage"
          title="FULL OS OPERATOR COVERAGE"
          dense
          status={{ tone: actionCatalog?.status === "ready" ? "green" : "amber", label: operatorMessage }}
          className="min-h-[172px]"
        >
          {actionCatalog ? (
            <div className="grid gap-2 text-xs xl:grid-cols-[1.2fr_1fr]">
              <div className="rounded border border-border bg-bg/40 p-2">
                <div className="text-[10px] uppercase text-muted">Agent coverage contract</div>
                <div className="mt-1 leading-5 text-fg">{actionCatalog.summary}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <MetricPill label="total" value={actionCatalog.total} />
                  <MetricPill label="ready" value={actionCatalog.counts.ready ?? 0} />
                  <MetricPill label="partial" value={actionCatalog.counts.partial ?? 0} warn />
                  <MetricPill label="blocked" value={actionCatalog.counts.blocked ?? 0} warn />
                </div>
              </div>
              <div className="grid max-h-32 gap-1 overflow-auto rounded border border-border bg-bg/40 p-2">
                {actionCatalog.contracts
                  .filter((contract) => contract.status !== "ready")
                  .slice(0, 6)
                  .map((contract) => (
                    <div key={contract.id} className="grid grid-cols-[1fr_auto] items-start gap-2">
                      <span className="min-w-0">
                        <span className="block truncate text-fg">{contract.label}</span>
                        <span className="block truncate text-muted">{contract.blocked_reason ?? contract.summary}</span>
                      </span>
                      <span className="rounded bg-accent-amber/15 px-1.5 py-0.5 text-[10px] uppercase text-accent-amber">{contract.status}</span>
                    </div>
                  ))}
              </div>
              <div className="xl:col-span-2 flex max-h-32 flex-wrap gap-1.5 overflow-auto pr-1">
                {actionCatalog.contracts.filter(canRunOperatorAction).map((contract) => (
                  <button
                    key={contract.id}
                    type="button"
                    disabled={operatorBusy !== null}
                    onClick={() => void runOperatorAction(contract, setOperatorBusy, setOperatorMessage, setActionCatalog)}
                    className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {operatorBusy === contract.id ? "running" : contract.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="Coverage catalog unavailable" detail="The local backend did not return a Hermes Agent operator action catalog." />
          )}
        </Panel>
      </div>
      <div className="col-span-12">
        <Panel
          id="agents.idle-workbench"
          title="IDLE WORKBENCH"
          dense
          status={{ tone: workbench.blockers.length > 0 ? "amber" : "cyan", label: workbenchMessage }}
          className="min-h-[132px]"
        >
          <div className="grid h-full gap-2 text-xs lg:grid-cols-[1fr_1fr_auto]">
            <div className="rounded border border-border bg-bg/40 p-2">
              <div className="text-[10px] uppercase text-muted">Daily queue</div>
              <div className="mt-1 text-fg">{workbench.daily_prompt.question}</div>
              <div className="mt-1 text-muted">{workbench.review_policy}</div>
            </div>
            <div className="grid max-h-24 content-start gap-1 overflow-auto rounded border border-border bg-bg/40 p-2">
              {workbench.candidates.slice(0, 4).map((candidate) => (
                <div key={candidate.id} className="grid grid-cols-[1fr_auto] gap-2">
                  <span className="truncate text-fg">{candidate.title}</span>
                  <span className="text-muted">{candidate.status}</span>
                </div>
              ))}
              {workbench.candidates.length === 0 && <div className="text-muted">No idle workbench candidates returned by the live API.</div>}
            </div>
            <div className="flex items-center justify-end">
              <button type="button" onClick={() => { window.location.hash = "learning"; }} className="rounded border border-border px-3 py-2 text-xs font-semibold text-fg">Open Learning</button>
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="agents.roster"
          title="AGENT ROSTER"
          dense
          status={{
            tone: activeAgents > 0 ? "green" : "muted",
            label: loadState === "loading" ? "loading" : `${activeAgents}/${agents.length}`,
          }}
          className="h-[480px]"
        >
          {agents.length > 0 ? (
            <ul className="flex flex-col gap-1 h-full overflow-auto">
              {agents.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(a.id)}
                    className={[
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors text-left",
                      a.id === selected?.id
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
          ) : (
            <EmptyState
              title={loadState === "loading" ? "Loading agents" : "No live agents"}
              detail={loadState === "unavailable" ? "The agents API is unavailable." : "The agents API returned an empty roster."}
            />
          )}
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-7 grid grid-cols-1 gap-2.5">
        {selected ? (
          <Panel
            id="agents.detail"
            title={`SELECTED · ${selected.role.toUpperCase()}`}
            dense
            status={{ tone: AGENT_TONE[selected.status], label: selected.status }}
            className="h-[300px]"
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
                {["pause", "resume", "retry", "handoff", "request-proof"].map((action) => (
                  <button
                    key={action}
                    type="button"
                    onClick={() => void runPersonaAction(selected.id, action, setActionMessage)}
                    className="rounded border border-border px-2 py-1 text-[11px] text-fg"
                  >
                    {action.replace("-", " ")}
                  </button>
                ))}
              </div>
              <div className="col-span-2 grid gap-1 rounded border border-border bg-bg/40 p-1.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] uppercase text-muted">Hermes Agent UI proof</span>
                  {(["observe", "smoke", "full"] as PlaywrightProofScope[]).map((scope) => (
                    <button
                      key={scope}
                      type="button"
                      onClick={() => setProofRunScope(scope)}
                      className={[
                        "rounded border px-2 py-0.5 text-[10px]",
                        proofRunScope === scope ? "border-accent-cyan/50 bg-accent-cyan/10 text-accent-cyan" : "border-border text-muted hover:text-fg",
                      ].join(" ")}
                    >
                      {scope}
                    </button>
                  ))}
                  <button
                    type="button"
                    disabled={proofRunBusy}
                    onClick={() => void runPlaywrightProof(selected.id, proofRunScope, setProofRunBusy, setProofRunMessage)}
                    className="rounded border border-border px-2 py-0.5 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {proofRunBusy ? "running" : "run"}
                  </button>
                </div>
                <div data-testid="agent-playwright-proof-status" className="truncate text-[10px] text-muted">{proofRunMessage}</div>
              </div>
              {actionMessage && <div className="col-span-2 rounded border border-border bg-bg/50 px-2 py-1 text-[10px] text-muted">{actionMessage}</div>}
            </div>
          </Panel>
        ) : (
          <Panel
            id="agents.detail"
            title="SELECTED AGENT"
            dense
            status={{ tone: "muted", label: "none" }}
            className="h-[300px]"
          >
            <EmptyState title="No selected agent" detail="Select a live agent after the backend returns a roster." />
          </Panel>
        )}
        <div className="grid grid-cols-2 gap-2.5">
          <Panel
            id="agents.activity"
            title="LIVE TASK LOG"
            dense
            status={{ tone: "cyan", label: "streaming" }}
            className="h-[240px]"
          >
            {agents.length > 0 ? (
              <ul className="flex flex-col gap-1 h-full overflow-auto text-[11px]">
                {[...agents]
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
            ) : (
              <EmptyState title="No live task events" detail="Agent activity will appear after the backend reports activity." />
            )}
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
                  role="button"
                  tabIndex={0}
                  onClick={() => setProviderDraft(p)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      setProviderDraft(p);
                    }
                  }}
                  className={[
                    "flex cursor-pointer items-center gap-2 px-2 py-1.5 rounded border",
                    p === providerDraft
                      ? "bg-surface2 border-accent-cyan/40"
                      : "border-border bg-surface2/30",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "h-1.5 w-1.5 rounded-full",
                      p === providerDraft ? "bg-accent-cyan" : "bg-muted",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="text-fg font-mono flex-1 truncate">{p}</span>
                  {p === providerDraft && (
                    <span className="text-accent-cyan text-[10px] uppercase">{p === selectedProvider ? "active" : "selected"}</span>
                  )}
                </div>
              ))}
              <div className="mt-1 flex justify-end">
                <button
                  type="button"
                  disabled={!selected || providerDraft === ""}
                  onClick={() => selected && void saveProviderSelection(selected.id, providerDraft, setActionMessage)}
                  className="rounded border border-border px-2 py-1 text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Apply selection
                </button>
              </div>
            </div>
          </Panel>
        </div>
      </div>
      <div className="col-span-12">
        <NotificationCenter notifications={notifications} />
      </div>
    </div>
  );
}

async function runPersonaAction(agentId: string, actionId: string, setMessage: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/actions/${encodeURIComponent(actionId)}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "operator requested from Agents tab" }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    setMessage(`${response.ok && actionAccepted(payload) ? "Accepted" : "Blocked"}: ${actionSummary(payload, response.statusText)}`);
    await adapters.emitProofEvent("agents.persona_action.requested", { agent_id: agentId, action_id: actionId, accepted: response.ok && actionAccepted(payload) });
  } catch {
    setMessage(`Blocked: agents backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

function canRunOperatorAction(contract: AgentActionContract): boolean {
  return RUNNABLE_OPERATOR_ACTIONS.has(contract.id) && contract.status === "ready";
}

async function runOperatorAction(
  contract: AgentActionContract,
  setBusy: (actionId: string | null) => void,
  setMessage: (message: string) => void,
  setCatalog: (catalog: AgentActionCatalog) => void,
) {
  setBusy(contract.id);
  setMessage(`Running ${contract.label}.`);
  try {
    const result = await adapters.runAgentCatalogAction(contract.id, "operator requested from Agents tab");
    const proof = result.proof_event_id ? ` proof ${result.proof_event_id}` : "";
    const status = result.accepted ? result.status : "blocked";
    setMessage(`${status}: ${contract.label}${proof}`);
    setCatalog(await adapters.getAgentActionCatalog());
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "operator action failed"}`);
  } finally {
    setBusy(null);
  }
}

async function saveProviderSelection(agentId: string, provider: string, setMessage: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/agents/config`, {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ config: { [`${agentId}.model_provider`]: provider } }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    const accepted = response.ok && actionAccepted(payload);
    setMessage(`${accepted ? "Saved" : "Blocked"}: ${actionSummary(payload, response.statusText)}`);
    if (accepted) {
      await adapters.emitProofEvent("agents.provider_selection.saved", { agent_id: agentId, provider, accepted });
    }
  } catch {
    setMessage(`Blocked: agents backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

async function runPlaywrightProof(
  agentId: string,
  scope: PlaywrightProofScope,
  setBusy: (busy: boolean) => void,
  setMessage: (message: string) => void,
) {
  setBusy(true);
  setMessage(`Running ${scope} Playwright proof through Hermes Agent ${agentId}.`);
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/playwright-run`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ scope, reason: "operator requested from Agents tab" }),
      cache: "no-store",
    });
    const payload = await response.json().catch(() => null) as PlaywrightProofResult | null;
    if (!payload || !response.ok && payload.accepted !== false) {
      setMessage(`Blocked: ${response.statusText || "Playwright proof response was not readable"}.`);
      return;
    }
    const status = payload.status ?? "unknown";
    const proof = payload.proof_event_id ? ` proof ${payload.proof_event_id}` : "";
    const artifact = payload.artifact_id ? ` artifact ${payload.artifact_id}` : "";
    const reason = payload.reason ? ` ${payload.reason}` : "";
    setMessage(`${status.toUpperCase()}: ${payload.scope ?? scope}${proof}${artifact}${reason}`.trim());
    await adapters.emitProofEvent("agents.playwright_proof.requested", { agent_id: agentId, scope, status, proof_event_id: payload.proof_event_id, artifact_id: payload.artifact_id });
  } catch {
    setMessage(`Blocked: agents backend API is unreachable at ${LIVE_BASE_URL}.`);
  } finally {
    setBusy(false);
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
  return String(payload.reason ?? payload.status ?? payload.saved ?? fallback);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-xs">
      <div className="font-medium text-fg">{title}</div>
      <div className="max-w-[280px] text-muted">{detail}</div>
    </div>
  );
}

function MetricPill({ label, value, warn = false }: { label: string; value: number; warn?: boolean }) {
  return (
    <span className={`rounded px-2 py-1 text-[10px] uppercase ${warn && value > 0 ? "bg-accent-amber/15 text-accent-amber" : "bg-surface2 text-muted"}`}>
      {label} {value}
    </span>
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
