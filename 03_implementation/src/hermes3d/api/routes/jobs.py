from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows
from hermes3d.api.safety import check_s1_lock
from hermes3d.services.local_state import local_printer as _local_printer
from hermes3d.services.proof_helpers import attach_version_fields

router = APIRouter()

# Printer IDs that may receive job commands (write-enabled, policy-gated).
# S1 (192.168.0.12) is camera/read-only and MUST NOT receive job commands.
WRITE_ALLOWED_PRINTERS = {"flsun_t1_a", "flsun_t1_b", "flsun_v400"}
# Moonraker print_stats states that are safe to send a new job to.
PRINTER_IDLE_STATES = {"standby", "complete", "ready", "error"}


def _check_printer_policy(job: dict[str, Any], actor: str) -> None:
    """Policy gate: raises HTTPException if the job's printer cannot accept commands.

    Rules enforced (in order):
    1. S1 (192.168.0.12) is always locked — never a job target.
    2. The printer must be in WRITE_ALLOWED_PRINTERS or have write_enabled=True in the DB.
    3. The printer must report an idle Moonraker state (PRINTER_IDLE gate).
    """
    printer_id = job.get("printer_id")
    if not printer_id:
        # No printer assigned — policy gate passes; the job does not command any printer.
        return

    # Gate 1: S1 hard lock
    check_s1_lock(printer_id)

    # Gate 2: write-allowed list + DB policy
    printer = _local_printer(printer_id)
    if printer is not None:
        safety_policy = str(printer.get("safety_policy") or "read_only")
        write_enabled = printer.get("write_enabled", False)
        is_write_allowed = (
            printer["id"] in WRITE_ALLOWED_PRINTERS
            or write_enabled
            or safety_policy == "write_enabled"
        )
        if not is_write_allowed:
            proof_event_id = _append_proof_event(
                "jobs.policy.printer_write_denied",
                actor,
                {
                    "job_id": job["id"],
                    "printer_id": printer_id,
                    "safety_policy": safety_policy,
                    "reason": "Printer is not write-enabled; job commands are blocked by policy.",
                },
            )
            raise HTTPException(
                status_code=423,
                detail={
                    "error": "PRINTER_WRITE_DENIED",
                    "printer_id": printer_id,
                    "safety_policy": safety_policy,
                    "reason": "Printer is not write-enabled; job commands are blocked by policy.",
                    "proof_event_id": proof_event_id,
                },
            )

        # Gate 3: PRINTER_IDLE — never send job commands to a moving printer
        live_state: str | None = printer.get("state") or printer.get("status")
        if live_state and live_state.lower() not in PRINTER_IDLE_STATES:
            proof_event_id = _append_proof_event(
                "jobs.policy.printer_not_idle",
                actor,
                {
                    "job_id": job["id"],
                    "printer_id": printer_id,
                    "printer_state": live_state,
                    "reason": "PRINTER_IDLE gate: printer is not idle; retry/repair/rollback commands are blocked.",
                },
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "PRINTER_NOT_IDLE",
                    "gate": "PRINTER_IDLE",
                    "printer_id": printer_id,
                    "printer_state": live_state,
                    "reason": "PRINTER_IDLE gate: printer is not idle; retry/repair/rollback commands are blocked until the printer reaches standby/complete/ready.",
                    "proof_event_id": proof_event_id,
                },
            )


class JobCreate(BaseModel):
    name: str | None = None
    type: str | None = None
    job_type: str = "print"
    printer_id: str | None = None
    dry_run: bool = True


class JobActorRequest(BaseModel):
    actor: str = "operator"
    reason: str = ""
    notes: str = ""


class JobRollbackRequest(JobActorRequest):
    target_artifact_id: str | None = None


@router.get("/api/jobs")
def list_jobs(status: str | None = None) -> list[dict]:
    return rows(
        "SELECT * FROM jobs WHERE (? IS NULL OR status IN (SELECT value FROM json_each(?))) ORDER BY created_at DESC",
        (status, json.dumps(status.split(",")) if status else None),
    )


@router.post("/api/jobs", status_code=201)
def create_job(body: JobCreate) -> dict:
    job_id = new_id()
    job_type = body.type or body.job_type
    name = body.name or job_type.replace("_", " ").title()
    execute(
        "INSERT INTO jobs (id, name, job_type, printer_id, dry_run) VALUES (?, ?, ?, ?, ?)",
        (job_id, name, job_type, body.printer_id, int(body.dry_run)),
    )
    return row("SELECT * FROM jobs WHERE id = ?", (job_id,)) or {}


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = row("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    job["steps"] = rows("SELECT * FROM job_steps WHERE job_id = ? ORDER BY step_number", (job_id,))
    job["events"] = rows("SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at", (job_id,))
    job["artifacts"] = rows(
        "SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at", (job_id,)
    )
    job["approvals"] = rows(
        "SELECT * FROM approvals WHERE job_id = ? ORDER BY requested_at DESC", (job_id,)
    )
    job["transition_state"] = _transition_state(
        job, job["steps"], job["artifacts"], job["approvals"]
    )
    return job


async def _job_events(job_id: str):
    yield f"data: {json.dumps({'job_id': job_id, 'event_type': 'stream_open'})}\n\n"
    while True:
        await asyncio.sleep(15)
        yield ": keepalive\n\n"


@router.get("/api/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    return StreamingResponse(_job_events(job_id), media_type="text/event-stream")


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = row("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] not in {"queued", "running"}:
        proof_event_id = _append_proof_event(
            "jobs.cancel.blocked",
            "jobs-api",
            {"job_id": job_id, "status": job["status"], "reason": "job is not cancellable"},
        )
        _append_job_event(
            job_id,
            "cancel_blocked",
            "jobs-api",
            f"Cancel blocked for status {job['status']}; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={"reason": "job is not cancellable", "proof_event_id": proof_event_id},
        )
    execute(
        "UPDATE jobs SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?", (job_id,)
    )
    proof_event_id = _append_proof_event(
        "jobs.cancel.accepted",
        "jobs-api",
        {"job_id": job_id, "previous_status": job["status"], "status": "cancelled"},
    )
    _append_job_event(
        job_id, "cancelled", "jobs-api", f"Job cancelled; proof_event_id={proof_event_id}"
    )
    return {"job_id": job_id, "status": "cancelled", "proof_event_id": proof_event_id}


@router.post("/api/jobs/{job_id}/repair/propose", status_code=202)
def propose_repair(job_id: str, body: JobActorRequest) -> dict:
    job = _require_job(job_id)
    # Repair proposal is a read-only planning step — no printer commands are sent.
    # We still check the S1 hard lock to prevent accidental mis-routing.
    check_s1_lock(job.get("printer_id"))
    steps = rows("SELECT * FROM job_steps WHERE job_id = ? ORDER BY step_number", (job_id,))
    failed_step = _failed_step(job, steps)
    if not failed_step:
        proof_event_id = _append_proof_event(
            "jobs.repair.proposal.blocked",
            body.actor,
            {
                "job_id": job_id,
                "status": job["status"],
                "reason": "No failed job step or failed job status is available for repair proposal.",
            },
        )
        _append_job_event(
            job_id,
            "repair_proposal_blocked",
            body.actor,
            f"Repair proposal blocked; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "No failed job step or failed job status is available for repair proposal.",
                "proof_event_id": proof_event_id,
            },
        )
    existing = row(
        "SELECT * FROM approvals WHERE job_id = ? AND approval_type = 'REPAIR_APPROVAL' AND status = 'pending' ORDER BY requested_at DESC LIMIT 1",
        (job_id,),
    )
    if existing:
        proof_event_id = _append_proof_event(
            "jobs.repair.proposal.existing",
            body.actor,
            {"job_id": job_id, "approval_id": existing["id"], "status": existing["status"]},
        )
        _append_job_event(
            job_id,
            "repair_proposal_existing",
            body.actor,
            f"Repair approval already pending: {existing['id']}; proof_event_id={proof_event_id}",
        )
        return {
            "job_id": job_id,
            "status": "pending",
            "approval_id": existing["id"],
            "proof_event_id": proof_event_id,
            "created": False,
        }
    approval_id = new_id()
    summary = _repair_summary(job, failed_step, body.reason or body.notes)
    execute(
        """
        INSERT INTO approvals (id, approval_type, job_id, model_name, requesting_agent, status, notes)
        VALUES (?, 'REPAIR_APPROVAL', ?, ?, ?, 'pending', ?)
        """,
        (approval_id, job_id, job["name"], body.actor, as_json(summary)),
    )
    proof_event_id = _append_proof_event(
        "jobs.repair.proposal.requested",
        body.actor,
        {"job_id": job_id, "approval_id": approval_id, **summary},
    )
    _append_job_event(
        job_id,
        "repair_proposal_requested",
        body.actor,
        f"Repair approval requested: {approval_id}; proof_event_id={proof_event_id}",
    )
    return {
        "job_id": job_id,
        "status": "pending",
        "approval_id": approval_id,
        "proof_event_id": proof_event_id,
        "created": True,
        "proposal": summary,
    }


@router.post("/api/jobs/{job_id}/repair/apply")
def apply_repair(job_id: str, body: JobActorRequest) -> dict:
    job = _require_job(job_id)
    # Policy gate: repair apply may queue the job — check printer is idle and write-allowed.
    _check_printer_policy(job, body.actor)
    steps = rows("SELECT * FROM job_steps WHERE job_id = ? ORDER BY step_number", (job_id,))
    failed_step = _failed_step(job, steps)
    approval = _approved_repair_approval(job_id)
    if not approval:
        proof_event_id = _append_proof_event(
            "jobs.repair.apply.blocked",
            body.actor,
            {
                "job_id": job_id,
                "status": job["status"],
                "reason": "Approved REPAIR_APPROVAL is required before repair execution.",
            },
        )
        _append_job_event(
            job_id,
            "repair_apply_blocked",
            body.actor,
            f"Repair apply blocked: approval required; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Approved REPAIR_APPROVAL is required before repair execution.",
                "proof_event_id": proof_event_id,
            },
        )
    if not failed_step:
        proof_event_id = _append_proof_event(
            "jobs.repair.apply.blocked",
            body.actor,
            {
                "job_id": job_id,
                "status": job["status"],
                "approval_id": approval["id"],
                "reason": "No failed job step remains to repair.",
            },
        )
        _append_job_event(
            job_id,
            "repair_apply_blocked",
            body.actor,
            f"Repair apply blocked: no failed step; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "No failed job step remains to repair.",
                "proof_event_id": proof_event_id,
            },
        )
    result = _repair_agent_result(job, failed_step)
    status = "repair_ready_for_retry" if result["outcome"] == "fixed" else "repair_escalated"
    if result["outcome"] == "fixed":
        execute(
            """
            UPDATE job_steps
            SET status = 'pending', error = NULL, started_at = NULL, ended_at = NULL, duration_s = NULL
            WHERE id = ?
            """,
            (failed_step["id"],),
        )
        execute(
            "UPDATE jobs SET status = 'queued', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
    proof_event_id = _append_proof_event(
        "jobs.repair.apply.completed",
        body.actor,
        {"job_id": job_id, "approval_id": approval["id"], "status": status, "repair": result},
    )
    _append_job_event(
        job_id,
        "repair_apply_completed",
        body.actor,
        f"Repair result {result['outcome']}; proof_event_id={proof_event_id}",
    )
    return {
        "job_id": job_id,
        "status": status,
        "approval_id": approval["id"],
        "proof_event_id": proof_event_id,
        "repair": result,
    }


@router.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, body: JobActorRequest) -> dict:
    job = _require_job(job_id)
    # Policy gate: retry re-queues the job for print — must pass PRINTER_IDLE + write policy.
    _check_printer_policy(job, body.actor)
    pending = _pending_repair_approval(job_id)
    if pending:
        proof_event_id = _append_proof_event(
            "jobs.retry.blocked",
            body.actor,
            {
                "job_id": job_id,
                "approval_id": pending["id"],
                "reason": "Pending REPAIR_APPROVAL must be decided before retry.",
            },
        )
        _append_job_event(
            job_id,
            "retry_blocked",
            body.actor,
            f"Retry blocked by pending repair approval {pending['id']}; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Pending REPAIR_APPROVAL must be decided before retry.",
                "approval_id": pending["id"],
                "proof_event_id": proof_event_id,
            },
        )
    if job["status"] not in {"failed", "cancelled", "rolled_back", "waiting_approval"}:
        proof_event_id = _append_proof_event(
            "jobs.retry.blocked",
            body.actor,
            {
                "job_id": job_id,
                "status": job["status"],
                "reason": "Only failed, cancelled, rolled_back, or waiting_approval jobs can be retried.",
            },
        )
        _append_job_event(
            job_id,
            "retry_blocked",
            body.actor,
            f"Retry blocked for status {job['status']}; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Only failed, cancelled, rolled_back, or waiting_approval jobs can be retried.",
                "proof_event_id": proof_event_id,
            },
        )
    execute(
        """
        UPDATE job_steps
        SET status = 'pending', error = NULL, started_at = NULL, ended_at = NULL, duration_s = NULL
        WHERE job_id = ? AND status = 'failed'
        """,
        (job_id,),
    )
    execute(
        "UPDATE jobs SET status = 'queued', updated_at = datetime('now') WHERE id = ?", (job_id,)
    )
    proof_event_id = _append_proof_event(
        "jobs.retry.accepted",
        body.actor,
        {
            "job_id": job_id,
            "previous_status": job["status"],
            "status": "queued",
            "reason": body.reason or body.notes,
        },
    )
    _append_job_event(
        job_id, "retry_queued", body.actor, f"Retry queued; proof_event_id={proof_event_id}"
    )
    return {"job_id": job_id, "status": "queued", "proof_event_id": proof_event_id}


@router.post("/api/jobs/{job_id}/rollback")
def rollback_job(job_id: str, body: JobRollbackRequest) -> dict:
    job = _require_job(job_id)
    # Policy gate: rollback reverts job state and may requeue — check printer is idle and write-allowed.
    _check_printer_policy(job, body.actor)
    target = _rollback_target(job_id, body.target_artifact_id)
    if not target:
        proof_event_id = _append_proof_event(
            "jobs.rollback.blocked",
            body.actor,
            {
                "job_id": job_id,
                "status": job["status"],
                "target_artifact_id": body.target_artifact_id,
                "reason": "No rollback checkpoint artifact is recorded for this job.",
            },
        )
        _append_job_event(
            job_id,
            "rollback_blocked",
            body.actor,
            f"Rollback blocked: no checkpoint; proof_event_id={proof_event_id}",
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "No rollback checkpoint artifact is recorded for this job.",
                "proof_event_id": proof_event_id,
            },
        )
    step_id = new_id()
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
        VALUES (?, ?, COALESCE((SELECT MAX(step_number) + 1 FROM job_steps WHERE job_id = ?), 1), ?, 'done', datetime('now'), datetime('now'), ?)
        """,
        (step_id, job_id, job_id, f"Rollback to {target['label'] or target['id']}", 0.0),
    )
    execute(
        "UPDATE jobs SET status = 'rolled_back', updated_at = datetime('now') WHERE id = ?",
        (job_id,),
    )
    proof_event_id = _append_proof_event(
        "jobs.rollback.accepted",
        body.actor,
        {
            "job_id": job_id,
            "previous_status": job["status"],
            "status": "rolled_back",
            "target_artifact_id": target["id"],
            "target_path": target["file_path"],
        },
    )
    _append_job_event(
        job_id,
        "rollback_completed",
        body.actor,
        f"Rolled back to artifact {target['id']}; proof_event_id={proof_event_id}",
    )
    return {
        "job_id": job_id,
        "status": "rolled_back",
        "target_artifact_id": target["id"],
        "proof_event_id": proof_event_id,
    }


@router.get("/api/jobs/{job_id}/artifacts/{artifact_id}/download")
def download_job_artifact(job_id: str, artifact_id: str) -> FileResponse:
    artifact = row("SELECT * FROM artifacts WHERE id = ? AND job_id = ?", (artifact_id, job_id))
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(artifact["file_path"])


def _require_job(job_id: str) -> dict[str, Any]:
    job = row("SELECT * FROM jobs WHERE id = ?", (job_id,))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


def _append_job_event(job_id: str, event_type: str, source_agent: str, message: str) -> str:
    event_id = new_id()
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, ?, ?, ?)",
        (event_id, job_id, event_type, source_agent, message),
    )
    return event_id


def _append_proof_event(event_type: str, source_agent: str, payload: dict[str, Any]) -> str:
    # Wave 2 P2-6 (2026-05-09): version-tag every persisted proof
    # event with the active Hermes Agent version + upstream tag at
    # write time. Provenance basis: NIST SP 800-92 §4 (log generation
    # / storage) + OpenTelemetry ``service.version`` resource
    # attribute. See services/proof_helpers.py. This jobs.py helper
    # adds ``ts_unix`` BEFORE merging version fields so a caller who
    # explicitly stamps a ``version_label`` in their payload still
    # wins (attach_version_fields preserves caller keys on collision).
    event_id = new_id()
    proof_payload = attach_version_fields(
        {"ts_unix": round(time.time(), 3), **payload},
    )
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (event_id, event_type, source_agent, as_json(proof_payload)),
    )
    return event_id


def _transition_state(
    job: dict[str, Any],
    steps: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = _failed_step(job, steps)
    pending_repair = next(
        (
            approval
            for approval in approvals
            if approval["approval_type"] == "REPAIR_APPROVAL" and approval["status"] == "pending"
        ),
        None,
    )
    approved_repair = next(
        (
            approval
            for approval in approvals
            if approval["approval_type"] == "REPAIR_APPROVAL" and approval["status"] == "approved"
        ),
        None,
    )
    rollback_targets = [
        _artifact_summary(artifact) for artifact in artifacts if _is_rollback_target(artifact)
    ]
    return {
        "failed_step_id": failed["id"] if failed else None,
        "failed_step": _step_summary(failed) if failed else None,
        "pending_repair_approval_id": pending_repair["id"] if pending_repair else None,
        "approved_repair_approval_id": approved_repair["id"] if approved_repair else None,
        "rollback_targets": rollback_targets,
        "can_request_repair": bool(failed and pending_repair is None),
        "can_apply_repair": bool(failed and approved_repair is not None),
        "can_retry": job["status"] in {"failed", "cancelled", "rolled_back", "waiting_approval"}
        and pending_repair is None,
        "can_rollback": bool(rollback_targets),
        "blocker": _transition_blocker(
            job, failed, pending_repair, approved_repair, rollback_targets
        ),
    }


def _transition_blocker(
    job: dict[str, Any],
    failed: dict[str, Any] | None,
    pending_repair: dict[str, Any] | None,
    approved_repair: dict[str, Any] | None,
    rollback_targets: list[dict[str, Any]],
) -> dict[str, str]:
    if pending_repair:
        return {
            "gate": "REPAIR_APPROVAL",
            "reason": f"Repair approval {pending_repair['id']} is pending operator decision.",
        }
    if failed and not approved_repair:
        return {
            "gate": "REPAIR_PROPOSAL",
            "reason": "A failed step needs a repair proposal and approval before retry or mutation.",
        }
    if failed and approved_repair:
        return {
            "gate": "REPAIR_EXECUTION",
            "reason": f"Approved repair {approved_repair['id']} can be applied or the job can be retried.",
        }
    if job["status"] in {"failed", "cancelled"} and not rollback_targets:
        return {
            "gate": "ROLLBACK_TARGET",
            "reason": "No rollback checkpoint artifact is recorded for this job.",
        }
    return {"gate": "NONE", "reason": "No job transition blocker is active."}


def _failed_step(job: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((step for step in steps if step["status"] == "failed"), None) or (
        {"id": None, "name": job["name"], "status": job["status"], "error": None}
        if job["status"] == "failed"
        else None
    )


def _step_summary(step: dict[str, Any] | None) -> dict[str, Any] | None:
    if not step:
        return None
    return {
        "id": step.get("id"),
        "name": step.get("name"),
        "status": step.get("status"),
        "error": step.get("error"),
    }


def _artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": artifact["id"],
        "label": artifact.get("label"),
        "file_path": artifact.get("file_path"),
        "evidence_type": artifact.get("evidence_type"),
        "gate": artifact.get("gate"),
    }


def _repair_summary(
    job: dict[str, Any], failed_step: dict[str, Any], reason: str
) -> dict[str, Any]:
    return {
        "job_id": job["id"],
        "job_name": job["name"],
        "job_status": job["status"],
        "failed_step": _step_summary(failed_step),
        "requested_reason": reason,
        "policy": "operator approval required before repair execution; no printer movement is performed by repair proposal",
    }


def _pending_repair_approval(job_id: str) -> dict[str, Any] | None:
    return row(
        "SELECT * FROM approvals WHERE job_id = ? AND approval_type = 'REPAIR_APPROVAL' AND status = 'pending' ORDER BY requested_at DESC LIMIT 1",
        (job_id,),
    )


def _approved_repair_approval(job_id: str) -> dict[str, Any] | None:
    return row(
        "SELECT * FROM approvals WHERE job_id = ? AND approval_type = 'REPAIR_APPROVAL' AND status = 'approved' ORDER BY decided_at DESC, requested_at DESC LIMIT 1",
        (job_id,),
    )


def _repair_agent_result(job: dict[str, Any], failed_step: dict[str, Any]) -> dict[str, Any]:
    try:
        from hermes3d.core.orchestration.repair_agent import RepairAgent
        from hermes3d.core.orchestration.retry_controller import RepairEscalation

        cause = RuntimeError(str(failed_step.get("error") or f"Job {job['id']} failed."))
        escalation = RepairEscalation(
            cause=cause,
            attempts=1,
            context={
                "job_id": job["id"],
                "node_name": failed_step.get("name") or job["name"],
                "printer_id": job.get("printer_id"),
            },
        )
        result = RepairAgent().repair(escalation)
        return {
            "outcome": result.outcome,
            "strategy_used": result.strategy_used,
            "notes": result.notes,
            "suggested_action": result.suggested_action,
        }
    except Exception as exc:
        return {
            "outcome": "escalated",
            "strategy_used": "backend_exception",
            "notes": f"Repair agent unavailable: {exc}",
            "suggested_action": {"manual_review_required": True},
        }


def _rollback_target(job_id: str, target_artifact_id: str | None) -> dict[str, Any] | None:
    if target_artifact_id:
        artifact = row(
            "SELECT * FROM artifacts WHERE id = ? AND job_id = ?", (target_artifact_id, job_id)
        )
        return artifact if artifact and _is_rollback_target(artifact) else None
    return row(
        """
        SELECT * FROM artifacts
        WHERE job_id = ?
          AND (
            evidence_type IN ('checkpoint', 'rollback_checkpoint')
            OR gate = 'ROLLBACK_TARGET'
            OR notes LIKE '%"rollback_target":true%'
          )
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (job_id,),
    )


def _is_rollback_target(artifact: dict[str, Any]) -> bool:
    return (
        artifact.get("evidence_type") in {"checkpoint", "rollback_checkpoint"}
        or artifact.get("gate") == "ROLLBACK_TARGET"
        or '"rollback_target":true' in str(artifact.get("notes") or "")
    )
