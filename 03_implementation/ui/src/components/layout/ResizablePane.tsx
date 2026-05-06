import {
  type AriaRole,
  type CSSProperties,
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";

type ResizeSide = "left" | "right";

type ResizablePaneProps = {
  children: ReactNode;
  storageKey: string;
  defaultWidth: number;
  minWidth: number;
  maxWidth: number;
  label: string;
  className?: string;
  handleClassName?: string;
  dataTestId?: string;
  ariaLabel?: string;
  role?: AriaRole;
  side?: ResizeSide;
};

export function ResizablePane({
  children,
  storageKey,
  defaultWidth,
  minWidth,
  maxWidth,
  label,
  className = "",
  handleClassName = "",
  dataTestId,
  ariaLabel,
  role,
  side = "right",
}: ResizablePaneProps) {
  const paneRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(() => readStoredWidth(storageKey, defaultWidth, minWidth, maxWidth));
  const [resizing, setResizing] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(storageKey, String(width));
  }, [storageKey, width]);

  useEffect(() => {
    if (!resizing) {
      return undefined;
    }

    const onPointerMove = (event: PointerEvent) => {
      const rect = paneRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }
      const rawWidth = side === "left" ? rect.right - event.clientX : event.clientX - rect.left;
      setWidth(clamp(Math.round(rawWidth), minWidth, maxWidth));
    };

    const onPointerUp = () => setResizing(false);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [maxWidth, minWidth, resizing, side]);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const step = event.shiftKey ? 32 : 16;
    if (event.key === "Home") {
      event.preventDefault();
      setWidth(minWidth);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      setWidth(maxWidth);
      return;
    }
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
      return;
    }
    event.preventDefault();
    const visualDirection = event.key === "ArrowRight" ? 1 : -1;
    const sideMultiplier = side === "right" ? 1 : -1;
    setWidth((current) => clamp(current + visualDirection * sideMultiplier * step, minWidth, maxWidth));
  };

  return (
    <div
      ref={paneRef}
      role={role}
      aria-label={ariaLabel}
      data-testid={dataTestId}
      data-resizing={resizing ? "true" : "false"}
      className={`relative ${className}`}
      style={{ "--pane-width": `${width}px` } as CSSProperties}
    >
      {children}
      <button
        type="button"
        aria-label={`Resize ${label}`}
        aria-orientation="vertical"
        aria-valuemin={minWidth}
        aria-valuemax={maxWidth}
        aria-valuenow={width}
        role="separator"
        title={`Drag to resize ${label}. Double-click to reset.`}
        onPointerDown={(event) => {
          event.preventDefault();
          event.currentTarget.setPointerCapture(event.pointerId);
          setResizing(true);
        }}
        onDoubleClick={() => setWidth(defaultWidth)}
        onKeyDown={onKeyDown}
        className={[
          "group absolute bottom-0 top-0 z-30 w-2 cursor-col-resize bg-transparent outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan/70",
          side === "right" ? "right-0" : "left-0",
          handleClassName,
        ].join(" ")}
      >
        <span
          className={[
            "absolute bottom-2 top-2 w-px rounded-full bg-border/80 transition-colors",
            "group-hover:bg-accent-cyan group-focus-visible:bg-accent-cyan",
            side === "right" ? "right-0.5" : "left-0.5",
          ].join(" ")}
        />
      </button>
    </div>
  );
}

function readStoredWidth(storageKey: string, defaultWidth: number, minWidth: number, maxWidth: number): number {
  if (typeof window === "undefined") {
    return defaultWidth;
  }
  const stored = Number(window.localStorage.getItem(storageKey));
  return Number.isFinite(stored) && stored > 0 ? clamp(stored, minWidth, maxWidth) : defaultWidth;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
