# Batch2-Agent10 — Compatibility-patch proposal (read-only research output)

**Lane**: H3D-60APP-UPDATE-READINESS-AUDIT / Batch 2 / Agent 10. **No source mutation** — diffs are proposals; Batch 3 reviews, Batch 4 (with user go-ahead) applies.

## Lane classification

**Hermes3D wrapper issue** — confirmed. Bug is in our gate, not upstream. Upstream `tests.yml` already uses path-based `--ignore`; our wrapper still uses marker-only `-m "not integration"`, which (per Batch 1 Agent 3) cannot defend against `tests/e2e/conftest.py` `sys.modules` contamination because `--ignore` runs at collection time **before** conftest body imports while `-m` runs **after**. Our skip path also returns `status:"skipped"` (CICD-SEC-1 fake-pass per Agent 6). All three are wrapper-side fixes.

## Unified diff #1 — `_run_update_checks` patch

Target: `G:/Github/h3d-gui-wiring-codex/03_implementation/src/hermes3d/api/routes/agent_updates.py`, function `_run_update_checks` only (lines 345-360).

```diff
--- a/03_implementation/src/hermes3d/api/routes/agent_updates.py
+++ b/03_implementation/src/hermes3d/api/routes/agent_updates.py
@@ -345,18 +345,68 @@ def _run_update_checks(repo: Path) -> list[dict[str, Any]]:
         tests_dir = repo / "tests"
-        if os.environ.get("HERMES_AGENT_RUN_PYTEST") == "1" and tests_dir.exists():
-            checks.append(_check_external(repo, "python pytest non-integration", ["python", "-m", "pytest", str(tests_dir), "-m", "not integration", "--maxfail=1", "-q"], timeout=300))
-        elif tests_dir.exists():
-            checks.append({"name": "python pytest non-integration", "status": "skipped", "output": "Set HERMES_AGENT_RUN_PYTEST=1 to run the full Hermes Agent pytest gate in this environment."})
+        # Hermes Agent pytest gate — security-hardened (Batch 2 Agent 6 must-fix).
+        # Path-based --ignore mirrors upstream tests.yml. Marker-only filtering
+        # cannot prevent tests/e2e/conftest.py from polluting sys.modules at
+        # collection time. Receipts:
+        #   https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml
+        #   https://docs.pytest.org/en/stable/example/pythoncollection.html#ignore-paths-during-test-collection
+        # Worker-count guard (must-fix #2): -n 0/1 disables xdist isolation,
+        # re-exposing conftest leak. Production requires >=2; HERMES_AGENT_DIAGNOSTIC=1 overrides.
+        # maxfail guard (must-fix #4): production stops at 1; diagnostic raises to 5.
+        # Skip-path fail-closed (must-fix #1): missing HERMES_AGENT_RUN_PYTEST surfaces
+        # as fail+REQUIRES_CONFIRMATION, never 200 skipped/OK. Blocks CICD-SEC-1 fake-pass per
+        #   https://owasp.org/www-project-top-10-ci-cd-security-risks/
+        #   https://about.codecov.io/apr-2021-post-mortem/
+        if os.environ.get("HERMES_AGENT_RUN_PYTEST") == "1" and tests_dir.exists():
+            workers_env = os.environ.get("HERMES_AGENT_PYTEST_WORKERS", "auto").strip()
+            diagnostic_mode = os.environ.get("HERMES_AGENT_DIAGNOSTIC", "").strip() == "1"
+            if workers_env != "auto":
+                try:
+                    parsed_workers = int(workers_env)
+                except ValueError as exc:
+                    raise HTTPException(
+                        status_code=400,
+                        detail=f"HERMES_AGENT_PYTEST_WORKERS must be 'auto' or positive integer; got {workers_env!r}.",
+                    ) from exc
+                if parsed_workers < 0:
+                    raise HTTPException(status_code=400,
+                        detail="HERMES_AGENT_PYTEST_WORKERS must be 'auto' or a positive integer.")
+                if not diagnostic_mode and parsed_workers < 2:
+                    raise HTTPException(status_code=400, detail=(
+                        "HERMES_AGENT_PYTEST_WORKERS<2 disables xdist isolation; "
+                        "set HERMES_AGENT_DIAGNOSTIC=1 to override in triage."))
+            maxfail = "5" if diagnostic_mode else "1"
+            pytest_args = [
+                "python", "-m", "pytest", str(tests_dir),
+                "-m", "not integration",
+                "--ignore=tests/integration",
+                "--ignore=tests/e2e",
+                f"--maxfail={maxfail}",
+                "-q",
+                "-n", workers_env,
+            ]
+            checks.append(_check_external(repo, "python pytest non-integration", pytest_args, timeout=600))
+        elif tests_dir.exists():
+            checks.append({
+                "name": "python pytest non-integration",
+                "status": "fail",
+                "output": (
+                    "REQUIRES_CONFIRMATION: HERMES_AGENT_RUN_PYTEST not set to '1'. "
+                    "Pytest gate cannot certify update without explicit opt-in. "
+                    "Re-run with HERMES_AGENT_RUN_PYTEST=1 (and optionally "
+                    "HERMES_AGENT_PYTEST_WORKERS=auto) to certify."
+                ),
+            })
     return checks
```

**Reviewer notes**: `HTTPException(400)` propagates up through `staged_update` (line 116) without invoking `_auto_repair_to_backup` — bad env config is a 4xx caller error, not a runtime regression. Caller line 130 already produces `stopped_on_unverified_check` for `skipped`; flipping to `fail` produces `stopped_on_failed_check` AND triggers auto-repair (intended).

## Unified diff #2 — meta-test new file

Target: `G:/Github/h3d-gui-wiring-codex/04_testing/pytest/unit/test_agent_updates_meta.py` (new).

```diff
--- /dev/null
+++ b/04_testing/pytest/unit/test_agent_updates_meta.py
@@ -0,0 +1,58 @@
+"""Meta-test: Hermes Agent pytest gate must mirror upstream tests.yml flags.
+
+If upstream removes --ignore=tests/integration or --ignore=tests/e2e from
+.github/workflows/tests.yml, our wrapper's path-based ignore is now hiding
+e2e regressions. Fail loud so we re-evaluate.
+"""
+
+from __future__ import annotations
+
+import os
+from pathlib import Path
+
+import pytest
+
+requests = pytest.importorskip("requests")  # offline CI: skipped, never errored.
+
+UPSTREAM_TESTS_YML = (
+    "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml"
+)
+IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3] / "03_implementation"
+AGENT_UPDATES_PY = IMPLEMENTATION_ROOT / "src" / "hermes3d" / "api" / "routes" / "agent_updates.py"
+
+
+def _is_offline() -> bool:
+    return os.environ.get("HERMES_META_TESTS_OFFLINE", "").strip() == "1"
+
+
+@pytest.mark.skipif(_is_offline(), reason="HERMES_META_TESTS_OFFLINE=1; skipping live network meta-test.")
+def test_upstream_tests_yml_still_uses_path_ignores() -> None:
+    try:
+        response = requests.get(UPSTREAM_TESTS_YML, timeout=10)
+    except requests.RequestException as exc:
+        pytest.skip(f"Network unavailable for upstream meta-test: {exc!r}")
+    if response.status_code != 200:
+        pytest.skip(f"Upstream returned HTTP {response.status_code}; cannot verify.")
+    body = response.text
+    assert "--ignore=tests/integration" in body, (
+        "Upstream tests.yml no longer contains '--ignore=tests/integration'. "
+        "Re-evaluate _run_update_checks before continuing the staged-update lane.")
+    assert "--ignore=tests/e2e" in body, (
+        "Upstream tests.yml no longer contains '--ignore=tests/e2e'.")
+
+
+def test_local_wrapper_mirrors_upstream_ignore_flags() -> None:
+    assert AGENT_UPDATES_PY.exists(), f"agent_updates.py not found at {AGENT_UPDATES_PY}"
+    source = AGENT_UPDATES_PY.read_text(encoding="utf-8")
+    assert '"--ignore=tests/integration"' in source
+    assert '"--ignore=tests/e2e"' in source
+    assert "REQUIRES_CONFIRMATION:" in source
+    assert 'timeout=600' in source
+
+
+def test_diagnostic_mode_required_for_lone_worker() -> None:
+    source = AGENT_UPDATES_PY.read_text(encoding="utf-8")
+    assert "HERMES_AGENT_DIAGNOSTIC" in source
+    assert "HERMES_AGENT_PYTEST_WORKERS" in source
```

`pytest.importorskip("requests")` covers offline CI; `HERMES_META_TESTS_OFFLINE=1` is the explicit override; local-wrapper assertions need no network.

## Unified diff #3 — firmware-archive-dir registry validator

Target: `G:/Github/h3d-gui-wiring-codex/03_implementation/src/hermes3d/db/load_modules.py`. Adds fail-closed validator that refuses to load if any `firmware_*` row lacks `firmware_archive_dir`. Hooked before `load_modules()` write loop.

```diff
--- a/03_implementation/src/hermes3d/db/load_modules.py
+++ b/03_implementation/src/hermes3d/db/load_modules.py
@@ -50,6 +50,12 @@ SECTION_TARGET_DIRS = {
 MANIFEST_ID_ALIASES = {
     "strec3d": "strecs3d",
 }
+# Firmware safety: every firmware row must declare firmware_archive_dir
+# (rollback target for vendor-signed previous .bin/.hex). Audit §3.4-3.5 + §5.7:
+# all 6 firmware rows carry safety: no_flash_without_explicit_approval; absence
+# of archive dir means rollback is unsafe -> refuse to load.
+FIRMWARE_SECTIONS = {"firmware"}
+FIRMWARE_LAUNCH_KINDS = {"firmware_source"}
 SOURCE_OVERRIDES = {
@@ -325,6 +331,32 @@ def inspect_source_path(local_path: str | None, repo_url: str | None) -> dict[st
     }
 
 
+def _validate_firmware_archive_dirs(registry: dict[str, dict[str, dict[str, Any]]]) -> None:
+    """Fail-closed: refuse to load if any firmware_* row lacks firmware_archive_dir.
+
+    Cross-checks firmware section AND any module whose launch_kind override pins
+    it to firmware_source (e.g. firmware_klipper lives under print_farm per the
+    Klipper double-registration in audit §5.8).
+    """
+    missing: list[str] = []
+    for section_key, entries in registry.items():
+        for module_id, entry in entries.items():
+            launch_kind = (
+                LAUNCH_KIND_OVERRIDES.get(module_id)
+                or entry.get("launch_kind")
+                or "unknown"
+            )
+            is_firmware = (
+                section_key in FIRMWARE_SECTIONS
+                or launch_kind in FIRMWARE_LAUNCH_KINDS
+                or module_id.startswith("firmware_")
+            )
+            if not is_firmware:
+                continue
+            archive_dir = entry.get("firmware_archive_dir")
+            if not archive_dir or not str(archive_dir).strip():
+                missing.append(f"{section_key}::{module_id}")
+    if missing:
+        raise ValueError(
+            "Refusing to load registry: firmware rows missing firmware_archive_dir: "
+            + ", ".join(sorted(missing))
+        )
+
+
 def load_modules() -> int:
     if not DB_PATH.exists():
         init_db()
@@ -332,6 +364,7 @@ def load_modules() -> int:
         registry = _parse_registry(_registry_path())
     except FileNotFoundError:
         registry = _registry_from_committed_proof()
+    _validate_firmware_archive_dirs(registry)
     manifest = _manifest_index()
     conn = connect()
     count = 0
```

Validator runs BEFORE any DB write. `firmware_klipper` (renamed via `LAUNCH_KIND_OVERRIDES`) caught by both prefix and launch-kind. Batch 3: confirm YAML has `firmware_archive_dir` populated for all 6 firmware rows OR add them in same PR.

## Receipt #1 — pytest official `--ignore` semantics

- **URL**: `https://docs.pytest.org/en/stable/example/pythoncollection.html#ignore-paths-during-test-collection`
- **Quote**: "The `--ignore=path` command-line option can be used to ignore individual file paths or whole directories from the test collection. Multiple `--ignore` options are allowed."
- **Cross-ref**: `https://docs.pytest.org/en/stable/reference/customize.html` — collectors run before any conftest body imports.
- **Claim**: `--ignore` operates at collection time BEFORE conftest is imported; `-m` operates at selection time AFTER. For `tests/e2e/conftest.py` `sys.modules` contamination, only `--ignore` defends.
- **Impact**: justifies adding `--ignore=tests/integration --ignore=tests/e2e`; keeping `-m "not integration"` as defense-in-depth.
- **Risk if unaddressed**: every staged update with `HERMES_AGENT_RUN_PYTEST=1` re-imports `tests/e2e/conftest.py`, mutating `sys.modules` for `pwd`/`grp`/`spwd` — original v0.13.0 lane A failure mode.

## Receipt #2 — cross-project compatibility-patch reference

- **URL**: `https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/.github/workflows/unit_tests.yml`
- **Claim**: lm-evaluation-harness uses `pytest --ignore=tests/models -n auto` as a path-based ignore for slow integration paths while running fast unit tests under xdist. Production-grade open-source project that adopted this exact pattern (path-ignore + xdist auto), validating our migration from marker-only to path-based for collection-time isolation.
- **Impact**: confirms pattern is industry-standard for fast/slow split AND collection-time isolation; supports `-n auto` default.
- **Risk if unaddressed**: without external precedent, patch could be challenged as ad-hoc; with this receipt + upstream Hermes Agent receipt (audit §6.1), Batch 3 has two precedents.

## Adversarial self-review

1. **`HERMES_AGENT_DIAGNOSTIC=1` becomes a permanent escape hatch.** If set in long-lived shell or `.env`, every staged update silently runs `--maxfail=5` and accepts `-n 0/1`. Mitigation (Batch 4): record `diagnostic_mode: true` in proof event and surface a `WARNING:` line in output head.
2. **Fail-closed skip path triggers auto-repair, which also fails the same gate.** `_auto_repair_to_backup` re-runs `_run_update_checks(repo)` against backup target; if `HERMES_AGENT_RUN_PYTEST` unset, rollback also returns `fail+REQUIRES_CONFIRMATION` => operator sees `rollback_failed_checks`. Technically correct but UX-confusing; Batch 3 may add special-case handling OR document runbook step "always set `HERMES_AGENT_RUN_PYTEST=1` before staged update."
3. **Meta-test #1 false-fails on transient upstream 404 / rate limit.** `pytest.importorskip` + `HERMES_META_TESTS_OFFLINE=1` cover offline; transient 5xx is skipped. But 200 with stale CDN content during brief upstream regression could yield false-fail and block PR merges. Mitigation (Batch 4): cache upstream `tests.yml` at PR-creation time into frozen artifact under `04_testing/fixtures/upstream_tests_yml.snapshot`; refresh weekly cron.

## Confirmation

**No source was modified by Agent 10.** Only this single sub-file (`agent10-compat-patch.md`) was written. Live `agent_updates.py`, `load_modules.py`, audit doc — all unchanged.
