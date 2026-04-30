# Hermes3D-OS UI E2E suite (Playwright)

Layer D of the test pyramid. Real-browser end-to-end coverage of the Gradio
launcher and the FastAPI server, with screenshot baselines and strict
console / network gating.

## What's covered

| Spec | What it asserts |
| --- | --- |
| `truth-gate-tab.spec.ts` | Uploads `fixtures/cube.stl`, runs Truth Gate, asserts PASS/FAIL/WARN appears + report table + JSON output |
| `desk-organizer-tab.spec.ts` | Tweaks a slider, generates an organizer, asserts STL link + signed-proof copy appear |
| `dry-run-pipeline.spec.ts` | Runs the dry-run orchestrator, asserts Job / Final stage / History lines render |
| `disabled-tab.spec.ts` | Asserts the "Full Autonomous Pipeline" tab is present, labelled disabled, and shows the deferred-feature disclosure (honesty gate) |
| `api-health.spec.ts` | `GET /health` returns the documented `{ok, version, ts_unix, fleet_size}` schema |
| `api-fleet.spec.ts` | `GET /fleet` returns 12 unique printer profiles with required fields |
| `api-dispatch.spec.ts` | `POST /dispatch` returns a `selected_printer_id` that exists in `/fleet` and scored candidate list |

Every spec ends on a real DOM/JSON content assertion. None of them are
green-on-empty smoke tests.

## Running locally

```bash
# Bring up FastAPI + Gradio, run the suite, tear down, capture artifacts:
bash scripts/run-e2e.sh

# Or, on Windows:
pwsh scripts/run-e2e.ps1
```

The script logs both servers to `var/e2e-runs/<utc>/{api,ui,playwright}.log`
and copies `playwright-report/` + `test-results/` into the same folder.

To run against an already-running stack:

```bash
HERMES3D_API_URL=http://127.0.0.1:8765 \
HERMES3D_UI_URL=http://127.0.0.1:7860 \
  (cd 04_testing/playwright && npm test)
```

## Updating screenshot baselines

```bash
(cd 04_testing/playwright && npm run test:update)
```

Then commit the changed `__snapshots__/**.png` as part of the PR that made
the UI change. See `__snapshots__/BASELINES.md` for full policy.

## Strict gates (these block the suite)

The `console-strict.ts` fixture (auto-applied to every spec via
`fixtures/console-strict.ts`) fails any test where the page emits:

- a `pageerror` (uncaught JS exception)
- a `console.error(...)` message
- a `requestfailed` network event
- an HTTP response with status >= 400

Excluded URL patterns (kept narrow, kept honest):

- `/favicon*` — browsers fetch this whether you serve it or not.
- `/.well-known/*` — browser/extension polling.
- `/manifest.json` — Gradio's optional PWA manifest probe.
- `/gradio_api/queue/data` — dev-server reload heartbeat that 404s harmlessly.

If you find yourself wanting to add another exclusion to silence a flake,
fix the underlying issue first. Exclusions are a last resort.

## Failure-triage checklist

1. Look at `var/e2e-runs/<utc>/playwright.log` first — Playwright's terminal
   output usually tells you which assertion failed.
2. Open `var/e2e-runs/<utc>/playwright-report/index.html` for the HTML
   report (per-test step trace, screenshots, video).
3. Failed-only screenshots are at
   `var/e2e-runs/<utc>/test-results/<spec>/test-failed-1.png`.
4. Server-side errors live in `api.log` and `ui.log` in the same folder.
5. If a `console-strict` violation tripped, the captured errors are
   attached to the test report as `strict-mode-errors.txt`.

## Known divergences from the contract

The original Hermes3D contract referenced `{status: "ok"}` for `/health` and
a `proof.signature` field on `/dispatch`. The implementation diverges:
`/health` returns `{ok: true, version, ts_unix, fleet_size}` and
`/dispatch` returns `{selected_printer_id, rationale, candidates}`. The
specs assert the implementation as-is so future drift is caught — fixing
the divergence is tracked separately.
