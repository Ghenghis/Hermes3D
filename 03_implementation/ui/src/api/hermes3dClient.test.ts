/**
 * W6-5 unit tests for the Hermes3D typed client.
 *
 * Run with:
 *   node --test --experimental-strip-types src/api/hermes3dClient.test.ts
 *
 * No new runtime dep — Node 22+ ships `node:test` and the type-stripping
 * flag enables direct .ts execution. We avoid `import.meta.env` access at
 * module evaluation time by stubbing global `import.meta.env` with a
 * `globalThis` shim before importing the module.
 */
import { strict as assert } from "node:assert";
import { describe, it, beforeEach, afterEach, mock } from "node:test";

// Pre-shim import.meta.env so the module under test reads the right port.
// Node strips types but keeps `import.meta`; the env object lives on it.
type FakeFetch = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

const originalFetch = globalThis.fetch;

// Lazy-import after the env shim is in place.
async function loadClient() {
  const mod = await import("./hermes3dClient.ts");
  return mod;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("redactSensitive", () => {
  it("redacts bearer tokens in error strings", async () => {
    const { redactSensitive } = await loadClient();
    const out = redactSensitive("Authorization: Bearer abc123def456 failed");
    assert.match(out, /Bearer \*\*\*/);
    assert.doesNotMatch(out, /abc123def456/);
  });

  it("redacts api_key=... query strings", async () => {
    const { redactSensitive } = await loadClient();
    const out = redactSensitive("https://example.com/x?api_key=SECRET&y=1");
    assert.match(out, /api_key=\*\*\*/);
    assert.doesNotMatch(out, /SECRET/);
  });

  it("redacts FOO_KEY=... shell-style markers", async () => {
    const { redactSensitive } = await loadClient();
    const out = redactSensitive("env OPENAI_KEY=sk-xxx ran ok");
    assert.match(out, /OPENAI_KEY=\*\*\*/);
    assert.doesNotMatch(out, /sk-xxx/);
  });
});

describe("agentsClient.getUpdateStatus", () => {
  let fetchMock: FakeFetch;

  beforeEach(() => {
    fetchMock = mock.fn(async () =>
      jsonResponse({
        repo_url: "https://github.com/NousResearch/Hermes-Agent.git",
        checkout_path: "G:/Github/hermes-agent-fresh",
        repo_ready: true,
        current: { exact_tag: "v0.13.0", commit: "abcdef0" },
        latest_release: { tag: "v2026.5.7" },
        outdated: false,
        outdated_by: 0,
        pending_tags: [],
        backup_available: false,
        latest_backup: null,
        strategy: "staged_backup_then_tag_checkout",
        rollback: "",
      }),
    );
    (globalThis as { fetch: FakeFetch }).fetch = fetchMock;
  });

  afterEach(() => {
    (globalThis as { fetch?: typeof originalFetch }).fetch = originalFetch;
  });

  it("returns the typed payload", async () => {
    const { agentsClient } = await loadClient();
    const status = await agentsClient.getUpdateStatus();
    assert.ok(status);
    assert.equal(status.current.exact_tag, "v0.13.0");
    assert.equal(status.latest_release.tag, "v2026.5.7");
  });

  it("returns null on 5xx instead of throwing (polling-friendly)", async () => {
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async () =>
      jsonResponse({ detail: "boom" }, 500),
    );
    const { agentsClient } = await loadClient();
    const status = await agentsClient.getUpdateStatus();
    assert.equal(status, null);
  });
});

describe("openCodeClient + openHandsClient", () => {
  afterEach(() => {
    (globalThis as { fetch?: typeof originalFetch }).fetch = originalFetch;
  });

  it("openCode preflight POST sends runner_id=opencode + task_id", async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push({ url, init });
      // First GET dry-run returns 404 to force POST fallback.
      if (init?.method !== "POST") return jsonResponse({}, 404);
      return jsonResponse({
        runner_id: "opencode",
        exit_code: 0,
        elapsed_ms: 12,
        ready: true,
      });
    });
    const { openCodeClient } = await loadClient();
    const result = await openCodeClient.preflight("task-W6-5-1");
    assert.ok(result);
    assert.equal(result.runner_id, "opencode");
    const post = calls.find((c) => c.init?.method === "POST");
    assert.ok(post, "should fall back to POST");
    const body = JSON.parse((post.init?.body as string) ?? "{}");
    assert.equal(body.runner_id, "opencode");
    assert.equal(body.task_id, "task-W6-5-1");
  });

  it("openHands spawnBoundedTask sends runner_id=openhands", async () => {
    let captured: { url: string; body: unknown } | null = null;
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();
      captured = { url, body: init?.body ? JSON.parse(init.body as string) : null };
      return jsonResponse({
        runner_id: "openhands",
        task_id: "T1",
        exit_code: 0,
        elapsed_ms: 5,
        status: "ok",
      });
    });
    const { openHandsClient } = await loadClient();
    const result = await openHandsClient.spawnBoundedTask({
      task_id: "T1",
      title: "ok",
      files: ["a.py"],
    });
    assert.equal(result.runner_id, "openhands");
    assert.ok(captured);
    assert.match(captured!.url, /\/cli-runners\/run-bounded-task$/);
    assert.equal((captured!.body as { runner_id: string }).runner_id, "openhands");
  });
});

describe("mcpClient + recoveryClient + appsClient + providersClient", () => {
  afterEach(() => {
    (globalThis as { fetch?: typeof originalFetch }).fetch = originalFetch;
  });

  it("mcpClient.listLocks returns null on transport failure", async () => {
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    const { mcpClient } = await loadClient();
    const locks = await mcpClient.listLocks();
    assert.equal(locks, null);
  });

  it("mcpClient.heartbeat throws redacted error on 401", async () => {
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async () =>
      jsonResponse({ detail: "auth required for token=SECRET" }, 401),
    );
    const { mcpClient } = await loadClient();
    await assert.rejects(
      mcpClient.heartbeat("T9"),
      (err: Error) => {
        // Token must be redacted in the surfaced error message.
        assert.doesNotMatch(err.message, /SECRET/);
        assert.match(err.message, /\*\*\*/);
        return true;
      },
    );
  });

  it("recoveryClient.listRuns appends task_id query string", async () => {
    let url = "";
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (input) => {
      url = typeof input === "string" ? input : input.toString();
      return jsonResponse({ runs: [] });
    });
    const { recoveryClient } = await loadClient();
    await recoveryClient.listRuns("task-T9-9");
    assert.match(url, /task_id=task-T9-9/);
  });

  it("appsClient.list hits /api/source-os/modules", async () => {
    let url = "";
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (input) => {
      url = typeof input === "string" ? input : input.toString();
      return jsonResponse([]);
    });
    const { appsClient } = await loadClient();
    await appsClient.list();
    assert.match(url, /\/api\/source-os\/modules$/);
  });

  it("providersClient.smoke posts the body as-is", async () => {
    let body: unknown = null;
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (_input, init) => {
      body = init?.body ? JSON.parse(init.body as string) : null;
      return jsonResponse({
        provider_id: "minimax",
        status: "ok",
        ready: true,
      });
    });
    const { providersClient } = await loadClient();
    await providersClient.smoke({ provider_id: "minimax", task_id: "T1" });
    assert.deepEqual(body, { provider_id: "minimax", task_id: "T1" });
  });
});

describe("auth headers", () => {
  afterEach(() => {
    (globalThis as { fetch?: typeof originalFetch }).fetch = originalFetch;
  });

  it("does not include an Authorization header when no token is set", async () => {
    let lastInit: RequestInit | undefined;
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (_input, init) => {
      lastInit = init;
      return jsonResponse({});
    });
    const { agentsClient, setBearerTokenProvider } = await loadClient();
    setBearerTokenProvider(() => null);
    await agentsClient.getUpdateStatus();
    const headers = (lastInit?.headers ?? {}) as Record<string, string>;
    assert.equal(headers["Authorization"], undefined);
  });

  it("attaches a Bearer header when the provider yields a token", async () => {
    let lastInit: RequestInit | undefined;
    (globalThis as { fetch: FakeFetch }).fetch = mock.fn(async (_input, init) => {
      lastInit = init;
      return jsonResponse({});
    });
    const { agentsClient, setBearerTokenProvider } = await loadClient();
    setBearerTokenProvider(() => "test-token-123");
    await agentsClient.getUpdateStatus();
    const headers = (lastInit?.headers ?? {}) as Record<string, string>;
    assert.equal(headers["Authorization"], "Bearer test-token-123");
    setBearerTokenProvider(() => null);
  });
});
