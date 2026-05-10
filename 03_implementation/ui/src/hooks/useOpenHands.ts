/**
 * OpenHands CLI runner hooks. Mirror of `useOpenCode` against the
 * `runner_id="openhands"` CLI runner.
 */
import {
  openHandsClient,
  type CliRunnerBoundedTaskResult,
  type CliRunnerPreflightResult,
  type CliRunnerReadiness,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export interface OpenHandsReadiness {
  runner: CliRunnerReadiness | null;
  sandbox: CliRunnerReadiness | null;
}

export function useOpenHands(): QueryResult<OpenHandsReadiness> {
  return useQuery<OpenHandsReadiness>({
    queryKey: "openhands/readiness",
    queryFn: async ({ signal }) => {
      const [runner, sandbox] = await Promise.all([
        openHandsClient.getReadiness({ signal }),
        openHandsClient.getSandboxReadiness({ signal }),
      ]);
      return { runner, sandbox };
    },
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface OpenHandsMutationBundle {
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

export function useOpenHandsMutations(): OpenHandsMutationBundle {
  const preflight = useMutation({
    mutationFn: (vars: { task_id?: string }) =>
      openHandsClient.preflight(vars.task_id),
  });
  const spawnBoundedTask = useMutation({
    mutationFn: (vars: { task_id: string; title: string; files: [string] }) =>
      openHandsClient.spawnBoundedTask(vars),
  });
  return { preflight, spawnBoundedTask };
}
