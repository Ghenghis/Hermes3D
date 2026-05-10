from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows, utc_now
from hermes3d.api.routes.agents import _trusted_runtime_url
from hermes3d.db.init import DB_PATH
from hermes3d.services.agent_runtime import (
    chat_completions_url,
    env_value,
    runtime_probe,
    runtime_request_body,
)
from hermes3d.services.local_state import local_printers

router = APIRouter()

MUTATING_WORK_KINDS = {
    "build",
    "download",
    "install",
    "merge",
    "update",
    "code",
    "app_update",
    "printer_action",
}
OPEN_JOB_STATUSES = {"queued", "running", "printing", "waiting_approval", "paused"}
ACTIVE_PRINTER_STATUSES = {"printing", "active", "paused"}
SAFE_DECISIONS = {"keep", "remove"}
IDLE_AUTOMATION_CAPABILITIES = [
    {
        "kind": "research",
        "label": "Research reports",
        "agent_id": "research-agent",
        "queue_enabled": True,
        "requires_quiet_system": False,
        "requires_agent_runtime": True,
    },
    {
        "kind": "documentation",
        "label": "Documentation updates",
        "agent_id": "documentation-agent",
        "queue_enabled": True,
        "requires_quiet_system": True,
        "requires_agent_runtime": True,
    },
    {
        "kind": "workflow",
        "label": "Workflow improvements",
        "agent_id": "factory-operator",
        "queue_enabled": True,
        "requires_quiet_system": True,
        "requires_agent_runtime": True,
    },
    {
        "kind": "app_update",
        "label": "App updates",
        "agent_id": "factory-operator",
        "queue_enabled": True,
        "requires_quiet_system": True,
        "requires_agent_runtime": True,
    },
    {
        "kind": "printer_maintenance",
        "label": "Printer maintenance",
        "agent_id": "print-safety-agent",
        "queue_enabled": True,
        "requires_quiet_system": True,
        "requires_agent_runtime": True,
    },
]


class LearningConfigUpdate(BaseModel):
    enabled: bool | None = None
    idle_minutes: int | None = None


class IdleCandidateCreate(BaseModel):
    title: str
    summary: str
    kind: str = "research"
    agent_id: str = "research-agent"
    risk_level: str = "low"
    source: str = "operator"
    source_url: str | None = None
    target_tab: str | None = None
    target_files: list[str] = []
    branch_ref: str | None = None
    created_by: str = "operator"


class IdleCandidateDecision(BaseModel):
    decision: str
    actor: str = "operator"
    reason: str | None = None


class IdleCandidateRun(BaseModel):
    actor: str = "operator"
    notes: str | None = None


@router.get("/api/learning/config")
def get_config() -> dict:
    enabled = row("SELECT value FROM settings WHERE key = 'learning.enabled'")
    idle = row("SELECT value FROM settings WHERE key = 'learning.idle_minutes'")
    runner_ready, runner_reason = _runner_ready()
    enabled_value = (enabled or {}).get("value", "false") == "true"
    return {
        "enabled": enabled_value,
        "active": enabled_value and runner_ready,
        "idle_minutes": int((idle or {}).get("value", "30")),
        "reports_directory": str(DB_PATH.parent / "learning" / "reports"),
        "runner_status": "ready" if runner_ready else "not_configured",
        "reason": None if runner_ready else runner_reason,
    }


@router.put("/api/learning/config")
def put_config(body: LearningConfigUpdate) -> dict:
    if body.enabled is not None:
        execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('learning.enabled', ?, datetime('now'))",
            (str(body.enabled).lower(),),
        )
    if body.idle_minutes is not None:
        if body.idle_minutes < 1 or body.idle_minutes > 1440:
            raise HTTPException(status_code=400, detail="idle_minutes must be between 1 and 1440")
        execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('learning.idle_minutes', ?, datetime('now'))",
            (str(body.idle_minutes),),
        )
    return get_config()


@router.get("/api/learning/reports")
def reports() -> list[dict]:
    path = DB_PATH.parent / "learning" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return [
        {"filename": p.name, "path": str(p), "size_bytes": p.stat().st_size}
        for p in path.glob("*.md")
    ]


@router.get("/api/learning/reports/{filename}")
def report(filename: str) -> dict:
    path = DB_PATH.parent / "learning" / "reports" / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return {"filename": path.name, "content": path.read_text(encoding="utf-8")}


@router.get("/api/learning/idle-workbench")
def idle_workbench() -> dict:
    runner_ready, runner_reason = _runner_ready()
    blockers = _idle_blockers()
    return {
        "status": "ready",
        "review_policy": "Research may be queued while printers are busy. Build, download, install, update, merge, and printer actions stay blocked until printers/jobs/approvals are clear and proof gates exist.",
        "blockers": blockers,
        "candidates": _candidate_rows(),
        "daily_prompt": _daily_prompt(),
        "automation": _automation_readiness(runner_ready, runner_reason, blockers),
    }


@router.post("/api/learning/idle-workbench/candidates", status_code=201)
def create_idle_candidate(body: IdleCandidateCreate) -> dict:
    title = body.title.strip()
    summary = body.summary.strip()
    if not title:
        raise HTTPException(status_code=400, detail="candidate title is required")
    if not summary:
        raise HTTPException(status_code=400, detail="candidate summary is required")
    kind = _safe_token(body.kind, "research")
    risk_level = _safe_token(body.risk_level, "low")
    agent_id = _safe_token(body.agent_id, "research-agent")
    source = _safe_token(body.source, "operator")
    blockers = _idle_blockers()
    blocked_reason = _blocked_reason(kind, risk_level, blockers)
    status = "blocked" if _is_mutating(kind, risk_level) and blocked_reason else "queued"
    candidate_id = new_id()
    proof_event_id = _append_proof(
        "learning.idle_candidate.created",
        agent_id,
        {
            "candidate_id": candidate_id,
            "title": title,
            "kind": kind,
            "risk_level": risk_level,
            "status": status,
            "blocked_reason": blocked_reason,
            "target_tab": body.target_tab,
            "target_files": body.target_files,
        },
    )
    execute(
        """
        INSERT INTO idle_workbench_candidates
            (id, title, kind, agent_id, status, risk_level, summary, source, source_url,
             target_tab, target_files, branch_ref, gate_status, proof_event_ids,
             blocked_reason, created_by, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?, datetime('now'))
        """,
        (
            candidate_id,
            title,
            kind,
            agent_id,
            status,
            risk_level,
            summary,
            source,
            body.source_url,
            body.target_tab,
            json.dumps(body.target_files[:24], sort_keys=True),
            body.branch_ref,
            json.dumps([proof_event_id]),
            blocked_reason,
            body.created_by,
        ),
    )
    _record_idle_event(
        candidate_id,
        "created",
        body.created_by,
        {"status": status, "blocked_reason": blocked_reason},
        proof_event_id,
    )
    candidate = _candidate(candidate_id)
    return {
        "accepted": status != "blocked",
        "status": status,
        "reason": blocked_reason,
        "proof_event_id": proof_event_id,
        "candidate": candidate,
        "blockers": blockers,
    }


@router.post("/api/learning/idle-workbench/candidates/{candidate_id}/request-review")
def request_idle_review(candidate_id: str, body: IdleCandidateDecision | None = None) -> dict:
    candidate = _require_candidate(candidate_id)
    approval_id = candidate.get("approval_id") or new_id()
    actor = body.actor if body else "operator"
    execute(
        """
        INSERT OR IGNORE INTO approvals
            (id, approval_type, model_name, requesting_agent, status, notes)
        VALUES (?, 'IDLE_CANDIDATE_REVIEW', ?, ?, 'pending', ?)
        """,
        (
            approval_id,
            candidate["title"],
            candidate["agent_id"],
            as_json(
                {
                    "candidate_id": candidate_id,
                    "target_tab": candidate.get("target_tab"),
                    "branch_ref": candidate.get("branch_ref"),
                }
            ),
        ),
    )
    proof_event_id = _append_proof(
        "learning.idle_candidate.review_requested",
        actor,
        {"candidate_id": candidate_id, "approval_id": approval_id},
    )
    proof_ids = [*_json_list(candidate.get("proof_event_ids")), proof_event_id]
    execute(
        """
        UPDATE idle_workbench_candidates
        SET status = 'ready_for_review',
            approval_id = ?,
            proof_event_ids = ?,
            blocked_reason = NULL,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (approval_id, json.dumps(proof_ids), candidate_id),
    )
    _record_idle_event(
        candidate_id, "review_requested", actor, {"approval_id": approval_id}, proof_event_id
    )
    return {
        "accepted": True,
        "status": "ready_for_review",
        "approval_id": approval_id,
        "proof_event_id": proof_event_id,
        "candidate": _candidate(candidate_id),
    }


@router.post("/api/learning/idle-workbench/candidates/{candidate_id}/decision")
def decide_idle_candidate(candidate_id: str, body: IdleCandidateDecision) -> dict:
    candidate = _require_candidate(candidate_id)
    decision = _safe_token(body.decision, "")
    actor = _safe_token(body.actor, "operator")
    blockers = _idle_blockers()
    if decision == "merge":
        reason = _merge_block_reason(candidate, blockers)
        if reason:
            proof_event_id = _append_proof(
                "learning.idle_candidate.merge_blocked",
                actor,
                {"candidate_id": candidate_id, "reason": reason},
            )
            _record_idle_event(
                candidate_id, "merge_blocked", actor, {"reason": reason}, proof_event_id
            )
            raise HTTPException(
                status_code=409,
                detail={"status": "blocked", "reason": reason, "proof_event_id": proof_event_id},
            )
        next_status = "completed"
    elif decision in SAFE_DECISIONS:
        next_status = "approved" if decision == "keep" else "rejected"
    else:
        raise HTTPException(status_code=400, detail=f"unsupported decision: {body.decision}")
    proof_event_id = _append_proof(
        "learning.idle_candidate.decision",
        actor,
        {
            "candidate_id": candidate_id,
            "decision": decision,
            "status": next_status,
            "reason": body.reason,
        },
    )
    proof_ids = [*_json_list(candidate.get("proof_event_ids")), proof_event_id]
    execute(
        """
        UPDATE idle_workbench_candidates
        SET status = ?,
            proof_event_ids = ?,
            blocked_reason = NULL,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (next_status, json.dumps(proof_ids), candidate_id),
    )
    _record_idle_event(
        candidate_id,
        f"decision_{decision}",
        actor,
        {"status": next_status, "reason": body.reason},
        proof_event_id,
    )
    return {
        "accepted": True,
        "status": next_status,
        "decision": decision,
        "proof_event_id": proof_event_id,
        "candidate": _candidate(candidate_id),
    }


@router.post("/api/learning/idle-workbench/candidates/{candidate_id}/run")
def run_idle_candidate(candidate_id: str, body: IdleCandidateRun | None = None) -> dict:
    candidate = _require_candidate(candidate_id)
    actor = _safe_token(body.actor if body else "operator", "operator")
    blockers = _idle_blockers()
    missing = _run_missing_reasons(candidate, blockers)
    if missing:
        reason = " ".join(missing)
        proof_event_id = _append_proof(
            "learning.idle_candidate.run_blocked",
            actor,
            {
                "candidate_id": candidate_id,
                "kind": candidate.get("kind"),
                "missing": missing,
                "blockers": _blocker_refs(blockers),
            },
        )
        proof_ids = [*_json_list(candidate.get("proof_event_ids")), proof_event_id]
        execute(
            """
            UPDATE idle_workbench_candidates
            SET status = 'blocked',
                blocked_reason = ?,
                proof_event_ids = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (reason, json.dumps(proof_ids), candidate_id),
        )
        _record_idle_event(
            candidate_id,
            "run_blocked",
            actor,
            {"reason": reason, "missing": missing},
            proof_event_id,
        )
        return {
            "accepted": False,
            "status": "blocked",
            "reason": reason,
            "proof_event_id": proof_event_id,
            "candidate": _candidate(candidate_id),
            "blockers": blockers,
        }

    runtime_url = _trusted_runtime_url()
    assert runtime_url is not None
    try:
        output = _call_agent_runtime(runtime_url, candidate, body.notes if body else None)
    except RuntimeError as exc:
        reason = str(exc)
        proof_event_id = _append_proof(
            "learning.idle_candidate.run_failed",
            actor,
            {"candidate_id": candidate_id, "kind": candidate.get("kind"), "reason": reason},
        )
        _record_idle_event(candidate_id, "run_failed", actor, {"reason": reason}, proof_event_id)
        return {
            "accepted": False,
            "status": "runtime_error",
            "reason": reason,
            "proof_event_id": proof_event_id,
            "candidate": _candidate(candidate_id),
        }

    report = _write_run_report(candidate, output)
    artifact_id = new_id()
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, NULL, 'report', ?, 'AGENT_CHAT', NULL, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            candidate.get("agent_id") or "research-agent",
            report["filename"],
            report["path"],
            report["size_bytes"],
            as_json(
                {
                    "source": "idle_workbench_runner",
                    "candidate_id": candidate_id,
                    "sha256": report["sha256"],
                }
            ),
        ),
    )
    proof_event_id = _append_proof(
        "learning.idle_candidate.run_completed",
        actor,
        {
            "candidate_id": candidate_id,
            "kind": candidate.get("kind"),
            "agent_id": candidate.get("agent_id"),
            "report_path": report["path"],
            "report_sha256": report["sha256"],
            "artifact_id": artifact_id,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        },
    )
    proof_ids = [*_json_list(candidate.get("proof_event_ids")), proof_event_id]
    gate_status = {
        **_json_dict(candidate.get("gate_status")),
        "runner_completed": True,
        "report_artifact_id": artifact_id,
        "all_passed": False,
    }
    execute(
        """
        UPDATE idle_workbench_candidates
        SET status = 'ready_for_review',
            gate_status = ?,
            proof_event_ids = ?,
            blocked_reason = NULL,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (json.dumps(gate_status, sort_keys=True), json.dumps(proof_ids), candidate_id),
    )
    _record_idle_event(
        candidate_id,
        "run_completed",
        actor,
        {"artifact_id": artifact_id, "report": report},
        proof_event_id,
    )
    return {
        "accepted": True,
        "status": "ready_for_review",
        "proof_event_id": proof_event_id,
        "candidate": _candidate(candidate_id),
        "report": report,
        "artifact_id": artifact_id,
    }


def _runner_ready() -> tuple[bool, str]:
    if env_value("HERMES3D_LEARNING_RUNNER_ENABLED").strip() == "1":
        return True, ""
    return (
        False,
        "Idle learning runner is not configured; set HERMES3D_LEARNING_RUNNER_ENABLED=1 after installing the research/report worker.",
    )


def _agent_runtime_ready() -> tuple[bool, str]:
    probe = runtime_probe()
    if probe["ready"]:
        return True, ""
    return False, str(probe["reason"])


def _automation_readiness(
    runner_ready: bool, runner_reason: str, blockers: list[dict[str, Any]]
) -> dict[str, Any]:
    agent_ready, agent_reason = _agent_runtime_ready()
    capabilities: list[dict[str, Any]] = []
    blocker_labels = ", ".join(str(item.get("label") or item.get("id")) for item in blockers[:4])
    for capability in IDLE_AUTOMATION_CAPABILITIES:
        missing: list[str] = []
        if not runner_ready:
            missing.append(runner_reason)
        if capability["requires_agent_runtime"] and not agent_ready:
            missing.append(agent_reason)
        if capability["requires_quiet_system"] and blockers:
            missing.append(f"Live blockers must clear before execution: {blocker_labels}.")
        capabilities.append(
            {
                "kind": capability["kind"],
                "label": capability["label"],
                "agent_id": capability["agent_id"],
                "queue_enabled": capability["queue_enabled"],
                "execution_status": "ready" if not missing else "blocked",
                "missing": missing,
                "proof_required": True,
                "safety_scope": "queue-only until runtime, blockers, approvals, and proof gates are green"
                if missing
                else "runtime execution allowed after proof gate pass",
            }
        )
    return {
        "runner_status": "ready" if runner_ready else "not_configured",
        "runner_reason": None if runner_ready else runner_reason,
        "agent_runtime_status": "ready" if agent_ready else "not_configured",
        "agent_runtime_reason": None if agent_ready else agent_reason,
        "capabilities": capabilities,
    }


def _idle_blockers() -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for printer in local_printers():
        status = str(printer.get("status") or "").lower()
        if status in ACTIVE_PRINTER_STATUSES:
            blockers.append(
                {
                    "type": "printer",
                    "id": printer.get("id"),
                    "label": printer.get("name") or printer.get("id"),
                    "status": status,
                    "reason": "Printer is active; agent build/download/install/merge work stays blocked.",
                }
            )
        if printer.get("id") == "flsun_s1":
            blockers.append(
                {
                    "type": "policy",
                    "id": "flsun_s1",
                    "label": "FLSUN S1",
                    "status": "locked",
                    "reason": "S1 stays read-only: no movement, upload, test, or print.",
                }
            )
    for job in rows(
        "SELECT id, name, status FROM jobs WHERE status IN ('queued', 'running', 'printing', 'waiting_approval', 'paused') ORDER BY created_at DESC LIMIT 12"
    ):
        blockers.append(
            {
                "type": "job",
                "id": job.get("id"),
                "label": job.get("name") or job.get("id"),
                "status": job.get("status"),
                "reason": "Open job exists; risky idle work waits for a quiet system.",
            }
        )
    approval_count = (
        row("SELECT COUNT(*) AS count FROM approvals WHERE status = 'pending'") or {}
    ).get("count", 0)
    if approval_count:
        blockers.append(
            {
                "type": "approval",
                "id": "pending_approvals",
                "label": f"{approval_count} pending approval(s)",
                "status": "pending",
                "reason": "Pending approvals must be handled before merge/install decisions.",
            }
        )
    return blockers


def _run_missing_reasons(candidate: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    enabled = (row("SELECT value FROM settings WHERE key = 'learning.enabled'") or {}).get(
        "value", "false"
    ) == "true"
    if not enabled:
        missing.append("Idle Learning mode is disabled.")
    runner_ready, runner_reason = _runner_ready()
    if not runner_ready:
        missing.append(runner_reason)
    agent_ready, agent_reason = _agent_runtime_ready()
    if not agent_ready:
        missing.append(agent_reason)
    kind = str(candidate.get("kind") or "research")
    risk_level = str(candidate.get("risk_level") or "low")
    if _is_mutating(kind, risk_level) and blockers:
        labels = ", ".join(str(item.get("label") or item.get("id")) for item in blockers[:4])
        missing.append(f"Live blockers must clear before {kind} execution: {labels}.")
    return missing


def _blocker_refs(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": item.get("type"),
            "id": item.get("id"),
            "label": item.get("label"),
            "status": item.get("status"),
        }
        for item in blockers
    ]


def _call_agent_runtime(runtime_url: str, candidate: dict[str, Any], notes: str | None) -> str:
    agent_id = str(candidate.get("agent_id") or "research-agent")
    user = (
        f"Idle workbench candidate: {candidate.get('title')}\n"
        f"Kind: {candidate.get('kind')}\n"
        f"Risk: {candidate.get('risk_level')}\n"
        f"Target tab: {candidate.get('target_tab') or 'none'}\n"
        f"Summary: {candidate.get('summary')}\n"
        f"Operator notes: {notes or 'none'}\n\n"
        "Produce a concise, evidence-oriented Hermes3D operator report. Do not claim to install, merge, update, upload, move, or print. "
        "Return recommended next steps and proof gates that should pass before any mutation."
    )
    request_body = json.dumps(
        runtime_request_body(
            {
                "model": agent_id,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Hermes3D OS idle-workbench agent. Use real local data only when supplied. "
                            "If information is missing, name the missing setup. S1 at 192.168.0.12 is locked for printer actions. "
                            "This run may create a report only; it must not perform or imply external mutations."
                        ),
                    },
                    {"role": "user", "content": user},
                ],
            }
        ),
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(runtime_url),
        method="POST",
        data=request_body,
        headers={"Content-Type": "application/json", "User-Agent": "Hermes3D-IdleWorkbench/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Hermes Agent runtime rejected idle candidate run: HTTP {exc.code}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Hermes Agent runtime is unreachable for idle candidate run: {exc}"
        ) from exc
    content = _runtime_content(payload)
    if not content.strip():
        raise RuntimeError(
            "Hermes Agent runtime returned no report content for idle candidate run."
        )
    return content.strip()[:20000]


def _runtime_content(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if isinstance(choices, list):
        chunks: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                chunks.append(message["content"])
            text = choice.get("text")
            if isinstance(text, str):
                chunks.append(text)
        return "\n".join(chunks)
    if isinstance(payload.get("content"), str):
        return payload["content"]
    if isinstance(payload.get("text"), str):
        return payload["text"]
    return ""


def _write_run_report(candidate: dict[str, Any], output: str) -> dict[str, Any]:
    reports_dir = DB_PATH.parent / "learning" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_report_slug(str(candidate.get("title") or candidate.get("id") or "idle-run"))
    filename = f"{utc_now().replace(':', '').replace('-', '').replace('.', '')}_{slug}.md"
    path = reports_dir / filename
    content = (
        f"# Idle Workbench Report: {candidate.get('title')}\n\n"
        f"- Candidate: `{candidate.get('id')}`\n"
        f"- Kind: `{candidate.get('kind')}`\n"
        f"- Agent: `{candidate.get('agent_id')}`\n"
        f"- Created: `{utc_now()}`\n\n"
        "## Runtime Output\n\n"
        f"{output}\n"
    )
    path.write_text(content, encoding="utf-8")
    encoded = content.encode("utf-8")
    return {
        "filename": filename,
        "path": str(path),
        "size_bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _safe_report_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return (slug or "idle-run")[:80]


def _candidate_rows() -> list[dict[str, Any]]:
    return [
        _candidate_from_row(item)
        for item in rows(
            "SELECT * FROM idle_workbench_candidates ORDER BY updated_at DESC, created_at DESC LIMIT 50"
        )
    ]


def _candidate(candidate_id: str) -> dict[str, Any] | None:
    item = row("SELECT * FROM idle_workbench_candidates WHERE id = ?", (candidate_id,))
    return _candidate_from_row(item) if item else None


def _require_candidate(candidate_id: str) -> dict[str, Any]:
    candidate = _candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="idle workbench candidate not found")
    return candidate


def _candidate_from_row(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result["target_files"] = _json_list(result.get("target_files"))
    result["proof_event_ids"] = _json_list(result.get("proof_event_ids"))
    result["gate_status"] = _json_dict(result.get("gate_status"))
    return result


def _record_idle_event(
    candidate_id: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    proof_event_id: str | None = None,
) -> None:
    execute(
        """
        INSERT INTO idle_workbench_events
            (id, candidate_id, event_type, actor, payload, proof_event_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (new_id(), candidate_id, event_type, actor, as_json(payload), proof_event_id),
    )


def _append_proof(event_type: str, source_agent: str, payload: dict[str, Any]) -> str:
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (proof_event_id, event_type, source_agent, as_json({**payload, "ts_utc": utc_now()})),
    )
    return proof_event_id


def _daily_prompt() -> dict[str, Any]:
    latest = row("SELECT * FROM idle_workbench_candidates ORDER BY created_at DESC LIMIT 1")
    return {
        "question": "What should Hermes3D improve while the workstation is idle?",
        "last_candidate_at": latest.get("created_at") if latest else None,
        "suggested_kinds": [
            "research",
            "app_update",
            "printer_maintenance",
            "documentation",
            "workflow",
        ],
    }


def _blocked_reason(kind: str, risk_level: str, blockers: list[dict[str, Any]]) -> str | None:
    if not _is_mutating(kind, risk_level):
        if blockers:
            return "Research is queued; build/download/install/update/merge follow-up stays blocked until printers, jobs, and approvals are clear."
        return None
    if blockers:
        labels = ", ".join(str(item.get("label") or item.get("id")) for item in blockers[:4])
        return f"{kind} work is blocked while these live blockers exist: {labels}."
    return None


def _merge_block_reason(candidate: dict[str, Any], blockers: list[dict[str, Any]]) -> str | None:
    if blockers:
        labels = ", ".join(str(item.get("label") or item.get("id")) for item in blockers[:4])
        return f"Merge is blocked while these live blockers exist: {labels}."
    approval_id = candidate.get("approval_id")
    if not approval_id:
        return "Merge requires an IDLE_CANDIDATE_REVIEW approval."
    approval = row("SELECT status FROM approvals WHERE id = ?", (str(approval_id),))
    if not approval or approval.get("status") != "approved":
        return "Merge requires the linked review approval to be approved."
    gate_status = _json_dict(candidate.get("gate_status"))
    if gate_status.get("all_passed") is not True:
        return "Merge requires passing proof gates recorded on the candidate."
    return None


def _is_mutating(kind: str, risk_level: str) -> bool:
    return kind in MUTATING_WORK_KINDS or risk_level in {"medium", "high", "critical"}


def _safe_token(value: str | None, fallback: str) -> str:
    token = (value or fallback).strip().lower().replace(" ", "_").replace("-", "_")
    return "".join(ch for ch in token if ch.isalnum() or ch in {"_", "."})[:64] or fallback


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
