import { Bell, CircleDot, Clock, Cpu, Settings as SettingsIcon, ShieldCheck } from "lucide-react";
import { EditionBadge } from "../badges/EditionBadge";
import { ProofChip } from "../badges/ProofChip";
import { MOCK_SYSTEM_SNAPSHOT } from "../../data/mock/system";
import { MOCK_NOTIFICATIONS } from "../../data/mock/notifications";

/**
 * Top header per visual contract. Right cluster grouped as:
 *   [edition · system status · gpu · security · proof]   |   [time · bell · gear · avatar]
 *
 * Time pill renders the snapshot's `ts_utc` (NOT `Date.now()`) so the topbar
 * is visually deterministic for the Playwright screenshot gate. Bell badge
 * counts unread notifications. Gear is visual-only in Phase 2 (the left
 * sidebar's Settings tab is the real entry point).
 */
export function TopBar({ activeLabel }: { activeLabel: string }) {
  const sys = MOCK_SYSTEM_SNAPSHOT;
  const unread = MOCK_NOTIFICATIONS.filter((n) => !n.read).length;
  const time = formatClock(sys.ts_utc);

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
      <div className="flex items-center gap-3">
        <EditionBadge edition={sys.edition} />
        <StatusPill icon={<CircleDot size={14} />} label="System" value={sys.system_status} tone="green" />
        <StatusPill icon={<Cpu size={14} />} label="GPU" value={`${sys.gpu_detected_pct}%`} tone="cyan" />
        <StatusPill icon={<ShieldCheck size={14} />} label="Security" value={sys.security_status} tone="green" />
        <ProofChip status="verified" />
        <span className="h-5 w-px bg-border mx-1" aria-hidden />
        <TimePill time={time} />
        <BellButton unread={unread} />
        <GearButton />
        <Avatar initials="FN" />
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
    <div className="flex items-center gap-1.5 text-xs">
      <span className={toneClass}>{icon}</span>
      <span className="text-muted">{label}</span>
      <span className={["font-semibold", toneClass].join(" ")}>{value}</span>
    </div>
  );
}

function TimePill({ time }: { time: string }) {
  return (
    <div className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-chip bg-surface2 border border-border">
      <Clock size={13} className="text-muted" />
      <span className="text-fg font-mono tabular-nums">{time}</span>
      <span className="text-muted text-[10px]">UTC</span>
    </div>
  );
}

function BellButton({ unread }: { unread: number }) {
  return (
    <button
      type="button"
      aria-label={`Notifications (${unread} unread)`}
      className="relative p-1.5 rounded-md text-muted hover:text-fg hover:bg-surface2 transition-colors"
    >
      <Bell size={16} />
      {unread > 0 && (
        <span
          className="absolute -top-0.5 -right-0.5 h-4 min-w-[16px] px-1 rounded-full bg-accent-red text-white text-[10px] font-bold leading-4 text-center"
          aria-hidden
        >
          {unread}
        </span>
      )}
    </button>
  );
}

function GearButton() {
  return (
    <button
      type="button"
      aria-label="Settings"
      className="p-1.5 rounded-md text-muted hover:text-fg hover:bg-surface2 transition-colors"
    >
      <SettingsIcon size={16} />
    </button>
  );
}

function Avatar({ initials }: { initials: string }) {
  return (
    <div
      className="h-8 w-8 rounded-full bg-accent-blue/20 border border-accent-blue/40 flex items-center justify-center text-fg text-xs font-semibold"
      aria-label="User account"
    >
      {initials}
    </div>
  );
}

function formatClock(iso: string): string {
  // Deterministic HH:MM extraction from the mock ts_utc — no Date.now() so
  // screenshots are reproducible across runs.
  const t = iso.split("T")[1] ?? "";
  return t.slice(0, 5); // HH:MM
}
