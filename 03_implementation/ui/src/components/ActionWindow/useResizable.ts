/**
 * useResizable — pointer-event driven resize hook for the Action Window.
 *
 * Implementation notes:
 *  - Uses HTML5 Pointer Events (https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events).
 *    Pointer events unify mouse + touch + pen and provide pointer-capture so a
 *    drag survives leaving the handle's bounding box.
 *  - Resize math is pure (`computeNextSize`); all DOM-touching code lives in
 *    the hook so the math itself is easy to unit-test from Node.
 *  - Persists last size to localStorage under `STORAGE_KEY`. Persistence is
 *    optional and gracefully degrades when localStorage is unavailable.
 *  - Caps at viewport on every change so a window resize never strands the
 *    Action Window off-screen.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export interface SizeLimits {
  minWidth: number;
  minHeight: number;
  maxWidth: number;
  maxHeight: number;
}

export interface ResizableSize {
  width: number;
  height: number;
}

export interface UseResizableOptions {
  /** localStorage key. Pass null to disable persistence (e.g. detached mode). */
  storageKey?: string | null;
  initialSize?: ResizableSize;
  minWidth?: number;
  minHeight?: number;
  /** Override the viewport size lookup (used by tests). */
  viewportRef?: () => { width: number; height: number };
}

const DEFAULT_INITIAL_SIZE: ResizableSize = { width: 960, height: 600 };
const DEFAULT_MIN_WIDTH = 600;
const DEFAULT_MIN_HEIGHT = 400;
export const ACTION_WINDOW_STORAGE_KEY = "hermes3d:action-window:size";

/**
 * Pure size-math step. Given a starting size, the pointer delta, and limits,
 * return the next clamped size. This is the function unit tests target.
 *
 * `direction` selects which edges the handle controls:
 *   - "right":  width follows dx, height unchanged
 *   - "bottom": height follows dy, width unchanged
 *   - "corner": both follow the deltas
 */
export function computeNextSize(
  start: ResizableSize,
  dx: number,
  dy: number,
  direction: "right" | "bottom" | "corner",
  limits: SizeLimits,
): ResizableSize {
  const widthRaw = direction === "bottom" ? start.width : start.width + dx;
  const heightRaw = direction === "right" ? start.height : start.height + dy;
  return {
    width: clamp(widthRaw, limits.minWidth, limits.maxWidth),
    height: clamp(heightRaw, limits.minHeight, limits.maxHeight),
  };
}

/**
 * Clamp the saved size to the current viewport so a smaller window doesn't
 * leave the panel oversized. Pure — also useful directly from tests.
 */
export function capToViewport(size: ResizableSize, limits: SizeLimits): ResizableSize {
  return {
    width: clamp(size.width, limits.minWidth, limits.maxWidth),
    height: clamp(size.height, limits.minHeight, limits.maxHeight),
  };
}

export function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

export function loadPersistedSize(
  storageKey: string | null,
  fallback: ResizableSize,
): ResizableSize {
  if (!storageKey) return fallback;
  if (typeof window === "undefined" || !window.localStorage) return fallback;
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as unknown;
    if (
      parsed &&
      typeof parsed === "object" &&
      "width" in parsed &&
      "height" in parsed &&
      typeof (parsed as { width: unknown }).width === "number" &&
      typeof (parsed as { height: unknown }).height === "number"
    ) {
      return {
        width: (parsed as ResizableSize).width,
        height: (parsed as ResizableSize).height,
      };
    }
  } catch {
    // Corrupt JSON or restricted storage — fall back silently.
  }
  return fallback;
}

export function persistSize(storageKey: string | null, size: ResizableSize): void {
  if (!storageKey) return;
  if (typeof window === "undefined" || !window.localStorage) return;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(size));
  } catch {
    // Quota exceeded or storage disabled — ignore.
  }
}

export interface ResizeHandleProps {
  onPointerDown: (event: React.PointerEvent<HTMLElement>) => void;
  role: string;
  "aria-label": string;
  "data-direction": "right" | "bottom" | "corner";
}

export interface UseResizableResult {
  size: ResizableSize;
  setSize: (size: ResizableSize) => void;
  isResizing: boolean;
  rightHandleProps: ResizeHandleProps;
  bottomHandleProps: ResizeHandleProps;
  cornerHandleProps: ResizeHandleProps;
}

/**
 * React hook wiring the math to pointer events. Each call sets up its own
 * captured-pointer drag — multiple handles can coexist on the same element
 * because we read `data-direction` from the handle that started the drag.
 */
export function useResizable(opts: UseResizableOptions = {}): UseResizableResult {
  const storageKey = opts.storageKey === undefined ? ACTION_WINDOW_STORAGE_KEY : opts.storageKey;
  const initial = opts.initialSize ?? DEFAULT_INITIAL_SIZE;
  const minWidth = opts.minWidth ?? DEFAULT_MIN_WIDTH;
  const minHeight = opts.minHeight ?? DEFAULT_MIN_HEIGHT;

  const getViewport = useCallback(() => {
    if (opts.viewportRef) return opts.viewportRef();
    if (typeof window === "undefined") {
      return { width: initial.width, height: initial.height };
    }
    return { width: window.innerWidth, height: window.innerHeight };
  }, [initial.height, initial.width, opts]);

  const [size, setSizeState] = useState<ResizableSize>(() => {
    const persisted = loadPersistedSize(storageKey, initial);
    const vp = getViewport();
    return capToViewport(persisted, {
      minWidth,
      minHeight,
      maxWidth: vp.width,
      maxHeight: vp.height,
    });
  });
  const [isResizing, setIsResizing] = useState(false);

  // Keep size capped when the window resizes.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => {
      const vp = getViewport();
      setSizeState((prev) =>
        capToViewport(prev, {
          minWidth,
          minHeight,
          maxWidth: vp.width,
          maxHeight: vp.height,
        }),
      );
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [getViewport, minHeight, minWidth]);

  // Persist size whenever it settles.
  useEffect(() => {
    persistSize(storageKey, size);
  }, [size, storageKey]);

  const setSize = useCallback(
    (next: ResizableSize) => {
      const vp = getViewport();
      setSizeState(
        capToViewport(next, {
          minWidth,
          minHeight,
          maxWidth: vp.width,
          maxHeight: vp.height,
        }),
      );
    },
    [getViewport, minHeight, minWidth],
  );

  const dragStateRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    start: ResizableSize;
    direction: "right" | "bottom" | "corner";
    target: HTMLElement;
    onMove: (e: PointerEvent) => void;
    onUp: (e: PointerEvent) => void;
  } | null>(null);

  const startDrag = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      const target = event.currentTarget;
      const direction =
        (target.getAttribute("data-direction") as "right" | "bottom" | "corner" | null) ??
        "corner";
      // Capture the pointer so movement outside the handle still fires events.
      try {
        target.setPointerCapture(event.pointerId);
      } catch {
        // Capture can fail in jsdom or non-pointer environments — keep going.
      }
      const startSize = { ...size };
      const onMove = (moveEvent: PointerEvent) => {
        if (!dragStateRef.current) return;
        if (moveEvent.pointerId !== dragStateRef.current.pointerId) return;
        const dx = moveEvent.clientX - dragStateRef.current.startX;
        const dy = moveEvent.clientY - dragStateRef.current.startY;
        const vp = getViewport();
        setSizeState(
          computeNextSize(dragStateRef.current.start, dx, dy, dragStateRef.current.direction, {
            minWidth,
            minHeight,
            maxWidth: vp.width,
            maxHeight: vp.height,
          }),
        );
      };
      const onUp = (upEvent: PointerEvent) => {
        if (!dragStateRef.current) return;
        if (upEvent.pointerId !== dragStateRef.current.pointerId) return;
        const t = dragStateRef.current.target;
        try {
          t.releasePointerCapture(dragStateRef.current.pointerId);
        } catch {
          // ignore — already released
        }
        t.removeEventListener("pointermove", onMove);
        t.removeEventListener("pointerup", onUp);
        t.removeEventListener("pointercancel", onUp);
        dragStateRef.current = null;
        setIsResizing(false);
      };
      dragStateRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        start: startSize,
        direction,
        target,
        onMove,
        onUp,
      };
      target.addEventListener("pointermove", onMove);
      target.addEventListener("pointerup", onUp);
      target.addEventListener("pointercancel", onUp);
      setIsResizing(true);
      event.preventDefault();
    },
    [getViewport, minHeight, minWidth, size],
  );

  // Cleanup any in-flight drag on unmount.
  useEffect(() => {
    return () => {
      const drag = dragStateRef.current;
      if (drag) {
        try {
          drag.target.releasePointerCapture(drag.pointerId);
        } catch {
          // ignore
        }
        drag.target.removeEventListener("pointermove", drag.onMove);
        drag.target.removeEventListener("pointerup", drag.onUp);
        drag.target.removeEventListener("pointercancel", drag.onUp);
        dragStateRef.current = null;
      }
    };
  }, []);

  return {
    size,
    setSize,
    isResizing,
    rightHandleProps: {
      onPointerDown: startDrag,
      role: "separator",
      "aria-label": "Resize Action Window width",
      "data-direction": "right",
    },
    bottomHandleProps: {
      onPointerDown: startDrag,
      role: "separator",
      "aria-label": "Resize Action Window height",
      "data-direction": "bottom",
    },
    cornerHandleProps: {
      onPointerDown: startDrag,
      role: "separator",
      "aria-label": "Resize Action Window",
      "data-direction": "corner",
    },
  };
}
