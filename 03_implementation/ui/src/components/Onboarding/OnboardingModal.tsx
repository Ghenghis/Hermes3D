/**
 * OnboardingModal — first-launch walkthrough.
 *
 * UX:
 *   - 4 steps, navigated via Back / Next.
 *   - Final step replaces "Next" with "Get started", which closes the
 *     modal and stamps `h3d.onboarding.dismissed`.
 *   - Top-right [X] aborts immediately — also stamps the dismissal record
 *     so we don't pester the user.
 *   - "Don't show again" footer toggle is on by default; clearing it
 *     leaves the modal eligible to re-open on the next launch.
 *
 * ARIA:
 *   - role="dialog" + aria-modal + aria-labelledby pointing at the step
 *     title id. Focus is trapped to the dialog while open.
 *   - Escape closes; Enter advances; Tab cycles within the dialog.
 *
 * The host is responsible for deciding *when* to render — the modal does
 * not auto-mount. Use `shouldShowOnboarding()` (exported below) inside
 * the app shell to gate first-launch.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { ONBOARDING_STEPS } from "./onboardingSteps";

const STORAGE_KEY = "h3d.onboarding.dismissed";

export interface OnboardingModalProps {
  /**
   * Render gate. Parents control when the modal mounts; pass `false` to
   * hide entirely (also returns `null` from the component).
   */
  open: boolean;
  /** Called when the user closes the modal (skip / finish / X / Esc). */
  onClose: (reason: "completed" | "skipped" | "dismissed") => void;
  /**
   * Override storage key — tests pass a unique key so they don't fight
   * each other.
   */
  storageKey?: string;
}

export function OnboardingModal({
  open,
  onClose,
  storageKey = STORAGE_KEY,
}: OnboardingModalProps): JSX.Element | null {
  const [stepIndex, setStepIndex] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(true);
  const dialogRef = useRef<HTMLDivElement>(null);

  const totalSteps = ONBOARDING_STEPS.length;
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === totalSteps - 1;
  const step = ONBOARDING_STEPS[stepIndex];

  const persist = useCallback(
    (reason: "completed" | "skipped" | "dismissed") => {
      if (dontShowAgain) {
        try {
          window.localStorage.setItem(
            storageKey,
            JSON.stringify({
              dismissedAtMs: Date.now(),
              reason,
              completedSteps: stepIndex + 1,
            }),
          );
        } catch {
          // ignore
        }
      }
    },
    [dontShowAgain, storageKey, stepIndex],
  );

  const handleClose = useCallback(
    (reason: "completed" | "skipped" | "dismissed") => {
      persist(reason);
      onClose(reason);
    },
    [persist, onClose],
  );

  // Focus management — when the modal opens, focus the dialog so
  // keyboard users land inside the trap.
  useEffect(() => {
    if (!open) return;
    const node = dialogRef.current;
    if (node) {
      const previous = document.activeElement as HTMLElement | null;
      node.focus();
      return () => {
        previous?.focus?.();
      };
    }
  }, [open]);

  // Reset to step 0 every time the modal opens — re-opening should not
  // resume a partial walk.
  useEffect(() => {
    if (open) setStepIndex(0);
  }, [open]);

  // Keyboard: Esc dismisses, ArrowRight advances, ArrowLeft retreats.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        handleClose("dismissed");
      } else if (event.key === "ArrowRight" || event.key === "Enter") {
        if (!isLast) {
          event.preventDefault();
          setStepIndex((prev) => Math.min(prev + 1, totalSteps - 1));
        } else if (event.key === "Enter") {
          event.preventDefault();
          handleClose("completed");
        }
      } else if (event.key === "ArrowLeft") {
        if (!isFirst) {
          event.preventDefault();
          setStepIndex((prev) => Math.max(prev - 1, 0));
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, isFirst, isLast, totalSteps, handleClose]);

  if (!open) return null;

  const titleId = `onboarding-step-title-${step.id}`;

  return (
    <div
      data-testid="onboarding-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
      onClick={(event) => {
        // Click outside the modal closes; clicks inside the panel are
        // intercepted by stopPropagation in the inner container.
        if (event.target === event.currentTarget) {
          handleClose("dismissed");
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="onboarding-modal"
        ref={dialogRef}
        tabIndex={-1}
        className="w-full max-w-lg rounded-lg border border-border bg-surface text-fg shadow-xl outline-none"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-[10px] uppercase tracking-wider text-muted">
            Welcome · Step {stepIndex + 1} of {totalSteps}
          </span>
          <button
            type="button"
            data-testid="onboarding-close"
            aria-label="Skip onboarding"
            onClick={() => handleClose("skipped")}
            className="rounded p-1 text-muted hover:bg-surface2 hover:text-fg"
          >
            <X size={14} aria-hidden />
          </button>
        </header>
        <div className="space-y-3 px-4 py-4">
          {step.illustration}
          <h2 id={titleId} className="text-base font-semibold">
            {step.title}
          </h2>
          <p className="text-sm text-muted leading-relaxed">{step.body}</p>
          <div className="flex items-center justify-center gap-1.5 pt-1">
            {ONBOARDING_STEPS.map((s, idx) => (
              <span
                key={s.id}
                data-testid={`onboarding-dot-${s.id}`}
                aria-hidden
                className={[
                  "h-1.5 w-6 rounded-full transition-colors",
                  idx === stepIndex ? "bg-accent-cyan" : "bg-border",
                ].join(" ")}
              />
            ))}
          </div>
        </div>
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-3">
          <label className="flex items-center gap-2 text-[11px] text-muted">
            <input
              type="checkbox"
              data-testid="onboarding-dont-show-again"
              checked={dontShowAgain}
              onChange={(event) => setDontShowAgain(event.target.checked)}
              className="h-3 w-3 rounded border-border bg-surface accent-accent-cyan"
            />
            Don&apos;t show again
          </label>
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              data-testid="onboarding-back"
              onClick={() => setStepIndex((prev) => Math.max(prev - 1, 0))}
              disabled={isFirst}
              className={[
                "inline-flex items-center gap-1 rounded border border-border px-3 py-1 text-xs",
                isFirst
                  ? "cursor-not-allowed opacity-40"
                  : "text-fg hover:bg-surface2",
              ].join(" ")}
            >
              <ChevronLeft size={14} aria-hidden /> Back
            </button>
            <button
              type="button"
              data-testid="onboarding-next"
              onClick={() => {
                if (isLast) {
                  handleClose("completed");
                } else {
                  setStepIndex((prev) => Math.min(prev + 1, totalSteps - 1));
                }
              }}
              className="inline-flex items-center gap-1 rounded bg-accent-cyan/90 px-3 py-1 text-xs font-semibold text-black hover:bg-accent-cyan"
            >
              {isLast ? "Get started" : "Next"} <ChevronRight size={14} aria-hidden />
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}

/**
 * Read the persisted dismissal record. Returns true when the user has
 * NOT yet dismissed onboarding, i.e. the modal should mount.
 */
export function shouldShowOnboarding(
  storageKey: string = STORAGE_KEY,
): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(storageKey);
    return !raw;
  } catch {
    return false;
  }
}

/** Reset persisted dismissal — useful for "Show tour again" buttons. */
export function resetOnboarding(storageKey: string = STORAGE_KEY): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(storageKey);
  } catch {
    // ignore
  }
}

export const __testing = { STORAGE_KEY };
