import type { BridgeTask } from "../../types/source-os";

const STATUS_CLASS: Record<BridgeTask["status"], string> = {
  pending: "bg-surface2 text-muted",
  running: "bg-cyan-800/60 text-cyan-200 animate-pulse",
  pass: "bg-green-800/60 text-green-200",
  fail: "bg-red-800/60 text-red-200",
  skipped: "bg-surface2 text-muted",
};

export function BridgeTasks({
  tasks,
  moduleId,
  onRun,
}: {
  tasks: BridgeTask[];
  moduleId: string;
  onRun: (taskId: string) => void;
}) {
  return (
    <section className="rounded border border-border bg-surface2/30 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
        Bridge Tasks
      </h3>
      <ul className="flex flex-col gap-1.5">
        {tasks.map((task) => (
          <li key={task.id} className="flex items-center gap-2 rounded bg-bg/40 px-2 py-1.5 text-xs">
            <input
              type="checkbox"
              checked={task.status === "pass"}
              readOnly
              aria-label={`${task.name} status`}
              className="h-3.5 w-3.5 accent-accent-green"
            />
            <span className="min-w-0 flex-1 truncate text-fg">{task.name}</span>
            <span className={`rounded px-2 py-0.5 text-[10px] uppercase ${STATUS_CLASS[task.status]}`}>
              {task.status}
            </span>
            <button
              type="button"
              onClick={() => onRun(task.id)}
              disabled={task.status === "running" || task.status === "skipped"}
              title={
                task.status === "running"
                  ? "Task is already running"
                  : task.status === "skipped"
                    ? "No real bridge runner is configured for this source module"
                    : `Run ${task.name} for ${moduleId}`
              }
              className="rounded border border-border px-2 py-0.5 text-[10px] text-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-60"
            >
              {task.status === "skipped" ? "Blocked" : task.status === "fail" ? "Retry" : "Run"}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
