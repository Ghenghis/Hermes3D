from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows, utc_now
from hermes3d.db.init import DB_PATH
from hermes3d.services.agent_runtime import (
    chat_completions_url,
    configured_runtime_model,
    runtime_probe,
    runtime_request_body,
    trusted_runtime_url,
)

router = APIRouter()
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
UI_ROOT = IMPLEMENTATION_ROOT / "ui"
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"
SOURCE_COMPLETION_PATH = PROOF_DIR / "SOURCE_APP_60_COMPLETION_AUDIT.json"
SOURCE_CLI_READINESS_PATH = PROOF_DIR / "SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json"
SOURCE_CLI_SURFACE_PATH = PROOF_DIR / "SOURCE_APP_CLI_SURFACE_AUDIT.json"
ACTION_CONTRACT_CACHE_TTL_S = 60.0  # W18-A25: bumped 8s→60s; cold call did 4 sequential
# probes (mcp_locks, provider_team_readiness, agent_e2e_readiness, code_cli_runners)
# whose underlying subprocesses (docker version 5s, docker image inspect 8s,
# opencode --version 8s, openhands version 8s) summed to ~41s wall time on a
# verified operator-local replay. 60s warm cache holds for the GUI 10s poll
# loop and keeps stale-config drift bounded; first cold call still does the
# real probes so a new docker/cli install is detected the next minute.
_ACTION_CONTRACT_CACHE: dict[str, Any] = {"ts": 0.0, "contracts": None}

# W18-A25: separate cache for /api/agents/tasks proof_events scan so the
# 10s GUI poll does not re-query SQLite on every tick when nothing has
# changed. 10s TTL matches the panel's planned refresh cadence.
_AGENT_TASKS_CACHE_TTL_S = 10.0
_AGENT_TASKS_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}

PERSONAS = [
    "factory-operator",
    "modeling-agent",
    "print-safety-agent",
    "mesh-go-agent",
    "mesh-repair-agent",
    "oliver-qa-agent",
    "print-monitor-agent",
    "privacy-agent",
]

MAX_ATTACHMENT_BYTES = 512 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".stl",
    ".3mf",
    ".obj",
    ".amf",
    ".ply",
    ".glb",
    ".gltf",
    ".fbx",
    ".dae",
    ".off",
    ".mesh",
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".scad",
    ".blend",
    ".gcode",
    ".gco",
    ".nc",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".csv",
    ".log",
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".py",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".zip",
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
    ".flac",
}
FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]")
SECRET_RE = re.compile(
    r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|([A-Za-z0-9_]*KEY=)[^\s]+"
)


class ChatRequest(BaseModel):
    message: str
    context: dict = Field(default_factory=dict)


class AgentConfigUpdate(BaseModel):
    config: dict = Field(default_factory=dict)


class AgentActionRequest(BaseModel):
    reason: str | None = None
    payload: dict = Field(default_factory=dict)


class AgentPlaywrightRunRequest(BaseModel):
    scope: str = "observe"
    reason: str | None = None


@router.get("/api/agents")
def list_agents() -> list[dict]:
    runtime_configured = _trusted_runtime_url() is not None
    status = "idle" if runtime_configured else "paused"
    model_provider = "local_llm_runtime" if runtime_configured else "not_configured"
    return [
        {
            "id": persona,
            "name": persona.replace("-", " ").title(),
            "status": status,
            "model_provider": model_provider,
        }
        for persona in PERSONAS
    ]


async def _chat_stream(persona_id: str, body: ChatRequest) -> AsyncIterator[str]:
    _require_persona(persona_id)
    message_id = new_id()
    execute(
        "INSERT INTO agent_conversations (id, persona_id, role, content) VALUES (?, ?, 'user', ?)",
        (message_id, persona_id, body.message),
    )
    attachments = _attachment_context(body.context)
    if attachments:
        attachment_lines = "\n".join(
            f"- {item['label']} ({item['file_size']} bytes, artifact {item['id']}, sha256 {_artifact_sha256(item)})"
            for item in attachments
        )
        execute(
            """
            INSERT INTO agent_conversations
                (id, persona_id, role, message_type, content)
            VALUES (?, ?, 'system', 'ATTACHMENT_CONTEXT', ?)
            """,
            (
                new_id(),
                persona_id,
                f"User attached {len(attachments)} local artifact(s):\n{attachment_lines}",
            ),
        )
    runtime_url = _trusted_runtime_url()
    if runtime_url:
        async for frame in _runtime_chat_stream(runtime_url, persona_id, body, attachments):
            yield frame
        return
    reply = {
        "id": new_id(),
        "persona_id": persona_id,
        "role": "assistant",
        "message_type": "STATUS_UPDATE",
        "content": "Message received. Live Hermes agent runtime is not configured yet.",
        "created_at": utc_now(),
    }
    execute(
        """
        INSERT INTO agent_conversations
            (id, persona_id, role, message_type, content)
        VALUES (?, ?, ?, ?, ?)
        """,
        (reply["id"], persona_id, reply["role"], reply["message_type"], reply["content"]),
    )
    yield f"data: {json.dumps(reply)}\n\n"


async def _runtime_chat_stream(
    runtime_url: str, persona_id: str, body: ChatRequest, attachments: list[dict]
) -> AsyncIterator[str]:
    session_id = new_id()
    runtime_model = configured_runtime_model(fallback=persona_id)
    request_body = json.dumps(
        runtime_request_body(
            {
                "model": persona_id,
                "stream": True,
                "messages": _runtime_messages(persona_id, body, attachments),
            }
        ),
        separators=(",", ":"),
    ).encode("utf-8")
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            new_id(),
            "hermes_agent_chat_runtime_request",
            persona_id,
            as_json(
                {
                    "session_id": session_id,
                    "message_sha256": hashlib.sha256(body.message.encode("utf-8")).hexdigest(),
                    "attachment_ids": [item["id"] for item in attachments],
                    "runtime_configured": True,
                    "requested_model": persona_id,
                    "resolved_model": runtime_model,
                    "active_surface": body.context.get("active_surface")
                    if isinstance(body.context, dict)
                    else None,
                }
            ),
        ),
    )
    request = urllib.request.Request(
        chat_completions_url(runtime_url),
        method="POST",
        data=request_body,
        headers={"Content-Type": "application/json", "User-Agent": "Hermes3D-Agent-Chat/1.0"},
    )
    assistant_content = ""
    try:
        upstream = await asyncio.to_thread(urllib.request.urlopen, request, timeout=120)
        try:
            while True:
                chunk = await asyncio.to_thread(upstream.readline)
                if not chunk:
                    break
                frame = chunk.decode("utf-8", errors="replace")
                assistant_content += _openai_sse_content(frame)
                yield frame
        finally:
            upstream.close()
    except urllib.error.HTTPError as exc:
        detail = _redact(exc.read().decode("utf-8", errors="replace"))[:500]
        yield _blocked_runtime_reply(
            persona_id,
            f"Configured Hermes Agent runtime rejected chat request: HTTP {exc.code}: {detail}",
        )
        return
    except Exception as exc:
        yield _blocked_runtime_reply(
            persona_id, f"Configured Hermes Agent runtime is unreachable: {_redact(str(exc))[:500]}"
        )
        return
    if assistant_content.strip():
        execute(
            """
            INSERT INTO agent_conversations
                (id, persona_id, role, message_type, content)
            VALUES (?, ?, 'assistant', 'RUNTIME_STREAM', ?)
            """,
            (session_id, persona_id, assistant_content.strip()),
        )


def _runtime_messages(persona_id: str, body: ChatRequest, attachments: list[dict]) -> list[dict]:
    active_surface = body.context.get("active_surface") if isinstance(body.context, dict) else None
    attachment_lines = [
        f"- {item['label']} | artifact {item['id']} | bytes {item['file_size']} | sha256 {_artifact_sha256(item)} | path {item['file_path']}"
        for item in attachments
    ]
    system = (
        f"You are the Hermes3D OS {persona_id} persona. Use real local data, source files, printer state, and proof gates. "
        "If a requested tool, printer, model, file, or runtime is unavailable, say it is blocked and name the proof or missing setup. "
        "S1 at 192.168.0.12 is locked for printer actions: no movement, no upload, no test, no print. "
        f"Active GUI surface: {active_surface or 'unknown'}."
    )
    if attachment_lines:
        system += "\nLocal Hermes3D attachments available to inspect:\n" + "\n".join(
            attachment_lines
        )
    message = (
        body.message.strip()
        or "User attached Hermes3D artifact(s). Inspect the attached context and recommend the safest real next action."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": message}]


def _blocked_runtime_reply(persona_id: str, content: str) -> str:
    reply = {
        "id": new_id(),
        "persona_id": persona_id,
        "role": "assistant",
        "message_type": "RUNTIME_BLOCKED",
        "content": content,
        "created_at": utc_now(),
    }
    execute(
        """
        INSERT INTO agent_conversations
            (id, persona_id, role, message_type, content)
        VALUES (?, ?, ?, ?, ?)
        """,
        (reply["id"], persona_id, reply["role"], reply["message_type"], reply["content"]),
    )
    return f"data: {json.dumps(reply)}\n\n"


def _openai_sse_content(frame: str) -> str:
    content = ""
    for line in frame.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[6:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list):
            continue
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            message = choice.get("message")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                content += delta["content"]
            elif isinstance(message, dict) and isinstance(message.get("content"), str):
                content += message["content"]
    return content


def _redact(value: str) -> str:
    return SECRET_RE.sub(
        lambda match: f"{match.group(1) or match.group(2) or match.group(3) or ''}[REDACTED]", value
    )


@router.post("/api/agents/{persona_id}/chat")
async def chat(persona_id: str, body: ChatRequest) -> StreamingResponse:
    return StreamingResponse(_chat_stream(persona_id, body), media_type="text/event-stream")


@router.post("/api/agents/{persona_id}/attachments", status_code=201)
async def upload_attachment(persona_id: str, request: Request) -> dict:
    _require_persona(persona_id)
    filename = _safe_filename(
        request.query_params.get("filename") or request.headers.get("x-hermes-filename") or ""
    )
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "status": "blocked",
                "reason": f"Unsupported Hermes3D agent attachment type: {extension or 'none'}",
                "allowed": sorted(ALLOWED_ATTACHMENT_EXTENSIONS),
            },
        )
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="attachment body is empty")
    if len(body) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=413, detail=f"attachment exceeds {MAX_ATTACHMENT_BYTES} bytes"
        )
    artifact_id = new_id()
    digest = hashlib.sha256(body).hexdigest()
    storage = DB_PATH.parent / "agent_uploads" / persona_id
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / f"{artifact_id}_{filename}"
    target.write_bytes(body)
    content_type = request.headers.get("content-type") or "application/octet-stream"
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, NULL, 'agent_attachment', ?, 'AGENT_CHAT', NULL, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            persona_id,
            filename,
            str(target),
            len(body),
            json.dumps(
                {"content_type": content_type, "sha256": digest, "source": "hermes_agent_chat"},
                sort_keys=True,
            ),
        ),
    )
    execute(
        """
        INSERT INTO agent_conversations
            (id, persona_id, role, message_type, content)
        VALUES (?, ?, 'system', 'ATTACHMENT_UPLOADED', ?)
        """,
        (
            new_id(),
            persona_id,
            f"Attachment uploaded: {filename} ({len(body)} bytes, artifact {artifact_id})",
        ),
    )
    artifact = row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
    return {"uploaded": True, "artifact": artifact}


@router.get("/api/agents/{persona_id}/history")
def history(persona_id: str) -> list[dict]:
    _require_persona(persona_id)
    return rows(
        "SELECT * FROM agent_conversations WHERE persona_id = ? ORDER BY created_at",
        (persona_id,),
    )


@router.delete("/api/agents/{persona_id}/history")
def clear_history(persona_id: str) -> dict:
    _require_persona(persona_id)
    execute("DELETE FROM agent_conversations WHERE persona_id = ?", (persona_id,))
    return {"persona_id": persona_id, "deleted": True}


@router.post("/api/agents/{persona_id}/confirm-action/{action_id}")
def confirm_action(persona_id: str, action_id: str) -> dict:
    action = _pending_action(persona_id, action_id)
    execute(
        "UPDATE agent_autonomous_actions SET outcome = ? WHERE id = ?", ("confirmed", action_id)
    )
    return {
        "persona_id": persona_id,
        "action_id": action_id,
        "decision": "confirmed",
        "recorded": True,
        "session_id": action["session_id"],
    }


@router.post("/api/agents/{persona_id}/deny-action/{action_id}")
def deny_action(persona_id: str, action_id: str) -> dict:
    action = _pending_action(persona_id, action_id)
    execute(
        "UPDATE agent_autonomous_actions SET outcome = ?, veto_reason = COALESCE(veto_reason, ?) WHERE id = ?",
        ("denied", "Denied by operator", action_id),
    )
    return {
        "persona_id": persona_id,
        "action_id": action_id,
        "decision": "denied",
        "recorded": True,
        "session_id": action["session_id"],
    }


@router.post("/api/agents/{persona_id}/actions/{action_id}")
def persona_action(persona_id: str, action_id: str, body: AgentActionRequest | None = None) -> dict:
    _require_persona(persona_id)
    return _run_catalog_action(action_id, persona_id, body)


@router.post("/api/agents/{persona_id}/playwright-run")
def playwright_run(persona_id: str, body: AgentPlaywrightRunRequest | None = None) -> dict:
    _require_persona(persona_id)
    requested_scope = (body.scope if body else "observe").strip().lower()
    command = _playwright_command(requested_scope)
    if command is None:
        proof_event_id = _append_agent_proof(
            "hermes_agent.playwright_run.blocked",
            persona_id,
            {
                "status": "blocked",
                "reason": "unsupported_scope",
                "requested_scope": requested_scope,
                "allowed_scopes": sorted(_playwright_scopes()),
            },
        )
        return {
            "accepted": False,
            "status": "blocked",
            "reason": "Unsupported Playwright proof scope. Use observe, smoke, or full.",
            "proof_event_id": proof_event_id,
        }
    if not (UI_ROOT / "package.json").exists():
        proof_event_id = _append_agent_proof(
            "hermes_agent.playwright_run.blocked",
            persona_id,
            {"status": "blocked", "reason": "ui_package_missing", "ui_root": str(UI_ROOT)},
        )
        return {
            "accepted": False,
            "status": "blocked",
            "reason": f"Hermes3D UI package.json was not found at {UI_ROOT}.",
            "proof_event_id": proof_event_id,
        }
    started = time.perf_counter()
    started_at = utc_now()
    timeout_s = 900 if requested_scope == "full" else 240
    try:
        completed = subprocess.run(
            command,
            cwd=UI_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=False,
        )
        duration_ms = round((time.perf_counter() - started) * 1000)
        status = "pass" if completed.returncode == 0 else "fail"
        artifact_id = _store_playwright_artifact(
            persona_id,
            requested_scope,
            status,
            started_at,
            duration_ms,
            completed.returncode,
            command,
            completed.stdout,
            completed.stderr,
        )
        proof_event_id = _append_agent_proof(
            f"hermes_agent.playwright_run.{status}",
            persona_id,
            {
                "status": status,
                "scope": requested_scope,
                "exit_code": completed.returncode,
                "duration_ms": duration_ms,
                "artifact_id": artifact_id,
                "reason": body.reason if body else None,
            },
        )
        return {
            "accepted": True,
            "status": status,
            "scope": requested_scope,
            "exit_code": completed.returncode,
            "duration_ms": duration_ms,
            "artifact_id": artifact_id,
            "proof_event_id": proof_event_id,
            "command_label": _command_label(command),
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000)
        artifact_id = _store_playwright_artifact(
            persona_id,
            requested_scope,
            "timeout",
            started_at,
            duration_ms,
            None,
            command,
            exc.stdout if isinstance(exc.stdout, str) else "",
            exc.stderr if isinstance(exc.stderr, str) else "",
        )
        proof_event_id = _append_agent_proof(
            "hermes_agent.playwright_run.timeout",
            persona_id,
            {
                "status": "timeout",
                "scope": requested_scope,
                "timeout_s": timeout_s,
                "duration_ms": duration_ms,
                "artifact_id": artifact_id,
            },
        )
        return {
            "accepted": False,
            "status": "timeout",
            "scope": requested_scope,
            "reason": f"Playwright proof exceeded {timeout_s} seconds.",
            "artifact_id": artifact_id,
            "proof_event_id": proof_event_id,
            "command_label": _command_label(command),
        }
    except OSError as exc:
        proof_event_id = _append_agent_proof(
            "hermes_agent.playwright_run.blocked",
            persona_id,
            {"status": "blocked", "scope": requested_scope, "reason": _redact(str(exc))[:500]},
        )
        return {
            "accepted": False,
            "status": "blocked",
            "scope": requested_scope,
            "reason": f"Playwright runner could not start: {_redact(str(exc))[:300]}",
            "proof_event_id": proof_event_id,
            "command_label": _command_label(command),
        }


@router.post("/api/agents/actions/{action_id}")
def fleet_action(action_id: str, body: AgentActionRequest | None = None) -> dict:
    return _run_catalog_action(action_id, "hermes-agent", body)


def action_catalog() -> dict:
    """Return the action catalog payload.  Unit-testable with no HTTP context."""
    contracts = _agent_action_contracts()
    counts = Counter(contract["status"] for contract in contracts)
    public_contracts = [_public_action_contract(contract) for contract in contracts]
    return {
        "status": "in_progress"
        if counts.get("blocked", 0) or counts.get("partial", 0)
        else "ready",
        "summary": "Hermes Agents can use any Hermes3D OS feature only after that feature has a cataloged backend action, safety policy, proof event, and ready/blocked state.",
        "contract_version": "agent-operator-contract-v1",
        "counts": dict(sorted(counts.items())),
        "total": len(contracts),
        "ready_now": [contract["id"] for contract in contracts if contract["status"] == "ready"],
        "blocked_or_partial": [
            contract["id"] for contract in contracts if contract["status"] != "ready"
        ],
        "contracts": public_contracts,
    }


@router.get("/api/agents/action-catalog")
def _action_catalog_route(response: Response) -> dict:
    # W18-A25: 60s Cache-Control so well-behaved GUI/proxy callers can avoid a
    # re-fetch storm; the backend's own _ACTION_CONTRACT_CACHE TTL is 60s so
    # this stays consistent with what the server will actually return.
    response.headers["Cache-Control"] = "max-age=60"
    return action_catalog()


# W18-A25: alias for callers that use the plural/slashed form.
# Operator-verified that some GUI callers had a 405 on
# ``GET /api/agents/actions/catalog`` because ``/api/agents/actions/{action_id}``
# is registered as POST only. We register the plural form as a *separate* GET
# that returns the exact same payload as the canonical singular form. We do
# not 308-redirect because:
#   1) browsers retain the POST method on 307/308 only for the same method,
#      and a 308 from GET to GET is correct, but adapters/tests sometimes
#      treat a redirect as failure; returning the body directly is simpler.
#   2) anything that already mounted Cache-Control on the canonical path will
#      still see it because the same response object is mutated.
@router.get("/api/agents/actions/catalog")
def action_catalog_alias(response: Response) -> dict:
    response.headers["Cache-Control"] = "max-age=60"
    return action_catalog()


# W18-A25 — GUI-friendly active code-team / provider-smoke task feed.
#
# Operator verified locally that the #agents GUI showed
# "0 active · 0 tasks · 0/8 roster" because there was no endpoint
# returning the live team-task work the providers had just done.
# This endpoint scans ``proof_events`` for the executed/blocked/failed
# Hermes-agent catalog actions whose ``action_id`` matches the
# ``code.teams.*`` or ``code.providers.smoke`` patterns and returns the
# last 50 within the last 7 days plus an ``active_count``.
#
# Important constraints:
#   - No printer-control endpoints touched.
#   - No mocks: rows come from real proof_events written by
#     ``_run_catalog_action`` (which calls ``_append_agent_proof``).
#   - Secrets stay redacted because we read only the structured fields we
#     wrote ourselves; provider/team/title/task_id are already user
#     bounded text validated upstream.
_AGENT_TASK_EVENT_TYPES: tuple[str, ...] = (
    "hermes_agent.action.executed",
    "hermes_agent.action.blocked",
    "hermes_agent.action.failed",
)
_AGENT_TASK_ACTION_PREFIXES: tuple[str, ...] = (
    "code.teams.",
    "code.providers.smoke",
    "code.e2e.",
)
_AGENT_TASK_STATUS_MAP: dict[str, str] = {
    "hermes_agent.action.executed": "completed",
    "hermes_agent.action.blocked": "blocked",
    "hermes_agent.action.failed": "failed",
}
# Active = anything still in flight from the GUI's point of view.
# We keep "completed" out of active because the work has produced its
# evidence and is now "recent" — but the panel still shows it.
_AGENT_TASK_ACTIVE_STATUSES: frozenset[str] = frozenset(
    {
        "claimed",
        "coding_plan_recorded",
        "review_recorded",
        "assigned",
        "in_progress",
    }
)


def _agent_task_kind_for(action_id: str) -> str:
    """Map action_id to the GUI task ``kind`` enum."""
    if action_id.startswith("code.teams.") or action_id.startswith("code.e2e."):
        return "code_team"
    if action_id == "code.providers.smoke":
        return "code_provider_smoke"
    return "code_action"


def _agent_task_title_from(payload: dict[str, Any], action_id: str) -> str:
    raw = (
        payload.get("title")
        or payload.get("requested_reason")
        or payload.get("reason")
        or action_id
    )
    text = str(raw).strip()
    return text[:200] if text else action_id


def _agent_task_status_from(payload: dict[str, Any], event_type: str) -> str:
    # Prefer the enriched result_status (set by _run_catalog_action when the
    # downstream handler returned ``status``); fall back to the event type.
    explicit = payload.get("result_status") or payload.get("status")
    if explicit:
        return str(explicit).strip()
    return _AGENT_TASK_STATUS_MAP.get(event_type, event_type)


@router.get("/api/agents/tasks")
def agent_tasks(response: Response, limit: int = 50) -> dict[str, Any]:
    """Recent Hermes code-team / provider-smoke / E2E tasks for the #agents tab.

    Reads from the local ``proof_events`` SQLite table (NOT the MCP evidence
    ledger — that data is on a different store) where ``event_type`` is one of
    the catalog-action events and the payload's ``action_id`` matches a
    ``code.teams.*`` / ``code.providers.smoke`` / ``code.e2e.*`` prefix.

    Window: 7 days. Default limit: 50. Hard upper bound: 200.
    """
    safe_limit = max(1, min(int(limit or 50), 200))
    now_mono = time.monotonic()
    cached = _AGENT_TASKS_CACHE.get("payload")
    cached_at = float(_AGENT_TASKS_CACHE.get("ts") or 0.0)
    cached_limit = int(_AGENT_TASKS_CACHE.get("limit") or 0)
    if (
        isinstance(cached, dict)
        and cached_limit == safe_limit
        and (now_mono - cached_at) < _AGENT_TASKS_CACHE_TTL_S
    ):
        response.headers["Cache-Control"] = "max-age=10"
        response.headers["X-Hermes-Cache"] = "hit"
        return cached

    # Use SQLite's strftime to filter to the last 7 days. ``created_at`` is
    # stored as a ``datetime('now')`` UTC string, so a lexicographic compare
    # against ``datetime('now', '-7 days')`` is correct.
    placeholders = ",".join("?" for _ in _AGENT_TASK_EVENT_TYPES)
    records = rows(
        f"""
        SELECT id, event_type, source_agent, payload, created_at
        FROM proof_events
        WHERE event_type IN ({placeholders})
          AND created_at >= datetime('now', '-7 days')
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (*_AGENT_TASK_EVENT_TYPES, safe_limit * 4),  # over-fetch then filter
    )

    tasks: list[dict[str, Any]] = []
    provider_latest: dict[str, dict[str, Any]] = {}
    for record in records:
        raw_payload = record.get("payload") or "{}"
        try:
            payload = (
                json.loads(raw_payload) if isinstance(raw_payload, str) else (raw_payload or {})
            )
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            continue
        action_id = str(payload.get("action_id") or "").strip()
        if not action_id:
            continue
        if not any(action_id.startswith(prefix) for prefix in _AGENT_TASK_ACTION_PREFIXES):
            continue
        kind = _agent_task_kind_for(action_id)
        status = _agent_task_status_from(payload, str(record["event_type"]))
        task_id = str(payload.get("task_id") or "").strip() or None
        team_id = str(payload.get("team_id") or "").strip() or None
        provider_id = str(payload.get("provider_id") or "").strip() or None
        # Pull provider_id from the action_id for the smoke action when
        # not otherwise present.
        if not provider_id and action_id == "code.providers.smoke":
            provider_id = str(payload.get("requested_provider_id") or "") or None
        title = _agent_task_title_from(payload, action_id)
        entry: dict[str, Any] = {
            "task_id": task_id,
            "team_id": team_id,
            "provider_id": provider_id,
            "title": title,
            "kind": kind,
            "action_id": action_id,
            "status": status,
            "event_type": record["event_type"],
            "created_utc": record["created_at"],
            "evidence_id": record["id"],
            "source_agent": record["source_agent"],
        }
        tasks.append(entry)
        if (
            action_id == "code.providers.smoke"
            and provider_id
            and provider_id not in provider_latest
        ):
            provider_latest[provider_id] = {
                "provider_id": provider_id,
                "status": status,
                "task_id": task_id,
                "created_utc": record["created_at"],
                "evidence_id": record["id"],
            }
        if len(tasks) >= safe_limit:
            break

    active_count = sum(1 for task in tasks if str(task["status"]) in _AGENT_TASK_ACTIVE_STATUSES)
    payload = {
        "tasks": tasks,
        "active_count": active_count,
        "total_count": len(tasks),
        "limit": safe_limit,
        "window_days": 7,
        "provider_smoke_latest": list(provider_latest.values()),
        "schema_version": "agent-tasks-v1",
    }
    _AGENT_TASKS_CACHE["payload"] = payload
    _AGENT_TASKS_CACHE["ts"] = now_mono
    _AGENT_TASKS_CACHE["limit"] = safe_limit
    response.headers["Cache-Control"] = "max-age=10"
    response.headers["X-Hermes-Cache"] = "miss"
    return payload


def _agent_task_fields(
    action_id: str,
    request_payload: dict[str, Any] | None,
    result: Any = None,
) -> dict[str, Any]:
    """W18-A25: extract task_id / team_id / provider_id / title from
    catalog-action request/result so they survive in the proof_events row
    in cleartext.

    The /api/agents/tasks endpoint reads only what we put here — no secrets
    pass through because the upstream code_history validators bound these
    values (task_id, team_id, title) before they ever reach this layer.
    """
    extracted: dict[str, Any] = {}
    request_payload = request_payload or {}
    # Pull from the request payload first (operator's intent).
    for key in ("task_id", "team_id", "provider_id", "title"):
        value = request_payload.get(key)
        if isinstance(value, str) and value.strip():
            extracted[key] = value.strip()[:200]
    # The smoke action carries provider_id in its top-level payload.
    if action_id == "code.providers.smoke" and "provider_id" not in extracted:
        provider = request_payload.get("provider_id") or request_payload.get("provider")
        if isinstance(provider, str) and provider.strip():
            extracted["provider_id"] = provider.strip()[:60]
    # Backfill from result if upstream service echoes them (assign_provider_team_task does).
    if isinstance(result, dict):
        for key in ("task_id", "team_id", "provider_id", "title"):
            if key in extracted:
                continue
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                extracted[key] = value.strip()[:200]
        # Provider smoke result has the provider id under provider.id.
        if "provider_id" not in extracted:
            nested = result.get("provider")
            if isinstance(nested, dict):
                value = nested.get("id")
                if isinstance(value, str) and value.strip():
                    extracted["provider_id"] = value.strip()[:60]
    return extracted


def _run_catalog_action(action_id: str, actor: str, body: AgentActionRequest | None = None) -> dict:
    contracts = {contract["id"]: contract for contract in _agent_action_contracts()}
    contract = contracts.get(action_id)
    requested_reason = body.reason if body else None
    payload = body.payload if body else {}
    # W18-A25: pre-extract cleartext task fields so blocked/failed paths still
    # land in /api/agents/tasks with a useful title.
    task_fields = _agent_task_fields(action_id, payload, None)
    if contract is None:
        proof_event_id = _append_agent_proof(
            "hermes_agent.action.blocked",
            actor,
            {
                "action_id": action_id,
                "status": "blocked",
                "reason": "action_not_registered",
                "requested_reason": requested_reason,
                **task_fields,
            },
        )
        return {
            "action_id": action_id,
            "accepted": False,
            "status": "blocked",
            "reason": "This Hermes Agent action is not registered in the operator action catalog.",
            "proof_event_id": proof_event_id,
        }
    handler = contract.get("handler")
    if not handler:
        proof_event_id = _append_agent_proof(
            "hermes_agent.action.blocked",
            actor,
            {
                "action_id": action_id,
                "status": contract["status"],
                "reason": contract.get("blocked_reason") or "action_has_no_executor",
                "requested_reason": requested_reason,
                **task_fields,
            },
        )
        return {
            "action_id": action_id,
            "accepted": False,
            "status": contract["status"],
            "reason": contract.get("blocked_reason") or "This action has no safe executor yet.",
            "proof_event_id": proof_event_id,
            "contract": _public_action_contract(contract),
        }
    try:
        result = _execute_catalog_handler(str(handler), actor, payload)
    except HTTPException:
        raise
    except Exception as exc:
        proof_event_id = _append_agent_proof(
            "hermes_agent.action.failed",
            actor,
            {
                "action_id": action_id,
                "handler": handler,
                "status": "failed",
                "reason": _redact(str(exc))[:500],
                **task_fields,
            },
        )
        return {
            "action_id": action_id,
            "accepted": False,
            "status": "failed",
            "reason": f"Catalog action failed: {_redact(str(exc))[:300]}",
            "proof_event_id": proof_event_id,
            "contract": _public_action_contract(contract),
        }
    # W18-A25: refresh task fields with anything the handler result added.
    task_fields = _agent_task_fields(action_id, payload, result)
    proof_event_id = _append_agent_proof(
        "hermes_agent.action.executed",
        actor,
        {
            "action_id": action_id,
            "handler": handler,
            "status": "completed",
            "result_status": _result_status(result),
            "result_sha256": hashlib.sha256(
                json.dumps(_proof_safe_result(result), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest(),
            "requested_reason": requested_reason,
            **task_fields,
        },
    )
    # W18-A25: bust the /api/agents/tasks cache so the next GUI poll sees
    # this new row immediately instead of waiting up to 10s.
    _AGENT_TASKS_CACHE["ts"] = 0.0
    _AGENT_TASKS_CACHE["payload"] = None
    return {
        "action_id": action_id,
        "accepted": True,
        "status": "completed",
        "proof_event_id": proof_event_id,
        "contract": _public_action_contract(contract),
        "result": result,
    }


def _execute_catalog_handler(handler: str, actor: str, payload: dict[str, Any]) -> dict:
    if handler.startswith("agents.playwright."):
        scope = handler.rsplit(".", 1)[-1]
        persona_id = str(
            payload.get("persona_id") or (actor if actor in PERSONAS else "oliver-qa-agent")
        )
        return playwright_run(
            persona_id,
            AgentPlaywrightRunRequest(
                scope=scope,
                reason=str(payload.get("reason") or "Hermes Agent operator catalog proof"),
            ),
        )
    if handler == "agents.health":
        probe = runtime_probe()
        return {
            "ready": bool(probe["ready"]),
            "status": probe["status"],
            "reason": probe["reason"],
            "model": probe.get("model"),
            "latency_ms": probe.get("latency_ms"),
        }
    if handler == "code.programming_readiness":
        from hermes3d.services import code_history

        return code_history.programming_readiness()
    if handler == "code.teams.readiness":
        from hermes3d.services import code_history

        return code_history.provider_team_readiness()
    if handler == "code.providers.smoke":
        from hermes3d.services import code_history

        return code_history.provider_execution_smoke(
            _required_payload_text(payload, "provider_id"),
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
        )
    if handler == "code.e2e.readiness":
        from hermes3d.services import code_history

        return code_history.agent_e2e_readiness()
    if handler == "code.cli_runners.readiness":
        from hermes3d.services import code_history

        return code_history.code_cli_runners()
    if handler == "code.e2e.run":
        from hermes3d.services import code_history

        files = payload.get("files")
        role_chain = payload.get("role_chain")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        if role_chain is not None and not isinstance(role_chain, list):
            raise ValueError("Payload field role_chain must be a list when supplied.")
        return code_history.run_agent_e2e_job(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            title=_required_payload_text(payload, "title"),
            files=files,
            objective=_required_payload_text(payload, "objective"),
            target_branch=str(payload.get("target_branch") or "") or None,
            role_chain=role_chain,
            cli_worker=str(payload.get("cli_worker") or "") or None,
            release_on_finish=bool(payload.get("release_on_finish", True)),
        )
    if handler == "code.teams.assign_task":
        from hermes3d.services import code_history

        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.assign_provider_team_task(
            owner=actor,
            team_id=_required_payload_text(payload, "team_id"),
            task_id=_required_payload_text(payload, "task_id"),
            title=_required_payload_text(payload, "title"),
            files=files,
            objective=_required_payload_text(payload, "objective"),
            target_branch=str(payload.get("target_branch") or "") or None,
            review_required=bool(payload.get("review_required", True)),
        )
    if handler == "code.teams.request_review":
        from hermes3d.services import code_history

        files = payload.get("files")
        proof_ids = payload.get("proof_ids")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        if not isinstance(proof_ids, list) or not proof_ids:
            raise ValueError("Payload field proof_ids must be a non-empty list.")
        return code_history.request_provider_team_review(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            summary=_required_payload_text(payload, "summary"),
            files=files,
            proof_ids=proof_ids,
            reviewer_team_id=str(payload.get("reviewer_team_id") or "deepseek-reviewers"),
        )
    if handler == "code.teams.run_coding_pass":
        from hermes3d.services import code_history

        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.run_provider_team_coding_pass(
            owner=actor,
            team_id=str(payload.get("team_id") or "minimax-builders"),
            task_id=_required_payload_text(payload, "task_id"),
            title=_required_payload_text(payload, "title"),
            files=files,
            objective=_required_payload_text(payload, "objective"),
            target_branch=str(payload.get("target_branch") or "") or None,
        )
    if handler == "code.teams.run_review_pass":
        from hermes3d.services import code_history

        files = payload.get("files")
        proof_ids = payload.get("proof_ids")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        if not isinstance(proof_ids, list) or not proof_ids:
            raise ValueError("Payload field proof_ids must be a non-empty list.")
        return code_history.run_provider_team_review_pass(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            summary=_required_payload_text(payload, "summary"),
            files=files,
            proof_ids=proof_ids,
            reviewer_team_id=str(payload.get("reviewer_team_id") or "deepseek-reviewers"),
        )
    if handler == "code.mcp_locks.readiness":
        from hermes3d.services import code_history

        return code_history.mcp_lock_readiness()
    if handler == "code.write.readiness":
        from hermes3d.services import code_history

        return code_history.code_write_readiness()
    if handler == "code.history.files":
        from hermes3d.services import code_history

        return code_history.list_touched_files(limit=int(payload.get("limit") or 200))
    if handler == "code.history.snapshot":
        from hermes3d.services import code_history

        return code_history.snapshot_file(
            _required_payload_text(payload, "relative_path"),
            agent_id=actor,
            action_id=str(payload.get("action_id") or "agent.catalog.snapshot"),
            reason=str(payload.get("reason") or "Hermes Agent requested code history snapshot"),
        )
    if handler == "code.repo.status":
        from hermes3d.services import code_history

        return code_history.repo_status()
    if handler == "code.repo.tree":
        from hermes3d.services import code_history

        return code_history.repo_tree(
            root=str(payload.get("root") or "."),
            limit=int(payload.get("limit") or 400),
        )
    if handler == "code.repo.search":
        from hermes3d.services import code_history

        return code_history.search_text(
            _required_payload_text(payload, "pattern"),
            root=str(payload.get("root") or "."),
            max_results=int(payload.get("max_results") or 100),
        )
    if handler == "code.file.read":
        from hermes3d.services import code_history

        return code_history.read_file_slice(
            _required_payload_text(payload, "relative_path"),
            start_line=int(payload.get("start_line") or 1),
            line_count=int(payload.get("line_count") or 120),
        )
    if handler == "code.patch.propose":
        from hermes3d.services import code_history

        return code_history.propose_file_replacement(
            _required_payload_text(payload, "relative_path"),
            _required_payload_text(payload, "proposed_text"),
            agent_id=actor,
            base_sha256=str(payload.get("base_sha256") or "") or None,
            reason=str(payload.get("reason") or "Hermes Agent patch proposal"),
        )
    if handler == "code.patch.apply":
        from hermes3d.services import code_history

        return code_history.apply_patch_proposal(
            _required_payload_text(payload, "proposal_id"),
            agent_id=actor,
            task_id=_required_payload_text(payload, "task_id"),
            reason=str(payload.get("reason") or "Hermes Agent patch apply"),
        )
    if handler == "code.patch.apply_reviewed":
        from hermes3d.services import code_history

        review_proofs = payload.get("review_proof_ids")
        if not isinstance(review_proofs, list) or not review_proofs:
            raise ValueError("Payload field review_proof_ids must be a non-empty list.")
        return code_history.apply_reviewed_patch_proposal(
            _required_payload_text(payload, "proposal_id"),
            agent_id=actor,
            task_id=_required_payload_text(payload, "task_id"),
            review_proof_ids=[str(item) for item in review_proofs],
            reason=str(payload.get("reason") or "Hermes Agent reviewed patch apply"),
        )
    if handler == "code.gates.list":
        from hermes3d.services import code_history

        return code_history.list_mcp_gates()
    if handler == "code.gate.run":
        from hermes3d.services import code_history

        return code_history.run_mcp_gate(
            _required_payload_text(payload, "gate_id"),
            owner=actor,
            cwd=str(payload.get("cwd") or "."),
        )
    if handler == "code.git.readiness":
        from hermes3d.services import code_history

        return code_history.git_ship_readiness()
    if handler == "code.git.branch":
        from hermes3d.services import code_history

        return code_history.git_create_branch(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            branch_name=_required_payload_text(payload, "branch_name"),
            base_ref=str(payload.get("base_ref") or "") or None,
            reason=str(payload.get("reason") or "Hermes Agent branch creation"),
        )
    if handler == "code.git.stage_owned":
        from hermes3d.services import code_history

        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.git_stage_owned_files(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            files=files,
        )
    if handler == "code.git.commit_owned":
        from hermes3d.services import code_history

        files = payload.get("files")
        proof_ids = payload.get("proof_ids")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.git_commit_owned_files(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            files=files,
            message=_required_payload_text(payload, "message"),
            proof_ids=proof_ids if isinstance(proof_ids, list) else [],
        )
    if handler == "code.git.push":
        from hermes3d.services import code_history

        return code_history.git_push_current_branch(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            remote=str(payload.get("remote") or "origin"),
        )
    if handler == "code.git.pr":
        from hermes3d.services import code_history

        return code_history.git_open_pull_request(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            base_ref=_required_payload_text(payload, "base_ref"),
            title=_required_payload_text(payload, "title"),
            body=str(payload.get("body") or ""),
            draft=bool(payload.get("draft", True)),
        )
    if handler == "code.mcp_locks.state":
        from hermes3d.services import code_history

        return code_history.mcp_lock_state()
    if handler == "code.mcp_locks.claim_task":
        from hermes3d.services import code_history

        return code_history.claim_mcp_task(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            title=str(payload.get("title") or ""),
            files=payload.get("files") if isinstance(payload.get("files"), list) else [],
            reason=str(payload.get("reason") or "Hermes Agent claimed a code task"),
            role=str(payload.get("role") or "agent"),
        )
    if handler == "code.mcp_locks.lock_files":
        from hermes3d.services import code_history

        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.lock_mcp_files(
            owner=actor,
            files=files,
            task_id=_required_payload_text(payload, "task_id"),
            reason=str(payload.get("reason") or "Hermes Agent locked files for code work"),
            role=str(payload.get("role") or "agent"),
            ttl_minutes=int(payload.get("ttl_minutes") or 90),
        )
    if handler == "code.mcp_locks.heartbeat":
        from hermes3d.services import code_history

        return code_history.heartbeat_mcp_task(
            owner=actor, task_id=_required_payload_text(payload, "task_id")
        )
    if handler == "code.mcp_locks.release_files":
        from hermes3d.services import code_history

        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Payload field files must be a non-empty list.")
        return code_history.release_mcp_files(
            owner=actor,
            files=files,
            note=str(payload.get("note") or "Hermes Agent released code file locks"),
        )
    if handler == "code.mcp_locks.release_task":
        from hermes3d.services import code_history

        return code_history.release_mcp_task(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            note=str(payload.get("note") or "Hermes Agent completed code task"),
        )
    if handler == "code.mcp_locks.evidence":
        from hermes3d.services import code_history

        data = payload.get("data")
        return code_history.append_mcp_evidence(
            owner=actor,
            task_id=_required_payload_text(payload, "task_id"),
            kind=str(payload.get("kind") or "proof"),
            summary=_required_payload_text(payload, "summary"),
            data=data if isinstance(data, dict) else {},
        )
    if handler == "dashboard.snapshot":
        from hermes3d.api.routes import jobs as jobs_route
        from hermes3d.api.routes import notifications as notifications_route
        from hermes3d.api.routes import printers as printers_route
        from hermes3d.api.routes import system as system_route

        return {
            "status": "ready",
            "snapshot": system_route.system_snapshot(),
            "printers": printers_route.list_printers(),
            "active_jobs": jobs_route.list_jobs("running,printing,queued")[:10],
            "notifications": notifications_route.list_notifications(limit=10),
        }
    if handler == "source.verify_all":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        body: dict[str, Any] = {"actor": actor}
        if section:
            body["section"] = section
        return modules_route.verify_all_module_runtimes(body)
    if handler == "source.plan_setup_queue":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        body: dict[str, Any] = {"actor": actor}
        if section:
            body["section"] = section
        return modules_route.create_module_runtime_setup_queue(body)
    if handler == "source.runtime_gaps":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        return modules_route.module_runtime_gaps(section)
    if handler == "source.runner_contracts":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        return modules_route.module_runtime_runner_contracts(section)
    if handler == "source.runner_contract":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        return modules_route.get_module_runtime_runner_contract(module_id)
    if handler == "source.read_only_runner.smoke":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeReadOnlyRunnerRequest(actor=actor)
        return modules_route.create_module_runtime_read_only_runner(module_id, body)
    if handler == "source.executable_path_runner.smoke":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeExecutablePathRunnerRequest(actor=actor)
        return modules_route.create_module_runtime_executable_path_runner(module_id, body)
    if handler == "source.python_import_repair.preflight":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimePythonImportRepairRunnerRequest(actor=actor)
        return modules_route.create_module_runtime_python_import_repair_runner(module_id, body)
    if handler == "source.cli_install_config.preflight":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeCliInstallConfigRunnerRequest(actor=actor)
        return modules_route.create_module_runtime_cli_install_config_runner(module_id, body)
    if handler == "source.npm_package.preflight":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeNpmPackageRunnerRequest(actor=actor)
        return modules_route.create_module_runtime_npm_package_runner(module_id, body)
    if handler == "source.service_runner.start":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeStartRunnerRequest(
            actor=actor,
            execute=bool(payload.get("execute", False)),
        )
        return modules_route.create_module_runtime_start_runner(module_id, body)
    if handler == "source.service_runner.stop":
        from hermes3d.api.routes import modules as modules_route

        module_id = _required_payload_text(payload, "module_id")
        body = modules_route.ModuleRuntimeStartRunnerRequest(actor=actor, execute=False)
        return modules_route.stop_module_runtime_runner(module_id, body)
    if handler == "source.agent_cli_readiness":
        from hermes3d.api.routes import modules as modules_route

        return modules_route.module_agent_cli_readiness()
    if handler == "source.cli_surface":
        from hermes3d.api.routes import modules as modules_route

        return modules_route.module_cli_surface_audit()
    if handler == "source.modules":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        module_rows = modules_route.list_modules(section)
        return {"status": "ready", "count": len(module_rows), "modules": module_rows}
    if handler == "source.update_readiness":
        from hermes3d.api.routes import modules as modules_route

        section = str(payload.get("section") or "").strip() or None
        deep = bool(payload.get("deep"))
        return modules_route.module_update_readiness(section=section, deep=deep)
    if handler == "source.verifiers":
        from hermes3d.api.routes import modules as modules_route

        return modules_route.module_runtime_verifiers()
    if handler == "settings.runtime_readiness":
        from hermes3d.api.routes import system as system_route

        return system_route.runtime_readiness()
    if handler == "providers.health":
        from hermes3d.api.routes import system as system_route

        return system_route.provider_health()
    if handler == "learning.idle_workbench":
        from hermes3d.api.routes import learning as learning_route

        return learning_route.idle_workbench()
    if handler == "learning.research_report":
        from hermes3d.api.routes import learning as learning_route

        candidate_id = str(payload.get("candidate_id") or "").strip()
        if not candidate_id:
            workbench = learning_route.idle_workbench()
            for candidate in workbench.get("candidates", []):
                if (
                    isinstance(candidate, dict)
                    and candidate.get("kind") == "research"
                    and candidate.get("status") in {"queued", "ready_for_review"}
                ):
                    candidate_id = str(candidate.get("id") or "")
                    break
        if not candidate_id:
            created = learning_route.create_idle_candidate(
                learning_route.IdleCandidateCreate(
                    title="Hermes Agent Source OS operator coverage research",
                    summary="Research-only report on current Source OS and operator-action coverage gaps. No code, install, update, movement, upload, or print actions.",
                    kind="research",
                    agent_id="research-agent",
                    risk_level="low",
                    source="hermes_agent_catalog",
                    target_tab="source_os",
                    created_by=actor,
                )
            )
            candidate_id = str((created.get("candidate") or {}).get("id") or "")
        if not candidate_id:
            raise HTTPException(
                status_code=409, detail={"reason": "No runnable research candidate is available."}
            )
        return learning_route.run_idle_candidate(
            candidate_id,
            learning_route.IdleCandidateRun(actor=actor, notes=str(payload.get("notes") or "")),
        )
    if handler == "printers.refresh":
        from hermes3d.api.routes import printers as printers_route

        printer_rows = printers_route.list_printers()
        return {"status": "ready", "count": len(printer_rows), "printers": printer_rows}
    if handler == "printers.upload_start":
        from hermes3d.api.routes import printers as printers_route

        printer_id = _required_payload_text(payload, "printer_id")
        gcode_path = _required_payload_text(payload, "gcode_path")
        request = printers_route.GcodeUploadRequest(
            gcode_path=gcode_path,
            job_id=str(payload.get("job_id") or ""),
            actor=actor,
            start=bool(payload.get("start")),
            remote_subdir=str(payload.get("remote_subdir") or "hermes3d"),
        )
        return printers_route.upload_gcode_to_printer(printer_id, request)
    if handler == "observe.cameras":
        from hermes3d.api.routes import observe as observe_route

        camera_rows = observe_route.cameras()
        return {"status": "ready", "count": len(camera_rows), "cameras": camera_rows}
    if handler == "observe.capture_evidence":
        from hermes3d.api.routes import observe as observe_route

        return observe_route.capture_evidence(_required_payload_text(payload, "printer_id"))
    if handler == "autopilot.guardrails":
        from hermes3d.api.routes import autopilot as autopilot_route

        return {
            "status": "ready",
            "readiness": autopilot_route.readiness(),
            "guardrails": autopilot_route.guardrails(),
        }
    if handler == "design.intake":
        from hermes3d.api.routes import design as design_route

        prompt = str(payload.get("prompt") or "parametric desk organizer")
        constraints = (
            payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
        )
        return design_route.submit_intake(
            design_route.DesignIntake(prompt=prompt, constraints=constraints)
        )
    if handler == "generation.run":
        from hermes3d.api.routes import generation as generation_route

        constraints = (
            payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {}
        )
        request = generation_route.GenerationRun(
            prompt=str(payload.get("prompt") or "calibration cube"),
            seed=int(payload.get("seed") or 3201),
            reference_artifact_id=str(payload.get("reference_artifact_id") or "") or None,
            constraints=constraints,
        )
        return generation_route.run_generation(request)
    if handler == "jobs.list":
        from hermes3d.api.routes import jobs as jobs_route

        status = str(payload.get("status") or "").strip() or None
        job_rows = jobs_route.list_jobs(status)
        return {"status": "ready", "count": len(job_rows), "jobs": job_rows}
    if handler == "jobs.transition":
        from hermes3d.api.routes import jobs as jobs_route

        job_id = _required_payload_text(payload, "job_id")
        transition = _required_payload_text(payload, "transition").lower()
        reason = str(payload.get("reason") or "Hermes Agent catalog action")
        if transition == "cancel":
            return jobs_route.cancel_job(job_id)
        if transition == "repair_propose":
            return jobs_route.propose_repair(
                job_id, jobs_route.JobActorRequest(actor=actor, reason=reason)
            )
        if transition == "repair_apply":
            return jobs_route.apply_repair(
                job_id, jobs_route.JobActorRequest(actor=actor, reason=reason)
            )
        if transition == "retry":
            return jobs_route.retry_job(
                job_id, jobs_route.JobActorRequest(actor=actor, reason=reason)
            )
        if transition == "rollback":
            return jobs_route.rollback_job(
                job_id,
                jobs_route.JobRollbackRequest(
                    actor=actor,
                    reason=reason,
                    target_artifact_id=str(payload.get("target_artifact_id") or "") or None,
                ),
            )
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "Unsupported job transition.",
                "allowed": ["cancel", "repair_propose", "repair_apply", "retry", "rollback"],
            },
        )
    if handler == "artifacts.list":
        from hermes3d.api.routes import artifacts as artifacts_route

        job_id = str(payload.get("job_id") or "").strip() or None
        artifact_rows = artifacts_route.list_artifacts(job_id=job_id)
        count = (
            len(artifact_rows)
            if isinstance(artifact_rows, list)
            else sum(len(items) for items in artifact_rows.values())
        )
        return {"status": "ready", "count": count, "artifacts": artifact_rows}
    if handler == "approvals.list":
        from hermes3d.api.routes import approvals as approvals_route

        status = str(payload.get("status") or "pending").strip() or "pending"
        approval_rows = approvals_route.list_approvals(status)
        return {"status": "ready", "count": len(approval_rows), "approvals": approval_rows}
    if handler == "approvals.decide":
        from hermes3d.api.routes import approvals as approvals_route

        approval_id = _required_payload_text(payload, "approval_id")
        decision = _required_payload_text(payload, "decision").lower()
        notes = str(payload.get("notes") or payload.get("reason") or "")
        if decision == "approve":
            return approvals_route.approve(approval_id, approvals_route.ApprovalNotes(notes=notes))
        if decision == "reject":
            return approvals_route.reject(approval_id, approvals_route.ApprovalNotes(reason=notes))
        raise HTTPException(
            status_code=422,
            detail={"reason": "Unsupported approval decision.", "allowed": ["approve", "reject"]},
        )
    if handler == "plugins.list":
        from hermes3d.api.routes import plugins as plugins_route

        plugin_rows = plugins_route.list_plugins()
        return {"status": "ready", "count": len(plugin_rows), "plugins": plugin_rows}
    if handler == "notifications.list":
        from hermes3d.api.routes import notifications as notifications_route

        return notifications_route.list_notifications(limit=int(payload.get("limit") or 50))
    if handler == "proof.bundles":
        from hermes3d.api.routes import system as system_route

        proof_rows = system_route.proof_bundles(limit=int(payload.get("limit") or 20))
        return {"status": "ready", "count": len(proof_rows), "proof_bundles": proof_rows}
    if handler == "workflows.list":
        from hermes3d.api.routes import system as system_route

        workflow_rows = system_route.workflows()
        return {"status": "ready", "count": len(workflow_rows), "workflows": workflow_rows}
    if handler == "design.toolchain":
        from hermes3d.api.routes import design as design_route

        return design_route.toolchain_status()
    if handler == "generation.services":
        from hermes3d.api.routes import generation as generation_route

        service_rows = generation_route.services()
        return {"status": "ready", "count": len(service_rows), "services": service_rows}
    if handler == "voice.catalog":
        from hermes3d.api.routes import voice as voice_route

        return voice_route.voices(locale=str(payload.get("locale") or "en"))
    if handler == "voice.agents":
        from hermes3d.api.routes import voice as voice_route

        voice_rows = voice_route.voice_agents()
        return {"status": "ready", "count": len(voice_rows), "voice_agents": voice_rows}
    if handler == "voice.preview":
        from hermes3d.api.routes import voice as voice_route

        return voice_route.preview_voice(
            voice_route.VoicePreview(
                id=str(payload.get("agent_id") or actor),
                voice=str(payload.get("voice") or "en-GB-MaisieNeural"),
                text=str(payload.get("text") or voice_route.DEFAULT_PREVIEW_TEXT),
                rate=float(payload.get("rate") or 1.0),
                pitch_pct=int(payload.get("pitch_pct") or 0),
            )
        )
    if handler == "voice.stt":
        from hermes3d.api.routes import voice as voice_route

        artifact_id = _required_payload_text(payload, "artifact_id")
        artifact = row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
        if not artifact:
            raise HTTPException(
                status_code=404,
                detail={"reason": "Audio artifact not found.", "artifact_id": artifact_id},
            )
        audio_path = Path(str(artifact.get("file_path") or ""))
        if not audio_path.exists() or not audio_path.is_file():
            raise HTTPException(
                status_code=404,
                detail={"reason": "Audio artifact file not found.", "artifact_id": artifact_id},
            )
        audio = audio_path.read_bytes()
        if len(audio) > voice_route.MAX_STT_AUDIO_BYTES:
            raise HTTPException(
                status_code=413,
                detail={
                    "reason": "Audio artifact is too large for speech transcription.",
                    "bytes": len(audio),
                },
            )
        config = voice_route._azure_config()
        if not config["configured"]:
            proof_event_id = voice_route._append_voice_proof(
                "voice.stt.blocked", {"status": "not_configured", "artifact_id": artifact_id}
            )
            return {
                "accepted": False,
                "configured": False,
                "status": "not_configured",
                "reason": "Azure Speech credentials are not configured in the private runtime env.",
                "proof_event_id": proof_event_id,
            }
        transcript = voice_route._azure_fast_transcribe(
            config,
            audio,
            _content_type_for_path(audio_path),
            audio_path.name,
            str(payload.get("locale") or "en-US"),
        )
        proof_event_id = voice_route._append_voice_proof(
            "voice.stt.transcribed",
            {
                "status": "ready",
                "artifact_id": artifact_id,
                "bytes": len(audio),
                "locale": str(payload.get("locale") or "en-US"),
                "provider": "azure_fast_transcription",
                "transcript_sha256": hashlib.sha256(
                    transcript["transcript"].encode("utf-8")
                ).hexdigest(),
                "phrase_count": transcript["phrase_count"],
            },
        )
        return {
            "accepted": True,
            "configured": True,
            "status": "ready",
            "provider": "azure",
            **transcript,
            "bytes": len(audio),
            "proof_event_id": proof_event_id,
        }
    if handler == "roadmap.operator_coverage":
        from hermes3d.api.routes import roadmap as roadmap_route

        payload = roadmap_route.tab_completion()
        return {
            "status": payload.get("agent_operator_contract", {}).get("state") or "in_progress",
            "agent_operator_contract": payload.get("agent_operator_contract"),
            "source_runtime_action_plan": payload.get("source_runtime_action_plan"),
        }
    raise RuntimeError(f"Unsupported handler: {handler}")


def _agent_action_contracts() -> list[dict[str, Any]]:
    cached_contracts = _ACTION_CONTRACT_CACHE.get("contracts")
    cached_at = float(_ACTION_CONTRACT_CACHE.get("ts") or 0.0)
    if (
        isinstance(cached_contracts, list)
        and (time.monotonic() - cached_at) < ACTION_CONTRACT_CACHE_TTL_S
    ):
        return [dict(contract) for contract in cached_contracts]
    source_counts = _source_action_counts()
    runtime = _runtime_action_counts()
    idle = _idle_action_counts()
    source_ready = int(source_counts.get("runtime_ready") or 0)
    source_gaps = int(source_counts.get("runner_gaps") or 0)
    agent_cli = int(source_counts.get("verified_agent_cli") or 0)
    cli_candidates = int(source_counts.get("cli_candidates") or 0)
    read_only_runners = int(source_counts.get("read_only_runner_available") or 0)
    executable_path_runners = int(source_counts.get("executable_path_runner_available") or 0)
    python_import_repairs = int(source_counts.get("python_import_repair_available") or 0)
    cli_install_configs = int(source_counts.get("cli_install_config_available") or 0)
    npm_package_preflights = int(source_counts.get("npm_package_preflight_available") or 0)
    # W18-A25: parallelize the four independent readiness probes and
    # cap the slowest one (cli_runners) with a 4s deadline.
    #
    # The W18-A3 audit measured 41s wall on cold-start because these
    # probes ran sequentially and each launched subprocesses. Profiling
    # showed the dominant cost is ``code_cli_runners()`` (~18s on a host
    # where opencode/openhands binaries are absent: each shell-out probes
    # ``--version`` then falls through to ``version`` with 8s timeouts,
    # plus ``code_sandbox_readiness()`` runs ``docker version`` 5s +
    # ``docker image inspect`` 8s).
    #
    # The contract-catalog only needs the "is the runner present?" answer
    # — it never blocks on a write run. So we run cli_runners with a 4s
    # budget and fall back to a deferred entry that the catalog
    # surfaces as `status: setup_required` if it doesn't finish in time.
    # The next 60s-TTL warm hit returns the cached full payload, and the
    # operator can hit ``/api/code-operator/cli-runners`` directly for
    # the un-bounded answer when they actually need to launch a runner.
    #
    # Operator-freeze contract: no printer-control endpoints invoked.
    _CLI_RUNNERS_BUDGET_S = 2.5
    _CLI_RUNNERS_DEFERRED: dict[str, Any] = {
        "status": "setup_required",
        "count": 2,
        "detected": 0,
        "runners": [
            {
                "id": "opencode",
                "label": "OpenCode CLI",
                "detected": False,
                "executable": None,
                "version": None,
                "version_status": "deferred",
                "write_allowed": False,
                "blocked_reason": (
                    "Catalog cold-path deferred CLI subprocess probe; "
                    "GET /api/code-operator/cli-runners for the un-bounded check."
                ),
                "policy": "version_preflight",
            },
            {
                "id": "openhands",
                "label": "OpenHands CLI",
                "detected": False,
                "executable": None,
                "version": None,
                "version_status": "deferred",
                "write_allowed": False,
                "blocked_reason": (
                    "Catalog cold-path deferred CLI subprocess probe; "
                    "GET /api/code-operator/cli-runners for the un-bounded check."
                ),
                "policy": "version_preflight",
            },
        ],
        "sandbox": {
            "status": "deferred",
            "ready": False,
            "mode": "docker",
            "docker_executable": None,
            "docker_version": None,
            "image_configured": False,
            "image": None,
            "network_mode": "none",
            "workspace_mount": "",
            "denied_paths": [],
            "blocked_reasons": [
                "Sandbox probe deferred from catalog cold path; the catalog cache "
                "will return the full payload within 60s once probes settle."
            ],
        },
        "policy": {
            "write_runs_allowed": False,
            "reason": "Deferred from catalog cold path; CLI runner write runs always require explicit /api/code-operator/cli-runners/run.",
            "allowed_now": ["detect_deferred"],
        },
    }
    try:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as _FutureTimeout

        from hermes3d.services import code_history

        # NOTE: we manage the pool manually so we can `shutdown(wait=False)`
        # when cli_runners exceeds its budget. A `with` block would wait
        # for the stuck CLI subprocess thread on exit.
        pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agents-catalog")
        try:
            mcp_future = pool.submit(code_history.mcp_lock_readiness)
            teams_future = pool.submit(code_history.provider_team_readiness)
            cli_future = pool.submit(code_history.code_cli_runners)
            programming_future = pool.submit(code_history.programming_readiness)
            mcp_locks = mcp_future.result(timeout=30)
            provider_teams = teams_future.result(timeout=30)
            programming = programming_future.result(timeout=30)
            try:
                cli_runners = cli_future.result(timeout=_CLI_RUNNERS_BUDGET_S)
                # If a real result came back this fast, drop any cached deferred fallback.
                _ACTION_CONTRACT_CACHE["cli_runners_deferred"] = cli_runners
            except _FutureTimeout:
                # Prefer last-known full payload if we have it; otherwise
                # the static deferred envelope is the GUI-honest answer.
                deferred_payload = _ACTION_CONTRACT_CACHE.get("cli_runners_deferred")
                cli_runners = (
                    deferred_payload
                    if isinstance(deferred_payload, dict)
                    else _CLI_RUNNERS_DEFERRED
                )

                def _capture_deferred(future: Any) -> None:
                    if future.cancelled() or future.exception() is not None:
                        return
                    try:
                        payload = future.result(timeout=0)
                    except Exception:
                        return
                    _ACTION_CONTRACT_CACHE["cli_runners_deferred"] = payload

                cli_future.add_done_callback(_capture_deferred)
        finally:
            # wait=False detaches the still-running cli thread so we don't
            # block the response. Subprocess timeouts inside that thread
            # cap its eventual termination.
            pool.shutdown(wait=False)

        # Build the e2e readiness summary from the cached parallel results
        # instead of calling ``agent_e2e_readiness()`` which would re-spawn
        # all the subprocess probes. We mirror the exact same shape and
        # ``blocked_reasons`` aggregation as the canonical helper so the
        # rest of the contract list keeps the same status semantics.
        folder_index = code_history.folder_index_context([])
        blocked_reasons: list[str] = []
        if not programming.get("ready"):
            blocked_reasons.extend(str(item) for item in programming.get("blocked_reasons", []))
        if not provider_teams.get("ready"):
            blocked_reasons.extend(str(item) for item in provider_teams.get("blocked_reasons", []))
        if folder_index.get("missing"):
            blocked_reasons.append(
                "Folder index is incomplete: " + ", ".join(folder_index["missing"])
            )
        e2e_readiness = {
            "status": "ready" if not blocked_reasons else "blocked",
            "ready": not blocked_reasons,
            "summary": "MiniMax builder + DeepSeek reviewer coding loop readiness.",
            "blocked_reasons": blocked_reasons,
            "programming": programming,
            "provider_teams": provider_teams,
            "folder_index": folder_index,
            "cli_runners": cli_runners,
            "next_required_steps": [
                "submit task through Agent Code Workbench",
                "load folder index",
                "claim task and lock files",
                "snapshot files",
                "run MiniMax coding pass",
                "run DeepSeek review pass",
                "apply only reviewed bounded patch proposals",
                "run gates and ship PR with proof",
            ],
        }
    except Exception:
        mcp_locks = {
            "ready": False,
            "blocked_reason": "Hermes MCP lock readiness could not be evaluated.",
        }
        provider_teams = {
            "ready": False,
            "status": "blocked",
            "blocked_reasons": ["Hermes Agent provider-team readiness could not be evaluated."],
        }
        e2e_readiness = {
            "ready": False,
            "status": "blocked",
            "blocked_reasons": ["Hermes Agent E2E readiness could not be evaluated."],
        }
        cli_runners = {
            "status": "blocked",
            "detected": 0,
            "runners": [],
            "policy": {"write_runs_allowed": False},
        }
    team_blocked_reason = (
        "; ".join(str(item) for item in provider_teams.get("blocked_reasons", [])[:4])
        if provider_teams.get("blocked_reasons")
        else None
    )
    e2e_blocked_reason = (
        "; ".join(str(item) for item in e2e_readiness.get("blocked_reasons", [])[:4])
        if e2e_readiness.get("blocked_reasons")
        else None
    )
    cli_runner_count = int(cli_runners.get("detected") or 0) if isinstance(cli_runners, dict) else 0
    contracts = [
        _contract(
            "agents.health.refresh",
            "Refresh Hermes Agent runtime health",
            "agents",
            "ready" if runtime.get("hermes_agent_runtime") == "ready" else "blocked",
            "read",
            "low",
            "GET /api/agents/health",
            "agents.health",
            "Checks the configured local/private agent runtime bridge.",
        ),
        _contract(
            "code.programming_readiness.refresh",
            "Refresh Hermes Agent programming readiness",
            "agents",
            "ready",
            "read",
            "low",
            "GET /api/code-operator/programming-readiness",
            "code.programming_readiness",
            "Checks true source inputs from Nous Hermes Agent and Atomic Hermes plus MiniMax/DeepSeek provider readiness.",
        ),
        _contract(
            "code.teams.readiness.refresh",
            "Refresh Hermes Agent team readiness",
            "agents",
            str(provider_teams.get("status") or "blocked"),
            "read",
            "low",
            "GET /api/code-operator/teams/readiness",
            "code.teams.readiness",
            "Checks MiniMax builder and DeepSeek reviewer team readiness without exposing provider secrets.",
            None
            if provider_teams.get("ready")
            else (team_blocked_reason or "Hermes Agent provider teams are not ready."),
        ),
        _contract(
            "code.providers.smoke",
            "Run live provider smoke proof",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/providers/smoke",
            "code.providers.smoke",
            "Calls MiniMax or DeepSeek through the same bounded OpenAI-compatible chat path used by coding/review passes and records pass/blocked evidence without exposing secrets.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason")
                or "Hermes MCP locks are not ready for provider proof."
            ),
        ),
        _contract(
            "code.e2e.readiness.refresh",
            "Refresh Agent Code Workbench readiness",
            "agents",
            "ready" if e2e_readiness.get("ready") else "blocked",
            "read",
            "low",
            "GET /api/code-operator/e2e/readiness",
            "code.e2e.readiness",
            "Checks folder index, MCP locks, MiniMax builder, DeepSeek reviewer, snapshots, and proof prerequisites for Hermes Agents coding alongside Codex.",
            None
            if e2e_readiness.get("ready")
            else (e2e_blocked_reason or "Hermes Agent E2E workbench is not ready."),
        ),
        _contract(
            "code.cli_runners.readiness.refresh",
            "Refresh OpenHands/OpenCode CLI readiness",
            "agents",
            "ready",
            "read",
            "low",
            "GET /api/code-operator/cli-runners",
            "code.cli_runners.readiness",
            f"Detects OpenHands and OpenCode CLI binaries for future sandboxed agent delegation; current contract is detection/version only, no writes. Detected now: {cli_runner_count}.",
        ),
        _contract(
            "code.e2e.run",
            "Run proof-gated Agent Code Workbench job",
            "agents",
            "ready" if e2e_readiness.get("ready") else "blocked",
            "artifact",
            "high",
            "POST /api/code-operator/e2e/jobs",
            "code.e2e.run",
            "Runs the real folder-index -> task claim -> file lock -> pre-snapshot -> MiniMax coding pass -> DeepSeek review pass loop and returns a reviewed patch-planning artifact. It does not mutate source directly.",
            None
            if e2e_readiness.get("ready")
            else (e2e_blocked_reason or "Hermes Agent E2E workbench is not ready."),
        ),
        _contract(
            "code.teams.assign_task",
            "Assign provider-backed code task",
            "agents",
            "ready" if provider_teams.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/teams/assign-task",
            "code.teams.assign_task",
            "Records a proof-backed provider-team coding task only after selected source, provider, and MCP lock prerequisites are ready.",
            None
            if provider_teams.get("ready")
            else (team_blocked_reason or "Hermes Agent provider teams are not ready."),
        ),
        _contract(
            "code.teams.request_review",
            "Request second-team code review",
            "agents",
            "ready" if provider_teams.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/teams/request-review",
            "code.teams.request_review",
            "Requests a proof-backed DeepSeek/Atomic Hermes review for files and proof ids before PR shipping.",
            None
            if provider_teams.get("ready")
            else (team_blocked_reason or "Hermes Agent reviewer team is not ready."),
        ),
        _contract(
            "code.teams.run_coding_pass",
            "Run MiniMax coding plan pass",
            "agents",
            "ready" if provider_teams.get("ready") else "blocked",
            "artifact",
            "medium",
            "POST /api/code-operator/teams/run-coding-pass",
            "code.teams.run_coding_pass",
            "Calls the configured MiniMax builder through a bounded OpenAI-compatible chat request and records a code-plan artifact; it does not edit source files.",
            None
            if provider_teams.get("ready")
            else (team_blocked_reason or "MiniMax builder team is not ready."),
        ),
        _contract(
            "code.teams.run_review_pass",
            "Run DeepSeek review pass",
            "agents",
            "ready" if provider_teams.get("ready") else "blocked",
            "artifact",
            "medium",
            "POST /api/code-operator/teams/run-review-pass",
            "code.teams.run_review_pass",
            "Calls the configured DeepSeek reviewer through a bounded OpenAI-compatible chat request and records a review artifact tied to proof ids.",
            None
            if provider_teams.get("ready")
            else (team_blocked_reason or "DeepSeek reviewer team is not ready."),
        ),
        _contract(
            "code.mcp_locks.readiness.refresh",
            "Refresh Hermes MCP lock readiness",
            "agents",
            "ready" if mcp_locks.get("ready") else "partial",
            "read",
            "low",
            "GET /api/code-operator/mcp-locks/readiness",
            "code.mcp_locks.readiness",
            "Checks that the Hermes Agent runtime has hermes3d-locks source/server access and that MCP_LOCK_WORKSPACE matches the actual edit workspace before write tools can enable.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for code writes."
            ),
        ),
        _contract(
            "code.write_readiness.refresh",
            "Refresh Hermes Agent write readiness",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "read",
            "low",
            "GET /api/code-operator/write/readiness",
            "code.write.readiness",
            "Explains whether Hermes Agents may enable patch/apply/command/git coding tools yet. Read-only context stays available; write tools stay blocked until locks, source inputs, providers, snapshots, and proof gates are ready.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for code writes."
            ),
        ),
        _contract(
            "code.history.files.refresh",
            "Refresh agent-touched file history",
            "agents",
            "ready",
            "read",
            "low",
            "GET /api/code-operator/history/files",
            "code.history.files",
            "Lists files already snapshotted by Hermes Agent code operations.",
        ),
        _contract(
            "code.history.snapshot",
            "Snapshot a Hermes3D source file",
            "agents",
            "ready",
            "artifact",
            "medium",
            "POST /api/code-operator/history/snapshots",
            "code.history.snapshot",
            "Creates a pre-change snapshot and proof event before an agent edits a source file.",
        ),
        _contract(
            "code.repo.status.refresh",
            "Refresh Hermes3D repo status",
            "agents",
            "ready",
            "read",
            "low",
            "GET /api/code-operator/repo/status",
            "code.repo.status",
            "Reads branch, commit, dirty files, and diff stat so agents know the current project state before planning.",
        ),
        _contract(
            "code.repo.tree.refresh",
            "Read bounded Hermes3D repo tree",
            "agents",
            "ready",
            "read",
            "low",
            "GET /api/code-operator/repo/tree",
            "code.repo.tree",
            "Returns a bounded project-relative file tree while excluding secrets, generated output, caches, node_modules, and VCS internals.",
        ),
        _contract(
            "code.repo.search",
            "Search Hermes3D source text",
            "agents",
            "ready",
            "read",
            "low",
            "POST /api/code-operator/repo/search",
            "code.repo.search",
            "Runs bounded ripgrep against allowed project paths and returns path, line, column, and excerpt for agent planning.",
        ),
        _contract(
            "code.file.read",
            "Read bounded Hermes3D source slice",
            "agents",
            "ready",
            "read",
            "low",
            "POST /api/code-operator/files/read",
            "code.file.read",
            "Reads a bounded line slice from an allowed project text file with a content hash for proof.",
        ),
        _contract(
            "code.patch.propose",
            "Propose a Hermes3D source patch",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "artifact",
            "medium",
            "POST /api/code-operator/patch/proposals",
            "code.patch.propose",
            "Creates a pre-snapshot, hash-checks the target, writes a reviewable patch proposal artifact, and appends proof without mutating source files.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason")
                or "Hermes MCP locks are not ready for code patch proposals."
            ),
        ),
        _contract(
            "code.patch.apply",
            "Apply MCP-locked Hermes3D source patch",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/patch/apply",
            "code.patch.apply",
            "Applies an existing patch proposal only with a same-owner Hermes MCP file lock for the target, records pre/post snapshots, and appends chained MCP evidence.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason")
                or "Hermes MCP locks are not ready for code patch apply."
            ),
        ),
        _contract(
            "code.patch.apply_reviewed",
            "Apply reviewed MCP-locked patch",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/patch/apply-reviewed",
            "code.patch.apply_reviewed",
            "Applies a patch proposal only after same-owner MCP lock checks and at least one review/proof id, then records reviewed-apply evidence for gate/PR shipping.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason")
                or "Hermes MCP locks are not ready for reviewed patch apply."
            ),
        ),
        _contract(
            "code.gates.list.refresh",
            "List Hermes MCP code gates",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "read",
            "low",
            "GET /api/code-operator/gates",
            "code.gates.list",
            "Lists gates exposed by the exact-worktree hermes3d-locks MCP server; no arbitrary shell is exposed.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for gates."
            ),
        ),
        _contract(
            "code.gate.run",
            "Run Hermes MCP allowlisted gate",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/gates/run",
            "code.gate.run",
            "Runs one allowlisted hermes3d-locks MCP gate in the exact edit worktree and stores the gate result in the MCP evidence ledger.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for gates."
            ),
        ),
        _contract(
            "code.git.readiness.refresh",
            "Refresh Hermes Agent git shipping readiness",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "read",
            "low",
            "GET /api/code-operator/git/readiness",
            "code.git.readiness",
            "Shows whether the current branch, dirty files, snapshots, and MCP lock prerequisites allow agent branch/commit/push/PR work.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.git.branch",
            "Create Hermes Agent git branch",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/git/branch",
            "code.git.branch",
            "Creates only codex/ or hermes-agent/ branches from a clean worktree and records MCP evidence.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.git.stage_owned",
            "Stage snapshotted locked files",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/git/stage-owned",
            "code.git.stage_owned",
            "Stages only files that are changed, source-allowed, snapshotted by the same agent, and covered by an active same-owner MCP file lock.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.git.commit_owned",
            "Commit snapshotted Hermes Agent changes",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/git/commit-owned",
            "code.git.commit_owned",
            "Commits only the same snapshotted locked file set and embeds supplied proof ids in the commit message.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.git.push",
            "Push Hermes Agent branch",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "mutate",
            "high",
            "POST /api/code-operator/git/push",
            "code.git.push",
            "Pushes the current codex/ or hermes-agent/ branch to origin without force after the worktree is clean.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.git.pr",
            "Open Hermes Agent pull request",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "high",
            "POST /api/code-operator/git/pr",
            "code.git.pr",
            "Opens a GitHub PR for the current safe agent branch through the authenticated gh CLI and records evidence.",
            None
            if mcp_locks.get("ready")
            else str(
                mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready for git work."
            ),
        ),
        _contract(
            "code.mcp_locks.state.refresh",
            "Refresh Hermes MCP lock state",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "read",
            "low",
            "GET /api/code-operator/mcp-locks/state",
            "code.mcp_locks.state",
            "Reads exact-worktree Hermes lock/task/evidence state before coding work.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.claim_task",
            "Claim Hermes MCP code task",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/mcp-locks/claim-task",
            "code.mcp_locks.claim_task",
            "Claims a task through hermes3d-locks before any file lock or write.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.lock_files",
            "Lock Hermes3D code files",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/mcp-locks/lock-files",
            "code.mcp_locks.lock_files",
            "Atomically locks project-relative files through hermes3d-locks; denied paths and unsafe file types fail closed.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.heartbeat",
            "Heartbeat Hermes MCP code task",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "low",
            "POST /api/code-operator/mcp-locks/heartbeat",
            "code.mcp_locks.heartbeat",
            "Refreshes task/file-lock TTL while an agent is working.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.evidence",
            "Append Hermes MCP evidence",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/mcp-locks/evidence",
            "code.mcp_locks.evidence",
            "Appends hash-chained proof to the exact-worktree Hermes ledger.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.release_files",
            "Release Hermes MCP file locks",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/mcp-locks/release-files",
            "code.mcp_locks.release_files",
            "Releases files after evidence and gates are recorded.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "code.mcp_locks.release_task",
            "Release Hermes MCP code task",
            "agents",
            "ready" if mcp_locks.get("ready") else "blocked",
            "proof",
            "medium",
            "POST /api/code-operator/mcp-locks/release-task",
            "code.mcp_locks.release_task",
            "Completes a claimed code task after its file locks have been released.",
            None
            if mcp_locks.get("ready")
            else str(mcp_locks.get("blocked_reason") or "Hermes MCP locks are not ready."),
        ),
        _contract(
            "dashboard.snapshot.refresh",
            "Refresh dashboard truth snapshot",
            "dashboard",
            "ready",
            "read",
            "low",
            "GET dashboard aggregate",
            "dashboard.snapshot",
            "Reads system, printer, job, and notification state for the main dashboard.",
        ),
        _contract(
            "agents.playwright.observe",
            "Run Observe Playwright proof",
            "agents",
            "ready",
            "proof",
            "low",
            "POST /api/agents/{persona_id}/playwright-run",
            "agents.playwright.observe",
            "Use the existing persona-scoped Playwright runner with scope=observe.",
        ),
        _contract(
            "agents.playwright.smoke",
            "Run smoke Playwright proof",
            "agents",
            "ready",
            "proof",
            "medium",
            "POST /api/agents/{persona_id}/playwright-run",
            "agents.playwright.smoke",
            "Use the existing persona-scoped Playwright runner with scope=smoke.",
        ),
        _contract(
            "agents.playwright.full",
            "Run full Playwright proof",
            "agents",
            "ready",
            "proof",
            "medium",
            "POST /api/agents/{persona_id}/playwright-run",
            "agents.playwright.full",
            "Use the existing persona-scoped Playwright runner with scope=full.",
        ),
        _contract(
            "source.modules.refresh",
            "Refresh Source OS module rows",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules",
            "source.modules",
            "Returns the 60 source-backed module registry rows.",
        ),
        _contract(
            "source.verify_all",
            "Verify all Source OS runtimes",
            "source_os",
            "ready",
            "proof",
            "low",
            "POST /api/modules/runtime/verify-all",
            "source.verify_all",
            f"Runs registered safe verifiers only. Current proof target: {source_ready} ready rows, {source_gaps} runner gaps.",
        ),
        _contract(
            "source.plan_setup_queue",
            "Plan Source OS setup queue",
            "source_os",
            "ready",
            "plan",
            "low",
            "POST /api/modules/runtime/setup-queue",
            "source.plan_setup_queue",
            "Creates a proof-backed plan; it does not run unregistered installers.",
        ),
        _contract(
            "source.update_readiness.refresh",
            "Refresh Source OS update readiness",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/update/readiness",
            "source.update_readiness",
            "Reads update readiness without fetch, pull, build, install, or update side effects.",
        ),
        _contract(
            "source.runtime_gaps.refresh",
            "Refresh Source OS runner gaps",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/runtime/gaps",
            "source.runtime_gaps",
            f"Shows {source_gaps} source-app runner gaps that still block full agent app operation.",
        ),
        _contract(
            "source.runner_contracts.refresh",
            "Refresh Source OS runner contracts",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/runtime/runner-contracts",
            "source.runner_contracts",
            "Returns the 60-row Hermes Agent execution contract matrix; only rows with agent_executable=true may run app actions. read_only_runner_available rows may only re-run metadata/API proof; executable_path_runner_available rows may only read executable metadata; python_import_repair_available rows may only read source/dependency metadata; npm_package_preflight_available rows may only read package metadata/script names.",
        ),
        _contract(
            "source.runner_contract.refresh",
            "Refresh one Source OS runner contract",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/{module_id}/runtime/runner-contract",
            "source.runner_contract",
            "Returns the proof gate, safe actions, and exact blocked reason for one source-backed app.",
        ),
        _contract(
            "source.read_only_runner.smoke",
            "Run Source OS read-only runner smoke",
            "source_os",
            "ready" if read_only_runners else "partial",
            "proof",
            "low",
            "POST /api/modules/{module_id}/runtime/read-only-runner",
            "source.read_only_runner.smoke",
            f"Reruns only registered package/import/local API verifier proof for {read_only_runners} eligible rows; no setup, install, update, launch, file output, or printer action.",
        ),
        _contract(
            "source.executable_path_runner.smoke",
            "Run Source OS executable path smoke",
            "source_os",
            "ready" if executable_path_runners else "partial",
            "proof",
            "low",
            "POST /api/modules/{module_id}/runtime/executable-path-runner",
            "source.executable_path_runner.smoke",
            f"Reads only installed executable metadata/hash proof for {executable_path_runners} eligible desktop launcher rows; no app launch, setup, install, update, file output, or printer action.",
        ),
        _contract(
            "source.python_import_repair.preflight",
            "Preflight Source OS Python import repair",
            "source_os",
            "ready" if python_import_repairs else "partial",
            "proof",
            "low",
            "POST /api/modules/{module_id}/runtime/python-import-repair-runner",
            "source.python_import_repair.preflight",
            f"Reads failed Python import proof plus source/dependency metadata for {python_import_repairs} eligible CAD/modeling rows; no package install, environment creation, worker start, output write, or printer action.",
        ),
        _contract(
            "source.cli_install_config.preflight",
            "Preflight Source OS slicer CLI install/config",
            "source_os",
            "ready" if cli_install_configs else "partial",
            "proof",
            "low",
            "POST /api/modules/{module_id}/runtime/cli-install-config-runner",
            "source.cli_install_config.preflight",
            f"Reads Slic3r/SuperSlicer source, adapter schema, profile/config, and candidate executable metadata for {cli_install_configs} eligible rows; no install, launch, slicing, output write, or printer action.",
        ),
        _contract(
            "source.npm_package.preflight",
            "Preflight Source OS npm package metadata",
            "source_os",
            "ready" if npm_package_preflights else "partial",
            "proof",
            "low",
            "POST /api/modules/{module_id}/runtime/npm-package-runner",
            "source.npm_package.preflight",
            f"Reads package.json metadata, script names, lockfile/manifests, and local node/npm executable presence for {npm_package_preflights} eligible npm rows; no npm install, npm run, process start, output write, update, or printer action.",
        ),
        _contract(
            "source.service_runner.start",
            "Start supervised Source OS service runner",
            "source_os",
            "partial",
            "mutate",
            "high",
            "POST /api/modules/{module_id}/runtime/start-runner",
            "source.service_runner.start",
            "Runs only a registered local/private service command through the Source OS supervisor, then requires live health proof before runtime-ready.",
            "Per-module start still blocks unless its runner contract preflight passes; use execute=false for proof-only preflight.",
        ),
        _contract(
            "source.service_runner.stop",
            "Stop supervised Source OS service runner",
            "source_os",
            "ready",
            "mutate",
            "medium",
            "POST /api/modules/{module_id}/runtime/stop-runner",
            "source.service_runner.stop",
            "Stops only a PID that the Source OS supervisor previously recorded for the same module.",
        ),
        _contract(
            "source.verifiers.refresh",
            "Refresh Source OS verifier registry",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/runtime/verifiers",
            "source.verifiers",
            "Shows registered safe runtime verifier rows.",
        ),
        _contract(
            "source.agent_cli_readiness.refresh",
            "Refresh agent CLI readiness",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/runtime/agent-cli-readiness",
            "source.agent_cli_readiness",
            f"Shows {agent_cli} verified agent CLI runners and {cli_candidates} CLI/service signals needing verifiers.",
        ),
        _contract(
            "source.cli_surface.refresh",
            "Refresh Source OS CLI surface audit",
            "source_os",
            "ready",
            "read",
            "low",
            "GET /api/modules/runtime/cli-surface",
            "source.cli_surface",
            "Returns the proof-backed CLI/service surface audit.",
        ),
        _contract(
            "source.update_all",
            "Update all Source OS apps",
            "source_os",
            "partial",
            "mutate",
            "high",
            "PENDING",
            None,
            "Blocked until one-click backup, approval, smoke gate, and rollback policy is complete for every app family.",
            "App update center is partial; agents may plan/check but cannot bulk-update yet.",
        ),
        _contract(
            "source.register_missing_runners",
            "Execute missing Source OS setup runners",
            "source_os",
            "partial",
            "mutate",
            "high",
            "PENDING",
            None,
            "Blocked until every runner gap has a registered safe verifier/runner.",
            f"{source_gaps} Source OS rows still need runner contracts.",
        ),
        _contract(
            "settings.runtime_readiness.refresh",
            "Refresh runtime readiness ledger",
            "settings",
            "ready",
            "read",
            "low",
            "GET /api/system/runtime-readiness",
            "settings.runtime_readiness",
            "Shows runtime keys/status without exposing secret values.",
        ),
        _contract(
            "providers.health.refresh",
            "Refresh provider health",
            "settings",
            "ready",
            "read",
            "low",
            "GET /api/providers/health",
            "providers.health",
            "Reads local/cloud provider health without exposing secret values.",
        ),
        _contract(
            "learning.idle_workbench.refresh",
            "Refresh idle workbench",
            "learning",
            "ready",
            "read",
            "low",
            "GET /api/learning/idle-workbench",
            "learning.idle_workbench",
            "Shows candidate queue, blockers, and per-kind readiness.",
        ),
        _contract(
            "learning.research_report.run",
            "Run idle research report",
            "learning",
            "ready" if idle.get("research") == "ready" else "blocked",
            "report",
            "low",
            "POST /api/learning/idle-workbench/candidates/{id}/run",
            "learning.research_report",
            "Runs a report-only idle candidate; no install, merge, upload, move, or print.",
            None
            if idle.get("research") == "ready"
            else "Idle research is blocked until runtime and proof prerequisites are ready.",
        ),
        _contract(
            "learning.documentation.run",
            "Run idle documentation work",
            "learning",
            "ready" if idle.get("documentation") == "ready" else "blocked",
            "report",
            "medium",
            "POST /api/learning/idle-workbench/candidates/{id}/run",
            None,
            "Documentation work must wait for quiet-system and proof gates.",
            None
            if idle.get("documentation") == "ready"
            else "Current idle blockers prevent documentation execution.",
        ),
        _contract(
            "learning.app_update.run",
            "Run idle app update work",
            "learning",
            "ready" if idle.get("app_update") == "ready" else "blocked",
            "mutate",
            "high",
            "POST /api/learning/idle-workbench/candidates/{id}/run",
            None,
            "App update work stays gated by quiet-system, backup, approval, smoke gate, and rollback.",
            None
            if idle.get("app_update") == "ready"
            else "Current idle blockers or app update gates prevent execution.",
        ),
        _contract(
            "printers.refresh",
            "Refresh printer fleet",
            "printers",
            "ready" if runtime.get("printer_fleet") == "ready" else "partial",
            "read",
            "low",
            "GET /api/printers",
            "printers.refresh",
            "Agents can read live/degraded printer telemetry; physical actions use separate gates.",
        ),
        _contract(
            "printers.upload_start",
            "Upload/start printer job",
            "printers",
            "ready",
            "mutate",
            "critical",
            "POST /api/printers/{printer_id}/upload-gcode",
            "printers.upload_start",
            "Ready only with job_id, approved PRINT_APPROVAL, passing truth gates, idle printer, and non-S1 target.",
        ),
        _contract(
            "printers.s1_actions",
            "Move/upload/test/print on S1",
            "printers",
            "blocked",
            "mutate",
            "critical",
            "HTTP 423 policy",
            None,
            "S1 read-only camera/status remains allowed.",
            "User policy locks S1 movement, upload, test, and print.",
        ),
        _contract(
            "observe.cameras.refresh",
            "Refresh Observe camera registry",
            "observe",
            "ready",
            "read",
            "low",
            "GET /api/observe/cameras",
            "observe.cameras",
            "Returns configured live camera endpoints and view settings.",
        ),
        _contract(
            "observe.capture_evidence",
            "Capture camera evidence",
            "observe",
            "ready",
            "artifact",
            "medium",
            "POST /api/observe/cameras/{printer_id}/capture-evidence",
            "observe.capture_evidence",
            "Captures a real camera snapshot artifact when the camera endpoint responds.",
        ),
        _contract(
            "autopilot.guardrails.refresh",
            "Refresh Autopilot guardrails",
            "autopilot",
            "ready",
            "read",
            "low",
            "GET /api/autopilot/readiness + /api/autopilot/guardrails",
            "autopilot.guardrails",
            "Shows proof-gated print/action policies.",
        ),
        _contract(
            "design.intake.submit",
            "Submit bounded design job",
            "design",
            "ready" if runtime.get("design_executor") == "ready" else "blocked",
            "artifact",
            "medium",
            "POST /api/design/intake",
            "design.intake",
            "Current bounded design executor can generate the supported parametric template with proof.",
        ),
        _contract(
            "design.toolchain.refresh",
            "Refresh design toolchain",
            "design",
            "ready",
            "read",
            "low",
            "GET /api/design/toolchain/status",
            "design.toolchain",
            "Reads modeler/CAD/source toolchain status and supported templates.",
        ),
        _contract(
            "generation.services.refresh",
            "Refresh 3D generation services",
            "gen3d",
            "ready",
            "read",
            "low",
            "GET /api/generation/services",
            "generation.services",
            "Reads provider/service setup state for 3D generation.",
        ),
        _contract(
            "generation.run.submit",
            "Submit bounded 3D generation job",
            "gen3d",
            "partial" if runtime.get("generation_provider") == "partial" else "ready",
            "artifact",
            "medium",
            "POST /api/generation/run",
            "generation.run",
            "Local calibration-cube generation is live; arbitrary external provider generation remains setup-gated.",
        ),
        _contract(
            "jobs.list.refresh",
            "Refresh jobs",
            "jobs",
            "ready",
            "read",
            "low",
            "GET /api/jobs",
            "jobs.list",
            "Reads current print/modeling job rows.",
        ),
        _contract(
            "jobs.transition",
            "Run job repair/retry/rollback transitions",
            "jobs",
            "ready",
            "mutate",
            "high",
            "POST /api/jobs/{job_id}/...",
            "jobs.transition",
            "Existing transition routes append proof and enforce backend transition state.",
        ),
        _contract(
            "artifacts.list.refresh",
            "Refresh artifacts",
            "artifacts",
            "ready",
            "read",
            "low",
            "GET /api/artifacts",
            "artifacts.list",
            "Reads proof/artifact rows for agent context.",
        ),
        _contract(
            "approvals.list.refresh",
            "Refresh approvals",
            "approvals",
            "ready",
            "read",
            "low",
            "GET /api/approvals",
            "approvals.list",
            "Reads pending approval rows before any decision action.",
        ),
        _contract(
            "approvals.decide",
            "Approve or reject pending approvals",
            "approvals",
            "ready",
            "mutate",
            "high",
            "POST /api/approvals/{id}/approve|reject",
            "approvals.decide",
            "Agents may request approval decisions; operator/user policy decides risky approvals.",
        ),
        _contract(
            "plugins.list.refresh",
            "Refresh plugins",
            "plugins",
            "ready",
            "read",
            "low",
            "GET /api/plugins",
            "plugins.list",
            "Reads plugin configuration/readiness state.",
        ),
        _contract(
            "notifications.list.refresh",
            "Refresh notifications",
            "notifications",
            "ready",
            "read",
            "low",
            "GET /api/notifications",
            "notifications.list",
            "Reads the live notification inbox.",
        ),
        _contract(
            "proof.bundles.refresh",
            "Refresh proof bundles",
            "proof",
            "ready",
            "read",
            "low",
            "GET /api/proof/bundles",
            "proof.bundles",
            "Reads latest proof bundles and file metadata.",
        ),
        _contract(
            "workflows.list.refresh",
            "Refresh workflows",
            "workflows",
            "ready",
            "read",
            "low",
            "GET /api/workflows",
            "workflows.list",
            "Reads workflow rows for agent planning context.",
        ),
        _contract(
            "voice.catalog.refresh",
            "Refresh Azure voice catalog",
            "voice",
            "ready" if runtime.get("azure_speech") == "ready" else "blocked",
            "read",
            "low",
            "GET /api/voice/voices",
            "voice.catalog",
            "Reads available Azure voices without exposing Azure credentials.",
        ),
        _contract(
            "voice.agents.refresh",
            "Refresh agent voice assignments",
            "voice",
            "ready",
            "read",
            "low",
            "GET /api/voice/agents",
            "voice.agents",
            "Reads per-agent voice assignment rows.",
        ),
        _contract(
            "voice.preview",
            "Preview Azure agent voice",
            "voice",
            "ready" if runtime.get("azure_speech") == "ready" else "blocked",
            "artifact",
            "low",
            "POST /api/voice/preview",
            "voice.preview",
            "Uses backend-only Azure Speech credentials and proof.",
        ),
        _contract(
            "voice.stt",
            "Transcribe voice note",
            "voice",
            "ready" if runtime.get("azure_speech") == "ready" else "blocked",
            "artifact",
            "low",
            "POST /api/voice/stt",
            "voice.stt",
            "Uses backend-only Azure Speech credentials and proof.",
        ),
        _contract(
            "roadmap.operator_coverage.refresh",
            "Refresh operator coverage truth",
            "roadmap",
            "ready",
            "read",
            "low",
            "GET /api/roadmap/tab-completion",
            "roadmap.operator_coverage",
            "Returns the live operator action contract summary.",
        ),
    ]
    _ACTION_CONTRACT_CACHE["contracts"] = [dict(contract) for contract in contracts]
    _ACTION_CONTRACT_CACHE["ts"] = time.monotonic()
    return contracts


def _contract(
    action_id: str,
    label: str,
    tab: str,
    status: str,
    kind: str,
    risk: str,
    route: str,
    handler: str | None,
    summary: str,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "tab": tab,
        "status": status,
        "kind": kind,
        "risk": risk,
        "route": route,
        "handler": handler,
        "agent_callable": bool(handler),
        "proof_required": True,
        "approval_required": risk in {"high", "critical"},
        "rollback_required": kind == "mutate" and risk in {"high", "critical"},
        "summary": summary,
        "blocked_reason": blocked_reason,
        "payload_schema": _contract_payload_schema(action_id),
    }


def _public_action_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in contract.items() if key != "handler"}


def _contract_payload_schema(action_id: str) -> dict[str, Any]:
    schemas: dict[str, dict[str, Any]] = {
        "agents.playwright.observe": {
            "required": [],
            "optional": {"persona_id": "agent persona id; defaults to Oliver QA Agent"},
        },
        "agents.playwright.smoke": {
            "required": [],
            "optional": {"persona_id": "agent persona id; defaults to Oliver QA Agent"},
        },
        "agents.playwright.full": {
            "required": [],
            "optional": {"persona_id": "agent persona id; defaults to Oliver QA Agent"},
        },
        "source.modules.refresh": {
            "required": [],
            "optional": {"section": "source registry section id"},
        },
        "source.update_readiness.refresh": {
            "required": [],
            "optional": {
                "section": "source registry section id",
                "deep": "boolean non-mutating deep check",
            },
        },
        "source.runtime_gaps.refresh": {
            "required": [],
            "optional": {"section": "source registry section id"},
        },
        "source.runner_contracts.refresh": {
            "required": [],
            "optional": {"section": "source registry section id"},
            "safety": "Read-only contract matrix; does not run setup, install, update, or launch commands.",
        },
        "source.runner_contract.refresh": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Read-only single-module contract; no source or runtime mutation.",
        },
        "source.read_only_runner.smoke": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Reruns only registered package/import/local API verifier proof and appends evidence; no setup, install, update, launch, output writes, or printer actions.",
        },
        "source.executable_path_runner.smoke": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Reads only configured executable file metadata/hash and appends evidence; no app launch, setup, install, update, output writes, or printer actions.",
        },
        "source.python_import_repair.preflight": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Reads only failed Python import proof plus local source/dependency metadata and appends evidence; no package install, environment creation, worker start, output writes, or printer actions.",
        },
        "source.cli_install_config.preflight": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Reads only Slic3r/SuperSlicer source, adapter schema, profile/config, and candidate executable metadata; no install, launch, slicing, output writes, updates, or printer actions.",
        },
        "source.npm_package.preflight": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Reads only package.json metadata, script names, lockfile/manifests, and local node/npm executable presence; no npm install, npm run, process start, output writes, updates, or printer actions.",
        },
        "source.service_runner.start": {
            "required": ["module_id"],
            "optional": {
                "execute": "boolean; false writes a preflight proof only, true attempts supervised local start"
            },
            "safety": "No arbitrary command input is accepted. Only registered service/web rows with local/private URL, source checkout, available command, and post-start health proof may start.",
        },
        "source.service_runner.stop": {
            "required": ["module_id"],
            "optional": {},
            "safety": "Stops only PIDs previously started and tracked by the Source OS supervisor.",
        },
        "printers.upload_start": {
            "required": ["printer_id", "gcode_path"],
            "optional": {
                "job_id": "required by backend when start=true",
                "start": "boolean; still requires approvals/truth gates",
                "remote_subdir": "Moonraker upload subdirectory, defaults to hermes3d",
            },
            "safety": "S1 aliases and 192.168.0.12 return HTTP 423 before upload/start.",
        },
        "observe.capture_evidence": {
            "required": ["printer_id"],
            "optional": {},
            "safety": "Captures a camera snapshot artifact only; no printer movement.",
        },
        "design.intake.submit": {
            "required": [],
            "optional": {
                "prompt": "bounded supported design prompt",
                "constraints": "desk_organizer parameter object",
            },
        },
        "generation.run.submit": {
            "required": [],
            "optional": {
                "prompt": "calibration cube prompt unless external providers are configured",
                "seed": "integer",
                "constraints": "size_mm etc.",
            },
        },
        "jobs.transition": {
            "required": ["job_id", "transition"],
            "optional": {
                "reason": "operator/agent reason",
                "target_artifact_id": "required for rollback",
            },
            "allowed_transition": ["cancel", "repair_propose", "repair_apply", "retry", "rollback"],
        },
        "approvals.decide": {
            "required": ["approval_id", "decision"],
            "optional": {"notes": "approval notes or rejection reason"},
            "allowed_decision": ["approve", "reject"],
        },
        "voice.catalog.refresh": {
            "required": [],
            "optional": {"locale": "Azure voice locale prefix, defaults to en"},
        },
        "voice.preview": {
            "required": [],
            "optional": {
                "agent_id": "agent id",
                "voice": "Azure short name",
                "text": "preview text",
                "rate": "0.5-2.0",
                "pitch_pct": "-50..50",
            },
        },
        "voice.stt": {
            "required": ["artifact_id"],
            "optional": {"locale": "speech locale, defaults to en-US"},
            "safety": "Reads an existing audio artifact; no secret values are returned.",
        },
        "code.teams.assign_task": {
            "required": ["team_id", "task_id", "title", "files", "objective"],
            "optional": {"target_branch": "safe git ref", "review_required": "defaults true"},
            "safety": "Team id must be minimax-builders, deepseek-reviewers, or dual; selected source/provider/MCP prerequisites must be ready before assignment is accepted.",
        },
        "code.teams.request_review": {
            "required": ["task_id", "summary", "files", "proof_ids"],
            "optional": {"reviewer_team_id": "defaults to deepseek-reviewers"},
            "safety": "Review requests require at least one proof/evidence id and route through the proof ledger; no provider secret values are returned.",
        },
        "code.providers.smoke": {
            "required": ["provider_id", "task_id"],
            "optional": {},
            "safety": "Provider id must be minimax or deepseek. The smoke call uses private env only server-side, redacts auth failures, and appends MCP evidence.",
        },
        "code.teams.run_coding_pass": {
            "required": ["task_id", "title", "files", "objective"],
            "optional": {
                "team_id": "defaults to minimax-builders; dual is accepted",
                "target_branch": "safe git ref",
            },
            "safety": "Creates a provider-backed planning artifact only; no source mutation happens without later patch proposal, MCP lock, snapshot, gate, and PR actions.",
        },
        "code.teams.run_review_pass": {
            "required": ["task_id", "summary", "files", "proof_ids"],
            "optional": {"reviewer_team_id": "defaults to deepseek-reviewers; dual is accepted"},
            "safety": "Creates a provider-backed review artifact only; it requires proof ids and never claims tests passed unless proof is supplied.",
        },
        "code.e2e.run": {
            "required": ["task_id", "title", "files", "objective"],
            "optional": {
                "target_branch": "safe git ref",
                "role_chain": "finder/builder/reviewer/tester role list",
                "cli_worker": "opencode or openhands preflight only",
                "release_on_finish": "defaults true",
            },
            "safety": "Runs folder-index context, task claim, same-owner file locks, pre-snapshots, MiniMax coding pass, and DeepSeek review pass. It records proof and returns reviewed planning artifacts; source mutation remains blocked until a separate patch proposal/apply/gate/PR workflow.",
        },
        "code.history.snapshot": {
            "required": ["relative_path"],
            "optional": {
                "action_id": "agent action identifier",
                "reason": "why this snapshot is needed",
            },
            "safety": "Project-relative source files only; secrets, binary/generated files, .git, node_modules, and printer config writes are blocked.",
        },
        "code.repo.tree.refresh": {
            "required": [],
            "optional": {
                "root": "project-relative directory or file; defaults to repository root",
                "limit": "1-1200 returned paths",
            },
            "safety": "Secrets, generated output, caches, node_modules, and VCS internals are excluded.",
        },
        "code.repo.search": {
            "required": ["pattern"],
            "optional": {"root": "project-relative search root", "max_results": "1-200"},
            "safety": "Bounded ripgrep only; absolute paths, parent traversal, secrets, and generated folders are blocked.",
        },
        "code.file.read": {
            "required": ["relative_path"],
            "optional": {"start_line": "1-based start line", "line_count": "1-240"},
            "safety": "Text file slices only; secrets, binaries, generated files, .git, node_modules, and printer config writes are blocked.",
        },
        "code.patch.propose": {
            "required": ["relative_path", "proposed_text"],
            "optional": {
                "base_sha256": "current file hash for stale-write protection",
                "reason": "why this patch is proposed",
            },
            "safety": "Creates a review artifact and proof only; it does not mutate source files. Apply remains a separate gated action.",
        },
        "code.patch.apply": {
            "required": ["proposal_id", "task_id"],
            "optional": {"reason": "why this proposal is being applied"},
            "safety": "Requires matching base sha256, active same-owner Hermes MCP file lock, pre/post snapshots, proof event, and chained MCP evidence.",
        },
        "code.patch.apply_reviewed": {
            "required": ["proposal_id", "task_id", "review_proof_ids"],
            "optional": {"reason": "why this reviewed proposal is being applied"},
            "safety": "Requires at least one review proof id in addition to the same base sha256, active same-owner lock, snapshots, proof event, and chained evidence required by patch apply.",
        },
        "code.gate.run": {
            "required": ["gate_id"],
            "optional": {"cwd": "project-relative directory; defaults to repository root"},
            "safety": "Calls hermes3d-locks hermes_run_gate only. Arbitrary commands and cwd outside the edit workspace are blocked.",
        },
        "code.git.branch": {
            "required": ["task_id", "branch_name"],
            "optional": {"base_ref": "safe git ref", "reason": "why this branch is needed"},
            "safety": "Only codex/ and hermes-agent/ branch prefixes are accepted; worktree must be clean.",
        },
        "code.git.stage_owned": {
            "required": ["task_id", "files"],
            "optional": {},
            "safety": "Every file must be changed, snapshotted by the same agent, source-allowed, and locked by the same owner/task.",
        },
        "code.git.commit_owned": {
            "required": ["task_id", "files", "message"],
            "optional": {"proof_ids": "list of proof/evidence ids to embed"},
            "safety": "Commits only staged files from the owned snapshot/lock set.",
        },
        "code.git.push": {
            "required": ["task_id"],
            "optional": {"remote": "origin only"},
            "safety": "No force push; current branch must use codex/ or hermes-agent/ prefix and worktree must be clean.",
        },
        "code.git.pr": {
            "required": ["task_id", "base_ref", "title"],
            "optional": {"body": "PR body", "draft": "defaults true"},
            "safety": "Uses gh pr create only for the current safe agent branch.",
        },
        "code.mcp_locks.claim_task": {
            "required": ["task_id"],
            "optional": {
                "title": "short task title",
                "files": "project-relative paths",
                "reason": "why the task is claimed",
            },
            "safety": "Uses hermes_claim_task in the exact edit workspace.",
        },
        "code.mcp_locks.lock_files": {
            "required": ["files", "task_id"],
            "optional": {"ttl_minutes": "5-720", "reason": "why files are locked"},
            "safety": "Uses hermes_lock_files only after a claimed task id is provided; secrets, denied paths, and outside-workspace paths fail closed.",
        },
        "code.mcp_locks.heartbeat": {
            "required": ["task_id"],
            "optional": {},
            "safety": "Uses hermes_heartbeat only for the server-side actor that owns the claimed task.",
        },
        "code.mcp_locks.evidence": {
            "required": ["task_id", "summary"],
            "optional": {"kind": "proof", "data": "JSON object"},
            "safety": "Uses hermes_append_evidence with bounded summary/kind for the server-side actor that owns the claimed task.",
        },
        "code.mcp_locks.release_files": {
            "required": ["files"],
            "optional": {"note": "release note"},
            "safety": "Uses hermes_release_files only.",
        },
        "code.mcp_locks.release_task": {
            "required": ["task_id"],
            "optional": {"note": "release note"},
            "safety": "Uses hermes_release_task only.",
        },
    }
    return schemas.get(action_id, {"required": [], "optional": {}})


def _source_action_counts() -> dict[str, int]:
    completion = _read_json(SOURCE_COMPLETION_PATH)
    cli_readiness = _read_json(SOURCE_CLI_READINESS_PATH)
    cli_surface = _read_json(SOURCE_CLI_SURFACE_PATH)
    if completion:
        queue_counts = completion.get("runtime_setup_queue", {}).get("counts", {})
        readiness_summary = cli_readiness.get("summary", {})
        surface_summary = cli_surface.get("summary", {})
        nested_surface_summary = cli_surface.get("cli_surface", {}).get("summary", {})
        return {
            "runtime_ready": int(
                queue_counts.get("runtime_ready")
                or completion.get("completion", {}).get("runtime_ready")
                or 0
            ),
            "runner_gaps": int(
                queue_counts.get("runner_not_registered")
                or readiness_summary.get("runner_gaps")
                or completion.get("completion", {}).get("remaining_runner_gap")
                or 0
            ),
            "verified_agent_cli": int(
                readiness_summary.get("verified_agent_cli")
                or nested_surface_summary.get("agent_enabled_cli")
                or surface_summary.get("agent_enabled_cli")
                or 0
            ),
            "cli_candidates": int(
                surface_summary.get("candidate_needs_verifier")
                or nested_surface_summary.get("candidate_needs_verifier")
                or 0
            ),
            "read_only_runner_available": int(
                readiness_summary.get("read_only_runner_available") or 0
            ),
            "executable_path_runner_available": int(
                readiness_summary.get("executable_path_runner_available") or 0
            ),
            "python_import_repair_available": int(
                readiness_summary.get("python_import_repair_available") or 0
            ),
            "cli_install_config_available": int(
                readiness_summary.get("cli_install_config_available") or 0
            ),
            "npm_package_preflight_available": int(
                readiness_summary.get("npm_package_preflight_available") or 0
            ),
        }
    try:
        from hermes3d.api.routes import modules as modules_route

        queue = modules_route.module_runtime_setup_queue_status()
        cli = modules_route.module_agent_cli_readiness()
        surface = modules_route.module_cli_surface_audit()
        counts = queue.get("counts") or {}
        return {
            "runtime_ready": int(counts.get("runtime_ready") or 0),
            "runner_gaps": int(counts.get("runner_not_registered") or cli.get("runner_gaps") or 0),
            "verified_agent_cli": int(cli.get("verified_agent_cli") or 0),
            "cli_candidates": int(
                (surface.get("summary") or {}).get("candidate_needs_verifier") or 0
            ),
            "read_only_runner_available": int(cli.get("read_only_runner_available") or 0),
            "executable_path_runner_available": int(
                cli.get("executable_path_runner_available") or 0
            ),
            "python_import_repair_available": int(cli.get("python_import_repair_available") or 0),
            "cli_install_config_available": int(cli.get("cli_install_config_available") or 0),
            "npm_package_preflight_available": int(cli.get("npm_package_preflight_available") or 0),
        }
    except Exception:
        return {
            "runtime_ready": 0,
            "runner_gaps": 0,
            "verified_agent_cli": 0,
            "cli_candidates": 0,
            "read_only_runner_available": 0,
            "executable_path_runner_available": 0,
            "python_import_repair_available": 0,
            "cli_install_config_available": 0,
            "npm_package_preflight_available": 0,
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _runtime_action_counts() -> dict[str, str]:
    try:
        from hermes3d.api.routes import system as system_route

        payload = system_route.runtime_readiness()
        runtimes = payload.get("runtimes") if isinstance(payload, dict) else []
        return {
            str(item.get("id")): str(item.get("status"))
            for item in runtimes
            if isinstance(item, dict)
        }
    except Exception:
        return {}


def _idle_action_counts() -> dict[str, str]:
    try:
        from hermes3d.api.routes import learning as learning_route

        payload = learning_route.idle_workbench()
        capabilities = (
            ((payload.get("automation") or {}).get("capabilities") or [])
            if isinstance(payload, dict)
            else []
        )
        return {
            str(item.get("kind")): str(item.get("execution_status"))
            for item in capabilities
            if isinstance(item, dict)
        }
    except Exception:
        return {}


def _result_status(result: Any) -> str:
    if isinstance(result, dict):
        return str(
            result.get("status") or result.get("state") or result.get("accepted") or "returned"
        )
    return "returned"


def _required_payload_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise HTTPException(
            status_code=422, detail={"reason": f"{key} is required for this Hermes Agent action."}
        )
    return value


def _content_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return "audio/wav"
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".m4a":
        return "audio/mp4"
    if suffix == ".ogg":
        return "audio/ogg"
    if suffix == ".flac":
        return "audio/flac"
    if suffix == ".webm":
        return "audio/webm"
    return "application/octet-stream"


def _proof_safe_result(result: Any) -> Any:
    encoded = json.dumps(result, default=str, sort_keys=True)
    if len(encoded) <= 12000:
        return result
    return {
        "truncated": True,
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "bytes": len(encoded),
    }


def _playwright_scopes() -> set[str]:
    return {"observe", "smoke", "full"}


def _playwright_command(scope: str) -> list[str] | None:
    npx = "npx.cmd" if os.name == "nt" else "npx"
    base = [npx, "playwright", "test", "--config=playwright.e2e.config.ts"]
    if scope == "observe":
        return [*base, "--grep", "Observe renders live camera|hash route sync"]
    if scope == "smoke":
        return [*base, "--grep", "all left-rail primary tabs|hash route sync|agent chat"]
    if scope == "full":
        return base
    return None


def _store_playwright_artifact(
    persona_id: str,
    scope: str,
    status: str,
    started_at: str,
    duration_ms: int,
    exit_code: int | None,
    command: list[str],
    stdout: str,
    stderr: str,
) -> str:
    artifact_id = new_id()
    storage = DB_PATH.parent / "agent_test_runs"
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / f"{artifact_id}_playwright_{scope}.json"
    payload = {
        "id": artifact_id,
        "agent": persona_id,
        "scope": scope,
        "status": status,
        "started_at": started_at,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "command_label": _command_label(command),
        "stdout": _redact(stdout)[-20000:],
        "stderr": _redact(stderr)[-20000:],
        "ts_utc": utc_now(),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, NULL, 'agent_playwright_run', ?, 'AGENT_QA', ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            persona_id,
            scope,
            f"Playwright {scope} proof: {status}",
            str(target),
            target.stat().st_size,
            as_json({"status": status, "exit_code": exit_code, "duration_ms": duration_ms}),
        ),
    )
    return artifact_id


def _append_agent_proof(event_type: str, persona_id: str, payload: dict) -> str:
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (proof_event_id, event_type, persona_id, as_json({**payload, "ts_utc": utc_now()})),
    )
    return proof_event_id


def _command_label(command: list[str]) -> str:
    return " ".join(command)


# ---------------------------------------------------------------------------
# W18-A19 — live MiniMax + DeepSeek provider routing.
#
# Operator verdict criteria (2026-05-11): GUI_AGENT_WORKFLOW_GREEN final
# PASS_REAL requires at least one *live* MiniMax/DeepSeek backed assistive
# task. LM Studio / Ollama are local fallback only.
#
# Role mapping (cf. PR body W18-A19 routing table):
#   builder   -> minimax     (implementation / refactor proposals)
#   reviewer  -> deepseek    (verification / regression review)
#   fallback  -> lm_studio   (dev/local fallback; never primary)
#   fallback  -> ollama      (dev/local fallback; never primary)
#
# Hard rules enforced in this section:
#   * NO API key values are logged / echoed / persisted. Only `key_present`
#     booleans and per-call metadata (status, latency, model, sha) ever leave
#     this module.
#   * Smallest-possible live smoke = 1-token completion. Assistive tasks cap
#     at 200 tokens to bound cost (estimate well under $0.001 per call).
# ---------------------------------------------------------------------------

PROVIDER_ROLE_MAP: dict[str, str] = {
    # Primary live providers (count toward GUI_AGENT_WORKFLOW_GREEN PASS_REAL).
    "minimax": "builder",
    "deepseek": "reviewer",
    # Local fallback only — never primary, never proof-bearing for the GREEN
    # verdict on their own.
    "lm_studio": "fallback",
    "ollama": "fallback",
    # Test fixture (offline).
    "openai-fixture": "fixture",
}

PROVIDER_ROLE_DESCRIPTION: dict[str, str] = {
    "builder": "Implementation / refactor proposals (MiniMax).",
    "reviewer": "Verification / regression review (DeepSeek).",
    "fallback": "Local dev fallback only (LM Studio / Ollama).",
    "fixture": "Offline test fixture.",
}


def _resolve_provider_key(provider_id: str) -> str | None:
    """Resolve a provider API key from env without ever logging the value."""
    chains: dict[str, tuple[str, ...]] = {
        "minimax": (
            "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY",
            "MINIMAX_TOKEN_PLAN_API_KEY",
            "HERMES3D_MINIMAX_HIGHSPEED_API_KEY",
            "MINIMAX_HIGHSPEED_API_KEY",
            "HERMES3D_MINIMAX_API_KEY",
            "MINIMAX_API_KEY",
        ),
        "deepseek": (
            "HERMES3D_DEEPSEEK_API_KEY",
            "DEEPSEEK_API_KEY",
        ),
    }
    for name in chains.get(provider_id, ()):
        value = os.environ.get(name)
        if value:
            return value
    return None


def _provider_endpoint(provider_id: str) -> tuple[str, str]:
    """Return (base_url, model) for a provider, env-overrideable."""
    if provider_id == "minimax":
        base = (
            os.environ.get("HERMES3D_MINIMAX_BASE_URL")
            or os.environ.get("MINIMAX_BASE_URL")
            or "https://api.minimax.io/v1"
        )
        model = (
            os.environ.get("HERMES3D_MINIMAX_MODEL")
            or os.environ.get("MINIMAX_MODEL")
            or "MiniMax-M2"
        )
        return base, model
    if provider_id == "deepseek":
        base = (
            os.environ.get("HERMES3D_DEEPSEEK_BASE_URL")
            or os.environ.get("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com/v1"
        )
        model = (
            os.environ.get("HERMES3D_DEEPSEEK_MODEL")
            or os.environ.get("DEEPSEEK_MODEL")
            or "deepseek-chat"
        )
        return base, model
    raise ValueError(f"unsupported provider_id: {provider_id}")


def _provider_call(
    provider_id: str,
    *,
    prompt: str,
    max_tokens: int,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Perform a single chat-completion HTTP call to a remote provider.

    Returns a metadata-only dict. NEVER contains the API key. The raw
    response body is sha256-hashed for proof, never persisted verbatim
    (defense against accidental secret-in-body leaks).
    """
    if provider_id not in ("minimax", "deepseek"):
        raise ValueError(f"unsupported provider_id: {provider_id}")
    key = _resolve_provider_key(provider_id)
    if not key:
        return {
            "provider_id": provider_id,
            "status": "FAIL_KEY_MISSING",
            "http_status": None,
            "latency_ms": 0,
            "key_present": False,
        }
    base_url, model = _provider_endpoint(provider_id)
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    started = time.monotonic_ns()
    text = ""
    status = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            text = ""
    except urllib.error.URLError as exc:
        status = 0
        text = f"URLError reason={type(exc).__name__}"
    latency_ms = int((time.monotonic_ns() - started) // 1_000_000)
    body_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    parsed_meta: dict[str, Any] = {}
    completion_text: str | None = None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed_meta["model"] = parsed.get("model")
            usage = parsed.get("usage")
            if isinstance(usage, dict):
                parsed_meta["tokens_in"] = usage.get("prompt_tokens")
                parsed_meta["tokens_out"] = usage.get("completion_tokens")
            choices = parsed.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, dict):
                        c = msg.get("content")
                        if isinstance(c, str) and c.strip():
                            completion_text = c
                        else:
                            # DeepSeek thinking models surface reasoning in a
                            # parallel ``reasoning_content`` field when the
                            # token budget is consumed by reasoning before
                            # the final answer streams. Fall back to it so
                            # we have *something* to persist + verify.
                            rc = msg.get("reasoning_content")
                            if isinstance(rc, str) and rc.strip():
                                completion_text = rc
            err = parsed.get("error")
            if isinstance(err, dict):
                parsed_meta["error_code"] = err.get("code") or err.get("type")
    except (json.JSONDecodeError, TypeError):
        pass
    if 200 <= status < 300:
        verdict = "PASS_LIVE"
    elif status == 0:
        verdict = "FAIL_NETWORK"
    elif status in (401, 403):
        verdict = "FAIL_AUTH"
    elif status == 429:
        verdict = "FAIL_RATE_LIMIT"
    elif 400 <= status < 500:
        verdict = "FAIL_REQUEST"
    else:
        verdict = "FAIL_UPSTREAM"
    return {
        "provider_id": provider_id,
        "status": verdict,
        "http_status": status,
        "latency_ms": latency_ms,
        "model": parsed_meta.get("model") or model,
        "tokens_in": parsed_meta.get("tokens_in"),
        "tokens_out": parsed_meta.get("tokens_out"),
        "body_sha256": body_sha,
        "body_size_bytes": len(text.encode("utf-8")),
        "error_code": parsed_meta.get("error_code"),
        "key_present": True,
        # `completion_text` is returned to the caller (assistive task path)
        # but NOT persisted by the smoke endpoint.
        "completion_text": completion_text,
    }


@router.post("/api/agents/providers/smoke")
def provider_smoke(body: dict | None = None) -> dict:
    """Run a 1-token live smoke against MiniMax and/or DeepSeek.

    Body (optional):
      {"providers": ["minimax", "deepseek"]}  # default: both

    Response shape (NEVER includes API keys):
      {
        "task_id": "...",
        "timestamp_utc": "...",
        "providers": {
          "minimax":  {"status", "http_status", "latency_ms", "model", ...},
          "deepseek": {"status", "http_status", "latency_ms", "model", ...}
        }
      }
    """
    requested = (body or {}).get("providers") if isinstance(body, dict) else None
    if not isinstance(requested, list) or not requested:
        requested = ["minimax", "deepseek"]
    out: dict[str, Any] = {
        "task_id": "W18-A19-PROVIDER-LIVE-SMOKE",
        "timestamp_utc": utc_now(),
        "providers": {},
    }
    for pid in requested:
        pid_norm = str(pid).strip().lower()
        if pid_norm not in ("minimax", "deepseek"):
            out["providers"][pid_norm] = {
                "status": "FAIL_UNSUPPORTED",
                "http_status": None,
                "latency_ms": 0,
            }
            continue
        result = _provider_call(pid_norm, prompt="1", max_tokens=1, timeout=20.0)
        # The smoke endpoint NEVER stores the completion text. Strip it.
        result.pop("completion_text", None)
        result["role"] = PROVIDER_ROLE_MAP.get(pid_norm, "unknown")
        out["providers"][pid_norm] = result
        # Persist proof event for the smoke (key-free, sha-only).
        _append_provider_proof_event("provider_smoke", pid_norm, result)
    return out


@router.post("/api/agents/providers/assist")
def provider_assist(body: dict) -> dict:
    """Submit an assistive task to a specific live provider.

    Body:
      {
        "provider": "minimax" | "deepseek",
        "prompt": "...",
        "role": "builder" | "reviewer",   # optional, derived from provider
        "max_tokens": 200                   # optional, default 200
      }

    Persists the request + response into ``agent_conversations`` with the
    provider tag (in the ``message_type`` column as ``ASSIST:<provider>``)
    and records a ``proof_events`` row tagged with the provider.

    NEVER stores the API key. The completion text itself is stored (this is
    the whole point of an assistive task) but the Authorization header is
    not.
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail={"status": "bad_request"})
    provider = str(body.get("provider", "")).strip().lower()
    if provider not in ("minimax", "deepseek"):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "unsupported_provider",
                "reason": f"provider must be 'minimax' or 'deepseek', got {provider!r}",
            },
        )
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail={"status": "bad_request", "reason": "prompt is required"},
        )
    max_tokens_raw = body.get("max_tokens", 200)
    try:
        max_tokens = max(1, min(int(max_tokens_raw), 1024))
    except (TypeError, ValueError):
        max_tokens = 200
    role = PROVIDER_ROLE_MAP.get(provider, "builder")
    persona = "modeling-agent" if role == "builder" else "oliver-qa-agent"
    result = _provider_call(provider, prompt=prompt, max_tokens=max_tokens, timeout=45.0)
    completion = result.pop("completion_text", None)
    # Persist user prompt + provider reply into agent_conversations. We tag
    # the row by stuffing provider info into message_type so downstream
    # queries can filter without a schema migration.
    user_msg_id = new_id()
    assistant_msg_id = new_id()
    execute(
        "INSERT INTO agent_conversations (id, persona_id, role, message_type, content) "
        "VALUES (?, ?, 'user', ?, ?)",
        (user_msg_id, persona, f"ASSIST_REQ:{provider}", prompt),
    )
    persisted_text = completion if isinstance(completion, str) and completion else ""
    if not persisted_text:
        persisted_text = json.dumps(
            {
                "status": result.get("status"),
                "http_status": result.get("http_status"),
                "error_code": result.get("error_code"),
                "note": "no completion text returned",
            },
            sort_keys=True,
        )
    execute(
        "INSERT INTO agent_conversations (id, persona_id, role, message_type, content) "
        "VALUES (?, ?, 'assistant', ?, ?)",
        (assistant_msg_id, persona, f"ASSIST_REPLY:{provider}", persisted_text),
    )
    proof_payload = dict(result)
    proof_payload["user_msg_id"] = user_msg_id
    proof_payload["assistant_msg_id"] = assistant_msg_id
    proof_payload["persona"] = persona
    proof_payload["role"] = role
    proof_event_id = _append_provider_proof_event("provider_assist", provider, proof_payload)
    return {
        "status": result.get("status"),
        "provider": provider,
        "role": role,
        "persona": persona,
        "model": result.get("model"),
        "http_status": result.get("http_status"),
        "latency_ms": result.get("latency_ms"),
        "tokens_in": result.get("tokens_in"),
        "tokens_out": result.get("tokens_out"),
        "user_msg_id": user_msg_id,
        "assistant_msg_id": assistant_msg_id,
        "proof_event_id": proof_event_id,
        "completion": completion if isinstance(completion, str) else None,
    }


def _append_provider_proof_event(
    event_type: str,
    provider_id: str,
    payload: dict[str, Any],
) -> str:
    """Insert a proof_events row tagged with the provider.

    Strips any field whose name looks key-like; we never write them, but
    defense in depth.
    """
    safe = {
        k: v
        for k, v in payload.items()
        if not (
            "api_key" in k.lower() or k.lower() == "authorization" or k.lower().endswith("_token")
        )
    }
    safe["provider"] = provider_id
    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (event_id, event_type, f"provider:{provider_id}", json.dumps(safe, sort_keys=True)),
    )
    return event_id


@router.get("/api/agents/health")
def health() -> dict:
    probe = runtime_probe()
    runtime_configured = bool(probe["ready"])
    # W18-A19 — surface per-provider smoke state on the health endpoint so
    # the GUI + Playwright proof can read it. We do a *light* presence check
    # only (key_present + role); the actual live smoke must be triggered via
    # POST /api/agents/providers/smoke to keep this endpoint cheap.
    providers: dict[str, dict[str, Any]] = {}
    for pid in ("minimax", "deepseek", "lm_studio", "ollama"):
        if pid in ("minimax", "deepseek"):
            key_present = bool(_resolve_provider_key(pid))
            base, model = _provider_endpoint(pid) if pid in ("minimax", "deepseek") else ("", "")
            providers[pid] = {
                "role": PROVIDER_ROLE_MAP.get(pid, "unknown"),
                "role_description": PROVIDER_ROLE_DESCRIPTION.get(
                    PROVIDER_ROLE_MAP.get(pid, "unknown"),
                    "",
                ),
                "key_present": key_present,
                "model": model,
                "base_url": base,
                "smoke_endpoint": "/api/agents/providers/smoke",
                "kind": "live_remote",
            }
        else:
            providers[pid] = {
                "role": PROVIDER_ROLE_MAP.get(pid, "fallback"),
                "role_description": PROVIDER_ROLE_DESCRIPTION.get("fallback", ""),
                "key_present": True,  # local providers don't require a key
                "kind": "local_fallback",
            }
    return {
        "healthy": runtime_configured,
        "status": "bridge_ready" if runtime_configured else probe["status"],
        "agents": {
            persona: "idle" if runtime_configured else "not_configured" for persona in PERSONAS
        },
        "setup": {
            "env": "HERMES3D_AGENT_RUNTIME_URL",
            "model_env": "HERMES3D_AGENT_RUNTIME_MODEL",
            "model": probe.get("model"),
            "reason": probe.get("reason"),
            "latency_ms": probe.get("latency_ms"),
        },
        "providers": providers,
        "provider_roles": {
            "builder": "minimax",
            "reviewer": "deepseek",
            "fallback": ["lm_studio", "ollama"],
        },
    }


@router.get("/api/agents/config")
def get_config() -> dict:
    """W18-A13 — return the current Hermes Agent operator config.

    The audit (W18-A3) classified ``GET /api/agents/config`` as
    ``FAIL_BROKEN`` because the only handler was PUT-only (405 on GET).
    The Settings → AgentConfigSection in the FE GETs first to populate
    the form, then PUTs on save. With no GET handler the form silently
    rendered empty.

    Shape mirrors :class:`AgentConfigUpdate.config` so the existing PUT
    round-trips: ``{"config": {key: value, ...}, "redacted": ["api_key"]}``.
    The ``api_key`` entry is **never** echoed back; instead we surface a
    boolean ``api_key_configured`` flag plus the redacted marker so the
    UI can render the masked state without ever holding the secret.
    """
    records = rows("SELECT key, value FROM agent_config")
    config: dict[str, Any] = {}
    api_key_configured = False
    for record in records:
        key = record.get("key")
        if not isinstance(key, str) or not key:
            continue
        raw = record.get("value")
        try:
            decoded = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, json.JSONDecodeError):
            decoded = raw
        if key == "api_key":
            api_key_configured = bool(decoded)
            continue
        config[key] = decoded
    return {
        "accepted": True,
        "status": "ready",
        "config": config,
        "api_key_configured": api_key_configured,
        "redacted": ["api_key"],
    }


@router.put("/api/agents/config")
def put_config(body: AgentConfigUpdate) -> dict:
    for key, value in body.config.items():
        if key == "api_key":
            continue
        execute(
            "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, json.dumps(value)),
        )
    return {"saved": True, "redacted": ["api_key"] if "api_key" in body.config else []}


def _trusted_runtime_url() -> str | None:
    return trusted_runtime_url()


def _pending_action(persona_id: str, action_id: str) -> dict:
    action = row(
        "SELECT * FROM agent_autonomous_actions WHERE id = ? AND persona_id = ?",
        (action_id, persona_id),
    )
    if not action:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_found",
                "reason": "No matching Hermes agent action exists for this persona.",
            },
        )
    if action.get("outcome") != "pending":
        raise HTTPException(
            status_code=409,
            detail={
                "status": "not_pending",
                "reason": f"Action outcome is already {action.get('outcome')}.",
            },
        )
    return action


def _require_persona(persona_id: str) -> None:
    if persona_id not in PERSONAS:
        raise HTTPException(
            status_code=404,
            detail={"status": "not_found", "reason": "Hermes agent persona not found."},
        )


def _safe_filename(value: str) -> str:
    name = Path(value.replace("\\", "/")).name.strip()
    name = FILENAME_RE.sub("_", name)
    return name[:180]


def _attachment_context(context: dict) -> list[dict]:
    value = context.get("attachments") if isinstance(context, dict) else None
    if not isinstance(value, list):
        return []
    artifacts: list[dict] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        artifact_id = str(item.get("id") or item.get("artifact_id") or "").strip()
        if not artifact_id:
            continue
        artifact = row(
            "SELECT * FROM artifacts WHERE id = ? AND evidence_type = 'agent_attachment'",
            (artifact_id,),
        )
        if artifact:
            artifacts.append(artifact)
    return artifacts


def _artifact_sha256(artifact: dict) -> str:
    try:
        notes = json.loads(str(artifact.get("notes") or "{}"))
    except json.JSONDecodeError:
        return "unavailable"
    value = notes.get("sha256") if isinstance(notes, dict) else None
    return value if isinstance(value, str) else "unavailable"
