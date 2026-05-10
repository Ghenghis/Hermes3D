/**
 * Hermes Agent Recovery Controller (RC v2) hooks. Owns the read side of
 * the recovery surface; W6-2 owns the active-loop component that consumes
 * these hooks.
 */
import {
  recoveryClient,
  type RecoveryRunsResponse,
  type RecoveryStateResponse,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export interface RecoverySnapshot {
  runs: RecoveryRunsResponse | null;
  state: RecoveryStateResponse | null;
}

export function useRecovery(taskId?: string): QueryResult<RecoverySnapshot> {
  return useQuery<RecoverySnapshot>({
    queryKey: `recovery/${taskId ?? "all"}`,
    queryFn: async ({ signal }) => {
      const [runs, state] = await Promise.all([
        recoveryClient.listRuns(taskId, { signal }),
        recoveryClient.getState(taskId, { signal }),
      ]);
      return { runs, state };
    },
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface RecoveryMutationBundle {
  proposeFailure: ReturnType<
    typeof useMutation<Record<string, unknown>, { attempt_id: string; status: string }>
  >;
  markOutcome: ReturnType<
    typeof useMutation<
      {
        attempt_id: string;
        status: string;
        recovery_summary?: string;
        proposal_id?: string;
        review_evidence_id?: string;
        apply_evidence_id?: string;
        retry_gate_id?: string;
      },
      { ok: boolean; attempt_id: string; status: string }
    >
  >;
}

export function useRecoveryMutations(): RecoveryMutationBundle {
  const proposeFailure = useMutation({
    mutationFn: (vars: Record<string, unknown>) =>
      recoveryClient.proposeFailure(vars),
  });
  const markOutcome = useMutation({
    mutationFn: (vars: {
      attempt_id: string;
      status: string;
      recovery_summary?: string;
      proposal_id?: string;
      review_evidence_id?: string;
      apply_evidence_id?: string;
      retry_gate_id?: string;
    }) => recoveryClient.markOutcome(vars),
  });
  return { proposeFailure, markOutcome };
}
