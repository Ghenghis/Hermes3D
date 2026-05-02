# Phase 3.4 — Real Provider Probes

## Summary

- Adds the bounded `ProviderProbeGateway` and MiniMax/DeepSeek provider adapter substrate.
- Wires `provider.probe`, R9 probe freshness, R10 probe budget refusal, and an operator-only probe CLI.
- Adds a read-only bridge provider-health route and a non-gating Gen3D provider status dot.
- Preserves Phase 3.3 deterministic/template fallback and default `default_mode: template`.

## Refusal rules

- R9 provider not probe-verified: `llm.complete` for a non-fixture provider is refused when no recent successful `provider.probe` row exists; planner falls back to template.
- R10 probe budget exhausted: `provider.probe` token issuance or probe execution is refused when the probe budget/rate boundary would be exceeded; `budget.exceeded` evidence is ledgered.

## Bundle

- Path: `06_release/phase3.4-bundle/a10d7b7ab6b4-20260502T221536Z.zip`
- SHA-256: `97a08570cb4989c2b468de417d5594dfdd0cd32044ea4433de17412c5897730f`
- Verified: `true`

## Test plan

- [x] `cd 03_implementation && python -m pytest ../04_testing/pytest -q` — 662 passed
- [x] `cd 03_implementation && python -m pytest ../04_testing/pytest/unit/gateways -q` — 47 passed
- [x] `cd 03_implementation && python -m pytest ../04_testing/pytest/unit/cli -q` — 4 passed
- [x] `cd 03_implementation && python -m pytest ../04_testing/pytest/integration -q` — 37 passed
- [x] `cd 03_implementation && python -m ruff check src ../04_testing/pytest`
- [x] `cd 03_implementation && python -m ruff format --check src ../04_testing/pytest`
- [x] `cd 03_implementation/ui && npm run lint`
- [x] `cd 03_implementation/ui && npm run build`
- [x] `cd 03_implementation/ui && npx playwright test --reporter=list` — 16 passed
- [x] `python 02_architecture/scripts/scaffolding/phase3_4_proof.py --playwright-json 03_implementation/ui/playwright-report.json` — bundle verifier passed

## Out of scope (deferred)

- Real 3D providers.
- Default real-provider routing.
- UI provider config editing.
- Phase 4 write capabilities.
- Streaming.
- Function-calling.
- Multi-provider routing or fallback chains.

## Reviewer checklist

- [ ] ADR-012 read
- [ ] PHASE3_4_PLAN.md read
- [ ] Bundle verifier output reviewed
- [ ] Ledger snapshot rows confirmed (`provider.probe` pass, `provider.probe` fail, `budget.exceeded` with `provider.probe`, `llm.complete`)
- [ ] No LLM/provider SDK import outside allowed gateway/provider files
- [ ] Bridge route is read-only and UI dot is non-gating

🤖 Generated with [Claude Code](https://claude.com/claude-code)
