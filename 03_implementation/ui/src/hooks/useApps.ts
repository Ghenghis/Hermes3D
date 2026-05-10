/**
 * 60-app registry hooks (W6-8 ships the data; W6-5 wires it).
 *
 *   useApps()             -> 5 s polled `/api/source-os/modules`
 *   useAppDetail(id)      -> 5 s polled `/api/source-os/modules/{id}`
 */
import { appsClient, type AppEntry } from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useQuery, type QueryResult } from "./_useQuery.ts";

export function useApps(): QueryResult<AppEntry[] | null> {
  return useQuery<AppEntry[] | null>({
    queryKey: "apps/list",
    queryFn: ({ signal }) => appsClient.list({ signal }),
    refetchInterval: STATUS_POLL_MS,
  });
}

export function useAppDetail(id: string | null | undefined): QueryResult<AppEntry | null> {
  return useQuery<AppEntry | null>({
    queryKey: `apps/detail/${id ?? "_none"}`,
    queryFn: ({ signal }) => {
      if (!id) return Promise.resolve(null);
      return appsClient.detail(id, { signal });
    },
    refetchInterval: STATUS_POLL_MS,
    enabled: typeof id === "string" && id.length > 0,
  });
}
