/**
 * useRecoveryRunsPoll — polls `GET /api/code-operator/recovery/runs` every
 * `intervalMs` (default 5s).
 *
 * Strategy:
 *  - Each poll uses an AbortController; on unmount we abort the in-flight
 *    request to avoid setState-after-unmount warnings.
 *  - On a 5xx (or transport failure that surfaces as RecoveryRunsFetchError
 *    with status 0/>=500), apply exponential backoff (capped at 60s) before
 *    the next poll. A successful poll resets the backoff to 0.
 *  - 4xx responses other than 404/405 are non-retryable and surfaced as
 *    `error` so the UI can show the cause.
 *
 * Reference:
 *  - https://tanstack.com/query/latest — same shape as TanStack Query's
 *    `refetchInterval`/`backoff`. We don't depend on TanStack to keep the
 *    bundle lean, but the semantics match.
 */

import { useEffect, useRef, useState } from "react";
import {
  RecoveryRunsFetchError,
  emptyRunsResponse,
  fetchRecoveryRuns,
  type FetchRecoveryRunsOptions,
  type RecoveryRunsResponse,
} from "../../api/recoveryRuns";

export interface UseRecoveryRunsPollOptions {
  /** Set to false to pause polling — used when the drawer is closed. */
  enabled?: boolean;
  /** Poll interval in ms. Default 5000. */
  intervalMs?: number;
  /** Optional task_id filter. */
  taskId?: string;
  /** Override fetcher — used by tests. */
  fetchRunsImpl?: typeof fetchRecoveryRuns;
}

export interface UseRecoveryRunsPollResult {
  data: RecoveryRunsResponse;
  loading: boolean;
  error: string | null;
  /** Number of successful polls — handy for tests. */
  successCount: number;
  /** Current backoff multiplier (0 = healthy). */
  backoffStep: number;
  refetch: () => void;
}

const DEFAULT_INTERVAL_MS = 5_000;
const MAX_BACKOFF_MS = 60_000;

export function nextBackoffMs(step: number, baseIntervalMs: number): number {
  if (step <= 0) return baseIntervalMs;
  // 2^step * base, capped at MAX_BACKOFF_MS.
  const exp = Math.pow(2, Math.min(step, 6));
  return Math.min(baseIntervalMs * exp, MAX_BACKOFF_MS);
}

/**
 * Decide whether a fetch error should trigger backoff (5xx / transport) or be
 * surfaced as a hard error (4xx). Pure for unit testing.
 */
export function classifyError(err: unknown): "retry" | "fatal" {
  if (err instanceof RecoveryRunsFetchError) {
    if (err.status === 0) return "retry";
    if (err.status >= 500) return "retry";
    return "fatal";
  }
  if (err instanceof DOMException && err.name === "AbortError") {
    return "retry";
  }
  return "retry";
}

export function useRecoveryRunsPoll(
  options: UseRecoveryRunsPollOptions = {},
): UseRecoveryRunsPollResult {
  const enabled = options.enabled ?? true;
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  const fetchImpl = options.fetchRunsImpl ?? fetchRecoveryRuns;
  const taskId = options.taskId;

  const [data, setData] = useState<RecoveryRunsResponse>(() => emptyRunsResponse());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successCount, setSuccessCount] = useState(0);
  const [backoffStep, setBackoffStep] = useState(0);
  const [tick, setTick] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);

    const opts: FetchRecoveryRunsOptions = {
      signal: controller.signal,
      taskId,
    };
    fetchImpl(opts)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setError(null);
        setSuccessCount((n) => n + 1);
        setBackoffStep(0);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        const classification = classifyError(err);
        const message = err instanceof Error ? err.message : String(err);
        if (classification === "retry") {
          setBackoffStep((step) => Math.min(step + 1, 6));
          setError(null);
        } else {
          setError(message);
        }
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
        const delay = nextBackoffMs(backoffStep, intervalMs);
        if (typeof window !== "undefined") {
          timerRef.current = window.setTimeout(() => {
            setTick((n) => n + 1);
          }, delay);
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
      if (timerRef.current !== null && typeof window !== "undefined") {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
    // backoffStep is intentionally read from state at fire time but not
    // included in deps — tick changes trigger the next fetch which reads it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, taskId, tick, fetchImpl]);

  const refetch = () => setTick((n) => n + 1);

  return { data, loading, error, successCount, backoffStep, refetch };
}
