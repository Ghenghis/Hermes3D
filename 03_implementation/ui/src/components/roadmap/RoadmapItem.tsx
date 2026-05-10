/**
 * RoadmapItem — single legacy-roadmap row with number, description, state
 * badge, and "Open" button that hops to the linked tab via the AppShell
 * `setActiveTabId` callback.
 *
 * Pure presentation; receives a normalized RoadmapItem + onOpen callback.
 * Lifted out of `tabs/Roadmap.tsx` (Wave 15 / Agent 16) for reuse and
 * testability.
 *
 * Sources consulted:
 *   - GitHub Projects status-column rows:
 *     https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
 *   - WAI-ARIA APG "Button" pattern (for disabled-with-tooltip state):
 *     https://www.w3.org/WAI/ARIA/apg/patterns/button/
 */
import type { RoadmapItem as RoadmapItemType } from "../../types/roadmap";

export type LinkableRoadmapItem = RoadmapItemType & {
  id?: number;
  status?: string;
  linkTab?: string | null;
  link_tab?: string | null;
};

interface RoadmapItemRowProps {
  item: LinkableRoadmapItem;
  onOpen: (targetTabId: string | null, rawTarget: string | null) => void;
  resolveTarget: (target: string | null) => string | null;
}

export function RoadmapItemRow({ item, onOpen, resolveTarget }: RoadmapItemRowProps) {
  const state = item.state ?? (item.complete ? "done" : "not_started");
  const target = item.linkTab ?? item.link_tab ?? null;
  const validTarget = resolveTarget(target);

  return (
    <div
      data-testid={`roadmap-item-${item.number}`}
      className="grid grid-cols-[3rem_1fr_auto_auto] items-center gap-3 rounded border border-border bg-bg/40 p-3 text-sm"
    >
      <span className="font-mono text-muted">{item.number}</span>
      <span className="text-fg">{item.description}</span>
      <span
        className={`rounded px-2 py-1 text-xs ${
          state === "done"
            ? "bg-green-900/50 text-green-300"
            : state === "in_progress"
              ? "bg-amber-900/50 text-amber-200"
              : "bg-surface2 text-muted"
        }`}
      >
        {state.replaceAll("_", " ").toUpperCase()}
      </span>
      <button
        type="button"
        disabled={!validTarget}
        title={validTarget ? `Open ${validTarget}` : "Roadmap API did not return a valid target tab."}
        onClick={() => onOpen(validTarget, target)}
        data-testid={`roadmap-open-${item.number}`}
        className="rounded border border-border px-2 py-1 text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
      >
        Open
      </button>
    </div>
  );
}
