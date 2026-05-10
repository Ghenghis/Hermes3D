"""Recovery ledger locking + idempotent outcome tests (Audit PR #135 Bonus 12).

Covers two bug fixes in ``hermes3d.services.code_history``:

1. **File-lock gap on the recovery ledger** (Bonus 12 finding #1, blocker).
   ``record_step_failure`` and ``mark_recovery_outcome`` previously used a
   bare ``open("a")`` with no OS-level lock; concurrent writers on Windows
   could interleave partial JSONL lines that ``mark_recovery_outcome`` would
   then ``json.JSONDecodeError``-skip and report "attempt_id not found".
   The patch wraps writes in ``_recovery_ledger_lock()`` (cross-platform
   ``fcntl`` / ``msvcrt``) plus ``flush()`` + ``os.fsync()``.

2. **Non-idempotent outcome recording** (Bonus 12 finding #2, major).
   ``mark_recovery_outcome`` previously had no check that an outcome row
   for ``attempt_id`` already existed. A retry could silently append a
   duplicate outcome row; ``list_recovery_attempts`` then returned both
   and consumers saw ambiguous state. The patch raises ``ValueError`` on
   the second call (atomic with the read scan inside the lock).

References:
- https://docs.python.org/3/library/fcntl.html#fcntl.flock
- https://docs.python.org/3/library/msvcrt.html#msvcrt.locking
- https://about.codecov.io/apr-2021-post-mortem/ (silent-corruption family)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from hermes3d.services import code_history

# ---------------------------------------------------------------------------
# Test fixtures: redirect ledger to tmp_path; stub MCP I/O so no network.
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect _RECOVERY_LEDGER_PATH + lock path to tmp_path; stub MCP."""
    ledger = tmp_path / "recovery-ledger.jsonl"
    lockfile = tmp_path / "recovery-ledger.lock"
    monkeypatch.setattr(code_history, "_RECOVERY_LEDGER_PATH", ledger)
    monkeypatch.setattr(code_history, "_RECOVERY_LEDGER_LOCK_PATH", lockfile)
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **kwargs: {"status": "recorded", "evidence_id": "stub", "result": {"ok": True}},
    )
    return ledger


def _record_one_failure(task_suffix: str = "demo") -> dict[str, Any]:
    return code_history.record_step_failure(
        owner="claude-test",
        task_id=f"a2a_test_{task_suffix}",
        failed_step="provider_smoke.minimax",
        failure_class="provider_auth",
        failure_summary="MiniMax token rejected",
        failed_step_type="provider_smoke",
        attempt_n=1,
        max_attempts=3,
    )


# ---------------------------------------------------------------------------
# Lock-helper structural tests
# ---------------------------------------------------------------------------


def test_recovery_ledger_lock_is_cross_platform(isolated_ledger: Path) -> None:
    """The lock helper must select an OS-backed lock or fall back cleanly."""
    with code_history._recovery_ledger_lock() as lock:
        assert lock.backend in {"fcntl", "msvcrt", "thread-only"}
    # Lockfile sidecar is created at the configured lock path.
    assert code_history._RECOVERY_LEDGER_LOCK_PATH.exists()


def test_recovery_ledger_lock_serializes_threads(isolated_ledger: Path) -> None:
    """Threading.Lock layer must serialize same-process writers.

    Without serialization, JSONL lines written from many threads would
    interleave bytes; we instead require that every recorded line round-trips
    through ``json.loads`` cleanly.
    """
    n_threads = 12
    n_per_thread = 25
    barrier = threading.Barrier(n_threads)
    errors: list[BaseException] = []

    def writer(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            for j in range(n_per_thread):
                _record_one_failure(task_suffix=f"t{idx:02d}_{j:03d}")
        except BaseException as exc:  # noqa: BLE001 - propagate to assert
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, f"Concurrent writers raised: {errors!r}"
    text = isolated_ledger.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line]
    assert len(lines) == n_threads * n_per_thread, (
        f"Expected {n_threads * n_per_thread} lines, got {len(lines)}. "
        "Lock did not serialize concurrent appends."
    )
    # Every line must json-parse — no partial / interleaved bytes.
    for line in lines:
        parsed = json.loads(line)  # would raise on corruption
        assert parsed.get("kind") == "failure"


# ---------------------------------------------------------------------------
# record_step_failure: append-with-lock + complete lines
# ---------------------------------------------------------------------------


def test_record_step_failure_writes_complete_jsonl_line(isolated_ledger: Path) -> None:
    """A single failure record must produce one parseable JSONL line."""
    result = _record_one_failure()
    assert result["status"] == "recorded"
    line = isolated_ledger.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert parsed["kind"] == "failure"
    assert parsed["attempt_id"] == result["attempt_id"]
    assert parsed["failure_class"] == "provider_auth"


def test_record_step_failure_creates_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parent dir must be created if missing, including the lockfile sidecar's dir."""
    deep_ledger = tmp_path / "deep" / "nested" / "recovery-ledger.jsonl"
    deep_lockfile = tmp_path / "deep" / "nested" / "recovery-ledger.lock"
    monkeypatch.setattr(code_history, "_RECOVERY_LEDGER_PATH", deep_ledger)
    monkeypatch.setattr(code_history, "_RECOVERY_LEDGER_LOCK_PATH", deep_lockfile)
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **kwargs: {"status": "recorded", "evidence_id": "stub", "result": {"ok": True}},
    )
    _record_one_failure()
    assert deep_ledger.exists()
    assert deep_lockfile.exists()


# ---------------------------------------------------------------------------
# mark_recovery_outcome: idempotency (Bonus 12 finding #2)
# ---------------------------------------------------------------------------


def test_mark_recovery_outcome_first_call_succeeds(isolated_ledger: Path) -> None:
    """First outcome row for an attempt_id is appended cleanly."""
    failure = _record_one_failure()
    result = code_history.mark_recovery_outcome(
        owner="claude-test",
        attempt_id=failure["attempt_id"],
        status="recovered",
        recovery_summary="Rotated token; smoke now passes",
    )
    assert result["status"] == "recorded"
    lines = isolated_ledger.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in lines if line.strip()]
    failures = [e for e in parsed if e["kind"] == "failure"]
    outcomes = [e for e in parsed if e["kind"] == "outcome"]
    assert len(failures) == 1
    assert len(outcomes) == 1
    assert outcomes[0]["attempt_id"] == failure["attempt_id"]
    assert outcomes[0]["status"] == "recovered"


def test_mark_recovery_outcome_second_call_raises_idempotency(
    isolated_ledger: Path,
) -> None:
    """Bonus 12 finding #2: a retry must NOT append a duplicate outcome row.

    Without the idempotency guard ``list_recovery_attempts`` would surface
    both outcomes and consumers could double-act (e.g., re-trigger merge
    after the first outcome already escalated).
    """
    failure = _record_one_failure()
    code_history.mark_recovery_outcome(
        owner="claude-test",
        attempt_id=failure["attempt_id"],
        status="recovered",
        recovery_summary="First finalize",
    )
    with pytest.raises(ValueError) as exc_info:
        code_history.mark_recovery_outcome(
            owner="claude-test",
            attempt_id=failure["attempt_id"],
            status="retry_failed",
            recovery_summary="Second finalize",
        )
    assert "already has a recorded outcome" in str(exc_info.value), (
        f"Idempotency error must explain duplication; got: {exc_info.value!r}"
    )
    # And the ledger must contain exactly ONE outcome row for this attempt.
    lines = isolated_ledger.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in lines if line.strip()]
    outcomes = [
        e for e in parsed if e["kind"] == "outcome" and e["attempt_id"] == failure["attempt_id"]
    ]
    assert len(outcomes) == 1, (
        f"Expected exactly 1 outcome after duplicate-rejected call, got {len(outcomes)}"
    )


def test_mark_recovery_outcome_unknown_attempt_id_raises(
    isolated_ledger: Path,
) -> None:
    """Outcome for an unrecorded attempt_id must raise — not silently skip."""
    _record_one_failure()  # ensure ledger exists
    bogus_id = "0" * 32
    with pytest.raises(ValueError) as exc_info:
        code_history.mark_recovery_outcome(
            owner="claude-test",
            attempt_id=bogus_id,
            status="recovered",
            recovery_summary="No matching attempt",
        )
    assert "not found in recovery ledger" in str(exc_info.value)


def test_mark_recovery_outcome_concurrent_finalize_only_one_wins(
    isolated_ledger: Path,
) -> None:
    """Two threads racing to finalize the same attempt — exactly one succeeds.

    This is the lock + idempotency guarantee combined: the read scan and
    the append are atomic, so the second thread sees the first thread's
    outcome row and raises.
    """
    failure = _record_one_failure()
    barrier = threading.Barrier(2)
    results: dict[str, Any] = {"ok": [], "err": []}

    def finalizer(suffix: str) -> None:
        barrier.wait(timeout=5)
        try:
            res = code_history.mark_recovery_outcome(
                owner="claude-test",
                attempt_id=failure["attempt_id"],
                status="recovered",
                recovery_summary=f"finalize {suffix}",
            )
            results["ok"].append(res)
        except ValueError as exc:
            results["err"].append(str(exc))

    t1 = threading.Thread(target=finalizer, args=("A",))
    t2 = threading.Thread(target=finalizer, args=("B",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert len(results["ok"]) == 1, (
        f"Exactly one finalizer should succeed under race; got {len(results['ok'])}"
    )
    assert len(results["err"]) == 1, (
        f"The other finalizer should raise idempotency error; got {len(results['err'])}"
    )
    assert "already has a recorded outcome" in results["err"][0]
