/**
 * ThemeSwitcher — W8-3 lane.
 *
 * Compact dropdown that toggles between Light, Dark, and System themes.
 * Two visual variants:
 *   - default — icon + label, suitable for menus and settings panels.
 *   - compact (icon-only) — for the topbar where horizontal space is
 *     scarce; current resolved theme renders as the trigger icon.
 *
 * ARIA: the trigger is `role="button"` with `aria-haspopup="listbox"`;
 * the menu is `role="listbox"` with each option `role="option"`. Keyboard
 * support: Escape closes; ArrowDown/ArrowUp move focus; Enter / Space
 * commits.
 */
import { useEffect, useRef, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "../../theme/ThemeProvider";
import type { ThemeMode } from "../../theme/tokens";

export interface ThemeSwitcherProps {
  /**
   * `compact` renders an icon-only button. `default` renders icon + label.
   */
  variant?: "default" | "compact";
  /** Optional className passed through to the trigger button. */
  className?: string;
  /** Override placement of the menu — defaults to bottom-right. */
  menuAlign?: "left" | "right";
}

const OPTIONS: ReadonlyArray<{
  mode: ThemeMode;
  label: string;
  description: string;
}> = [
  { mode: "light", label: "Light", description: "Bright surfaces, dark text" },
  { mode: "dark", label: "Dark", description: "Default — deep navy chrome" },
  { mode: "system", label: "System", description: "Follow OS preference" },
];

function ModeIcon({ mode, size = 14 }: { mode: ThemeMode; size?: number }) {
  if (mode === "light") return <Sun size={size} aria-hidden />;
  if (mode === "dark") return <Moon size={size} aria-hidden />;
  return <Monitor size={size} aria-hidden />;
}

export function ThemeSwitcher({
  variant = "default",
  className,
  menuAlign = "right",
}: ThemeSwitcherProps): JSX.Element {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onClickOutside);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onClickOutside);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const handleSelect = (next: ThemeMode) => {
    setTheme(next);
    setOpen(false);
  };

  const triggerLabel = variant === "compact" ? null : (
    <span className="text-xs font-medium">
      {OPTIONS.find((o) => o.mode === theme)?.label ?? "Theme"}
    </span>
  );

  // Compact mode shows the *resolved* icon so the user always sees what's
  // visually active. Default mode shows the *user choice* so "system"
  // still renders the monitor glyph.
  const triggerMode = variant === "compact" ? resolvedTheme : theme;

  return (
    <div ref={containerRef} className={`relative inline-flex ${className ?? ""}`}>
      <button
        type="button"
        data-testid="theme-switcher-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Theme: ${theme}. Click to change.`}
        title={`Theme: ${theme}`}
        onClick={() => setOpen((prev) => !prev)}
        className={[
          "inline-flex items-center gap-1.5 rounded-md border border-border",
          "bg-surface px-2 py-1 text-fg",
          "hover:bg-surface2 transition-colors",
          variant === "compact" ? "h-8 w-8 justify-center" : "",
        ].join(" ")}
      >
        <ModeIcon mode={triggerMode} size={variant === "compact" ? 16 : 14} />
        {triggerLabel}
      </button>
      {open ? (
        <div
          role="listbox"
          aria-label="Choose theme"
          data-testid="theme-switcher-menu"
          className={[
            "absolute top-full mt-1 z-50 min-w-[176px]",
            "rounded-md border border-border bg-surface",
            "shadow-lg shadow-black/40 p-1",
            menuAlign === "right" ? "right-0" : "left-0",
          ].join(" ")}
        >
          {OPTIONS.map((option) => {
            const active = option.mode === theme;
            return (
              <button
                key={option.mode}
                type="button"
                role="option"
                aria-selected={active}
                data-testid={`theme-switcher-option-${option.mode}`}
                onClick={() => handleSelect(option.mode)}
                className={[
                  "flex w-full items-start gap-2 rounded px-2 py-1.5 text-left",
                  "text-fg hover:bg-surface2 transition-colors",
                  active ? "bg-surface2" : "",
                ].join(" ")}
              >
                <span className="mt-0.5 text-muted">
                  <ModeIcon mode={option.mode} />
                </span>
                <span className="flex flex-col">
                  <span className="text-xs font-semibold">{option.label}</span>
                  <span className="text-[10px] text-muted">
                    {option.description}
                  </span>
                </span>
                {active ? (
                  <span
                    aria-hidden
                    className="ml-auto self-center text-[10px] uppercase tracking-wide text-accent-cyan"
                  >
                    Active
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
