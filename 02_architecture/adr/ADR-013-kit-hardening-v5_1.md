# ADR-013 — Kit Hardening for v5.1: end-to-end wiring + operational ops

**Status:** Proposed (CP5.1-A).
**Date:** 2026-05-02.
**Supersedes:** none. Builds on [ADR-009 orchestration skeleton](ADR-009-orchestration-skeleton.md), [ADR-012 real provider probes](ADR-012-real-provider-probes.md).
**Related plan:** [`PHASE5_1_PLAN.md`](../../00_overview/PHASE5_1_PLAN.md).

## Context

Hermes3D v5.0 baseline (delivered) and Phase 3.4 (real provider probes, merged at `e25fe7e`) leave four modules in a state the HONESTY_LEDGER calls "runnable" but which the ROADMAP v5.1 row asks to be **end-to-end wired**:

- `core.intelligence.failure_predictor` — has unit tests, but its `PrintHistory` reads in production go through a fixture-derived adapter, not the live `core.farm.print_history` JSONL.
- `core.farm.backup` — has tar.gz round-trip tests, but no scheduler invokes it.
- `core.slicer.profile_generator` — has 6 unit tests against explicit inputs, but cannot derive (printer × material × quality) suggestions from `core.memory.skill_store` rows.
- `scripts/doctor.{ps1,sh}` — verifies env vars but does not exercise platform-specific prerequisites (WSL2, kernel version, port availability, libGL).

This ADR fixes the contract for what those wirings must look like, so multiple agents (Claude, Codex, Windsurf) can execute the implementation in parallel without re-litigating the boundaries.

## Decision

### 1. Reader-protocol injection, not direct imports

Each consumer takes its data dependency as a **reader protocol** parameter with a sane production default. This keeps unit tests fixture-driven while letting integration tests exercise the live wire.

```python
# core/farm/print_history.py
class PrintHistoryReader(Protocol):
    def iter_jobs(self) -> Iterator[CompletedJob]: ...
    def since(self, ts_utc: datetime) -> Iterator[CompletedJob]: ...
    def by_printer(self, printer_id: str) -> Iterator[CompletedJob]: ...

# core/intelligence/failure_predictor.py
def predict(
    printer_id: str,
    material: str,
    *,
    history: PrintHistoryReader | None = None,  # new: injectable
) -> FailureProbability:
    history = history or default_print_history_reader()  # NEW production default
    ...
```

The fixture-based unit tests pass an in-memory `FakePrintHistoryReader`. The new integration test seeds a real `print_history.jsonl` and lets `default_print_history_reader()` discover it.

`core.slicer.profile_generator.generate_profile()` follows the identical pattern with `SkillStoreReader`.

### 2. Scheduler tick for `farm.backup`

The supervisor daemon already exists (`core.supervisor.daemon` — Tier 3, 2 tests). v5.1 adds **one** scheduler hook:

```python
# core/supervisor/daemon.py
class SupervisorDaemon:
    async def _on_tick(self, now: datetime) -> None:
        ...
        if self._backup_policy.enabled and self._is_due(now, last=self._last_backup_at):
            await asyncio.to_thread(
                run_scheduled_backup,
                state_dir=self.state_dir,
                target_dir=self._backup_policy.target_dir,
                now=now,
            )
            self._last_backup_at = now
```

`BackupPolicy.enabled` defaults to **false**. Operators opt in via `config/backup_policy.yaml`.

`run_scheduled_backup()` is a thin wrapper over the existing `backup.create_archive()`; it adds retention pruning by sorting `target_dir/*.tar.gz` and removing the oldest beyond `retain_count`.

### 3. Doctor script JSON contract

`scripts/doctor.{ps1,sh}` must emit a stable JSON envelope when invoked with `--json`:

```json
{
  "json_schema_version": 1,
  "platform": "windows" | "macos" | "linux",
  "checks": [
    {"id": "wsl2_present",      "ok": true|false, "detail": "..."},
    {"id": "kernel_version",    "ok": true|false, "detail": "..."},
    {"id": "python_3_11_or_12", "ok": true|false, "detail": "..."},
    {"id": "port_8080_free",    "ok": true|false, "detail": "..."},
    {"id": "libgl_present",     "ok": true|false, "detail": "..."},
    {"id": "git_present",       "ok": true|false, "detail": "..."}
  ],
  "ok": true|false,
  "fix_hints": ["..."]
}
```

`json_schema_version` lets v5.2+ evolve the shape without breaking CI consumers. New checks added in later phases bump the version.

Platform-specific checks (`wsl2_present`, `libgl_present`) emit `{"ok": null, "detail": "skipped: not applicable on this platform"}` when run on a platform where they don't apply.

### 4. Layer-D3 (Gradio smoke) is non-gating on first 5 CI runs

Per the Risk-Mitigation table in the plan: the new headless Gradio smoke job is `continue-on-error: true` on first 5 runs to gather flake data, then promoted to required.

### 5. Matrix coverage gate as a workflow step, not a status check

Adding a status check requires touching repo branch protection. Instead, a single shell step in the `Layer M` job parses `${{ needs.layer-b.result }}` and `${{ steps.*.outcome }}` to verify all 4 cells reported `success`. Failure of this step fails the job and breaks the merge gate via the existing required-checks rule.

## Consequences

**Positive:**
- Four modules go from "module-runnable" to "operational-loop-runnable" without changing their public surface.
- Integration tests are added without disturbing existing unit suites.
- The Reader-protocol pattern becomes a reusable convention for any future "wire X to Y" work in v5.2+.
- Operators get scheduled backups and a real prerequisite check on Windows.

**Negative:**
- The supervisor daemon becomes responsible for one more periodic action; the test that seeds a 3-second tick interval relies on real time, which is mildly flaky on slow CI runners. Mitigated by `pytest.mark.flaky(reruns=2)`.
- Two new Layer-D3 / Layer-M CI jobs increase runtime by ~90 s; acceptable given they catch real classes of regression.

**Neutral:**
- No public API changes for users running `hermes3d` from the CLI. All new behavior is opt-in via config (`backup_policy.enabled`) or invisible (Reader injection).
- Phase 4 write-action boundary unchanged.

## Alternatives considered

1. **Singleton imports.** Rejected: re-introduces the global-mutable-state coupling the v5.0 design explicitly avoided.
2. **Cron-based backup outside the daemon.** Rejected: adds an OS-specific external dependency; makes Windows-vs-Linux behavior diverge at a layer the kit otherwise unifies.
3. **Stick with one CI cell + ad-hoc Windows tests.** Rejected: HONESTY_LEDGER already lists `ci.yml` as runnable; the matrix-coverage gate exists to prevent silent matrix regressions during Phase 5.2+ work.

## Status of the four ledger rows after CP5.1-E

| Module | Before v5.1 | After v5.1 |
|---|---|---|
| `core.intelligence.failure_predictor` | runnable (unit) | runnable (unit) + e2e-wired |
| `core.farm.backup` | runnable (unit) | runnable (unit) + scheduled |
| `core.slicer.profile_generator` | runnable (unit) | runnable (unit) + skill-wired |
| `scripts/doctor.{ps1,sh}` | runnable (env-vars) | runnable (full prerequisite) |

`HONESTY_LEDGER.md` gets updated in CP5.1-E to reflect this.
