/**
 * TaskMonitorMount — floating toggle button + drawer host. Kept separate so
 * the AppShell can mount this once (via W6-3's eventual integration) without
 * pulling in dispatcher details.
 *
 * The drawer is rendered un-conditionally so its slide-out transition runs;
 * `open` toggles the `translate-x` class inside the drawer.
 */

import { ListTree } from "lucide-react";
import { useState } from "react";
import {
  TaskMonitorDrawer,
  type TaskMonitorDrawerProps,
} from "./TaskMonitorDrawer";

export interface TaskMonitorMountProps extends Partial<TaskMonitorDrawerProps> {
  /** Initial open state. Default false. */
  defaultOpen?: boolean;
}

export function TaskMonitorMount({ defaultOpen = false, ...drawerProps }: TaskMonitorMountProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Toggle Task Monitor"
        aria-expanded={open}
        data-testid="task-monitor-toggle"
        className="fixed bottom-4 right-4 z-40 flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-semibold text-fg shadow-md hover:bg-surface2"
      >
        <ListTree size={14} />
        <span>Task Monitor</span>
      </button>
      <TaskMonitorDrawer
        {...drawerProps}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
