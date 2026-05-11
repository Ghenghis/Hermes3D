# W18-A17 Assistive Tasks — Extracted Assistant Content

Real LLM replies from local qwen3.5-9b runtime, captured from live SSE streams.

## Task 1 — factory-operator — Source OS card audit

1) GUI renders a rollback button conditionally based on `rollback_supported`, which currently evaluates to false for 'flsun_t1_a'. 2) The backend /api/apps/flsun_t1_a response omits `rollback_supported=true`, defaulting it to false in the mock layer. 3) Missing UI wiring: no `onRollback` event handler is bound to the button, and the endpoint `/api/apps/{app_id}/rollback` lacks a corresponding resolver in AppActions.ts.

## Task 2 — modeling-agent — W18-A5 modeler workflow audit

Blocked: Local source `03_implementation/src/hermes3d/api/routes/design.py` and W18-A5 PASS_REAL_PARAMETRIC doc are unavailable. Proof: missing local data access / blocked file read permission. Cannot determine endpoints, artifact paths, or merge risks without these files. S1 printer lock remains active but is unrelated to this API code query.

## Task 3 — oliver-qa-agent — 60 app cards / /api/apps audit

1) Backend reads `/config/app_registry.yaml` to populate the /api/apps table of app cards.
2) Field name divergence: UI schema expects `trigger_id`, but backend API requires `event_trigger`.
3) This causes card rendering (data exists) while the backend rejects action execution due to semantic mismatch.
4) Proof event for a gated update is `PROOF.GATE.APP_CARD_UPDATE_BLOCKED` fired on the agent surface.
5) Read-only audit confirmed; S1 at 192.168.0.12 remains locked per active constraints.

## Task 4 — print-monitor-agent — W18-A12 slicer disk audit

1. Likely endpoint path: `/api/v1/slice/generate/{model_id}` routing output to `04_testing/fixtures/`.
2. Corruption type: Truncated header lacking initial coordinate initialization (G28/G92), causing layer misalignment despite file existence.
3. E2E test validates disk persistence at `03_implementation/ui/tests/e2e/slicer-gcode-disk-persistence.test.js` checking write-read integrity.
