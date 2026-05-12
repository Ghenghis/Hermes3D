/**
 * Tiny React Query-shape primitives for Hermes3D-OS.
 *
 * Why not React Query? The UI bundle deliberately stays thin
 * (no react-query / swr / zustand-query) — see `package.json`. We replicate
 * the *signature* so future migration is a one-line swap.
 *
 *   const { data, error, isLoading, refetch } = useQuery({
 *     queryKey: "agents-status",
 *     queryFn: ({ signal }) => agentsClient.getUpdateStatus({ signal }),
 *     refetchInterval: 5_000,
 *   });
 *
 * Mutation shape:
 *
 *   const { mutate, isLoading, error, data } = useMutation({
 *     mutationFn: (vars) => agentsClient.stagedUpdate(vars),
 *   });
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface QueryOptions<T> {
  queryKey: string;
  queryFn: (ctx: { signal: AbortSignal }) => Promise<T>;
  /** Polling interval in ms. Omit for one-shot fetches. */
  refetchInterval?: number;
  /** Skip the initial fetch entirely (useful when args aren't ready). */
  enabled?: boolean;
}

export interface QueryResult<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isFetching: boolean;
  refetch: () => Promise<void>;
}

export function useQuery<T>(options: QueryOptions<T>): QueryResult<T> {
  const { queryKey, queryFn, refetchInterval, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(enabled);
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const queryFnRef = useRef(queryFn);
  queryFnRef.current = queryFn;
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const run = useCallback(async () => {
    if (!enabled) return;
    const controller = new AbortController();
    setIsFetching(true);
    try {
      const result = await queryFnRef.current({ signal: controller.signal });
      if (!mountedRef.current) return;
      setData(result);
      setError(null);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
        setIsFetching(false);
      }
    }
  }, [enabled]);

  // Initial fetch + polling.
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return undefined;
    }
    void run();
    if (!refetchInterval || refetchInterval <= 0) return undefined;
    const id = window.setInterval(() => {
      void run();
    }, refetchInterval);
    return () => window.clearInterval(id);
    // queryKey is the cache discriminator: change it -> refetch from scratch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey, refetchInterval, enabled]);

  return useMemo(
    () => ({
      data,
      error,
      isLoading,
      isFetching,
      refetch: run,
    }),
    [data, error, isLoading, isFetching, run],
  );
}

export interface MutationOptions<TVars, TResult> {
  mutationFn: (vars: TVars) => Promise<TResult>;
  onSuccess?: (result: TResult, vars: TVars) => void;
  onError?: (error: Error, vars: TVars) => void;
}

export interface MutationState<TVars, TResult> {
  data: TResult | null;
  error: Error | null;
  isLoading: boolean;
  mutate: (vars: TVars) => Promise<TResult | null>;
  reset: () => void;
}

export function useMutation<TVars, TResult>(
  options: MutationOptions<TVars, TResult>,
): MutationState<TVars, TResult> {
  const [data, setData] = useState<TResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const optsRef = useRef(options);
  optsRef.current = options;
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const mutate = useCallback(async (vars: TVars): Promise<TResult | null> => {
    setIsLoading(true);
    try {
      const result = await optsRef.current.mutationFn(vars);
      if (!mountedRef.current) return result;
      setData(result);
      setError(null);
      optsRef.current.onSuccess?.(result, vars);
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      if (mountedRef.current) {
        setError(e);
      }
      optsRef.current.onError?.(e, vars);
      return null;
    } finally {
      if (mountedRef.current) setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return useMemo(
    () => ({ data, error, isLoading, mutate, reset }),
    [data, error, isLoading, mutate, reset],
  );
}

/** Standard polling cadence for status panels (5 s). */
export const STATUS_POLL_MS = 5_000;

/**
 * Polling cadence for "background" data panels (15 s) — the Files,
 * Artifacts, Agents, Gen3D, Plugins tabs whose data changes when the
 * operator (or another tab) acts, but doesn't need 5 s status-strip
 * freshness. W21-MVP-5 baseline; tune per-tab if a workflow needs it.
 */
export const PANEL_POLL_MS = 15_000;

/**
 * Lag-protected polling effect. Calls ``effect`` once immediately, then
 * on every ``intervalMs`` tick — but **never overlaps** in-flight runs:
 * if a previous invocation is still pending when the next tick fires,
 * the tick is skipped. The most-recent ``effect`` closure is always
 * used (via ref) so callers can pass an inline arrow without
 * re-arming the interval every render.
 *
 * Cleans up on unmount: cancels the interval and sets a ``cancelled``
 * flag so any pending ``effect`` can early-exit before touching state.
 *
 * Cancellation note: this hook does NOT pass an AbortSignal because the
 * stale tabs reuse their existing un-aborted fetch functions; if a
 * caller wants cancellation, they can capture an AbortController inside
 * their own ``effect`` and close over it. ``useQuery`` is the
 * preferred primitive when AbortSignal-based cancellation matters.
 *
 *   usePollingEffect(refresh, PANEL_POLL_MS, []);
 *
 * Match-points: pass an empty dep array if ``effect`` is stable across
 * renders (``useCallback`` or top-level function); otherwise list the
 * inputs that should restart the timer.
 */
export function usePollingEffect(
  effect: () => void | Promise<void>,
  intervalMs: number,
  deps: ReadonlyArray<unknown> = [],
): void {
  const effectRef = useRef(effect);
  effectRef.current = effect;

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;

    const tick = async (): Promise<void> => {
      if (cancelled || inFlight) return;
      inFlight = true;
      try {
        await effectRef.current();
      } finally {
        inFlight = false;
      }
    };

    void tick(); // immediate first call
    if (!intervalMs || intervalMs <= 0) {
      return () => {
        cancelled = true;
      };
    }
    const timer = window.setInterval(() => {
      void tick();
    }, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);
}
