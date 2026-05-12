import { describe, expect, it, vi } from "vitest";
import {
  createAppsClient,
  redactProofReason,
  toRegistryApp,
  toRegistryAppDetail,
} from "../../src/api/appsClient";

describe("appsClient mappers", () => {
  it("maps a sparse module entry to a RegistryApp with honest unknowns", () => {
    const entry = { id: "fdm-marlin", display: "Marlin Firmware" };
    const app = toRegistryApp(entry);
    expect(app.id).toBe("fdm-marlin");
    expect(app.name).toBe("Marlin Firmware");
    expect(app.current_version).toBeNull();
    expect(app.tested_versions).toEqual([]);
    expect(app.update_lane).toBe("unknown");
    expect(app.lifecycle).toBe("unknown");
    expect(app.license.spdx).toBe("Unknown");
    expect(app.last_proof).toBeNull();
    expect(app.rollback_supported).toBe(false);
  });

  it("maps a rich registry app entry", () => {
    const entry = {
      id: "blender",
      name: "Blender",
      current_version: "4.2.1",
      tested_versions: ["4.0.0", "4.1.0", "4.2.1"],
      license: { spdx: "GPL-3.0", label: "GNU GPL v3" },
      update_lane: "stable",
      lifecycle: "stable",
      last_proof: { id: "ev-123", status: "pass", at: "2026-05-09T12:00:00Z", reason: "ok" },
      rollback_supported: true,
      description: "3D modeling app",
      upstream_url: "https://blender.org",
    };
    const app = toRegistryApp(entry);
    expect(app.tested_versions).toEqual(["4.0.0", "4.1.0", "4.2.1"]);
    expect(app.last_proof?.status).toBe("pass");
    expect(app.last_proof?.proof_event_id).toBe("ev-123");
    expect(app.rollback_supported).toBe(true);
    expect(app.update_lane).toBe("stable");
  });

  it("includes recent_proofs and rollback_runbook_url on detail", () => {
    const detail = toRegistryAppDetail({
      id: "blender",
      name: "Blender",
      tested_versions: ["4.0.0"],
      recent_proofs: [{ id: "p1", status: "pass", at: "2026-05-09T12:00:00Z", reason: "ok" }],
      rollback_runbook_url: "https://docs.example.com/rollback",
      proof_command: "blender --version",
    });
    expect(detail.recent_proofs).toHaveLength(1);
    expect(detail.recent_proofs[0]?.proof_event_id).toBe("p1");
    expect(detail.rollback_runbook_url).toBe("https://docs.example.com/rollback");
    expect(detail.proof_command).toBe("blender --version");
  });

  it("redacts control characters and caps long proof reasons", () => {
    expect(redactProofReason(null)).toBe("");
    expect(redactProofReason("ok")).toBe("ok");
    expect(redactProofReason("hi\x00there")).toBe("hi there");
    const long = "x".repeat(400);
    expect(redactProofReason(long)).toHaveLength(280);
    expect(redactProofReason(long).endsWith("…")).toBe(true);
  });
});

describe("appsClient HTTP layer", () => {
  function makeFetcher(routes: Record<string, unknown>): typeof fetch {
    return vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
      const url = typeof input === "string" ? input : input.toString();
      if (!(url in routes)) {
        return new Response(JSON.stringify({ error: "not found" }), { status: 404 });
      }
      const value = routes[url];
      return new Response(JSON.stringify(value), { status: 200 });
    }) as unknown as typeof fetch;
  }

  it("listApps falls back to /api/source-os/modules when /api/apps 404s", async () => {
    const client = createAppsClient({
      baseUrl: "http://test.local",
      fetcher: makeFetcher({
        "http://test.local/api/source-os/modules": {
          modules: [{ id: "blender", name: "Blender" }],
        },
      }),
    });
    const apps = await client.listApps();
    expect(apps).toHaveLength(1);
    expect(apps[0]?.id).toBe("blender");
  });

  it("listApps prefers /api/apps when present", async () => {
    const client = createAppsClient({
      baseUrl: "http://test.local",
      fetcher: makeFetcher({
        "http://test.local/api/apps": [{ id: "blender", name: "Blender" }],
      }),
    });
    const apps = await client.listApps();
    expect(apps[0]?.id).toBe("blender");
  });

  it("getApp throws AppsClientError when both endpoints 404", async () => {
    const client = createAppsClient({
      baseUrl: "http://test.local",
      fetcher: makeFetcher({}),
    });
    await expect(client.getApp("missing")).rejects.toThrow(/not found in registry/);
  });

  it("runProofSweep posts a bounded operator request and maps the summary", async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        actor: "test-operator",
        limit: 3,
        timeout_s: 7,
        include_without_command: false,
      });
      return new Response(
        JSON.stringify({
          accepted: true,
          status: "completed",
          proof_event_id: "proof-sweep-1",
          summary: { total: 3, pass: 1, fail: 1, timeout: 0, error: 0, not_set: 1 },
        }),
        { status: 200 },
      );
    }) as unknown as typeof fetch;
    const client = createAppsClient({ baseUrl: "http://test.local", fetcher });

    const result = await client.runProofSweep({
      actor: "test-operator",
      limit: 3,
      timeout_s: 7,
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://test.local/api/apps/run-proofs",
      expect.any(Object),
    );
    expect(result).toEqual({
      accepted: true,
      status: "completed",
      proof_event_id: "proof-sweep-1",
      summary: { total: 3, pass: 1, fail: 1, timeout: 0, error: 0, not_set: 1 },
      reason: "",
    });
  });
});
