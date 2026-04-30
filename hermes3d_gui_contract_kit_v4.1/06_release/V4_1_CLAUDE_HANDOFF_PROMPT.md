# Claude Handoff Prompt — v4.1 Execution Hardening

```text
You are implementing Hermes3D v4.1 execution-hardening.

Do not freestyle. Follow this contract kit.

Goals:
1. Preserve current stabilization.
2. Implement Windows Desktop GPU Worker edition.
3. Implement Ubuntu VPS Control Server edition.
4. Keep one shared UI/API model.
5. Use external tools through adapters, not merged into core.
6. Support docked, undocked, and fullscreen external app states.
7. Use local Windows GPU workers from the VPS via secure tunnel.
8. Add proof gates for every phase.

Non-negotiable:
- Never commit to main/master.
- No raw shell passthrough from VPS to worker.
- No printer write-control until safety gates pass.
- No UI-Final merge until screenshot gates pass.
- No release if any hard gate fails.

Start with Phase 0 baseline, then Phase 1 registry validator.
```
