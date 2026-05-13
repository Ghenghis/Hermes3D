from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _init_db(path: Path) -> sqlite3.Connection:
    schema = SRC / "hermes3d" / "db" / "schema.sql"
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _insert_job(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: str = "queued",
    dry_run: int = 1,
    created_at: str = "2026-05-11 16:52:59",
    printer_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run, created_at, updated_at)
        VALUES (?, ?, 'slice', ?, ?, ?, ?, ?)
        """,
        (job_id, f"job-{job_id}", status, printer_id, dry_run, created_at, created_at),
    )
    conn.commit()


def test_retire_stale_dry_run_jobs_marks_only_old_dry_run_queue_entries(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes3d.services import job_reconciler

    db_path = tmp_path / "hermes3d.db"
    conn = _init_db(db_path)
    _insert_job(conn, "old-dry", dry_run=1, created_at="2026-05-11 00:00:00")
    _insert_job(conn, "fresh-dry", dry_run=1, created_at="2026-05-13 04:59:00")
    _insert_job(conn, "old-real", dry_run=0, created_at="2026-05-11 00:00:00")
    _insert_job(conn, "old-done", status="completed", dry_run=1, created_at="2026-05-11 00:00:00")
    conn.close()
    monkeypatch.setattr(job_reconciler, "DB_PATH", db_path)

    result = job_reconciler.retire_stale_dry_run_jobs(max_age_hours=24)

    assert result["retired_count"] == 1
    assert result["retired"][0]["job_id"] == "old-dry"
    with sqlite3.connect(db_path) as check:
        check.row_factory = sqlite3.Row
        statuses = {
            row["id"]: row["status"] for row in check.execute("SELECT id, status FROM jobs")
        }
        assert statuses == {
            "old-dry": "cancelled",
            "fresh-dry": "queued",
            "old-real": "queued",
            "old-done": "completed",
        }
        events = check.execute(
            "SELECT event_type, source_agent, message FROM job_events WHERE job_id = ?",
            ("old-dry",),
        ).fetchall()
        assert len(events) == 1
        assert events[0]["event_type"] == "stale_dry_run_cancelled"
        assert events[0]["source_agent"] == "job_reconciler"
        assert "proof_event_id=" in events[0]["message"]
        proof = check.execute(
            "SELECT event_type, source_agent, payload FROM proof_events"
        ).fetchone()
        assert proof["event_type"] == "jobs.reconcile.stale_dry_run_cancelled"
        assert proof["source_agent"] == "job_reconciler"
        payload = json.loads(proof["payload"])
        assert payload["job_id"] == "old-dry"
        assert payload["status"] == "cancelled"
        assert payload["dry_run"] is True
        assert payload["reason"].endswith("no printer command sent.")


def test_retire_stale_dry_run_jobs_clamps_age_and_is_idempotent(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes3d.services import job_reconciler

    db_path = tmp_path / "hermes3d.db"
    conn = _init_db(db_path)
    _insert_job(conn, "old-dry", dry_run=1, created_at="2026-05-11 00:00:00")
    conn.close()
    monkeypatch.setattr(job_reconciler, "DB_PATH", db_path)

    first = job_reconciler.retire_stale_dry_run_jobs(max_age_hours=-1)
    second = job_reconciler.retire_stale_dry_run_jobs(max_age_hours=24)

    assert first["max_age_hours"] == 1
    assert first["retired_count"] == 1
    assert second["retired_count"] == 0
