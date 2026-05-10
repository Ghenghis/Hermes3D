/**
 * CategoryCoverageBar — small horizontal bar surfacing per-category
 * proof / install coverage for the 60-app coverage matrix.
 *
 * Honest contract: a category is "covered" only when an app has BOTH
 * `proof_command` AND `last_proof_status === "passed"|"pass"`. Apps
 * missing either field are counted as unknown — NEVER as ready.
 *
 * Sources consulted:
 *   - React Grid Layout sizing pattern
 *     <https://github.com/react-grid-layout/react-grid-layout> — used the
 *     normalized 0..1 ratio convention from their `cols` math.
 *   - VS Code Marketplace coverage indicator
 *     <https://marketplace.visualstudio.com/> — green / amber / muted
 *     tri-tone bar idiom for extension/feature coverage.
 *
 * Owner: claude-w15-a13-source-os.
 * Scope: NEW file, no replacements of existing AppRegistry components.
 */

interface CategoryCoverageBarProps {
  /** Display label, e.g. "Slicers". */
  label: string;
  /** Total apps in the category. */
  total: number;
  /** Apps with proof_command AND last_proof_status === passed/pass. */
  passed: number;
  /** Apps with proof_command but the last proof failed. */
  failed: number;
  /** Apps with NO proof_command on record. Honest "unknown". */
  unknown: number;
  /** Optional click handler to filter the matrix by this category. */
  onSelect?: () => void;
  /** Whether this category is currently active (highlighted). */
  active?: boolean;
}

export function CategoryCoverageBar({
  label,
  total,
  passed,
  failed,
  unknown,
  onSelect,
  active = false,
}: CategoryCoverageBarProps) {
  // Defensive clamp — never let the segments overrun 100%.
  const safeTotal = Math.max(total, passed + failed + unknown, 1);
  const passedPct = (passed / safeTotal) * 100;
  const failedPct = (failed / safeTotal) * 100;
  const unknownPct = (unknown / safeTotal) * 100;

  const Wrapper = onSelect ? "button" : "div";
  const wrapperProps = onSelect
    ? {
        type: "button" as const,
        onClick: onSelect,
        "aria-pressed": active,
      }
    : {};

  return (
    <Wrapper
      {...wrapperProps}
      data-testid={`category-coverage-${label.toLowerCase().replace(/\s+/g, "-")}`}
      className={[
        "flex w-full flex-col gap-1 rounded border px-2 py-1.5 text-left transition-colors",
        active
          ? "border-accent-blue bg-accent-blue/10"
          : "border-border bg-surface/40 hover:border-accent-blue/40",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[11px] font-semibold text-fg">{label}</span>
        <span className="shrink-0 font-mono text-[10px] text-muted">
          {passed}/{total}
        </span>
      </div>
      <div
        className="relative h-1.5 w-full overflow-hidden rounded bg-surface2"
        role="meter"
        aria-valuenow={passed}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={`${label} coverage: ${passed} of ${total} apps proof-passed`}
      >
        {passedPct > 0 && (
          <span
            className="absolute inset-y-0 left-0 bg-green-500"
            style={{ width: `${passedPct}%` }}
            aria-hidden
          />
        )}
        {failedPct > 0 && (
          <span
            className="absolute inset-y-0 bg-rose-500"
            style={{ left: `${passedPct}%`, width: `${failedPct}%` }}
            aria-hidden
          />
        )}
        {unknownPct > 0 && (
          <span
            className="absolute inset-y-0 bg-amber-700/70"
            style={{ left: `${passedPct + failedPct}%`, width: `${unknownPct}%` }}
            aria-hidden
          />
        )}
      </div>
    </Wrapper>
  );
}
