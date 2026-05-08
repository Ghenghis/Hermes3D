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
import type {
  AgentActionCatalog,
  AgentActionContract,
  AgentE2EJobResult,
  AgentE2EReadiness,
  CodeCliRunnerPreflightResult,
  CodeCliRunnerRunResult,
  ProviderSmokeResult,
} from "../types/agent-actions";
import type { IdleWorkbenchState } from "../types/learning";
import type { Notification } from "../types/notification";
import type { RuntimeIdentity } from "../types/system";

const AGENT_TONE: Record<Agent["status"], StatusTone> = {
  active: "green",
  idle: "muted",
  paused: "amber",
  error: "red",
};

const PROVIDER_OPTIONS = [
  "minimax/MiniMax builder",
  "deepseek/DeepSeek V4 reviewer",
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
  "code.e2e.readiness.refresh",
  "code.cli_runners.readiness.refresh",
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
  const [e2eReadiness, setE2eReadiness] = useState<AgentE2EReadiness | null>(null);
  const [e2eBusy, setE2eBusy] = useState(false);
  const [e2eMessage, setE2eMessage] = useState("Loading Agent Code Workbench readiness.");
  const [e2eResult, setE2eResult] = useState<AgentE2EJobResult | null>(null);
  const [e2eTitle, setE2eTitle] = useState("Hermes Agent E2E code task");
  const [e2eObjective, setE2eObjective] = useState("Use folder-index context, inspect the listed files, produce a bounded patch plan, and route it through DeepSeek review before any source mutation.");
  const [e2eFiles, setE2eFiles] = useState("03_implementation/ROADMAP.md\n03_implementation/docs/handoffs/HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md");
  const [e2eTargetBranch, setE2eTargetBranch] = useState("");
  const [e2eCliWorker, setE2eCliWorker] = useState("");
  const [cliRunnerBusy, setCliRunnerBusy] = useState<string | null>(null);
  const [cliRunnerMessage, setCliRunnerMessage] = useState("OpenHands/OpenCode can be detected now; write runs stay proof-gated.");
  const [cliRunnerPreflight, setCliRunnerPreflight] = useState<CodeCliRunnerPreflightResult | null>(null);
  const [cliRunnerRun, setCliRunnerRun] = useState<CodeCliRunnerRunResult | null>(null);
  const [providerSmokeBusy, setProviderSmokeBusy] = useState<"minimax" | "deepseek" | null>(null);
  const [providerSmokeResult, setProviderSmokeResult] = useState<ProviderSmokeResult | null>(null);
  const [providerSmokeMessage, setProviderSmokeMessage] = useState("Provider smoke calls use private env on the backend and store MCP evidence.");
  const [runtimeIdentity, setRuntimeIdentity] = useState<RuntimeIdentity | null>(null);
  const [shipTaskId, setShipTaskId] = useState("H3D-AGENT-SHIP");
  const [shipProposalId, setShipProposalId] = useState("");
  const [shipReviewProofs, setShipReviewProofs] = useState("");
  const [shipGateId, setShipGateId] = useState("git-diff-check");
  const [shipFiles, setShipFiles] = useState("03_implementation/ROADMAP.md");
  const [shipBranch, setShipBranch] = useState("hermes-agent/reviewed-workbench-change");
  const [shipBase, setShipBase] = useState("codex/hermes-agent-e2e-workbench");
  const [shipCommitMessage, setShipCommitMessage] = useState("feat(agents): ship reviewed workbench patch");
  const [shipPrTitle, setShipPrTitle] = useState("feat(agents): ship reviewed workbench patch");
  const [shipMessage, setShipMessage] = useState("Reviewed ship lane is gated: proposal + review proof + lock + gate + PR.");
  const [shipBusy, setShipBusy] = useState<string | null>(null);
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
    let mounted = true;
    void refreshRuntimeIdentity(setRuntimeIdentity, setE2eMessage, () => mounted);
    void refreshAgentE2EReadiness(setE2eReadiness, setE2eMessage, () => mounted);
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
          id="agents.code-workbench"
          title="AGENT CODE WORKBENCH"
          dense
          status={{ tone: e2eReadiness?.ready ? "green" : "amber", label: e2eMessage }}
          className="min-h-[228px]"
        >
          <div className="grid gap-2 text-xs xl:grid-cols-[0.92fr_1.08fr]">
            <div className="grid gap-2">
              <div className="rounded border border-border bg-bg/40 p-2">
                <div className="text-[10px] uppercase text-muted">Truth chain</div>
                <div className="mt-1 text-fg">{e2eReadiness?.summary ?? "Waiting for backend readiness."}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <MetricPill label="folder docs" value={e2eReadiness?.folder_index.loaded.length ?? 0} />
                  <MetricPill label="missing" value={e2eReadiness?.folder_index.missing.length ?? 0} warn />
                  <MetricPill label="sent" value={e2eReadiness?.folder_index.provider_context_files?.length ?? 0} />
                  <MetricPill label="cli found" value={e2eReadiness?.cli_runners.detected ?? 0} />
                </div>
              </div>
              <div className="grid gap-1 rounded border border-border bg-bg/40 p-2">
                <div className="text-[10px] uppercase text-muted">Provider auth from private env</div>
                {(e2eReadiness?.programming.provider_lanes ?? []).map((provider) => (
                  <div key={provider.id} className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded border border-border/70 bg-surface1/50 px-2 py-1">
                    <span className="font-semibold uppercase text-fg">{provider.id}</span>
                    <span className="min-w-0 truncate font-mono text-[10px] text-muted">
                      {provider.api_key_source ?? (provider.api_key_configured ? "private env detected" : provider.accepted_api_key_env?.join(" or ") ?? "missing key")}
                    </span>
                    <span className={provider.status === "ready" ? "text-[10px] uppercase text-accent-green" : "text-[10px] uppercase text-accent-amber"}>
                      {provider.live_status ?? provider.status}
                    </span>
                    {provider.blocked_reason && (
                      <div className="col-span-3 text-[10px] text-muted">{provider.blocked_reason}</div>
                    )}
                  </div>
                ))}
              </div>
              <div className="grid gap-1 rounded border border-border bg-bg/40 p-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[10px] uppercase text-muted">OpenHands / OpenCode runners</div>
                  <span className={e2eReadiness?.cli_runners.sandbox?.ready ? "text-[10px] uppercase text-accent-green" : "text-[10px] uppercase text-accent-amber"}>
                    sandbox {e2eReadiness?.cli_runners.sandbox?.status ?? "unknown"}
                  </span>
                </div>
                {(e2eReadiness?.cli_runners.runners ?? []).map((runner) => (
                  <div key={runner.id} className="grid gap-1 rounded border border-border/70 bg-surface1/50 p-1.5">
                    <div className="grid grid-cols-[1fr_auto] gap-2">
                      <span className="min-w-0 truncate text-fg">{runner.label}</span>
                      <span className={runner.detected ? "text-accent-green" : "text-accent-amber"}>{runner.detected ? runner.version ?? "detected" : "executable missing"}</span>
                    </div>
                    <div className="grid gap-x-2 gap-y-0.5 text-[10px] sm:grid-cols-[auto_1fr]">
                      <span className="text-muted">source</span>
                      <span className="min-w-0 truncate font-mono text-muted">{runner.source_path ?? "not configured"}</span>
                      <span className="text-muted">bin key</span>
                      <span className="min-w-0 truncate font-mono text-muted">{runner.configured_path ?? runner.required_env_keys?.[0] ?? "not configured"}</span>
                    </div>
                    {runner.blocked_reason ? <div className="text-[10px] text-accent-amber">{runner.blocked_reason}</div> : null}
                    <div className="flex flex-wrap gap-1">
                      <button
                        type="button"
                        disabled={cliRunnerBusy != null || !isCliRunnerId(runner.id)}
                        onClick={() => isCliRunnerId(runner.id) ? void runCliRunnerPreflight(runner.id, setCliRunnerBusy, setCliRunnerPreflight, setCliRunnerMessage, setE2eReadiness) : undefined}
                        className="rounded border border-border px-2 py-0.5 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {cliRunnerBusy === `${runner.id}:preflight` ? "checking" : "Preflight"}
                      </button>
                      <button
                        type="button"
                        disabled={cliRunnerBusy != null || !isCliRunnerId(runner.id)}
                        onClick={() => isCliRunnerId(runner.id) ? void runCliRunnerContract(runner.id, { title: e2eTitle, objective: e2eObjective, files: e2eFiles, targetBranch: e2eTargetBranch }, setCliRunnerBusy, setCliRunnerRun, setCliRunnerMessage, setE2eReadiness) : undefined}
                        className="rounded border border-accent-amber/50 bg-accent-amber/10 px-2 py-0.5 text-[10px] text-accent-amber disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {cliRunnerBusy === `${runner.id}:run` ? "checking" : "Run contract"}
                      </button>
                    </div>
                  </div>
                ))}
                {!e2eReadiness && <div className="text-muted">CLI runner API has not responded yet.</div>}
                <div className="text-[10px] text-muted">{cliRunnerMessage}</div>
                {cliRunnerPreflight ? (
                  <div className={cliRunnerPreflight.accepted ? "text-[10px] text-accent-green" : "text-[10px] text-accent-amber"}>
                    preflight {cliRunnerPreflight.runner.label}: {cliRunnerPreflight.status}
                  </div>
                ) : null}
                {(cliRunnerRun?.blocked_reasons.length ?? 0) > 0 ? (
                  <div className="max-h-16 overflow-auto rounded border border-accent-amber/30 bg-accent-amber/10 p-1.5 text-[10px] text-accent-amber">
                    {cliRunnerRun?.blocked_reasons.slice(0, 4).map((reason) => <div key={reason}>- {reason}</div>)}
                  </div>
                ) : null}
                {(e2eReadiness?.cli_runners.sandbox?.blocked_reasons.length ?? 0) > 0 ? (
                  <div className="max-h-16 overflow-auto rounded border border-accent-amber/30 bg-accent-amber/10 p-1.5 text-[10px] text-accent-amber">
                    {e2eReadiness?.cli_runners.sandbox?.blocked_reasons.slice(0, 3).map((reason) => <div key={reason}>- {reason}</div>)}
                  </div>
                ) : null}
              </div>
              <div className="grid gap-1 rounded border border-border bg-bg/40 p-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[10px] uppercase text-muted">Runtime freshness</div>
                  <span className={runtimeIdentity?.fresh ? "text-[11px] text-accent-green" : "text-[11px] text-accent-amber"}>
                    {runtimeIdentity ? runtimeIdentity.status : "checking"}
                  </span>
                </div>
                <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[11px]">
                  <span className="text-muted">branch</span>
                  <span className="min-w-0 truncate font-mono text-fg">{runtimeIdentity?.branch ?? "unknown"}</span>
                  <span className="text-muted">commit</span>
                  <span className="font-mono text-fg">{runtimeIdentity?.commit ?? "unknown"}</span>
                  <span className="text-muted">routes</span>
                  <span className={runtimeIdentity?.missing_agent_workbench_routes.length ? "text-accent-amber" : "text-accent-green"}>
                    {runtimeIdentity ? `${runtimeIdentity.agent_workbench_required_routes.length - runtimeIdentity.missing_agent_workbench_routes.length}/${runtimeIdentity.agent_workbench_required_routes.length}` : "unknown"}
                  </span>
                </div>
                {runtimeIdentity?.missing_agent_workbench_routes.length ? (
                  <div className="max-h-14 overflow-auto rounded border border-accent-amber/30 bg-accent-amber/10 p-1.5 font-mono text-[10px] text-accent-amber">
                    stale backend missing: {runtimeIdentity.missing_agent_workbench_routes.join(", ")}
                  </div>
                ) : null}
              </div>
              <div className="grid gap-2 rounded border border-border bg-bg/40 p-2">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[10px] uppercase text-muted">Provider live smoke</div>
                    <div className="mt-0.5 text-[11px] text-muted">{providerSmokeMessage}</div>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button
                      type="button"
                      disabled={providerSmokeBusy != null}
                      onClick={() => void runProviderSmoke("minimax", setProviderSmokeBusy, setProviderSmokeResult, setProviderSmokeMessage)}
                      className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {providerSmokeBusy === "minimax" ? "probing" : "MiniMax"}
                    </button>
                    <button
                      type="button"
                      disabled={providerSmokeBusy != null}
                      onClick={() => void runProviderSmoke("deepseek", setProviderSmokeBusy, setProviderSmokeResult, setProviderSmokeMessage)}
                      className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {providerSmokeBusy === "deepseek" ? "probing" : "DeepSeek"}
                    </button>
                  </div>
                </div>
                {providerSmokeResult && (
                  <div className={providerSmokeResult.accepted ? "text-[11px] text-accent-green" : "text-[11px] text-accent-amber"}>
                    {providerSmokeResult.provider_id}: {providerSmokeResult.status}
                    {providerSmokeResult.blocked_reasons?.[0] ? ` · ${providerSmokeResult.blocked_reasons[0]}` : ""}
                  </div>
                )}
              </div>
              {(e2eReadiness?.blocked_reasons.length ?? 0) > 0 && (
                <div className="max-h-20 overflow-auto rounded border border-accent-amber/30 bg-accent-amber/10 p-2 text-[11px] text-accent-amber">
                  {e2eReadiness?.blocked_reasons.slice(0, 5).map((reason) => <div key={reason}>- {reason}</div>)}
                </div>
              )}
            </div>
            <div className="grid gap-2 rounded border border-border bg-bg/40 p-2">
              <div className="grid gap-2 md:grid-cols-[1fr_0.72fr_0.48fr]">
                <label className="grid gap-1">
                  <span className="text-[10px] uppercase text-muted">Title</span>
                  <input value={e2eTitle} onChange={(event) => setE2eTitle(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none" />
                </label>
                <label className="grid gap-1">
                  <span className="text-[10px] uppercase text-muted">Target branch</span>
                  <input value={e2eTargetBranch} onChange={(event) => setE2eTargetBranch(event.target.value)} placeholder="optional" className="rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none" />
                </label>
                <label className="grid gap-1">
                  <span className="text-[10px] uppercase text-muted">CLI worker</span>
                  <select value={e2eCliWorker} onChange={(event) => setE2eCliWorker(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none">
                    <option value="">none</option>
                    <option value="opencode">OpenCode</option>
                    <option value="openhands">OpenHands</option>
                  </select>
                </label>
              </div>
              <label className="grid gap-1">
                <span className="text-[10px] uppercase text-muted">Files, one per line</span>
                <textarea value={e2eFiles} onChange={(event) => setE2eFiles(event.target.value)} className="h-16 resize-y rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
              </label>
              <label className="grid gap-1">
                <span className="text-[10px] uppercase text-muted">Objective</span>
                <textarea value={e2eObjective} onChange={(event) => setE2eObjective(event.target.value)} className="h-20 resize-y rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none" />
              </label>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] text-muted">
                  {e2eResult ? `${e2eResult.status}${e2eResult.task_id ? ` · ${e2eResult.task_id}` : ""}` : "Runs planning/review only; patch apply remains separately gated."}
                </span>
                <div className="flex gap-1.5">
                  <button type="button" onClick={() => void refreshAgentE2EReadiness(setE2eReadiness, setE2eMessage)} className="rounded border border-border px-2 py-1 text-[11px] text-fg">Refresh</button>
                  <button
                    type="button"
                    disabled={e2eBusy || !e2eReadiness?.ready}
                    onClick={() => void runAgentE2EWorkbench({ title: e2eTitle, objective: e2eObjective, files: e2eFiles, targetBranch: e2eTargetBranch, cliWorker: e2eCliWorker }, setE2eBusy, setE2eMessage, setE2eResult, setE2eReadiness)}
                    className="rounded border border-accent-cyan/50 bg-accent-cyan/10 px-3 py-1 text-[11px] font-semibold text-accent-cyan disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {e2eBusy ? "running" : "Start E2E job"}
                  </button>
                </div>
              </div>
              {(e2eResult?.blocked_reasons?.length ?? 0) > 0 && (
                <div className="max-h-24 overflow-auto rounded border border-accent-amber/30 bg-accent-amber/10 p-2 text-[11px] text-accent-amber">
                  {e2eResult?.blocked_reasons?.slice(0, 3).map((reason) => <div key={reason}>- {reason}</div>)}
                </div>
              )}
              {e2eResult?.next_required_steps?.length ? (
                <div className="rounded border border-border bg-bg/40 p-2 text-[11px] text-muted">
                  next: {e2eResult.next_required_steps.slice(0, 2).join(" -> ")}
                </div>
              ) : null}
              <div className="grid gap-2 rounded border border-border bg-surface1/60 p-2">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[10px] uppercase text-muted">Reviewed patch to gates to PR</div>
                    <div className="mt-0.5 text-[11px] text-muted">{shipMessage}</div>
                  </div>
                </div>
                <div className="grid gap-2 md:grid-cols-3">
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Task ID</span>
                    <input value={shipTaskId} onChange={(event) => setShipTaskId(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none" />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Proposal ID</span>
                    <input value={shipProposalId} onChange={(event) => setShipProposalId(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Gate</span>
                    <input value={shipGateId} onChange={(event) => setShipGateId(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Files</span>
                    <textarea value={shipFiles} onChange={(event) => setShipFiles(event.target.value)} className="h-14 resize-y rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Review proof IDs</span>
                    <textarea value={shipReviewProofs} onChange={(event) => setShipReviewProofs(event.target.value)} className="h-14 resize-y rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Branch</span>
                    <input value={shipBranch} onChange={(event) => setShipBranch(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-[10px] uppercase text-muted">Base</span>
                    <input value={shipBase} onChange={(event) => setShipBase(event.target.value)} className="rounded border border-border bg-surface2 px-2 py-1 font-mono text-[11px] text-fg outline-none" />
                  </label>
                </div>
                <label className="grid gap-1">
                  <span className="text-[10px] uppercase text-muted">Commit / PR title</span>
                  <input value={shipCommitMessage} onChange={(event) => {
                    setShipCommitMessage(event.target.value);
                    setShipPrTitle((current) => current === shipCommitMessage ? event.target.value : current);
                  }} className="rounded border border-border bg-surface2 px-2 py-1 text-fg outline-none" />
                </label>
                <div className="flex flex-wrap gap-1.5">
                  <ShipButton id="apply" busy={shipBusy} label="Apply reviewed" onClick={() => void runReviewedPatchApply({ shipTaskId, shipProposalId, shipReviewProofs }, setShipBusy, setShipMessage)} />
                  <ShipButton id="gate" busy={shipBusy} label="Run gate" onClick={() => void runCodeGateStep({ shipGateId }, setShipBusy, setShipMessage)} />
                  <ShipButton id="branch" busy={shipBusy} label="Branch" onClick={() => void runGitStep("branch", { shipTaskId, shipBranch, shipBase }, setShipBusy, setShipMessage)} />
                  <ShipButton id="stage" busy={shipBusy} label="Stage" onClick={() => void runGitStep("stage", { shipTaskId, shipFiles }, setShipBusy, setShipMessage)} />
                  <ShipButton id="commit" busy={shipBusy} label="Commit" onClick={() => void runGitStep("commit", { shipTaskId, shipFiles, shipCommitMessage, shipReviewProofs }, setShipBusy, setShipMessage)} />
                  <ShipButton id="push" busy={shipBusy} label="Push" onClick={() => void runGitStep("push", { shipTaskId }, setShipBusy, setShipMessage)} />
                  <ShipButton id="pr" busy={shipBusy} label="PR" onClick={() => void runGitStep("pr", { shipTaskId, shipBase, shipPrTitle }, setShipBusy, setShipMessage)} />
                </div>
              </div>
            </div>
          </div>
        </Panel>
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

async function refreshAgentE2EReadiness(
  setReadiness: (readiness: AgentE2EReadiness | null) => void,
  setMessage: (message: string) => void,
  isMounted: () => boolean = () => true,
) {
  try {
    const readiness = await adapters.getAgentE2EReadiness();
    if (!isMounted()) return;
    setReadiness(readiness);
    const blocked = readiness.blocked_reasons.length;
    const label = readiness.ready ? "ready" : `${blocked} blocker${blocked === 1 ? "" : "s"}`;
    setMessage(`Agent Code Workbench ${label}.`);
  } catch (error) {
    if (!isMounted()) return;
    setReadiness(null);
    setMessage(`Workbench unavailable: ${error instanceof Error ? error.message : "backend error"}`);
  }
}

async function refreshRuntimeIdentity(
  setIdentity: (identity: RuntimeIdentity | null) => void,
  setMessage: (message: string) => void,
  isMounted: () => boolean = () => true,
) {
  try {
    const identity = await adapters.getRuntimeIdentity();
    if (!isMounted()) return;
    setIdentity(identity);
    if (identity && !identity.fresh) {
      setMessage(`Backend is stale: missing ${identity.missing_agent_workbench_routes.length} Agent Workbench route${identity.missing_agent_workbench_routes.length === 1 ? "" : "s"}.`);
    }
  } catch (error) {
    if (!isMounted()) return;
    setIdentity(null);
    setMessage(`Runtime freshness unavailable: ${error instanceof Error ? error.message : "backend error"}`);
  }
}

async function runAgentE2EWorkbench(
  input: { title: string; objective: string; files: string; targetBranch: string; cliWorker: string },
  setBusy: (busy: boolean) => void,
  setMessage: (message: string) => void,
  setResult: (result: AgentE2EJobResult | null) => void,
  setReadiness: (readiness: AgentE2EReadiness | null) => void,
) {
  const files = parseWorkbenchFiles(input.files);
  if (files.length === 0) {
    setMessage("Blocked: add at least one existing project-relative file.");
    return;
  }
  const taskId = `H3D-AGENT-E2E-${Date.now()}`;
  setBusy(true);
  setResult(null);
  setMessage(`Starting ${taskId}.`);
  try {
    const result = await adapters.runAgentE2EJob({
      task_id: taskId,
      title: input.title.trim() || "Hermes Agent E2E code task",
      files,
      objective: input.objective.trim(),
      target_branch: input.targetBranch.trim() || undefined,
      role_chain: ["finder", "builder", "reviewer", "tester"],
      cli_worker: input.cliWorker || undefined,
      release_on_finish: true,
    });
    setResult(result);
    const proof = proofIdFromResult(result);
    const blocked = result.blocked_reasons?.length ? ` · ${result.blocked_reasons[0]}` : "";
    setMessage(`${result.accepted ? "Accepted" : "Blocked"}: ${result.status}${proof}${blocked}`);
    await adapters.emitProofEvent("agents.e2e_workbench.requested", { task_id: taskId, status: result.status, accepted: result.accepted, files });
    void adapters.getAgentE2EReadiness().then(setReadiness).catch(() => undefined);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "Agent Code Workbench job failed"}`);
  } finally {
    setBusy(false);
  }
}

function isCliRunnerId(value: string): value is "opencode" | "openhands" {
  return value === "opencode" || value === "openhands";
}

async function runCliRunnerPreflight(
  runnerId: "opencode" | "openhands",
  setBusy: (busy: string | null) => void,
  setResult: (result: CodeCliRunnerPreflightResult | null) => void,
  setMessage: (message: string) => void,
  setReadiness: (readiness: AgentE2EReadiness | null) => void,
) {
  const taskId = `H3D-CLI-PREFLIGHT-${runnerId.toUpperCase()}-${Date.now()}`;
  setBusy(`${runnerId}:preflight`);
  setResult(null);
  setMessage(`Running ${runnerId} preflight through backend private env.`);
  try {
    const result = await adapters.preflightCodeCliRunner(runnerId, taskId);
    setResult(result);
    const next = result.next_required_steps?.[0] ? ` · ${result.next_required_steps[0]}` : "";
    setMessage(`${result.runner.label} preflight ${result.accepted ? "ready" : "blocked"}: ${result.status}${next}`);
    void adapters.getAgentE2EReadiness().then(setReadiness).catch(() => undefined);
  } catch (error) {
    setMessage(`Blocked ${runnerId} preflight: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

async function runCliRunnerContract(
  runnerId: "opencode" | "openhands",
  input: { title: string; objective: string; files: string; targetBranch: string },
  setBusy: (busy: string | null) => void,
  setResult: (result: CodeCliRunnerRunResult | null) => void,
  setMessage: (message: string) => void,
  setReadiness: (readiness: AgentE2EReadiness | null) => void,
) {
  const files = parseWorkbenchFiles(input.files);
  if (files.length === 0) {
    setMessage("Blocked: add at least one existing project-relative file.");
    return;
  }
  const taskId = `H3D-CLI-RUN-${runnerId.toUpperCase()}-${Date.now()}`;
  setBusy(`${runnerId}:run`);
  setResult(null);
  setMessage(`Checking ${runnerId} run contract; execution stays fail-closed without sandbox proof.`);
  try {
    const result = await adapters.runCodeCliRunner({
      runner_id: runnerId,
      task_id: taskId,
      title: input.title.trim() || `${runnerId} Hermes Agent code task`,
      files,
      objective: input.objective.trim(),
      target_branch: input.targetBranch.trim() || undefined,
    });
    setResult(result);
    const reason = result.blocked_reasons?.[0] ? ` · ${result.blocked_reasons[0]}` : "";
    setMessage(`${result.runner.label} run contract ${result.accepted ? "accepted" : "blocked"}: ${result.status}${reason}`);
    void adapters.getAgentE2EReadiness().then(setReadiness).catch(() => undefined);
  } catch (error) {
    setMessage(`Blocked ${runnerId} run contract: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

function ShipButton(props: { id: string; busy: string | null; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      disabled={props.busy != null}
      onClick={props.onClick}
      className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
    >
      {props.busy === props.id ? "running" : props.label}
    </button>
  );
}

async function runProviderSmoke(
  providerId: "minimax" | "deepseek",
  setBusy: (provider: "minimax" | "deepseek" | null) => void,
  setResult: (result: ProviderSmokeResult | null) => void,
  setMessage: (message: string) => void,
) {
  const taskId = `H3D-PROVIDER-SMOKE-${providerId.toUpperCase()}-${Date.now()}`;
  setBusy(providerId);
  setMessage(`Running ${providerId} live smoke through backend private env.`);
  try {
    const result = await adapters.runProviderSmoke(providerId, taskId);
    setResult(result);
    const blocked = result.blocked_reasons?.[0] ? ` · ${result.blocked_reasons[0]}` : "";
    setMessage(`${result.accepted ? "Passed" : "Blocked"} ${providerId} smoke: ${result.status}${blocked}`);
  } catch (error) {
    setMessage(`Blocked ${providerId} smoke: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

async function runReviewedPatchApply(
  input: { shipTaskId: string; shipProposalId: string; shipReviewProofs: string },
  setBusy: (busy: string | null) => void,
  setMessage: (message: string) => void,
) {
  const reviewProofs = parseProofIds(input.shipReviewProofs);
  if (!input.shipTaskId.trim() || !input.shipProposalId.trim() || reviewProofs.length === 0) {
    setMessage("Blocked: task id, proposal id, and at least one review proof id are required.");
    return;
  }
  setBusy("apply");
  setMessage("Applying reviewed patch through same-owner MCP lock checks.");
  try {
    const result = await adapters.applyReviewedPatch({
      task_id: input.shipTaskId.trim(),
      proposal_id: input.shipProposalId.trim(),
      review_proof_ids: reviewProofs,
      reason: "Operator requested reviewed patch apply from Agent Code Workbench.",
    });
    setMessage(`${result.accepted ? "Applied" : "Blocked"} reviewed patch: ${result.status}`);
  } catch (error) {
    setMessage(`Blocked reviewed apply: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

async function runCodeGateStep(
  input: { shipGateId: string },
  setBusy: (busy: string | null) => void,
  setMessage: (message: string) => void,
) {
  const gateId = input.shipGateId.trim();
  if (!gateId) {
    setMessage("Blocked: gate id is required.");
    return;
  }
  setBusy("gate");
  setMessage(`Running Hermes MCP gate ${gateId}.`);
  try {
    const result = await adapters.runCodeGate({ gate_id: gateId });
    setMessage(`${result.ok ? "Passed" : "Failed"} gate ${gateId}: ${result.status}`);
  } catch (error) {
    setMessage(`Gate blocked: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

async function runGitStep(
  step: "branch" | "stage" | "commit" | "push" | "pr",
  input: {
    shipTaskId: string;
    shipFiles?: string;
    shipBranch?: string;
    shipBase?: string;
    shipCommitMessage?: string;
    shipReviewProofs?: string;
    shipPrTitle?: string;
  },
  setBusy: (busy: string | null) => void,
  setMessage: (message: string) => void,
) {
  const taskId = input.shipTaskId.trim();
  if (!taskId) {
    setMessage("Blocked: task id is required for git shipping.");
    return;
  }
  const files = parseWorkbenchFiles(input.shipFiles ?? "");
  setBusy(step);
  setMessage(`Running git ${step} through code-operator policy.`);
  try {
    if (step === "branch") {
      await adapters.createCodeBranch({
        task_id: taskId,
        branch_name: String(input.shipBranch ?? "").trim(),
        base_ref: String(input.shipBase ?? "").trim() || undefined,
        reason: "Operator requested reviewed workbench shipping branch.",
      });
    } else if (step === "stage") {
      await adapters.stageOwnedCodeFiles({ task_id: taskId, files });
    } else if (step === "commit") {
      await adapters.commitOwnedCodeFiles({
        task_id: taskId,
        files,
        message: String(input.shipCommitMessage ?? "").trim(),
        proof_ids: parseProofIds(input.shipReviewProofs ?? ""),
      });
    } else if (step === "push") {
      await adapters.pushCodeBranch({ task_id: taskId });
    } else {
      await adapters.openCodePullRequest({
        task_id: taskId,
        base_ref: String(input.shipBase ?? "").trim(),
        title: String(input.shipPrTitle ?? input.shipCommitMessage ?? "Hermes Agent reviewed workbench patch").trim(),
        body: "Hermes Agent reviewed workbench PR opened through proof-gated code-operator APIs.",
        draft: true,
      });
    }
    setMessage(`Git ${step} accepted.`);
  } catch (error) {
    setMessage(`Git ${step} blocked: ${error instanceof Error ? error.message : "backend error"}`);
  } finally {
    setBusy(null);
  }
}

function parseProofIds(value: string): string[] {
  return value
    .split(/[\s,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseWorkbenchFiles(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(/[\n,]+/)
    .map((item) => item.trim().replaceAll("\\", "/"))
    .filter((item) => item.length > 0)
    .filter((item) => {
      if (seen.has(item)) return false;
      seen.add(item);
      return true;
    });
}

function proofIdFromResult(result: AgentE2EJobResult): string {
  const evidence = result.mcp_evidence;
  if (isRecord(evidence) && typeof evidence.evidence_id === "string") {
    return ` · proof ${evidence.evidence_id}`;
  }
  return "";
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
