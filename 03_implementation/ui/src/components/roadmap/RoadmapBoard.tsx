/**
 * RoadmapBoard — legacy roadmap rows list. Falls back to an honest empty
 * state when `GET /api/roadmap` returns 0 items.
 *
 * Pure presentation; receives a list of normalized RoadmapItem rows + the
 * AppShell route resolver. Lifted out of `tabs/Roadmap.tsx` (Wave 15 /
 * Agent 16) for reuse and testability.
 *
 * Sources consulted:
 *   - GitHub Projects Backlog board:
 *     https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
 *   - Linear-style roadmap row list:
 *     https://linear.app/docs (general convention)
 */
import type { ReactNode } from "react";
import { RoadmapItemRow, type LinkableRoadmapItem } from "./RoadmapItem";

interface RoadmapBoardProps {
  items: LinkableRoadmapItem[];
  onOpen: (targetTabId: string | null, rawTarget: string | null) => void;
  resolveTarget: (target: string | null) => string | null;
  footer?: ReactNode;
}

export function RoadmapBoard({ items, onOpen, resolveTarget, footer }: RoadmapBoardProps) {
  return (
    <div className="mt-3 grid gap-2">
      {items.map((item) => (
        <RoadmapItemRow
          key={item.number}
          item={item}
          onOpen={onOpen}
          resolveTarget={resolveTarget}
        />
      ))}
      {footer}
      {items.length === 0 && (
        <div
          data-testid="roadmap-items-empty"
          className="rounded border border-border bg-bg/40 p-3 text-sm text-muted"
        >
          No roadmap items returned by the live roadmap API.
        </div>
      )}
    </div>
  );
}
