/**
 * Hermes Agent (self-update + roster) hooks.
 *
 *   useAgentUpdateStatus()  -> 5 s polled `/api/agents/update/status`
 *   useAgents()             -> 5 s polled `/api/agents`
 *   useAgentHealth()        -> 5 s polled `/api/agents/health`
 *   useAgentMutations()     -> { backup, stagedUpdate, rollback }
 */
import {
  agentsClient,
  type HermesAgentBackup,
  type HermesAgentUpdateResult,
  type HermesAgentUpdateStatus,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export function useAgentUpdateStatus(): QueryResult<HermesAgentUpdateStatus | null> {
  return useQuery<HermesAgentUpdateStatus | null>({
    queryKey: "agents/update/status",
    queryFn: ({ signal }) => agentsClient.getUpdateStatus({ signal }),
    refetchInterval: STATUS_POLL_MS,
  });
}

export function useAgents(): QueryResult<unknown[] | null> {
  return useQuery<unknown[] | null>({
    queryKey: "agents/list",
    queryFn: ({ signal }) => agentsClient.listAgents({ signal }),
    refetchInterval: STATUS_POLL_MS,
  });
}

export function useAgentHealth() {
  return useQuery({
    queryKey: "agents/health",
    queryFn: ({ signal }) => agentsClient.health({ signal }),
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface AgentMutationBundle {
  backup: ReturnType<typeof useMutation<{ note?: string }, HermesAgentBackup>>;
  stagedUpdate: ReturnType<
    typeof useMutation<
      { target_tag?: string | null; max_steps?: number; create_backup?: boolean; run_checks?: boolean; actor?: string },
      HermesAgentUpdateResult
    >
  >;
  rollback: ReturnType<
    typeof useMutation<
      { backup_id?: string; tag?: string; actor?: string },
      HermesAgentUpdateResult
    >
  >;
}

export function useAgentMutations(): AgentMutationBundle {
  const backup = useMutation({
    mutationFn: (vars: { note?: string }) => agentsClient.backup(vars.note),
  });
  const stagedUpdate = useMutation({
    mutationFn: (
      vars: { target_tag?: string | null; max_steps?: number; create_backup?: boolean; run_checks?: boolean; actor?: string },
    ) => agentsClient.stagedUpdate(vars),
  });
  const rollback = useMutation({
    mutationFn: (vars: { backup_id?: string; tag?: string; actor?: string }) =>
      agentsClient.rollback(vars),
  });
  return { backup, stagedUpdate, rollback };
}
