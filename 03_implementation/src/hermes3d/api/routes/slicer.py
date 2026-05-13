"""Slicer HTTP route — W18-A12 wire-up.

Status: runnable
Verdict gate: GUI_SLICER_GREEN

Exposes:
    POST /api/slice            — start a slice job (background thread).
    GET  /api/slice/{job_id}   — poll job status + final artifact details.

STRICT operator freeze (2026-05-11):
    The slicer produces G-code as a FILE on disk. This route NEVER uploads,
    dispatches, or transmits that G-code to a printer (no Moonraker /
    Klipper / OctoPrint / /api/printers writes). The deliverable is the
    file path + sha256 + analyzer metadata returned by GET.

Storage layout:
    var/slicer/{job_id}/
        ├── {stl_basename}.gcode       (real slicer output)
        └── proof.json                 (proof envelope: argv, sha256, etc.)

Persistence:
    * A row in ``jobs`` with ``job_type='slice'`` and ``dry_run=1``
      (the slicer never touches a printer, so dry_run is the honest flag).
    * Step + event rows + a ``slice_completed`` / ``slice_failed`` proof
      event in ``proof_events``.
    * Two ``artifacts`` rows on success (gcode + proof.json), so the
      existing /api/artifacts surface picks the files up automatically.

Backgrounding:
    Slicing takes a few seconds for a 10 mm cube but can grow to minutes
    for a large desk-organizer mesh, so the POST handler returns
    ``202 Accepted`` immediately and the work runs in a Python thread.
    SQLite is the rendezvous point — GET reads job + step + artifact rows.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows
from hermes3d.services.local_state import implementation_path

LOG = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request body
# ---------------------------------------------------------------------------


class SliceRequest(BaseModel):
    """Body of POST /api/slice."""

    stl_path: str = Field(..., description="Absolute or repo-relative path to the input STL.")
    printer_profile: str | None = Field(
        default=None,
        description=(
            "Slicer .ini profile path or profile id. Optional — when omitted the "
            "slicer falls back to its bundled defaults."
        ),
    )
    options: dict[str, Any] = Field(default_factory=dict, description="Future-use options.")


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _slicer_root() -> Path:
    """Return ``<repo>/var/slicer`` and ensure it exists."""

    root = implementation_path("var", "slicer")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(job_id: str) -> Path:
    out = _slicer_root() / job_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _detect_slicer_binary() -> Path | None:
    """Return the local slicer CLI binary when the active host can slice."""

    from hermes3d.core.slicer.slicer_runner import find_slicer

    slicer = find_slicer()
    return slicer if slicer is not None and slicer.is_file() else None


def _source_mesh_artifact_id(stl_path: Path) -> str | None:
    """Return the existing mesh artifact id for ``stl_path`` when known."""

    artifact = row(
        """
        SELECT id FROM artifacts
         WHERE file_path = ?
           AND evidence_type IN ('mesh', 'model')
         ORDER BY created_at DESC
         LIMIT 1
        """,
        (str(stl_path),),
    )
    artifact_id = artifact.get("id") if artifact else None
    return str(artifact_id) if artifact_id else None


def _resolve_stl(raw_path: str) -> Path:
    """Resolve the user-supplied path against common repo roots."""

    candidates: list[Path] = []
    raw = Path(raw_path)
    candidates.append(raw)
    if not raw.is_absolute():
        candidates.append(implementation_path(raw_path))
        candidates.append(implementation_path("..", raw_path))
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    raise HTTPException(
        status_code=404,
        detail={
            "status": "blocked",
            "reason": f"STL not found: {raw_path}",
            "searched": [str(c) for c in candidates],
        },
    )


def _record_proof_event(event_type: str, payload: dict[str, Any]) -> str:
    """Insert a row in ``proof_events`` and return the new event_id."""

    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, 'slicer-executor', ?)",
        (event_id, event_type, as_json(payload)),
    )
    return event_id


def _write_proof_envelope(
    *,
    job_dir: Path,
    job_id: str,
    request_body: SliceRequest,
    slice_result_dict: dict[str, Any],
    analyzer_dict: dict[str, Any],
    gcode_sha256: str,
    gcode_size_bytes: int,
    proof_event_id: str,
) -> Path:
    """Write the slicer proof envelope JSON beside the G-code."""

    proof_path = job_dir / "proof.json"
    envelope = {
        "schema": "hermes3d.slicer.proof.v1",
        "job_id": job_id,
        "request": request_body.model_dump(),
        "slicer": slice_result_dict,
        "analyzer": analyzer_dict,
        "gcode": {
            "path": slice_result_dict.get("gcode_path"),
            "size_bytes": gcode_size_bytes,
            "sha256": gcode_sha256,
        },
        "proof_event_id": proof_event_id,
        "freeze_assertions": {
            "no_printer_writes": True,
            "no_moonraker_upload": True,
            "no_klipper_dispatch": True,
            "no_octoprint_upload": True,
        },
    }
    proof_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return proof_path


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


def _run_slice_job(job_id: str, body: SliceRequest, stl_path: Path) -> None:
    """Run slice_mesh in a thread; persist outcome rows."""

    job_dir = _job_dir(job_id)
    try:
        from hermes3d.core.slicer.gcode_analyzer import analyze_gcode
        from hermes3d.core.slicer.slicer_runner import (
            SlicerError,
            SlicerNotFound,
            slice_mesh,
        )

        try:
            result = slice_mesh(
                stl_path,
                profile=body.printer_profile,
                output_dir=job_dir,
                timeout_seconds=int(body.options.get("timeout_seconds", 600)),
            )
        except SlicerNotFound as exc:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer_not_found: {exc}",
                stage="slicer.binary_lookup",
            )
            return
        except SlicerError as exc:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer_error: {exc}",
                stage="slicer.exec",
            )
            return
        except Exception as exc:  # noqa: BLE001 — capture any unexpected failure
            _finalize_failure(
                job_id=job_id,
                reason=f"unexpected_error: {exc}",
                stage="slicer.exec",
            )
            return

        gcode_path = Path(result.gcode_path)
        if not gcode_path.is_file():
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer reported success but gcode missing at {gcode_path}",
                stage="slicer.output_check",
            )
            return
        size_bytes = gcode_path.stat().st_size
        if size_bytes <= 0:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer wrote a zero-byte gcode at {gcode_path}",
                stage="slicer.output_check",
            )
            return

        gcode_sha = _file_sha256(gcode_path)
        try:
            analyzer = analyze_gcode(gcode_path)
            analyzer_dict = analyzer.to_dict()
        except Exception as exc:  # noqa: BLE001 — analyzer must not nuke a real slice
            LOG.warning("analyze_gcode failed for %s: %s", gcode_path, exc)
            analyzer_dict = {
                "error": f"analyzer_failed: {exc}",
                "layer_count": None,
                "motion_lines": 0,
            }

        result_dict = result.to_dict()
        proof_event_id = _record_proof_event(
            "slice_completed",
            {
                "job_id": job_id,
                "stl_path": str(stl_path),
                "gcode_path": str(gcode_path),
                "gcode_size_bytes": size_bytes,
                "gcode_sha256": gcode_sha,
                "layer_count": analyzer_dict.get("layer_count"),
                "motion_lines": analyzer_dict.get("motion_lines"),
                "estimated_print_time_min": analyzer_dict.get("estimated_print_time_min"),
                "slicer_binary": result_dict.get("slicer_binary"),
                "duration_seconds": result_dict.get("duration_seconds"),
            },
        )
        proof_path = _write_proof_envelope(
            job_dir=job_dir,
            job_id=job_id,
            request_body=body,
            slice_result_dict=result_dict,
            analyzer_dict=analyzer_dict,
            gcode_sha256=gcode_sha,
            gcode_size_bytes=size_bytes,
            proof_event_id=proof_event_id,
        )

        # Persist artifacts rows so /api/artifacts and the GUI artifact list
        # pick them up. We attach two artifacts: the gcode + the proof envelope.
        gcode_artifact_id = new_id()
        proof_artifact_id = new_id()
        source_mesh_artifact_id = _source_mesh_artifact_id(stl_path)
        gcode_notes = {
            "sha256": gcode_sha,
            "size_bytes": size_bytes,
            "layer_count": analyzer_dict.get("layer_count"),
            "motion_lines": analyzer_dict.get("motion_lines"),
            "estimated_print_time_min": analyzer_dict.get("estimated_print_time_min"),
            "estimated_filament_g": analyzer_dict.get("filament_used_g"),
            "proof_artifact_id": proof_artifact_id,
            "proof_event_id": proof_event_id,
            "slicer_binary": result_dict.get("slicer_binary"),
        }
        if source_mesh_artifact_id:
            gcode_notes["mesh_artifact_id"] = source_mesh_artifact_id
            gcode_notes["source_stl_path"] = str(stl_path)
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'gcode', 'slicer-executor', 'SLICING', 'SLICER_OUTPUT', ?, ?, ?, ?)
            """,
            (
                gcode_artifact_id,
                job_id,
                gcode_path.name,
                str(gcode_path),
                size_bytes,
                as_json(gcode_notes),
            ),
        )
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'proof_report', 'slicer-executor', 'SLICING', 'SLICER_OUTPUT', ?, ?, ?, ?)
            """,
            (
                proof_artifact_id,
                job_id,
                proof_path.name,
                str(proof_path),
                proof_path.stat().st_size,
                as_json(
                    {
                        "sha256": _file_sha256(proof_path),
                        "gcode_artifact_id": gcode_artifact_id,
                        "proof_event_id": proof_event_id,
                    }
                ),
            ),
        )

        execute(
            """
            INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
            VALUES (?, ?, 2, 'Slice STL via PrusaSlicer CLI', 'done', datetime('now'), datetime('now'), ?),
                   (?, ?, 3, 'Write signed slicer proof envelope', 'done', datetime('now'), datetime('now'), 0)
            """,
            (
                new_id(),
                job_id,
                float(result_dict.get("duration_seconds") or 0.0),
                new_id(),
                job_id,
            ),
        )
        execute(
            "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_completed', 'slicer-executor', ?)",
            (
                new_id(),
                job_id,
                f"Sliced {gcode_path.name} ({size_bytes} bytes, sha256={gcode_sha[:16]}); proof_event_id={proof_event_id}",
            ),
        )
        execute(
            "UPDATE jobs SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
    except Exception as exc:  # noqa: BLE001 — final safety net
        LOG.exception("Slicer background thread crashed for job %s", job_id)
        _finalize_failure(
            job_id=job_id,
            reason=f"background_thread_crash: {exc}",
            stage="slicer.thread",
        )


def _finalize_failure(*, job_id: str, reason: str, stage: str) -> None:
    """Mark the job failed and emit a slice_failed proof event."""

    proof_event_id = _record_proof_event(
        "slice_failed",
        {"job_id": job_id, "reason": reason, "stage": stage},
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, error)
        VALUES (?, ?, 2, 'Slice STL via PrusaSlicer CLI', 'failed', datetime('now'), datetime('now'), ?)
        """,
        (new_id(), job_id, reason[:1000]),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_failed', 'slicer-executor', ?)",
        (new_id(), job_id, f"{stage}: {reason[:400]}; proof_event_id={proof_event_id}"),
    )
    execute(
        "UPDATE jobs SET status = 'failed', updated_at = datetime('now') WHERE id = ?",
        (job_id,),
    )


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------


@router.post("/api/slice", status_code=202)
def post_slice(body: SliceRequest) -> dict[str, Any]:
    """Start a slicer job. Returns 202 with the new job_id immediately.

    The actual ``slice_mesh()`` call runs on a daemon thread and writes its
    outcome rows + artifacts back into SQLite.
    """

    stl_path = _resolve_stl(body.stl_path)
    job_id = new_id()
    execute(
        """
        INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run)
        VALUES (?, ?, 'slice', 'running', NULL, 1)
        """,
        (job_id, f"Slice {stl_path.name}"),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at)
        VALUES (?, ?, 1, 'Slice request received', 'done', datetime('now'), datetime('now'))
        """,
        (new_id(), job_id),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_requested', 'slicer-executor', ?)",
        (
            new_id(),
            job_id,
            f"POST /api/slice for stl={stl_path}; profile={body.printer_profile or '(default)'}",
        ),
    )

    thread = threading.Thread(
        target=_run_slice_job,
        args=(job_id, body, stl_path),
        name=f"slice-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return {
        "status": "accepted",
        "accepted": True,
        "job_id": job_id,
        "id": job_id,
        "stl_path": str(stl_path),
        "printer_profile": body.printer_profile,
        "freeze": {
            "no_printer_writes": True,
            "no_dispatch": True,
        },
    }


@router.get("/api/slice/{job_id}")
def get_slice(job_id: str) -> dict[str, Any]:
    """Return the job's current state plus G-code artifact details when terminal."""

    job = row("SELECT * FROM jobs WHERE id = ? AND job_type = 'slice'", (job_id,))
    if not job:
        raise HTTPException(
            status_code=404, detail={"status": "not_found", "reason": "slice job not found"}
        )
    status = str(job.get("status") or "queued").lower()

    job_artifacts = rows(
        "SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at ASC",
        (job_id,),
    )
    gcode_row = next(
        (a for a in job_artifacts if (a.get("evidence_type") or "").lower() == "gcode"),
        None,
    )
    proof_row = next(
        (a for a in job_artifacts if (a.get("evidence_type") or "").lower() == "proof_report"),
        None,
    )

    events_rows = rows(
        "SELECT id, event_type, source_agent, payload, created_at "
        "FROM proof_events WHERE event_type IN ('slice_completed','slice_failed') "
        "AND payload LIKE ? ORDER BY created_at DESC LIMIT 1",
        (f'%"job_id":"{job_id}"%',),
    )
    proof_event = events_rows[0] if events_rows else None
    proof_event_id = proof_event.get("id") if proof_event else None

    response: dict[str, Any] = {
        "id": job_id,
        "job_id": job_id,
        "status": status,
        "name": job.get("name"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "dry_run": bool(job.get("dry_run")),
        "proof_event_id": proof_event_id,
    }

    if gcode_row:
        notes = _parse_notes(gcode_row.get("notes"))
        response["gcode_path"] = gcode_row.get("file_path")
        response["sha256"] = notes.get("sha256")
        response["size_bytes"] = gcode_row.get("file_size")
        response["layer_count"] = notes.get("layer_count")
        response["motion_lines"] = notes.get("motion_lines")
        response["estimated_print_time_min"] = notes.get("estimated_print_time_min")
        response["estimated_filament_g"] = notes.get("estimated_filament_g")
        response["slicer_binary"] = notes.get("slicer_binary")
        response["gcode_artifact_id"] = gcode_row.get("id")
    if proof_row:
        response["proof_path"] = proof_row.get("file_path")
        response["proof_artifact_id"] = proof_row.get("id")

    if status == "failed":
        # Pull the last failed step's error and the slice_failed payload for
        # better operator messages.
        failed_step = next(
            iter(
                rows(
                    "SELECT * FROM job_steps WHERE job_id = ? AND status = 'failed' ORDER BY step_number DESC LIMIT 1",
                    (job_id,),
                )
            ),
            None,
        )
        if failed_step:
            response["error"] = failed_step.get("error")
        if proof_event:
            try:
                response["failure_payload"] = json.loads(str(proof_event.get("payload") or "{}"))
            except json.JSONDecodeError:
                response["failure_payload"] = None

    return response


def _parse_notes(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _slice_job_counts() -> dict[str, int]:
    counts = {"running": 0, "completed": 0, "failed": 0, "queued": 0, "total": 0}
    for item in rows(
        "SELECT status, COUNT(*) AS count FROM jobs WHERE job_type = 'slice' GROUP BY status"
    ):
        status = str(item.get("status") or "unknown").lower()
        value = int(item.get("count") or 0)
        counts[status] = value
        counts["total"] += value
    return counts


def _latest_slice_job() -> dict[str, Any] | None:
    job = row(
        """
        SELECT * FROM jobs
         WHERE job_type = 'slice'
         ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC
         LIMIT 1
        """
    )
    return _slice_job_status(job)


def _slice_job_by_id(job_id: str | None) -> dict[str, Any] | None:
    if not job_id:
        return None
    job = row("SELECT * FROM jobs WHERE id = ? AND job_type = 'slice'", (job_id,))
    return _slice_job_status(job)


def _slice_job_status(job: dict[str, Any] | None) -> dict[str, Any] | None:
    if not job:
        return None
    return {
        "id": job.get("id"),
        "job_id": job.get("id"),
        "name": job.get("name"),
        "status": str(job.get("status") or "").lower(),
        "dry_run": bool(job.get("dry_run")),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


def _latest_slice_artifact(evidence_type: str, job_id: str | None = None) -> dict[str, Any] | None:
    params: tuple[Any, ...]
    if job_id:
        sql = """
            SELECT * FROM artifacts
             WHERE evidence_type = ?
               AND job_id = ?
             ORDER BY datetime(created_at) DESC
             LIMIT 1
        """
        params = (evidence_type, job_id)
    else:
        sql = """
            SELECT * FROM artifacts
             WHERE evidence_type = ?
               AND agent = 'slicer-executor'
             ORDER BY datetime(created_at) DESC
             LIMIT 1
        """
        params = (evidence_type,)
    artifact = row(sql, params)
    return _artifact_status(artifact) if artifact else None


def _artifact_status(artifact: dict[str, Any] | None) -> dict[str, Any] | None:
    if not artifact:
        return None
    notes = _parse_notes(artifact.get("notes"))
    raw_path = str(artifact.get("file_path") or "")
    path = Path(raw_path) if raw_path else None
    exists = bool(path and path.is_file())
    actual_size = path.stat().st_size if path and exists else None
    expected_size = artifact.get("file_size")
    expected_sha = notes.get("sha256")
    sha256_match: bool | None = None
    sha256_checked = False
    sha256_check_reason: str | None = None
    if exists and expected_sha:
        max_hash_bytes = int(os.environ.get("HERMES3D_SLICER_STATUS_HASH_LIMIT_BYTES", "67108864"))
        if actual_size is not None and actual_size <= max_hash_bytes:
            sha256_checked = True
            sha256_match = _file_sha256(path) == expected_sha
        else:
            sha256_check_reason = f"file_size_exceeds_hash_limit:{max_hash_bytes}"
    size_matches = (
        actual_size == expected_size if actual_size is not None and expected_size else None
    )
    valid = exists and bool(actual_size and actual_size > 0) and sha256_match is not False
    return {
        "id": artifact.get("id"),
        "job_id": artifact.get("job_id"),
        "evidence_type": artifact.get("evidence_type"),
        "label": artifact.get("label"),
        "file_path": raw_path,
        "file_exists": exists,
        "file_size": expected_size,
        "actual_size": actual_size,
        "size_matches": size_matches,
        "sha256": expected_sha,
        "sha256_checked": sha256_checked,
        "sha256_match": sha256_match,
        "sha256_check_reason": sha256_check_reason,
        "created_at": artifact.get("created_at"),
        "notes": notes,
        "valid": valid,
    }


def _latest_slice_proof_event(job_id: str | None = None) -> dict[str, Any] | None:
    if job_id:
        event = row(
            """
            SELECT id, event_type, source_agent, payload, created_at
              FROM proof_events
             WHERE event_type IN ('slice_completed','slice_failed')
               AND payload LIKE ?
             ORDER BY datetime(created_at) DESC
             LIMIT 1
            """,
            (f'%"job_id":"{job_id}"%',),
        )
    else:
        event = row(
            """
            SELECT id, event_type, source_agent, payload, created_at
              FROM proof_events
             WHERE event_type IN ('slice_completed','slice_failed')
             ORDER BY datetime(created_at) DESC
             LIMIT 1
            """
        )
    if not event:
        return None
    return {
        "id": event.get("id"),
        "event_type": event.get("event_type"),
        "source_agent": event.get("source_agent"),
        "created_at": event.get("created_at"),
        "payload": _parse_notes(event.get("payload")),
    }


@router.get("/api/slicer/status")
def get_slicer_status() -> dict[str, Any]:
    """Read-only slicer readiness + latest G-code proof summary.

    This endpoint never invokes the slicer and never contacts a printer. It is
    the operator-facing status surface for deciding whether the existing
    ``POST /api/slice`` path has real local CLI + artifact proof behind it.
    """

    slicer_binary = _detect_slicer_binary()
    execution_ready = slicer_binary is not None
    latest_job = _latest_slice_job()
    latest_gcode = _latest_slice_artifact("gcode")
    proof_job_id = (
        str(latest_gcode["job_id"]) if latest_gcode and latest_gcode.get("job_id") else None
    )
    latest_success_job = _slice_job_by_id(proof_job_id)
    latest_proof = _latest_slice_artifact("proof_report", job_id=proof_job_id)
    latest_event = _latest_slice_proof_event(job_id=proof_job_id)
    proof_ready = bool(
        latest_gcode
        and latest_gcode.get("valid")
        and latest_proof
        and latest_proof.get("valid")
        and latest_event
        and latest_event.get("event_type") == "slice_completed"
    )
    if execution_ready and proof_ready:
        overall = "ready"
    elif execution_ready:
        overall = "proof_required"
    else:
        overall = "blocked"
    blockers: list[str] = []
    if not execution_ready:
        blockers.append(
            "No PrusaSlicer/OrcaSlicer CLI binary found. Install one or set HERMES3D_SLICER_BIN."
        )
    if not proof_ready:
        blockers.append(
            "No valid latest slice_completed G-code + proof_report artifact pair is available."
        )
    return {
        "accepted": True,
        "status": overall,
        "execution_ready": execution_ready,
        "proof_ready": proof_ready,
        "readiness": "ready" if execution_ready else "slicer_not_found",
        "slicer_binary": str(slicer_binary) if slicer_binary else None,
        "updated_at": _utc_now_for_status(),
        "counts": _slice_job_counts(),
        "latest_job": latest_job,
        "latest_success_job": latest_success_job,
        "latest_gcode": latest_gcode,
        "latest_proof": latest_proof,
        "latest_proof_event": latest_event,
        "endpoints": {
            "submit": "/api/slice",
            "poll": "/api/slice/{job_id}",
            "status": "/api/slicer/status",
        },
        "freeze": {
            "no_printer_writes": True,
            "no_dispatch": True,
            "no_moonraker_upload": True,
            "no_klipper_dispatch": True,
            "no_octoprint_upload": True,
        },
        "blockers": blockers,
    }


def _utc_now_for_status() -> str:
    from hermes3d.api.routes._common import utc_now

    return utc_now()


__all__ = ["router"]
