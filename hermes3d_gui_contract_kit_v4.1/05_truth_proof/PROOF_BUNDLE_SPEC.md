# Proof Bundle Spec

Each build creates a signed proof bundle containing:
- manifest.json
- branch + commit
- registry version pins
- adapter capability report
- UI screenshots
- Playwright report
- test logs
- safety policy snapshot
- slicer/printer dry-run artifacts
- denied dangerous-command test proof
- evidence_ledger.md

## Release cannot proceed if
- Layer D fails.
- proof bundle missing.
- registry has floating main/dev provider promoted to production.
- dangerous command tests skipped.
- UI screenshot missing.
