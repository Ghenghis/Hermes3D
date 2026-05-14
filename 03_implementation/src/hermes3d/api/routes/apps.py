"""W6-7 (2026-05-09): /api/apps routes — extended app-registry surface.

This route group is the data-layer surface of the 60-app registry. It
exposes:

- ``GET  /api/apps``                          list all apps with the W6-7 fields
- ``GET  /api/apps/{app_id}``                 single app, full extended metadata
- ``POST /api/apps/{app_id}/run-proof``       run the seeded ``proof_command``
- ``POST /api/apps/{app_id}/rollback``        invoke the per-app rollback hook

The lane 5 (W6-8) GUI surface consumes these. The /api/modules
endpoints stay unchanged for backward compatibility — apps is the new
canonical surface.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, row, rows
from hermes3d.db.load_modules import load_modules
from hermes3d.services.app_proof_runner import run_proof_command
from hermes3d.services.app_proof_truth import classify_app_proof

router = APIRouter()

_ACCEPTED_BLOCKED_STATUS_BY_CAPABILITY = {
    "DESKTOP_PROOF_REQUIRED": "ACCEPTED_BLOCKED_DESKTOP",
    "RUNTIME_PROOF_REQUIRED": "ACCEPTED_BLOCKED_RUNTIME",
    "MODEL_RUNTIME_PROOF_REQUIRED": "MODEL_RUNTIME_ACCEPTED_BLOCKED",
}

# Lazy one-shot sync, mirrors modules.py._sync_registry_once.
_APPS_SYNCED = False


def _sync_apps_once() -> None:
    global _APPS_SYNCED
    if _APPS_SYNCED:
        return
    load_modules()
    _APPS_SYNCED = True


def _app_or_404(app_id: str) -> dict[str, Any]:
    _sync_apps_once()
    record = row("SELECT * FROM modules WHERE id = ?", (app_id,))
    if not record:
        raise HTTPException(status_code=404, detail="app not found")
    return record


def _decode_tested_versions(raw: Any) -> list[str]:
    if raw in (None, ""):
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def _truthful_status(record: dict[str, Any]) -> str:
    """Honest install status based on proof evidence, not just git-dir check."""
    install_state = record.get("install_state") or ""
    last_proof = record.get("last_proof_status")
    has_proof_cmd = bool((record.get("proof_command") or "").strip())
    proof_truth = classify_app_proof(record)
    proof_capability = proof_truth.get("proof_capability")

    if install_state not in ("installed", "source_available"):
        return "NOT_INSTALLED"
    if install_state == "source_available":
        return "SOURCE_AVAILABLE"
    # install_state == "installed"
    if last_proof == "pass":
        return "INSTALLED_PROVEN"
    if last_proof == "fail":
        return "FAILED_PROOF"
    if last_proof == "accepted_blocked":
        return _accepted_blocker_status(proof_capability)
    if not has_proof_cmd:
        if proof_truth.get("proof_blocker_accepted"):
            return _accepted_blocker_status(proof_capability)
        if proof_capability == "REFERENCE_ONLY":
            return "REFERENCE_ONLY"
        if proof_capability == "FIRMWARE_SOURCE_FROZEN":
            return "FIRMWARE_SOURCE_FROZEN"
        if proof_capability == "MODEL_RUNTIME_PROOF_REQUIRED":
            return "MODEL_RUNTIME_PROOF_REQUIRED"
        if proof_capability in {"DESKTOP_PROOF_REQUIRED", "RUNTIME_PROOF_REQUIRED"}:
            return "PROOF_REQUIRED"
        return "NO_PROOF_COMMAND"
    return "INSTALLED_UNPROVEN"


def _accepted_blocker_status(proof_capability: str | None) -> str:
    if proof_capability in _ACCEPTED_BLOCKED_STATUS_BY_CAPABILITY:
        return _ACCEPTED_BLOCKED_STATUS_BY_CAPABILITY[proof_capability]
    if proof_capability == "REFERENCE_ONLY":
        return "REFERENCE_ONLY"
    if proof_capability == "FIRMWARE_SOURCE_FROZEN":
        return "FIRMWARE_SOURCE_FROZEN"
    return "ACCEPTED_BLOCKED"


def _app_response(record: dict[str, Any]) -> dict[str, Any]:
    proof_truth = classify_app_proof(record)
    return {
        "id": record["id"],
        "display_name": record.get("display_name"),
        "section": record.get("section"),
        "priority": record.get("priority"),
        "license": record.get("license"),
        "license_spdx": record.get("license_spdx"),
        "repo_url": record.get("repo_url"),
        "local_path": record.get("local_path"),
        "install_state": record.get("install_state"),
        "install_progress": record.get("install_progress"),
        "detected_version": record.get("detected_version"),
        "health": record.get("health"),
        "launch_kind": record.get("launch_kind"),
        # W6-7 extension fields:
        "tested_versions": _decode_tested_versions(record.get("tested_versions")),
        "rollback_supported": bool(record.get("rollback_supported") or 0),
        "rollback_runbook_url": record.get("rollback_runbook_url"),
        "proof_command": record.get("proof_command"),
        "update_lane": record.get("update_lane") or "frozen",
        "last_proof_status": record.get("last_proof_status"),
        "last_proof_at": record.get("last_proof_at"),
        "last_sync_at": record.get("last_sync_at"),
        "updated_at": record.get("updated_at"),
        "truthful_status": _truthful_status(record),
        **proof_truth,
    }


def _proof_summary(apps: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    capability_counts: dict[str, int] = {}
    for app in apps:
        status = str(app.get("truthful_status") or "UNKNOWN")
        capability = str(app.get("proof_capability") or "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
        capability_counts[capability] = capability_counts.get(capability, 0) + 1
    accepted_blockers = [
        app
        for app in apps
        if bool(app.get("proof_blocker_accepted"))
        and app.get("truthful_status") != "INSTALLED_PROVEN"
    ]
    return {
        "truthful_status_counts": status_counts,
        "proof_capability_counts": capability_counts,
        "command_proof_count": capability_counts.get("COMMAND_PROOF", 0),
        "accepted_blocker_count": len(accepted_blockers),
        "accepted_blocker_ids": [str(app["id"]) for app in accepted_blockers],
        "generic_no_proof_count": sum(
            1
            for app in apps
            if app.get("truthful_status") in {"NO_PROOF_COMMAND", "PROOF_REQUIRED"}
            or app.get("proof_capability") == "PROOF_COMMAND_MISSING"
        ),
        "lm_studio_counts_for_modeling": False,
    }


@router.get("/api/apps")
def list_apps(
    section: str | None = None,
    update_lane: str | None = None,
) -> dict[str, Any]:
    """List all apps; optional filters on section and update_lane."""
    _sync_apps_once()
    sql = "SELECT * FROM modules WHERE (? IS NULL OR section = ?)"
    params: list[Any] = [section, section]
    if update_lane:
        sql += " AND update_lane = ?"
        params.append(update_lane)
    sql += " ORDER BY section, display_name"
    records = rows(sql, tuple(params))
    app_payloads = [_app_response(record) for record in records]
    return {
        "count": len(records),
        "filters": {"section": section, "update_lane": update_lane},
        "proof_summary": _proof_summary(app_payloads),
        "apps": app_payloads,
    }


@router.get("/api/apps/{app_id}")
def get_app(app_id: str) -> dict[str, Any]:
    return _app_response(_app_or_404(app_id))


class ProofRunRequest(BaseModel):
    actor: str = "operator"
    timeout_s: int | None = None


class ProofSweepRequest(BaseModel):
    actor: str = "operator"
    timeout_s: int | None = None
    app_ids: list[str] | None = None
    include_without_command: bool = False
    limit: int = 20


def _run_proof_for_record(record: dict[str, Any], *, timeout_s: int) -> dict[str, Any]:
    app_id = str(record["id"])
    proof_command = (record.get("proof_command") or "").strip()
    if not proof_command:
        proof_truth = classify_app_proof(record)
        blocker_accepted = bool(proof_truth.get("proof_blocker_accepted"))
        status = "accepted_blocked" if blocker_accepted else "not_set"
        execute(
            """
            UPDATE modules
               SET last_proof_status = ?,
                   last_proof_at = datetime('now'),
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (status, app_id),
        )
        return {
            "accepted": False,
            "status": status,
            "app_id": app_id,
            "reason": proof_truth["proof_gap_reason"] or "module has no proof_command configured",
            **proof_truth,
            "captured_output_redacted": "",
            "evidence_id": None,
        }

    result = run_proof_command(
        proof_command,
        timeout_s=timeout_s,
        cwd=_proof_cwd(record, proof_command),
    )
    execute(
        """
        UPDATE modules
           SET last_proof_status = ?,
               last_proof_at = datetime('now'),
               updated_at = datetime('now')
         WHERE id = ?
        """,
        (result["status"], app_id),
    )
    evidence_id = uuid.uuid4().hex
    captured = (
        f"$ {result['command']}\n"
        f"[exit_code={result['exit_code']} duration_ms={result['duration_ms']}]\n"
        f"--- stdout ---\n{result['stdout']}\n"
        f"--- stderr ---\n{result['stderr']}\n"
    )
    return {
        "accepted": bool(result["accepted"]),
        "status": result["status"],
        "app_id": app_id,
        "exit_code": result["exit_code"],
        "duration_ms": result["duration_ms"],
        "timed_out": bool(result["timed_out"]),
        "captured_output_redacted": captured,
        "evidence_id": evidence_id,
    }


def _proof_cwd(record: dict[str, Any], proof_command: str) -> str | None:
    if not proof_command.strip().startswith("git rev-parse "):
        return None
    local_path = str(record.get("local_path") or "").strip()
    if not local_path:
        return None
    path = Path(local_path)
    if path.exists() and path.is_dir():
        return str(path)
    return None


@router.post("/api/apps/run-proofs")
def run_app_proof_sweep(body: ProofSweepRequest | None = None) -> dict[str, Any]:
    """Run a bounded batch of app proof commands.

    This is intentionally operator-triggered and bounded. It does not
    auto-run on page load, does not touch printer hardware, and by default
    skips rows without ``proof_command`` so the operator can advance the
    60-app registry from "installed but unproven" to explicit pass/fail
    evidence without pretending every app is ready.
    """
    _sync_apps_once()
    request = body or ProofSweepRequest()
    timeout_s = request.timeout_s or 12
    limit = max(1, min(int(request.limit or 20), 60))
    selected_ids = [item.strip() for item in request.app_ids or [] if item.strip()]
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        records = rows(
            f"SELECT * FROM modules WHERE id IN ({placeholders}) ORDER BY section, display_name",
            tuple(selected_ids),
        )
    else:
        filter_sql = (
            ""
            if request.include_without_command
            else "WHERE proof_command IS NOT NULL AND trim(proof_command) != ''"
        )
        records = rows(
            f"SELECT * FROM modules {filter_sql} ORDER BY section, display_name LIMIT ?",
            (limit,),
        )
    records = records[:limit]

    results = [
        _run_proof_for_record(record, timeout_s=timeout_s)
        for record in records
        if request.include_without_command or (record.get("proof_command") or "").strip()
    ]
    summary = {
        "total": len(results),
        "pass": sum(1 for result in results if result["status"] == "pass"),
        "fail": sum(1 for result in results if result["status"] == "fail"),
        "timeout": sum(1 for result in results if result["status"] == "timeout"),
        "error": sum(1 for result in results if result["status"] == "error"),
        "not_set": sum(1 for result in results if result["status"] == "not_set"),
        "accepted_blocked": sum(1 for result in results if result["status"] == "accepted_blocked"),
    }
    proof_event_id = uuid.uuid4().hex
    execute(
        """
        INSERT INTO proof_events (id, event_type, source_agent, payload)
        VALUES (?, 'apps.proof_sweep.completed', ?, ?)
        """,
        (
            proof_event_id,
            request.actor,
            json.dumps(
                {
                    "summary": summary,
                    "app_ids": [result["app_id"] for result in results],
                    "timeout_s": timeout_s,
                    "include_without_command": request.include_without_command,
                },
                sort_keys=True,
            ),
        ),
    )
    return {
        "accepted": True,
        "status": "completed",
        "proof_event_id": proof_event_id,
        "summary": summary,
        "results": results,
    }


@router.post("/api/apps/{app_id}/run-proof")
def run_app_proof(app_id: str, body: ProofRunRequest | None = None) -> dict[str, Any]:
    """Run the seeded ``proof_command``.

    Persists the resulting status into ``modules.last_proof_status``
    and the timestamp into ``modules.last_proof_at`` so the GUI lane
    can render up-to-date proof state without re-running the command
    on every page load.
    """
    record = _app_or_404(app_id)
    timeout_s = (body.timeout_s if body else None) or 12
    return _run_proof_for_record(record, timeout_s=timeout_s)


@router.post("/api/source-os/modules/{app_id}/run-proof")
def run_source_os_module_proof(app_id: str, body: ProofRunRequest | None = None) -> dict[str, Any]:
    """W18-A13 — Source-OS alias of :func:`run_app_proof`.

    Matches the existing alias pattern (:func:`hermes3d.api.routes.modules.
    get_source_os_module` is an alias of :func:`get_module`). Audit
    W18-A3 flagged this path as ``FAIL_BACKEND_MISSING``: the
    ``appsClient`` singleton's primary URL is
    ``/api/source-os/modules/{id}/run-proof`` even though the canonical
    handler lives at ``/api/apps/{id}/run-proof``. Both paths now
    delegate to the same implementation so the FE behaves identically
    regardless of which it calls.
    """
    return run_app_proof(app_id, body)


class RollbackRequest(BaseModel):
    actor: str = "operator"
    target_version: str | None = None
    reason: str | None = None


@router.post("/api/apps/{app_id}/rollback")
def rollback_app(app_id: str, body: RollbackRequest | None = None) -> dict[str, Any]:
    """Per-app rollback hook.

    Default is a no-op + 501 ``Not Implemented`` for any app whose
    rollback_supported flag is False. The W6-7 surface intentionally
    does NOT execute git operations on its own; that work belongs to
    the existing /api/modules/{id}/rollback path. This route returns a
    "request accepted, dispatched to module rollback path" envelope so
    GUI lane 5 can route the user accordingly.
    """
    record = _app_or_404(app_id)
    if not record.get("rollback_supported"):
        raise HTTPException(
            status_code=501,
            detail={
                "status": "rollback_unsupported",
                "app_id": app_id,
                "reason": "rollback_supported=False on this app",
                "rollback_runbook_url": record.get("rollback_runbook_url"),
            },
        )
    return {
        "accepted": True,
        "status": "rollback_requested",
        "app_id": app_id,
        "target_version": (body.target_version if body else None),
        "reason": (body.reason if body else None),
        "rollback_runbook_url": record.get("rollback_runbook_url"),
        "next_route": f"/api/modules/{app_id}/rollback",
    }
