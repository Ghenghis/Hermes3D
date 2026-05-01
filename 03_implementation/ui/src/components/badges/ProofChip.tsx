import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";

export type ProofStatus = "verified" | "pending" | "failed";

const TONE: Record<
  ProofStatus,
  { Icon: typeof ShieldCheck; text: string; ring: string; label: string }
> = {
  verified: {
    Icon: ShieldCheck,
    text: "text-accent-green",
    ring: "ring-accent-green/40",
    label: "VERIFIED",
  },
  pending: {
    Icon: ShieldQuestion,
    text: "text-accent-amber",
    ring: "ring-accent-amber/40",
    label: "PENDING",
  },
  failed: {
    Icon: ShieldAlert,
    text: "text-accent-red",
    ring: "ring-accent-red/40",
    label: "FAILED",
  },
};

export function ProofChip({ status }: { status: ProofStatus }) {
  const { Icon, text, ring, label } = TONE[status];
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-chip text-[11px] font-bold tracking-wide ring-1",
        text,
        ring,
      ].join(" ")}
    >
      <Icon size={12} />
      {label}
    </span>
  );
}
