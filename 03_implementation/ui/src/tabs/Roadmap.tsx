import { useEffect, useState } from "react";
import { adapters } from "../api/adapters";
import { TABS } from "../app/routes";
import { useStore } from "../app/store";
import { RoadmapBoard } from "../components/roadmap/RoadmapBoard";
import type { LinkableRoadmapItem } from "../components/roadmap/RoadmapItem";
import type { RoadmapItem, RoadmapTabCompletion } from "../types/roadmap";
import type { SourceModuleRuntimeSetupQueue } from "../types/source-os";

type RoadmapRow = LinkableRoadmapItem;

export function RoadmapTab() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [items, setItems] = useState<RoadmapItem[]>([]);
  const [completion, setCompletion] = useState<RoadmapTabCompletion | null>(null);
  const [setupQueue, setSetupQueue] = useState<SourceModuleRuntimeSetupQueue | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      adapters.getRoadmapItems(),
      adapters.getRoadmapTabCompletion(),
      adapters.getModuleRuntimeSetupQueue().catch(() => null),
    ]).then(async ([next, nextCompletion, nextSetupQueue]) => {
      const normalized = next.map(normalizeRoadmapItem);
      setItems(normalized);
      setCompletion(nextCompletion);
      setSetupQueue(nextSetupQueue);
      await adapters.emitProofEvent("roadmap.viewed", {
        done_count: normalized.filter((item) => (item.state ?? (item.complete ? "done" : "not_started")) === "done").length,
        in_progress_count: normalized.filter((item) => item.state === "in_progress").length,
        not_started_count: normalized.filter((item) => item.state === "not_started").length,
        tab_ledger_count: nextCompletion.tabs.length,
        work_package_count: nextCompletion.next_packages.length,
        source_apps: nextSetupQueue?.count ?? null,
        runtime_ready_apps: nextSetupQueue?.counts.runtime_ready ?? null,
        runner_gap_apps: nextSetupQueue?.counts.runner_not_registered ?? null,
      });
    });
  }, []);

  return (
    <div data-testid="roadmap-root" className="grid gap-3 text-xs">
      <section className="rounded border border-border bg-surface p-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-fg">Roadmap</h2>
            <p className="text-xs text-muted">Daily-use completion path</p>
          </div>
          {completion && (
            <div className="rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-muted">
              {completion.roadmap_path} · {completion.updated_at}
            </div>
          )}
        </div>
        {completion && (
          <div className="mt-3 grid gap-1 sm:grid-cols-2 xl:grid-cols-4">
            {completion.contract.map((rule) => (
              <div key={rule} className="rounded border border-border bg-bg/40 px-2 py-1.5 text-[11px] text-muted">{rule}</div>
            ))}
          </div>
        )}
      </section>

      {setupQueue && (
        <section className="rounded border border-border bg-surface p-3" data-testid="roadmap-source-runtime-gap">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-fg">Source App Runtime Gap</h3>
              <p className="mt-1 text-[11px] leading-4 text-muted">
                Current local registry proves {setupQueue.count} source-backed modules. The corrected target is these 60 apps: keep every row source-backed, then register safe setup runners and smoke gates before calling it runtime ready.
              </p>
            </div>
            <StateBadge state={setupQueue.counts.runner_not_registered > 0 ? "in_progress" : "done"} />
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            <RuntimeMetric label="Proven apps" value={setupQueue.count} />
            <RuntimeMetric label="Runtime ready" value={setupQueue.counts.runtime_ready} />
            <RuntimeMetric label="Need runners" value={setupQueue.counts.runner_not_registered} alert={setupQueue.counts.runner_not_registered > 0} />
            <RuntimeMetric label="Install ready" value={setupQueue.counts.source_install_available} alert={setupQueue.counts.source_install_available > 0} />
            <RuntimeMetric label="Blocked" value={setupQueue.counts.blocked} alert={setupQueue.counts.blocked > 0} />
          </div>
          <p className="mt-2 text-[11px] leading-4 text-muted">{setupQueue.agent_gate}</p>
        </section>
      )}

      {completion?.source_runtime_action_plan && (
        <section className="rounded border border-cyan-900/50 bg-surface p-3" data-testid="roadmap-source-action-plan">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-fg">Source OS Action Plan</h3>
              <p className="mt-1 text-[11px] leading-4 text-muted">{completion.source_runtime_action_plan.rule}</p>
            </div>
            <span className={`rounded px-2 py-1 text-[10px] uppercase ${completion.source_runtime_action_plan.exists ? "bg-cyan-950/70 text-cyan-200" : "bg-amber-950/70 text-amber-200"}`}>
              {completion.source_runtime_action_plan.exists ? "tracked" : "missing"}
            </span>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            <RuntimeMetric label="60-app target" value={completion.source_runtime_action_plan.source_backed_apps} />
            <RuntimeMetric label="Runtime ready" value={completion.source_runtime_action_plan.runtime_ready} />
            <RuntimeMetric label="Need runners" value={completion.source_runtime_action_plan.runner_gaps} alert={completion.source_runtime_action_plan.runner_gaps > 0} />
            <RuntimeMetric label="Agent CLIs" value={completion.source_runtime_action_plan.verified_agent_cli} />
            <RuntimeMetric label="CLI signals" value={completion.source_runtime_action_plan.cli_candidates} alert={completion.source_runtime_action_plan.cli_candidates > 0} />
          </div>
          <div className="mt-2 rounded border border-border bg-bg/40 px-2 py-1 font-mono text-[10px] text-muted">
            {completion.source_runtime_action_plan.path}
            {completion.source_runtime_action_plan.generated_at_utc ? ` · ${completion.source_runtime_action_plan.generated_at_utc}` : ""}
          </div>
        </section>
      )}

      {completion?.agent_operator_contract && (
        <section className="rounded border border-accent-amber/40 bg-surface p-3" data-testid="roadmap-agent-operator-contract">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-fg">Hermes Agent Full OS Coverage</h3>
              <p className="mt-1 text-[11px] leading-4 text-muted">{completion.agent_operator_contract.summary}</p>
            </div>
            <StateBadge state={completion.agent_operator_contract.state} />
          </div>
          <div className="mt-3 grid gap-2 lg:grid-cols-3">
            <ContractList title="Ready now" rows={completion.agent_operator_contract.ready_now} />
            <ContractList title="Missing coverage" rows={completion.agent_operator_contract.missing} alert />
            <ContractList title="Blocked now" rows={completion.agent_operator_contract.blocked_now} alert />
          </div>
        </section>
      )}

      {completion && (
        <section className="rounded border border-border bg-surface p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-fg">Tab Completion Ledger</h3>
            <span className="rounded bg-surface2 px-2 py-1 text-[10px] uppercase text-muted">{completion.tabs.length} surfaces</span>
          </div>
          <div className="mt-3 grid gap-2 lg:grid-cols-2 2xl:grid-cols-3">
            {completion.tabs.map((tab) => {
              const validTarget = safeTabId(tab.tab);
              return (
                <button
                  key={tab.tab}
                  type="button"
                  disabled={!validTarget}
                  onClick={() => validTarget && setActiveTabId(validTarget)}
                  className="grid min-h-20 grid-cols-[1fr_auto] gap-2 rounded border border-border bg-bg/40 p-2 text-left disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <span>
                    <span className="block text-xs font-semibold text-fg">{tab.label}</span>
                    <span className="mt-1 block text-[11px] leading-4 text-muted">{tab.summary}</span>
                  </span>
                  <StateBadge state={tab.state} />
                </button>
              );
            })}
          </div>
        </section>
      )}

      {completion && (
        <section className="rounded border border-border bg-surface p-3">
          <h3 className="text-sm font-semibold text-fg">Next 5 Work Packages</h3>
          <div className="mt-3 grid gap-2 xl:grid-cols-2">
            {completion.next_packages.map((pkg) => (
              <div key={pkg.id} className="rounded border border-border bg-bg/40 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold text-fg">{pkg.title}</h4>
                  <span className="rounded bg-cyan-950/60 px-2 py-1 text-[10px] uppercase text-cyan-200">{pkg.state}</span>
                </div>
                <p className="mt-2 text-[11px] leading-4 text-muted">{pkg.summary}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {pkg.tabs.map((tab) => (
                    <button
                      key={`${pkg.id}-${tab}`}
                      type="button"
                      onClick={() => {
                        const validTarget = safeTabId(tab);
                        if (validTarget) setActiveTabId(validTarget);
                      }}
                      className="rounded border border-border px-2 py-1 text-[10px] text-fg"
                    >
                      {tab.replaceAll("_", " ")}
                    </button>
                  ))}
                </div>
                <div className="mt-3 grid gap-1">
                  {pkg.acceptance.map((item) => (
                    <div key={item} className="text-[11px] leading-4 text-muted">- {item}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="rounded border border-border bg-surface p-3">
        <h3 className="text-sm font-semibold text-fg">Legacy Roadmap Rows</h3>
        <RoadmapBoard
          items={items as RoadmapRow[]}
          resolveTarget={safeTabId}
          onOpen={(validTarget, rawTarget) => {
            if (!validTarget) {
              setMessage(`Blocked: roadmap target ${rawTarget ?? "(none)"} is not a registered Hermes3D tab.`);
              return;
            }
            setMessage(null);
            setActiveTabId(validTarget);
          }}
          footer={
            message ? (
              <div className="rounded border border-border bg-bg/40 p-2 text-xs text-muted">{message}</div>
            ) : null
          }
        />
      </section>
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const tone =
    state === "done"
      ? "bg-green-950/70 text-green-300"
      : state === "in_progress"
        ? "bg-amber-950/70 text-amber-200"
        : "bg-surface2 text-muted";
  return <span className={`h-fit rounded px-2 py-1 text-[10px] uppercase ${tone}`}>{state.replaceAll("_", " ")}</span>;
}

function RuntimeMetric({ label, value, alert = false }: { label: string; value: number; alert?: boolean }) {
  return (
    <div className={`rounded border px-2 py-1.5 ${alert ? "border-accent-amber/40 bg-accent-amber/10" : "border-border bg-bg/40"}`}>
      <div className="text-[10px] uppercase text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-semibold text-fg">{value}</div>
    </div>
  );
}

function ContractList({ title, rows, alert = false }: { title: string; rows: string[]; alert?: boolean }) {
  return (
    <div className={`rounded border p-2 ${alert ? "border-accent-amber/30 bg-accent-amber/10" : "border-border bg-bg/40"}`}>
      <div className="text-[10px] uppercase text-muted">{title}</div>
      <div className="mt-1 grid max-h-36 gap-1 overflow-auto">
        {rows.slice(0, 8).map((row) => (
          <div key={row} className="text-[11px] leading-4 text-fg">{row}</div>
        ))}
        {rows.length === 0 && <div className="text-[11px] text-muted">No rows returned.</div>}
      </div>
    </div>
  );
}

function safeTabId(target: string | null): string | null {
  const normalized = target === "source-os" ? "source_os" : target === "simple" || target === "simple_mode" ? "dashboard" : target;
  return normalized && TABS.some((tab) => tab.id === normalized) ? normalized : null;
}

function normalizeRoadmapItem(item: RoadmapItem): RoadmapItem {
  const row = item as RoadmapRow;
  const rawState = row.state ?? row.status?.toLowerCase();
  const state = rawState === "done" || rawState === "in_progress" ? rawState : "not_started";
  return {
    ...item,
    number: item.number ?? row.id ?? 0,
    complete: item.complete ?? state === "done",
    state,
  };
}
