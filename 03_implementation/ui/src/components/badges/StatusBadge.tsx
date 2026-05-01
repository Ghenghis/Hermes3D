/**
 * Status chip per visual contract: small pill with colored dot + label.
 * Tones map to the design-token accent palette.
 */
export type StatusTone = "green" | "amber" | "red" | "blue" | "cyan" | "muted";

const TONE: Record<StatusTone, { dot: string; text: string; bg: string }> = {
  green: { dot: "bg-accent-green", text: "text-accent-green", bg: "bg-accent-green/10" },
  amber: { dot: "bg-accent-amber", text: "text-accent-amber", bg: "bg-accent-amber/10" },
  red: { dot: "bg-accent-red", text: "text-accent-red", bg: "bg-accent-red/10" },
  blue: { dot: "bg-accent-blue", text: "text-accent-blue", bg: "bg-accent-blue/10" },
  cyan: { dot: "bg-accent-cyan", text: "text-accent-cyan", bg: "bg-accent-cyan/10" },
  muted: { dot: "bg-muted", text: "text-muted", bg: "bg-muted/10" },
};

export function StatusBadge({ tone, label }: { tone: StatusTone; label: string }) {
  const t = TONE[tone];
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-chip text-xs font-medium",
        t.bg,
        t.text,
      ].join(" ")}
    >
      <span className={["h-1.5 w-1.5 rounded-full", t.dot].join(" ")} aria-hidden />
      {label}
    </span>
  );
}
