import { Lock } from "lucide-react";

/**
 * Shared "locked until adapter phase" pill used everywhere a Phase-6
 * dangerous action would otherwise live (printer commands, slicer launch,
 * artifact download, etc.). Visual-only — no onClick wiring; the pill
 * communicates intent without granting capability.
 */
export function LockedAction({
  label,
  hint = "locked · adapter phase",
}: {
  label: string;
  /** Tooltip-style sub-text. Defaults to "locked · adapter phase". */
  hint?: string;
}) {
  return (
    <button
      type="button"
      disabled
      aria-disabled="true"
      title={hint}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface2/60 border border-border text-muted text-[11px] cursor-not-allowed opacity-80 hover:opacity-100"
    >
      <Lock size={11} />
      <span className="truncate">{label}</span>
    </button>
  );
}
