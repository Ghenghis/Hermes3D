/**
 * LLM provider hooks: list, team readiness, single-provider smoke.
 */
import {
  providersClient,
  type ProviderHealthEntry,
  type ProviderSmokeResult,
  type ProviderTeamReadiness,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export interface ProvidersSnapshot {
  providers: ProviderHealthEntry[] | null;
  teams: ProviderTeamReadiness | null;
}

export function useProviders(): QueryResult<ProvidersSnapshot> {
  return useQuery<ProvidersSnapshot>({
    queryKey: "providers/snapshot",
    queryFn: async ({ signal }) => {
      const [providers, teams] = await Promise.all([
        providersClient.list({ signal }),
        providersClient.getTeamReadiness({ signal }),
      ]);
      return { providers, teams };
    },
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface ProviderMutationBundle {
  smoke: ReturnType<
    typeof useMutation<{ provider_id: string; task_id: string }, ProviderSmokeResult>
  >;
}

export function useProviderMutations(): ProviderMutationBundle {
  const smoke = useMutation({
    mutationFn: (vars: { provider_id: string; task_id: string }) =>
      providersClient.smoke(vars),
  });
  return { smoke };
}
