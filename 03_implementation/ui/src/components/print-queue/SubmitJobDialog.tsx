/**
 * Submit Job dialog for the Print Queue tab.
 *
 * Background: the W17-NEW-A5 audit confirmed that `#print_queue` had only
 * Refresh + Pause controls and no upstream surface emitting a real job
 * into the queue. This dialog wires the missing "submit job" control to
 * `POST /api/jobs`, the FastAPI route exposed by
 * `hermes3d.api.routes.jobs.create_job`.
 *
 * Design constraints (from the W17-NEW-A5 follow-up brief):
 *   1. NO fake job creation. The dialog defaults `dry_run=true` so the
 *      backend records a planning row and never commands a physical
 *      printer until the operator explicitly disables the flag.
 *   2. The printer dropdown is populated from `/api/printers`. If the
 *      list is empty the operator can still submit an unassigned
 *      planning row — the backend allows `printer_id=null`.
 *   3. The submit handler propagates the backend error string verbatim
 *      (including 503 / 423 policy gates from `_check_printer_policy`)
 *      so operators see honest failure reasons, not a generic toast.
 *
 * References:
 *   - React modal/dialog pattern: https://react.dev/reference/react-dom/createPortal
 *     (we use a centered fixed overlay div rather than a portal because
 *     the test harness uses jsdom and the existing tabs follow the same
 *     overlay pattern — see Approvals, OnboardingModal).
 *   - FastAPI POST handler conventions: https://fastapi.tiangolo.com/tutorial/body/
 *     The backend accepts `{name, type|job_type, printer_id, dry_run}`
 *     and returns the row with the persisted `id` + `status='queued'`.
 */

import { useCallback, useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { jobsClient, type JobsEnqueueResult } from "../../api/hermes3dClient";
import type { Printer } from "../../types/printer";

export interface SubmitJobDialogProps {
  /** Available printers; usually the same list the queue already loaded. */
  printers: Printer[];
  /** Called with the persisted job row after a successful submission. */
  onSubmitted: (job: JobsEnqueueResult) => void;
  /** Called when the operator cancels or closes the dialog. */
  onClose: () => void;
}

export function SubmitJobDialog({
  printers,
  onSubmitted,
  onClose,
}: SubmitJobDialogProps) {
  const [name, setName] = useState("");
  const [jobType, setJobType] = useState("print");
  const [printerId, setPrinterId] = useState<string>("");
  const [dryRun, setDryRun] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Esc closes the dialog. Matches the existing OnboardingModal UX.
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose, submitting]);

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setError(null);
      setSubmitting(true);
      try {
        const job = await jobsClient.enqueue({
          name: name.trim() || undefined,
          job_type: jobType.trim() || "print",
          printer_id: printerId.trim() || null,
          dry_run: dryRun,
        });
        onSubmitted(job);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to enqueue job.");
      } finally {
        setSubmitting(false);
      }
    },
    [name, jobType, printerId, dryRun, onSubmitted],
  );

  return (
    <div
      data-testid="submit-job-dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="submit-job-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose();
      }}
    >
      <div
        data-testid="submit-job-dialog"
        className="w-full max-w-md rounded border border-border bg-surface p-4 shadow-lg"
      >
        <div className="flex items-center justify-between gap-2">
          <h3
            id="submit-job-dialog-title"
            className="text-sm font-semibold text-fg"
          >
            Submit Job to Print Queue
          </h3>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close dialog"
            data-testid="submit-job-dialog-close"
            className="rounded p-1 text-muted hover:text-fg disabled:opacity-50"
          >
            <X size={14} />
          </button>
        </div>
        <p className="mt-1 text-[11px] text-muted">
          POST <code className="font-mono">/api/jobs</code> with{" "}
          <code className="font-mono">dry_run=true</code> by default; toggle
          off only when you intend to command a physical printer.
        </p>

        <form
          className="mt-3 flex flex-col gap-3"
          onSubmit={handleSubmit}
          data-testid="submit-job-dialog-form"
        >
          <label className="flex flex-col gap-1 text-xs text-muted">
            Job name
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. dimensional-calibration-T1A"
              data-testid="submit-job-dialog-name"
              disabled={submitting}
              className="rounded border border-border bg-bg/40 px-2 py-1 text-xs text-fg outline-none focus:border-accent-cyan/60 disabled:opacity-50"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-muted">
            Job type
            <select
              value={jobType}
              onChange={(event) => setJobType(event.target.value)}
              data-testid="submit-job-dialog-type"
              disabled={submitting}
              className="rounded border border-border bg-bg/40 px-2 py-1 text-xs text-fg outline-none focus:border-accent-cyan/60 disabled:opacity-50"
            >
              <option value="print">print (full slice + dispatch)</option>
              <option value="slice">slice (slice only, no print)</option>
              <option value="calibration">calibration</option>
              <option value="dimensional_qc">dimensional_qc</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs text-muted">
            Printer
            <select
              value={printerId}
              onChange={(event) => setPrinterId(event.target.value)}
              data-testid="submit-job-dialog-printer"
              disabled={submitting}
              className="rounded border border-border bg-bg/40 px-2 py-1 text-xs text-fg outline-none focus:border-accent-cyan/60 disabled:opacity-50"
            >
              <option value="">— unassigned (planning row only) —</option>
              {printers.map((printer) => (
                <option key={printer.id} value={printer.id}>
                  {printer.name} ({printer.id})
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(event) => setDryRun(event.target.checked)}
              data-testid="submit-job-dialog-dry-run"
              disabled={submitting}
            />
            Dry-run (no physical motion; backend records a planning row only)
          </label>

          {error && (
            <div
              role="alert"
              data-testid="submit-job-dialog-error"
              className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200"
            >
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              data-testid="submit-job-dialog-cancel"
              className="rounded border border-border px-3 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              data-testid="submit-job-dialog-submit"
              className="flex items-center gap-1.5 rounded border border-accent-cyan/40 bg-accent-cyan/10 px-3 py-1 text-[11px] text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-50"
            >
              {submitting && <Loader2 size={11} className="animate-spin" />}
              {submitting ? "Submitting..." : "Submit"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
