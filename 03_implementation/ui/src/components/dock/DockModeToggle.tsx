import { Maximize2, Minimize2, PictureInPicture2 } from "lucide-react";
import { type DockMode, useStore } from "../../app/store";

const MODES: { mode: DockMode; Icon: typeof Maximize2; label: string }[] = [
  { mode: "docked", Icon: Minimize2, label: "Docked" },
  { mode: "undocked", Icon: PictureInPicture2, label: "Undocked" },
  { mode: "external", Icon: Maximize2, label: "Fullscreen" },
];

/**
 * 3-mode dock toggle per ADR-008 §3 (docked / undocked / external) +
 * `TAB_SPECS.md` "Every panel has: ... undock, fullscreen."
 *
 * Phase 2 ships CSS-only fullscreen and writes the chosen mode to the
 * zustand store. Phase 3+ may wire native detached windows for "undocked";
 * the contract surface (this 3-button toggle) stays stable.
 */
export function DockModeToggle({ panelId }: { panelId: string }) {
  const dock = useStore((s) => s.panelDock[panelId] ?? "docked");
  const setPanelDock = useStore((s) => s.setPanelDock);
  return (
    <div
      className="inline-flex items-center gap-0.5 border border-border rounded-md p-0.5"
      role="group"
      aria-label="Dock mode"
    >
      {MODES.map(({ mode, Icon, label }) => {
        const active = dock === mode;
        return (
          <button
            key={mode}
            type="button"
            aria-label={label}
            aria-pressed={active}
            onClick={() => setPanelDock(panelId, mode)}
            className={[
              "p-1 rounded-sm transition-colors",
              active
                ? "bg-surface2 text-accent-cyan"
                : "text-muted hover:text-fg",
            ].join(" ")}
          >
            <Icon size={12} />
          </button>
        );
      })}
    </div>
  );
}
