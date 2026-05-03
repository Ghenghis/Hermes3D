# ENHANCEMENT_QUEUE.md — non-gate work queue

> Same claim convention as GATE_GAP_QUEUE. Items here are improvements
> that don't add a gate but do add capability. Pickup order: priority
> then domain locality (claim things adjacent to your current work).

---

## P0 (3 items)

### enh-2026-05-03-001 — lm-studio-provider-implementation
- domain: providers
- status: unclaimed
- evidence: Task 4a brief never converted to PR; LMStudioProvider Enum exists, BaseLLMClient subclass missing
- estimated-effort: M

Brief: `handoffs/HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md`. Implementation
must:
1. Add `LMStudioClient(BaseLLMClient)` in `03_implementation/src/hermes3d/core/providers/lmstudio_client.py`
2. Wire as default in `llm_policy.yaml` (or schema-permissible equivalent)
3. Relax `^https://` schema to allow `^http://localhost(:[0-9]+)?$` for local
4. Smoke test against Hermes-4-14B-FP8 weights (NousResearch)
5. Falls back to OllamaClient if LM Studio offline

### enh-2026-05-03-002 — service-health-page-completion
- domain: ui
- status: claimed:claude-impl-h3d-svchealth
- evidence: PR #37 partial; ServiceCard missing, /api/health/services unwired
- estimated-effort: M

Complete the service health page per Codex's audit on PR #37. Land as
`feat/cp-h3d-service-health-complete` (separate from #37 to keep #37
audit-of-record clean).

### enh-2026-05-03-003 — injection-scanner-full-port
- domain: security
- status: unclaimed
- evidence: PR #37 has stub at `03_implementation/src/hermes3d/core/security/`; needs full port from Hermes Agent
- estimated-effort: L

Port the full `injection_scanner.py` from `NousResearch/hermes-agent`
v0.12.0. Adapt to Hermes3D's I/O surface. Add unit tests covering OWASP
LLM-01 patterns.

---

## P1 (4 items)

### enh-2026-05-03-004 — registry-format-fix
- domain: tool-registry
- status: unclaimed
- evidence: PR #37 audit found `registry.py` format failure
- estimated-effort: S

Run `ruff format` on the file, push commit. Already a 1-line CI failure.

### enh-2026-05-03-005 — readme-versioning-cleanup
- domain: docs
- status: unclaimed
- evidence: PR #36 merged but README still references v0.5.0 in places where 0.6 hardening landed
- estimated-effort: S

Search `README.md` + `site/` for references to old gate counts; sync
to current count.

### enh-2026-05-03-006 — gradio-launcher-screenshot-22
- domain: docs / marketing
- status: unclaimed
- evidence: H3D-SCREENSHOT-CAPTURE listed in roadmap; needs launcher running
- estimated-effort: M

Playwright-driven capture of 22 launcher screenshots for marketing site.
Depends on launcher being demoable (LM Studio integration helpful).

### enh-2026-05-03-007 — vhs-demo-render
- domain: docs / marketing
- status: unclaimed
- evidence: H3D-VHS-DEMO listed in roadmap
- estimated-effort: S

Author + render `site/demos/quickstart.tape`. Depends on CLI being
demoable.

---

## P2 (2 items)

### enh-2026-05-03-008 — orchestrator-anonymous-rotation-v0.7
- domain: orchestration
- status: unclaimed
- evidence: roadmap v0.7; published pattern (claude-flow, OpenHands, A2A, MetaGPT)
- estimated-effort: L

Anonymous role-rotation: builder/critic/scribe roles assigned to whichever
agent claims first. Reference: `reference_adversarial_code_review.md`.

### enh-2026-05-03-009 — codebase-reorganization
- domain: structure
- status: unclaimed
- evidence: user request for "section by section organized professional codebase"
- estimated-effort: L

Section-by-section folder rewrite. NOT to be claimed without explicit
approval — touches everything.

---

## Bookkeeping

- 2026-05-03 11:30Z — initial seed by Claude SCRIBE
