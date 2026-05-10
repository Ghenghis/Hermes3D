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
import type { Approval } from "../types/approval";

const DEFAULT_POLL_MS = 5_000;

type ActionKind = "approve" | "reject" | "defer";

interface PendingFormState {
  id: string;
  kind: ActionKind;
  value: string;
}

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
        <div
          role="feed"
          aria-busy="false"
          aria-label="Pending approvals feed"
          className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto md:grid-cols-2"
        >
          {pending.map((approval) => {
            const formOpen = openForm?.id === approval.id;
            const fileScope = approval.fileScope ?? [];
            return (
              <article
                key={approval.id}
                data-testid={`approvals-pending-${approval.id}`}
                className="rounded border border-border bg-bg/40 p-3"
                aria-labelledby={`approval-${approval.id}-title`}
              >
                <span className="rounded bg-amber-900/50 px-2 py-1 text-xs text-amber-200">
                  {approval.approvalType}
                </span>
                <h3
                  id={`approval-${approval.id}-title`}
                  className="mt-2 font-medium text-fg"
                >
                  {approval.jobTitle}
                </h3>
                <dl className="mt-1 grid grid-cols-1 gap-0.5 text-[11px] text-muted">
                  <div className="flex gap-1">
                    <dt className="text-[10px] uppercase">Requester</dt>
                    <dd className="font-mono text-fg/90">{approval.requester ?? "—"}</dd>
                  </div>
                  <div className="flex gap-1">
                    <dt className="text-[10px] uppercase">Requested</dt>
                    <dd>{new Date(approval.createdAt).toLocaleString()}</dd>
                  </div>
                </dl>
                {fileScope.length > 0 && (
                  <details className="mt-2 text-[11px]" data-testid={`approvals-file-scope-${approval.id}`}>
                    <summary className="cursor-pointer text-muted">
                      File scope · {fileScope.length} {fileScope.length === 1 ? "file" : "files"}
                    </summary>
                    <ul className="mt-1 max-h-28 overflow-auto rounded bg-bg/40 p-1 font-mono text-[10px] text-fg/90">
                      {fileScope.map((path) => (
                        <li key={path} className="truncate" title={path}>
                          {path}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                <button
                  type="button"
                  onClick={() => setActiveTabId("artifacts")}
                  className="mt-2 text-xs text-accent-cyan"
                >
                  Evidence summary
                </button>
                {!formOpen && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setOpenForm({ id: approval.id, kind: "approve", value: "" })}
                      data-testid={`approvals-action-approve-${approval.id}`}
                      className="rounded bg-green-800 px-3 py-1 text-sm text-green-100 hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenForm({ id: approval.id, kind: "reject", value: "" })}
                      data-testid={`approvals-action-deny-${approval.id}`}
                      className="rounded bg-red-900 px-3 py-1 text-sm text-red-100 hover:bg-red-800"
                    >
                      Deny
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenForm({ id: approval.id, kind: "defer", value: "" })}
                      data-testid={`approvals-action-defer-${approval.id}`}
                      className="rounded bg-amber-900 px-3 py-1 text-sm text-amber-100 hover:bg-amber-800"
                    >
                      Defer
                    </button>
                  </div>
                )}
                {formOpen && openForm && (
                  <form
                    className="mt-3 flex flex-col gap-2"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void submit(approval, openForm.kind, openForm.value);
                    }}
                  >
                    <label className="text-[11px] text-muted" htmlFor={`approvals-input-${approval.id}`}>
                      {openForm.kind === "approve"
                        ? "Optional notes:"
                        : openForm.kind === "defer"
                          ? "Reason for deferral:"
                          : "Reason for denial:"}
                    </label>
                    <input
                      id={`approvals-input-${approval.id}`}
                      data-testid={`approvals-input-${approval.id}`}
                      type="text"
                      value={openForm.value}
                      onChange={(e) =>
                        setOpenForm({ ...openForm, value: e.target.value })
                      }
                      autoFocus
                      className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg"
                    />
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        data-testid={`approvals-submit-${approval.id}`}
                        className="rounded bg-surface2 px-3 py-1 text-xs text-fg hover:bg-surface2/80"
                      >
                        Confirm {openForm.kind}
                      </button>
                      <button
                        type="button"
                        onClick={() => setOpenForm(null)}
                        className="rounded border border-border px-3 py-1 text-xs text-muted hover:text-fg"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </article>
            );
          })}
          {pending.length === 0 && (
            <div
              data-testid="approvals-pending-empty"
              className="rounded border border-border bg-bg/40 p-3 text-sm text-muted md:col-span-2"
            >
              No pending approvals returned by the live approvals API.
            </div>
          )}
        </div>
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
