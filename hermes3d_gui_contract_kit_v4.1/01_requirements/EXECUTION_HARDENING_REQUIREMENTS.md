# Execution Hardening Requirements

## Required implementation order

1. Stabilize current develop.
2. Add v4.1 registry validator and task files.
3. Implement read-only discovery adapters.
4. Implement UI shell with mock data.
5. Implement dock/undock/fullscreen shell.
6. Implement Windows Desktop worker.
7. Implement Ubuntu VPS control server.
8. Implement secure tunnel worker registration.
9. Implement tool adapters in read-only mode.
10. Promote write-control one adapter at a time.
11. Add UI-Final screenshot gate.
12. Cut release only after all hard gates pass.

Every phase must provide branch name, PR/commit hash, test output, screenshots for UI work, version pins, rollback note, and failure summary if repaired.
