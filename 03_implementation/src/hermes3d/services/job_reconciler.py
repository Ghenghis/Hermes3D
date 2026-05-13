"""Job table reconciliation helpers."""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from hermes3d.db.init import DB_PATH

DEFAULT_STALE_DRY_RUN_JOB_HOURS = 24


def _new_id() -> str:
    return os.urandom(16).hex()


def _stale_hours(raw: int | float | str | None) -> int:
    try:
        value = int(raw) if raw is not None else DEFAULT_STALE_DRY_RUN_JOB_HOURS
    except (TypeError, ValueError):
        value = DEFAULT_STALE_DRY_RUN_JOB_HOURS
    return max(1, min(value, 168))


def retire_stale_dry_run_jobs(*, max_age_hours: int | None = None) -> dict[str, Any]:
    """Cancel old dry-run queued jobs that can never command hardware.

    Dry-run jobs are proof/workbench bookkeeping. If they remain queued
    after a day, they make the product look like it has real unhandled
    print work. Reconcile them into ``cancelled`` with explicit proof and
    job events. This function never sends printer commands.
    """

    age_hours = _stale_hours(
        max_age_hours
        if max_age_hours is not None
        else os.environ.get("HERMES3D_STALE_DRY_RUN_JOB_HOURS")
    )
    cutoff_expr = f"-{age_hours} hours"
    retired: list[dict[str, Any]] = []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        jobs = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'queued'
                  AND COALESCE(dry_run, 0) = 1
                  AND datetime(created_at) <= datetime('now', ?)
                ORDER BY created_at ASC
                """,
                (cutoff_expr,),
            ).fetchall()
        ]
        for job in jobs:
            proof_event_id = _new_id()
            payload = {
                "job_id": job["id"],
                "previous_status": job["status"],
                "status": "cancelled",
                "dry_run": bool(job.get("dry_run")),
                "printer_id": job.get("printer_id"),
                "max_age_hours": age_hours,
                "reason": "Retired stale dry-run queued job; no printer command sent.",
            }
            conn.execute(
                """
                INSERT INTO proof_events (id, event_type, source_agent, payload)
                VALUES (?, 'jobs.reconcile.stale_dry_run_cancelled', 'job_reconciler', ?)
                """,
                (proof_event_id, json.dumps(payload, sort_keys=True)),
            )
            conn.execute(
                """
                INSERT INTO job_events (id, job_id, event_type, source_agent, message)
                VALUES (?, ?, 'stale_dry_run_cancelled', 'job_reconciler', ?)
                """,
                (
                    _new_id(),
                    job["id"],
                    f"Retired stale dry-run queued job; proof_event_id={proof_event_id}",
                ),
            )
            conn.execute(
                "UPDATE jobs SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
                (job["id"],),
            )
            retired.append(
                {
                    "job_id": job["id"],
                    "name": job.get("name"),
                    "printer_id": job.get("printer_id"),
                    "proof_event_id": proof_event_id,
                }
            )
        conn.commit()

    return {
        "status": "ready",
        "retired_count": len(retired),
        "max_age_hours": age_hours,
        "retired": retired,
    }
