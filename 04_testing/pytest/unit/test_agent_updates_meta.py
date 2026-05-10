"""Meta-test: Hermes Agent pytest gate must mirror upstream tests.yml flags.

If upstream NousResearch/hermes-agent removes ``--ignore=tests/integration`` or
``--ignore=tests/e2e`` from ``.github/workflows/tests.yml``, our wrapper's
path-based ignore is now hiding e2e regressions. Fail loud so we re-evaluate.

Two layers of assertions:

1.  Live upstream check (network) — fetches upstream ``tests.yml`` once and
    asserts both ``--ignore=`` substrings are still present. Skipped offline
    via ``HERMES_META_TESTS_OFFLINE=1`` or when ``requests`` is missing.
2.  Local source check — reads our own ``agent_updates.py`` and confirms the
    compatibility patch is in place. Always runs (no network).

Cross-references (audit PR #135 / commit 5ecd8ff):
- https://docs.pytest.org/en/stable/example/pythoncollection.html#ignore-paths-during-test-collection
- https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml
- https://about.codecov.io/apr-2021-post-mortem/
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

requests = pytest.importorskip("requests")  # offline CI: skipped, never errored.

UPSTREAM_TESTS_YML = (
    "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/.github/workflows/tests.yml"
)
# 04_testing/pytest/unit/<this>.py -> 04_testing/pytest/unit -> 04_testing/pytest -> 04_testing -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_UPDATES_PY = (
    REPO_ROOT / "03_implementation" / "src" / "hermes3d" / "api" / "routes" / "agent_updates.py"
)


def _is_offline() -> bool:
    return os.environ.get("HERMES_META_TESTS_OFFLINE", "").strip() == "1"


@pytest.mark.skipif(
    _is_offline(),
    reason="HERMES_META_TESTS_OFFLINE=1; skipping live upstream meta-test.",
)
def test_upstream_tests_yml_still_uses_path_ignores() -> None:
    """Upstream tests.yml must still contain both --ignore= path filters.

    If upstream removes them later, our wrapper's --ignore= mirrors are now
    silently hiding regressions; this assertion fails loud so we re-evaluate.
    """
    try:
        response = requests.get(UPSTREAM_TESTS_YML, timeout=10)
    except requests.RequestException as exc:
        pytest.skip(f"Network unavailable for upstream meta-test: {exc!r}")
    if response.status_code != 200:
        pytest.skip(f"Upstream returned HTTP {response.status_code}; cannot verify.")
    body = response.text
    assert "--ignore=tests/integration" in body, (
        "Upstream tests.yml no longer contains '--ignore=tests/integration'. "
        "Re-evaluate _run_update_checks before continuing the staged-update lane."
    )
    assert "--ignore=tests/e2e" in body, (
        "Upstream tests.yml no longer contains '--ignore=tests/e2e'. "
        "Re-evaluate _run_update_checks before continuing the staged-update lane."
    )


def test_local_wrapper_mirrors_upstream_ignore_flags() -> None:
    """Our agent_updates.py source must contain both path-ignore strings.

    No network needed — pure source assertion. Catches accidental revert of the
    Audit PR #135 / Step 5A compatibility patch.
    """
    assert AGENT_UPDATES_PY.exists(), f"agent_updates.py not found at {AGENT_UPDATES_PY}"
    source = AGENT_UPDATES_PY.read_text(encoding="utf-8")
    assert '"--ignore=tests/integration"' in source, (
        "Our wrapper no longer carries --ignore=tests/integration. "
        "Step 5A compatibility patch was reverted or refactored unsafely."
    )
    assert '"--ignore=tests/e2e"' in source, (
        "Our wrapper no longer carries --ignore=tests/e2e. "
        "Step 5A compatibility patch was reverted or refactored unsafely."
    )
    assert "REQUIRES_CONFIRMATION:" in source, (
        "Skip path no longer returns REQUIRES_CONFIRMATION. "
        "Possible regression of CICD-SEC-1 fake-pass guard."
    )
    assert "timeout=600" in source, (
        "pytest gate timeout was lowered below 600s. "
        "Larger collected set under upstream-aligned --ignore needs the longer budget."
    )


def test_diagnostic_mode_required_for_lone_worker() -> None:
    """The worker-count guard must be present in source.

    HERMES_AGENT_PYTEST_WORKERS in {"0","1"} must require HERMES_AGENT_DIAGNOSTIC=1.
    Catches accidental removal of the xdist isolation guard.
    """
    source = AGENT_UPDATES_PY.read_text(encoding="utf-8")
    assert "HERMES_AGENT_DIAGNOSTIC" in source
    assert "HERMES_AGENT_PYTEST_WORKERS" in source
    # Production default is 4 (mirrors upstream GHA's 4-vCPU runner).
    assert '"HERMES_AGENT_PYTEST_WORKERS", "4"' in source, (
        "Default HERMES_AGENT_PYTEST_WORKERS is no longer 4. "
        "Step 5A spec requires production default = 4 (mirrors upstream GHA)."
    )
