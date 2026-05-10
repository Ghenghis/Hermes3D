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
  Terminal,
  X as CloseIcon,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import {
  ACTION_WINDOW_STORAGE_KEY,
  useResizable,
  type ResizableSize,
} from "./useResizable";

export type ActionWindowTab = "code" | "output" | "diff";

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
}: ActionWindowProps) {
  const storageKey = detached ? null : ACTION_WINDOW_STORAGE_KEY;
  const { size, rightHandleProps, bottomHandleProps, cornerHandleProps, isResizing } =
    useResizable({ storageKey, initialSize });
  const [activeTab, setActiveTab] = useState<ActionWindowTab>(defaultTab);
  const [maximized, setMaximized] = useState(false);

  const containerStyle = useMemo<React.CSSProperties>(() => {
    if (detached || maximized) {
      return { width: "100%", height: "100%" };
    }
    return { width: `${size.width}px`, height: `${size.height}px` };
  }, [detached, maximized, size.height, size.width]);

  const onPopOut = useCallback(() => {
    if (typeof window === "undefined") return;
    window.open(detachUrl, "hermes3d-action-window", "noopener,noreferrer");
  }, [detachUrl]);

  return (
    <section
      data-testid="action-window-root"
      data-detached={detached ? "true" : "false"}
      data-resizing={isResizing ? "true" : "false"}
      className="relative flex flex-col overflow-hidden rounded-lg border border-border bg-surface text-fg shadow-lg"
      style={containerStyle}
      aria-label="Action Window"
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-surface2 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-muted">Action Window</span>
          <span className="hidden text-xs text-muted sm:inline">·</span>
          <span className="hidden truncate text-xs text-fg sm:inline" data-testid="action-window-size-label">
            {detached || maximized ? "viewport" : `${size.width}×${size.height}`}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {!detached && (
            <button
              type="button"
              onClick={() => setMaximized((v) => !v)}
              aria-label={maximized ? "Restore Action Window" : "Maximize Action Window"}
              className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
            >
              {maximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
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

      {!detached && !maximized && (
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
