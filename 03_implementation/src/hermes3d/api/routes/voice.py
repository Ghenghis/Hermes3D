from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, rows, utc_now

router = APIRouter()
DEFAULT_PREVIEW_TEXT = "Hello. Hermes3D voice preview is running through the local backend."
DEFAULT_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
REQUEST_TIMEOUT_S = 8.0
STT_REQUEST_TIMEOUT_S = 45.0
MAX_STT_AUDIO_BYTES = 25 * 1024 * 1024
FAST_TRANSCRIPTION_API_VERSION = "2025-10-15"


class VoiceUpdate(BaseModel):
    voice: str


class VoicePreview(BaseModel):
    id: str | None = None
    voice: str
    text: str = DEFAULT_PREVIEW_TEXT
    rate: float = 1.0
    pitch_pct: int = 0


@router.get("/api/voice/agents")
def voice_agents() -> list[dict]:
    return rows("SELECT * FROM voice_assignments ORDER BY agent_name")


@router.put("/api/voice/agents/{agent_id}")
def save_voice(agent_id: str, body: VoiceUpdate) -> dict:
    if not body.voice.strip():
        raise HTTPException(status_code=400, detail="voice must not be empty")
    existing = rows("SELECT agent_id FROM voice_assignments WHERE agent_id = ?", (agent_id,))
    if not existing:
        raise HTTPException(status_code=404, detail=f"voice agent not found: {agent_id}")
    execute("UPDATE voice_assignments SET voice_name = ?, updated_at = datetime('now') WHERE agent_id = ?", (body.voice, agent_id))
    return {"agent_id": agent_id, "voice_name": body.voice, "saved": True}


@router.post("/api/voice/preview")
def preview_voice(body: VoicePreview):
    config = _azure_config()
    if not config["configured"]:
        proof_event_id = _append_voice_proof(
            "voice.tts.blocked",
            {
                "status": "not_configured",
                "agent_id": body.id,
                "voice": body.voice,
                "text_sha256": hashlib.sha256(body.text[:500].encode("utf-8")).hexdigest(),
            },
        )
        return JSONResponse(
            status_code=409,
            content=_blocked("not_configured", "Azure Speech credentials are not configured in the private runtime env.", body.voice, proof_event_id=proof_event_id),
        )
    try:
        token = _azure_issue_token(config)
        audio = _azure_synthesize(config, token, body)
    except urllib.error.HTTPError as exc:
        proof_event_id = _append_voice_proof(
            "voice.tts.failed",
            {
                "status": "azure_error",
                "agent_id": body.id,
                "voice": body.voice,
                "http_status": exc.code,
                "text_sha256": hashlib.sha256(body.text[:500].encode("utf-8")).hexdigest(),
            },
        )
        return JSONResponse(
            status_code=502,
            content=_blocked("azure_error", f"Azure Speech returned HTTP {exc.code}.", body.voice, exc.code, proof_event_id=proof_event_id),
        )
    except OSError as exc:
        proof_event_id = _append_voice_proof(
            "voice.tts.failed",
            {
                "status": "unreachable",
                "agent_id": body.id,
                "voice": body.voice,
                "text_sha256": hashlib.sha256(body.text[:500].encode("utf-8")).hexdigest(),
            },
        )
        return JSONResponse(
            status_code=502,
            content=_blocked("unreachable", f"Azure Speech request failed: {exc}", body.voice, proof_event_id=proof_event_id),
        )
    proof_event_id = _append_voice_proof(
        "voice.tts.synthesized",
        {
            "status": "ready",
            "agent_id": body.id,
            "voice": body.voice,
            "provider": "azure",
            "output_format": DEFAULT_OUTPUT_FORMAT,
            "bytes": len(audio),
            "text_sha256": hashlib.sha256(body.text[:500].encode("utf-8")).hexdigest(),
        },
    )
    return {
        "queued": True,
        "voice": body.voice,
        "status": "ready",
        "mime_type": "audio/mpeg",
        "output_format": DEFAULT_OUTPUT_FORMAT,
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "bytes": len(audio),
        "proof_event_id": proof_event_id,
    }


@router.post("/api/voice/stt")
async def speech_to_text(request: Request) -> dict:
    config = _azure_config()
    locale = _clean_locale(request.query_params.get("locale") or "en-US")
    if not config["configured"]:
        proof_event_id = _append_voice_proof("voice.stt.blocked", {"status": "not_configured", "locale": locale})
        return JSONResponse(
            status_code=409,
            content={
                "accepted": False,
                "configured": False,
                "status": "not_configured",
                "reason": "Azure Speech credentials are not configured in the private runtime env.",
                "proof_event_id": proof_event_id,
            },
        )
    audio = await request.body()
    if not audio:
        proof_event_id = _append_voice_proof("voice.stt.blocked", {"status": "empty_audio", "locale": locale})
        raise HTTPException(status_code=400, detail={"status": "empty_audio", "reason": "Audio body is required.", "proof_event_id": proof_event_id})
    if len(audio) > MAX_STT_AUDIO_BYTES:
        proof_event_id = _append_voice_proof("voice.stt.blocked", {"status": "too_large", "bytes": len(audio), "locale": locale})
        raise HTTPException(status_code=413, detail={"status": "too_large", "reason": f"Audio body exceeds {MAX_STT_AUDIO_BYTES} bytes.", "proof_event_id": proof_event_id})
    content_type = (request.headers.get("content-type") or "application/octet-stream").split(";", 1)[0].strip().lower()
    filename = _safe_filename(request.headers.get("x-hermes-filename") or f"voice-note.{_audio_extension(content_type)}")
    try:
        transcript = await asyncio.to_thread(_azure_fast_transcribe, config, audio, content_type, filename, locale)
    except urllib.error.HTTPError as exc:
        proof_event_id = _append_voice_proof("voice.stt.failed", {"status": "azure_error", "http_status": exc.code, "bytes": len(audio), "locale": locale})
        return JSONResponse(
            status_code=502,
            content={"accepted": False, "configured": True, "status": "azure_error", "http_status": exc.code, "reason": f"Azure Speech fast transcription returned HTTP {exc.code}.", "proof_event_id": proof_event_id},
        )
    except OSError:
        proof_event_id = _append_voice_proof("voice.stt.failed", {"status": "unreachable", "bytes": len(audio), "locale": locale})
        return JSONResponse(
            status_code=502,
            content={"accepted": False, "configured": True, "status": "unreachable", "reason": "Azure Speech fast transcription request failed.", "proof_event_id": proof_event_id},
        )
    except ValueError as exc:
        proof_event_id = _append_voice_proof("voice.stt.failed", {"status": "invalid_response", "bytes": len(audio), "locale": locale})
        return JSONResponse(
            status_code=502,
            content={"accepted": False, "configured": True, "status": "invalid_response", "reason": str(exc), "proof_event_id": proof_event_id},
        )
    proof_event_id = _append_voice_proof(
        "voice.stt.transcribed",
        {
            "status": "ready",
            "bytes": len(audio),
            "locale": locale,
            "provider": "azure_fast_transcription",
            "transcript_sha256": hashlib.sha256(transcript["transcript"].encode("utf-8")).hexdigest(),
            "phrase_count": transcript["phrase_count"],
        },
    )
    return {
        "accepted": True,
        "configured": True,
        "status": "ready",
        "provider": "azure",
        "mode": "fast_transcription",
        "locale": locale,
        "transcript": transcript["transcript"],
        "confidence": transcript["confidence"],
        "duration_ms": transcript["duration_ms"],
        "phrase_count": transcript["phrase_count"],
        "bytes": len(audio),
        "proof_event_id": proof_event_id,
    }


@router.get("/api/voice/transcripts")
def voice_transcripts(limit: int = 50, offset: int = 0) -> list[dict]:
    """Return STT transcript history, newest first."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    raw = rows(
        """
        SELECT id, event_type, source_agent, payload, created_at
        FROM proof_events
        WHERE event_type IN ('voice.stt.transcribed', 'voice.stt.failed', 'voice.stt.blocked')
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    result = []
    for row in raw:
        try:
            payload = json.loads(row.get("payload") or "{}")
        except (ValueError, TypeError):
            payload = {}
        result.append({
            "id": row.get("id", ""),
            "event_type": row.get("event_type", ""),
            "status": payload.get("status", "unknown"),
            "locale": payload.get("locale", ""),
            "transcript": payload.get("transcript", ""),
            "transcript_sha256": payload.get("transcript_sha256"),
            "phrase_count": payload.get("phrase_count"),
            "bytes": payload.get("bytes"),
            "provider": payload.get("provider", ""),
            "ts_utc": payload.get("ts_utc") or row.get("created_at", ""),
            "proof_event_id": row.get("id", ""),
        })
    return result


@router.get("/api/voice/recordings/{recording_id}")
def voice_recording(recording_id: str):
    """
    Serve a stored voice recording by ID.

    Recordings are stored as rows in proof_events with event_type
    'voice.tts.synthesized' and base64-encoded audio in the payload.
    The frontend never receives audio device handles — audio is served
    from the backend buffer only.
    """
    from fastapi.responses import Response as FastAPIResponse
    raw = rows(
        "SELECT payload FROM proof_events WHERE id = ? AND event_type = 'voice.tts.synthesized'",
        (recording_id,),
    )
    if not raw:
        raise HTTPException(status_code=404, detail="Recording not found.")
    try:
        payload = json.loads(raw[0].get("payload") or "{}")
    except (ValueError, TypeError):
        raise HTTPException(status_code=500, detail="Recording payload is corrupt.")
    audio_b64 = payload.get("audio_base64")
    if not audio_b64:
        raise HTTPException(status_code=404, detail="Recording has no audio data.")
    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        raise HTTPException(status_code=500, detail="Recording audio data is not valid base64.")
    output_format = payload.get("output_format", DEFAULT_OUTPUT_FORMAT)
    mime = "audio/mpeg" if "mp3" in output_format or "mpeg" in output_format else "audio/wav"
    return FastAPIResponse(content=audio_bytes, media_type=mime, headers={"Cache-Control": "no-store"})


@router.get("/api/voice/proof-events")
def voice_proof_events(limit: int = 100, offset: int = 0) -> list[dict]:
    """Return recent voice proof events for the proof review panel."""
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    raw = rows(
        """
        SELECT id, event_type, source_agent, payload, created_at
        FROM proof_events
        WHERE event_type LIKE 'voice.%'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    result = []
    for row in raw:
        try:
            payload = json.loads(row.get("payload") or "{}")
        except (ValueError, TypeError):
            payload = {}
        result.append({
            "id": row.get("id", ""),
            "event_type": row.get("event_type", ""),
            "source_agent": row.get("source_agent", ""),
            "status": payload.get("status", "unknown"),
            "ts_utc": payload.get("ts_utc") or row.get("created_at", ""),
            "summary": _proof_event_summary(row.get("event_type", ""), payload),
        })
    return result


def _proof_event_summary(event_type: str, payload: dict) -> str:
    status = payload.get("status", "")
    if event_type == "voice.tts.synthesized":
        return f"TTS: {payload.get('bytes', 0)} bytes, voice={payload.get('voice', '')}"
    if event_type == "voice.tts.blocked":
        return f"TTS blocked: {status}"
    if event_type == "voice.tts.failed":
        return f"TTS failed: {status} HTTP={payload.get('http_status', '')}"
    if event_type == "voice.stt.transcribed":
        return f"STT: {payload.get('phrase_count', 0)} phrases, {payload.get('bytes', 0)} bytes"
    if event_type == "voice.stt.blocked":
        return f"STT blocked: {status}"
    if event_type == "voice.stt.failed":
        return f"STT failed: {status}"
    if event_type == "voice.agent.voice_saved":
        return f"Agent {payload.get('agent_id', '')} → voice={payload.get('voice', '')}"
    if event_type == "voice.agent.preview.triggered":
        return f"Preview: agent={payload.get('agent_id', '')}, accepted={payload.get('accepted', False)}"
    return event_type


@router.get("/api/voice/providers")
def providers() -> list[dict]:
    config = _azure_config()
    return [{
        "id": "azure",
        "name": "Azure Speech",
        "configured": config["configured"],
        "status": "ready" if config["configured"] else "not_configured",
        "region": config["region"] if config["configured"] else None,
        "source": config["source"],
    }]


@router.get("/api/voice/voices")
def voices(locale: str = "en") -> dict[str, Any]:
    config = _azure_config()
    if not config["configured"]:
        return {
            "provider": "azure",
            "configured": False,
            "status": "not_configured",
            "reason": "Azure Speech credentials are not configured in the private runtime env.",
            "voices": [],
            "count": 0,
        }
    try:
        catalog = _azure_voice_catalog(config)
    except urllib.error.HTTPError as exc:
        return {
            "provider": "azure",
            "configured": True,
            "status": "azure_error",
            "http_status": exc.code,
            "reason": f"Azure Speech returned HTTP {exc.code} while loading voices.",
            "voices": [],
            "count": 0,
        }
    except OSError as exc:
        return {
            "provider": "azure",
            "configured": True,
            "status": "unreachable",
            "reason": f"Azure Speech voice catalog request failed: {exc}",
            "voices": [],
            "count": 0,
        }
    prefix = locale.strip().lower()
    filtered = [
        _voice_row(item)
        for item in catalog
        if _voice_row(item)["locale"].lower().startswith(prefix)
    ]
    return {
        "provider": "azure",
        "configured": True,
        "status": "ready",
        "region": config["region"],
        "voices": filtered,
        "count": len(filtered),
    }


def _blocked(status: str, reason: str, voice: str, http_status: int | None = None, proof_event_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "queued": False,
        "voice": voice,
        "status": status,
        "reason": reason,
    }
    if http_status is not None:
        payload["http_status"] = http_status
    if proof_event_id is not None:
        payload["proof_event_id"] = proof_event_id
    return payload


def _azure_voice_catalog(config: dict[str, Any]) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"https://{config['region']}.tts.speech.microsoft.com/cognitiveservices/voices/list",
        headers={
            "Accept": "application/json",
            "Ocp-Apim-Subscription-Key": config["key"],
            "User-Agent": "Hermes3D-OS",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        payload = response.read().decode("utf-8")
    value = json.loads(payload)
    return value if isinstance(value, list) else []


def _azure_issue_token(config: dict[str, Any]) -> str:
    request = urllib.request.Request(
        f"https://{config['region']}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
        data=b"",
        headers={
            "Ocp-Apim-Subscription-Key": config["key"],
            "Content-Length": "0",
            "User-Agent": "Hermes3D-OS",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return response.read().decode("utf-8")


def _azure_synthesize(config: dict[str, Any], token: str, body: VoicePreview) -> bytes:
    ssml = _ssml(body)
    request = urllib.request.Request(
        f"https://{config['region']}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": DEFAULT_OUTPUT_FORMAT,
            "User-Agent": "Hermes3D-OS",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return response.read()


def _azure_fast_transcribe(config: dict[str, Any], audio: bytes, content_type: str, filename: str, locale: str) -> dict[str, Any]:
    api_version = os.environ.get("AZURE_SPEECH_STT_API_VERSION", FAST_TRANSCRIPTION_API_VERSION).strip() or FAST_TRANSCRIPTION_API_VERSION
    boundary, body = _multipart_transcription_body(audio, content_type, filename, {"locales": [locale] if locale else []})
    request = urllib.request.Request(
        f"https://{config['region']}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe?api-version={api_version}",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Ocp-Apim-Subscription-Key": config["key"],
            "User-Agent": "Hermes3D-OS",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=STT_REQUEST_TIMEOUT_S) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    transcript = _transcript_text(payload)
    if not transcript.strip():
        raise ValueError("Azure Speech fast transcription returned no transcript text.")
    return {
        "transcript": transcript.strip(),
        "confidence": _transcript_confidence(payload),
        "duration_ms": _int_value(payload.get("durationMilliseconds")) if isinstance(payload, dict) else None,
        "phrase_count": _phrase_count(payload),
    }


def _multipart_transcription_body(audio: bytes, content_type: str, filename: str, definition: dict[str, Any]) -> tuple[str, bytes]:
    boundary = f"----Hermes3D{new_id()}"
    safe_type = content_type if content_type and "\r" not in content_type and "\n" not in content_type else "application/octet-stream"
    definition_json = json.dumps(definition, separators=(",", ":"))
    parts = [
        (
            f"--{boundary}\r\n"
            "Content-Disposition: form-data; name=\"definition\"\r\n"
            "Content-Type: application/json\r\n\r\n"
            f"{definition_json}\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"audio\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {safe_type}\r\n\r\n"
        ).encode("utf-8"),
        audio,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    return boundary, b"".join(parts)


def _ssml(body: VoicePreview) -> str:
    voice = escape(body.voice.strip())
    text = escape(body.text[:500].strip() or DEFAULT_PREVIEW_TEXT)
    locale = _locale_from_voice(body.voice)
    rate_pct = max(-50, min(100, round((body.rate - 1.0) * 100)))
    pitch_pct = max(-50, min(50, body.pitch_pct))
    return (
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{rate_pct:+d}%' pitch='{pitch_pct:+d}%'>"
        f"{text}"
        "</prosody></voice></speak>"
    )


def _locale_from_voice(voice: str) -> str:
    parts = voice.split("-")
    if len(parts) >= 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
        return f"{parts[0]}-{parts[1]}"
    return "en-US"


def _voice_row(item: dict[str, Any]) -> dict[str, Any]:
    styles = item.get("StyleList")
    return {
        "id": str(item.get("ShortName") or item.get("Name") or ""),
        "short_name": str(item.get("ShortName") or item.get("Name") or ""),
        "display_name": str(item.get("DisplayName") or item.get("LocalName") or item.get("ShortName") or ""),
        "local_name": str(item.get("LocalName") or ""),
        "locale": str(item.get("Locale") or ""),
        "gender": str(item.get("Gender") or ""),
        "styles": styles if isinstance(styles, list) and all(isinstance(style, str) for style in styles) else [],
    }


def _transcript_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    combined = payload.get("combinedPhrases")
    if isinstance(combined, list):
        lines = [str(item.get("text") or "").strip() for item in combined if isinstance(item, dict)]
        text = "\n".join(item for item in lines if item)
        if text:
            return text
    phrases = payload.get("phrases") or payload.get("recognizedPhrases")
    if isinstance(phrases, list):
        lines: list[str] = []
        for phrase in phrases:
            if not isinstance(phrase, dict):
                continue
            if isinstance(phrase.get("text"), str):
                lines.append(phrase["text"])
                continue
            nbest = phrase.get("nBest") or phrase.get("NBest")
            if isinstance(nbest, list) and nbest and isinstance(nbest[0], dict):
                text = nbest[0].get("display") or nbest[0].get("Display") or nbest[0].get("text")
                if isinstance(text, str):
                    lines.append(text)
        return "\n".join(item.strip() for item in lines if item.strip())
    return str(payload.get("text") or "").strip()


def _transcript_confidence(payload: Any) -> float | None:
    if not isinstance(payload, dict):
        return None
    phrases = payload.get("phrases") or payload.get("recognizedPhrases")
    if isinstance(phrases, list):
        for phrase in phrases:
            if not isinstance(phrase, dict):
                continue
            nbest = phrase.get("nBest") or phrase.get("NBest")
            if isinstance(nbest, list) and nbest and isinstance(nbest[0], dict):
                confidence = nbest[0].get("confidence") or nbest[0].get("Confidence")
                if isinstance(confidence, (int, float)):
                    return float(confidence)
    return None


def _phrase_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    for key in ("combinedPhrases", "phrases", "recognizedPhrases"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def _int_value(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _clean_locale(value: str) -> str:
    candidate = value.strip()
    if len(candidate) < 2 or len(candidate) > 12:
        return "en-US"
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-")
    return candidate if all(ch in allowed for ch in candidate) else "en-US"


def _safe_filename(value: str) -> str:
    candidate = Path(value).name.strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in candidate)
    return (safe or "voice-note.webm")[:120]


def _audio_extension(content_type: str) -> str:
    if "wav" in content_type:
        return "wav"
    if "ogg" in content_type or "opus" in content_type:
        return "ogg"
    if "mpeg" in content_type or "mp3" in content_type:
        return "mp3"
    if "mp4" in content_type or "m4a" in content_type:
        return "m4a"
    if "flac" in content_type:
        return "flac"
    return "webm"


def _append_voice_proof(event_type: str, payload: dict[str, Any]) -> str:
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (proof_event_id, event_type, "voice-runtime", as_json({**payload, "ts_utc": utc_now()})),
    )
    return proof_event_id


def _azure_config() -> dict[str, Any]:
    private_env = _private_env()
    key = os.environ.get("AZURE_SPEECH_KEY") or private_env.get("AZURE_SPEECH_KEY", "")
    region = os.environ.get("AZURE_SPEECH_REGION") or private_env.get("AZURE_SPEECH_REGION", "")
    source = "environment" if os.environ.get("AZURE_SPEECH_KEY") else "private_env"
    return {
        "configured": bool(key and region),
        "key": key,
        "region": region,
        "source": source if key and region else None,
    }


def _private_env() -> dict[str, str]:
    env_path = Path(os.environ.get("HERMES3D_ENV_FILE", r"G:\private\.env"))
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            result[key] = value
    return result
