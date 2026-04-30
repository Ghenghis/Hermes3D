import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 2 });

const API_BASE = process.env.HERMES3D_API_URL ?? 'http://127.0.0.1:8765';

test('FastAPI /dispatch returns a decision with scored candidates from /fleet', async ({
  request,
}) => {
  // Discover the fleet first; assert dispatch references real printer IDs.
  const fleetRes = await request.get(`${API_BASE}/fleet`);
  expect(fleetRes.status()).toBe(200);
  const fleet = await fleetRes.json();
  const fleetIds = new Set<string>(fleet.map((p: { profile_id: string }) => p.profile_id));
  expect(fleetIds.size).toBeGreaterThanOrEqual(12);

  const res = await request.post(`${API_BASE}/dispatch`, {
    data: {
      mesh_extents_mm: [80, 80, 60],
      mesh_xy_radius_mm: 60,
      material: 'PLA',
      quality_level: 'normal',
      strategy: 'auto',
    },
  });
  expect(res.status(), await res.text()).toBe(200);

  const body = await res.json();
  // The kit's /dispatch response schema is
  //   { selected_printer_id, rationale, candidates: [...] }
  // (documented in 03_implementation/src/hermes3d/api/server.py). The
  // task contract referenced a `proof.signature` field — the API does not
  // currently emit one; that's flagged in 04_testing/playwright/README.md.
  expect(body).toEqual(
    expect.objectContaining({
      selected_printer_id: expect.any(String),
      rationale: expect.any(String),
      candidates: expect.any(Array),
    }),
  );

  expect(fleetIds.has(body.selected_printer_id)).toBe(true);
  expect(body.candidates.length).toBeGreaterThan(0);

  for (const c of body.candidates) {
    expect(c).toEqual(
      expect.objectContaining({
        printer_id: expect.any(String),
        score: expect.any(Number),
        fits: expect.any(Boolean),
        eligible: expect.any(Boolean),
        reasons: expect.any(Array),
        blockers: expect.any(Array),
      }),
    );
    expect(fleetIds.has(c.printer_id)).toBe(true);
  }
});
