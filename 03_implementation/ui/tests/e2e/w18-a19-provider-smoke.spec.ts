/**
 * W18-A19 — live MiniMax + DeepSeek provider smoke Playwright proof.
 *
 * Operator verdict criteria (2026-05-11): GUI_AGENT_WORKFLOW_GREEN final
 * PASS_REAL requires at least one *live* MiniMax / DeepSeek backed
 * assistive task. LM Studio / Ollama are local fallback only.
 *
 * This spec proves three things end-to-end against the live backend at
 * ``HERMES3D_API_BASE`` (default ``http://127.0.0.1:8030``):
 *
 *   1. ``GET /api/agents/health`` returns a ``providers`` map with
 *      MiniMax + DeepSeek tagged as ``builder`` and ``reviewer``
 *      respectively, and ``lm_studio`` / ``ollama`` tagged as ``fallback``.
 *
 *   2. ``POST /api/agents/providers/smoke`` returns ``PASS_LIVE`` for
 *      both MiniMax and DeepSeek when keys are present in the runtime
 *      env. When keys are not present (CI without secrets) the spec
 *      accepts the honest ``FAIL_KEY_MISSING`` verdict — no mock, no
 *      skip; the proof bundle records which mode it ran in.
 *
 *   3. ``POST /api/agents/providers/assist`` with provider=minimax
 *      (builder) and provider=deepseek (reviewer) produces persisted
 *      conversation IDs + proof_event IDs. When keys are present the
 *      reply must be ``PASS_LIVE``.
 *
 * No printer-control writes. No mocks. No API keys ever appear in the
 * spec, captured screenshot, or proof bundle. The Authorization header
 * is never read by the FE; the smoke is server-side only.
 */
import { expect, test, type APIRequestContext } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readApiBase(): string {
  // Order of resolution:
  //   1. Explicit env override.
  //   2. The start-e2e-stack runtime manifest at
  //      ``03_implementation/var/runtime-ports.json``.
  //   3. The default uvicorn port 8030 (legacy).
  if (process.env.HERMES3D_API_BASE) {
    return process.env.HERMES3D_API_BASE;
  }
  const candidates = [
    path.join(__dirname, "..", "..", "..", "var", "runtime-ports.json"),
    path.join(__dirname, "..", "..", "..", "..", "var", "runtime-ports.json"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(candidate, "utf-8")) as {
          urls?: { gui_api?: string };
        };
        const url = manifest?.urls?.gui_api;
        if (typeof url === "string" && url.startsWith("http")) {
          return url;
        }
      } catch {
        // fall through
      }
    }
  }
  return "http://127.0.0.1:8030";
}

const API_BASE = readApiBase();
const PROOF_DIR = path.join(
  __dirname,
  "..",
  "..",
  "test-results",
  "w18-a19",
);

interface SmokeResult {
  status: string;
  http_status: number | null;
  latency_ms: number;
  model?: string;
  role?: string;
  key_present?: boolean;
}

interface HealthResponse {
  healthy: boolean;
  status: string;
  providers: Record<
    string,
    {
      role: string;
      role_description: string;
      key_present: boolean;
      kind: string;
      model?: string;
    }
  >;
  provider_roles: {
    builder: string;
    reviewer: string;
    fallback: string[];
  };
}

interface AssistResponse {
  status: string;
  provider: string;
  role: string;
  persona: string;
  http_status: number | null;
  latency_ms: number;
  tokens_in?: number | null;
  tokens_out?: number | null;
  user_msg_id: string;
  assistant_msg_id: string;
  proof_event_id: string;
  completion: string | null;
}

function writeProof(name: string, payload: unknown): string {
  fs.mkdirSync(PROOF_DIR, { recursive: true });
  const fpath = path.join(PROOF_DIR, name);
  fs.writeFileSync(fpath, JSON.stringify(payload, null, 2), "utf-8");
  return fpath;
}

/**
 * Pull /api/agents/health. Fail honestly if the backend is unreachable —
 * the spec never proceeds against a fabricated response.
 */
async function fetchHealth(request: APIRequestContext): Promise<HealthResponse> {
  const r = await request.get(`${API_BASE}/api/agents/health`, { timeout: 20_000 });
  expect(
    r.status(),
    `GET /api/agents/health must be 200; got ${r.status()}`,
  ).toBe(200);
  const body = (await r.json()) as HealthResponse;
  return body;
}

test.describe("W18-A19 provider live smoke", () => {
  test("/api/agents/health surfaces MiniMax + DeepSeek with correct roles", async ({
    request,
  }) => {
    const health = await fetchHealth(request);
    writeProof("agents_health.json", health);

    expect(health.providers).toBeDefined();
    expect(health.providers.minimax).toBeDefined();
    expect(health.providers.deepseek).toBeDefined();
    expect(health.providers.minimax.role).toBe("builder");
    expect(health.providers.deepseek.role).toBe("reviewer");
    expect(health.providers.minimax.kind).toBe("live_remote");
    expect(health.providers.deepseek.kind).toBe("live_remote");

    // Local fallback providers must NOT be tagged as builder/reviewer.
    if (health.providers.lm_studio) {
      expect(health.providers.lm_studio.role).toBe("fallback");
    }
    if (health.providers.ollama) {
      expect(health.providers.ollama.role).toBe("fallback");
    }

    // The provider_roles summary block is the canonical mapping the FE
    // reads — it must agree with the per-provider entries.
    expect(health.provider_roles.builder).toBe("minimax");
    expect(health.provider_roles.reviewer).toBe("deepseek");
    expect(health.provider_roles.fallback).toContain("lm_studio");
    expect(health.provider_roles.fallback).toContain("ollama");
  });

  test("POST /api/agents/providers/smoke returns PASS_LIVE for MiniMax + DeepSeek when keys present", async ({
    request,
  }) => {
    // Read key presence from the health endpoint *first* so the spec can
    // make a truthful decision without ever seeing the key value.
    const health = await fetchHealth(request);
    const mmKeyPresent = Boolean(health.providers.minimax?.key_present);
    const dsKeyPresent = Boolean(health.providers.deepseek?.key_present);

    const r = await request.post(`${API_BASE}/api/agents/providers/smoke`, {
      data: { providers: ["minimax", "deepseek"] },
      timeout: 60_000,
    });
    expect(r.status()).toBe(200);
    const body = (await r.json()) as {
      task_id: string;
      providers: Record<string, SmokeResult>;
    };
    writeProof("agents_providers_smoke.json", body);

    expect(body.task_id).toContain("W18-A19");
    expect(body.providers.minimax).toBeDefined();
    expect(body.providers.deepseek).toBeDefined();
    expect(body.providers.minimax.role).toBe("builder");
    expect(body.providers.deepseek.role).toBe("reviewer");

    if (mmKeyPresent) {
      expect(
        body.providers.minimax.status,
        `MiniMax with key_present must PASS_LIVE; got ${body.providers.minimax.status}`,
      ).toBe("PASS_LIVE");
      expect(body.providers.minimax.http_status).toBe(200);
      expect(body.providers.minimax.latency_ms).toBeGreaterThan(0);
    } else {
      // Honest CI-without-secrets path: must be FAIL_KEY_MISSING, never
      // a fabricated PASS.
      expect(body.providers.minimax.status).toBe("FAIL_KEY_MISSING");
    }

    if (dsKeyPresent) {
      expect(
        body.providers.deepseek.status,
        `DeepSeek with key_present must PASS_LIVE; got ${body.providers.deepseek.status}`,
      ).toBe("PASS_LIVE");
      expect(body.providers.deepseek.http_status).toBe(200);
      expect(body.providers.deepseek.latency_ms).toBeGreaterThan(0);
    } else {
      expect(body.providers.deepseek.status).toBe("FAIL_KEY_MISSING");
    }

    // Belt-and-braces: NO field in the response is allowed to leak an
    // Authorization-bearer-shaped token. The smoke endpoint never echoes
    // the key; we double-check the serialised body here.
    const text = JSON.stringify(body);
    expect(text).not.toMatch(/Bearer\s+[A-Za-z0-9._~+/=-]{8,}/);
    expect(text).not.toMatch(/sk-[A-Za-z0-9_-]{8,}/);
  });

  test("POST /api/agents/providers/assist (builder=MiniMax) persists a real assistive reply", async ({
    request,
  }) => {
    const health = await fetchHealth(request);
    const mmKeyPresent = Boolean(health.providers.minimax?.key_present);
    const prompt =
      "List 3 concrete refactor opportunities in src/hermes3d/api/routes/jobs.py that improve readability without changing behavior. Under 150 words.";
    const r = await request.post(`${API_BASE}/api/agents/providers/assist`, {
      data: { provider: "minimax", prompt, max_tokens: 400 },
      timeout: 90_000,
    });
    expect(r.status()).toBe(200);
    const body = (await r.json()) as AssistResponse;
    // Strip the completion text from the proof bundle so we don't drag
    // a 2-KB blob into the test-results dir; the persisted DB row holds it.
    const safeProof = { ...body, completion: null };
    writeProof("agents_assist_minimax.json", safeProof);

    expect(body.provider).toBe("minimax");
    expect(body.role).toBe("builder");
    expect(body.user_msg_id).toMatch(/^[a-f0-9]+$/);
    expect(body.assistant_msg_id).toMatch(/^[a-f0-9]+$/);
    expect(body.proof_event_id).toMatch(/^[a-f0-9]+$/);
    if (mmKeyPresent) {
      expect(body.status).toBe("PASS_LIVE");
      expect(body.http_status).toBe(200);
    } else {
      expect(body.status).toBe("FAIL_KEY_MISSING");
    }
  });

  test("POST /api/agents/providers/assist (reviewer=DeepSeek) persists a real review reply", async ({
    request,
  }) => {
    const health = await fetchHealth(request);
    const dsKeyPresent = Boolean(health.providers.deepseek?.key_present);
    const prompt =
      "Review the W18-A13 backend wiring fix PR #244 merge commit e880616. Are the 12 endpoint fixes consistent with the W18-A3 audit? Identify any regression risk in under 150 words.";
    const r = await request.post(`${API_BASE}/api/agents/providers/assist`, {
      data: { provider: "deepseek", prompt, max_tokens: 600 },
      timeout: 90_000,
    });
    expect(r.status()).toBe(200);
    const body = (await r.json()) as AssistResponse;
    const safeProof = { ...body, completion: null };
    writeProof("agents_assist_deepseek.json", safeProof);

    expect(body.provider).toBe("deepseek");
    expect(body.role).toBe("reviewer");
    expect(body.user_msg_id).toMatch(/^[a-f0-9]+$/);
    expect(body.assistant_msg_id).toMatch(/^[a-f0-9]+$/);
    expect(body.proof_event_id).toMatch(/^[a-f0-9]+$/);
    if (dsKeyPresent) {
      expect(body.status).toBe("PASS_LIVE");
      expect(body.http_status).toBe(200);
    } else {
      expect(body.status).toBe("FAIL_KEY_MISSING");
    }
  });

  test("rejects unsupported provider names with 400", async ({ request }) => {
    const r = await request.post(`${API_BASE}/api/agents/providers/assist`, {
      data: { provider: "lm_studio", prompt: "x", max_tokens: 1 },
      timeout: 10_000,
    });
    // lm_studio is fallback-only — the assist endpoint must reject it
    // with 400, not pretend to route there. This is part of the
    // operator's "LM Studio is fallback only" verdict criterion.
    expect(r.status()).toBe(400);
  });
});
