import { expect, test } from "@playwright/test";

/**
 * Service Health API smoke. Locks in the wire shape of
 * ``GET /api/health/services`` so the React UI's parser never silently
 * drifts from the FastAPI serialiser.
 *
 * The Layer D harness (`scripts/run-e2e.sh`) brings up
 * `uvicorn hermes3d.api.server:app` on port 8765, which auto-registers
 * the new `register_health_routes(...)` handler. We just hit it.
 */

test.describe.configure({ retries: 2 });

const API_BASE = process.env.HERMES3D_API_URL ?? "http://127.0.0.1:8765";

test("FastAPI /api/health/services returns the documented schema", async ({ request }) => {
  const res = await request.get(`${API_BASE}/api/health/services`);
  expect(res.status(), `unexpected HTTP status: ${res.status()}`).toBe(200);

  const body = await res.json();
  expect(body).toHaveProperty("results");
  expect(Array.isArray(body.results)).toBe(true);
  expect(body.results.length).toBeGreaterThan(0);

  for (const entry of body.results) {
    expect(entry).toEqual(
      expect.objectContaining({
        name: expect.any(String),
        category: expect.stringMatching(/^(mcp|llm|modeling|printer|api|tunnel)$/),
        host: expect.any(String),
        port: expect.any(Number),
        status: expect.stringMatching(
          /^(online|offline|unreachable|auth-required|disabled|unknown)$/,
        ),
        detail: expect.any(String),
        latency_ms: expect.any(Number),
        probed_at: expect.any(String),
      }),
    );
  }
});
