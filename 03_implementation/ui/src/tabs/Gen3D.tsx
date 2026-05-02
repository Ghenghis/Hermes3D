/**
 * 3D Generation tab — Phase 2 mock-only per TAB_SPECS.md §4.
 *
 * Prompt + reference image · provider selector · generated model cards ·
 * "Send to Blender MCP" (locked).
 */
import { Panel } from "../components/layout/Panel";
import { LockedAction } from "../components/badges/LockedAction";
import { StatusBadge } from "../components/badges/StatusBadge";
import { WorkflowPipeline, type PipelineStage } from "../components/pipeline/WorkflowPipeline";
import { adapters } from "../api/adapters";
import type { TaskDAG } from "../types/dag";
import { GitBranch, Image as ImageIcon } from "lucide-react";
import { useState } from "react";

const PROVIDERS = [
  { id: "minimax_vision", name: "MiniMax Vision", status: "ready", note: "vision-conditioned 3D" },
  { id: "trellis", name: "TRELLIS", status: "ready", note: "Microsoft Research" },
  { id: "hunyuan3d", name: "Hunyuan3D", status: "ready", note: "Tencent" },
  { id: "tripo_sr", name: "TripoSR", status: "ready", note: "single-image-to-3D" },
  { id: "custom", name: "Custom Provider", status: "idle", note: "configure under Settings" },
];

const GENERATED = [
  { id: "gen-001", name: "frame-bracket-v3", provider: "TRELLIS", duration_s: 42, vertices: 18420 },
  { id: "gen-002", name: "spindle-housing", provider: "Hunyuan3D", duration_s: 71, vertices: 22115 },
  { id: "gen-003", name: "tolerance-fit-A", provider: "TRELLIS", duration_s: 38, vertices: 9801 },
  { id: "gen-004", name: "calibration-cube", provider: "TripoSR", duration_s: 18, vertices: 1248 },
];

export function Gen3DTab() {
  const [prompt, setPrompt] = useState("calibration cube");
  const [previewDag, setPreviewDag] = useState<TaskDAG | null>(null);
  const [previewState, setPreviewState] = useState<"idle" | "loading" | "ready" | "error">("idle");

  const previewPlan = async () => {
    setPreviewState("loading");
    try {
      const dag = await adapters.planPreview(prompt);
      setPreviewDag(dag);
      setPreviewState("ready");
    } catch {
      setPreviewDag(null);
      setPreviewState("error");
    }
  };

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="gen3d-root">
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="gen3d.input"
          title="PROMPT + REFERENCE"
          dense
          status={{ tone: "muted", label: "input" }}
          className="h-[260px]"
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
                <LockedAction label="Generate" hint="locked · Phase 4 wires real providers" />
              </div>
            </div>
            <div className="col-span-1 flex flex-col gap-2 min-w-0">
              <div className="text-muted text-[10px] uppercase tracking-wide">Reference Image</div>
              <div className="flex-1 bg-gradient-to-br from-surface2 to-bg border border-dashed border-border rounded flex flex-col items-center justify-center gap-1 text-muted text-[10px]">
                <ImageIcon size={20} className="text-muted/60" />
                drop image here
                <span className="text-[9px]">(visual placeholder)</span>
              </div>
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="gen3d.providers"
          title="PROVIDERS"
          dense
          status={{ tone: "green", label: `${PROVIDERS.filter((p) => p.status === "ready").length} ready` }}
          className="h-[260px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto text-xs">
            {PROVIDERS.map((p, i) => (
              <li
                key={p.id}
                className={[
                  "flex items-center gap-2 px-2 py-1.5 rounded border",
                  i === 0 ? "bg-surface2 border-accent-cyan/40" : "bg-surface2/30 border-border",
                ].join(" ")}
              >
                <span
                  className={[
                    "h-1.5 w-1.5 rounded-full shrink-0",
                    p.status === "ready" ? "bg-accent-green" : "bg-muted",
                  ].join(" ")}
                  aria-hidden
                />
                <div className="flex-1 min-w-0 leading-tight">
                  <div className="text-fg font-medium truncate">{p.name}</div>
                  <div className="text-muted text-[10px] truncate">{p.note}</div>
                </div>
                {i === 0 && <span className="text-accent-cyan text-[10px] uppercase shrink-0">active</span>}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12">
        <Panel
          id="gen3d.plan"
          title="PLAN PREVIEW"
          dense
          status={{ tone: previewState === "ready" ? "cyan" : "muted", label: previewState }}
          className="h-[170px]"
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
      <div className="col-span-12">
        <Panel
          id="gen3d.results"
          title="GENERATED MODELS"
          dense
          status={{ tone: "cyan", label: `${GENERATED.length} models` }}
          className="h-[300px]"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 h-full overflow-auto">
            {GENERATED.map((g) => (
              <ModelCard key={g.id} g={g} />
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function dagToStages(dag: TaskDAG): PipelineStage[] {
  return dag.nodes.map((node, index) => ({
    id: node.node_id,
    label: node.kind.split(".").at(-1)?.replaceAll("_", " ") ?? node.tool,
    status: index === 0 ? "active" : "pending",
    detail: node.tool,
  }));
}

function ModelCard({
  g,
}: {
  g: { id: string; name: string; provider: string; duration_s: number; vertices: number };
}) {
  return (
    <div className="bg-surface2/40 border border-border rounded-lg flex flex-col overflow-hidden">
      <div className="flex-1 bg-gradient-to-br from-surface2 to-bg flex items-center justify-center relative min-h-[120px]">
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full max-h-[110px] text-accent-cyan drop-shadow-[0_0_4px_rgba(34,211,238,0.4)]"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.5"
          strokeLinejoin="round"
        >
          <polygon points="25,30 75,30 75,80 25,80" />
          <polygon points="25,30 50,15 100,15 75,30" />
          <polygon points="75,30 100,15 100,65 75,80" />
          <line x1="25" y1="30" x2="50" y2="15" />
          <line x1="50" y1="15" x2="50" y2="65" stroke="currentColor" strokeOpacity="0.3" />
          <line x1="50" y1="65" x2="25" y2="80" stroke="currentColor" strokeOpacity="0.3" />
          <line x1="50" y1="65" x2="100" y2="65" stroke="currentColor" strokeOpacity="0.3" />
        </svg>
      </div>
      <div className="px-2 py-1.5 border-t border-border text-xs flex flex-col gap-1">
        <div className="text-fg font-medium truncate">{g.name}</div>
        <div className="flex items-center gap-2">
          <StatusBadge tone="cyan" label={g.provider} />
          <span className="text-muted text-[10px] font-mono">{g.duration_s}s</span>
          <span className="text-muted text-[10px] font-mono">{g.vertices.toLocaleString()} v</span>
        </div>
        <LockedAction label="Send to Blender MCP" />
      </div>
    </div>
  );
}
