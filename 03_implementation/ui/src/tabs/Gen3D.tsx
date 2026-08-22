/**
 * 3D Generation tab.
 *
 * Prompt + reference image · provider selector · generated model cards ·
 * "Send to Blender MCP" (locked).
 *
 * Lane 13 additions (H3D-CLAUDE-GEN3D):
 *  - Provider status panel backed by real /api/gen3d/providers data
 *    (sourced from Lane 04 GEN3D_VERIFY proof + live port probes)
 *  - Local template gallery backed by real /api/gen3d/templates data
 *  - Generate button shows "Provider not available" for provider-backed
 *    templates when the provider is not available
 */
import { Panel } from "../components/layout/Panel";
import { WorkflowPipeline, type PipelineStage } from "../components/pipeline/WorkflowPipeline";
import { adapters } from "../api/adapters";
import type { TaskDAG } from "../types/dag";
import type { ProviderHealth } from "../types/provider";
import type { Artifact } from "../types/artifact";
import { GitBranch, Image as ImageIcon, Layers, AlertTriangle } from "lucide-react";
import { useCallback, useState } from "react";
import { PANEL_POLL_MS, usePollingEffect } from "../hooks/_useQuery";

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
  packageLabel?: string;
  packagePath?: string;
  packageSize?: number;
  previewLabel?: string;
  proofLabel?: string;
  proofEvent?: string;
  truthGate?: string;
}

/** From GET /api/gen3d/providers — real provider readiness data */
interface Gen3DProvider {
  provider_id: string;
  label: string;
  readiness: "available" | "installed_not_running" | "not_installed" | "unavailable";
  installed: boolean;
  pip_version: string | null;
  repo_reachable: boolean;
  weights_present: boolean;
  live_reachable: boolean | null;
  proof_source: string | null;
  proof_gate_version: string | null;
}

/** From GET /api/gen3d/templates — real local templates */
interface Gen3DTemplate {
  id: string;
  name: string;
  source: "local_executor" | "provider_backed";
  description: string;
  parameters: Array<{ name: string; type: string; default: unknown; min?: number; max?: number }>;
  outputs: string[];
  requires_provider: string | null;
  schema_file: string | null;
  schema_present?: boolean;
  requires_reference_image?: boolean;
  requires_background_removal?: boolean;
}

export function Gen3DTab() {
  const [prompt, setPrompt] = useState("calibration cube");
  const [sizeMm, setSizeMm] = useState(20);
  const [previewDag, setPreviewDag] = useState<TaskDAG | null>(null);
  const [previewState, setPreviewState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [providerHealth, setProviderHealth] = useState<ProviderHealth[]>([]);
  const [gen3dProviders, setGen3DProviders] = useState<Gen3DProvider[]>([]);
  const [gen3dTemplates, setGen3DTemplates] = useState<Gen3DTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("calibration_cube");
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [generatedModels, setGeneratedModels] = useState<GeneratedModelResult[]>([]);
  const [artifactModels, setArtifactModels] = useState<GeneratedModelResult[]>([]);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [referenceArtifactId, setReferenceArtifactId] = useState<string | null>(null);
  const [referenceMessage, setReferenceMessage] = useState<string | null>(null);
  const plannerMode = previewDag?.metadata?.planner_mode;
  const displayedModels = mergeGeneratedModels(generatedModels, artifactModels);

  // W21-MVP-5: poll provider health + Gen3D providers + Gen3D templates
  // on PANEL_POLL_MS. When the operator installs rembg / TripoSR /
  // Hunyuan3D in the background, this tab will surface readiness
  // without a reload. ``usePollingEffect`` cancels overlap + cleans up
  // on unmount; per-fetch failures are caught locally so one bad
  // endpoint never breaks the others.
  const refreshGen3DPanels = useCallback(async () => {
    await Promise.all([
      adapters
        .getProviderHealth()
        .then((data) => setProviderHealth(data))
        .catch((error) => setGenerateMessage(`Blocked: ${errorMessage(error)}`)),
      fetch(`${LIVE_BASE_URL}/api/gen3d/providers`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      })
        .then(async (res) => {
          if (!res.ok) return;
          const data: unknown = await res.json();
          if (Array.isArray(data)) {
            setGen3DProviders(data as Gen3DProvider[]);
          }
        })
        .catch(() => {
          /* backend not yet running — silently ignore */
        }),
      fetch(`${LIVE_BASE_URL}/api/gen3d/templates`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      })
        .then(async (res) => {
          if (!res.ok) return;
          const data: unknown = await res.json();
          if (Array.isArray(data)) {
            setGen3DTemplates(data as Gen3DTemplate[]);
          }
        })
        .catch(() => {
          /* backend not yet running — silently ignore */
        }),
      adapters
        .getArtifacts()
        .then((artifacts) => setArtifactModels(artifactsToGeneratedModels(artifacts)))
        .catch(() => {
          /* artifacts are best-effort reload history */
        }),
    ]);
  }, []);
  usePollingEffect(refreshGen3DPanels, PANEL_POLL_MS, [refreshGen3DPanels]);

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
    // Check if selected template requires a provider that isn't available
    const template = gen3dTemplates.find((t) => t.id === selectedTemplate);
    if (template?.requires_provider) {
      const reqProvider = gen3dProviders.find((p) => p.provider_id === template.requires_provider);
      if (!reqProvider || reqProvider.readiness !== "available") {
        const providerLabel = reqProvider?.label ?? template.requires_provider;
        setGenerateMessage(
          `Blocked: Provider not available — ${providerLabel} is ${reqProvider?.readiness ?? "not configured"}. ` +
          `Install and start ${providerLabel} to use this template.`
        );
        await adapters.emitProofEvent("generation.run.blocked", {
          reason: "provider_not_available",
          provider_id: template.requires_provider,
          readiness: reqProvider?.readiness ?? "unknown",
        });
        return;
      }
    }
    if (template?.requires_reference_image && referenceArtifactId == null) {
      setGenerateMessage("Blocked: Attach a reference image before running this template.");
      await adapters.emitProofEvent("generation.run.blocked", {
        reason: "reference_image_required",
        template_id: template.id,
      });
      return;
    }

    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/generation/run`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          template_id: selectedTemplate,
          reference_artifact_id: referenceArtifactId,
          constraints: { size_mm: sizeMm },
        }),
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
      evidence_type: "reference_image",
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
      const artifactId = parseArtifactId(payload);
      if (response.ok && artifactId) {
        setReferenceArtifactId(artifactId);
      }
      setReferenceMessage(`${response.ok ? "Attached" : "Blocked"}: ${generationSummary(payload, response.statusText)}`);
      await adapters.emitProofEvent("generation.reference.attached", { accepted: response.ok, filename: referenceFile.name, artifact_id: artifactId, response: payload });
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
                  max={180}
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
                  onChange={(event) => {
                    setReferenceFile(event.target.files?.[0] ?? null);
                    setReferenceArtifactId(null);
                  }}
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
          title="3D GENERATION PROVIDERS"
          dense
          status={{
            tone: gen3dProviders.some((p) => p.readiness === "available")
              ? "green"
              : providerHealth.some((p) => p.status === "green")
                ? "green"
                : "muted",
            label: `${gen3dProviders.filter((p) => p.readiness === "available").length} available`,
          }}
          className="h-full min-h-0"
        >
          <div className="flex flex-col gap-3">
            {/* Real Gen3D provider readiness from /api/gen3d/providers */}
            <div data-testid="gen3d-provider-readiness">
              <div className="text-muted text-[10px] uppercase tracking-wide mb-1.5 flex items-center gap-1">
                <Layers size={10} />
                Generation Provider Readiness
                <span className="ml-auto font-mono text-[9px]">(GEN3D_VERIFY proof)</span>
              </div>
              {gen3dProviders.length > 0 ? (
                <ul className="flex flex-col gap-1">
                  {gen3dProviders.map((p) => (
                    <li
                      key={p.provider_id}
                      className="flex items-center gap-2 px-1 py-0.5 text-[11px]"
                      data-testid="gen3d-readiness-row"
                      data-provider={p.provider_id}
                      data-readiness={p.readiness}
                    >
                      <span
                        className={[
                          "h-1.5 w-1.5 rounded-full shrink-0",
                          p.readiness === "available"
                            ? "bg-accent-green"
                            : p.readiness === "installed_not_running"
                              ? "bg-amber-400"
                              : p.readiness === "not_installed"
                                ? "bg-red-500"
                                : "bg-muted",
                        ].join(" ")}
                        aria-label={`${p.provider_id} readiness ${p.readiness}`}
                      />
                      <span className="text-fg font-medium truncate">{p.label}</span>
                      <span className="text-muted text-[10px] font-mono ml-auto">
                        {p.readiness === "available"
                          ? "live"
                          : p.readiness === "installed_not_running"
                            ? "installed"
                            : p.readiness === "not_installed"
                              ? "not installed"
                              : "unavailable"}
                      </span>
                      {p.readiness !== "available" && (
                        <AlertTriangle size={9} className="text-amber-400 shrink-0" aria-hidden />
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-muted text-[10px]">Loading provider readiness…</div>
              )}
            </div>
            {/* LLM provider health for context */}
            {providerHealth.length > 0 && (
              <div data-testid="gen3d-provider-health">
                <div className="text-muted text-[10px] uppercase tracking-wide mb-1">LLM Providers</div>
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
              </div>
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
              <div className="grid h-full min-h-[120px] grid-cols-1 gap-2 text-xs md:grid-cols-3">
                <div className="rounded border border-border bg-bg/40 p-3">
                  <div className="font-semibold text-fg">Plan preview not requested</div>
                  <p className="mt-1 text-muted">
                    Use Preview plan to build a live DAG from the current prompt. No staged work is being claimed as ready yet.
                  </p>
                </div>
                <div className="rounded border border-border bg-bg/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted">Current input</div>
                  <div className="mt-1 truncate font-mono text-fg">{prompt || "(empty prompt)"}</div>
                  <div className="mt-1 text-muted">Size target: {sizeMm} mm</div>
                </div>
                <div className="rounded border border-border bg-bg/40 p-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted">Selected template</div>
                  <div className="mt-1 truncate font-semibold text-fg">
                    {gen3dTemplates.find((template) => template.id === selectedTemplate)?.name ?? selectedTemplate}
                  </div>
                  <div className="mt-1 text-muted">
                    Reference image: {referenceArtifactId ? "attached" : referenceFile ? "selected, not attached" : "not attached"}
                  </div>
                </div>
              </div>
            )}
          </div>
        </Panel>
      </div>
      <div className="col-span-12 min-h-0">
        <Panel
          id="gen3d.templates"
          title="LOCAL TEMPLATE GALLERY"
          dense
          status={{
            tone: gen3dTemplates.length > 0 ? "cyan" : "muted",
            label: `${gen3dTemplates.length} templates`,
          }}
          className="h-full min-h-0"
        >
          <div data-testid="gen3d-template-gallery">
            {gen3dTemplates.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {gen3dTemplates.map((t) => {
                  const isSelected = selectedTemplate === t.id;
                  const requiresProvider = t.requires_provider != null;
                  const providerReady = !requiresProvider
                    || gen3dProviders.find((p) => p.provider_id === t.requires_provider)?.readiness === "available";
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        setSelectedTemplate(t.id);
                        // If it's a local template, pre-fill a matching prompt keyword
                        if (t.source === "local_executor" && t.id === "calibration_cube") {
                          setPrompt("calibration cube");
                          setSizeMm(20);
                        }
                        if (t.source === "local_executor" && t.id === "reference_image_relief") {
                          setPrompt("logo relief from reference image");
                          setSizeMm(60);
                        }
                        if (t.source === "local_executor" && t.id === "precision_image_relief") {
                          setPrompt("perfect 1:1 precision relief from reference image");
                          setSizeMm(180);
                        }
                        if (t.id === "hunyuan3d_image_to_3d") {
                          setPrompt("Hunyuan image to 3D from reference image");
                          setSizeMm(60);
                        }
                      }}
                      data-testid="gen3d-template-card"
                      data-template-id={t.id}
                      data-source={t.source}
                      data-requires-provider={t.requires_provider ?? "none"}
                      className={[
                        "text-left rounded border px-2.5 py-2 text-xs transition-colors",
                        isSelected
                          ? "border-accent-cyan/70 bg-accent-cyan/10"
                          : "border-border bg-surface2/30 hover:border-accent-cyan/40",
                        !providerReady ? "opacity-60" : "",
                      ].join(" ")}
                      aria-pressed={isSelected}
                      title={t.description}
                    >
                      <div className="flex items-start justify-between gap-1 mb-0.5">
                        <span className="font-semibold text-fg truncate">{t.name}</span>
                        <span
                          className={[
                            "shrink-0 rounded px-1 py-0.5 text-[9px] uppercase font-medium",
                            t.source === "local_executor"
                              ? "bg-accent-green/15 text-accent-green"
                              : providerReady
                                ? "bg-accent-cyan/15 text-accent-cyan"
                                : "bg-surface2 text-muted",
                          ].join(" ")}
                        >
                          {t.source === "local_executor" ? "local" : (providerReady ? "ready" : "needs provider")}
                        </span>
                      </div>
                      <div className="text-muted text-[10px] leading-relaxed line-clamp-2">{t.description}</div>
                      <div className="mt-1 text-[10px] text-muted font-mono">
                        out: {t.outputs.join(", ")}
                        {t.requires_provider && (
                          <span className="ml-1 text-amber-400">· requires {t.requires_provider}</span>
                        )}
                        {t.requires_reference_image && (
                          <span className="ml-1 text-amber-400">· requires image</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <EmptyState title="No templates loaded" detail="The /api/gen3d/templates endpoint is not yet reachable. Start the backend to see available templates." />
            )}
          </div>
        </Panel>
      </div>
      <div className="col-span-12 min-h-0">
        <Panel
          id="gen3d.results"
          title="GENERATED MODELS"
          dense
          status={{ tone: displayedModels.length > 0 ? "cyan" : "muted", label: `${displayedModels.length} models` }}
          className="h-full min-h-0"
        >
          {displayedModels.length > 0 ? (
            <div className="grid h-full min-h-0 gap-2 overflow-auto md:grid-cols-2 xl:grid-cols-3">
              {displayedModels.map((model) => (
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
                    {model.packageLabel && <div className="truncate">3MF: <span className="font-mono text-fg">{model.packageLabel}{model.packageSize != null ? ` · ${formatBytes(model.packageSize)}` : ""}</span></div>}
                    {model.previewLabel && <div className="truncate">Preview: <span className="font-mono text-fg">{model.previewLabel}</span></div>}
                    {model.proofLabel && <div className="truncate">Proof: <span className="font-mono text-fg">{model.proofLabel}</span></div>}
                  </div>
                  <div className="truncate font-mono text-[10px] text-accent-cyan">{model.packagePath ?? model.proofEvent ?? model.artifactPath}</div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No generated models" detail="No mesh, STL, 3MF, GLB, or OBJ artifacts were returned by the backend." />
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
    const packageLabel = isRecord(payload.package_3mf) && typeof payload.package_3mf.label === "string" ? `; 3MF ${payload.package_3mf.label}` : "";
    const proofId = isRecord(payload.proof) && typeof payload.proof.event_id === "string" ? `; proof ${payload.proof.event_id}` : "";
    return `${payload.artifact.label}${packageLabel}${proofId}`;
  }
  return String(payload.reason ?? payload.message ?? payload.status ?? payload.id ?? payload.artifact_id ?? fallback);
}

function mergeGeneratedModels(sessionModels: GeneratedModelResult[], artifactModels: GeneratedModelResult[]): GeneratedModelResult[] {
  const seen = new Set<string>();
  const merged: GeneratedModelResult[] = [];
  for (const model of [...sessionModels, ...artifactModels]) {
    const key = model.packagePath ?? model.artifactPath;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(model);
  }
  return merged.slice(0, 12);
}

function artifactsToGeneratedModels(artifacts: Artifact[]): GeneratedModelResult[] {
  return artifacts
    .filter(isGeneratedModelArtifact)
    .sort((left, right) => Date.parse(right.createdAt || "0") - Date.parse(left.createdAt || "0"))
    .slice(0, 12)
    .map((artifact) => {
      const isPackage = /\.(3mf)$/i.test(artifact.path) || /\.(3mf)$/i.test(artifact.name);
      return {
        jobId: String(artifact.jobId),
        template: artifact.stage || "artifact_history",
        artifactLabel: artifact.label ?? artifact.name,
        artifactPath: artifact.path,
        artifactSize: artifact.sizeBytes,
        packageLabel: isPackage ? artifact.label ?? artifact.name : undefined,
        packagePath: isPackage ? artifact.path : undefined,
        packageSize: isPackage ? artifact.sizeBytes : undefined,
        truthGate: artifact.gate ?? "artifact",
      };
    });
}

function isGeneratedModelArtifact(artifact: Artifact): boolean {
  const path = `${artifact.path} ${artifact.name}`.toLowerCase();
  return artifact.type === "mesh"
    || artifact.type === "model_evidence"
    || /\.(stl|3mf|glb|gltf|obj)\b/.test(path);
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
  const package3mf = isRecord(payload.package_3mf) ? payload.package_3mf : null;
  return {
    jobId: payload.job_id,
    template: typeof payload.template === "string" ? payload.template : "local_template",
    artifactLabel: artifact.label,
    artifactPath: artifact.file_path,
    artifactSize: typeof artifact.file_size === "number" ? artifact.file_size : 0,
    packageLabel: package3mf != null && typeof package3mf.label === "string" ? package3mf.label : undefined,
    packagePath: package3mf != null && typeof package3mf.file_path === "string" ? package3mf.file_path : undefined,
    packageSize: package3mf != null && typeof package3mf.file_size === "number" ? package3mf.file_size : undefined,
    previewLabel: isRecord(payload.preview) && typeof payload.preview.label === "string" ? payload.preview.label : undefined,
    proofLabel: isRecord(payload.proof) && typeof payload.proof.label === "string" ? payload.proof.label : undefined,
    proofEvent: isRecord(payload.proof) && typeof payload.proof.event_id === "string" ? payload.proof.event_id : undefined,
    truthGate: isRecord(payload.truth_gate) && typeof payload.truth_gate.status === "string" ? payload.truth_gate.status : undefined,
  };
}

function parseArtifactId(payload: unknown): string | null {
  if (!isRecord(payload)) {
    return null;
  }
  return typeof payload.id === "string" ? payload.id : null;
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
