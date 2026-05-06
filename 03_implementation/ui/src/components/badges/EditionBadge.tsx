import type { Edition } from "../../types/edition";

const LABELS: Record<Edition, { label: string; tone: string }> = {
  desktop_gpu_worker: { label: "Desktop GPU Worker", tone: "text-accent-cyan border-accent-cyan/40" },
  ubuntu_vps_control_server: { label: "Ubuntu VPS", tone: "text-accent-blue border-accent-blue/40" },
  blocked_no_gpu: { label: "No GPU", tone: "text-accent-red border-accent-red/40" },
};

export function EditionBadge({ edition }: { edition: Edition }) {
  const e = LABELS[edition] ?? LABELS.blocked_no_gpu;
  return (
    <span
      className={[
        "inline-flex items-center px-2.5 py-0.5 rounded-chip text-xs font-medium border",
        e.tone,
      ].join(" ")}
    >
      {e.label}
    </span>
  );
}
