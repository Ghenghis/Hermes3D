import { Bell, CircleDot, Clock, Cpu, Settings as SettingsIcon, ShieldCheck } from "lucide-react";
import { EditionBadge } from "../badges/EditionBadge";
import { ProofChip } from "../badges/ProofChip";
import { DashboardModeSwitcher } from "../dashboard/DashboardModeSwitcher";
import { ThemeSwitcher } from "../ThemeSwitcher";
import { adapters } from "../../api/adapters";
import type { Notification } from "../../types/notification";
import type { ProofBundle } from "../../types/proof";
import type { SystemSnapshot } from "../../types/system";
import { useEffect, useState } from "react";
import { useStore } from "../../app/store";

/**
 * Top header per visual contract. Right cluster grouped as:
 *   [edition · system status · gpu · security · proof]   |   [time · bell · gear · avatar]
 *
 * Time pill renders the snapshot's `ts_utc` (NOT `Date.now()`) so the topbar
 * is visually deterministic for the Playwright screenshot gate. Bell opens the
 * dashboard notification center; Gear routes to the live Settings tab.
 */
export function TopBar({ activeLabel }: { activeLabel: string }) {
  const setUiMode = useStore((s) => s.setUiMode);
  const setActiveTabId = useStore((s) => s.setActiveTabId);
  const activeTabId = useStore((s) => s.activeTabId);
  const [sys, setSys] = useState<SystemSnapshot | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [latestProof, setLatestProof] = useState<ProofBundle | null>(null);
  const unread = notifications.filter((n) => !n.read).length;
  const time = sys ? formatClock(sys.ts_utc) : "--:--";
  const showDashboardModes = activeTabId === "dashboard";

  useEffect(() => {
    let mounted = true;

    const fetchAll = () => {
      void adapters.getSystemSnapshot().then((snapshot) => {
        if (mounted) setSys(snapshot);
      });
      void adapters.getNotifications().then((items) => {
        if (mounted) setNotifications(items);
      });
      void adapters.getLatestProofBundle().then((bundle) => {
        if (mounted) setLatestProof(bundle);
      });
    };

    fetchAll();
    // Refresh system status every 10 s — non-critical display data; 10 s avoids render churn.
    const timer = window.setInterval(fetchAll, 10_000);

    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <header className="flex min-h-14 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-surface px-3 py-2 md:flex-nowrap md:px-6">
      <div className="flex min-w-0 items-baseline gap-2 md:gap-3">
        <span className="text-fg font-semibold text-base truncate">
          AI-DRIVEN 3D PRINTING OS
        </span>
        <span className="hidden text-muted text-xs truncate sm:inline">
          Design · Verify · Slice · Print · Monitor
        </span>
        <span className="hidden text-muted text-xs sm:inline">·</span>
        <span className="text-muted text-xs truncate">{activeLabel}</span>
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-1.5 md:flex-nowrap md:gap-2.5">
        {sys ? (
          <>
            <span className="hidden lg:inline-flex"><EditionBadge edition={sys.edition} /></span>
            <StatusPill icon={<CircleDot size={13} />} label="System" value={sys.system_status} tone={systemTone(sys.system_status)} />
            <span className="hidden sm:inline-flex"><StatusPill icon={<Cpu size={13} />} label="GPU" value={`${sys.gpu_detected_pct}%`} tone="cyan" /></span>
            <span className="hidden xl:inline-flex"><StatusPill icon={<ShieldCheck size={13} />} label="Security" value={sys.security_status} tone={sys.security_status === "Locked" ? "green" : "amber"} /></span>
            {latestProof && <ProofChip status={latestProof.verdict === "verified" ? "verified" : "pending"} />}
          </>
        ) : (
          <StatusPill icon={<CircleDot size={13} />} label="Backend" value="unavailable" tone="amber" />
        )}
        <span className="h-6 w-px bg-border mx-1.5" aria-hidden />
        {showDashboardModes && <DashboardModeSwitcher />}
        <button
          type="button"
          onClick={() => setUiMode("simple")}
          className="rounded-md border border-accent-blue/50 bg-accent-blue/10 px-2 py-1 text-xs font-semibold text-accent-blue hover:bg-accent-blue/20"
          title="Switch to the live Simple Version (legacy)"
        >
          Simple
        </button>
        <TimePill time={time} />
        <ThemeSwitcher variant="compact" />
        <BellButton unread={unread} onClick={() => setActiveTabId("dashboard")} />
        <GearButton onClick={() => setActiveTabId("settings")} />
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

function BellButton({ unread, onClick }: { unread: number; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Notifications (${unread} unread)`}
      title="Open dashboard notification center"
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

function GearButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open settings panel"
      title="Open settings"
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
  const t = iso.split("T")[1] ?? "";
  return t.slice(0, 5); // HH:MM
}

function systemTone(status: SystemSnapshot["system_status"]): "green" | "amber" | "red" {
  if (status === "OK") return "green";
  if (status === "DEGRADED") return "amber";
  return "red";
}
