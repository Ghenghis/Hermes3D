/**
 * DetachedActionWindow — full-viewport host for the pop-out browser tab.
 *
 * Reads `?detached=1` from the location and mounts the Action Window with
 * `detached={true}` so resize handles and localStorage persistence are
 * suppressed (the browser tab itself IS the window). The panel fills the
 * viewport via the parent CSS shell (`html`/`body { height: 100% }`).
 */

import { useEffect, useState } from "react";
import { ActionWindow } from "./ActionWindow";

export function DetachedActionWindow() {
  const [size, setSize] = useState<{ width: number; height: number }>(() => ({
    width: typeof window === "undefined" ? 1280 : window.innerWidth,
    height: typeof window === "undefined" ? 720 : window.innerHeight,
  }));

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setSize({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <div
      data-testid="action-window-detached-host"
      className="flex h-screen w-screen flex-col bg-bg text-fg"
      style={{ width: size.width, height: size.height }}
    >
      <ActionWindow detached />
    </div>
  );
}
