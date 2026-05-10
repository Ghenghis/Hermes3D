"""Policy-gate tests for job repair/retry/rollback routes.

Covers:
- S1 (192.168.0.12) is rejected for all write actions (propose, apply, retry, rollback)
- Read-only printer is rejected for apply/retry/rollback
- Non-idle printer state is rejected for apply/retry/rollback
- Jobs without a printer_id pass the policy gate (no printer targeted)
- Write-enabled printer in idle state passes all gates
- Proof events are recorded in the DB on every policy block
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — make hermes3d importable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---------------------------------------------------------------------------
# Minimal DB fixture
# ---------------------------------------------------------------------------
SCHEMA_SQL = (SRC / "hermes3d" / "db" / "schema.sql").read_text()


def _new_id() -> str:
    return uuid.uuid4().hex


def _make_db(tmp_path: Path) -> tuple[sqlite3.Connection, Path]:
    db_path = tmp_path / "hermes3d_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn, db_path


def _insert_job(
    conn: sqlite3.Connection, job_id: str, status: str = "failed", printer_id: str | None = None
) -> None:
    conn.execute(
        "INSERT INTO jobs (id, name, job_type, status, printer_id) VALUES (?, ?, 'print', ?, ?)",
        (job_id, f"job-{job_id[:8]}", status, printer_id),
    )
    conn.commit()


def _insert_failed_step(conn: sqlite3.Connection, job_id: str) -> str:
    step_id = _new_id()
    conn.execute(
        "INSERT INTO job_steps (id, job_id, step_number, name, status, error) VALUES (?, ?, 1, 'slice', 'failed', 'adhesion lost')",
        (step_id, job_id),
    )
    conn.commit()
    return step_id


def _insert_approved_repair(conn: sqlite3.Connection, job_id: str) -> str:
    approval_id = _new_id()
    conn.execute(
        "INSERT INTO approvals (id, approval_type, job_id, status) VALUES (?, 'REPAIR_APPROVAL', ?, 'approved')",
        (approval_id, job_id),
    )
    conn.commit()
    return approval_id


def _insert_checkpoint_artifact(conn: sqlite3.Connection, job_id: str) -> str:
    artifact_id = _new_id()
    conn.execute(
        "INSERT INTO artifacts (id, job_id, evidence_type, gate, label, file_path) VALUES (?, ?, 'checkpoint', 'ROLLBACK_TARGET', 'v1', '/tmp/ckpt.zip')",
        (artifact_id, job_id),
    )
    conn.commit()
    return artifact_id


# ---------------------------------------------------------------------------
# Printer stub factory
# ---------------------------------------------------------------------------


def _make_printer(
    printer_id: str,
    *,
    write_enabled: bool = True,
    safety_policy: str = "write_enabled",
    state: str = "standby",
) -> dict[str, Any]:
    return {
        "id": printer_id,
        "name": printer_id,
        "write_enabled": write_enabled,
        "safety_policy": safety_policy,
        "state": state,
        "status": state,
    }


# ---------------------------------------------------------------------------
# Context manager: patch the jobs routes to use a test DB and stubbed printers
# ---------------------------------------------------------------------------


def _job_patches(conn: sqlite3.Connection, printer_stub: dict | None, is_s1: bool = False):
    """Return a list of patch context managers for isolating jobs route calls."""

    def _rows(sql, params=()):
        return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def _row(sql, params=()):
        results = _rows(sql, params)
        return results[0] if results else None

    def _execute(sql, params=()):
        conn.execute(sql, params)
        conn.commit()

    return [
        patch("hermes3d.api.routes.jobs.rows", _rows),
        patch("hermes3d.api.routes.jobs.row", _row),
        patch("hermes3d.api.routes.jobs.execute", _execute),
        # Patch is_s1_target at the safety module level (where check_s1_lock reads it)
        patch("hermes3d.api.safety.is_s1_target", lambda pid: is_s1),
        # Patch _local_printer in the jobs module (imported as alias)
        patch("hermes3d.api.routes.jobs._local_printer", lambda pid, **kw: printer_stub),
    ]


@contextlib.contextmanager
def _ctx(conn, printer_stub, is_s1=False):
    patches = _job_patches(conn, printer_stub, is_s1)
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


# ---------------------------------------------------------------------------
# Import the jobs routes module
# ---------------------------------------------------------------------------


def _routes():
    import hermes3d.api.routes.jobs as m

    return m


# ===========================================================================
# Tests: S1 hard lock — all write actions must be blocked for S1 printer IDs
# ===========================================================================


class TestS1HardLock:
    """S1 (192.168.0.12 / flsun-s1) must NEVER receive job commands."""

    S1_IDS = ["192.168.0.12", "flsun-s1", "flsun_s1", "s1"]

    @pytest.mark.parametrize("s1_id", S1_IDS)
    def test_propose_repair_blocked_for_s1(self, tmp_path, s1_id):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=s1_id)
        _insert_failed_step(conn, job_id)

        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub=None, is_s1=True):
            with pytest.raises(HTTPException) as exc_info:
                jobs.propose_repair(job_id, body)
            assert exc_info.value.status_code == 423
            assert "PRINTER_LOCKED" in str(exc_info.value.detail)

    @pytest.mark.parametrize("s1_id", S1_IDS)
    def test_retry_blocked_for_s1(self, tmp_path, s1_id):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=s1_id)

        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub=None, is_s1=True):
            with pytest.raises(HTTPException) as exc_info:
                jobs.retry_job(job_id, body)
            assert exc_info.value.status_code == 423

    @pytest.mark.parametrize("s1_id", S1_IDS)
    def test_rollback_blocked_for_s1(self, tmp_path, s1_id):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=s1_id)
        _insert_checkpoint_artifact(conn, job_id)

        jobs = _routes()
        body = jobs.JobRollbackRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub=None, is_s1=True):
            with pytest.raises(HTTPException) as exc_info:
                jobs.rollback_job(job_id, body)
            assert exc_info.value.status_code == 423

    @pytest.mark.parametrize("s1_id", S1_IDS)
    def test_apply_repair_blocked_for_s1(self, tmp_path, s1_id):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=s1_id)
        _insert_failed_step(conn, job_id)
        _insert_approved_repair(conn, job_id)

        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub=None, is_s1=True):
            with pytest.raises(HTTPException) as exc_info:
                jobs.apply_repair(job_id, body)
            assert exc_info.value.status_code == 423


# ===========================================================================
# Tests: read-only printer policy
# ===========================================================================


class TestReadOnlyPrinterPolicy:
    """A printer with safety_policy=read_only must not receive job commands."""

    def test_retry_blocked_for_read_only_printer(self, tmp_path):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="mystery_printer")

        printer_stub = _make_printer(
            "mystery_printer", write_enabled=False, safety_policy="read_only", state="standby"
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.retry_job(job_id, body)
            assert exc_info.value.status_code == 423
            assert exc_info.value.detail["error"] == "PRINTER_WRITE_DENIED"

    def test_rollback_blocked_for_read_only_printer(self, tmp_path):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="mystery_printer")
        _insert_checkpoint_artifact(conn, job_id)

        printer_stub = _make_printer(
            "mystery_printer", write_enabled=False, safety_policy="read_only", state="standby"
        )
        jobs = _routes()
        body = jobs.JobRollbackRequest(actor="operator")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.rollback_job(job_id, body)
            assert exc_info.value.status_code == 423
            assert exc_info.value.detail["error"] == "PRINTER_WRITE_DENIED"

    def test_apply_repair_blocked_for_read_only_printer(self, tmp_path):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="mystery_printer")
        _insert_failed_step(conn, job_id)
        _insert_approved_repair(conn, job_id)

        printer_stub = _make_printer(
            "mystery_printer", write_enabled=False, safety_policy="read_only", state="standby"
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.apply_repair(job_id, body)
            assert exc_info.value.status_code == 423
            assert exc_info.value.detail["error"] == "PRINTER_WRITE_DENIED"


# ===========================================================================
# Tests: PRINTER_IDLE gate
# ===========================================================================


class TestPrinterIdleGate:
    """Retry/repair-apply/rollback must be blocked when printer is not idle."""

    @pytest.mark.parametrize("active_state", ["printing", "paused", "busy", "homing"])
    def test_retry_blocked_when_printer_not_idle(self, tmp_path, active_state):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_a")

        printer_stub = _make_printer(
            "flsun_t1_a", write_enabled=True, safety_policy="write_enabled", state=active_state
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.retry_job(job_id, body)
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["error"] == "PRINTER_NOT_IDLE"
            assert exc_info.value.detail["gate"] == "PRINTER_IDLE"

    @pytest.mark.parametrize("active_state", ["printing", "paused"])
    def test_apply_repair_blocked_when_printer_not_idle(self, tmp_path, active_state):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_a")

        printer_stub = _make_printer(
            "flsun_t1_a", write_enabled=True, safety_policy="write_enabled", state=active_state
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.apply_repair(job_id, body)
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["gate"] == "PRINTER_IDLE"

    @pytest.mark.parametrize("active_state", ["printing", "busy"])
    def test_rollback_blocked_when_printer_not_idle(self, tmp_path, active_state):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_a")
        _insert_checkpoint_artifact(conn, job_id)

        printer_stub = _make_printer(
            "flsun_t1_a", write_enabled=True, safety_policy="write_enabled", state=active_state
        )
        jobs = _routes()
        body = jobs.JobRollbackRequest(actor="operator")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.rollback_job(job_id, body)
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["gate"] == "PRINTER_IDLE"


# ===========================================================================
# Tests: no printer — policy gate passes
# ===========================================================================


class TestNoPrinterPassesGate:
    """Jobs without a printer_id should pass the policy gate (no printer targeted)."""

    def test_retry_passes_for_job_without_printer(self, tmp_path):
        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=None)

        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub=None, is_s1=False):
            result = jobs.retry_job(job_id, body)
            assert result["status"] == "queued"
            assert "proof_event_id" in result

    def test_rollback_passes_for_job_without_printer(self, tmp_path):
        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id=None)
        _insert_checkpoint_artifact(conn, job_id)

        jobs = _routes()
        body = jobs.JobRollbackRequest(actor="operator")

        with _ctx(conn, printer_stub=None, is_s1=False):
            result = jobs.rollback_job(job_id, body)
            assert result["status"] == "rolled_back"
            assert "proof_event_id" in result


# ===========================================================================
# Tests: write-enabled idle printer — all actions pass policy gate
# ===========================================================================


class TestWriteEnabledIdlePrinterPasses:
    """A write-enabled printer in an idle state should pass the policy gate."""

    @pytest.mark.parametrize("idle_state", ["standby", "complete", "ready"])
    def test_retry_passes_for_idle_write_enabled_printer(self, tmp_path, idle_state):
        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_a")

        printer_stub = _make_printer(
            "flsun_t1_a", write_enabled=True, safety_policy="write_enabled", state=idle_state
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub, is_s1=False):
            result = jobs.retry_job(job_id, body)
            assert result["status"] == "queued"
            assert "proof_event_id" in result

    @pytest.mark.parametrize("idle_state", ["standby", "complete", "ready"])
    def test_rollback_passes_for_idle_write_enabled_printer(self, tmp_path, idle_state):
        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_a")
        _insert_checkpoint_artifact(conn, job_id)

        printer_stub = _make_printer(
            "flsun_t1_a", write_enabled=True, safety_policy="write_enabled", state=idle_state
        )
        jobs = _routes()
        body = jobs.JobRollbackRequest(actor="operator")

        with _ctx(conn, printer_stub, is_s1=False):
            result = jobs.rollback_job(job_id, body)
            assert result["status"] == "rolled_back"
            assert "proof_event_id" in result


# ===========================================================================
# Tests: proof events are recorded on policy violation
# ===========================================================================


class TestProofEventsOnPolicyBlock:
    """Policy gate blocks must record proof events in proof_events table."""

    def test_proof_event_written_on_write_denied(self, tmp_path):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="locked_printer")

        printer_stub = _make_printer(
            "locked_printer", write_enabled=False, safety_policy="read_only", state="standby"
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator", reason="test")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.retry_job(job_id, body)
            assert exc_info.value.status_code == 423
            proof_event_id = exc_info.value.detail.get("proof_event_id")
            assert proof_event_id, "proof_event_id must be returned in 423 response detail"

            events = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM proof_events WHERE id = ?", (proof_event_id,)
                ).fetchall()
            ]
            assert len(events) == 1
            payload = json.loads(events[0]["payload"])
            assert payload["job_id"] == job_id
            assert payload["printer_id"] == "locked_printer"

    def test_proof_event_written_on_printer_not_idle(self, tmp_path):
        from fastapi import HTTPException

        conn, _ = _make_db(tmp_path)
        job_id = _new_id()
        _insert_job(conn, job_id, status="failed", printer_id="flsun_t1_b")

        printer_stub = _make_printer(
            "flsun_t1_b", write_enabled=True, safety_policy="write_enabled", state="printing"
        )
        jobs = _routes()
        body = jobs.JobActorRequest(actor="operator")

        with _ctx(conn, printer_stub, is_s1=False):
            with pytest.raises(HTTPException) as exc_info:
                jobs.retry_job(job_id, body)
            assert exc_info.value.status_code == 409
            proof_event_id = exc_info.value.detail.get("proof_event_id")
            assert proof_event_id, "proof_event_id must be in 409 detail"

            events = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM proof_events WHERE id = ?", (proof_event_id,)
                ).fetchall()
            ]
            assert len(events) == 1
            payload = json.loads(events[0]["payload"])
            assert payload["printer_state"] == "printing"
