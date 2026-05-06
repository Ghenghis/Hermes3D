import { useEffect, useState } from "react";
import { adapters } from "../api/adapters";
import { useStore } from "../app/store";
import type { Approval } from "../types/approval";

export function ApprovalsTab() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [pending, setPending] = useState<Approval[]>([]);
  const [history, setHistory] = useState<Approval[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = () => {
    void adapters.getPendingApprovals().then(async (next) => {
      setPending(next);
      await adapters.emitProofEvent("approvals.pending.loaded", { pending_count: next.length });
    });
    void adapters.getApprovalHistory().then(setHistory);
  };

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 15_000);
    return () => window.clearInterval(timer);
  }, []);

  const approve = async (approval: Approval) => {
    const notes = window.prompt(`Approve ${approval.approvalType} for ${approval.jobTitle}?`, "");
    if (notes == null) {
      setActionMessage(`Approval cancelled for ${approval.id}.`);
      return;
    }
    try {
      await adapters.approveApproval(approval.id, notes);
      await adapters.emitProofEvent("approvals.approval.approved", { approval_id: approval.id, accepted: true });
      setActionMessage(`Approved ${approval.id}.`);
      load();
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
    }
  };

  const reject = async (approval: Approval) => {
    const reason = window.prompt(`Reject ${approval.approvalType} for ${approval.jobTitle}?`, "");
    if (!reason) {
      return;
    }
    try {
      await adapters.rejectApproval(approval.id, reason);
      await adapters.emitProofEvent("approvals.approval.rejected", { approval_id: approval.id, accepted: true });
      setActionMessage(`Rejected ${approval.id}.`);
      load();
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
    }
  };

  return (
    <div data-testid="approvals-root" className="grid min-h-[calc(100vh-6.5rem)] grid-rows-[minmax(0,1.1fr)_minmax(0,1fr)] gap-3">
      <section id="approvals.pending" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-fg">PENDING APPROVALS</h2>
          <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{pending.length}</span>
        </div>
        {actionMessage && <div className="mt-3 rounded border border-border bg-bg/40 p-2 text-xs text-muted">{actionMessage}</div>}
        <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto md:grid-cols-2">
          {pending.map((approval) => (
            <div key={approval.id} className="rounded border border-border bg-bg/40 p-3">
              <span className="rounded bg-amber-900/50 px-2 py-1 text-xs text-amber-200">{approval.approvalType}</span>
              <h3 className="mt-2 font-medium text-fg">{approval.jobTitle}</h3>
              <p className="text-xs text-muted">Requested {new Date(approval.createdAt).toLocaleString()}</p>
              <button type="button" onClick={() => setActiveTabId("artifacts")} className="mt-2 text-xs text-accent-cyan">Evidence summary</button>
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={() => void approve(approval)} className="rounded bg-green-800 px-3 py-1 text-sm text-green-100">Approve</button>
                <button type="button" onClick={() => void reject(approval)} className="rounded bg-red-900 px-3 py-1 text-sm text-red-100">Reject</button>
              </div>
            </div>
          ))}
          {pending.length === 0 && (
            <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted md:col-span-2">
              No pending approvals returned by the live approvals API.
            </div>
          )}
        </div>
      </section>
      <section id="approvals.history" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4">
        <h2 className="text-base font-semibold text-fg">APPROVAL HISTORY</h2>
        <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
          {history.map((approval) => (
            <div key={approval.id} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded border border-border bg-bg/40 p-2 text-sm">
              <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{approval.approvalType}</span>
              <span className="truncate text-fg">{approval.jobTitle}</span>
              <span className={`rounded px-2 py-1 text-xs ${approval.status === "approved" ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>{approval.status.toUpperCase()}</span>
            </div>
          ))}
          {history.length === 0 && <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted">No approval history returned by the live approvals API.</div>}
        </div>
      </section>
    </div>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the approval action.";
}
