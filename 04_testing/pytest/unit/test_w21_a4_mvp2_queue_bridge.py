"""W21-A4 MVP-2 — unit tests for ``hermes3d.services.queue_bridge``.

Mission: pin the bridge primitives so the auto-poller and the HTTP route
have a reliable substrate. No real orchestrator state directory is touched
— each test builds its own ``tmp_path/.hermes3d_orchestrator/...`` tree.
"""

from __future__ import annotations

import json
from pathlib import Path

from hermes3d.services import queue_bridge

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_task(
    root: Path,
    state: str,
    task_id: str,
    *,
    target_owner_pattern: str = "factory-operator|oliver-qa-agent",
    priority: int = 100,
    claimed_by: str | None = None,
) -> Path:
    """Create a task file under tmp_path/.hermes3d_orchestrator/tasks/<state>/."""
    state_dir = root / ".hermes3d_orchestrator" / "tasks" / state
    state_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "task_schema_version": 1,
        "task_id": task_id,
        "title": f"test {task_id}",
        "summary": "fake task for unit tests",
        "target_owner_pattern": target_owner_pattern,
        "priority": priority,
        "claimed_by": claimed_by,
        "claimed_utc": None,
        "heartbeat_utc": None,
        "done_utc": None,
        "blocked_reason": None,
    }
    path = state_dir / f"{task_id}.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# match_persona
# ---------------------------------------------------------------------------


def test_match_persona_first_alternative_wins() -> None:
    matched = queue_bridge.match_persona(
        "factory-operator|oliver-qa-agent",
        ["factory-operator", "oliver-qa-agent"],
    )
    # The function iterates the available_personas list (not the pattern),
    # so the first AVAILABLE persona that fits wins.
    assert matched in ("factory-operator", "oliver-qa-agent")


def test_match_persona_returns_none_when_no_match() -> None:
    assert queue_bridge.match_persona("modeling-agent", ["factory-operator"]) is None


def test_match_persona_anchors_full_string() -> None:
    """A persona id that PARTIALLY matches must not be accepted, e.g.
    'factory-operator-foo' must not match the 'factory-operator' pattern."""
    matched = queue_bridge.match_persona("factory-operator", ["factory-operator-foo"])
    assert matched is None


def test_match_persona_handles_empty_pattern() -> None:
    assert queue_bridge.match_persona("", ["factory-operator"]) is None
    assert queue_bridge.match_persona("   ", ["factory-operator"]) is None


def test_match_persona_handles_invalid_regex() -> None:
    """A malformed pattern must not raise — return None."""
    assert queue_bridge.match_persona("(unclosed", ["factory-operator"]) is None


# ---------------------------------------------------------------------------
# list_tasks / status_counts
# ---------------------------------------------------------------------------


def test_list_pending_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    assert queue_bridge.list_tasks(tmp_path, "pending") == []


def test_status_counts_empty(tmp_path: Path) -> None:
    counts = queue_bridge.status_counts(tmp_path)
    assert counts == {"pending": 0, "claimed": 0, "done": 0, "blocked": 0}


def test_list_pending_reads_all_json_files(tmp_path: Path) -> None:
    _write_task(tmp_path, "pending", "T1")
    _write_task(tmp_path, "pending", "T2")
    snaps = queue_bridge.list_tasks(tmp_path, "pending")
    ids = sorted(s.task_id for s in snaps)
    assert ids == ["T1", "T2"]
    assert all(s.state == "pending" for s in snaps)


def test_list_skips_malformed_json(tmp_path: Path) -> None:
    """Corrupt file must be skipped, not crash."""
    _write_task(tmp_path, "pending", "T1")
    bad = tmp_path / ".hermes3d_orchestrator" / "tasks" / "pending" / "T_bad.json"
    bad.write_text("not json at all", encoding="utf-8")
    snaps = queue_bridge.list_tasks(tmp_path, "pending")
    assert [s.task_id for s in snaps] == ["T1"]


# ---------------------------------------------------------------------------
# claim_task
# ---------------------------------------------------------------------------


def test_claim_task_moves_file_and_records_owner(tmp_path: Path) -> None:
    _write_task(tmp_path, "pending", "T1")
    snap = queue_bridge.claim_task(tmp_path, "T1", "factory-operator")
    assert snap is not None
    assert snap.state == "claimed"
    assert snap.claimed_by == "hermes/factory-operator"
    assert snap.claimed_utc is not None
    # Pending file is gone; claimed file is on disk.
    pending_path = tmp_path / ".hermes3d_orchestrator" / "tasks" / "pending" / "T1.json"
    claimed_path = tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / "T1.json"
    assert not pending_path.exists()
    assert claimed_path.exists()
    body = json.loads(claimed_path.read_text(encoding="utf-8"))
    assert body["claimed_by"] == "hermes/factory-operator"


def test_claim_task_missing_returns_none(tmp_path: Path) -> None:
    snap = queue_bridge.claim_task(tmp_path, "nonexistent", "factory-operator")
    assert snap is None


def test_claim_task_already_claimed_returns_none(tmp_path: Path) -> None:
    """A task already in claimed/ cannot be claimed again from pending/."""
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    snap = queue_bridge.claim_task(tmp_path, "T1", "factory-operator")
    assert snap is None


# ---------------------------------------------------------------------------
# heartbeat / complete / block / release
# ---------------------------------------------------------------------------


def test_heartbeat_refreshes_timestamp(tmp_path: Path) -> None:
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    assert queue_bridge.heartbeat(tmp_path, "T1", persona="factory-operator") is True
    body = json.loads(
        (tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / "T1.json").read_text(
            encoding="utf-8"
        )
    )
    assert body["heartbeat_utc"] is not None


def test_heartbeat_rejects_wrong_persona(tmp_path: Path) -> None:
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    # A different persona must not be able to heartbeat someone else's claim.
    assert queue_bridge.heartbeat(tmp_path, "T1", persona="modeling-agent") is False


def test_complete_task_moves_to_done(tmp_path: Path) -> None:
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    assert queue_bridge.complete_task(tmp_path, "T1", persona="factory-operator") is True
    assert (tmp_path / ".hermes3d_orchestrator" / "tasks" / "done" / "T1.json").exists()
    assert not (tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / "T1.json").exists()


def test_block_task_moves_to_blocked_with_reason(tmp_path: Path) -> None:
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    assert (
        queue_bridge.block_task(tmp_path, "T1", "missing CAD toolchain", persona="factory-operator")
        is True
    )
    body = json.loads(
        (tmp_path / ".hermes3d_orchestrator" / "tasks" / "blocked" / "T1.json").read_text(
            encoding="utf-8"
        )
    )
    assert body["blocked_reason"] == "missing CAD toolchain"


def test_release_task_returns_to_pending(tmp_path: Path) -> None:
    _write_task(tmp_path, "claimed", "T1", claimed_by="hermes/factory-operator")
    assert queue_bridge.release_task(tmp_path, "T1") is True
    body = json.loads(
        (tmp_path / ".hermes3d_orchestrator" / "tasks" / "pending" / "T1.json").read_text(
            encoding="utf-8"
        )
    )
    assert body["claimed_by"] is None
    assert body["claimed_utc"] is None
