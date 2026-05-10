# Hermes Agent multi-version CI handoff (Wave 2 P3-3, 2026-05-09)

Owner: claude-lead-p3-3-gha-proof
Task ID: P3-3-MULTI-VERSION-CI-2026-05-09
Branch: claude/p3-3-multi-version-gha-proof
PR target: claude/v013-promotion-flip
Workflow: .github/workflows/hermes-agent-versions.yml

## 1. Why this workflow exists (Wave 2 gate)

After PR #160 (squash 3158a4e) promoted Hermes Agent v0.13 (v2026.5.7
"Tenacity Release") to the production default, the v0.12 (v2026.4.30)
checkout at G:/Github/hermes-agent-fresh became the operator rollback
path. Wave 2 added two regression-pin pytest suites that lock that
contract on both sides:

- PR #163 — test_v012_fallback_regression_pin.py (8 surfaces under
  HERMES_AGENT_CHECKOUT=fresh).
- PR #165 — test_v013_default_regression_pin.py (8 surfaces with the
  env unset, exercising the post-Wave-1 default).

Plus the per-call resolver suite from PR #155
(test_agent_checkout_resolver.py, 11 tests).

This workflow is the Wave 2 gate that runs all 27 tests on every push
that touches the contract surfaces, so a future commit cannot silently
break either version's behavior.

## 2. What this workflow tests on each OS

Matrix: ubuntu-24.04 + windows-latest, Python 3.11 only, fail-fast=false.

Per OS, the workflow:

1. Checks out the source.
2. Installs Python 3.11 (cached pip).
3. Installs minimal deps: pytest, fastapi, httpx, pydantic. No
   `pip install -e .` because the regression suites are env-mocked and
   path-mocked; they only need PYTHONPATH=03_implementation/src.
4. Runs the three pytest files end to end with `--tb=short` and the
   resolver default left intact (HERMES_AGENT_CHECKOUT unset =>
   resolver returns v0.13 per Wave 1 promotion). The v0.12 suite
   uses pytest's monkeypatch.setenv internally, per the recommended
   pattern in pytest docs (see Sources, ref [2]).
5. Captures host + interpreter summary (always, even on failure) so
   the matrix log makes the OS / Python diff obvious at a glance.

The matrix uses `fail-fast: false` (per [1]) so an Ubuntu failure
does NOT mask Windows breakage and vice versa — both rows run to
completion and the job summary shows two independent dots.

### Why both Ubuntu and Windows?

- Ubuntu = server-style CI hosts where most contract drift is
  caught (`ci.yml` already covers Ubuntu).
- Windows = where v0.13 actually runs in production. The
  Tenacity Release ships a Windows TUI guard the v0.12 line does
  not have, so any subprocess / path / encoding regression that
  is Windows-specific (line endings, drive letters, console
  encoding) only shows up on the Windows row.

A red bar on either OS = the rollback path is half-broken or the
production default is half-broken.

## 3. What this workflow does NOT test

- **Live HTTP probes against MiniMax / DeepSeek.** Those are
  manual operator drills with real API keys; CI must never carry
  them. Surface 6 in the v0.13 pin file asserts the
  *constructed request shape* (URL, headers, bearer scheme)
  without a network call.
- **Real subprocess execution of git/npm/pytest gates inside the
  v0.12 / v0.13 checkouts.** The runners cannot host those repos.
  Surface 5 stubs `subprocess.run` / `_check_external` /
  `_check_command`.
- **Filesystem existence of G:/Github/hermes-agent-fresh or
  G:/Github/hermes-agent-v013-canary.** Both regression suites
  only assert `Path(str)` equality; they never call `.exists()`.
  Confirmed by reading both pin files end to end before authoring
  this workflow (see PR body for exact line references).

## 4. When to add a new OS / Python row

Add a row when one of the following triggers fires:

- **macOS host parity matters.** If a Hermes Agent release adds
  Mac TUI / clipboard / notification support, add `macos-14`.
- **Python 3.12 in production.** When the Hermes3D server
  pyproject pins to >=3.12, add `python: ['3.11', '3.12']`. Until
  then, 3.11 alone matches the actual server runtime so the test
  surface tracks reality.
- **Hermes Agent v0.14 lands.** When the next upstream tag ships
  (P3-1 watcher PR will detect), add a third regression-pin suite
  and update the gated `paths` in this workflow plus the test list
  in the run step. Consider Python 3.12 at that time as well.

Do NOT add Python 3.10 / 3.13 speculatively. The contract is the
deployed runtime, not the entire support window.

## 5. How to debug a failure

### Symptom: pytest collection error on either OS

Most likely cause = a transitive import in hermes3d.* needs a dep
not in the minimal install list (currently pytest + fastapi + httpx
+ pydantic). Add the missing dep to the install step and rebase.

### Symptom: only Windows fails (Ubuntu green)

- Path normalization. Check `Path("G:/Github/...")` assertions —
  the regression suites use forward slashes; if a sister site now
  resolves with backslashes the equality check breaks. Fix the
  source, not the test.
- Git Bash quoting. The workflow uses `shell: bash` on the test
  steps so backslash line continuation works on both runners. If
  someone removes that, Windows defaults to PowerShell and the
  multi-line pytest command silently truncates to the first line.
- Console encoding. Set `PYTHONUTF8: "1"` if any test prints
  non-ASCII (none currently do; if a future test does, this is
  the fix).

### Symptom: only Ubuntu fails (Windows green)

- A Windows-only constant leaked into a sister site. Check
  `BUILTIN_RUNTIME_PROBES["hermes_agent"]["path"]` and
  `SOURCE_OVERRIDES["hermes_agent"]["local_path"]` — if either
  is being constructed via a Windows-only API (e.g.
  `winreg`, `os.startfile`) the Linux row will explode at import.
- Case-sensitivity. The regression suites assert
  `Path("G:/Github/hermes-agent-fresh")` exactly — Linux is
  case-sensitive but Path comparison via PurePath stringifies the
  same way; if a sister site lowercases or capitalizes the path,
  the assert fails ONLY on Linux.

### Where to look in the GHA logs

- The `Run resolver + v0.12 + v0.13 regression pins` step shows
  per-test PASS/FAIL with `--tb=short` (one screen per failure).
- The `Capture host + interpreter summary` step always runs (even
  on failure) and prints `OS:` / `Python:` / `Executable:` so the
  matrix-cell delta is obvious.

### One-shot manual trigger

To re-run after a fix without pushing, use the GitHub UI:
Actions → hermes-agent-versions → Run workflow → pick branch.
The workflow has `workflow_dispatch:` declared.

## 6. Sources cited

[1] GitHub Actions matrix strategy — fail-fast and matrix shape.
    https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
    Read for: matrix.os syntax, fail-fast=false semantics
    (queued + in-progress jobs both continue when one fails).

[2] pytest skip / xfail and platform-conditional tests.
    https://docs.pytest.org/en/stable/how-to/skipping.html
    Read for: `pytest.mark.skipif(sys.platform == "win32", ...)` —
    the canonical OS-conditional pattern. Currently UNUSED here
    (both regression suites are platform-portable by design), but
    documented as the lever to pull if a future surface really is
    Windows-only.

[3] 12-Factor App config rule III (env-driven config).
    https://12factor.net/config
    Read for: justification of HERMES_AGENT_CHECKOUT being the
    single contract knob — the workflow leaves it unset to test the
    default, and the v0.12 suite mutates it via monkeypatch.

## 7. Local re-run gate

The workflow's contract was verified locally before merge by:

```text
PYTHONPATH=03_implementation/src python -m pytest -v --tb=short \
  04_testing/pytest/unit/test_agent_checkout_resolver.py \
  04_testing/pytest/unit/test_v012_fallback_regression_pin.py \
  04_testing/pytest/unit/test_v013_default_regression_pin.py
```

Result on Windows + Python 3.14: 27 passed in 2.40s.
The CI workflow will run the same three suites on Python 3.11
(matching the deployed runtime) on Ubuntu + Windows.

## 8. First-run feedback plan

After merge, the workflow runs automatically on the first push that
touches a gated path. To force-trigger it before that:

```text
gh workflow run hermes-agent-versions \
  --ref claude/v013-promotion-flip
```

Expected first-run URL pattern:
`https://github.com/Ghenghis/h3d-gui-wiring-codex/actions/workflows/hermes-agent-versions.yml`

If the first run red-bars:

1. Capture the failing matrix cell (OS + Python).
2. Apply section 5 debug steps.
3. Open a follow-up commit on this branch (NEW commit, never
   `--amend`). The workflow re-runs automatically because
   `.github/workflows/hermes-agent-versions.yml` is in the gated
   paths list.
