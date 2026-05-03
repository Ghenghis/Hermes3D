# ROADMAP — Hermes3D-OS Lite

> Honest forward-looking plan. Work that is committed lives at the top;
> work that is speculative lives at the bottom. Anything described here
> as "next" must have a tracking issue and a definition of "done".

---

## v5 (current) — Contract Kit foundation

**Status:** delivered as the present repository.

- 12-printer fleet model (6 delta + 4 cartesian + 2 CoreXY)
- Dispatcher with 8 strategies (auto/fastest/quality/largest_bed/
  smallest_fit/least_busy/delta_prefer/cartesian_prefer)
- Eight truth gates + HMAC-signed proof envelopes
- 12-node print workflow graph with atomic checkpointing
- Skill memory store (5 skill kinds) with skill-pack import/export
- Multi-LLM provider abstraction (Ollama, LM Studio, vLLM, llama.cpp,
  OpenRouter)
- Tool registry with 11 built-in tools registered against real backends
- Vector memory backend (TF-IDF + optional FAISS)
- Incident detector covering 9 incident types
- Telegram + Discord remote-control bridge
- Farm auto-discovery (Moonraker, Mainsail, Fluidd, OctoPrint, Obico)
- LangGraph adapter (exports workflow as StateGraph source)
- 264 passing tests, 48/48 acceptance variants, signed proof envelopes

---

## v5.1 — Hardening (✅ shipped v5.1.0, 2026-05-03)

**Goal:** raise every Tier-2 module to Tier-1 (runnable + tested) and
close the documented honesty-ledger gaps.

| Item | Target |
|------|--------|
| `core.farm.print_history` — JSON-backed append-only log | runnable |
| `core.intelligence.failure_predictor` — wire `PrintHistory` reads end-to-end | runnable |
| `core.farm.backup` — scheduled backups of `./var/` to `./var/backups/<utc>/` | runnable |
| `core.slicer.profile_generator` — auto-derive material/printer profiles from skill store | runnable |
| Doctor script — full prerequisite check on Windows + WSL | runnable |
| Layer-D UI smoke tests against Gradio launcher | new test tier |
| GitHub Actions CI matrix (Windows + Ubuntu, 3.11 + 3.12) | infrastructure |

**Completion evidence:** `00_overview/PHASE5_1_COMPLETION_REPORT.md` and
`00_overview/proofs/phase_5_1_proof.json`.

**Definition of done for v5.1:** every targeted kit-hardening entry is now
documented in `HONESTY_LEDGER.md` as runnable plus end-to-end wired where
evidence exists. Layer D3 exists but remains advisory until a later hard-gate
promotion.

---

## v5.2 — Multi-agent maturity (next, committed)

**Goal:** turn the multi-agent scaffolding into a daily-driver.

| Item | Notes |
|------|-------|
| Critic / Optimiser / Executor agents working against real LLM backends | replace synthetic-response paths with real Ollama / LM Studio calls |
| LangGraph runtime adapter — not just source export | optional dependency, not required for headless runs |
| Skill-pack marketplace bundle format (`.skillpack`) | signed bundles, importable via Gradio UI |
| Tool-registry-backed REPL for Dave's workflow scripting | one-off "do this then that" scripts with logged outcomes |

---

## v5.3 — Print farm dashboard polish (committed)

**Goal:** the Gradio UI hits parity with Mainsail's basic view, plus
fleet-wide dashboarding Mainsail can't do.

| Item | Notes |
|------|-------|
| Live cost-per-hour widget on every printer card | reads from `core.farm.cost_estimator` + Moonraker telemetry |
| Spool deduction trace from completed jobs | `core.farm.spool_tracker` already exposes the API; needs UI binding |
| Failure forecast tile per printer | already-tested predictor needs a tab |
| Calibration history per printer | timeline of input-shaper / pressure-advance values over weeks |

---

## Future / Pending Audits

Third-party projects evaluated for adoption. Each row points to an ADR
that records the verdict and evidence.

| Item | Status | Date |
|------|--------|------|
| Blender MCP integration path (ADR-014) | Status: REJECT | 2026-05-03 |

---

## v6 — Speculative (not yet committed)

**Anything in this section may be reshaped or dropped.** It is listed so
the design space is visible, not because the work is scheduled.

- **Distributed control plane.** Hermes3D-OS as a daemon on every Pi
  attached to a printer, with a coordinator on Dave's main rig. WebRTC
  for low-latency video, gRPC for control. Trade-off: drastically more
  ops surface area; only worth it if the printer fleet doubles.
- **Photo-based first-layer QA.** ESP32-CAM modules looking at the bed,
  feeding into a small vision model that calls `truth_gate` if the
  first layer doesn't look right. Today: Obico does this externally.
- **Material spectral identification.** A $30 NIR sensor module per
  loader to verify the spool material matches what the queue claims.
- **Co-printing handoff.** Two printers, same job: one prints the
  scaffold, one prints the part. Reduces wall-clock time for
  multi-material parts. Hard problem. Probably not worth it for a
  hobby farm.
- **Cloud-tier feature parity.** A subset of the dashboard exposed via
  a Cloudflare tunnel. Today: Telegram bridge covers the same need
  with less attack surface.

---

## Anti-roadmap

Things explicitly **not** on the roadmap, so future contributors don't
have to wonder:

- **Telemetry to Anthropic / OpenAI / anyone.** No data leaves the
  farm except via explicitly-configured LLM provider calls and
  explicitly-configured remote control bridges.
- **Cloud account requirement.** The system runs fully offline. Cloud
  is optional in every dimension.
- **Subscription gating.** No features are paywalled; the kit is
  source-available under the terms of `LICENSE`.
- **Dependency on any one LLM vendor.** The provider abstraction is
  load-bearing; we will not optimise the codebase for a single
  vendor's quirks.
- **Vendor-specific slicer integration.** PrusaSlicer and OrcaSlicer
  are first-class, both via CLI. Closed-source slicers are not.

---

## How items get on this roadmap

1. A user need or contract gap is identified.
2. The item is sketched in a `proposals/` markdown doc.
3. If the proposal is accepted, it gets a tracking issue.
4. When at least one author commits to the work, the item moves into
   the "committed" tier of this document.

That last step matters: an item is on the roadmap because someone has
agreed to do it. Wishlists live elsewhere.

---

## Cadence

There is no fixed release cadence. The contract privileges shipping
working software over schedule discipline. Releases happen when the
honesty ledger is clean and the gates are green — and not before.
