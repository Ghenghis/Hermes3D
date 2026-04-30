import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 2 });

const API_BASE = process.env.HERMES3D_API_URL ?? 'http://127.0.0.1:8765';

test('FastAPI /health responds with the expected schema', async ({ request }) => {
  const res = await request.get(`${API_BASE}/health`);
  expect(res.status(), `unexpected HTTP status from /health: ${res.status()}`).toBe(200);

  const body = await res.json();
  // The kit's actual /health schema is `{ok: true, version, ts_unix, fleet_size}`.
  // (The contract spec mentioned `{status:"ok"}` — the implementation deviates;
  // this assertion locks in what server.py actually returns so future drift
  // is caught.)
  expect(body).toEqual(
    expect.objectContaining({
      ok: true,
      version: expect.stringMatching(/^\d+\.\d+\.\d+/),
      ts_unix: expect.any(Number),
      fleet_size: expect.any(Number),
    }),
  );
  expect(body.fleet_size).toBeGreaterThanOrEqual(12);
});
