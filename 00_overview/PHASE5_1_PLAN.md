# Phase 5.1 (initial) — Kit Hardening: end-to-end wiring + operational ops

**Status:** plan + scope only · no source edits yet.
**Architecture references:** [`02_architecture/adr/ADR-013-kit-hardening-v5_1.md`](../02_architecture/adr/ADR-013-kit-hardening-v5_1.md), [`00_overview/contract/ROADMAP.md`](contract/ROADMAP.md) (v5.1 section), [`00_overview/contract/HONESTY_LEDGER.md`](contract/HONESTY_LEDGER.md).
**Branch:** `feat/phase-5-1-kit-hardening` (forks from `develop` after Phase 3.4 merge at `e25fe7e`).
**Scope discipline:** smaller than Phase 3.4 — no new product features, no real-provider routing, no write-action expansion, no UI surface changes beyond a new test layer for the existing Gradio launcher.

---

## 1. Objective

Move every `core.*` module that the ROADMAP marks as "v5.1 next" from "module-runnable" to **end-to-end-wired and operationally exercised**. The HONESTY_LEDGER already lists these modules as `runnable` (each has unit tests). v5.1 closes the gap between "unit-tested module" and "wired into the live operational loop":

- `failure_predictor` reads from a real `print_history` ledger end-to-end (not a fixture)
- `backup` runs on a scheduled tick under the supervisor daemon (not just a tar.gz round-trip in tests)
- `profile_generator` auto-derives suggestions from `skill_store` (not just from explicit input)
- `doctor` reports a real Windows + WSL prerequisite verdict (not just env-var presence)
- New **Layer-D2 / Layer-D3** UI smoke tier exercises the Gradio launcher headlessly (the existing Layer-D2 covers the React UI; the new tier covers Gradio)
- CI matrix validated as Windows + Ubuntu × py3.11 + py3.12 (already in `.github/workflows/ci.yml` per the LEDGER; phase 5.1 verifies + adds matrix completeness gates)

---

## 2. Out of scope

The following are **NOT** in Phase 5.1. Each is deferred to a later phase with its own ADR + checkpoint:

- Real 3D providers (TRELLIS / Hunyuan3D / TripoSR / MiniMax 3D), including real 3D probes — Phase 3.5+.
- Any write capability (`printer.write`, `slicer.execute`, `gcode.send`, `blender.execute`, `printer.print_start`) — Phase 4 boundary unchanged.
- Real LLM completion routed by default — Phase 3.4's R9/R10 invariants stay; default mode remains `template`.
- Provider list editing or API-key UI surface — Phase 5.2+.
- Streaming, function-calling, tool-use LLM modes — Phase 5.2+.
- Per-provider routing or fallback chains — Phase 5.2+.
- Auto-probing on app boot, page load, or interval timers — Phase 5.2+ (still requires explicit operator trigger).
- New tabs, new dock states, or new UI primitives.
- Removal of the Phase 3.3 fixture path or the Phase 3.4 probe-first invariant.

---

## 3. File / module list

### Python — wiring + operational ops

| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `00_overview/PHASE5_1_PLAN.md` | CP5.1-A | new | this plan |
| `02_architecture/adr/ADR-013-kit-hardening-v5_1.md` | CP5.1-A | new | wiring contract: end-to-end loop boundaries, supervisor scheduler hook, doctor surface |
| `03_implementation/src/hermes3d/intelligence/failure_predictor.py` | CP5.1-B | modify (additive) | accept a `PrintHistoryReader` protocol; default to live `print_history` source; remove fixture-only paths |
| `03_implementation/src/hermes3d/farm/print_history.py` | CP5.1-B | modify (additive) | expose a thin `PrintHistoryReader` interface (read-only iter / since(ts) / by_printer(id)); existing append API unchanged |
| `03_implementation/src/hermes3d/supervisor/daemon.py` | CP5.1-B | modify (additive) | scheduler tick wires `farm.backup.run_scheduled_backup()` per `BackupPolicy.interval_minutes`; tick is opt-in via config |
| `03_implementation/src/hermes3d/farm/backup.py` | CP5.1-B | modify (additive) | new `run_scheduled_backup(state_dir, target_dir, *, now)` helper; existing API unchanged |
| `03_implementation/config/backup_policy.yaml` | CP5.1-B | new | small policy file: `enabled: false` default, `interval_minutes: 60`, `retain_count: 24`, `target_dir: ./var/backups/<utc>` |
| `03_implementation/src/hermes3d/slicer/profile_generator.py` | CP5.1-C | modify (additive) | accept optional `SkillStoreReader`; when present, derive (printer × material × quality) suggestions from skill rows; deterministic fallback when None |
| `03_implementation/src/hermes3d/memory/skill_store.py` | CP5.1-C | modify (additive) | expose `SkillStoreReader` protocol matching the four query shapes profile_generator needs |
| `scripts/doctor.ps1` | CP5.1-C | modify | add Windows-specific prerequisite checks: WSL2 presence, kernel version, distro list, distro user, repo bind mount, ports 80/8080/4408 free |
| `scripts/doctor.sh` | CP5.1-C | modify | mirror in bash; on macOS skip WSL; on Linux check distro + Python toolchain + libGL |

### UI / Gradio — new test layer (no UI changes)

| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `04_testing/playwright/gradio_smoke.spec.ts` | CP5.1-D | new | Layer-D3 — headless Gradio smoke: launch app, hit each major panel, screenshot |
| `04_testing/playwright/playwright.gradio.config.ts` | CP5.1-D | new | separate config so the React Layer-D2 suite stays unaffected |
| `.github/workflows/ui-ci.yml` | CP5.1-D | modify (additive) | add new job `Layer D3 — Gradio smoke (linux × py3.11)` after the existing D2 job |

### CI / matrix verification

| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `.github/workflows/ci.yml` | CP5.1-D | modify (additive) | assert matrix completeness: a single `Layer M — matrix coverage` step verifies all 4 cells (windows/ubuntu × 3.11/3.12) reported success in the Layer-B job; fails if any cell is missing |
| `02_architecture/scripts/scaffolding/phase5_1_proof.py` | CP5.1-E | new | proof bundle assembler + verifier (mirrors `phase3_4_proof.py` shape) |

### Tests / fixtures

| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `04_testing/pytest/integration/test_failure_predictor_e2e.py` | CP5.1-B | new | seed a real `print_history` JSONL, run predictor end-to-end, assert calibrated probability + citations match seeded outcomes |
| `04_testing/pytest/integration/test_backup_scheduler.py` | CP5.1-B | new | start supervisor daemon with `interval_minutes=0.05` (3 s) and `enabled=true`; assert two backup files appear in `target_dir` within 8 s and the older one is pruned at retain_count=1 |
| `04_testing/pytest/integration/test_profile_generator_skill_wired.py` | CP5.1-C | new | seed skill_store with two reinforced rows; assert generated profile reflects the reinforced overrides; deterministic fallback proven by reading with no skill store |
| `04_testing/pytest/unit/scripts/test_doctor_windows.py` | CP5.1-C | new | parse `scripts/doctor.ps1` JSON output against fixed transcripts: WSL present, WSL absent, kernel old |
| `04_testing/pytest/unit/scripts/test_doctor_unix.py` | CP5.1-C | new | parse `scripts/doctor.sh` JSON output for macOS + Linux fixtures |

### Docs / completion

| Path | Checkpoint | Status | Purpose |
|---|---|---|---|
| `00_overview/PHASE5_1_COMPLETION_REPORT.md` | CP5.1-E | new | completion report; mirrors PHASE3_4_COMPLETION_REPORT.md structure |
| `06_release/PHASE5_1_PR_BODY.md` | CP5.1-E | new | PR body |
| `06_release/phase5.1-bundle/<run_id>.zip` | CP5.1-E | generated | proof bundle |
| `06_release/phase5.1-bundle/<run_id>.manifest.json` | CP5.1-E | generated | bundle manifest |
| `06_release/phase5.1-bundle/<run_id>.sha256` | CP5.1-E | generated | bundle digest sidecar |
| `00_overview/contract/HONESTY_LEDGER.md` | CP5.1-E | modify | move four affected modules from "runnable" to "runnable + e2e-wired"; add note acknowledging the wiring tests; tier counts unchanged |
| `00_overview/contract/ROADMAP.md` | CP5.1-E | modify | mark v5.1 row complete; bump v5.2 to "next" |

---

## 4. Checkpoints

| ID | Scope | Owner | Done when |
|---|---|---|---|
| **CP5.1-A** | This plan + ADR-013 + lock-and-evidence dry run via HermesProof | `claude-lead` | PR opens; CI green on `feat/phase-5-1-kit-hardening`; evidence row appended |
| **CP5.1-B** | failure_predictor end-to-end + backup scheduler tick + 2 integration tests | `codex-impl-01` (recommended) | both integration tests pass locally and in CI; no regressions in unit suite |
| **CP5.1-C** | profile_generator + skill_store reader + doctor Win/WSL + 3 tests | `codex-impl-02` or a Claude subagent | tests pass; `python -m hermes3d.cli.doctor --json` emits a stable shape on Windows + Linux + macOS fixtures |
| **CP5.1-D** | Layer-D3 Gradio smoke spec + CI matrix completeness gate | `claude-impl-NN` (subagent) | new D3 job green; matrix coverage gate fails when intentionally broken in a draft commit, then passes when fixed |
| **CP5.1-E** | Proof bundle assembler + completion report + ledger/roadmap updates | `claude-lead` | bundle verified; ledger + roadmap updated; PR body in place |

Each checkpoint MUST: claim a HermesProof task, lock the files in §3 it intends to edit, append evidence on completion, release files, release task. Other agents requesting overlapping locks must use `hermes_request_handoff` — never overwrite.

---

## 5. Acceptance gates

`npm run truth-gates` (HermesProof side) and the existing Hermes3D `Layer A/B/C/D/D2/T/F` gates must all pass on the branch HEAD before merge. Phase 5.1 specifically adds:

- **Layer D3** — new headless Gradio smoke (CP5.1-D)
- **Layer M** — matrix coverage gate (CP5.1-D): runs after Layer-B and asserts that all 4 cells (windows/ubuntu × py3.11/py3.12) reported `SUCCESS`. Fails the workflow if any cell missing.
- **Layer P5.1** — phase 5.1 proof bundle verifier (CP5.1-E)

The honesty-gate F layer must continue to pass — no new TODO/FIXME/STUB allowed in shipped code.

---

## 6. Risks and rollback

| Risk | Mitigation |
|---|---|
| Backup scheduler tick interferes with print operations on a real machine | `enabled: false` by default; integration test uses opt-in flag with 3-second interval; production users opt in via config |
| failure_predictor wiring changes test outputs of existing 3 unit tests | Keep the existing fixture-based tests under `04_testing/pytest/unit/intelligence/`; only the new e2e test under `integration/` exercises live print_history |
| profile_generator change breaks the existing 6 unit tests | The skill_store reader is optional (default `None`); existing tests pass `None` and continue to use the deterministic path |
| Doctor script JSON shape change breaks CI consumers | Add a `--json-schema-version 1` flag; old shape stays default until v5.2 |
| Layer-D3 flakes on first CI run | Mark non-blocking on first 5 runs (`continue-on-error: true` for one PR), then promote to required after stability proven |

Rollback path: each CP is a separate commit. Reverting any CP individually is a single-commit revert that leaves the prior CPs intact.
