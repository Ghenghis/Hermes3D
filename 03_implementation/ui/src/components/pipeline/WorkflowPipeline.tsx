import { Check, CircleDot, X } from "lucide-react";
import { Fragment } from "react";

export type PipelineStageStatus = "done" | "active" | "pending" | "failed";

export type PipelineStage = {
  id: string;
  label: string;
  status: PipelineStageStatus;
  /** Optional sub-label (e.g. "98.2%"). */
  detail?: string;
};

/**
 * Horizontal pipeline visualization per visual contract: connected nodes
 * with status icons + connector lines tinted by completion state.
 *
 * Used by Dashboard (Task 21+) and Workflows (Task 28). The Dimensional
 * Truth Engine 12-stage pipeline (Task 28b) reuses this component with a
 * longer stage list.
 */
export function WorkflowPipeline({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex items-center gap-0 w-full overflow-x-auto py-2">
      {stages.map((stage, i) => (
        <Fragment key={stage.id}>
          <PipelineNode stage={stage} />
          {i < stages.length - 1 && (
            <div
              className={[
                "h-px flex-1 min-w-[24px]",
                stage.status === "done"
                  ? "bg-accent-green/60"
                  : stage.status === "active"
                    ? "bg-accent-cyan/60"
                    : "bg-border",
              ].join(" ")}
              aria-hidden
            />
          )}
        </Fragment>
      ))}
    </div>
  );
}

function PipelineNode({ stage }: { stage: PipelineStage }) {
  const { Icon, ring, text } = STATUS_VISUAL[stage.status];
  return (
    <div className="flex flex-col items-center gap-1 px-2 shrink-0">
      <div
        className={[
          "h-8 w-8 rounded-full bg-surface flex items-center justify-center ring-1",
          ring,
          text,
        ].join(" ")}
      >
        <Icon size={14} />
      </div>
      <div className="text-fg text-[11px] font-medium leading-tight max-w-[80px] text-center truncate">
        {stage.label}
      </div>
      {stage.detail && (
        <div className="text-muted text-[10px] leading-tight">{stage.detail}</div>
      )}
    </div>
  );
}

const STATUS_VISUAL: Record<
  PipelineStageStatus,
  { Icon: typeof Check; ring: string; text: string }
> = {
  done: { Icon: Check, ring: "ring-accent-green/60", text: "text-accent-green" },
  active: { Icon: CircleDot, ring: "ring-accent-cyan/80", text: "text-accent-cyan" },
  pending: { Icon: CircleDot, ring: "ring-border", text: "text-muted" },
  failed: { Icon: X, ring: "ring-accent-red/60", text: "text-accent-red" },
};
