/**
 * W6-5 hook-shape smoke test.
 *
 * Vitest is not installed in this UI bundle. We verify each hook module
 * exposes the documented signatures. Behavioural tests for the underlying
 * client live in `../api/hermes3dClient.test.ts`. Render-time tests live
 * in the Playwright e2e spec (`tests/e2e/gui-wiring-smoke.spec.ts`).
 *
 * Run with:
 *   node --test --experimental-strip-types --no-warnings src/hooks/useAgents.test.ts
 *
 * Note: hook source files use the project convention of extension-less
 * imports (Vite resolves these). The Node test runner cannot resolve those
 * without the `.ts` suffix, so we import each hook module directly here
 * rather than through the barrel.
 */
import { strict as assert } from "node:assert";
import { describe, it } from "node:test";

describe("hook modules", () => {
  it("useAgents exports useAgents/useAgentUpdateStatus/useAgentHealth/useAgentMutations", async () => {
    const mod = await import("./useAgents.ts");
    for (const name of ["useAgents", "useAgentUpdateStatus", "useAgentHealth", "useAgentMutations"]) {
      assert.equal(typeof (mod as Record<string, unknown>)[name], "function", `missing: ${name}`);
    }
  });

  it("useOpenCode + useOpenHands expose useX + useXMutations", async () => {
    const opencode = await import("./useOpenCode.ts");
    const openhands = await import("./useOpenHands.ts");
    assert.equal(typeof opencode.useOpenCode, "function");
    assert.equal(typeof opencode.useOpenCodeMutations, "function");
    assert.equal(typeof openhands.useOpenHands, "function");
    assert.equal(typeof openhands.useOpenHandsMutations, "function");
  });

  it("useProviders + useMcp + useRecovery expose query + mutation hooks", async () => {
    const providers = await import("./useProviders.ts");
    const mcp = await import("./useMcp.ts");
    const recovery = await import("./useRecovery.ts");
    assert.equal(typeof providers.useProviders, "function");
    assert.equal(typeof providers.useProviderMutations, "function");
    assert.equal(typeof mcp.useMcp, "function");
    assert.equal(typeof mcp.useMcpMutations, "function");
    assert.equal(typeof recovery.useRecovery, "function");
    assert.equal(typeof recovery.useRecoveryMutations, "function");
  });

  it("useApps exposes useApps + useAppDetail", async () => {
    const apps = await import("./useApps.ts");
    assert.equal(typeof apps.useApps, "function");
    assert.equal(typeof apps.useAppDetail, "function");
  });
});

describe("_useQuery primitives", () => {
  it("exports useQuery, useMutation, STATUS_POLL_MS=5000", async () => {
    const { useQuery, useMutation, STATUS_POLL_MS } = await import("./_useQuery.ts");
    assert.equal(typeof useQuery, "function");
    assert.equal(typeof useMutation, "function");
    assert.equal(STATUS_POLL_MS, 5_000);
  });
});
