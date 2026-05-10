/**
 * Approvals tab — pending + history queue (W8-2 GUI breadth pages).
 *
 * Surfaces:
 *   - Pending approvals from `GET /api/approvals?status=pending` (matches
 *     `hermes_request_handoff` / `hermes_list_pending_tasks` MCP shape).
 *   - Each row shows requester, file scope, requested-at timestamp, and
 *     three actions: Approve, Deny (Reject), Defer.
 *   - Approval history list below.
 *
 * Polling cadence:
 *   - Refreshes every 5s by default to keep the queue lively. Tests can
 *     pass `pollIntervalMs={0}` (consumed by the underlying hook helper)
 *     to disable polling — but at the tab level we expose a single test
 *     seam via `__TEST_POLL_INTERVAL_MS__` window override so tests don't
 *     have to refactor the tab signature.
 *
 * Sources consulted:
 *   - WAI-ARIA APG, "Feed" pattern · https://www.w3.org/WAI/ARIA/apg/patterns/feed/
 *     for the live-updating list role + aria-busy semantics.
 *   - React Router DOM "Working with the URL"
 *     https://reactrouter.com/en/main/start/concepts (we use hash routing,
 *     not react-router; the existing AppShell convention).
 */
import { useEffect, useState } from "react";
import { adapters } from "../api/adapters";
import { useStore } from "../app/store";
import { ApprovalQueue } from "../components/approvals/ApprovalQueue";
import type { ApprovalActionKind, ApprovalFormState } from "../components/approvals/ApprovalRow";
import type { Approval } from "../types/approval";

const DEFAULT_POLL_MS = 5_000;

type ActionKind = ApprovalActionKind;

type PendingFormState = ApprovalFormState;

declare global {
  interface Window {
    __HERMES_APPROVALS_POLL_MS__?: number;
  }
}

export function ApprovalsTab() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [pending, setPending] = useState<Approval[]>([]);
  const [history, setHistory] = useState<Approval[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [openForm, setOpenForm] = useState<PendingFormState | null>(null);

  const load = () => {
    void adapters.getPendingApprovals().then(async (next) => {
      setPending(next);
      await adapters.emitProofEvent("approvals.pending.loaded", { pending_count: next.length });
    });
    void adapters.getApprovalHistory().then(setHistory);
  };

  useEffect(() => {
    load();
    const intervalMs =
      typeof window !== "undefined" && typeof window.__HERMES_APPROVALS_POLL_MS__ === "number"
        ? window.__HERMES_APPROVALS_POLL_MS__
        : DEFAULT_POLL_MS;
    if (intervalMs <= 0) return;
    const timer = window.setInterval(load, intervalMs);
    return () => window.clearInterval(timer);
  }, []);

  const submit = async (approval: Approval, kind: ActionKind, value: string) => {
    try {
      if (kind === "approve") {
        await adapters.approveApproval(approval.id, value);
        await adapters.emitProofEvent("approvals.approval.approved", {
          approval_id: approval.id,
          accepted: true,
        });
        setActionMessage(`Approved ${approval.id}.`);
      } else if (kind === "reject") {
        if (!value) {
          setActionMessage(`Rejection requires a reason.`);
          return;
        }
        await adapters.rejectApproval(approval.id, value);
        await adapters.emitProofEvent("approvals.approval.rejected", {
          approval_id: approval.id,
          accepted: true,
        });
        setActionMessage(`Rejected ${approval.id}.`);
      } else {
        if (!value) {
          setActionMessage(`Defer requires a reason.`);
          return;
        }
        await adapters.deferApproval(approval.id, value);
        await adapters.emitProofEvent("approvals.approval.deferred", {
          approval_id: approval.id,
          accepted: true,
        });
        setActionMessage(`Deferred ${approval.id}.`);
      }
      setOpenForm(null);
      load();
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
    }
  };

  return (
    <div
      data-testid="approvals-root"
      className="grid min-h-[calc(100vh-6.5rem)] grid-rows-[minmax(0,1.1fr)_minmax(0,1fr)] gap-3"
    >
      <section
        id="approvals.pending"
        className="flex min-h-0 flex-col rounded border border-border bg-surface p-4"
        aria-label="Pending approvals"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-fg">PENDING APPROVALS</h2>
          <span
            data-testid="approvals-pending-count"
            className="rounded bg-surface2 px-2 py-1 text-xs text-muted"
          >
            {pending.length}
          </span>
        </div>
        {actionMessage && (
          <div
            role="status"
            data-testid="approvals-action-message"
            className="mt-3 rounded border border-border bg-bg/40 p-2 text-xs text-muted"
          >
            {actionMessage}
          </div>
        )}
        <ApprovalQueue
          pending={pending}
          openForm={openForm}
          onOpenForm={setOpenForm}
          onCloseForm={() => setOpenForm(null)}
          onFormValueChange={(value) =>
            setOpenForm(openForm ? { ...openForm, value } : null)
          }
          onSubmit={(approval, kind, value) => submit(approval, kind, value)}
          onEvidenceSummary={() => setActiveTabId("artifacts")}
        />
      </section>
      <section
        id="approvals.history"
        className="flex min-h-0 flex-col rounded border border-border bg-surface p-4"
        aria-label="Approval history"
      >
        <h2 className="text-base font-semibold text-fg">APPROVAL HISTORY</h2>
        <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
          {history.map((approval) => (
            <div
              key={approval.id}
              data-testid={`approvals-history-${approval.id}`}
              className="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded border border-border bg-bg/40 p-2 text-sm"
            >
              <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{approval.approvalType}</span>
              <span className="truncate text-fg">{approval.jobTitle}</span>
              <span
                className={`rounded px-2 py-1 text-xs ${
                  approval.status === "approved"
                    ? "bg-green-900/50 text-green-300"
                    : approval.status === "deferred"
                      ? "bg-amber-900/50 text-amber-300"
                      : "bg-red-900/50 text-red-300"
                }`}
              >
                {approval.status.toUpperCase()}
              </span>
            </div>
          ))}
          {history.length === 0 && (
            <div className="rounded border border-border bg-bg/40 p-3 text-sm text-muted">
              No approval history returned by the live approvals API.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the approval action.";
}
