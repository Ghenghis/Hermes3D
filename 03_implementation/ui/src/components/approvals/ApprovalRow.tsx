/**
 * ApprovalRow — single pending approval card with [Approve][Deny][Defer]
 * action buttons + inline form for the reason/notes input.
 *
 * Pure presentation; receives an Approval + decision callbacks. Lifted out
 * of `tabs/Approvals.tsx` (Wave 15 / Agent 16) for reuse and testability.
 *
 * Sources consulted:
 *   - GitHub Pull Request review button conventions:
 *     https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews
 *   - WAI-ARIA APG "Disclosure" pattern (for inline expand-on-action form):
 *     https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/
 */
import type { Approval } from "../../types/approval";

export type ApprovalActionKind = "approve" | "reject" | "defer";

export interface ApprovalFormState {
  id: string;
  kind: ApprovalActionKind;
  value: string;
}

interface ApprovalRowProps {
  approval: Approval;
  openForm: ApprovalFormState | null;
  onOpenForm: (state: ApprovalFormState) => void;
  onCloseForm: () => void;
  onFormValueChange: (value: string) => void;
  onSubmit: (approval: Approval, kind: ApprovalActionKind, value: string) => void | Promise<void>;
  onEvidenceSummary: () => void;
}

export function ApprovalRow({
  approval,
  openForm,
  onOpenForm,
  onCloseForm,
  onFormValueChange,
  onSubmit,
  onEvidenceSummary,
}: ApprovalRowProps) {
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
          <dd className="font-mono text-fg/90">{approval.requester ?? "-"}</dd>
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
        onClick={onEvidenceSummary}
        className="mt-2 text-xs text-accent-cyan"
      >
        Evidence summary
      </button>
      {!formOpen && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onOpenForm({ id: approval.id, kind: "approve", value: "" })}
            data-testid={`approvals-action-approve-${approval.id}`}
            className="rounded bg-green-800 px-3 py-1 text-sm text-green-100 hover:bg-green-700"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => onOpenForm({ id: approval.id, kind: "reject", value: "" })}
            data-testid={`approvals-action-deny-${approval.id}`}
            className="rounded bg-red-900 px-3 py-1 text-sm text-red-100 hover:bg-red-800"
          >
            Deny
          </button>
          <button
            type="button"
            onClick={() => onOpenForm({ id: approval.id, kind: "defer", value: "" })}
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
            void onSubmit(approval, openForm.kind, openForm.value);
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
            onChange={(e) => onFormValueChange(e.target.value)}
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
              onClick={onCloseForm}
              className="rounded border border-border px-3 py-1 text-xs text-muted hover:text-fg"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </article>
  );
}
