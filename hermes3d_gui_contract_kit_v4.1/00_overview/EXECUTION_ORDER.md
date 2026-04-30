# Execution Order

## Phase 0 — Preserve current stable line
- Confirm PR #10 is merged and PR #9 rerun is GREEN before release work.
- Do not start UI-Final merge until rc1 is cut.

## Phase 1 — Add registry + adapter shell
- Add `config/external_repos_registry.yaml`.
- Add provider manager interfaces.
- Add no-op/detect-only adapters.
- Add tests for registry validation.

## Phase 2 — UI-Final branch only
Branch: `feat/ui-final-dashboard`
- Add screenshot as `06_release/UI_FINAL_VISUAL_CONTRACT.png`.
- Build React + Tailwind shell with mock data.
- Implement all tabs from `01_requirements/TAB_SPECS.md`.
- Dock/undock before real integrations.

## Phase 3 — Integration in safe order
1. Detect installed tools.
2. Read-only health/status.
3. File export/import.
4. Slicing dry-run.
5. Printer read-only status.
6. Write controls behind confirmation.
7. Print start only after proof gates.

## Phase 4 — Release gates
- Playwright screenshot gate.
- Adapter smoke gates.
- Proof bundle generation.
- External app launcher tests.
- Dangerous command denial tests.

## Phase 5 — Merge only when green
- No failing Layer D.
- No skipped proof bundle.
- No untested printer-control writes.
