import { Maximize2, Minimize2, PictureInPicture2 } from "lucide-react";
import { type DockMode, useStore } from "../../app/store";

const MODES: { mode: DockMode; Icon: typeof Maximize2; label: string; hint: string }[] = [
  { mode: "docked",     Icon: Minimize2,         label: "Docked",     hint: "Inline panel (default)" },
  { mode: "undocked",   Icon: PictureInPicture2, label: "Undocked",   hint: "Floating panel overlay" },
  { mode: "fullscreen", Icon: Maximize2,         label: "Fullscreen", hint: "Expanded CSS overlay" },
];

/**
 * 3-mode dock toggle per ADR-008 §3 + `TAB_SPECS.md` "Every panel has:
 * ... undock, fullscreen."
 *
 * Phase 2 is store-only — every transition writes to the zustand
 * `panelDock` map and renders via CSS.
 *
 * Click already-active mode → returns to "docked" (so the toggle is
 * always escapable without a separate close button).
 */
export function DockModeToggle({ panelId, panelTitle }: { panelId: string; panelTitle: string }) {
  const dock = useStore((s) => s.panelDock[panelId] ?? "docked");
  const togglePanelDock = useStore((s) => s.togglePanelDock);
  return (
    <div
      className="inline-flex items-center gap-0.5 border border-border rounded-md p-0.5"
      role="group"
      aria-label={`Dock mode controls for ${panelTitle}`}
    >
      {MODES.map(({ mode, Icon, label, hint }) => {
        const active = dock === mode;
        return (
          <button
            key={mode}
            type="button"
            aria-label={`Set ${panelTitle} panel to ${label.toLowerCase()}`}
            aria-pressed={active}
            title={`${label}: ${hint}`}
            data-dock-mode={mode}
            data-active={active}
            onClick={() => togglePanelDock(panelId, mode)}
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
