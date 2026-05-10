"""Bounded process supervisor for Source OS service/web runners."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hermes3d.services.module_runtime import module_runtime_probe

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = IMPLEMENTATION_ROOT / "var" / "source_service_processes.json"
LOG_DIR = IMPLEMENTATION_ROOT / "var" / "source_service_logs"

SAFE_ENV_KEYS = {
    "ALLUSERSPROFILE",
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PUBLIC",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERDOMAIN",
    "USERPROFILE",
    "USERNAME",
    "WINDIR",
}


def start_source_service_runner(
    mod: dict[str, Any],
    contract: dict[str, Any],
    *,
    actor: str,
    post_start_probe_attempts: int = 3,
) -> dict[str, Any]:
    """Start a registered service runner and immediately verify health.

    The caller supplies the already-computed preflight contract. This function
    never accepts arbitrary commands: it runs only the exact command preview
    emitted by the Source OS runner contract, with shell disabled, a source
    checkout cwd, a sanitized environment, and PID state for rollback/stop.
    """

    module_id = str(mod.get("id") or contract.get("module_id") or "")
    runtime_ready = (
        bool(contract.get("runtime_ready")) or contract.get("status") == "already_running_verified"
    )
    if runtime_ready:
        return {
            "status": "already_running_verified",
            "accepted": True,
            "runtime_ready": True,
            "execution_mode": "supervised_local_process_noop_already_healthy",
            "supervisor": _supervisor_policy(),
            "post_start_runtime": module_runtime_probe(mod, live=True),
        }

    if not contract.get("start_preflight_passed"):
        return {
            "status": "blocked",
            "accepted": False,
            "runtime_ready": False,
            "execution_mode": "supervised_local_process_blocked_by_preflight",
            "blocked_reason": contract.get("blocked_reason")
            or "Service start preflight did not pass.",
            "blocked_reasons": list(contract.get("blocked_reasons") or []),
            "supervisor": _supervisor_policy(),
        }

    runner = contract.get("runner") if isinstance(contract.get("runner"), dict) else {}
    command = [str(item) for item in runner.get("command_preview") or []]
    if not command:
        return _blocked("No command is registered for this service runner.")

    local_path = Path(str(contract.get("local_path") or mod.get("local_path") or ""))
    if not local_path.is_dir():
        return _blocked("The service source checkout directory is missing.")

    active = _active_state(module_id)
    if active:
        runtime = module_runtime_probe(mod, live=True)
        return {
            "status": "tracked_process_running_verified"
            if runtime.get("status") == "ready"
            else "tracked_process_running_pending_health",
            "accepted": True,
            "runtime_ready": runtime.get("status") == "ready",
            "execution_mode": "supervised_local_process_existing_pid",
            "supervisor": _supervisor_policy(),
            "process": _public_process_record(active),
            "post_start_runtime": runtime,
            "blocked_reason": None if runtime.get("status") == "ready" else runtime.get("reason"),
        }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = LOG_DIR / f"{module_id}.stdout.log"
    stderr_path = LOG_DIR / f"{module_id}.stderr.log"
    resolved_command = _resolve_command(command, local_path)
    command_hash = _hash_command(resolved_command)

    try:
        with stdout_path.open("ab") as stdout_handle, stderr_path.open("ab") as stderr_handle:
            proc = subprocess.Popen(
                resolved_command,
                cwd=str(local_path),
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                env=_safe_process_env(runner),
                shell=False,
                creationflags=_creation_flags(),
            )
    except OSError as exc:
        return _blocked(f"Service process could not be started: {exc}", status="start_failed")

    record = {
        "module_id": module_id,
        "pid": proc.pid,
        "actor": actor,
        "started_utc": _utc_now(),
        "cwd": str(local_path),
        "command_hash": command_hash,
        "command_family": runner.get("command_family"),
        "configured_url": contract.get("configured_url") or "",
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }
    _upsert_process_state(module_id, record)

    runtime = _probe_after_start(mod, proc, attempts=post_start_probe_attempts)
    exited = proc.poll()
    if runtime.get("status") == "ready":
        status = "started_verified"
        accepted = True
    elif exited is None:
        status = "started_pending_health"
        accepted = True
    else:
        status = "start_failed"
        accepted = False
        _remove_process_state(module_id)

    return {
        "status": status,
        "accepted": accepted,
        "runtime_ready": runtime.get("status") == "ready",
        "execution_mode": "supervised_local_process_with_post_start_health_proof",
        "supervisor": _supervisor_policy(),
        "process": _public_process_record(record),
        "post_start_runtime": runtime,
        "blocked_reason": None
        if runtime.get("status") == "ready"
        else (
            runtime.get("reason")
            or (
                "Process exited before health proof."
                if exited is not None
                else "Health proof is pending."
            )
        ),
    }


def stop_source_service_runner(module_id: str, *, actor: str) -> dict[str, Any]:
    """Terminate only a PID previously started by this supervisor."""

    record = _process_state().get(module_id)
    if not record:
        return {
            "status": "not_running",
            "accepted": True,
            "stopped": True,
            "actor": actor,
            "reason": "No supervised Source OS process is recorded for this module.",
        }
    pid = int(record.get("pid") or 0)
    if pid <= 0 or not _pid_alive(pid):
        _remove_process_state(module_id)
        return {
            "status": "not_running",
            "accepted": True,
            "stopped": True,
            "actor": actor,
            "process": _public_process_record(record),
        }
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return {
            "status": "stop_failed",
            "accepted": False,
            "stopped": False,
            "actor": actor,
            "process": _public_process_record(record),
            "reason": str(exc),
        }
    _remove_process_state(module_id)
    return {
        "status": "stopped",
        "accepted": True,
        "stopped": True,
        "actor": actor,
        "process": _public_process_record(record),
    }


def _blocked(reason: str, *, status: str = "blocked") -> dict[str, Any]:
    return {
        "status": status,
        "accepted": False,
        "runtime_ready": False,
        "execution_mode": "supervised_local_process_blocked",
        "blocked_reason": reason,
        "supervisor": _supervisor_policy(),
    }


def _probe_after_start(
    mod: dict[str, Any], proc: subprocess.Popen[Any], *, attempts: int
) -> dict[str, Any]:
    runtime: dict[str, Any] = {
        "status": "setup_required",
        "reason": "No post-start probe was run.",
    }
    for attempt in range(max(1, attempts)):
        if attempt:
            time.sleep(min(1.0 + attempt, 3.0))
        runtime = module_runtime_probe(mod, live=True)
        if runtime.get("status") == "ready" or proc.poll() is not None:
            return runtime
    return runtime


def _resolve_command(command: list[str], cwd: Path) -> list[str]:
    executable = command[0]
    path = Path(executable)
    if path.is_absolute():
        return command
    local_candidate = cwd / path
    if local_candidate.exists():
        return [str(local_candidate), *command[1:]]
    import shutil

    found = shutil.which(executable)
    return [found or executable, *command[1:]]


def _safe_process_env(runner: dict[str, Any]) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in SAFE_ENV_KEYS and isinstance(value, str)
    }
    env["PYTHONUNBUFFERED"] = "1"
    for key, value in dict(runner.get("env") or {}).items():
        env[str(key)] = str(value)
    return env


def _creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def _hash_command(command: list[str]) -> str:
    return hashlib.sha256(json.dumps(command, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _process_state() -> dict[str, dict[str, Any]]:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _upsert_process_state(module_id: str, record: dict[str, Any]) -> None:
    state = _process_state()
    state[module_id] = record
    _write_process_state(state)


def _remove_process_state(module_id: str) -> None:
    state = _process_state()
    state.pop(module_id, None)
    _write_process_state(state)


def _write_process_state(state: dict[str, dict[str, Any]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_name(f"{STATE_PATH.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _active_state(module_id: str) -> dict[str, Any] | None:
    record = _process_state().get(module_id)
    if not record:
        return None
    pid = int(record.get("pid") or 0)
    if pid > 0 and _pid_alive(pid):
        return record
    _remove_process_state(module_id)
    return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _public_process_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "module_id": record.get("module_id"),
        "pid": record.get("pid"),
        "started_utc": record.get("started_utc"),
        "command_hash": record.get("command_hash"),
        "command_family": record.get("command_family"),
        "configured_url": record.get("configured_url"),
        "stdout_log": record.get("stdout_log"),
        "stderr_log": record.get("stderr_log"),
    }


def _supervisor_policy() -> dict[str, Any]:
    return {
        "name": "source-service-supervisor-v1",
        "shell": False,
        "cwd": "module_source_checkout",
        "environment": "sanitized_allowlist_plus_runner_env",
        "command_source": "registered_source_os_runner_contract_only",
        "post_start_gate": "local_http_health_verifier_must_return_ready_before_runtime_ready",
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
