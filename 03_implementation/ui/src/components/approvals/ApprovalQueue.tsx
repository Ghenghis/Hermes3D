/**
 * ApprovalQueue — feed-style list of pending approvals. Renders ApprovalRow
 * per item, falls back to an honest "no pending approvals returned" empty
 * state when the live `/api/approvals?status=pending` endpoint returns 0
 * rows. Never synthesizes fake rows.
 *
 * Sources consulted:
 *   - WAI-ARIA APG "Feed" pattern · https://www.w3.org/WAI/ARIA/apg/patterns/feed/
 *   - GitHub PR queue grid conventions:
 *     https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/grouping-issues-and-pull-requests
 */
import type { Approval } from "../../types/approval";
import { ApprovalRow, type ApprovalActionKind, type ApprovalFormState } from "./ApprovalRow";

interface ApprovalQueueProps {
  pending: Approval[];
  openForm: ApprovalFormState | null;
  onOpenForm: (state: ApprovalFormState) => void;
  onCloseForm: () => void;
  onFormValueChange: (value: string) => void;
  onSubmit: (approval: Approval, kind: ApprovalActionKind, value: string) => void | Promise<void>;
  onEvidenceSummary: () => void;
}

export function ApprovalQueue({
  pending,
  openForm,
  onOpenForm,
  onCloseForm,
  onFormValueChange,
  onSubmit,
  onEvidenceSummary,
}: ApprovalQueueProps) {
  return (
    <div
      role="feed"
      aria-busy="false"
      aria-label="Pending approvals feed"
      className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto md:grid-cols-2"
    >
      {pending.map((approval) => (
        <ApprovalRow
          key={approval.id}
          approval={approval}
          openForm={openForm}
          onOpenForm={onOpenForm}
          onCloseForm={onCloseForm}
          onFormValueChange={onFormValueChange}
          onSubmit={onSubmit}
          onEvidenceSummary={onEvidenceSummary}
        />
      ))}
      {pending.length === 0 && (
        <div
          data-testid="approvals-pending-empty"
          className="rounded border border-border bg-bg/40 p-3 text-sm text-muted md:col-span-2"
        >
          No pending approvals returned by the live approvals API.
        </div>
      )}
    </div>
  );
}
