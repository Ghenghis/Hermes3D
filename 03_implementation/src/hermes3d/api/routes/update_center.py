"""Update Center REST routes.

Provides a single aggregated endpoint ``GET /api/settings/update-center``
that the Settings → Update Center subtab consumes. It surfaces:

- Current installed versions of key components (read from package.json / pyproject)
- Desktop app update status (delegates to desktop_updates._source_state)
- Agent update status (delegates to agent_updates._repo_state)
- Velopack / app-updater readiness
- Provider health summary
- Failsafe / rollback availability per component
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from hermes3d.api.routes._common import execute, new_id, as_json

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]

# Paths — read-only; never mutated here
_UI_PKG = IMPLEMENTATION_ROOT / "ui" / "package.json"
_BACKEND_PKG = IMPLEMENTATION_ROOT / "pyproject.toml"

# Velopack marker: if the binary was produced by Velopack, a Squirrel-style
# app-manifest file will exist next to the executable.  We look for the
# env var the Velopack SDK sets at runtime first.
_VELOPACK_ENV = "VELOPACK_CURRENT_VERSION"
_VELOPACK_MANIFEST = Path(os.environ.get("VELOPACK_APP_DIR", "")) / "current" / "RELEASES" if os.environ.get("VELOPACK_APP_DIR") else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json_file(path: Path) -> dict[str, Any]:
    """Return parsed JSON from *path*, or {} on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ui_version() -> dict[str, Any]:
    pkg = _read_json_file(_UI_PKG)
    return {
        "component": "hermes3d-ui",
        "version": pkg.get("version") or "unknown",
        "name": pkg.get("name") or "hermes3d-ui",
        "source": str(_UI_PKG) if _UI_PKG.exists() else "not found",
        "found": _UI_PKG.exists(),
    }


def _backend_version() -> dict[str, Any]:
    """Read version from pyproject.toml [project] table (PEP 517)."""
    path = IMPLEMENTATION_ROOT / "pyproject.toml"
    version = "unknown"
    name = "hermes3d-backend"
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("version") and "=" in stripped:
                    version = stripped.split("=", 1)[1].strip().strip('"\'')
                if stripped.startswith("name") and "=" in stripped:
                    name = stripped.split("=", 1)[1].strip().strip('"\'')
        except OSError:
            pass
    return {
        "component": "hermes3d-backend",
        "version": version,
        "name": name,
        "source": str(path),
        "found": path.exists(),
    }


def _velopack_readiness() -> dict[str, Any]:
    """Determine whether the Velopack app-updater is configured and ready."""
    env_version = os.environ.get(_VELOPACK_ENV)
    manifest_found = bool(_VELOPACK_MANIFEST and _VELOPACK_MANIFEST.exists())
    ready = bool(env_version or manifest_found)
    if ready:
        reason = (
            f"Velopack runtime detected — current version: {env_version}"
            if env_version
            else "Velopack manifest file found next to executable."
        )
        status = "ready"
    else:
        reason = (
            "VELOPACK_CURRENT_VERSION env var is not set and no Velopack manifest "
            "was found. The app was likely launched from source (npm run dev / "
            "python -m hermes3d) rather than a packaged Velopack build."
        )
        status = "not_configured"
    return {
        "updater": "velopack",
        "status": status,
        "ready": ready,
        "current_version": env_version or None,
        "manifest_found": manifest_found,
        "reason": reason,
    }


def _component_backup_available(component: str) -> dict[str, Any]:
    """Return rollback availability metadata for *component*."""
    backup_dirs: dict[str, Path] = {
        "hermes-desktop": IMPLEMENTATION_ROOT / "var" / "hermes_desktop_backups",
        "hermes-agent": IMPLEMENTATION_ROOT / "var" / "hermes_agent_backups",
    }
    backup_root = backup_dirs.get(component)
    if not backup_root or not backup_root.exists():
        return {
            "component": component,
            "backup_available": False,
            "latest_backup": None,
            "rollback_action": f"POST /api/desktop/update/backup" if component == "hermes-desktop" else "POST /api/agents/update/backup",
        }
    backups = sorted(backup_root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return {
            "component": component,
            "backup_available": False,
            "latest_backup": None,
            "rollback_action": f"POST /api/desktop/update/backup" if component == "hermes-desktop" else "POST /api/agents/update/backup",
        }
    try:
        meta = json.loads(backups[0].read_text(encoding="utf-8"))
        return {
            "component": component,
            "backup_available": True,
            "latest_backup": {
                "backup_id": meta.get("backup_id"),
                "created_at": meta.get("created_at"),
                "package_version": meta.get("package_version"),
                "tag": meta.get("tag"),
                "commit": meta.get("commit"),
            },
            "rollback_action": "POST /api/agents/update/rollback" if component == "hermes-agent" else "POST /api/desktop/update/rollback",
        }
    except Exception:
        return {
            "component": component,
            "backup_available": False,
            "latest_backup": None,
            "rollback_action": None,
        }


def _probe_provider(provider_id: str, base_url: str, path: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    started = time.perf_counter()
    http_status: int | None = None
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=1.5) as response:
            http_status = int(response.status)
            status = "green" if 200 <= http_status < 400 else "amber"
    except urllib.error.HTTPError as exc:
        http_status = int(exc.code)
        status = "amber" if 400 <= http_status < 500 else "red"
    except OSError:
        status = "red"
    latency_ms = round((time.perf_counter() - started) * 1000)
    return {
        "provider_id": provider_id,
        "status": status,
        "last_probe_utc": _utc_now(),
        "http_status": http_status,
        "latency_ms": latency_ms,
        "stale": False,
    }


def _private_env() -> dict[str, str]:
    env_path = Path(os.environ.get("HERMES3D_ENV_FILE", r"G:\private\.env"))
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    except OSError:
        return {}
    return values


def _env_value(name: str, private_env: dict[str, str], default: str = "") -> str:
    return os.environ.get(name) or private_env.get(name) or default


@router.get("/api/settings/update-center")
def update_center() -> dict[str, Any]:
    """Aggregated update-center payload for the Settings UI."""
    private_env = _private_env()

    # Component versions
    ui_ver = _ui_version()
    backend_ver = _backend_version()

    # Velopack / desktop updater readiness
    velopack = _velopack_readiness()

    # Rollback availability
    desktop_rollback = _component_backup_available("hermes-desktop")
    agent_rollback = _component_backup_available("hermes-agent")

    # Provider health (lightweight probes — same as /api/providers/health but
    # isolated so we don't depend on the locked system.py route)
    providers = [
        _probe_provider(
            "lm_studio",
            _env_value("HERMES3D_LM_STUDIO_BASE_URL", private_env, "http://127.0.0.1:1234/v1"),
            "/models",
        ),
        _probe_provider(
            "ollama",
            _env_value("OLLAMA_BASE_URL", private_env, "http://127.0.0.1:11434"),
            "/api/tags",
        ),
    ]
    provider_summary = {
        "green": sum(1 for p in providers if p["status"] == "green"),
        "amber": sum(1 for p in providers if p["status"] == "amber"),
        "red": sum(1 for p in providers if p["status"] == "red"),
    }

    payload = {
        "generated_at": _utc_now(),
        "components": [ui_ver, backend_ver],
        "updater": velopack,
        "rollback": {
            "desktop": desktop_rollback,
            "agent": agent_rollback,
        },
        "provider_health": {
            "summary": provider_summary,
            "providers": providers,
        },
    }

    # Record proof event (non-fatal)
    try:
        execute(
            "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
            (
                new_id(),
                "settings.update_center.read",
                "claude-settings-plugins-07",
                as_json({"updater_status": velopack["status"], "providers": provider_summary}),
            ),
        )
    except Exception:
        pass

    return payload


@router.post("/api/settings/update-center/rollback/{component}", status_code=202)
def request_rollback(component: str) -> dict[str, Any]:
    """Surface rollback availability; actual rollback is delegated to the
    component-specific route (desktop_updates or agent_updates)."""
    allowed = {"hermes-desktop", "hermes-agent"}
    if component not in allowed:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown component '{component}'. Allowed: {sorted(allowed)}")
    meta = _component_backup_available(component)
    if not meta["backup_available"]:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail={
                "status": "no_backup",
                "reason": f"No backup is available for {component}. Create one first via the dedicated update route.",
                "rollback_action": meta.get("rollback_action"),
            },
        )
    return {
        "status": "rollback_available",
        "component": component,
        "backup": meta["latest_backup"],
        "next_step": meta["rollback_action"],
        "message": (
            f"A backup exists for {component}. POST to {meta['rollback_action']} "
            "to execute the rollback through the standard proof-gated flow."
        ),
    }
