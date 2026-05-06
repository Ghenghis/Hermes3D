/**
 * 3D Generation tab.
 *
 * Prompt + reference image · provider selector · generated model cards ·
 * "Send to Blender MCP" (locked).
 */
import { Panel } from "../components/layout/Panel";
import { WorkflowPipeline, type PipelineStage } from "../components/pipeline/WorkflowPipeline";
import { adapters } from "../api/adapters";
import type { TaskDAG } from "../types/dag";
import type { ProviderHealth } from "../types/provider";
import { GitBranch, Image as ImageIcon } from "lucide-react";
import { useEffect, useState } from "react";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

interface GeneratedModelResult {
  jobId: string;
  template: string;
  artifactLabel: string;
  artifactPath: string;
  artifactSize: number;
  previewLabel?: string;
  proofLabel?: string;
  proofEvent?: string;
  truthGate?: string;
}

export function Gen3DTab() {
  const [prompt, setPrompt] = useState("calibration cube");
  const [sizeMm, setSizeMm] = useState(20);
  const [previewDag, setPreviewDag] = useState<TaskDAG | null>(null);
  const [previewState, setPreviewState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [providerHealth, setProviderHealth] = useState<ProviderHealth[]>([]);
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [generatedModels, setGeneratedModels] = useState<GeneratedModelResult[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [referenceMessage, setReferenceMessage] = useState<string | null>(null);
  const plannerMode = previewDag?.metadata?.planner_mode;

  useEffect(() => {
    let cancelled = false;
    adapters.getProviderHealth()
      .then((data) => {
        if (!cancelled) setProviderHealth(data);
      })
      .catch((error) => {
        if (!cancelled) setGenerateMessage(`Blocked: ${errorMessage(error)}`);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const previewPlan = async () => {
    setPreviewState("loading");
    try {
      const dag = await adapters.planPreview(prompt);
      setPreviewDag(dag);
      setPreviewState("ready");
    } catch (error) {
      setPreviewDag(null);
      setPreviewState("error");
      setGenerateMessage(`Blocked: ${errorMessage(error)}`);
    }
  };

  const runGeneration = async () => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/generation/run`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, constraints: { size_mm: sizeMm } }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const accepted = actionAccepted(response.ok, payload);
      setGenerateMessage(`${accepted ? "Accepted" : "Blocked"}: ${generationSummary(payload, response.statusText)}`);
      if (accepted) {
        const parsed = parseGeneratedModel(payload);
        if (parsed) {
          setGeneratedModels((current) => [parsed, ...current].slice(0, 8));
        }
      }
      await adapters.emitProofEvent("generation.run.requested", { accepted, response: payload });
    } catch {
      setGenerateMessage("Blocked: generation backend API is unreachable.");
      await adapters.emitProofEvent("generation.run.requested", { accepted: false, reason: "backend_unreachable" });
    }
  };

  const attachReference = async () => {
    if (referenceFile == null) {
      setReferenceMessage("Select a reference image before attaching.");
      return;
    }
    const params = new URLSearchParams({
      evidence_type: "screenshot",
      stage: "INTAKE",
      label: referenceFile.name,
      notes: `3D generation reference image for prompt: ${prompt}`,
    });
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/artifacts?${params.toString()}`, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: await referenceFile.arrayBuffer(),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      setReferenceMessage(`${response.ok ? "Attached" : "Blocked"}: ${generationSummary(payload, response.statusText)}`);
      await adapters.emitProofEvent("generation.reference.attached", { accepted: response.ok, filename: referenceFile.name, response: payload });
    } catch {
      setReferenceMessage("Blocked: artifacts backend API is unreachable.");
      await adapters.emitProofEvent("generation.reference.attached", { accepted: false, filename: referenceFile.name, reason: "backend_unreachable" });
    }
  };

  return (
    <div className="grid min-h-[calc(100vh-6.5rem)] grid-cols-12 gap-2.5 lg:grid-rows-[minmax(270px,0.95fr)_minmax(170px,0.55fr)_minmax(260px,1fr)]" data-testid="gen3d-root">
      <div className="col-span-12 min-h-0 lg:col-span-8">
        <Panel
          id="gen3d.input"
          title="PROMPT + REFERENCE"
          dense
          status={{ tone: "muted", label: "input" }}
          className="h-full min-h-0"
        >
          <div className="grid grid-cols-3 gap-3 h-full text-xs">
            <div className="col-span-2 flex flex-col gap-2 min-w-0">
              <label
                htmlFor="gen3d-prompt"
                className="text-muted text-[10px] uppercase tracking-wide"
              >
                Text Prompt
              </label>
              <textarea
                id="gen3d-prompt"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                className="flex-1 bg-surface2/40 border border-border rounded p-2 font-mono text-[11px] text-fg leading-relaxed resize-none outline-none focus:border-accent-cyan/60"
                spellCheck={false}
              />
              <label className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted">
                Size mm
                <input
                  aria-label="Generation size mm"
                  type="number"
                  min={5}
                  max={80}
                  value={sizeMm}
                  onChange={(event) => setSizeMm(Number(event.target.value))}
                  className="w-20 rounded border border-border bg-bg px-2 py-1 text-[11px] font-semibold text-fg"
                />
              </label>
              <div className="flex justify-end gap-1.5">
                <button
                  type="button"
                  onClick={previewPlan}
                  disabled={previewState === "loading"}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-accent-cyan/15 border border-accent-cyan/40 text-accent-cyan text-[11px] hover:bg-accent-cyan/20 disabled:opacity-60"
                >
                  <GitBranch size={11} />
                  <span>{previewState === "loading" ? "Previewing" : "Preview plan"}</span>
                </button>
                {plannerMode === "llm" && (
                  <span
                    data-testid="gen3d-planner-mode-badge"
                    data-mode="llm"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent-cyan/10 border border-accent-cyan/40 text-accent-cyan text-[11px]"
                  >
                    via LLM ✓
                  </span>
                )}
                {plannerMode === "template" && (
                  <span
                    data-testid="gen3d-planner-mode-badge"
                    data-mode="template"
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface2/40 border border-border text-muted text-[11px]"
                  >
                    template ↻
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => void runGeneration()}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-surface2/50 text-fg text-[11px] hover:border-accent-blue/50"
                >
                  Generate
                </button>
              </div>
              {generateMessage && <div className="rounded border border-border bg-bg/50 px-2 py-1 text-[10px] text-muted">{generateMessage}</div>}
            </div>
            <div className="col-span-1 flex flex-col gap-2 min-w-0">
              <div className="text-muted text-[10px] uppercase tracking-wide">Reference Image</div>
              <div className="flex-1 bg-surface2/30 border border-dashed border-border rounded flex flex-col items-center justify-center gap-2 p-2 text-muted text-[10px]">
                <ImageIcon size={20} className="text-muted/60" />
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp"
                  onChange={(event) => setReferenceFile(event.target.files?.[0] ?? null)}
                  className="w-full text-[10px]"
                />
                <button type="button" onClick={() => void attachReference()} className="rounded border border-border px-2 py-1 text-[10px] text-fg">
                  Attach
                </button>
                {referenceMessage && <span className="text-[9px]">{referenceMessage}</span>}
              </div>
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 min-h-0 lg:col-span-4">
        <Panel
          id="gen3d.providers"
          title="PROVIDERS"
          dense
          status={{ tone: providerHealth.some((p) => p.status === "green") ? "green" : "muted", label: `${providerHealth.length} live` }}
          className="h-full min-h-0"
        >
          <div data-testid="gen3d-provider-health">
            <div className="text-muted text-[10px] uppercase tracking-wide mb-1">
              Live Provider Health
            </div>
            {providerHealth.length > 0 ? (
              <ul className="flex flex-col gap-1">
                {providerHealth.map((p) => (
                  <li
                    key={p.provider_id}
                    className="flex items-center gap-2 px-1 py-0.5 text-[11px]"
                  >
                    <span
                      data-testid="gen3d-provider-dot"
                      data-provider={p.provider_id}
                      data-status={p.status}
                      aria-label={`${p.provider_id} status ${p.status}`}
                      className={[
                        "h-1.5 w-1.5 rounded-full shrink-0",
                        p.status === "green"
                          ? "bg-accent-green"
                          : p.status === "amber"
                            ? "bg-amber-400"
                            : p.status === "red"
                              ? "bg-red-500"
                              : "bg-muted",
                      ].join(" ")}
                    />
                    <span className="text-fg font-medium">{p.provider_id}</span>
                    <span className="text-muted text-[10px] font-mono">{p.status}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="No live providers" detail="The provider health API returned no configured providers." />
            )}
          </div>
        </Panel>
      </div>
      <div className="col-span-12 min-h-0">
        <Panel
          id="gen3d.plan"
          title="PLAN PREVIEW"
          dense
          status={{ tone: previewState === "ready" ? "cyan" : "muted", label: previewState }}
          className="h-full min-h-0"
        >
          <div
            className="h-full flex flex-col gap-2"
            data-testid="gen3d-plan-preview"
            data-run-id={previewDag?.run_id ?? "none"}
          >
            {previewDag ? (
              <>
                <WorkflowPipeline stages={dagToStages(previewDag)} />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 overflow-auto">
                  {previewDag.nodes.map((node) => (
                    <div
                      key={node.node_id}
                      data-testid="gen3d-plan-node"
                      data-tool={node.tool}
                      className="bg-surface2/40 border border-border rounded px-2 py-1.5 text-xs min-w-0"
                    >
                      <div className="text-fg font-medium truncate">{node.kind}</div>
                      <div className="text-muted text-[10px] font-mono truncate">{node.tool}</div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-muted text-xs">
                No plan preview loaded
              </div>
            )}
          </div>
        </Panel>
      </div>
      <div className="col-span-12 min-h-0">
        <Panel
          id="gen3d.results"
          title="GENERATED MODELS"
          dense
          status={{ tone: generatedModels.length > 0 ? "cyan" : "muted", label: `${generatedModels.length} models` }}
          className="h-full min-h-0"
        >
          {generatedModels.length > 0 ? (
            <div className="grid h-full min-h-0 gap-2 overflow-auto md:grid-cols-2 xl:grid-cols-3">
              {generatedModels.map((model) => (
                <article key={`${model.jobId}-${model.artifactLabel}`} className="grid min-h-[150px] grid-rows-[auto_1fr_auto] gap-2 rounded border border-border bg-surface2/30 p-3 text-xs">
                  <div className="flex min-w-0 items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-fg">{model.artifactLabel}</div>
                      <div className="truncate font-mono text-[10px] text-muted">{model.jobId}</div>
                    </div>
                    <span className="rounded bg-accent-green/15 px-2 py-1 text-[10px] uppercase text-accent-green">{model.truthGate ?? "proof"}</span>
                  </div>
                  <div className="grid content-start gap-1 text-[11px] text-muted">
                    <div className="truncate">Template: <span className="text-fg">{model.template}</span></div>
                    <div className="truncate">Mesh: <span className="font-mono text-fg">{formatBytes(model.artifactSize)}</span></div>
                    {model.previewLabel && <div className="truncate">Preview: <span className="font-mono text-fg">{model.previewLabel}</span></div>}
                    {model.proofLabel && <div className="truncate">Proof: <span className="font-mono text-fg">{model.proofLabel}</span></div>}
                  </div>
                  <div className="truncate font-mono text-[10px] text-accent-cyan">{model.proofEvent ?? model.artifactPath}</div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No generated models" detail="No generated model artifacts were returned by the backend." />
          )}
        </Panel>
      </div>
    </div>
  );
}

function generationSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return fallback || "No response body.";
  }
  if (isRecord(payload.detail)) {
    return String(payload.detail.reason ?? payload.detail.message ?? payload.detail.status ?? fallback);
  }
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (isRecord(payload.artifact) && typeof payload.artifact.label === "string") {
    const proofId = isRecord(payload.proof) && typeof payload.proof.event_id === "string" ? `; proof ${payload.proof.event_id}` : "";
    return `${payload.artifact.label}${proofId}`;
  }
  return String(payload.reason ?? payload.message ?? payload.status ?? payload.id ?? payload.artifact_id ?? fallback);
}

function actionAccepted(httpOk: boolean, payload: unknown): boolean {
  if (!httpOk) {
    return false;
  }
  if (!isRecord(payload)) {
    return true;
  }
  const falseFlags = ["accepted", "success", "queued", "created", "started", "uploaded"] as const;
  if (falseFlags.some((key) => payload[key] === false)) {
    return false;
  }
  const status = typeof payload.status === "string" ? payload.status.toLowerCase() : "";
  return !["blocked", "failed", "error", "not_configured", "unreachable", "rejected"].includes(status);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function parseGeneratedModel(payload: unknown): GeneratedModelResult | null {
  if (!isRecord(payload) || typeof payload.job_id !== "string" || !isRecord(payload.artifact)) {
    return null;
  }
  const artifact = payload.artifact;
  if (typeof artifact.label !== "string" || typeof artifact.file_path !== "string") {
    return null;
  }
  return {
    jobId: payload.job_id,
    template: typeof payload.template === "string" ? payload.template : "local_template",
    artifactLabel: artifact.label,
    artifactPath: artifact.file_path,
    artifactSize: typeof artifact.file_size === "number" ? artifact.file_size : 0,
    previewLabel: isRecord(payload.preview) && typeof payload.preview.label === "string" ? payload.preview.label : undefined,
    proofLabel: isRecord(payload.proof) && typeof payload.proof.label === "string" ? payload.proof.label : undefined,
    proofEvent: isRecord(payload.proof) && typeof payload.proof.event_id === "string" ? payload.proof.event_id : undefined,
    truthGate: isRecord(payload.truth_gate) && typeof payload.truth_gate.status === "string" ? payload.truth_gate.status : undefined,
  };
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${bytes} B`;
}

function dagToStages(dag: TaskDAG): PipelineStage[] {
  return dag.nodes.map((node, index) => ({
    id: node.node_id,
    label: node.kind.split(".").at(-1)?.replaceAll("_", " ") ?? node.tool,
    status: index === 0 ? "active" : "pending",
    detail: node.tool,
  }));
}

function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-xs">
      <div className="font-medium text-fg">{title}</div>
      <div className="max-w-[320px] text-muted">{detail}</div>
    </div>
  );
}
