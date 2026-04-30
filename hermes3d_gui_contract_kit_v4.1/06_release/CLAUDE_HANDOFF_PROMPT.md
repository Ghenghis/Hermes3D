# Claude Handoff Prompt

You are continuing Hermes3D. Use this v3 FINAL contract kit as the source of truth.

## First action
Read:
1. `00_overview/README.md`
2. `00_overview/EXECUTION_ORDER.md`
3. `config/external_repos_registry.yaml`
4. `01_requirements/TAB_SPECS.md`
5. `02_architecture/ARCHITECTURE.md`
6. `04_testing/TEST_PLAN.md`

## Rules
- Do not commit to main/master.
- Use feature branches.
- Do not merge unstable QA.
- Do not vendor upstream apps into core.
- Do not downgrade dependencies just to satisfy stale tests.
- Do not send printer commands until safety gates are implemented.

## Task
Implement v3 in phases:
1. Registry validator.
2. Adapter interfaces.
3. UI mock shell.
4. Dock/undock UI.
5. Detect-only adapters.
6. Read-only adapters.
7. Proof gates.
8. Write-control adapters last.

## Done means
- All tests green.
- UI screenshot proof exists.
- Proof bundle validates.
- Adapter registry has pinned versions for any promoted provider.

## v4 Dual Edition Addendum

Implement Hermes3D as one product with two deployment modes: Windows Desktop GPU Worker Edition and Ubuntu VPS Control Server Edition. Do not fork the UI. The VPS routes heavy jobs to registered local GPU workers over secure tunnel. The EVGA FTW3 Ultra RTX 3090 Ti should be detected by the Windows worker and reported as capability. No release until both editions pass gates.
