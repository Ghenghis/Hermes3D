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
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, row, rows
from hermes3d.db.load_modules import load_modules
from hermes3d.services.app_proof_runner import run_proof_command

router = APIRouter()

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

    if install_state not in ("installed", "source_available"):
        return "NOT_INSTALLED"
    if install_state == "source_available":
        return "SOURCE_AVAILABLE"
    # install_state == "installed"
    if last_proof == "pass":
        return "INSTALLED_PROVEN"
    if last_proof == "fail":
        return "FAILED_PROOF"
    if not has_proof_cmd:
        return "NO_PROOF_COMMAND"
    return "INSTALLED_UNPROVEN"


def _app_response(record: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "count": len(records),
        "filters": {"section": section, "update_lane": update_lane},
        "apps": [_app_response(record) for record in records],
    }


@router.get("/api/apps/{app_id}")
def get_app(app_id: str) -> dict[str, Any]:
    return _app_response(_app_or_404(app_id))


class ProofRunRequest(BaseModel):
    actor: str = "operator"
    timeout_s: int | None = None


@router.post("/api/apps/{app_id}/run-proof")
def run_app_proof(app_id: str, body: ProofRunRequest | None = None) -> dict[str, Any]:
    """Run the seeded ``proof_command``.

    Persists the resulting status into ``modules.last_proof_status``
    and the timestamp into ``modules.last_proof_at`` so the GUI lane
    can render up-to-date proof state without re-running the command
    on every page load.
    """
    record = _app_or_404(app_id)
    proof_command = (record.get("proof_command") or "").strip()
    timeout_s = (body.timeout_s if body else None) or 12
    if not proof_command:
        # No-op: don't run, but update state to "not_set" once so the
        # GUI can show a deterministic value.
        execute(
            """
            UPDATE modules
               SET last_proof_status = 'not_set',
                   last_proof_at = datetime('now'),
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (app_id,),
        )
        return {
            "accepted": False,
            "status": "not_set",
            "app_id": app_id,
            "reason": "module has no proof_command configured",
            "captured_output_redacted": "",
            "evidence_id": None,
        }
    result = run_proof_command(proof_command, timeout_s=timeout_s)
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
