/**
 * OpenCode CLI runner hooks.
 *
 *   useOpenCode()            -> 5 s polled `/cli-runners` + `/sandbox/readiness`
 *   useOpenCodeMutations()   -> { preflight, spawnBoundedTask }
 */
import {
  openCodeClient,
  type CliRunnerBoundedTaskResult,
  type CliRunnerPreflightResult,
  type CliRunnerReadiness,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export interface OpenCodeReadiness {
  runner: CliRunnerReadiness | null;
  sandbox: CliRunnerReadiness | null;
}

export function useOpenCode(): QueryResult<OpenCodeReadiness> {
  return useQuery<OpenCodeReadiness>({
    queryKey: "opencode/readiness",
    queryFn: async ({ signal }) => {
      const [runner, sandbox] = await Promise.all([
        openCodeClient.getReadiness({ signal }),
        openCodeClient.getSandboxReadiness({ signal }),
      ]);
      return { runner, sandbox };
    },
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface OpenCodeMutationBundle {
  preflight: ReturnType<
    typeof useMutation<{ task_id?: string }, CliRunnerPreflightResult | null>
  >;
  spawnBoundedTask: ReturnType<
    typeof useMutation<
      { task_id: string; title: string; files: [string] },
      CliRunnerBoundedTaskResult
    >
  >;
}

export function useOpenCodeMutations(): OpenCodeMutationBundle {
  const preflight = useMutation({
    mutationFn: (vars: { task_id?: string }) =>
      openCodeClient.preflight(vars.task_id),
  });
  const spawnBoundedTask = useMutation({
    mutationFn: (vars: { task_id: string; title: string; files: [string] }) =>
      openCodeClient.spawnBoundedTask(vars),
  });
  return { preflight, spawnBoundedTask };
}
