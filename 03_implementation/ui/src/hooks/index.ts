/**
 * Hermes3D-OS GUI hook barrel — W6-5 wiring layer.
 *
 * Each hook is a thin React wrapper around a domain client in
 * `../api/hermes3dClient`. They share a tiny `useQuery`-shape primitive
 * (defined inline in `_useQuery.ts`) so call sites get a predictable
 * `{ data, error, isLoading, refetch }` contract identical to
 * `@tanstack/react-query` even though we don't ship that dep yet.
 */
export { useAgents, useAgentUpdateStatus, useAgentHealth, useAgentMutations } from "./useAgents";
export { useOpenCode, useOpenCodeMutations } from "./useOpenCode";
export { useOpenHands, useOpenHandsMutations } from "./useOpenHands";
export { useProviders, useProviderMutations } from "./useProviders";
export { useMcp, useMcpMutations } from "./useMcp";
export { useApps, useAppDetail } from "./useApps";
export { useRecovery, useRecoveryMutations } from "./useRecovery";
export type { QueryResult, MutationState } from "./_useQuery";
