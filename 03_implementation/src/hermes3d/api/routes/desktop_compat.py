from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, utc_now
from hermes3d.services.agent_runtime import (
    chat_completions_url,
    configured_runtime_model,
    runtime_probe,
    runtime_request_body,
    trusted_runtime_url,
)

router = APIRouter()

DEFAULT_MODEL = "hermes3d-desktop-bridge"
DESKTOP_CONTRACT = "fathah/hermes-desktop@v0.3.4"
DEFAULT_CHAT_TIMEOUT_SECONDS = 12.0
SECRET_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|([A-Za-z0-9_]*KEY=)[^\s]+")


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]] = []
    stream: bool = False


@router.get("/health")
def desktop_health() -> dict[str, Any]:
    runtime_url = _runtime_url()
    probe = runtime_probe()
    return {
        "status": "ok" if probe["ready"] else "degraded",
        "service": "hermes3d-desktop-compat",
        "desktop_contract": DESKTOP_CONTRACT,
        "runtime_configured": bool(runtime_url),
        "runtime_ready": bool(probe["ready"]),
        "runtime_model": probe.get("model"),
        "runtime_reason": probe.get("reason"),
        "runtime_url": _redacted_runtime_url(runtime_url),
        "endpoints": {
            "health": "/health",
            "chat": "/v1/chat/completions",
        },
        "ts_utc": utc_now(),
    }


@router.get("/api/desktop/compat")
def desktop_compat_status() -> dict[str, Any]:
    runtime_url = _runtime_url()
    probe = runtime_probe()
    runtime_configured = bool(runtime_url)
    runtime_ready = bool(probe["ready"])
    return {
        "available": runtime_ready,
        "bridge_available": True,
        "agent_runtime_available": runtime_ready,
        "status": "ready" if runtime_ready else probe["status"],
        "desktop_url": f"http://127.0.0.1:{_runtime_port('HERMES3D_DESKTOP_COMPAT_PORT', '8642')}",
        "gui_api_url": f"http://127.0.0.1:{_runtime_port('HERMES3D_GUI_API_PORT', '8765')}",
        "contract": DESKTOP_CONTRACT,
        "health_path": "/health",
        "chat_path": "/v1/chat/completions",
        "streaming": "OpenAI-compatible SSE data frames ending with data: [DONE]",
        "auth": "No bearer token required on localhost by the current Hermes Desktop contract.",
        "runtime_configured": runtime_configured,
        "runtime_model": probe.get("model"),
        "reason": None if runtime_ready else str(probe["reason"]),
    }


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(body: ChatCompletionRequest, response: Response):
    session_id = new_id()
    response.headers["x-hermes-session-id"] = session_id
    _append_desktop_proof("hermes_desktop_chat_request", body, session_id)
    if not _runtime_url():
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_configured",
                "reason": "Hermes Desktop bridge is online, but live Hermes Agent execution is blocked until HERMES3D_AGENT_RUNTIME_URL is configured.",
                "desktop_contract": DESKTOP_CONTRACT,
                "session_id": session_id,
            },
        )

    if body.stream:
        return StreamingResponse(
            _stream_chat_response(body, session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "x-hermes-session-id": session_id,
            },
        )
    content = await _chat_content(body, session_id)
    return {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model or DEFAULT_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


async def _stream_chat_response(body: ChatCompletionRequest, session_id: str) -> AsyncIterator[str]:
    runtime_url = _runtime_url()
    if runtime_url:
        try:
            async for frame in _proxy_runtime_stream(runtime_url, body):
                yield frame
            return
        except Exception as exc:
            yield _sse_delta(body, session_id, f"Hermes3D Desktop bridge could not reach the configured Hermes Agent runtime: {exc}")
            yield "data: [DONE]\n\n"
            return

    content = await _chat_content(body, session_id)
    yield _sse_delta(body, session_id, content)
    yield "data: [DONE]\n\n"


async def _chat_content(body: ChatCompletionRequest, session_id: str) -> str:
    runtime_url = _runtime_url()
    if runtime_url:
        try:
            return await asyncio.to_thread(_proxy_runtime_non_stream, runtime_url, body)
        except Exception as exc:
            return f"Hermes3D Desktop bridge is online, but the configured Hermes Agent runtime is unreachable: {exc}"

    latest = _latest_user_message(body.messages)
    execute(
        """
        INSERT INTO agent_conversations
            (id, persona_id, role, message_type, content)
        VALUES (?, 'desktop-bridge', 'user', 'DESKTOP_CHAT', ?)
        """,
        (new_id(), latest[:4000]),
    )
    content = (
        "Hermes3D Desktop bridge is online on port 8642. "
        "Live Hermes Agent execution is not configured yet; set HERMES3D_AGENT_RUNTIME_URL "
        "to a trusted local Hermes Agent API before this bridge can execute agent tasks."
    )
    execute(
        """
        INSERT INTO agent_conversations
            (id, persona_id, role, message_type, content)
        VALUES (?, 'desktop-bridge', 'assistant', 'STATUS_UPDATE', ?)
        """,
        (session_id, content),
    )
    return content


def _runtime_url() -> str | None:
    return trusted_runtime_url()


def _runtime_port(env_name: str, fallback: str) -> str:
    value = os.environ.get(env_name, fallback).strip()
    return value if value.isdigit() else fallback


def _redacted_runtime_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def _latest_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        return _content_to_text(message.get("content"))
    return ""


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _sse_delta(body: ChatCompletionRequest, session_id: str, content: str) -> str:
    payload = {
        "id": f"chatcmpl-{session_id}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": body.model or DEFAULT_MODEL,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def _proxy_runtime_stream(runtime_url: str, body: ChatCompletionRequest) -> AsyncIterator[str]:
    request_body = json.dumps(runtime_request_body({**body.model_dump(), "stream": True})).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(runtime_url),
        method="POST",
        data=request_body,
        headers={"Content-Type": "application/json", "User-Agent": "Hermes3D-Desktop-Compat/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as upstream:
        while True:
            chunk = await asyncio.to_thread(upstream.readline)
            if not chunk:
                break
            yield chunk.decode("utf-8")


def _proxy_runtime_non_stream(runtime_url: str, body: ChatCompletionRequest) -> str:
    request_body = json.dumps(runtime_request_body({**body.model_dump(), "stream": False})).encode("utf-8")
    request = urllib.request.Request(
        chat_completions_url(runtime_url),
        method="POST",
        data=request_body,
        headers={"Content-Type": "application/json", "User-Agent": "Hermes3D-Desktop-Compat/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_chat_timeout_seconds()) as upstream:
            payload = json.loads(upstream.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _redact(exc.read().decode("utf-8", errors="replace"))[:400]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    content = payload.get("choices", [{}])[0].get("message", {}).get("content")
    if isinstance(content, str):
        return content
    error = payload.get("error", {}).get("message")
    if isinstance(error, str):
        return error
    return "Hermes Agent runtime returned no assistant content."


def _chat_timeout_seconds() -> float:
    raw = os.environ.get("HERMES3D_AGENT_RUNTIME_CHAT_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_CHAT_TIMEOUT_SECONDS
    try:
        return min(max(float(raw), 1.0), 120.0)
    except ValueError:
        return DEFAULT_CHAT_TIMEOUT_SECONDS


def _redact(value: str) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1) or match.group(2) or match.group(3) or ''}[REDACTED]", value)


def _append_desktop_proof(event_type: str, body: ChatCompletionRequest, session_id: str) -> None:
    digest = hashlib.sha256(_latest_user_message(body.messages).encode("utf-8")).hexdigest()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            new_id(),
            event_type,
            "hermes-desktop-compat",
            as_json(
                {
                    "session_id": session_id,
                    "requested_model": body.model or DEFAULT_MODEL,
                    "resolved_model": configured_runtime_model(fallback=body.model or DEFAULT_MODEL),
                    "stream": body.stream,
                    "message_sha256": digest,
                    "runtime_configured": bool(_runtime_url()),
                    "contract": DESKTOP_CONTRACT,
                }
            ),
        ),
    )
