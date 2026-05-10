/**
 * Dashboard mode switcher — W6-3 lane.
 *
 * Top-right segmented toggle "Simple | Advanced | Custom". The choice is held
 * in `useDashboardModeStore` (persisted to localStorage). The switcher emits
 * a hashchange (`#dashboard:<mode>`) so deep links survive a refresh and so
 * other parts of the app that observe `location.hash` stay in sync.
 *
 * The component is presentational — colours come from the shared Tailwind
 * tokens (`bg-surface`, `text-fg`, etc.) so it adopts whatever theme the
 * AppShell provides.
 */
import { DASHBOARD_MODES, type DashboardMode, useDashboardModeStore } from "./dashboardModeStore";

const MODE_LABELS: Record<DashboardMode, string> = {
  simple: "Simple",
  advanced: "Advanced",
  custom: "Custom",
};

const MODE_TITLES: Record<DashboardMode, string> = {
  simple: "Minimal KPI cards and system status only",
  advanced: "Full live dashboard with all panels and the Hermes Agents dock",
  custom: "User-configurable widget layout (drag to rearrange)",
};

export type DashboardModeSwitcherProps = {
  /**
   * When provided, overrides the store. Useful in unit tests and stories.
   * In production callers should rely on the live store.
   */
  mode?: DashboardMode;
  onChange?: (mode: DashboardMode) => void;
  className?: string;
};

export function DashboardModeSwitcher({ mode, onChange, className = "" }: DashboardModeSwitcherProps) {
  const storeMode = useDashboardModeStore((state) => state.mode);
  const setStoreMode = useDashboardModeStore((state) => state.setMode);
  const active = mode ?? storeMode;

  const handleSelect = (next: DashboardMode) => {
    if (onChange) {
      onChange(next);
      return;
    }
    setStoreMode(next);
    if (typeof window !== "undefined") {
      const desired = `#dashboard:${next}`;
      if (window.location.hash !== desired) {
        window.history.replaceState(null, "", desired);
        try {
          window.dispatchEvent(new HashChangeEvent("hashchange"));
        } catch {
          // Safari / older browsers: fall back to a manual event
          const event = document.createEvent("HTMLEvents");
          event.initEvent("hashchange", true, false);
          window.dispatchEvent(event);
        }
      }
    }
  };

  return (
    <div
      role="radiogroup"
      aria-label="Dashboard mode"
      data-testid="dashboard-mode-switcher"
      className={[
        "inline-flex items-center gap-0.5 rounded-md border border-border bg-surface p-0.5 text-[12px]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {DASHBOARD_MODES.map((candidate) => {
        const selected = candidate === active;
        return (
          <button
            key={candidate}
            type="button"
            role="radio"
            aria-checked={selected}
            data-testid={`dashboard-mode-btn-${candidate}`}
            data-active={selected ? "true" : "false"}
            onClick={() => handleSelect(candidate)}
            title={MODE_TITLES[candidate]}
            className={[
              "rounded px-2.5 py-1 font-semibold uppercase tracking-wide transition-colors",
              selected
                ? "bg-accent-blue/20 text-accent-blue"
                : "text-muted hover:bg-surface2 hover:text-fg",
            ].join(" ")}
          >
            {MODE_LABELS[candidate]}
          </button>
        );
      })}
    </div>
  );
}
