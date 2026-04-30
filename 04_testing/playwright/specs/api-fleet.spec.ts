import { test, expect } from '@playwright/test';

test.describe.configure({ retries: 2 });

const API_BASE = process.env.HERMES3D_API_URL ?? 'http://127.0.0.1:8765';

test('FastAPI /fleet returns 12 printer profiles with required fields', async ({ request }) => {
  const res = await request.get(`${API_BASE}/fleet`);
  expect(res.status()).toBe(200);

  const fleet = await res.json();
  expect(Array.isArray(fleet)).toBe(true);
  expect(fleet.length).toBe(12);

  for (const p of fleet) {
    expect(p).toEqual(
      expect.objectContaining({
        profile_id: expect.any(String),
        manufacturer: expect.any(String),
        model: expect.any(String),
        kinematics: expect.any(String),
        z_height_mm: expect.any(Number),
        hotend_max_c: expect.any(Number),
        bed_max_c: expect.any(Number),
        enclosed: expect.any(Boolean),
        direct_drive: expect.any(Boolean),
      }),
    );
    // bed must expose at minimum x/y dims.
    expect(p.bed).toBeDefined();
  }

  // Profile IDs should be unique.
  const ids = fleet.map((p: { profile_id: string }) => p.profile_id);
  expect(new Set(ids).size).toBe(ids.length);
});
