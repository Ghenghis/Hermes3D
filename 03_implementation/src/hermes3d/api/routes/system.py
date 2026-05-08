from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import platform
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, rows, utc_now
from hermes3d.db.init import DB_PATH
from hermes3d.services.agent_runtime import runtime_probe
from hermes3d.services.local_state import implementation_path, local_printers

router = APIRouter()
SELF_BRIDGE_PORTS = {8765, 8642}


class ProofEventCreate(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    source_agent: str | None = None


@router.get("/api/system/snapshot")
def system_snapshot() -> dict[str, Any]:
    printers = local_printers()
    telemetry = _host_telemetry()
    gpu_name = _gpu_name()
    api_auth_enforced = _api_auth_enforced()
    return {
        "ts_utc": utc_now(),
        "edition": "desktop_gpu_worker" if gpu_name else "blocked_no_gpu",
        "system_status": "OK" if gpu_name else "DEGRADED",
        "security_status": "Locked" if api_auth_enforced else "Open",
        "gpu_detected_pct": 100 if gpu_name else 0,
        "gpu_name": gpu_name,
        "vram_used_gb": None,
        "vram_total_gb": None,
        "cpu_pct": telemetry["cpu_pct"],
        "ram_pct": telemetry["ram_pct"],
        "gpu_util_pct": 0,
        "disk_pct": telemetry["disk_pct"],
        "network_kbps": telemetry["network_kbps"],
        "hostname": platform.node(),
        "platform": platform.platform(),
        "database": {"path": str(DB_PATH), "exists": DB_PATH.exists()},
        "printers": {
            "total": len(printers),
            "online": sum(1 for printer in printers if printer["status"] in {"online", "printing", "paused"}),
            "locked": sum(1 for printer in printers if printer["maintenance_flag"]),
        },
        "jobs": {
            "queued": _count("SELECT COUNT(*) AS count FROM jobs WHERE status = 'queued'"),
            "running": _count("SELECT COUNT(*) AS count FROM jobs WHERE status = 'running'"),
        },
        "approvals": {"pending": _count("SELECT COUNT(*) AS count FROM approvals WHERE status = 'pending'")},
    }


@router.get("/api/logs")
def logs(limit: int = 100) -> list[dict[str, Any]]:
    log_dir = implementation_path("var", "logs")
    if not log_dir.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True):
        for line in _tail_lines(path, max(1, min(limit, 500))):
            entries.append(
                {
                    "ts_utc": utc_now(),
                    "level": "info",
                    "source": path.name,
                    "message": line,
                }
            )
            if len(entries) >= limit:
                return entries
    return entries


@router.get("/api/proof/bundles")
def proof_bundles(limit: int = 50) -> list[dict[str, Any]]:
    events = rows("SELECT * FROM proof_events ORDER BY created_at DESC LIMIT ?", (limit,))
    artifacts = rows(
        """
        SELECT * FROM artifacts
        WHERE evidence_type LIKE '%proof%' OR gate IS NOT NULL
        ORDER BY created_at DESC LIMIT ?
        """,
        (limit,),
    )
    if not events and not artifacts:
        return []
    return [
        {
            "id": f"local-audit-evidence-{index}",
            "sha256": _stable_hash(item),
            "branch": "local",
            "commit": "",
            "ts_utc": item.get("created_at") or utc_now(),
            "files_count": 1 if item.get("file_path") else 0,
            "size_bytes": int(item.get("file_size") or 0),
            "verdict": "pending",
            "gates": [],
        }
        for index, item in enumerate([*events, *artifacts], start=1)
    ]


@router.post("/api/proof/events", status_code=201)
def create_proof_event(body: ProofEventCreate) -> dict[str, Any]:
    if not body.type.strip():
        raise HTTPException(status_code=400, detail="proof/audit event type must not be empty")
    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (event_id, body.type, body.source_agent, as_json(body.payload)),
    )
    return {
        "id": event_id,
        "event_type": body.type,
        "recorded": True,
        "proof_kind": "audit_event",
        "verified": False,
        "reason": "Recorded as local audit evidence only; not a signed proof bundle.",
    }


@router.get("/api/workflows")
def workflows() -> list[dict[str, Any]]:
    jobs = rows("SELECT * FROM jobs WHERE status IN ('queued', 'running') ORDER BY created_at DESC")
    return [
        {
            "id": job["id"],
            "name": job["name"],
            "status": "active" if job["status"] == "running" else job["status"],
            "stages": [],
            "active_stage": 0,
            "progress": int(job.get("progress") or 0) if "progress" in job else 0,
            "started_utc": job.get("created_at"),
            "job_type": job["job_type"],
            "printer_id": job["printer_id"],
            "created_at": job["created_at"],
        }
        for job in jobs
    ]


@router.get("/api/dimensional-reports")
def dimensional_reports() -> list[dict[str, Any]]:
    report_dir = implementation_path("var", "dimensional_reports")
    reports = [
        _file_report(path)
        for path in sorted(report_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    ] if report_dir.exists() else []
    artifact_reports = rows(
        """
        SELECT id, file_path, file_size, created_at, notes
        FROM artifacts
        WHERE evidence_type = 'dimensional_report'
        ORDER BY created_at DESC
        """
    )
    return [*reports, *artifact_reports]


@router.get("/api/providers/health")
def provider_health() -> dict[str, list[dict[str, Any]]]:
    private_env = _private_env()
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
    for provider_id, key_name in [
        ("minimax", "HERMES3D_MINIMAX_API_KEY"),
        ("deepseek", "HERMES3D_DEEPSEEK_API_KEY"),
        ("openrouter", "HERMES3D_LLM_API_KEY"),
    ]:
        if _env_value(key_name, private_env):
            providers.append(
                {
                    "provider_id": provider_id,
                    "status": "idle",
                    "last_probe_utc": utc_now(),
                    "http_status": None,
                    "latency_ms": None,
                    "stale": False,
                }
            )
    return {"providers": providers}


@router.get("/api/env/status")
def env_status() -> dict[str, list[dict[str, Any]]]:
    private_env = _private_env()
    variables = [
        ("HERMES3D_ENV_FILE", False, "Path to the private runtime .env file."),
        ("HERMES3D_PROFILE", False, "Active runtime profile."),
        ("HERMES3D_LM_STUDIO_BASE_URL", False, "Local LM Studio base URL."),
        ("OLLAMA_BASE_URL", False, "Local Ollama base URL."),
        ("HERMES3D_MINIMAX_API_KEY", True, "MiniMax API key."),
        ("HERMES3D_DEEPSEEK_API_KEY", True, "DeepSeek API key."),
        ("AZURE_SPEECH_KEY", True, "Azure Speech key for local voice runtime."),
        ("AZURE_SPEECH_REGION", False, "Azure Speech region."),
        ("HERMES3D_PROOF_KEY", True, "Proof envelope HMAC key."),
        ("HERMES3D_AGENT_RUNTIME_URL", False, "Trusted local/private OpenAI-compatible agent runtime URL."),
        ("HERMES3D_AGENT_RUNTIME_MODEL", False, "Concrete local model used for Hermes Agent personas."),
        ("HERMES3D_LEARNING_RUNNER_ENABLED", False, "Enables idle learning report execution after runtime gates pass."),
    ]
    return {
        "variables": [
            {
                "name": name,
                "set": bool(_env_value(name, private_env)),
                "sensitive": sensitive,
                "description": description,
            }
            for name, sensitive, description in variables
        ]
    }


@router.get("/api/system/runtime-readiness")
def runtime_readiness() -> dict[str, Any]:
    private_env = _private_env()
    agent_probe = runtime_probe(private_env)
    learning_runner_ready = _env_value("HERMES3D_LEARNING_RUNNER_ENABLED", private_env).strip() == "1"
    azure_ready = bool(_env_value("AZURE_SPEECH_KEY", private_env) and _env_value("AZURE_SPEECH_REGION", private_env))
    proof_ready = bool(_env_value("HERMES3D_PROOF_KEY", private_env))
    lm_studio = _probe_provider("lm_studio", _env_value("HERMES3D_LM_STUDIO_BASE_URL", private_env, "http://127.0.0.1:1234/v1"), "/models")
    ollama = _probe_provider("ollama", _env_value("OLLAMA_BASE_URL", private_env, "http://127.0.0.1:11434"), "/api/tags")
    local_llm_ready = any(item["status"] == "green" for item in [lm_studio, ollama])
    design_ready = _python_importable("trimesh")
    printers = local_printers()
    online_printers = [printer for printer in printers if printer.get("status") in {"online", "printing", "paused"}]
    runtimes = [
        _runtime_row(
            "hermes_agent_runtime",
            "Hermes Agent runtime bridge",
            "agents",
            "ready" if agent_probe["ready"] else "blocked",
            "private_env/local_http_probe",
            str(agent_probe["reason"]),
            ["HERMES3D_AGENT_RUNTIME_URL", "HERMES3D_AGENT_RUNTIME_MODEL"],
            "/api/agents/health",
        ),
        _runtime_row(
            "idle_learning_runner",
            "Idle Learning runner",
            "agents",
            "ready" if learning_runner_ready else "blocked",
            "env/private_env",
            "Idle Learning runner execution is enabled." if learning_runner_ready else "Set HERMES3D_LEARNING_RUNNER_ENABLED=1 only after the real report runner is installed and gate-tested.",
            ["HERMES3D_LEARNING_RUNNER_ENABLED"],
            "/api/learning/idle-workbench",
        ),
        _runtime_row(
            "azure_speech",
            "Azure Speech TTS/STT",
            "voice",
            "ready" if azure_ready else "blocked",
            "private_env" if azure_ready else "env/private_env",
            "Azure Speech key and region are available to the backend only." if azure_ready else "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in G:/private/.env.",
            ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"],
            "/api/voice/providers",
        ),
        _runtime_row(
            "proof_key",
            "Proof envelope signing key",
            "proof",
            "ready" if proof_ready else "blocked",
            "env/private_env",
            "HERMES3D_PROOF_KEY is configured." if proof_ready else "Set HERMES3D_PROOF_KEY in private env to replace the local development proof key.",
            ["HERMES3D_PROOF_KEY"],
            "python -m hermes3d.cli proof verify",
        ),
        _runtime_row(
            "local_llm",
            "Local LLM provider",
            "providers",
            "ready" if local_llm_ready else "blocked",
            "local_http_probe",
            "LM Studio or Ollama responded to backend probe." if local_llm_ready else "Start LM Studio/Ollama or configure their base URLs in private env.",
            ["HERMES3D_LM_STUDIO_BASE_URL", "OLLAMA_BASE_URL"],
            "/api/providers/health",
        ),
        _runtime_row(
            "source_update_execution",
            "Source app update execution",
            "updates",
            "partial",
            "backend",
            "Readiness checks are live; one-click update is still blocked until backup, gates, rollback, and user approval are wired for each app.",
            [],
            "/api/modules/update/readiness",
        ),
        _runtime_row(
            "design_executor",
            "Design/CAD executor",
            "modeling",
            "ready" if design_ready else "blocked",
            "python_runtime",
            "Parametric executor and trimesh proof gate are importable." if design_ready else "Install the Python mesh validation/runtime dependencies used by Design.",
            [],
            "/api/design/toolchain/status",
        ),
        _runtime_row(
            "generation_provider",
            "3D generation providers",
            "generation",
            "partial",
            "backend",
            "Local calibration-cube generation is live; external ComfyUI/TRELLIS/Hunyuan3D provider runtimes remain optional and must be configured before arbitrary prompt generation.",
            ["HERMES3D_COMFYUI_URL", "HERMES3D_TRELLIS_URL", "HERMES3D_HUNYUAN3D_URL"],
            "/api/generation/run",
        ),
        _runtime_row(
            "printer_fleet",
            "Moonraker printer fleet",
            "printers",
            "ready" if len(online_printers) >= 3 else "partial",
            "live_moonraker/config",
            f"{len(online_printers)}/{len(printers)} configured printers are online/active; S1 remains read-only locked by policy.",
            [],
            "/api/printers",
        ),
    ]
    counts = {
        "total": len(runtimes),
        "ready": sum(1 for item in runtimes if item["status"] == "ready"),
        "partial": sum(1 for item in runtimes if item["status"] == "partial"),
        "blocked": sum(1 for item in runtimes if item["status"] == "blocked"),
        "locked": sum(1 for item in runtimes if item["status"] == "locked"),
    }
    return {"updated_at": utc_now(), "summary": counts, "runtimes": runtimes}


def _count(sql: str) -> int:
    item = rows(sql)
    return int(item[0]["count"]) if item else 0


def _api_auth_enforced() -> bool:
    token = os.environ.get("HERMES3D_API_TOKEN") or os.environ.get("HERMES3D_API_KEY")
    required = os.environ.get("HERMES3D_REQUIRE_API_AUTH", "").strip().lower() in {"1", "true", "yes", "on"}
    return bool(token and required)


def _stable_hash(item: dict[str, Any]) -> str:
    payload = json.dumps(item, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tail_lines(path: Path, limit: int) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [line for line in lines[-limit:] if line.strip()]


def _file_report(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "id": path.stem,
        "file_path": str(path),
        "file_size": stat.st_size,
        "created_at": utc_now(),
        "notes": "Local dimensional report file.",
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


def _runtime_row(
    runtime_id: str,
    label: str,
    category: str,
    status: str,
    source: str,
    reason: str,
    required_env: list[str],
    proof: str,
) -> dict[str, Any]:
    return {
        "id": runtime_id,
        "label": label,
        "category": category,
        "status": status,
        "source": source,
        "reason": reason,
        "required_env": required_env,
        "proof": proof,
    }


def _trusted_runtime_url(private_env: dict[str, str]) -> str | None:
    value = _env_value("HERMES3D_AGENT_RUNTIME_URL", private_env).strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    try:
        host = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return None
    if host.is_loopback and parsed.port in SELF_BRIDGE_PORTS:
        return None
    if host.is_loopback or host.is_private or host.is_link_local:
        return value.rstrip("/")
    return None


def _python_importable(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


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
        "last_probe_utc": utc_now(),
        "http_status": http_status,
        "latency_ms": latency_ms,
        "stale": False,
    }


def _host_telemetry() -> dict[str, Any]:
    cpu_pct = 0
    ram_pct = 0
    try:
        import psutil  # type: ignore

        cpu_pct = int(round(psutil.cpu_percent(interval=0.05)))
        ram_pct = int(round(psutil.virtual_memory().percent))
    except Exception:
        pass
    try:
        disk_pct = int(round(shutil.disk_usage(implementation_path()).used / shutil.disk_usage(implementation_path()).total * 100))
    except OSError:
        disk_pct = 0
    return {
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "disk_pct": disk_pct,
        "network_kbps": [],
    }


def _gpu_name() -> str | None:
    candidates = [
        os.environ.get("CUDA_VISIBLE_DEVICES"),
        os.environ.get("HERMES3D_GPU_NAME"),
    ]
    for candidate in candidates:
        if candidate and candidate not in {"", "-1"}:
            return candidate
    return None
