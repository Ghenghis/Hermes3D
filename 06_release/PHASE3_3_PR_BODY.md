# Phase 3.3 — LLM Planner Gateway

## Summary

- Adds the bounded LLM gateway with policy validation, sanitizer, redaction, budget checks, and injected-caller-only completion.
- Integrates planner LLM mode with deterministic template fallback and ledger evidence.
- Surfaces `metadata.planner_mode` through the existing bridge plan-preview envelope.
- Adds a 3D Generation mode indicator for validated DAG previews.

## Refusal rules

- R7 budget exhausted: `llm.complete` is refused when per-run or per-day budget would be exceeded; planner falls back to template.
- R8 planner output rejected: malformed, unsafe, or unregistered planner output is rejected; planner falls back to template.

## Bundle

- Path: `06_release/phase3.3-bundle/4ae16075915a-20260502T114728Z.zip`
- SHA-256: `a5a77b55981ddc1f9b81ac59f47a633ff61f12a8b7b7c6dd9ce00f46355bc47a`
- Verified: `true`

## Test plan

- [x] `python -m ruff check 03_implementation/src/hermes3d 04_testing/pytest 02_architecture/scripts/scaffolding/phase3_3_proof.py`
- [x] `python -m pytest 04_testing/pytest/unit/gateways -q` — 31 passed
- [x] `python -m pytest 04_testing/pytest/unit/planner -q` — 8 passed
- [x] `python -m pytest 04_testing/pytest/integration -q` — 28 passed
- [x] `cd 03_implementation/ui && npm run lint`
- [x] `cd 03_implementation/ui && npm run build`
- [x] `cd 03_implementation/ui && npx playwright test --reporter=list` — 13 passed
- [x] `python 02_architecture/scripts/scaffolding/phase3_3_proof.py --playwright-json 03_implementation/ui/playwright-report.json` — bundle verifier passed

## Out of scope (deferred)

- Phase 3.4 real providers.
- Phase 3.4 provider chips.
- Phase 4 write capabilities.
- Streaming.
- Function-calling.
- Real provider gateway.

## Reviewer checklist

- [ ] ADR-011 read
- [ ] PHASE3_3_PLAN.md read
- [ ] Bundle verifier output reviewed
- [ ] Ledger snapshot rows confirmed
- [ ] No LLM SDK outside gateways/llm.py

🤖 Generated with [Claude Code](https://claude.com/claude-code)
