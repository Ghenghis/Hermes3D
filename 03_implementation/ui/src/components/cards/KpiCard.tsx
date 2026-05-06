import type { ReactNode } from "react";

/**
 * KPI tile per visual contract: large number + label + optional delta + optional sparkline slot.
 * Used in the Dashboard top row.
 */
export type KpiCardProps = {
  label: string;
  value: string | number;
  delta?: { value: string; tone: "green" | "amber" | "red" | "muted" };
  /** Optional right-aligned chart child (Sparkline, etc.). */
  chart?: ReactNode;
  /** Optional left-aligned icon. */
  icon?: ReactNode;
};

const DELTA_TONE = {
  green: "text-accent-green",
  amber: "text-accent-amber",
  red: "text-accent-red",
  muted: "text-muted",
} as const;

export function KpiCard({ label, value, delta, chart, icon }: KpiCardProps) {
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 flex h-full items-center gap-2 min-w-0">
      {icon && <div className="text-accent-cyan shrink-0 opacity-80">{icon}</div>}
      <div className="flex-1 min-w-0">
        <div className="text-muted text-[10px] uppercase tracking-wider truncate">{label}</div>
        <div className="text-fg text-[21px] font-bold leading-none mt-0.5 tabular-nums">{value}</div>
        {delta && (
          <div className={["text-[10px] mt-1 truncate", DELTA_TONE[delta.tone]].join(" ")}>
            {delta.value}
          </div>
        )}
      </div>
      {chart && <div className="shrink-0 h-9 w-20">{chart}</div>}
    </div>
  );
}
