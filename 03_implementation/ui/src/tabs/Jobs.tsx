import { useCallback, useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import type { Job } from "../types/job";
import type { JobDetail } from "../types/job-detail";
import type { Printer } from "../types/printer";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const FILTERS = [
  { id: "queued", label: "Queued" },
  { id: "printing", label: "Running" },
  { id: "completed", label: "Done" },
  { id: "failed", label: "Failed" },
  { id: "cancelled", label: "Cancelled" },
] as const;

const PIPELINE_STAGES = [
  { id: "model", label: "Model", gate: "MODEL_INTAKE", terms: ["model", "intake", "design"] },
  { id: "slice", label: "Slice", gate: "SLICER_OUTPUT", terms: ["slice", "slicer", "gcode", "g-code"] },
  { id: "bounds", label: "Bounds", gate: "GCODE_BOUNDS", terms: ["bounds", "size", "volume"] },
  { id: "approval", label: "Approval", gate: "PRINT_APPROVAL", terms: ["approval", "approve"] },
  { id: "upload", label: "Upload", gate: "MOONRAKER_UPLOAD", terms: ["upload", "moonraker"] },
  { id: "print", label: "Print", gate: "PRINTER_IDLE", terms: ["print", "start"] },
  { id: "observe", label: "Observe", gate: "CAMERA_OBSERVE", terms: ["observe", "camera", "plate"] },
  { id: "complete", label: "Complete", gate: "COMPLETE_PROOF", terms: ["complete", "done"] },
  { id: "repair", label: "Repair", gate: "REPAIR_APPROVAL", terms: ["repair", "rollback"] },
] as const;

type PipelineStageStatus = "done" | "running" | "blocked" | "pending";

export function JobsTab() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [activeFilter, setActiveFilter] = useState<(typeof FILTERS)[number]["id"]>("queued");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [detail, setDetail] = useState<JobDetail | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const printerName = useMemo(() => new Map(printers.map((printer) => [printer.id, printer.name])), [printers]);

  const loadJobs = useCallback(() => {
    void adapters.getJobs(activeFilter)
      .then((next) => {
        setJobs(next);
        setLoadError(null);
      })
      .catch((error) => {
        setLoadError(errorMessage(error));
        setJobs([]);
      });
  }, [activeFilter]);

  useEffect(() => {
    loadJobs();
    void adapters.getPrinters().then(setPrinters);
    const timer = activeFilter === "queued" || activeFilter === "printing" ? window.setInterval(loadJobs, 10_000) : null;
    return () => {
      if (timer != null) {
        window.clearInterval(timer);
      }
    };
  }, [activeFilter, loadJobs]);

  useEffect(() => {
    if (jobs.length === 0) {
      setSelectedJobId(null);
      return;
    }
    if (selectedJobId == null || !jobs.some((job) => job.id === selectedJobId)) {
      setSelectedJobId(jobs[0].id);
    }
  }, [jobs, selectedJobId]);

  useEffect(() => {
    if (selectedJobId == null) {
      setDetail(null);
      setActionMessage(null);
      return;
    }
    setActionMessage(null);
    void adapters.getJobDetail(selectedJobId)
      .then(setDetail)
      .catch((error) => {
        setDetail(null);
        setActionMessage(`Blocked: ${errorMessage(error)}`);
      });
    void adapters.emitProofEvent("jobs.job.selected", { job_id: selectedJobId });
  }, [selectedJobId]);

  // Only show the count for the active filter — inactive filters show no count because the API
  // is not queried for them, so displaying "0" would be a fake/misleading value.
  const activeFilterCount = jobs.length;
  const cancel = async () => {
    if (!detail || !window.confirm(`Cancel job ${detail.title}? This cannot be undone.`)) {
      return;
    }
    try {
      await adapters.cancelJob(detail.id);
      await adapters.emitProofEvent("jobs.job.cancelled", { job_id: detail.id, accepted: true });
      setActionMessage(`Cancelled job ${detail.id}.`);
      loadJobs();
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
    }
  };
  const reloadSelectedJob = async (jobId: string) => {
    const next = await adapters.getJobDetail(jobId);
    setDetail(next);
    loadJobs();
  };
  const runTransition = async (action: "propose" | "apply" | "retry" | "rollback") => {
    if (!detail) {
      return;
    }
    try {
      if (action === "propose") {
        const reason = window.prompt("Request a repair proposal for this failed job step?", detail.transition_state?.failed_step?.error ?? "") ?? "";
        const result = await adapters.proposeJobRepair(detail.id, reason);
        setActionMessage(`Repair approval ${result.approval_id ?? "created"} is ${result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      } else if (action === "apply") {
        const result = await adapters.applyJobRepair(detail.id, "Operator approved repair execution from Jobs tab.");
        setActionMessage(`Repair ${result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      } else if (action === "retry") {
        const result = await adapters.retryJob(detail.id, "Operator retried from Jobs tab after proof review.");
        setActionMessage(`Retry moved job to ${result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      } else {
        const target = detail.transition_state?.rollback_targets[0];
        const result = await adapters.rollbackJob(detail.id, target?.id);
        setActionMessage(`Rollback moved job to ${result.status}; proof ${result.proof_event_id ?? "recorded"}.`);
      }
      await reloadSelectedJob(detail.id);
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
      await reloadSelectedJob(detail.id).catch(() => undefined);
    }
  };

  return (
    <div data-testid="jobs-root" className="grid min-h-[calc(100vh-6.5rem)] gap-3 lg:grid-cols-12">
      <section className="flex min-h-0 flex-col rounded border border-border bg-surface p-3 lg:col-span-5">
        <div className="flex gap-2 border-b border-border">
          {FILTERS.map((filter) => (
            <button key={filter.id} type="button" onClick={() => setActiveFilter(filter.id)} className={`px-3 py-2 text-sm ${activeFilter === filter.id ? "border-b-2 border-accent-blue text-fg" : "text-muted"}`}>
              {filter.label}
              {filter.id === activeFilter && (
                <span className="ml-1 text-xs">{activeFilterCount}</span>
              )}
            </button>
          ))}
        </div>
        <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
          {jobs.map((job) => (
            <button key={job.id} type="button" onClick={() => setSelectedJobId(job.id)} className="rounded border border-border bg-bg/40 p-3 text-left hover:border-accent-blue">
              <div className="flex items-center justify-between gap-3">
                <span className="truncate font-medium text-fg">{job.name}</span>
                <span className="rounded bg-surface2 px-2 py-1 text-xs uppercase text-muted">{job.status}</span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-xs text-muted">
                <span>{new Date(job.started_utc).toLocaleTimeString()}</span>
                <span>{job.printer_id ? printerName.get(job.printer_id) ?? job.printer_id : "unassigned"}</span>
              </div>
            </button>
          ))}
          {jobs.length === 0 && (
            <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted">
              {loadError ? `Jobs API blocked: ${loadError}` : `No ${activeFilter} jobs returned by the live jobs API.`}
            </div>
          )}
        </div>
      </section>

      <section className="flex min-h-0 flex-col rounded border border-border bg-surface p-3 lg:col-span-7">
        {detail ? (
          <>
            {(() => {
              const cancellable = detail.status === "queued" || detail.status === "running";
              const cancelReason = cancellable ? "Cancel this queued/running job." : `Job status ${detail.status} is not cancellable by the backend.`;
              return (
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-fg">{detail.title}</h2>
                <p className="text-sm text-muted">{detail.type} · {detail.status}</p>
              </div>
              <button
                type="button"
                disabled={!cancellable}
                title={cancelReason}
                onClick={() => void cancel()}
                className="rounded border border-red-800 px-3 py-1 text-sm text-red-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
              );
            })()}
            {actionMessage && <div className="mt-3 rounded border border-border bg-bg/40 p-2 text-xs text-muted">{actionMessage}</div>}
            <div className="mt-4 grid min-h-0 flex-1 content-start gap-3 overflow-auto">
              <JobPipelineSummary detail={detail} printerLabel={detail.printer_id ? printerName.get(detail.printer_id) ?? detail.printer_id : "unassigned"} onTransition={(action) => void runTransition(action)} />
              <SubPanel title="Workflow Steps">
                {detail.steps.map((step) => <Row key={step.id} left={step.description} right={step.status} />)}
                {detail.steps.length === 0 && <div className="text-sm text-muted">No workflow steps returned for this job yet.</div>}
              </SubPanel>
              <SubPanel title="Artifacts">
                {detail.artifacts.map((artifact) => (
                  <Row key={artifact.id} left={`${artifact.name} · ${artifact.kind}`} right={<button type="button" onClick={() => void downloadArtifact(detail.id, artifact.id, artifact.url, setActionMessage)} className="rounded border border-border px-2 py-1 text-xs text-fg">Download</button>} />
                ))}
                {detail.artifacts.length === 0 && <div className="text-sm text-muted">No artifacts returned for this job.</div>}
              </SubPanel>
              <SubPanel title="Events">
                {detail.events.map((event) => <Row key={event.id} left={`${event.type}: ${event.description}`} right={new Date(event.timestamp).toLocaleTimeString()} />)}
                {detail.events.length === 0 && <div className="text-sm text-muted">No events returned for this job.</div>}
              </SubPanel>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-muted">Select a job</div>
        )}
      </section>
    </div>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the request.";
}

async function downloadArtifact(jobId: string, artifactId: string, url: string, setMessage: (message: string) => void) {
  const target = url || `${LIVE_BASE_URL}/api/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(artifactId)}/download`;
  try {
    const response = await fetch(target, { method: "GET", cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    window.open(target, "_blank", "noopener,noreferrer");
    setMessage(`Opened artifact ${artifactId}.`);
    await adapters.emitProofEvent("jobs.artifact.downloaded", { job_id: jobId, artifact_id: artifactId, accepted: true });
  } catch (error) {
    setMessage(`Blocked: artifact download failed: ${errorMessage(error)}`);
  }
}

function JobPipelineSummary({ detail, printerLabel, onTransition }: { detail: JobDetail; printerLabel: string; onTransition: (action: "propose" | "apply" | "retry" | "rollback") => void }) {
  const stageRows = PIPELINE_STAGES.map((stage) => ({
    ...stage,
    status: pipelineStageStatus(detail, stage),
  }));
  const blocker = currentBlocker(detail, printerLabel);
  const transition = detail.transition_state;
  const rollbackTarget = transition?.rollback_targets[0] ?? null;
  return (
    <SubPanel title="Proof-Gated Pipeline">
      <div className="grid gap-2 xl:grid-cols-[1fr_0.85fr]">
        <div className="grid grid-cols-3 gap-1 md:grid-cols-5 xl:grid-cols-9">
          {stageRows.map((stage) => (
            <div key={stage.id} className={`rounded border px-2 py-2 text-center ${stageClass(stage.status)}`}>
              <div className="truncate text-[10px] font-semibold uppercase">{stage.label}</div>
              <div className="mt-1 truncate font-mono text-[9px]">{stage.gate}</div>
              <div className="mt-1 text-[10px]">{stage.status}</div>
            </div>
          ))}
        </div>
        <div className="rounded border border-border bg-surface2/40 p-2 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-fg">Current blocker</span>
            <span className="rounded bg-bg px-2 py-0.5 font-mono text-[10px] text-muted">{blocker.gate}</span>
          </div>
          <div className="mt-1 text-fg">{blocker.title}</div>
          <div className="mt-1 text-muted">{blocker.reason}</div>
          {transition && (
            <div className="mt-2 rounded border border-border bg-bg/40 p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] uppercase text-muted">Backend transition state</span>
                <span className="font-mono text-[10px] text-muted">{transition.blocker.gate}</span>
              </div>
              <p className="mt-1 text-[11px] text-muted">{transition.blocker.reason}</p>
              {transition.pending_repair_approval_id && <p className="mt-1 font-mono text-[10px] text-amber-200">pending {transition.pending_repair_approval_id}</p>}
              {transition.approved_repair_approval_id && <p className="mt-1 font-mono text-[10px] text-green-200">approved {transition.approved_repair_approval_id}</p>}
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-1">
            <button
              type="button"
              disabled={!transition?.can_request_repair}
              onClick={() => onTransition("propose")}
              className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:text-muted disabled:opacity-60"
              title={transition?.can_request_repair ? "Create a real REPAIR_APPROVAL record and proof event." : "Repair proposal is only available for failed jobs without pending repair approval."}
            >
              Request Repair
            </button>
            <button
              type="button"
              disabled={!transition?.can_apply_repair}
              onClick={() => onTransition("apply")}
              className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:text-muted disabled:opacity-60"
              title={transition?.can_apply_repair ? "Run the backend repair agent result and record proof." : "Repair execution requires an approved REPAIR_APPROVAL."}
            >
              Apply Repair
            </button>
            <button
              type="button"
              disabled={!transition?.can_retry}
              onClick={() => onTransition("retry")}
              className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:text-muted disabled:opacity-60"
              title={transition?.can_retry ? "Queue the job for retry and record proof." : "Retry is blocked until the backend transition state allows it."}
            >
              Retry
            </button>
            <button
              type="button"
              disabled={!transition?.can_rollback}
              onClick={() => onTransition("rollback")}
              className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:text-muted disabled:opacity-60"
              title={rollbackTarget ? `Rollback to ${rollbackTarget.label ?? rollbackTarget.id}.` : "Rollback requires a recorded checkpoint artifact."}
            >
              Rollback
            </button>
          </div>
        </div>
      </div>
    </SubPanel>
  );
}

function pipelineStageStatus(detail: JobDetail, stage: (typeof PIPELINE_STAGES)[number]): PipelineStageStatus {
  const step = detail.steps.find((item) => stage.terms.some((term) => item.description.toLowerCase().includes(term)));
  if (step?.status === "done") return "done";
  if (step?.status === "running") return "running";
  if (step?.status === "failed") return "blocked";
  if (stage.id === "repair" && detail.steps.some((item) => item.status === "failed")) return "running";
  if ((detail.status === "completed" || detail.status === "done") && stage.id !== "repair") return "done";
  if (detail.status === "waiting_approval" && stage.id === "approval") return "blocked";
  if ((detail.status === "printing" || detail.status === "running") && ["model", "slice", "bounds", "approval", "upload"].includes(stage.id)) return "done";
  if ((detail.status === "printing" || detail.status === "running") && stage.id === "print") return "running";
  if (detail.status === "failed" && stage.id === "repair") return "running";
  return "pending";
}

function currentBlocker(detail: JobDetail, printerLabel: string): { title: string; gate: string; reason: string } {
  const failedStep = detail.steps.find((step) => step.status === "failed");
  if (failedStep) {
    return {
      title: failedStep.description,
      gate: "REPAIR_APPROVAL",
      reason: failedStep.error || "A workflow step failed; Hermes Agents need an explicit repair or rollback decision before mutating artifacts.",
    };
  }
  if (detail.status === "waiting_approval") {
    return {
      title: "Print approval required",
      gate: "PRINT_APPROVAL",
      reason: "Approve the print job before upload/start can pass backend gates.",
    };
  }
  if (!detail.printer_id) {
    return {
      title: "Printer target missing",
      gate: "TARGET_PRINTER",
      reason: "Assign a printer before slice/upload/print actions can proceed.",
    };
  }
  const hasGcode = detail.artifacts.some((artifact) => artifact.kind === "gcode");
  if (!hasGcode && detail.status !== "completed" && detail.status !== "done") {
    return {
      title: "G-code artifact missing",
      gate: "SLICER_OUTPUT",
      reason: `Selected printer: ${printerLabel}. Slice output must exist before upload/start gates run.`,
    };
  }
  if (detail.status === "printing" || detail.status === "running") {
    return {
      title: "Observe active print",
      gate: "CAMERA_OBSERVE",
      reason: `Monitor ${printerLabel}, plate state, and Moonraker status until completion proof is recorded.`,
    };
  }
  return {
    title: "No active blocker",
    gate: "COMPLETE_PROOF",
    reason: "The job detail API did not report a blocking step.",
  };
}

function stageClass(status: PipelineStageStatus): string {
  if (status === "done") return "border-green-700/60 bg-green-950/30 text-green-200";
  if (status === "running") return "border-cyan-700/60 bg-cyan-950/30 text-cyan-200";
  if (status === "blocked") return "border-amber-700/60 bg-amber-950/30 text-amber-200";
  return "border-border bg-bg/50 text-muted";
}

function SubPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-border bg-bg/40 p-3">
      <h3 className="mb-2 text-xs font-semibold uppercase text-muted">{title}</h3>
      <div className="grid gap-1 text-sm">{children}</div>
    </div>
  );
}

function Row({ left, right }: { left: React.ReactNode; right: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded bg-surface2/40 px-2 py-1">
      <span className="min-w-0 truncate text-fg">{left}</span>
      <span className="shrink-0 text-muted">{right}</span>
    </div>
  );
}
