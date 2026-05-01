import { CircleDot, Cpu, ShieldCheck } from "lucide-react";
import { EditionBadge } from "../badges/EditionBadge";
import { ProofChip } from "../badges/ProofChip";

/**
 * Top header per visual contract: thin bar with branding (delegated to Sidebar
 * column), centered title 'AI-DRIVEN 3D PRINTING OS', right-side cluster
 * showing System Status, GPU Detected (100%), Security badge, and a proof
 * status chip.
 *
 * Hardcoded mock snapshot in Phase 2; refactor to consume `data/mock/system.ts`
 * when that lands (Task 18).
 */
export function TopBar({ activeLabel }: { activeLabel: string }) {
  return (
    <header className="h-14 flex items-center justify-between border-b border-border bg-surface px-6 shrink-0">
      <div className="flex items-baseline gap-3 min-w-0">
        <span className="text-fg font-semibold text-base truncate">
          AI-DRIVEN 3D PRINTING OS
        </span>
        <span className="text-muted text-xs truncate">
          Design · Verify · Slice · Print · Monitor
        </span>
        <span className="text-muted text-xs">·</span>
        <span className="text-muted text-xs truncate">{activeLabel}</span>
      </div>
      <div className="flex items-center gap-4">
        <EditionBadge edition="desktop_gpu_worker" />
        <StatusPill icon={<CircleDot size={14} />} label="System Status" value="OK" tone="green" />
        <StatusPill icon={<Cpu size={14} />} label="GPU Detected" value="100%" tone="cyan" />
        <StatusPill icon={<ShieldCheck size={14} />} label="Security" value="Locked" tone="green" />
        <ProofChip status="verified" />
      </div>
    </header>
  );
}

function StatusPill({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "green" | "cyan" | "amber" | "red";
}) {
  const toneClass = {
    green: "text-accent-green",
    cyan: "text-accent-cyan",
    amber: "text-accent-amber",
    red: "text-accent-red",
  }[tone];
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={toneClass}>{icon}</span>
      <span className="text-muted">{label}</span>
      <span className={["font-semibold", toneClass].join(" ")}>{value}</span>
    </div>
  );
}
