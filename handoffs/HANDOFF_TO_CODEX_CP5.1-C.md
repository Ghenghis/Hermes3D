# HANDOFF_TO_CODEX_CP5.1-C

> **Status:** READY for Codex to claim once CP5.1-B (PR not yet open) is in flight or merged. Strictly non-overlapping with CP5.1-B (different file group). Can run in parallel with B if you want — no shared files.

## 1. Mission

Implement Phase 5.1 Checkpoint C per [`PHASE5_1_PLAN.md`](../00_overview/PHASE5_1_PLAN.md) §3 (Python — wiring + operational ops, the §3 "CP5.1-C" rows) and [`ADR-013-kit-hardening-v5_1.md`](../02_architecture/adr/ADR-013-kit-hardening-v5_1.md) §1 + §3.

Three concrete additions:
1. `profile_generator.generate_profile()` accepts an optional `SkillStoreReader` for auto-derivation of (printer × material × quality) suggestions. Reader-protocol injection per ADR-013 §1.
2. `skill_store` exposes the `SkillStoreReader` Protocol matching the four query shapes the generator needs.
3. `scripts/doctor.{ps1,sh}` emit a versioned JSON envelope (`json_schema_version: 1`) per ADR-013 §3 — Windows + WSL prerequisites for `.ps1`, macOS + Linux for `.sh`.

## 2. Workspace + branch

**Workspace:** `G:\Github\Hermes3D` (HermesProof MCP wired)

**Branch base:**
- If CP5.1-A (PR #18) has merged to `develop`: branch from `develop`
- If CP5.1-A is still open: branch from `feat/phase-5-1-kit-hardening` (currently at `b1a5182` after path-fix)

**Branch name:** `feat/phase-5-1-cp-c-profile-generator-and-doctor`

## 3. Pre-flight (HermesProof)

```text
hermes_doctor                                    confirm ok=true
hermes_read_policy                               confirm workspace=G:\Github\Hermes3D
hermes_get_state                                 sanity check: no codex-impl-* locks under H3D-CP5.1-C

hermes_claim_task
  owner=codex-impl-02
  taskId=H3D-CP5.1-C
  role=implementation
  title=CP5.1-C: profile_generator + skill_store reader + doctor JSON envelope
  reason=Per ADR-013 §1 + §3, on top of CP5.1-A (b1a5182) and CP5.1-B (when merged or in-flight). Independent scope from CP5.1-B and CP5.1-D.
```

Note: `owner=codex-impl-02` (not `-01`) so HermesProof state cleanly distinguishes this checkpoint from CP5.1-B (which uses `codex-impl-01`).

## 4. Lock these exact 7 files

```text
hermes_lock_files
  owner=codex-impl-02
  taskId=H3D-CP5.1-C
  ttlMinutes=120
  files=[
    "03_implementation/src/hermes3d/core/slicer/profile_generator.py",
    "03_implementation/src/hermes3d/core/memory/skill_store.py",
    "scripts/doctor.ps1",
    "scripts/doctor.sh",
    "04_testing/pytest/integration/test_profile_generator_skill_wired.py",
    "04_testing/pytest/unit/scripts/test_doctor_windows.py",
    "04_testing/pytest/unit/scripts/test_doctor_unix.py"
  ]
```

If any lock fails → `hermes_request_handoff` against the current owner. **Do not overwrite. Do not edit any file outside this list.**

## 5. Implementation contract (read ADR-013 first)

### §1 — `SkillStoreReader` reader-protocol pattern

Add to `03_implementation/src/hermes3d/core/memory/skill_store.py` (additive — keep existing public API):

```python
from typing import Protocol, Iterable

class SkillStoreReader(Protocol):
    def by_printer(self, printer_id: str) -> Iterable[SkillRow]: ...
    def by_material(self, material: str) -> Iterable[SkillRow]: ...
    def by_quality(self, quality_level: str) -> Iterable[SkillRow]: ...
    def reinforced_only(self, *, min_score: float = 0.0) -> Iterable[SkillRow]: ...

def default_skill_store_reader() -> SkillStoreReader: ...
```

Add to `03_implementation/src/hermes3d/core/slicer/profile_generator.py`:

```python
from hermes3d.core.memory.skill_store import SkillStoreReader, default_skill_store_reader

def generate_profile(
    printer_id: str,
    material: str,
    quality_level: str,
    *,
    skills: SkillStoreReader | None = None,  # NEW: injectable, default None = deterministic
) -> Profile:
    if skills is None:
        return _deterministic_profile(printer_id, material, quality_level)
    overrides = _derive_overrides_from_skills(skills, printer_id, material, quality_level)
    return _deterministic_profile(printer_id, material, quality_level)._with_overrides(overrides)
```

Default `skills=None` → existing deterministic path (the 6 existing unit tests stay green).

### §3 — Doctor JSON envelope (`json_schema_version: 1`)

When invoked with `--json`, both `scripts/doctor.ps1` and `scripts/doctor.sh` MUST emit the exact envelope from ADR-013 §3:

```json
{
  "json_schema_version": 1,
  "platform": "windows" | "macos" | "linux",
  "checks": [
    {"id": "wsl2_present",      "ok": true|false|null, "detail": "..."},
    {"id": "kernel_version",    "ok": true|false|null, "detail": "..."},
    {"id": "python_3_11_or_12", "ok": true|false,      "detail": "..."},
    {"id": "port_8080_free",    "ok": true|false,      "detail": "..."},
    {"id": "libgl_present",     "ok": true|false|null, "detail": "..."},
    {"id": "git_present",       "ok": true|false,      "detail": "..."}
  ],
  "ok": true|false,
  "fix_hints": ["..."]
}
```

Rules:
- Platform-skipped checks return `"ok": null` and `"detail": "skipped: not applicable on this platform"`.
- `wsl2_present` + `kernel_version` are Windows-only (`null` on macOS/Linux).
- `libgl_present` is Linux-only (`null` on Windows/macOS).
- `python_3_11_or_12`, `port_8080_free`, `git_present` run on all platforms.
- `ok` (top-level) is `true` iff every non-null check is `ok: true`.
- `fix_hints` lists actionable strings for any failed check.

Keep the existing default (non-`--json`) human-readable output — `--json` is additive.

## 6. Tests (REQUIRED — all must pass)

| Path | Asserts |
|---|---|
| `04_testing/pytest/integration/test_profile_generator_skill_wired.py` | seed `skill_store` with 2 reinforced rows; `generate_profile(skills=reader)` reflects the reinforced overrides; `generate_profile(skills=None)` returns the deterministic baseline; both return profiles with stable schema |
| `04_testing/pytest/unit/scripts/test_doctor_windows.py` | parse `scripts/doctor.ps1 --json` against fixed transcripts (WSL present / WSL absent / kernel old). On non-Windows runners, mock the WSL probe; do not require real WSL |
| `04_testing/pytest/unit/scripts/test_doctor_unix.py` | parse `scripts/doctor.sh --json` against fixed transcripts (macOS + Linux). Mock libGL + python version probes; do not require real environment |

The existing 6 unit tests under `04_testing/pytest/unit/slicer/test_profile_generator.py` MUST continue to pass — they pass `skills=None` and exercise the deterministic path.

## 7. Gates (run before push)

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Then locally:
- `pytest 04_testing/pytest/unit -v` — all unit suites green (incl. existing 6 profile_generator tests + 2 new doctor tests)
- `pytest 04_testing/pytest/integration/test_profile_generator_skill_wired.py -v` — green
- `ruff format --check 03_implementation/src 04_testing/pytest`
- `ruff check 03_implementation/src 04_testing/pytest`
- `python scripts/doctor.{ps1,sh} --json | python -m json.tool` — emits valid JSON matching the envelope

CI gates that will run on the PR (do not skip): Layer A, B, C, F (honesty gates).

## 8. Commit + push + PR

```bash
git push -u origin feat/phase-5-1-cp-c-profile-generator-and-doctor
gh pr create \
  --base feat/phase-5-1-kit-hardening \
  --title "Phase 5.1 — CP5.1-C: profile_generator + skill_store reader + doctor JSON" \
  --body "<conventional summary, link ADR-013 §1 + §3, link this handoff>"
```

If PR #18 has already merged to `develop`, set `--base develop` instead.

Conventional commit message format (mirrors CP3.4 / CP5.1-A):

```
feat(phase5.1): profile_generator + skill_store reader + doctor JSON envelope (CP5.1-C)

[summary of §1 reader pattern + §3 doctor envelope]

==== Files ====
03_implementation/src/hermes3d/core/slicer/profile_generator.py   (M)
03_implementation/src/hermes3d/core/memory/skill_store.py         (M)
scripts/doctor.ps1                                                 (M)
scripts/doctor.sh                                                  (M)
04_testing/pytest/integration/test_profile_generator_skill_wired.py (A)
04_testing/pytest/unit/scripts/test_doctor_windows.py              (A)
04_testing/pytest/unit/scripts/test_doctor_unix.py                 (A)

==== Coordination ====
Task:       H3D-CP5.1-C (codex-impl-02, implementation)
Locks:      [the 7 above]
Handoff:    handoffs/HANDOFF_TO_CODEX_CP5.1-C.md
Gates run via hermes_run_gate:
  git-status      pass
  git-diff-check  pass

==== Done criteria ====
[mirror §10 below]
```

## 9. Close out (after PR opens)

```text
hermes_append_evidence
  owner=codex-impl-02
  taskId=H3D-CP5.1-C
  kind=checkpoint
  summary=CP5.1-C landed: profile_generator + skill_store reader + doctor JSON in PR #<N> (commit <SHA>). Tests: <pass-counts>.

hermes_release_files  owner=codex-impl-02  files=[...same 7]
hermes_release_task   owner=codex-impl-02  taskId=H3D-CP5.1-C
```

## 10. Done criteria

- [ ] PR open against the correct base
- [ ] All required CI checks green (Layer A, B, C, F minimum)
- [ ] All 7 locked files modified or created exactly per §5
- [ ] No file outside the lock set modified
- [ ] Existing 6 profile_generator unit tests still pass
- [ ] 3 new tests pass (1 integration + 2 doctor unit)
- [ ] `doctor.{ps1,sh} --json` round-trips through `python -m json.tool` on all 3 platforms (or fixture-mocked equivalent)
- [ ] `hermes_verify_evidence` reports chain valid after release
- [ ] `hermes_get_state` shows zero `codex-impl-02` locks remaining
- [ ] No `TODO` / `FIXME` / `STUB` introduced in any file

## 11. Hard rules (block-or-handoff if violated)

- DO NOT touch any file outside the 7 locked above. CP5.1-B owns `core/farm/`, `core/intelligence/`, `core/supervisor/`. CP5.1-D owned `04_testing/playwright/` + `.github/workflows/ci.yml` (already shipped).
- DO NOT change the public signature of `generate_profile()` — `skills` is a new keyword-only parameter with default `None`, additive only.
- DO NOT remove or reshape any of the 6 existing `test_profile_generator.py` unit tests.
- DO NOT regress the existing non-`--json` doctor output. `--json` is additive.
- DO NOT introduce new top-level dependencies (`pyproject.toml` or `requirements*.txt` MUST NOT be touched). Stick to stdlib + `pyyaml` (already a dep).
- If a lock conflict appears: `hermes_request_handoff` against the current owner. Never overwrite.

## 12. Failure protocol

If blocked, write `handoffs/HANDOFF_TO_CLAUDE_CP5.1-C_BLOCKED.md` containing:

- Branch name + tip SHA
- Locks held at time of block
- Files attempted, files succeeded, files unchanged
- Exact error output (last 50 lines, untruncated)
- Suggested fix or open question
- HermesProof evidence id of the block-event

Then: release all `codex-impl-02` locks, release task `H3D-CP5.1-C`, append evidence with `kind=block` referencing the handoff file, and stop. Do not push partial work without the handoff file.

## 13. References

- Plan: [`00_overview/PHASE5_1_PLAN.md`](../00_overview/PHASE5_1_PLAN.md) (§3 CP5.1-C rows, §4 CP5.1-C done-when, §5 acceptance gates)
- ADR: [`02_architecture/adr/ADR-013-kit-hardening-v5_1.md`](../02_architecture/adr/ADR-013-kit-hardening-v5_1.md) (§1 reader-protocol pattern, §3 doctor JSON envelope)
- HONESTY_LEDGER: [`00_overview/contract/HONESTY_LEDGER.md`](../00_overview/contract/HONESTY_LEDGER.md) (Tier 2 — `core.slicer.profile_generator` row)
- ROADMAP: [`00_overview/contract/ROADMAP.md`](../00_overview/contract/ROADMAP.md) (v5.1 row — "auto-derive material/printer profiles from skill store" + "Doctor script — full prerequisite check on Windows + WSL")
- Prior CP completion shape: [`00_overview/PHASE3_4_COMPLETION_REPORT.md`](../00_overview/PHASE3_4_COMPLETION_REPORT.md)

## 14. Architect contact

If any part of this brief is ambiguous or contradicts the ADR, write a clarification request as `handoffs/HANDOFF_TO_CLAUDE_CP5.1-C_CLARIFY.md` with the specific section quoted and the ambiguity highlighted. Claude (`owner=claude-lead`) will respond with a path-fix-style mini-PR if needed.
