# Tests/Proof Readiness - Steps 20-24 and 34

Owner: TESTS-PROOF

Sources read:
- `00_overview/PHASE2_PLAN.md` for task mapping.
- `00_overview/contract/MASTER_CONTRACT.md` for proof requirements.
- `05_truth_proof/PROOF_PROTOCOL.md` and `05_truth_proof/BUNDLE_FORMAT.md` for bundle shape.
- `hermes3d_gui_contract_kit_v4.1/05_truth_proof/PROOF_BUNDLE_SPEC.md` for release gate expectations.

Unavailable requested sources:
- `CODEX_MASTER_EXECUTION.md` was not present in this checkout.
- `06_TESTS_AND_PROOF` was not present in this checkout.

Prepared e2e specs:
- `03_implementation/ui/tests/e2e/dashboard.steps-20-24.spec.ts`
- `03_implementation/ui/tests/e2e/printer-control.step-34.spec.ts`
- `03_implementation/ui/playwright.e2e.config.ts`

Expected stable hooks:
- Step 20: `[data-panel-id="dashboard.fleet"]`, 12 `tbody tr`, provenance chips with `data-source`.
- Step 21: `[data-panel-id="dashboard.pipeline"]`.
- Step 22: `[data-panel-id="dashboard.agents.active"]`.
- Step 23: `[data-panel-id="dashboard.agents.activity"]`.
- Step 24: `[data-panel-id="dashboard.resources"]`, visible `CPU`, `RAM`, and `GPU` gauge labels.
- Step 34: `[data-testid="control-root"]`, plus panel ids `control.selector`, `control.jog`, `control.temps`, `control.gcode`, `control.estop`.

Known readiness gaps observed without editing production UI:
- The current `src/App.tsx` imports tabs that are not present in this checkout (`SourceOS`, `Autopilot`, `Design`, `Jobs`, `Printers`, `Observe`, `Voice`, `Learning`, `Artifacts`, `Approvals`, `Plugins`, `Roadmap`), so the Vite app cannot compile until the owning UI worker lands those files or adjusts routing.
- Step 24 currently renders `CPU`, `RAM`, and `DISK`; the Phase 2 plan says `CPU/RAM/GPU`. The e2e proof intentionally expects `GPU`.
- Step 34 has a `PrinterControlTab` implementation file, but current route labels use `Printers` and `src/App.tsx` imports `PrintersTab`; there is no verified route to `PrinterControlTab` in this checkout.

Run commands:
- `cd 03_implementation/ui && npx playwright test -c playwright.e2e.config.ts`
- `python 03_implementation/scripts/generate_proof_bundle.py --test-results 03_implementation/ui/test-results/e2e --output 03_implementation/proof`
