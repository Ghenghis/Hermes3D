import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import type {
  IdleCandidateCreateRequest,
  IdleWorkbenchCandidate,
  IdleWorkbenchState,
  LearningConfig,
  ReportMeta,
} from "../types/learning";

const DEFAULT_CONFIG: LearningConfig = {
  enabled: false,
  active: false,
  mode: "idle-research-reporting",
  idle_minutes: 30,
  reports_directory: "var/hermes3d.db/learning/reports",
  next_topic: "",
  runner_status: "not_configured",
  reason: null,
};

const DEFAULT_WORKBENCH: IdleWorkbenchState = {
  status: "loading",
  review_policy: "Loading idle workbench policy from the local API.",
  blockers: [],
  candidates: [],
  automation: {
    runner_status: "not_configured",
    runner_reason: "Idle learning runner status is loading from the local API.",
    agent_runtime_status: "not_configured",
    agent_runtime_reason: "Hermes Agent runtime status is loading from the local API.",
    capabilities: [],
  },
  daily_prompt: {
    question: "What should Hermes3D improve while the workstation is idle?",
    last_candidate_at: null,
    suggested_kinds: ["research", "app_update", "printer_maintenance", "documentation", "workflow"],
  },
};

const KIND_OPTIONS = ["research", "app_update", "printer_maintenance", "documentation", "workflow"];

export function LearningTab() {
  const [config, setConfig] = useState<LearningConfig>(DEFAULT_CONFIG);
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [reportPreview, setReportPreview] = useState<string>("Select a report to read it from the learning reports API.");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [workbench, setWorkbench] = useState<IdleWorkbenchState>(DEFAULT_WORKBENCH);
  const [workbenchMessage, setWorkbenchMessage] = useState("Loading idle workbench from /api/learning/idle-workbench.");
  const [candidateDraft, setCandidateDraft] = useState<IdleCandidateCreateRequest>({
    title: "",
    summary: "",
    kind: "research",
    risk_level: "low",
    target_tab: "source_os",
    created_by: "operator",
  });
  const blockedMutations = workbench.blockers.length > 0;
  const queueCount = workbench.candidates.filter((candidate) => ["queued", "ready_for_review"].includes(candidate.status)).length;
  const latestCandidate = useMemo(() => workbench.candidates[0] ?? null, [workbench.candidates]);
  const automation = workbench.automation ?? DEFAULT_WORKBENCH.automation;
  const readyAutomationCount = automation?.capabilities.filter((capability) => capability.execution_status === "ready").length ?? 0;
  const automationCount = automation?.capabilities.length ?? 0;
  const automationRuntimeReady = automation?.runner_status === "ready" && automation?.agent_runtime_status === "ready";

  useEffect(() => {
    void adapters.getLearningConfig()
      .then((next) => {
        setConfig(next);
        setSaveMessage("Learning config loaded from /api/learning/config.");
      })
      .catch((error) => {
        setSaveMessage(`Blocked: ${errorMessage(error)}`);
      });
    void adapters.getLearningReports()
      .then(setReports)
      .catch((error) => {
        setReports([]);
        setReportPreview(`Reports unavailable: ${errorMessage(error)}`);
      });
    void refreshWorkbench(setWorkbench, setWorkbenchMessage);
  }, []);

  const saveField = async (patch: Partial<LearningConfig>) => {
    const next = { ...config, ...patch };
    setConfig(next);
    setSaving(true);
    setSaveMessage("Saving learning config...");
    try {
      const saved = await adapters.saveLearningConfig({
        enabled: next.enabled,
        idle_minutes: next.idle_minutes,
      });
      setConfig(saved);
      setSaveMessage(learningConfigMessage(saved));
      await adapters.emitProofEvent("learning.config.saved", patch as Record<string, unknown>);
    } catch (error) {
      setConfig(next);
      setSaveMessage(`Save blocked: ${errorMessage(error)} Selection is local only until the learning config API accepts it.`);
    } finally {
      setSaving(false);
    }
  };

  const viewReport = async (report: ReportMeta) => {
    try {
      const content = await adapters.getLearningReport(report.filename);
      setReportPreview(content.content);
      await adapters.emitProofEvent("learning.report.viewed", { filename: report.filename, accepted: true });
    } catch (error) {
      setReportPreview(`Report request failed: ${errorMessage(error)}`);
    }
  };

  const createCandidate = async () => {
    const title = candidateDraft.title.trim();
    const summary = candidateDraft.summary.trim();
    if (!title || !summary) {
      setWorkbenchMessage("Add a title and summary before queuing idle work.");
      return;
    }
    setWorkbenchMessage("Queuing idle work candidate through the local API...");
    try {
      const result = await adapters.createIdleCandidate({
        ...candidateDraft,
        title,
        summary,
        target_files: [],
        created_by: "operator",
      });
      setWorkbenchMessage(result.reason ? `${result.status}: ${result.reason}` : `${result.status}: candidate recorded with proof ${result.proof_event_id ?? "pending"}.`);
      await refreshWorkbench(setWorkbench, setWorkbenchMessage);
      setCandidateDraft((current) => ({ ...current, title: "", summary: "" }));
    } catch (error) {
      setWorkbenchMessage(`Candidate request blocked: ${errorMessage(error)}`);
    }
  };

  const requestReview = async (candidateId: string) => {
    setWorkbenchMessage("Requesting user review approval...");
    try {
      const result = await adapters.requestIdleCandidateReview(candidateId);
      setWorkbenchMessage(`Review approval ${result.approval_id ?? "created"} linked to idle workbench candidate.`);
      await refreshWorkbench(setWorkbench, setWorkbenchMessage);
    } catch (error) {
      setWorkbenchMessage(`Review request blocked: ${errorMessage(error)}`);
    }
  };

  const runCandidate = async (candidateId: string) => {
    setWorkbenchMessage("Running idle candidate through trusted Hermes runtime boundary...");
    try {
      const result = await adapters.runIdleCandidate(candidateId);
      await refreshWorkbench(setWorkbench, setWorkbenchMessage);
      if (result.accepted) {
        const report = result.report?.filename ? ` report ${result.report.filename};` : "";
        setWorkbenchMessage(`Run completed:${report} proof ${result.proof_event_id ?? "recorded"}.`);
      } else {
        setWorkbenchMessage(`Run blocked: ${result.reason ?? result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      }
    } catch (error) {
      setWorkbenchMessage(`Run request blocked: ${errorMessage(error)}`);
    }
  };

  const decideCandidate = async (candidateId: string, decision: "keep" | "remove" | "merge") => {
    setWorkbenchMessage(`${decision} decision requested...`);
    try {
      const result = await adapters.decideIdleCandidate(candidateId, decision, "operator decision from Learning tab");
      setWorkbenchMessage(`${decision}: ${result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      await refreshWorkbench(setWorkbench, setWorkbenchMessage);
    } catch (error) {
      setWorkbenchMessage(`${decision} blocked: ${errorMessage(error)}`);
    }
  };

  return (
    <div data-testid="learning-root" className="grid min-h-[calc(100vh-6.5rem)] gap-3 lg:grid-cols-12">
      <section id="learning.config" className="rounded border border-border bg-surface p-4 lg:col-span-4">
        <h2 className="text-base font-semibold text-fg">IDLE LEARNING MODE</h2>
        <p className="text-sm text-muted">Live reports, idle queue, and user review policy.</p>
        <div className="mt-4 grid gap-3 text-sm">
          <Readonly label="Research Agents" value="Research, Audit, Documentation" />
          <label className="grid gap-1 text-muted">Mode
            <select
              className="rounded border border-border bg-bg px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
              value={config.enabled ? "idle" : "disabled"}
              disabled={saving}
              onChange={(event) => {
                const value = event.target.value;
                void saveField({ enabled: value === "idle" });
              }}
            >
              <option value="idle">idle</option>
              <option value="disabled">disabled</option>
            </select>
          </label>
          <Editable label="Idle Minutes" value={String(config.idle_minutes)} disabled={saving} onSave={(value) => saveField({ idle_minutes: normalizeIdleMinutes(value) })} />
          <Readonly label="Reports Directory" value={config.reports_directory} />
          <Readonly label="Next Topic" value={latestCandidate?.title ?? "No queued candidate yet"} />
          <Readonly label="Queue" value={`${queueCount} active candidate${queueCount === 1 ? "" : "s"}`} />
          <Readonly label="Runtime" value={config.active ? "Idle runner active" : config.enabled ? `Idle selected; ${config.runner_status ?? "runtime blocked"}` : "Disabled by user"} />
          <Readonly label="Agent Runtime" value={automation?.agent_runtime_status === "ready" ? "Hermes runtime ready" : "Hermes runtime not configured"} />
          <Readonly label="Automation" value={`${readyAutomationCount}/${automationCount} execution-ready; queue remains review-gated`} />
          <Readonly label="Policy" value={config.reason ?? (blockedMutations ? "Research only until blockers clear" : "Research and review queue ready")} />
        </div>
        {saveMessage && <div className="mt-3 rounded border border-border bg-bg/40 px-2 py-1 text-xs text-muted">{saveMessage}</div>}
      </section>

      <section id="learning.idle-workbench" className="rounded border border-border bg-surface p-4 lg:col-span-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-fg">IDLE WORKBENCH</h2>
            <p className="text-sm text-muted">{workbench.daily_prompt.question}</p>
          </div>
          <button type="button" onClick={() => void refreshWorkbench(setWorkbench, setWorkbenchMessage)} className="rounded border border-border px-2 py-1 text-xs text-fg">Refresh</button>
        </div>
        <div className="mt-3 rounded border border-border bg-bg/40 p-3 text-xs text-muted">{workbench.review_policy}</div>
        <div className="mt-3 grid gap-2 rounded border border-border bg-bg/40 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-semibold uppercase text-fg">Runtime Truth</div>
              <div className="text-muted">Idle selection is saved separately from executable agent automation.</div>
            </div>
            <span className={statusPill(automationRuntimeReady)}>
              {automationRuntimeReady ? "runtime ready" : "runtime blocked"}
            </span>
          </div>
          {automation?.runner_reason && <div className="text-accent-amber">{automation.runner_reason}</div>}
          {automation?.agent_runtime_reason && <div className="text-accent-amber">{automation.agent_runtime_reason}</div>}
          <div className="grid gap-2 sm:grid-cols-2">
            {automation?.capabilities.map((capability) => (
              <div key={capability.kind} className="rounded border border-border bg-surface/70 p-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-fg">{capability.label}</div>
                    <div className="text-muted">{capability.agent_id}</div>
                  </div>
                  <span className={statusPill(capability.execution_status === "ready")}>
                    {capability.execution_status === "ready" ? "exec ready" : "queue only"}
                  </span>
                </div>
                <div className="mt-1 text-muted">{capability.safety_scope}</div>
                {capability.missing.length > 0 && <div className="mt-1 text-accent-amber">{capability.missing[0]}</div>}
                {capability.proof_required && <div className="mt-1 text-accent-cyan">trust/proof gate required before action</div>}
              </div>
            ))}
            {automation?.capabilities.length === 0 && <div className="rounded border border-border bg-surface/70 p-2 text-muted">Automation readiness is loading from the live idle workbench API.</div>}
          </div>
        </div>
        <div className="mt-3 grid gap-2 text-xs">
          {workbench.blockers.length > 0 ? (
            workbench.blockers.map((blocker) => (
              <div key={`${blocker.type}-${blocker.id ?? blocker.label}`} className="rounded border border-accent-amber/30 bg-accent-amber/10 p-2">
                <div className="font-semibold text-accent-amber">{blocker.label} · {blocker.status}</div>
                <div className="text-muted">{blocker.reason}</div>
              </div>
            ))
          ) : (
            <div className="rounded border border-accent-green/30 bg-accent-green/10 p-2 text-accent-green">No live blockers from printers, open jobs, or approvals.</div>
          )}
        </div>
        <div className="mt-4 grid gap-2 text-sm">
          <label className="grid gap-1 text-muted">Candidate title
            <input
              className="rounded border border-border bg-bg px-2 py-1 text-fg"
              value={candidateDraft.title}
              onChange={(event) => {
                const title = event.target.value;
                setCandidateDraft((current) => ({ ...current, title }));
              }}
            />
          </label>
          <label className="grid gap-1 text-muted">Kind
            <select
              className="rounded border border-border bg-bg px-2 py-1 text-fg"
              value={candidateDraft.kind}
              onChange={(event) => {
                const kind = event.target.value;
                setCandidateDraft((current) => ({ ...current, kind, risk_level: kind === "research" ? "low" : "medium" }));
              }}
            >
              {KIND_OPTIONS.map((kind) => <option key={kind} value={kind}>{kind.replace("_", " ")}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-muted">Target tab
            <input
              className="rounded border border-border bg-bg px-2 py-1 text-fg"
              value={candidateDraft.target_tab ?? ""}
              onChange={(event) => {
                const target_tab = event.target.value;
                setCandidateDraft((current) => ({ ...current, target_tab }));
              }}
            />
          </label>
          <label className="grid gap-1 text-muted">Summary
            <textarea
              className="min-h-20 rounded border border-border bg-bg px-2 py-1 text-fg"
              value={candidateDraft.summary}
              onChange={(event) => {
                const summary = event.target.value;
                setCandidateDraft((current) => ({ ...current, summary }));
              }}
            />
          </label>
          <button type="button" onClick={() => void createCandidate()} className="rounded border border-accent-cyan/60 bg-accent-cyan/10 px-3 py-2 text-sm font-semibold text-accent-cyan">Queue Candidate</button>
          <div className="rounded border border-border bg-bg/40 px-2 py-1 text-xs text-muted">{workbenchMessage}</div>
        </div>
      </section>

      <section id="learning.candidates" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-4">
        <h2 className="text-base font-semibold text-fg">USER REVIEW QUEUE</h2>
        <div className="mt-4 grid content-start gap-2 overflow-auto pr-1">
          {workbench.candidates.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              mergeDisabled={blockedMutations || candidate.approval_id == null || candidate.gate_status.all_passed !== true}
              onRun={runCandidate}
              onReview={requestReview}
              onDecision={decideCandidate}
            />
          ))}
          {workbench.candidates.length === 0 && <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted">No idle workbench candidates returned by the live API.</div>}
        </div>
      </section>

      <section id="learning.resources" className="flex flex-col gap-3 rounded border border-border bg-surface p-4 lg:col-span-6" data-testid="learning-resources">
        <div>
          <h2 className="text-base font-semibold text-fg">LEARNING RESOURCES</h2>
          <p className="text-xs text-muted">
            Static reference links pinned to upstream truth. No backend fetch — links are honest URLs the operator can verify offline.
          </p>
        </div>
        <ul className="grid gap-2 text-sm">
          {LEARNING_RESOURCES.map((resource) => (
            <li key={resource.url}>
              <a
                href={resource.url}
                target="_blank"
                rel="noreferrer noopener"
                className="grid gap-1 rounded border border-border bg-bg/40 p-3 hover:border-accent-cyan/60"
                data-testid={`learning-resource-${resource.id}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-fg">{resource.title}</span>
                  <span className="rounded border border-border px-1.5 py-0.5 text-[10px] uppercase text-muted">{resource.kind}</span>
                </div>
                <span className="text-xs text-muted">{resource.summary}</span>
                <span className="truncate font-mono text-[10px] text-accent-cyan">{resource.url}</span>
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section id="learning.reports" className="flex min-h-[360px] flex-col rounded border border-border bg-surface p-4 lg:col-span-6">
        <h2 className="text-base font-semibold text-fg">RESEARCH REPORTS</h2>
        <div className="mt-4 grid content-start gap-2">
          {reports.map((report) => (
            <div key={report.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded border border-border bg-bg/40 p-3 text-sm">
              <span className="truncate text-fg">{report.filename}</span>
              <span className="text-xs text-muted">{(report.size_bytes / 1024).toFixed(1)} KB</span>
              <button type="button" onClick={() => void viewReport(report)} className="rounded border border-border px-2 py-1 text-xs text-fg">View</button>
            </div>
          ))}
          {reports.length === 0 && <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted">No research reports returned by the live learning API.</div>}
        </div>
        <pre className="mt-4 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded bg-bg/70 p-3 text-xs text-muted">{reportPreview}</pre>
      </section>
    </div>
  );
}

/**
 * Curated static learning resources — these are NOT fetched from any backend.
 * They are honest reference URLs to upstream truth (Hermes Agent repo + project docs).
 * When backend reports are unreachable, this section still gives the operator
 * verifiable starting points instead of a blank tab.
 */
const LEARNING_RESOURCES: { id: string; title: string; summary: string; url: string; kind: string }[] = [
  {
    id: "hermes-agent",
    title: "NousResearch / hermes-agent",
    summary: "Upstream Hermes Agent runtime. Source of v0.13 'Tenacity Release' + supervisor patterns.",
    url: "https://github.com/NousResearch/hermes-agent",
    kind: "repo",
  },
  {
    id: "hermes3d",
    title: "Ghenghis / Hermes3D",
    summary: "This workbench. Includes printer safety policies, observe routes, and Hermes Agent integration.",
    url: "https://github.com/Ghenghis/Hermes3D",
    kind: "repo",
  },
  {
    id: "hermesproof",
    title: "Ghenghis / HermesProof",
    summary: "Proof-gated supervision and truth-gate library used by Hermes Agent Workbench evidence chain.",
    url: "https://github.com/Ghenghis/HermesProof",
    kind: "repo",
  },
  {
    id: "a2a-protocol",
    title: "Agent-to-Agent (A2A) Protocol",
    summary: "Specification for handoff/task transfer between agents — what hermes_a2a_* MCP tools implement.",
    url: "https://github.com/google/A2A",
    kind: "spec",
  },
];

async function refreshWorkbench(
  setWorkbench: (state: IdleWorkbenchState) => void,
  setMessage: (message: string) => void,
) {
  try {
    const next = await adapters.getIdleWorkbench();
    setWorkbench(next);
    setMessage(`Idle workbench loaded: ${next.candidates.length} candidate${next.candidates.length === 1 ? "" : "s"}, ${next.blockers.length} blocker${next.blockers.length === 1 ? "" : "s"}.`);
  } catch (error) {
    setMessage(`Idle workbench unavailable: ${errorMessage(error)}`);
  }
}

function normalizeIdleMinutes(value: string): number {
  const minutes = Number.parseInt(value, 10);
  return Number.isFinite(minutes) && minutes > 0 ? minutes : 30;
}

function learningConfigMessage(config: LearningConfig): string {
  if (config.enabled && !config.active) {
    return `Saved Idle selection; runtime blocked: ${config.reason ?? "idle learning runner is not configured."}`;
  }
  return "Saved learning config to /api/learning/config.";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown backend error.";
}

function statusPill(ready: boolean): string {
  return `rounded border px-2 py-0.5 text-[10px] uppercase ${ready ? "border-accent-green/40 bg-accent-green/10 text-accent-green" : "border-accent-amber/40 bg-accent-amber/10 text-accent-amber"}`;
}

function Readonly({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs uppercase text-muted">{label}</div><div className="text-fg">{value}</div></div>;
}

function Editable({ label, value, disabled = false, onSave }: { label: string; value: string; disabled?: boolean; onSave: (value: string) => Promise<unknown> }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <label className="grid grid-cols-[1fr_auto] gap-2 text-muted">
      <span className="col-span-2 text-xs uppercase">{label}</span>
      <input
        className="rounded border border-border bg-bg px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
        value={draft}
        disabled={disabled}
        onChange={(event) => {
          const value = event.target.value;
          setDraft(value);
        }}
      />
      <button type="button" disabled={disabled} onClick={() => void onSave(draft)} className="rounded border border-border px-2 py-1 text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50">Save</button>
    </label>
  );
}

function CandidateCard({
  candidate,
  mergeDisabled,
  onRun,
  onReview,
  onDecision,
}: {
  candidate: IdleWorkbenchCandidate;
  mergeDisabled: boolean;
  onRun: (candidateId: string) => Promise<void>;
  onReview: (candidateId: string) => Promise<void>;
  onDecision: (candidateId: string, decision: "keep" | "remove" | "merge") => Promise<void>;
}) {
  return (
    <article className="rounded border border-border bg-bg/40 p-3 text-xs">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-fg">{candidate.title}</div>
          <div className="text-muted">{candidate.kind.replace("_", " ")} · {candidate.status}</div>
        </div>
        <span className="rounded border border-border px-2 py-0.5 text-[10px] uppercase text-muted">{candidate.risk_level}</span>
      </div>
      <p className="mt-2 text-muted">{candidate.summary}</p>
      {candidate.blocked_reason && <div className="mt-2 rounded border border-accent-amber/30 bg-accent-amber/10 p-2 text-accent-amber">{candidate.blocked_reason}</div>}
      <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-muted">
        <span>Agent: {candidate.agent_id}</span>
        <span>Proof: {candidate.proof_event_ids.length}</span>
        <span>Tab: {candidate.target_tab ?? "none"}</span>
        <span>Approval: {candidate.approval_id ?? "none"}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <button type="button" onClick={() => void onRun(candidate.id)} className="rounded border border-accent-cyan/60 px-2 py-1 text-accent-cyan">Run</button>
        <button type="button" onClick={() => void onReview(candidate.id)} className="rounded border border-border px-2 py-1 text-fg">Review</button>
        <button type="button" onClick={() => void onDecision(candidate.id, "keep")} className="rounded border border-border px-2 py-1 text-fg">Keep</button>
        <button type="button" onClick={() => void onDecision(candidate.id, "remove")} className="rounded border border-border px-2 py-1 text-fg">Remove</button>
        <button
          type="button"
          disabled={mergeDisabled}
          onClick={() => void onDecision(candidate.id, "merge")}
          className="rounded border border-border px-2 py-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          Merge
        </button>
      </div>
    </article>
  );
}
