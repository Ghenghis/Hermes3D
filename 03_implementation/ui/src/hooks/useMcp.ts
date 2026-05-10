/**
 * Hermes MCP lock + readiness hooks. The HTTP endpoint proxies the
 * stdio-only hermes3d-locks MCP server, so the GUI never speaks MCP directly.
 */
import {
  mcpClient,
  type McpLockState,
  type McpReadiness,
} from "../api/hermes3dClient.ts";
import { STATUS_POLL_MS, useMutation, useQuery, type QueryResult } from "./_useQuery.ts";

export interface McpSnapshot {
  readiness: McpReadiness | null;
  locks: McpLockState | null;
}

export function useMcp(): QueryResult<McpSnapshot> {
  return useQuery<McpSnapshot>({
    queryKey: "mcp/snapshot",
    queryFn: async ({ signal }) => {
      const [readiness, locks] = await Promise.all([
        mcpClient.readiness({ signal }),
        mcpClient.listLocks({ signal }),
      ]);
      return { readiness, locks };
    },
    refetchInterval: STATUS_POLL_MS,
  });
}

export interface McpMutationBundle {
  heartbeat: ReturnType<typeof useMutation<{ task_id: string }, { ok: boolean }>>;
}

export function useMcpMutations(): McpMutationBundle {
  const heartbeat = useMutation({
    mutationFn: (vars: { task_id: string }) => mcpClient.heartbeat(vars.task_id),
  });
  return { heartbeat };
}
