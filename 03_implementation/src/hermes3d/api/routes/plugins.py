from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, row, rows

router = APIRouter()


class PluginConfig(BaseModel):
    config: dict = {}


@router.get("/api/plugins")
def list_plugins() -> list[dict]:
    return [_honest_plugin(row) for row in rows("SELECT * FROM plugins ORDER BY name")]


@router.post("/api/plugins/{plugin_id}/activate")
def activate(plugin_id: str) -> dict:
    plugin = row("SELECT * FROM plugins WHERE id = ?", (plugin_id,))
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    configured, reason = _plugin_configured(plugin_id, plugin.get("config"))
    if not configured:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "not_configured",
                "reason": reason,
                "plugin": _honest_plugin(plugin),
            },
        )
    execute("UPDATE plugins SET state = 'ACTIVE', activated_at = datetime('now') WHERE id = ?", (plugin_id,))
    return _honest_plugin(row("SELECT * FROM plugins WHERE id = ?", (plugin_id,)) or plugin)


@router.post("/api/plugins/{plugin_id}/deactivate")
def deactivate(plugin_id: str) -> dict:
    execute("UPDATE plugins SET state = 'READY', updated_at = datetime('now') WHERE id = ?", (plugin_id,))
    plugin = row("SELECT * FROM plugins WHERE id = ?", (plugin_id,))
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    return _honest_plugin(plugin)


@router.get("/api/plugins/{plugin_id}/config")
def get_config(plugin_id: str) -> dict:
    plugin = row("SELECT config FROM plugins WHERE id = ?", (plugin_id,))
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    return _redact_config(json.loads(plugin["config"] or "{}"))


@router.put("/api/plugins/{plugin_id}/config")
def put_config(plugin_id: str, body: PluginConfig) -> dict:
    execute("UPDATE plugins SET config = ?, updated_at = datetime('now') WHERE id = ?", (json.dumps(body.config), plugin_id))
    return {"plugin_id": plugin_id, "config": _redact_config(body.config)}


@router.get("/api/plugins/{plugin_id}/logs")
def logs(plugin_id: str, limit: int = 50) -> dict:
    return {"plugin_id": plugin_id, "lines": [f"{plugin_id}: no live log source configured"][:limit]}


@router.get("/api/plugins/{plugin_id}/status")
def status(plugin_id: str) -> dict:
    plugin = row("SELECT * FROM plugins WHERE id = ?", (plugin_id,))
    if not plugin:
        raise HTTPException(status_code=404, detail="plugin not found")
    honest = _honest_plugin(plugin)
    return {"id": honest["id"], "state": honest["state"], "status": honest["status"], "reason": honest["reason"]}


def _honest_plugin(plugin: dict) -> dict:
    configured, reason = _plugin_configured(plugin["id"], plugin.get("config"))
    state = plugin["state"]
    if state == "ACTIVE" and not configured:
        state = "READY"
    public_plugin = dict(plugin)
    public_plugin["config"] = _redact_config(json.loads(plugin.get("config") or "{}"))
    return {
        **public_plugin,
        "display": plugin.get("name"),
        "state": state,
        "configured": configured,
        "status": "configured" if configured else "not_configured",
        "reason": None if configured else reason,
        "dependencies": [],
        "configSchema": None,
        "healthUrl": None,
        "installVia": "none",
        "sourceOsModuleId": None,
    }


def _plugin_configured(plugin_id: str, config_json: str | None) -> tuple[bool, str]:
    config = json.loads(config_json or "{}")
    if plugin_id in {"moonraker", "camera-observer", "visual-evidence", "maintenance", "evidence-ledger", "autopilot-setup"}:
        return True, ""
    if plugin_id == "azure-voice":
        ok = bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))
        return ok, "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."
    if plugin_id in {"deepseek-v4", "minimax-mcp-vision", "local-modeling-llm"}:
        ok = bool(config.get("url") or os.environ.get("HERMES3D_MODEL_LLM_URL"))
        return ok, "Configure a local/provider URL before activation."
    return bool(config), "No local configuration has been saved for this plugin."


def _redact_config(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _secret_key(key) else _redact_config(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_config(item) for item in value]
    return value


def _secret_key(key: object) -> bool:
    lowered = str(key).lower()
    return any(token in lowered for token in ("key", "token", "secret", "password", "authorization"))
