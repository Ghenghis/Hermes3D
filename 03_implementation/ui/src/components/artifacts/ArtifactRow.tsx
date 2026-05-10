/**
 * ArtifactRow — single-row display for an artifact entry in the Artifacts tab.
 *
 * Pure presentation; receives an Artifact + onView callback. Used by
 * ArtifactList. Lifted out of `tabs/Artifacts.tsx` (Wave 15 / Agent 16)
 * for reuse and testability.
 *
 * Sources consulted:
 *   - GitHub Projects "Item row" conventions:
 *     https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
 *   - WAI-ARIA APG "listitem" semantics:
 *     https://www.w3.org/WAI/ARIA/apg/patterns/listbox/
 */
import type { Artifact } from "../../types/artifact";

interface ArtifactRowProps {
  artifact: Artifact;
  onView: (artifact: Artifact) => void;
}

export function ArtifactRow({ artifact, onView }: ArtifactRowProps) {
  return (
    <div
      key={artifact.id}
      data-testid={`artifact-row-${artifact.id}`}
      role="listitem"
      className="mt-2 grid grid-cols-[auto_1fr_auto] items-center gap-2 text-sm"
    >
      <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{artifact.type}</span>
      <span className="min-w-0">
        <span className="block truncate text-fg">{artifact.name}</span>
        <span className="block truncate text-xs text-muted">
          {artifact.path} · {(artifact.sizeBytes / 1024).toFixed(1)} KB
        </span>
      </span>
      <button
        type="button"
        onClick={() => onView(artifact)}
        data-testid={`artifact-view-${artifact.id}`}
        className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2"
      >
        View
      </button>
    </div>
  );
}
