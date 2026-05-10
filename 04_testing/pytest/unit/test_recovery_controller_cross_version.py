"""Wave 4 P3-4 — RC v2 cross-version (v0.12 + v0.13) saga semantics regression.

Mission
-------
Confirm Recovery Controller v2 (RC v2) freeze/thaw/saga-compensation semantics
behave **identically** against the v0.12 fallback checkout
(``G:/Github/hermes-agent-fresh``) and the v0.13 production default
(``G:/Github/hermes-agent-v013-canary``). Per the action plan §P3-4, the user
requirement is::

    "freeze/snapshot/MCP-lock semantics unchanged"

This is a **regression-style** test, NOT a freeze redesign. RC v2 source
(``recovery_controller.py``) MUST NOT be modified. The new tests stub all v1
collaborators (``code_history.lock_mcp_files`` / ``release_mcp_files`` /
``snapshot_file`` / ``record_step_failure`` / ``mark_recovery_outcome``) so
the run is deterministic and does not require either the v0.12 or v0.13
checkout directory to physically exist on disk.

Sources cited (2-source minimum from brief)
-------------------------------------------
1. **Saga pattern (Garcia-Molina + Salem 1987) -- Temporal docs**
   https://temporal.io/blog/saga-pattern-made-easy

   The saga pattern decomposes a long-running transaction into a series of
   compensable local transactions. Each step's compensation is "the inverse
   of the local transaction" -- e.g., for ``lock_mcp_files`` the inverse is
   ``release_mcp_files``. RC v2 ``freeze_run`` is exactly this: step 1 lock
   files, step 2 snapshot files, with the snapshot-failure compensator
   releasing the locks and writing a v1 retry_failed outcome row. The
   cross-version test verifies that the compensation invariants hold
   regardless of which Hermes Agent checkout is active, because the saga
   steps are version-agnostic by design.

2. **PostgreSQL transaction-rollback semantics**
   https://www.postgresql.org/docs/current/tutorial-transactions.html

   PostgreSQL's BEGIN..ROLLBACK guarantees that a partial commit is never
   observed: either all statements in the transaction land or none do.
   RC v2 ``freeze_run`` mirrors this on top of two non-atomic external
   resources (MCP locks + filesystem snapshots). When step 2 (snapshot)
   fails after step 1 (lock) has succeeded, the controller must release
   the partial locks AND write a retry_failed v1 outcome AND transition
   the run to RETRY_FAILED. This is the SQL-style "rollback" behavior.
   The cross-version test pins this behavior on both v0.12 and v0.13.

Tests in this file
------------------
1. ``test_freeze_run_creates_record_under_v013_default`` -- env unset; freeze
   produces a RecoveryRun with the saga step 2 fields populated.
2. ``test_freeze_run_creates_record_under_v012_fallback`` -- env set to v0.12;
   identical record shape.
3. ``test_thaw_run_releases_locks_v013`` -- thaw releases all freeze locks.
4. ``test_thaw_run_releases_locks_v012`` -- parity under v0.12.
5. ``test_compensate_freeze_failure_under_both_versions`` -- snapshot failure
   on the 3rd file: 2 acquired locks released, partial snapshot path
   compensated, v1 outcome row written, RETRY_FAILED transitioned. Same on
   both versions.
6. ``test_freeze_run_proof_event_records_active_version`` -- conditionally
   skipped: depends on P2-6 (proof event version tagging) landing. Detected
   via inspecting the ``RecoveryRun`` dataclass for a version field.
7. ``test_recovery_run_dataclass_field_set_unchanged`` -- pin the RecoveryRun
   field set across versions; no version-specific drift permitted.
8. ``test_freeze_thaw_round_trip_identical_across_versions`` -- run the full
   freeze->thaw round-trip on both versions; capture the v1-collaborator
   call sequence; assert identical TYPES and ORDER.

Constraints honored
-------------------
* RC v2 source NOT modified.
* No filesystem requirement on the actual v0.12 / v0.13 directories.
* Only the resolver env (``HERMES_AGENT_CHECKOUT``) is monkeypatched.
* All v1 collaborators stubbed so no real MCP locks / snapshots are taken.
* RC v2 commits 3-5 (autonomous mode, propose/review/apply, UI panel) are
  out of scope -- these tests live entirely in commit 1+2 surface.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest

from hermes3d.services import code_history, recovery_controller


# ---------------------------------------------------------------------------
# Cross-version path constants (mirrors the v0.12 + v0.13 regression pins)
# ---------------------------------------------------------------------------

V012_FALLBACK = "G:/Github/hermes-agent-fresh"
V013_DEFAULT = "G:/Github/hermes-agent-v013-canary"


# ---------------------------------------------------------------------------
# Cross-version fixture: stub all v1 collaborators + reset registry.
# Mirrors the ``freeze_setup`` fixture in test_recovery_controller_freeze.py
# but parameterizes over the active checkout.
# ---------------------------------------------------------------------------


def _build_freeze_stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """Return a captured-call dict and stub all v1 collaborators.

    Identical surface to the existing ``freeze_setup`` fixture so the
    cross-version tests reuse the same audited stub shape.
    """
    captured: dict[str, list[Any]] = {
        "lock_calls": [],
        "snapshot_calls": [],
        "release_calls": [],
        "mark_outcome_calls": [],
        "step_failure_calls": [],
        "evidence_calls": [],
    }
    recovery_controller._reset_registry_for_tests()

    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_lock(**kwargs: Any) -> dict[str, Any]:
        captured["lock_calls"].append(kwargs)
        return {
            "status": "locked",
            "files": kwargs.get("files", []),
            "owner": kwargs.get("owner"),
        }

    def stub_release(**kwargs: Any) -> dict[str, Any]:
        captured["release_calls"].append(kwargs)
        return {"status": "released", "files": kwargs.get("files", [])}

    def stub_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        captured["snapshot_calls"].append({"rel": rel, **kwargs})
        return {
            "id": f"snap-{rel}-{len(captured['snapshot_calls'])}",
            "ts_utc": "2026-05-09T00:00:00Z",
        }

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        captured["step_failure_calls"].append(kwargs)
        attempt_id = f"{len(captured['step_failure_calls']):032x}"
        return {
            "status": "recorded",
            "attempt_id": attempt_id,
            "record": {
                "kind": "failure",
                "attempt_id": attempt_id,
                "task_id": kwargs.get("task_id"),
                "failure_class": kwargs.get("failure_class"),
                "failed_step": kwargs.get("failed_step"),
                "failed_step_type": kwargs.get("failed_step_type", "unknown"),
                "failure_summary": kwargs.get("failure_summary"),
                "failure_fingerprint": "f" * 16,
                "retry_budget": {
                    "attempt_n": 1,
                    "max_attempts": 3,
                    "exhausted": False,
                },
                "ts_utc": "2026-05-09T00:00:00Z",
            },
            "mcp_evidence": {"evidence_id": "ev-stub"},
        }

    def stub_mark_outcome(**kwargs: Any) -> dict[str, Any]:
        captured["mark_outcome_calls"].append(kwargs)
        return {
            "status": "recorded",
            "outcome": {"attempt_id": kwargs.get("attempt_id")},
            "mcp_evidence": {},
        }

    def stub_evidence(**kwargs: Any) -> dict[str, Any]:
        captured["evidence_calls"].append(kwargs)
        return {
            "status": "recorded",
            "evidence_id": "ev-stub",
            "result": {"ok": True},
        }

    monkeypatch.setattr(code_history, "lock_mcp_files", stub_lock)
    monkeypatch.setattr(code_history, "release_mcp_files", stub_release)
    monkeypatch.setattr(code_history, "snapshot_file", stub_snapshot)
    monkeypatch.setattr(
        code_history, "record_step_failure", stub_record_step_failure
    )
    monkeypatch.setattr(code_history, "mark_recovery_outcome", stub_mark_outcome)
    monkeypatch.setattr(code_history, "append_mcp_evidence", stub_evidence)
    return captured


def _start_run(failure_class: str = "patch_rejected") -> str:
    """Helper: start a recovery run and return its attempt_id.

    Identical to the helper in ``test_recovery_controller_freeze.py`` --
    the cross-version test re-uses the same minimum-viable spec so any
    behavior delta surfaces from the resolver, not the spec.
    """
    spec = recovery_controller.RecoveryRunSpec(
        task_id="task-cv-001",
        failed_step="apply_patch",
        failure_class=failure_class,
        failure_summary="patch did not apply cleanly",
        failed_step_type="patch_apply",
        actor="user",
    )
    out = recovery_controller.start_recovery(spec=spec, owner="claude-cv-test")
    return out["run"]["attempt_id"]


def _set_v013_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mirror v0.13 production default by removing the env override."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)


def _set_v012_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mirror v0.12 rollback by setting the operator-flip env."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)


def _has_version_field_on_run() -> bool:
    """Detect whether P2-6 (proof event version tagging) has landed.

    P2-6 will add either a version field to the RecoveryRun dataclass OR
    extend the freeze-event payload. Either way, ``inspect``-ing the
    dataclass fields tells us whether the test should skip or run. This
    avoids hard-coding a date and lets the conditional flip automatically
    once P2-6 lands.
    """
    fields = recovery_controller.RecoveryRun.__dataclass_fields__
    candidates = {
        "version_label",
        "version_tag",
        "active_checkout",
        "hermes_agent_version",
    }
    return bool(candidates & set(fields))


# Capture the canonical RecoveryRun field set ONCE at module import for the
# cross-version stability pin (test 7). If a future commit accidentally adds
# a version-specific field while the env is set one way, the captured set
# will diverge from the live set when the env flips.
_RECOVERY_RUN_FIELDS_AT_IMPORT: frozenset[str] = frozenset(
    recovery_controller.RecoveryRun.__dataclass_fields__.keys()
)


# ---------------------------------------------------------------------------
# Test 1: freeze_run under v0.13 default produces saga step 2 record.
# ---------------------------------------------------------------------------


def test_freeze_run_creates_record_under_v013_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saga step 2 records the freeze artifacts under v0.13 production default.

    Pins:
    * RecoveryRun.locked_files matches the input file tuple.
    * RecoveryRun.pre_snapshot_ids is populated (one per file).
    * RecoveryRun.freeze_event_utc is non-empty.
    * Resolver returns v0.13 path during the run (sanity: env hygiene).
    """
    _set_v013_default(monkeypatch)
    captured = _build_freeze_stubs(monkeypatch)

    # Sanity: resolver under env-unset returns v0.13 default.
    from hermes3d.services import agent_checkout as ac

    assert ac.hermes_agent_checkout() == Path(V013_DEFAULT)

    attempt_id = _start_run()
    files = ("src/v013/a.py", "src/v013/b.py")
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )

    assert result["status"] == "frozen"
    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    assert run["locked_files"] == list(files)
    assert len(run["pre_snapshot_ids"]) == len(files)
    assert run["freeze_event_utc"], (
        "freeze_event_utc must be populated by saga step 2 under v0.13 default"
    )
    # The state must transition past CREATED into PROPOSING per saga step 6.
    assert run["state"] == "proposing"
    # Lock-call captured shape -- v1 stub got the RC v2 freeze-reason prefix.
    assert len(captured["lock_calls"]) == 1
    assert captured["lock_calls"][0]["files"] == list(files)
    assert captured["lock_calls"][0]["reason"].startswith("recovery-freeze:")


# ---------------------------------------------------------------------------
# Test 2: freeze_run under v0.12 fallback produces identically-shaped record.
# ---------------------------------------------------------------------------


def test_freeze_run_creates_record_under_v012_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operator-flipped v0.12 rollback path: saga step 2 record shape MUST match v0.13.

    Same dataclass fields, same types, same call sequence. This is the core
    P3-4 invariant: ``freeze/snapshot/MCP-lock semantics unchanged``.
    """
    _set_v012_fallback(monkeypatch)
    captured = _build_freeze_stubs(monkeypatch)

    # Sanity: resolver under explicit env returns v0.12 fallback.
    from hermes3d.services import agent_checkout as ac

    assert ac.hermes_agent_checkout() == Path(V012_FALLBACK)

    attempt_id = _start_run()
    files = ("src/v012/a.py", "src/v012/b.py")
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )

    assert result["status"] == "frozen"
    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    assert run["locked_files"] == list(files)
    assert len(run["pre_snapshot_ids"]) == len(files)
    assert run["freeze_event_utc"]
    assert run["state"] == "proposing"
    assert len(captured["lock_calls"]) == 1
    assert captured["lock_calls"][0]["files"] == list(files)
    assert captured["lock_calls"][0]["reason"].startswith("recovery-freeze:")
    # Payload-shape identity pin: every key that v0.13 produces must exist
    # under v0.12 too. This is the cross-version dataclass-shape contract.
    expected_keys = {
        "attempt_id", "task_id", "state", "branch", "failure_class",
        "failed_step_type", "failure_fingerprint", "retry_count",
        "retry_budget_max", "actor", "confirm", "started_utc",
        "last_event_utc", "last_event_summary", "proposal_id",
        "review_evidence_id", "apply_evidence_id", "retry_gate_id",
        "terminal_status", "cancelled_reason", "is_terminal",
        "is_cancellable", "locked_files", "pre_snapshot_ids",
        "freeze_event_utc", "next_action",
    }
    assert expected_keys <= set(run.keys()), (
        f"v0.12 fallback regression: state payload missing keys "
        f"{expected_keys - set(run.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 3: thaw_run under v0.13 releases all locks acquired by freeze_run.
# ---------------------------------------------------------------------------


def test_thaw_run_releases_locks_v013(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thaw under v0.13 default: every freeze-acquired lock is released.

    No leak invariant: ``release_mcp_files`` is called exactly once with
    the full freeze file list.
    """
    _set_v013_default(monkeypatch)
    captured = _build_freeze_stubs(monkeypatch)

    attempt_id = _start_run()
    files = ("src/v013/x.py", "src/v013/y.py", "src/v013/z.py")
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )

    out = recovery_controller.thaw_run(
        attempt_id=attempt_id, owner="claude-cv-test"
    )
    assert out["status"] == "thawed"
    assert len(captured["release_calls"]) == 1, (
        "v0.13 thaw regression: release_mcp_files must be called exactly once"
    )
    assert captured["release_calls"][0]["files"] == list(files)
    # Run state: locked_files cleared after thaw (saga compensation rule).
    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    assert run["locked_files"] == [], "Thaw must clear locked_files on the run"


# ---------------------------------------------------------------------------
# Test 4: thaw_run under v0.12 -- parity with v0.13.
# ---------------------------------------------------------------------------


def test_thaw_run_releases_locks_v012(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thaw under v0.12 fallback: identical behavior to v0.13.

    Same release count, same files released, same locked_files clear.
    """
    _set_v012_fallback(monkeypatch)
    captured = _build_freeze_stubs(monkeypatch)

    attempt_id = _start_run()
    files = ("src/v012/x.py", "src/v012/y.py", "src/v012/z.py")
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )

    out = recovery_controller.thaw_run(
        attempt_id=attempt_id, owner="claude-cv-test"
    )
    assert out["status"] == "thawed"
    assert len(captured["release_calls"]) == 1
    assert captured["release_calls"][0]["files"] == list(files)
    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    assert run["locked_files"] == []


# ---------------------------------------------------------------------------
# Test 5: saga compensation -- partial freeze failure on file 3 (Postgres-style
# rollback). Identical compensation under v0.12 and v0.13.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "checkout_label,setter",
    [
        ("v013_default", _set_v013_default),
        ("v012_fallback", _set_v012_fallback),
    ],
)
def test_compensate_freeze_failure_under_both_versions(
    checkout_label: str,
    setter: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Saga step 2 compensator: snapshot fails on the 3rd of 3 files.

    Postgres-style invariants (https://www.postgresql.org/docs/current/tutorial-transactions.html):
    * The transaction (freeze) is fully rolled back.
    * The 2 already-acquired locks are released (no leak).
    * The partial-snapshot work is not "applied" -- pre_snapshot_ids stays empty.
    * A v1 outcome row is written with status=retry_failed.
    * The run transitions to RETRY_FAILED (terminal).

    Saga reference: https://temporal.io/blog/saga-pattern-made-easy
    -- "if any step fails, all previously completed steps must be undone".
    """
    setter(monkeypatch)
    captured = _build_freeze_stubs(monkeypatch)
    attempt_id = _start_run()

    call_count = {"n": 0}

    def failing_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        call_count["n"] += 1
        # Files 1 and 2 succeed; file 3 raises.
        if call_count["n"] == 3:
            raise OSError(28, f"Disk full (synthetic, {checkout_label})")
        return {"id": f"snap-{rel}-ok", "ts_utc": "2026-05-09T00:00:00Z"}

    monkeypatch.setattr(code_history, "snapshot_file", failing_snapshot)

    files = ("src/cv/a.py", "src/cv/b.py", "src/cv/c.py")
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )
    assert result["status"] == "snapshot_failed", (
        f"{checkout_label}: snapshot failure on file 3 must surface as "
        f"snapshot_failed; got {result['status']!r}"
    )

    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    # Postgres rollback invariant: terminal RETRY_FAILED state.
    assert run["state"] == "retry_failed", (
        f"{checkout_label}: saga compensation must end in retry_failed; "
        f"got {run['state']!r}"
    )
    assert run["terminal_status"] == "retry_failed"
    assert run["is_terminal"] is True
    # Locks released exactly once over the same file set.
    assert len(captured["release_calls"]) == 1, (
        f"{checkout_label}: exactly one release_mcp_files compensation call expected"
    )
    assert captured["release_calls"][0]["files"] == list(files)
    # v1 outcome row written exactly once with retry_failed status.
    assert len(captured["mark_outcome_calls"]) == 1
    assert captured["mark_outcome_calls"][0]["status"] == "retry_failed"
    assert captured["mark_outcome_calls"][0]["attempt_id"] == attempt_id
    # Saga partial-snapshot is NOT applied to the run.
    assert run["pre_snapshot_ids"] == [], (
        f"{checkout_label}: partial snapshot IDs must NOT be persisted "
        f"after compensation"
    )


# ---------------------------------------------------------------------------
# Test 6: P2-6 conditional -- proof event records active version label.
# Skips automatically until P2-6 (proof event version tagging) lands.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _has_version_field_on_run(),
    reason="P2-6 (proof event version tagging) has not landed yet; "
    "RecoveryRun has no version field. Re-run after P2-6 merges.",
)
def test_freeze_run_proof_event_records_active_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When P2-6 lands, freeze events MUST record the active checkout version.

    Detection: scans ``RecoveryRun.__dataclass_fields__`` for any of
    ``version_label`` / ``version_tag`` / ``active_checkout`` /
    ``hermes_agent_version``. If none are present, P2-6 has not landed and
    pytest skips this test. The skip will flip to a real assertion once the
    version field is added by the P2-6 PR.
    """
    _set_v013_default(monkeypatch)
    _build_freeze_stubs(monkeypatch)

    attempt_id = _start_run()
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=("src/v013/p26.py",)
    )

    run = recovery_controller.get_run_state(attempt_id)
    assert run is not None
    # When the version field exists, the v0.13 run must record the v0.13
    # path or label. Cover the common candidate names so this test stays
    # green regardless of which spelling P2-6 chooses.
    found_value = None
    for key in ("version_label", "version_tag", "active_checkout",
                "hermes_agent_version"):
        if key in run:
            found_value = str(run[key])
            break
    assert found_value, "P2-6 fence: a version field exists on the dataclass " \
        "but no version-named key surfaced in to_state_payload"
    # The recorded value should reference v0.13 (default path or canary
    # label), never the v0.12 path while env is unset.
    assert (
        "v013" in found_value or "Tenacity" in found_value
        or "v2026.5" in found_value or V013_DEFAULT in found_value
    ), (
        f"P2-6 regression: v0.13-default freeze recorded version "
        f"{found_value!r}; expected a v0.13-style label"
    )
    assert "fresh" not in found_value and V012_FALLBACK not in found_value, (
        f"P2-6 cross-contamination: v0.13-default freeze leaked v0.12 "
        f"path into version field: {found_value!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: dataclass field-set stability -- pin RecoveryRun fields are
# version-agnostic. No field added/removed when the resolver flips.
# ---------------------------------------------------------------------------


def test_recovery_run_dataclass_field_set_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin: RecoveryRun.__dataclass_fields__ is identical across versions.

    A future commit could accidentally add a v0.13-only or v0.12-only field
    behind a feature flag that reads HERMES_AGENT_CHECKOUT at import time.
    This test catches that drift by:
    1. Capturing the field set at module import (above, _RECOVERY_RUN_FIELDS_AT_IMPORT).
    2. Reloading recovery_controller with env=v0.12 and re-capturing fields.
    3. Reloading recovery_controller with env unset (v0.13 default) and re-capturing.
    4. Asserting all three sets are equal.
    """
    baseline = _RECOVERY_RUN_FIELDS_AT_IMPORT

    _set_v012_fallback(monkeypatch)
    importlib.reload(recovery_controller)
    v012_fields = frozenset(recovery_controller.RecoveryRun.__dataclass_fields__.keys())

    _set_v013_default(monkeypatch)
    importlib.reload(recovery_controller)
    v013_fields = frozenset(recovery_controller.RecoveryRun.__dataclass_fields__.keys())

    assert v012_fields == v013_fields, (
        f"P3-4 regression: RecoveryRun fields differ across versions. "
        f"v0.12-only={v012_fields - v013_fields}, "
        f"v0.13-only={v013_fields - v012_fields}"
    )
    assert v012_fields == baseline, (
        f"P3-4 regression: env-driven reload changed RecoveryRun fields. "
        f"baseline={baseline}, after-reload={v012_fields}"
    )


# ---------------------------------------------------------------------------
# Test 8: end-to-end round-trip -- freeze then thaw, capture event ORDER
# and TYPES, assert identical across versions.
# ---------------------------------------------------------------------------


def _round_trip_call_sequence(
    monkeypatch: pytest.MonkeyPatch,
    setter: Any,
) -> tuple[list[str], list[str]]:
    """Run freeze->thaw under the given checkout setter, return:

    * call_sequence: list of v1-collaborator names in invocation order
      (e.g. ['record_step_failure', 'lock_mcp_files', 'snapshot_file',
      'snapshot_file', 'release_mcp_files']).
    * file_args: list of file lists by call (only for lock/release steps).

    Used by test 8 to compare across v0.12 and v0.13 — saga step ordering
    must not differ.
    """
    setter(monkeypatch)
    sequence: list[str] = []
    file_args: list[str] = []
    recovery_controller._reset_registry_for_tests()
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_lock(**kwargs: Any) -> dict[str, Any]:
        sequence.append("lock_mcp_files")
        file_args.append(",".join(kwargs.get("files", [])))
        return {"status": "locked", "files": kwargs.get("files", [])}

    def stub_release(**kwargs: Any) -> dict[str, Any]:
        sequence.append("release_mcp_files")
        file_args.append(",".join(kwargs.get("files", [])))
        return {"status": "released"}

    def stub_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        sequence.append("snapshot_file")
        return {"id": f"snap-{rel}", "ts_utc": "2026-05-09T00:00:00Z"}

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        sequence.append("record_step_failure")
        attempt_id = "a" * 32
        return {
            "status": "recorded",
            "attempt_id": attempt_id,
            "record": {
                "kind": "failure",
                "attempt_id": attempt_id,
                "task_id": kwargs.get("task_id"),
                "failure_class": kwargs.get("failure_class"),
                "failed_step": kwargs.get("failed_step"),
                "failed_step_type": kwargs.get("failed_step_type", "unknown"),
                "failure_summary": kwargs.get("failure_summary"),
                "failure_fingerprint": "f" * 16,
                "retry_budget": {
                    "attempt_n": 1,
                    "max_attempts": 3,
                    "exhausted": False,
                },
                "ts_utc": "2026-05-09T00:00:00Z",
            },
            "mcp_evidence": {"evidence_id": "ev-stub"},
        }

    def stub_mark_outcome(**kwargs: Any) -> dict[str, Any]:
        sequence.append("mark_recovery_outcome")
        return {"status": "recorded", "outcome": {}, "mcp_evidence": {}}

    def stub_evidence(**kwargs: Any) -> dict[str, Any]:
        return {"status": "recorded", "evidence_id": "ev-stub"}

    monkeypatch.setattr(code_history, "lock_mcp_files", stub_lock)
    monkeypatch.setattr(code_history, "release_mcp_files", stub_release)
    monkeypatch.setattr(code_history, "snapshot_file", stub_snapshot)
    monkeypatch.setattr(
        code_history, "record_step_failure", stub_record_step_failure
    )
    monkeypatch.setattr(code_history, "mark_recovery_outcome", stub_mark_outcome)
    monkeypatch.setattr(code_history, "append_mcp_evidence", stub_evidence)

    spec = recovery_controller.RecoveryRunSpec(
        task_id="task-rt-001",
        failed_step="apply_patch",
        failure_class="patch_rejected",
        failure_summary="round-trip probe",
        failed_step_type="patch_apply",
        actor="user",
    )
    out = recovery_controller.start_recovery(spec=spec, owner="claude-cv-test")
    attempt_id = out["run"]["attempt_id"]
    files = ("src/rt/a.py", "src/rt/b.py")
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-cv-test", files=files
    )
    recovery_controller.thaw_run(
        attempt_id=attempt_id, owner="claude-cv-test"
    )
    return sequence, file_args


def test_freeze_thaw_round_trip_identical_across_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end pin: freeze->thaw call ORDER + TYPES are version-agnostic.

    Saga reference (https://temporal.io/blog/saga-pattern-made-easy):
    > "Each step in a saga is a local transaction; their order is fixed;
    >  compensation runs in reverse."

    Postgres reference (https://www.postgresql.org/docs/current/tutorial-transactions.html):
    > Transactions guarantee ordering: BEGIN, work, COMMIT (or ROLLBACK
    > with compensation in reverse). Same applies here.

    The version metadata in the events MAY differ once P2-6 lands (test 6
    covers that), but the saga step types and order MUST NOT differ.
    """
    seq_v013, files_v013 = _round_trip_call_sequence(monkeypatch, _set_v013_default)
    seq_v012, files_v012 = _round_trip_call_sequence(monkeypatch, _set_v012_fallback)

    expected_sequence = [
        "record_step_failure",  # start_recovery -> v1 ledger row
        "lock_mcp_files",       # saga step 1
        "snapshot_file",        # saga step 2 (file 1)
        "snapshot_file",        # saga step 2 (file 2)
        "release_mcp_files",    # thaw -> compensation/cleanup
    ]
    assert seq_v013 == expected_sequence, (
        f"v0.13 saga ordering regression: got {seq_v013}"
    )
    assert seq_v012 == expected_sequence, (
        f"v0.12 saga ordering regression: got {seq_v012}"
    )
    assert seq_v013 == seq_v012, (
        f"P3-4 cross-version regression: saga step ORDER differs.\n"
        f"v0.13={seq_v013}\n"
        f"v0.12={seq_v012}"
    )
    # File argument identity: lock + release must agree on the same files
    # under both versions (file 0 = lock arg, file 1 = release arg).
    assert files_v013 == files_v012, (
        f"P3-4 cross-version regression: lock/release file lists differ.\n"
        f"v0.13={files_v013}\n"
        f"v0.12={files_v012}"
    )
