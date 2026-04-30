# Test Plan

## Gate order
1. Registry validation.
2. Adapter interface tests.
3. UI mock data tests.
4. Dock/undock state tests.
5. Playwright screenshot gate.
6. External app detect tests.
7. Read-only adapter smoke tests.
8. Dangerous command denial tests.
9. Proof bundle validation.

## Layer D UI gate
Minimum current gate:
- UI launches.
- Core tabs visible.
- No console errors.
- Screenshot captured.
- Dock/undock controls work.

UI-Final gate:
- Screenshot comparison against visual contract.
- All 13 tabs render.
- No broken layout at 1920x1080 and 1366x768.

## Adapter gates
Every adapter must prove:
- detect returns stable envelope.
- validate returns capabilities.
- missing tool produces helpful UI state.
- write action blocked without confirmation.
