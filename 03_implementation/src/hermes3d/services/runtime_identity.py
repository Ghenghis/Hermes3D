from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from hermes3d.services.local_state import implementation_path

AGENT_WORKBENCH_REQUIRED_ROUTES = [
    "/api/code-operator/e2e/readiness",
    "/api/code-operator/e2e/jobs",
    "/api/code-operator/providers/smoke",
    "/api/code-operator/patch/apply-reviewed",
    "/api/code-operator/gates/run",
    "/api/code-operator/git/pr",
    "/api/code-operator/cli-runners",
    "/api/code-operator/cli-runners/preflight",
    "/api/code-operator/cli-runners/run",
    "/api/code-operator/sandbox/readiness",
]


def runtime_identity_payload(
    *,
    required_routes: Iterable[str] = (),
    route_paths: Iterable[str] = (),
) -> dict[str, Any]:
    """Return source/commit identity for the running backend process.

    The live desktop backend can be launched from any checkout on the
    machine. Exposing the actual repo root and commit makes stale-process
    drift visible in normal health probes instead of requiring operators to
    infer it from DB paths or behavior.
    """

    repo_root = implementation_path().parent
    full_commit = _git_value(repo_root, ["rev-parse", "HEAD"])
    branch = (
        _git_value(repo_root, ["branch", "--show-current"])
        or os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("GITHUB_REF_NAME")
        or ""
    )
    dirty = bool(_git_value(repo_root, ["status", "--porcelain"]))

    expected_repo_root = _expected_env(
        "HERMES3D_EXPECTED_REPO_ROOT",
        "HERMES3D_EXPECTED_SOURCE_ROOT",
    )
    expected_branch = _expected_env("HERMES3D_EXPECTED_GIT_BRANCH")
    expected_commit = _expected_env(
        "HERMES3D_EXPECTED_GIT_SHA",
        "HERMES3D_EXPECTED_COMMIT",
    )

    mismatches: list[str] = []
    if expected_repo_root and not _same_path(repo_root, Path(expected_repo_root)):
        mismatches.append("repo_root")
    if expected_branch and expected_branch != branch:
        mismatches.append("branch")
    if expected_commit and full_commit and not _commit_matches(full_commit, expected_commit):
        mismatches.append("commit")

    route_set = {str(path) for path in route_paths if path}
    required = [str(path) for path in required_routes]
    missing_routes = [path for path in required if path not in route_set]
    if missing_routes:
        mismatches.append("routes")

    expected_configured = bool(expected_repo_root or expected_branch or expected_commit)
    status = "stale" if mismatches else "fresh"
    if not expected_configured and not required:
        status = "unchecked"

    return {
        "status": status,
        "fresh": status == "fresh",
        "stale": status == "stale",
        "mismatches": mismatches,
        "missing_routes": missing_routes,
        "expected": {
            "configured": expected_configured,
            "repo_root": expected_repo_root,
            "branch": expected_branch,
            "commit": expected_commit,
        },
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "repo_root": str(repo_root),
        "implementation_root": str(implementation_path()),
        "backend_source": str(Path(__file__).resolve()),
        "branch": branch or "unknown",
        "commit": (full_commit[:12] if full_commit else "unknown"),
        "dirty": dirty,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }


def _expected_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def _same_path(actual: Path, expected: Path) -> bool:
    try:
        actual_value = str(actual.resolve())
    except OSError:
        actual_value = str(actual.absolute())
    try:
        expected_value = str(expected.resolve())
    except OSError:
        expected_value = str(expected.absolute())
    return os.path.normcase(actual_value) == os.path.normcase(expected_value)


def _commit_matches(actual: str, expected: str) -> bool:
    actual_norm = actual.strip().lower()
    expected_norm = expected.strip().lower()
    return actual_norm.startswith(expected_norm) or expected_norm.startswith(actual_norm)


def _git_value(cwd: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
