/**
 * ArtifactList — groups Artifact entries by jobTitle and renders ArtifactRow
 * per item. Pure presentation; the Artifacts tab feeds in normalized rows
 * already fetched from `GET /api/artifacts`.
 *
 * Honest-blocked: when zero rows are received, renders an explicit empty
 * message stating the API returned nothing — no synthetic data.
 *
 * Sources consulted:
 *   - GitHub Projects "Group by" pattern:
 *     https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/grouping-issues-and-pull-requests
 *   - React grouping pattern (Map<key, items[]>):
 *     https://react.dev/reference/react/Children
 */
import { useMemo } from "react";
import type { Artifact } from "../../types/artifact";
import { ArtifactRow } from "./ArtifactRow";

interface ArtifactListProps {
  artifacts: Artifact[];
  onView: (artifact: Artifact) => void;
}

export function ArtifactList({ artifacts, onView }: ArtifactListProps) {
  const grouped = useMemo(() => groupArtifacts(artifacts), [artifacts]);

  if (artifacts.length === 0) {
    return (
      <div
        data-testid="artifact-list-empty"
        className="rounded border border-border bg-bg/40 p-3 text-sm text-muted"
      >
        No artifacts returned by the live artifacts API.
      </div>
    );
  }

  return (
    <div role="list" aria-label="Artifacts grouped by job" className="grid gap-3">
      {Array.from(grouped.entries()).map(([jobTitle, rows]) => (
        <div
          key={jobTitle}
          data-testid={`artifact-group-${jobTitle}`}
          className="rounded border border-border bg-bg/40 p-3"
        >
          <h3 className="font-medium text-fg">{jobTitle}</h3>
          {rows.map((artifact) => (
            <ArtifactRow key={artifact.id} artifact={artifact} onView={onView} />
          ))}
        </div>
      ))}
    </div>
  );
}

function groupArtifacts(artifacts: Artifact[]): Map<string, Artifact[]> {
  return artifacts.reduce((groups, artifact) => {
    groups.set(artifact.jobTitle, [...(groups.get(artifact.jobTitle) ?? []), artifact]);
    return groups;
  }, new Map<string, Artifact[]>());
}
