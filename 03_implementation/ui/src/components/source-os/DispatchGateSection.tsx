import { Lock } from "lucide-react";
import type { DispatchGate } from "../../types/source-os";

export function DispatchGateSection({
  gates,
  disabled,
}: {
  gates: DispatchGate[];
  disabled: boolean;
}) {
  return (
    <section className="relative rounded border border-border bg-surface2/30 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
        Dispatch Gate
      </h3>
      <div className={disabled ? "opacity-50 pointer-events-none" : ""}>
        {gates.length === 0 ? (
          <div className="rounded border border-border bg-bg/40 px-2 py-2 text-xs text-muted">
            No real dispatch gate endpoint is connected for this source module.
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {gates.map((gate) => (
            <li key={gate.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 rounded bg-bg/40 px-2 py-1.5 text-xs">
              <div className="min-w-0">
                <div className="truncate font-mono text-fg">{gate.id}</div>
                <div className="text-[10px] text-muted">Approver: {gate.current_approver ?? "unassigned"}</div>
              </div>
              <span className="rounded bg-surface2 px-2 py-0.5 text-[10px] text-muted">
                {gate.required_approvals} approvals
              </span>
              <span className="flex gap-1">
                <button
                  type="button"
                  disabled
                  title="Approval wiring is owned by the Approvals tab"
                  className="rounded border border-border px-2 py-0.5 text-[10px] text-muted disabled:cursor-not-allowed"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled
                  title="Approval wiring is owned by the Approvals tab"
                  className="rounded border border-border px-2 py-0.5 text-[10px] text-muted disabled:cursor-not-allowed"
                >
                  Reject
                </button>
              </span>
            </li>
            ))}
          </ul>
        )}
      </div>
      {disabled && (
        <div className="absolute inset-0 flex items-center justify-center rounded bg-bg/30">
          <div className="inline-flex items-center gap-2 rounded border border-border bg-surface px-3 py-1.5 text-xs text-muted">
            <Lock size={13} />
            Install or detect module first
          </div>
        </div>
      )}
    </section>
  );
}
