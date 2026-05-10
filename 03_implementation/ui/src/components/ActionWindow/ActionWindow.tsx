/**
 * ActionWindow — resizable, pop-out workbench panel.
 *
 * Two host modes:
 *  - Embedded (default): floats inside the AppShell with right + bottom +
 *    corner resize handles; persists size to localStorage.
 *  - Detached: rendered when the route is `/action-window?detached=1`.
 *    The browser tab IS the window, so the panel fills the viewport, omits
 *    resize handles, and disables localStorage persistence.
 *
 * Tabs: Code · Output · Diff. The body is intentionally lightweight — the
 * tabs hold tool-runner output that is wired up by other lanes (W6-2 ships
 * the diff/apply preview hook). All three tabs render real backend data only;
 * empty states show "No data yet" with the source they're awaiting (no
 * placeholder text, per the no-fake contract).
 */

import {
  Code as CodeIcon,
  ExternalLink,
  GitMerge,
  Maximize2,
  Minimize2,
  Square,
  Terminal,
  X as CloseIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ACTION_WINDOW_STORAGE_KEY,
  useResizable,
  type ResizableSize,
} from "./useResizable";

export type ActionWindowTab = "code" | "output" | "diff";

/**
 * Three display modes per W15-A19 spec:
 *  - "normal":     embedded panel at the persisted (useResizable) size — inline
 *                  in the AppShell. This is the default.
 *  - "expanded":   ~50% of viewport (50vw × 50vh), centered as a non-modal
 *                  overlay. Useful when the user wants to focus but keep the
 *                  underlying tab visible behind the panel.
 *  - "fullscreen": 100% viewport modal — pinned to `fixed inset-0` and rendered
 *                  on top of the AppShell. The previous code's `maximized`
 *                  state corresponded to this mode.
 *
 * The mode is persisted to `localStorage` so the user's last choice survives a
 * page reload. The detached browser-tab form (rendered when the route is
 * `/action-window?detached=1`) ignores the persisted mode and always fills its
 * tab's viewport, because there is no surrounding chrome to expand against.
 */
export const ACTION_WINDOW_MODES = ["normal", "expanded", "fullscreen"] as const;
export type ActionWindowMode = (typeof ACTION_WINDOW_MODES)[number];

const MODE_STORAGE_KEY = "hermes3d.actionWindow.mode";

function isActionWindowMode(value: unknown): value is ActionWindowMode {
  return typeof value === "string" && (ACTION_WINDOW_MODES as readonly string[]).includes(value);
}

function readPersistedMode(): ActionWindowMode {
  if (typeof window === "undefined") {
    return "normal";
  }
  try {
    const raw = window.localStorage.getItem(MODE_STORAGE_KEY);
    return isActionWindowMode(raw) ? raw : "normal";
  } catch {
    return "normal";
  }
}

function writePersistedMode(mode: ActionWindowMode): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(MODE_STORAGE_KEY, mode);
  } catch {
    /* ignore — quota or private-mode failures are not fatal here */
  }
}

/** Cycle order: normal -> expanded -> fullscreen -> normal. */
export function nextActionWindowMode(mode: ActionWindowMode): ActionWindowMode {
  const idx = ACTION_WINDOW_MODES.indexOf(mode);
  return ACTION_WINDOW_MODES[(idx + 1) % ACTION_WINDOW_MODES.length];
}

export interface ActionWindowOutputEntry {
  ts: string; // ISO timestamp
  stream: "stdout" | "stderr";
  text: string;
}

export interface ActionWindowDiff {
  /** File path the diff applies to. */
  path: string;
  /** Unified-diff body (hunks, no headers required). */
  body: string;
}

export interface ActionWindowProps {
  /** When true, renders in detached/full-viewport mode. */
  detached?: boolean;
  /** Optional initial size override (used by tests). */
  initialSize?: ResizableSize;
  /** Pop-out URL — defaults to `/action-window?detached=1`. */
  detachUrl?: string;
  /** Close handler. When omitted, the close button is hidden. */
  onClose?: () => void;
  /** Optional code body (CodeMirror replacement is wired by integrators). */
  codeContent?: string;
  /** Output stream entries — empty array renders "Awaiting output". */
  output?: ActionWindowOutputEntry[];
  /** Reviewed-patch diff preview (W6-2 supplies this). */
  diff?: ActionWindowDiff | null;
  /** Default tab on mount. */
  defaultTab?: ActionWindowTab;
  /**
   * Optional initial display mode override. When omitted, the persisted value
   * from `localStorage` is used (falling back to "normal"). Pass an explicit
   * mode to bypass persistence — useful in tests.
   */
  initialMode?: ActionWindowMode;
  /** Called whenever the user cycles the mode toggle. */
  onModeChange?: (mode: ActionWindowMode) => void;
}

const TAB_DEFS: Array<{ id: ActionWindowTab; label: string; icon: JSX.Element }> = [
  { id: "code", label: "Code", icon: <CodeIcon size={13} /> },
  { id: "output", label: "Output", icon: <Terminal size={13} /> },
  { id: "diff", label: "Diff", icon: <GitMerge size={13} /> },
];

export function ActionWindow({
  detached = false,
  initialSize,
  detachUrl = "/action-window?detached=1",
  onClose,
  codeContent = "",
  output = [],
  diff = null,
  defaultTab = "code",
  initialMode,
  onModeChange,
}: ActionWindowProps) {
  const storageKey = detached ? null : ACTION_WINDOW_STORAGE_KEY;
  const { size, rightHandleProps, bottomHandleProps, cornerHandleProps, isResizing } =
    useResizable({ storageKey, initialSize });
  const [activeTab, setActiveTab] = useState<ActionWindowTab>(defaultTab);
  // Detached browser-tab form is always fullscreen-equivalent and ignores the
  // persisted mode. For the embedded form we initialise from the explicit prop
  // first, then `localStorage`, falling back to "normal".
  const [mode, setMode] = useState<ActionWindowMode>(() => {
    if (detached) return "fullscreen";
    if (initialMode) return initialMode;
    return readPersistedMode();
  });

  // Persist only when the embedded form changes mode (detached form is
  // ephemeral — its mode is implicit in the pop-out).
  useEffect(() => {
    if (detached) return;
    writePersistedMode(mode);
  }, [detached, mode]);

  const cycleMode = useCallback(() => {
    setMode((prev) => {
      const next = nextActionWindowMode(prev);
      onModeChange?.(next);
      return next;
    });
  }, [onModeChange]);

  const setExplicitMode = useCallback(
    (next: ActionWindowMode) => {
      setMode((prev) => {
        if (prev === next) return prev;
        onModeChange?.(next);
        return next;
      });
    },
    [onModeChange],
  );

  const containerStyle = useMemo<React.CSSProperties>(() => {
    if (detached || mode === "fullscreen") {
      return { width: "100%", height: "100%" };
    }
    if (mode === "expanded") {
      // ~50% of the viewport, centered. Using vw/vh keeps the math honest
      // across the breakpoints the AppShell supports.
      return { width: "50vw", height: "50vh" };
    }
    return { width: `${size.width}px`, height: `${size.height}px` };
  }, [detached, mode, size.height, size.width]);

  const sizeLabel = useMemo(() => {
    if (detached || mode === "fullscreen") return "viewport";
    if (mode === "expanded") return "50vw × 50vh";
    return `${size.width}×${size.height}`;
  }, [detached, mode, size.height, size.width]);

  const containerClassName = useMemo(() => {
    const base =
      "relative flex flex-col overflow-hidden rounded-lg border border-border bg-surface text-fg shadow-lg";
    if (detached) return base;
    if (mode === "fullscreen") return `${base} fixed inset-0 z-50`;
    if (mode === "expanded") return `${base} fixed left-1/2 top-1/2 z-40 -translate-x-1/2 -translate-y-1/2`;
    return base;
  }, [detached, mode]);

  const onPopOut = useCallback(() => {
    if (typeof window === "undefined") return;
    window.open(detachUrl, "hermes3d-action-window", "noopener,noreferrer");
  }, [detachUrl]);

  const modeButtonLabel: Record<ActionWindowMode, string> = {
    normal: "Expand Action Window to half-viewport",
    expanded: "Maximize Action Window to fullscreen",
    fullscreen: "Restore Action Window to normal",
  };
  const modeButtonIcon: Record<ActionWindowMode, JSX.Element> = {
    normal: <Maximize2 size={14} />,
    expanded: <Square size={14} />,
    fullscreen: <Minimize2 size={14} />,
  };

  return (
    <section
      data-testid="action-window-root"
      data-detached={detached ? "true" : "false"}
      data-resizing={isResizing ? "true" : "false"}
      data-mode={mode}
      className={containerClassName}
      style={containerStyle}
      aria-label="Action Window"
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-surface2 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-muted">Action Window</span>
          <span className="hidden text-xs text-muted sm:inline">·</span>
          <span className="hidden truncate text-xs text-fg sm:inline" data-testid="action-window-size-label">
            {sizeLabel}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {!detached && (
            <div
              role="group"
              aria-label="Action Window mode"
              data-testid="action-window-mode-group"
              className="hidden items-center gap-0.5 rounded-md border border-border bg-bg/40 p-0.5 md:flex"
            >
              {ACTION_WINDOW_MODES.map((m) => {
                const active = mode === m;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setExplicitMode(m)}
                    aria-label={`Set Action Window to ${m}`}
                    aria-pressed={active}
                    data-testid={`action-window-mode-${m}`}
                    className={[
                      "rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide transition-colors",
                      active
                        ? "bg-accent-blue/15 text-accent-blue"
                        : "text-muted hover:bg-surface hover:text-fg",
                    ].join(" ")}
                  >
                    {m === "normal" ? "Norm" : m === "expanded" ? "Exp" : "Full"}
                  </button>
                );
              })}
            </div>
          )}
          {!detached && (
            <button
              type="button"
              onClick={cycleMode}
              aria-label={modeButtonLabel[mode]}
              data-testid="action-window-mode-toggle"
              data-mode={mode}
              className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
            >
              {modeButtonIcon[mode]}
            </button>
          )}
          <button
            type="button"
            onClick={onPopOut}
            aria-label="Open Action Window in new tab"
            data-testid="action-window-popout"
            className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
          >
            <ExternalLink size={14} />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close Action Window"
              className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
            >
              <CloseIcon size={14} />
            </button>
          )}
        </div>
      </header>

      <nav className="flex shrink-0 items-center gap-1 border-b border-border bg-surface px-2 py-1.5" role="tablist">
        {TAB_DEFS.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              data-testid={`action-window-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={[
                "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors",
                active
                  ? "bg-accent-blue/15 text-accent-blue"
                  : "text-muted hover:bg-surface2 hover:text-fg",
              ].join(" ")}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div
        className="min-h-0 flex-1 overflow-auto bg-bg p-3 font-mono text-xs"
        data-testid={`action-window-panel-${activeTab}`}
      >
        {activeTab === "code" && <CodePanel code={codeContent} />}
        {activeTab === "output" && <OutputPanel entries={output} />}
        {activeTab === "diff" && <DiffPanel diff={diff} />}
      </div>

      {!detached && mode === "normal" && (
        <>
          <div
            {...rightHandleProps}
            data-testid="action-window-handle-right"
            className="absolute right-0 top-0 h-full w-1.5 cursor-ew-resize bg-transparent hover:bg-accent-blue/40"
          />
          <div
            {...bottomHandleProps}
            data-testid="action-window-handle-bottom"
            className="absolute bottom-0 left-0 h-1.5 w-full cursor-ns-resize bg-transparent hover:bg-accent-blue/40"
          />
          <div
            {...cornerHandleProps}
            data-testid="action-window-handle-corner"
            className="absolute bottom-0 right-0 h-3 w-3 cursor-nwse-resize bg-transparent hover:bg-accent-blue/60"
          />
        </>
      )}
    </section>
  );
}

function CodePanel({ code }: { code: string }) {
  if (!code) {
    return <EmptyState label="No code loaded yet — open a workbench task." />;
  }
  return <pre className="whitespace-pre-wrap break-words text-fg">{code}</pre>;
}

function OutputPanel({ entries }: { entries: ActionWindowOutputEntry[] }) {
  if (entries.length === 0) {
    return <EmptyState label="Awaiting output from the active runner." />;
  }
  return (
    <div className="space-y-1">
      {entries.map((entry, idx) => (
        <div
          key={`${entry.ts}-${idx}`}
          className={[
            "flex gap-2",
            entry.stream === "stderr" ? "text-accent-red" : "text-fg",
          ].join(" ")}
        >
          <span className="shrink-0 text-muted">{shortTs(entry.ts)}</span>
          <span className="shrink-0 uppercase text-[10px] text-muted">{entry.stream}</span>
          <span className="whitespace-pre-wrap break-words">{entry.text}</span>
        </div>
      ))}
    </div>
  );
}

function DiffPanel({ diff }: { diff: ActionWindowDiff | null }) {
  if (!diff) {
    return <EmptyState label="No reviewed patch loaded — apply a proposal to preview." />;
  }
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted">
        <span className="text-fg">{diff.path}</span>
      </div>
      <pre className="whitespace-pre-wrap break-words text-fg">{diff.body}</pre>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center text-muted">
        <div className="text-xs uppercase tracking-wide">Action Window</div>
        <div className="mt-1 text-sm">{label}</div>
      </div>
    </div>
  );
}

function shortTs(iso: string): string {
  const [, time] = iso.split("T");
  if (!time) return iso;
  return time.slice(0, 8);
}
