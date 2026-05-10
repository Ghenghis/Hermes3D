/**
 * ActionWindowMount — host wrapper that renders the Action Window plus the
 * floating control surface used by integrators. Kept separate from
 * `ActionWindow.tsx` so that `App.tsx` (currently locked by W6-3) can later
 * import either the bare panel or this complete mount without ceremony.
 *
 * Behaviour:
 *  - When `forceVisible` is false (default) the mount draws a floating
 *    control button that toggles visibility. This is what the eventual main
 *    AppShell wires up.
 *  - When `forceVisible` is true the panel is always rendered — used by the
 *    detached `/action-window` route.
 */

import { Wrench } from "lucide-react";
import { useState } from "react";
import { ActionWindow, type ActionWindowProps } from "./ActionWindow";

export interface ActionWindowMountProps extends ActionWindowProps {
  /** When true, panel is always rendered with no toggle. */
  forceVisible?: boolean;
  /** Initial open state when forceVisible is false. */
  defaultOpen?: boolean;
}

export function ActionWindowMount({
  forceVisible = false,
  defaultOpen = false,
  ...rest
}: ActionWindowMountProps) {
  const [open, setOpen] = useState<boolean>(forceVisible || defaultOpen);

  if (forceVisible) {
    return <ActionWindow {...rest} />;
  }

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open Action Window"
          data-testid="action-window-toggle"
          className="fixed bottom-4 right-20 z-30 flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-semibold text-fg shadow-md hover:bg-surface2"
        >
          <Wrench size={14} />
          <span>Action Window</span>
        </button>
      )}
      {open && (
        <div
          data-testid="action-window-floating"
          className="fixed bottom-4 right-4 z-30"
        >
          <ActionWindow {...rest} onClose={() => setOpen(false)} />
        </div>
      )}
    </>
  );
}
