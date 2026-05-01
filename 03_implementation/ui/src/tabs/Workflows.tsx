/**
 * Workflows tab — Phase 2 mock-only per TAB_SPECS.md §3.
 *
 * Active workflows · visual pipeline · failed steps with repair (locked) ·
 * workflow templates (standard 7-stage + Dimensional Truth Engine 12-stage).
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { WorkflowPipeline } from "../components/pipeline/WorkflowPipeline";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import {
  MOCK_WORKFLOWS,
  STANDARD_PIPELINE_TEMPLATE,
  DIMENSIONAL_TRUTH_PIPELINE_TEMPLATE,
} from "../data/mock/workflows";
import { MOCK_JOBS } from "../data/mock/jobs";
import type { Workflow } from "../types/workflow";

const STATUS_TONE: Record<Workflow["status"], StatusTone> = {
  active: "cyan",
  completed: "green",
  failed: "red",
  queued: "muted",
};

export function WorkflowsTab() {
  const [selectedId, setSelectedId] = useState(MOCK_WORKFLOWS[0].id);
  const selected = MOCK_WORKFLOWS.find((w) => w.id === selectedId) ?? MOCK_WORKFLOWS[0];
  const failedJobs = MOCK_JOBS.filter((j) => j.status === "failed");

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="workflows-root">
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="workflows.list"
          title="ACTIVE WORKFLOWS"
          dense
          status={{ tone: "cyan", label: `${MOCK_WORKFLOWS.length} total` }}
          className="h-[300px]"
        >
          <ul className="flex flex-col gap-1 h-full overflow-auto">
            {MOCK_WORKFLOWS.map((w) => (
              <li key={w.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(w.id)}
                  className={[
                    "w-full flex flex-col gap-1 px-2 py-1.5 rounded border text-left text-xs",
                    w.id === selectedId
                      ? "bg-surface2 border-accent-cyan/40"
                      : "bg-surface2/30 border-border hover:border-accent-cyan/20",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-fg font-medium truncate">{w.name}</span>
                    <StatusBadge tone={STATUS_TONE[w.status]} label={w.status} />
                  </div>
                  <div className="h-1 bg-surface rounded-full overflow-hidden">
                    <div
                      className={[
                        "h-full rounded-full",
                        w.status === "active"
                          ? "bg-accent-cyan"
                          : w.status === "completed"
                            ? "bg-accent-green"
                            : w.status === "failed"
                              ? "bg-accent-red"
                              : "bg-muted",
                      ].join(" ")}
                      style={{ width: `${w.progress}%` }}
                    />
                  </div>
                  <div className="text-muted text-[10px] font-mono">
                    {w.progress}% · stage {w.active_stage + 1}/{w.stages.length}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="workflows.pipeline"
          title={`PIPELINE · ${selected.name}`}
          dense
          status={{ tone: STATUS_TONE[selected.status], label: selected.status }}
          className="h-[300px]"
        >
          <div className="flex flex-col gap-3 h-full">
            <WorkflowPipeline stages={selected.stages} />
            <div className="grid grid-cols-3 gap-2 text-xs border-t border-border pt-2">
              <KV k="Started" v={<span className="font-mono text-[11px]">{selected.started_utc}</span>} />
              <KV k="Active Stage" v={`${selected.active_stage + 1} / ${selected.stages.length}`} />
              <KV k="Progress" v={`${selected.progress}%`} />
            </div>
            <div className="flex flex-wrap gap-1.5">
              <LockedAction label="Retry stage" />
              <LockedAction label="Pause workflow" />
              <LockedAction label="Cancel" />
              <LockedAction label="Request proof" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-7">
        <Panel
          id="workflows.failed"
          title="FAILED STEPS"
          dense
          status={{ tone: failedJobs.length > 0 ? "red" : "green", label: `${failedJobs.length} failures` }}
          className="h-[220px]"
        >
          {failedJobs.length === 0 ? (
            <div className="text-muted text-xs text-center py-6">No failed steps. ✓</div>
          ) : (
            <ul className="flex flex-col gap-1.5 h-full overflow-auto text-xs">
              {failedJobs.map((j) => (
                <li
                  key={j.id}
                  className="flex items-center gap-2 px-2 py-1.5 rounded bg-accent-red/5 border border-accent-red/30"
                >
                  <span className="h-2 w-2 rounded-full bg-accent-red shrink-0" aria-hidden />
                  <span className="text-fg font-mono truncate flex-1">{j.name}</span>
                  <span className="text-muted text-[10px] truncate shrink-0">layer {j.progress}%</span>
                  <LockedAction label="Repair" />
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-5">
        <Panel
          id="workflows.templates"
          title="WORKFLOW TEMPLATES"
          dense
          status={{ tone: "muted", label: "2 available" }}
          className="h-[220px]"
        >
          <div className="grid grid-cols-1 gap-2 h-full overflow-auto">
            <TemplateCard
              name="Standard 7-stage"
              stages={STANDARD_PIPELINE_TEMPLATE.map((s) => s.label)}
              tone="cyan"
            />
            <TemplateCard
              name="Dimensional Truth Engine 12-stage"
              stages={DIMENSIONAL_TRUTH_PIPELINE_TEMPLATE.map((s) => s.label)}
              tone="amber"
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function TemplateCard({ name, stages, tone }: { name: string; stages: string[]; tone: "cyan" | "amber" }) {
  const ringClass = tone === "cyan" ? "border-accent-cyan/30" : "border-accent-amber/30";
  return (
    <div className={`px-2 py-1.5 rounded border ${ringClass} bg-surface2/40 text-xs`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-fg font-medium truncate">{name}</span>
        <span className="text-muted text-[10px] font-mono shrink-0">{stages.length} stages</span>
      </div>
      <div className="text-muted text-[10px] font-mono truncate">{stages.join(" → ")}</div>
    </div>
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
