from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import time
import zipfile
from collections import Counter
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from hermes3d.adapters.printrun import PrintrunAdapter
from hermes3d.api.routes._common import as_json, execute, new_id, row, rows
from hermes3d.api.safety import check_s1_lock
from hermes3d.db.load_modules import inspect_source_path, load_modules
from hermes3d.services.app_proof_truth import classify_app_proof
from hermes3d.services.module_runtime import (
    module_cli_install_config_runner_contract,
    module_executable_path_runner_contract,
    module_npm_package_runner_contract,
    module_python_import_repair_runner_contract,
    module_read_only_runner_contract,
    module_runner_contract,
    module_runner_contracts,
    module_runtime_probe,
    module_service_start_runner_contract,
    module_setup_steps,
    registered_runtime_probe_ids,
)
from hermes3d.services.source_service_supervisor import (
    start_source_service_runner,
    stop_source_service_runner,
)

router = APIRouter()
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
SOURCE_UPDATE_BACKUP_ROOT = IMPLEMENTATION_ROOT / "var" / "source_module_backups"
SOURCE_CLI_SURFACE_AUDIT_PATH = IMPLEMENTATION_ROOT / "proof" / "SOURCE_APP_CLI_SURFACE_AUDIT.json"
_MODULES_SYNCED = False
SECRET_RE = re.compile(
    r"(?i)(https?://)([^/@\s]+@)|([?&](?:token|key|api_key|access_token)=)[^&\s]+"
)
BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,180}$")
GIT_REF_RE = re.compile(r"^[A-Za-z0-9._/-]{1,180}$")
RUNNER_RECOMMENDATIONS = {
    "cli_worker": "Register a version/help verifier and one dry-run command that cannot write printers or source files.",
    "cli_or_python_worker": "Register either a CLI version probe or a Python import/version probe, then add a bounded smoke gate.",
    "desktop_app": "Register the installed executable path and a non-launching version/file-presence verifier before enabling Launch.",
    "desktop_or_cli": "Register the installed executable path, prefer a CLI help/version probe, and keep GUI launch separate.",
    "firmware_source": "Register a read-only version/build metadata verifier; flashing remains locked behind explicit approval.",
    "gpu_worker": "Register an import/device availability probe and a tiny bounded inference smoke gate before enabling jobs.",
    "npm_package": "Register npm package metadata/version checks and a read-only node import or help probe.",
    "python_worker": "Register a Python import/version probe in the selected environment before enabling worker actions.",
    "service": "Register a local health endpoint or process probe plus a read-only API smoke check.",
    "web_app": "Register a local URL health check and a browser route smoke check.",
    "reference": "Register a read-only index parser or documentation inventory proof.",
    "catalog_reference": "Register a read-only catalog parser and scoring proof.",
    "hardware_reference": "Register a read-only hardware inventory/index proof.",
    "rust_library_reference": "Register Cargo metadata or source index proof before promoting any adapter.",
    "service_reference": "Register reference docs/config parser proof; do not expose service controls until an adapter exists.",
    "source_reference": "Register source inventory proof and only promote to runtime when a concrete adapter exists.",
    "touch_ui_reference": "Register source inventory proof; touch UI actions need a separate device/screen adapter.",
    "web_app_reference": "Register reference route/build metadata proof before exposing a runnable web app.",
}
CLI_PREFERRED_LAUNCH_KINDS = {"cli_worker", "cli_or_python_worker", "desktop_or_cli"}
CLI_POSSIBLE_LAUNCH_KINDS = {
    "desktop_app",
    "python_worker",
    "gpu_worker",
    "service",
    "web_app",
    "npm_package",
}


class ModuleBackupRequest(BaseModel):
    actor: str = "operator"
    note: str | None = None


class ModuleUpdateRequest(BaseModel):
    actor: str = "operator"
    backup_id: str | None = None
    reason: str | None = None


class ModuleRollbackRequest(BaseModel):
    actor: str = "operator"
    backup_id: str | None = None
    reason: str | None = None


class ModuleRuntimeStartRunnerRequest(BaseModel):
    actor: str = "operator"
    execute: bool = False


class ModuleRuntimeReadOnlyRunnerRequest(BaseModel):
    actor: str = "operator"


class ModuleRuntimeExecutablePathRunnerRequest(BaseModel):
    actor: str = "operator"


class ModuleRuntimePythonImportRepairRunnerRequest(BaseModel):
    actor: str = "operator"


class ModuleRuntimeCliInstallConfigRunnerRequest(BaseModel):
    actor: str = "operator"


class ModuleRuntimeNpmPackageRunnerRequest(BaseModel):
    actor: str = "operator"


def _sync_registry_once() -> None:
    global _MODULES_SYNCED
    if _MODULES_SYNCED:
        return
    load_modules()
    _MODULES_SYNCED = True


# W18-A13 — small response cache for the two cold-slow runtime probes
# (``/api/modules/runtime/verifiers`` and
# ``/api/modules/runtime/agent-cli-readiness``). Audit W18-A3 measured
# cold-start latency >20s on both because each iterates 60 modules and
# probes the runtime status of each. Subsequent calls within the cache
# window return the previously computed payload instantly, keeping the
# Hermes Agent action catalog (which calls these probes transitively)
# under its 8s FE timeout.
RUNTIME_RESPONSE_CACHE_TTL_S = 8.0
_RUNTIME_RESPONSE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cached_runtime_response(key: str, builder: Any) -> dict[str, Any]:
    cached = _RUNTIME_RESPONSE_CACHE.get(key)
    if cached is not None:
        cached_at, cached_payload = cached
        if (time.monotonic() - cached_at) < RUNTIME_RESPONSE_CACHE_TTL_S:
            return cached_payload
    fresh = builder()
    _RUNTIME_RESPONSE_CACHE[key] = (time.monotonic(), fresh)
    return fresh


def _invalidate_runtime_response_cache() -> None:
    """Clear the runtime-response cache.

    Called from write-path handlers (``/verify-all``, runner-contract
    edits, etc.) so the next GET returns the freshly computed state
    instead of a stale snapshot.
    """
    _RUNTIME_RESPONSE_CACHE.clear()
    _MODULE_LIST_CACHE.clear()
    _MODULE_RUNTIME_PROBE_CACHE.clear()


# W18-A18 — modules-list response cache + parallel per-module probe.
#
# Audit (operator, 2026-05-11): /api/source-os/modules and the
# canonical /api/modules endpoint took ~19 s on a warm backend, and
# the cold first-call could exceed the FE 15s AbortSignal timeout.
# Profile: ``list_modules`` iterates ~60 module rows and calls
# ``_module_response`` for each. ``_module_response`` invokes
# ``module_runtime_probe(mod, live=False)`` per module; for kinds
# ``python_import`` / ``python_source_import`` / ``python_module_cli``
# / ``node_package`` / ``moonraker_fleet`` / ``local_http_health`` the
# probe runs a subprocess (or HTTP call) regardless of ``live``. With
# 60 modules × ~0.3 s subprocess wrapping, sequential cost is ~18 s
# wall-clock. The list endpoint is not a hot mutation point — every
# GET re-paying that cost is wasted work, and the FE polls it.
#
# Fix is two-pronged:
#   1. Short TTL response cache (``MODULE_LIST_CACHE_TTL_S``) so a
#      second GET inside the window returns the previous payload
#      instantly — the same pattern W18-A13 already uses for the
#      ``/api/modules/runtime/verifiers`` endpoint.
#   2. Build the first-call payload with a ``ThreadPoolExecutor`` so
#      the 60 per-module probes run in parallel (~8 threads on a
#      typical workstation), driving cold-start under 5 s.
#
# Honest data preserved: we still call the real ``_module_response``;
# we just stop running it sequentially. The cache is invalidated by
# any write path (``set_module_provider``, ``verify_all_module_runtimes``,
# install/update/rollback) via ``_invalidate_runtime_response_cache()``.
MODULE_LIST_CACHE_TTL_S = 12.0
# Concurrency budget for cold-list builds. Audit (2026-05-11): profiled
# 60-module cold-list with p50 per-module probe = 91 ms and p100 ~ 1.5 s.
# 32 workers is a sweet spot: enough to amortize the slowest single-probe
# wall-time, but bounded so Windows ``CreateProcess`` contention does not
# inflate startup latency.
MODULE_LIST_PARALLELISM = 32
# Per-future timeout MUST exceed the slowest per-module probe seen in
# profiling (1.5 s) with comfortable headroom; otherwise an honest
# probe spike degrades the row to an "unreachable" fallback envelope.
MODULE_LIST_PER_FUTURE_TIMEOUT_S = 4.0
_MODULE_LIST_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}

# W18-A18 — per-module runtime-probe cache, keyed by ``module_id``.
#
# The 60-module list calls ``_module_runtime_probe(mod, live=False)``
# for each row, and several probe kinds (``python_import``,
# ``moonraker_fleet``, ``local_http_health``, ``node_package``,
# ``python_module_cli``, ``python_source_import``) execute subprocess
# or network calls regardless of the ``live`` flag — each costing
# ~100–1500 ms. Caching the dict result by module_id with the same
# TTL as the list response means a re-request inside the cache window
# avoids re-spawning those subprocesses entirely.
#
# Honest data: cache values are exactly what ``module_runtime_probe``
# computed last call — no fabrication. The TTL plus write-path
# invalidation (``_invalidate_runtime_response_cache``) keeps results
# fresh enough for the FE polling cadence.
MODULE_RUNTIME_PROBE_CACHE_TTL_S = 12.0
_MODULE_RUNTIME_PROBE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _cached_module_list(cache_key: str, builder: Any) -> list[dict[str, Any]]:
    cached = _MODULE_LIST_CACHE.get(cache_key)
    if cached is not None:
        cached_at, payload = cached
        if (time.monotonic() - cached_at) < MODULE_LIST_CACHE_TTL_S:
            return payload
    fresh = builder()
    _MODULE_LIST_CACHE[cache_key] = (time.monotonic(), fresh)
    return fresh


def _build_module_responses_parallel(module_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run ``_module_response`` for each row in parallel and preserve order.

    Per-module work is I/O bound (subprocess + filesystem stat), so a
    thread pool is the appropriate parallelism unit. We cap workers at
    ``MODULE_LIST_PARALLELISM`` to avoid overwhelming the OS process
    table when the registry grows.
    """
    if not module_rows:
        return []
    max_workers = min(len(module_rows), MODULE_LIST_PARALLELISM) or 1
    results: list[dict[str, Any] | None] = [None] * len(module_rows)
    with ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="hermes-module-list"
    ) as pool:
        future_to_index = {
            pool.submit(_module_response, mod): idx for idx, mod in enumerate(module_rows)
        }
        for future, idx in future_to_index.items():
            try:
                results[idx] = future.result(timeout=MODULE_LIST_PER_FUTURE_TIMEOUT_S)
            except Exception:  # noqa: BLE001 — degrade per-module, never the whole list
                # Fall back to the raw DB row + a minimal envelope so the
                # response still surfaces the module honestly. We do NOT
                # invent a runtime "ready" verdict — the runtime field
                # carries an explicit ``blocked`` status with the reason.
                mod = module_rows[idx]
                results[idx] = {
                    **mod,
                    "display": mod.get("display_name"),
                    "repo": mod.get("repo_url"),
                    "localPath": mod.get("local_path"),
                    "installState": mod.get("install_state"),
                    "installProgress": mod.get("install_progress") or 0,
                    "detectedVersion": mod.get("detected_version"),
                    "launchKind": mod.get("launch_kind"),
                    "bridgeTasks": [],
                    "proofs": [],
                    "dispatchGates": [],
                    "providers": [],
                    "activeProvider": None,
                    "runtime": {
                        "status": "blocked",
                        "label": "Runtime probe did not return in time",
                        "kind": mod.get("launch_kind"),
                        "verifier": None,
                        "path": mod.get("local_path") or "",
                        "detected": False,
                        "executed": False,
                        "return_code": None,
                        "capabilities": [],
                        "reason": "Per-module runtime probe exceeded the parallel-list budget; rerun Verify from Source OS.",
                        "setup_steps": [],
                        "proof_source": None,
                        "output_head": [],
                    },
                }
    return [item if item is not None else {} for item in results]


def _module_or_404(module_id: str) -> dict[str, Any]:
    _sync_registry_once()
    mod = row("SELECT * FROM modules WHERE id = ?", (module_id,))
    if not mod:
        raise HTTPException(status_code=404, detail="module not found")
    return mod


def _write_source_status(module_id: str, status: dict[str, Any], *, synced: bool = False) -> None:
    execute(
        """
        UPDATE modules
           SET install_state = ?,
               install_progress = ?,
               detected_version = ?,
               health = ?,
               last_sync_at = CASE WHEN ? THEN datetime('now') ELSE last_sync_at END,
               updated_at = datetime('now')
         WHERE id = ?
        """,
        (
            status["install_state"],
            status["install_progress"],
            status["detected_version"],
            status["health"],
            1 if synced else 0,
            module_id,
        ),
    )


def _sync_module_status(mod: dict[str, Any]) -> dict[str, Any]:
    status = inspect_source_path(mod.get("local_path"), mod.get("repo_url"))
    if any(
        mod.get(key) != status[value_key]
        for key, value_key in (
            ("install_state", "install_state"),
            ("install_progress", "install_progress"),
            ("detected_version", "detected_version"),
            ("health", "health"),
        )
    ):
        _write_source_status(mod["id"], status)
        mod = {**mod, **status}
    return mod


def _bridge_runner_configured(_module_id: str) -> bool:
    return False


def _module_response(mod: dict[str, Any]) -> dict[str, Any]:
    mod = _sync_module_status(mod)
    tasks = rows("SELECT * FROM bridge_tasks WHERE module_id = ? ORDER BY name", (mod["id"],))
    bridge_runner_ready = _bridge_runner_configured(mod["id"])
    providers = _module_providers(mod["id"])
    runtime = _module_runtime_probe(mod)
    return {
        **mod,
        "display": mod.get("display_name"),
        "repo": mod.get("repo_url"),
        "localPath": mod.get("local_path"),
        "installState": mod.get("install_state"),
        "installProgress": mod.get("install_progress") or 0,
        "detectedVersion": mod.get("detected_version"),
        "launchKind": mod.get("launch_kind"),
        "bridgeTasks": [
            {
                "id": task["id"],
                "name": task["name"],
                "status": task["status"]
                if bridge_runner_ready and task["status"] in {"pending", "running", "pass", "fail"}
                else "skipped",
                "last_run_at": task["last_run_at"],
                "last_run_log": task["last_result"]
                if bridge_runner_ready
                else "No real bridge runner is configured for this source module yet.",
                "duration_ms": None,
            }
            for task in tasks
        ],
        "proofs": [],
        "dispatchGates": [],
        "providers": providers,
        "activeProvider": _active_provider(mod["id"], providers),
        "runtime": runtime,
        **classify_app_proof(mod),
    }


def _module_providers(module_id: str) -> list[dict[str, Any]]:
    provider_rows = rows(
        "SELECT * FROM module_providers WHERE module_id = ? ORDER BY display_name", (module_id,)
    )
    return [_provider_response(provider) for provider in provider_rows]


def _provider_response(provider: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": provider["id"],
        "moduleId": provider["module_id"],
        "display": provider["display_name"],
        "kind": provider["provider_kind"],
        "repo": provider["repo_url"],
        "installCommand": provider["install_command"],
        "verifyCommands": _json_array(provider.get("verify_commands")),
        "capabilities": _json_array(provider.get("capabilities")),
        "license": provider["license"],
        "state": provider["state"],
        "notes": provider["notes"],
    }


def _module_runtime_probe(mod: dict[str, Any], *, live: bool = False) -> dict[str, Any]:
    """W18-A18 — TTL-cached when ``live=False``.

    The non-live path is the one called from list/aggregation endpoints
    (e.g. ``/api/modules``, ``/api/source-os/modules``). Several probe
    kinds subprocess regardless of ``live`` (see audit note on
    :data:`_MODULE_RUNTIME_PROBE_CACHE` above), so we cache by
    ``module_id`` for :data:`MODULE_RUNTIME_PROBE_CACHE_TTL_S`. The
    ``live=True`` path (operator-initiated Verify, etc.) always
    bypasses the cache and re-executes the probe.
    """
    if live:
        result = module_runtime_probe(mod, live=True)
        # Refresh the cache so a follow-up non-live list sees the
        # verified state instead of the previous stale snapshot.
        _MODULE_RUNTIME_PROBE_CACHE[str(mod.get("id") or "")] = (time.monotonic(), result)
        return result
    module_id = str(mod.get("id") or "")
    if module_id:
        cached = _MODULE_RUNTIME_PROBE_CACHE.get(module_id)
        if cached is not None:
            cached_at, payload = cached
            if (time.monotonic() - cached_at) < MODULE_RUNTIME_PROBE_CACHE_TTL_S:
                return payload
    fresh = module_runtime_probe(mod, live=False)
    if module_id:
        _MODULE_RUNTIME_PROBE_CACHE[module_id] = (time.monotonic(), fresh)
    return fresh


def _module_setup_steps(mod: dict[str, Any]) -> list[str]:
    return module_setup_steps(mod)


def _runtime_setup_plan_record(mod: dict[str, Any]) -> dict[str, Any]:
    synced = _sync_module_status(mod)
    runtime = _module_runtime_probe(synced, live=False)
    status = str(runtime.get("status") or "blocked")
    setup_steps = [str(step) for step in runtime.get("setup_steps") or []]
    if status == "ready":
        runner_status = "runtime_ready"
        next_action = "run existing verifier or launch bridge"
        setup_steps = ["Runtime verifier is already registered and passing."]
    elif status == "source_ready":
        runner_status = "runner_not_registered"
        next_action = "register safe module runner"
        setup_steps = setup_steps or _module_setup_steps(synced)
    elif status == "setup_required":
        runner_status = "runtime_repair_required"
        next_action = "repair configured runtime path"
    elif status == "not_installed":
        runner_status = "source_install_available"
        next_action = "run source install before runtime setup"
    else:
        runner_status = "blocked"
        next_action = "fix source registry before setup"

    return {
        "module_id": synced["id"],
        "display": synced.get("display_name"),
        "section": synced.get("section"),
        "repo": synced.get("repo_url"),
        "local_path": synced.get("local_path"),
        "launch_kind": synced.get("launch_kind"),
        "install_state": synced.get("install_state"),
        "runtime_status": status,
        "runtime_label": runtime.get("label"),
        "verifier": runtime.get("verifier"),
        "runner_status": runner_status,
        "next_action": next_action,
        "source_install_supported": status == "not_installed"
        and bool(synced.get("repo_url") and synced.get("local_path")),
        "runtime_ready": status == "ready",
        "agent_can_execute_setup_now": False,
        "agent_setup_gate": "No source module setup runner executes until it is registered with a safe verifier and proof gate.",
        "setup_steps": setup_steps[:6],
        "reason": runtime.get("reason"),
        "proof_source": runtime.get("proof_source"),
    }


def _runtime_setup_queue_payload(
    *,
    section: str | None,
    actor: str | None = None,
    append_proof: bool = False,
) -> dict[str, Any]:
    _sync_registry_once()
    result = rows(
        "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
        (section, section),
    )
    records = [_runtime_setup_plan_record(mod) for mod in result]
    counts = {
        "runtime_ready": 0,
        "source_ready": 0,
        "runner_not_registered": 0,
        "source_install_available": 0,
        "runtime_repair_required": 0,
        "blocked": 0,
    }
    for record in records:
        runner_status = str(record.get("runner_status") or "blocked")
        if runner_status == "runtime_ready":
            counts["runtime_ready"] += 1
        elif runner_status == "runner_not_registered":
            counts["source_ready"] += 1
            counts["runner_not_registered"] += 1
        elif runner_status == "source_install_available":
            counts["source_install_available"] += 1
        elif runner_status == "runtime_repair_required":
            counts["runtime_repair_required"] += 1
        else:
            counts["blocked"] += 1

    proof_event_id = None
    if append_proof:
        proof_event_id = _append_module_proof(
            "source_module.runtime_setup_queue.planned",
            actor or "operator",
            {
                "section": section,
                "count": len(records),
                "counts": counts,
                "records": records,
            },
        )
    return {
        "accepted": counts["blocked"] == 0,
        "status": "planned" if counts["blocked"] == 0 else "blocked",
        "section": section,
        "count": len(records),
        "counts": counts,
        "execution_mode": "plan_only_until_safe_runner_registered",
        "agent_gate": "Hermes Agents may consume this queue, but setup execution remains blocked until a module-specific safe runner and verifier are registered.",
        "records": records,
        "proof_event_id": proof_event_id,
    }


def _json_array(value: Any) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _active_provider(module_id: str, providers: list[dict[str, Any]] | None = None) -> str | None:
    if not providers:
        providers = _module_providers(module_id)
    if not providers:
        return None
    setting_key = f"source_os.{module_id}.active_provider"
    setting = row("SELECT value FROM settings WHERE key = ?", (setting_key,))
    active = str(setting["value"]) if setting else None
    provider_ids = {provider["id"] for provider in providers}
    if active in provider_ids:
        return active
    return providers[0]["id"]


def _module_update_record(mod: dict[str, Any], *, deep: bool = False) -> dict[str, Any]:
    local_path = mod.get("local_path")
    path = Path(str(local_path)) if local_path else None
    exists = bool(path and path.exists())
    git_ready = bool(path and exists and (path / ".git").exists())
    commit = (
        _run_git_optional(path, ["rev-parse", "--short=12", "HEAD"]) if git_ready and deep else None
    )
    branch = (
        _run_git_optional(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if git_ready and deep
        else None
    )
    exact_tag = (
        _run_git_optional(path, ["describe", "--tags", "--exact-match"])
        if git_ready and deep
        else None
    )
    nearest_tag = (
        _run_git_optional(path, ["describe", "--tags", "--abbrev=0"])
        if git_ready and deep
        else None
    )
    dirty_entries = (
        (_run_git_optional(path, ["status", "--porcelain=v1"]) or "").splitlines()
        if git_ready and deep
        else []
    )
    upstream = (
        _run_git_optional(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
        if git_ready and deep
        else None
    )
    behind_text = (
        _run_git_optional(path, ["rev-list", "--count", "HEAD..@{u}"])
        if git_ready and upstream and deep
        else None
    )
    behind_count = int(behind_text) if behind_text and behind_text.isdigit() else None
    remote_url = (
        _run_git_optional(path, ["remote", "get-url", "origin"]) if git_ready and deep else None
    )
    latest_backup = _latest_source_backup(mod["id"])
    latest_check = _latest_source_update_check(mod["id"])
    source_update_supported = bool(git_ready and (not deep or (remote_url and not dirty_entries)))
    reason = None
    if not local_path:
        reason = "No local source checkout path is configured."
    elif not exists:
        reason = "Local source checkout path is missing."
    elif not git_ready:
        reason = "Local source path is not a git checkout; update requires a source checkout with .git metadata."
    elif dirty_entries:
        reason = "Local source checkout has uncommitted changes; create a backup or commit before update."
    elif deep and not remote_url:
        reason = "Local source checkout has no origin remote."
    return {
        "module_id": mod["id"],
        "display": mod.get("display_name"),
        "section": mod.get("section"),
        "repo": mod.get("repo_url"),
        "local_path": local_path,
        "install_state": mod.get("install_state"),
        "detected_version": mod.get("detected_version"),
        "git_ready": git_ready,
        "source_update_supported": source_update_supported,
        "reason": reason,
        "current": {
            "commit": commit,
            "branch": branch,
            "exact_tag": exact_tag,
            "nearest_tag": nearest_tag,
            "upstream": upstream,
            "remote": _redact_url(remote_url),
        },
        "dirty": bool(dirty_entries),
        "dirty_entries": dirty_entries[:20],
        "cached_behind_count": behind_count,
        "latest_backup": _public_backup(latest_backup),
        "backup_available": latest_backup is not None,
        "latest_check": latest_check,
        "deep_checked": deep,
        "update_action": "blocked"
        if reason
        else "deep_check_required"
        if not deep
        else "check_ready",
        "safety": "readiness only; no fetch, checkout, pull, install, or build runs from this endpoint",
    }


def _run_git_optional(path: Path | None, args: list[str], *, timeout: int = 5) -> str | None:
    if path is None:
        return None
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _redact_url(value: str | None) -> str | None:
    if not value:
        return None
    return SECRET_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]@"
        if match.group(1)
        else f"{match.group(3)}[REDACTED]",
        value,
    )


@router.get("/api/modules")
def list_modules(section: str | None = None) -> list[dict[str, Any]]:
    """W18-A18 — cached + parallelized.

    Operator reproduced 19 s wall-clock per call because
    ``_module_response`` was called sequentially across ~60 module rows
    and each call dispatched a subprocess via
    ``module_runtime_probe(mod, live=False)``. We now:

    * Cache the response by section key for
      :data:`MODULE_LIST_CACHE_TTL_S` (12 s) so the FE polling cadence
      (typically <5 s) sees instant warm responses.
    * Build the cold response with a thread-pool fan-out so
      first-call latency is bounded by the slowest single per-module
      probe (~0.3 s), not their sum.

    Write paths call :func:`_invalidate_runtime_response_cache` which
    also clears :data:`_MODULE_LIST_CACHE`, so cache freshness is
    coupled to real state changes.
    """
    cache_key = f"section={section or ''}"
    return _cached_module_list(cache_key, lambda: _build_list_modules_payload(section))


def _build_list_modules_payload(section: str | None) -> list[dict[str, Any]]:
    _sync_registry_once()
    result = rows(
        "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
        (section, section),
    )
    if not result:
        load_modules()
        result = rows(
            "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
            (section, section),
        )
    return _build_module_responses_parallel(result)


@router.get("/api/modules/update/readiness")
def module_update_readiness(section: str | None = None, deep: bool = False) -> dict[str, Any]:
    """Return local, non-mutating source update readiness for the app update center."""
    _sync_registry_once()
    result = rows(
        "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
        (section, section),
    )
    records = [
        _module_update_record(_sync_module_status(mod) if deep else mod, deep=deep)
        for mod in result
    ]
    return {
        "status": "ready",
        "strategy": "server_side_lightweight_readiness_by_default; deep=true adds local git preflight only; update execution requires backup, proof gates, and rollback route",
        "section": section,
        "deep": deep,
        "count": len(records),
        "ready_for_update_check": sum(1 for record in records if record["source_update_supported"]),
        "blocked": sum(1 for record in records if not record["source_update_supported"]),
        "outdated_cached": sum(
            1
            for record in records
            if record["cached_behind_count"] and record["cached_behind_count"] > 0
        ),
        "dirty": sum(1 for record in records if record["dirty"]),
        "records": records,
    }


@router.get("/api/source-os/modules")
def list_source_os_modules(section: str | None = None) -> list[dict[str, Any]]:
    return list_modules(section)


@router.get("/api/source-os/modules/update-readiness")
def get_source_os_modules_update_readiness(
    section: str | None = None, deep: bool = False
) -> dict[str, Any]:
    """W18-A13 — Source-OS alias of :func:`module_update_readiness`.

    Mirrors the canonical ``/api/modules/update/readiness`` handler so
    the FE ``hermes3dClient.sourceOsClient.updateReadiness()`` (which
    GETs ``/api/source-os/modules/update-readiness``) no longer 404s.
    Audit W18-A3 flagged the FE path as ``FAIL_BACKEND_MISSING``;
    aliasing keeps both FE and BE call sites stable.

    NOTE: This route must be declared **before** the more general
    ``/api/source-os/modules/{module_id}`` path operation below so
    FastAPI's path matcher does not bind ``update-readiness`` as a
    ``module_id``.
    """
    return module_update_readiness(section=section, deep=deep)


@router.get("/api/modules/{module_id}")
def get_module(module_id: str) -> dict[str, Any]:
    return _module_response(_module_or_404(module_id))


@router.get("/api/source-os/modules/{module_id}")
def get_source_os_module(module_id: str) -> dict[str, Any]:
    return get_module(module_id)


@router.get("/api/modules/{module_id}/providers")
def list_module_providers(module_id: str) -> dict[str, Any]:
    _module_or_404(module_id)
    providers = _module_providers(module_id)
    return {
        "module_id": module_id,
        "activeProvider": _active_provider(module_id, providers),
        "providers": providers,
    }


@router.put("/api/modules/{module_id}/provider")
def set_module_provider(module_id: str, body: dict[str, Any]) -> dict[str, Any]:
    _module_or_404(module_id)
    provider_id = str(body.get("provider_id") or body.get("id") or "").strip()
    provider = row(
        "SELECT * FROM module_providers WHERE module_id = ? AND id = ?",
        (module_id, provider_id),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found for module")
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (f"source_os.{module_id}.active_provider", provider_id),
    )
    return {
        "module_id": module_id,
        "activeProvider": provider_id,
        "provider": _provider_response(provider),
        "accepted": True,
        "status": "saved",
    }


@router.post("/api/modules/{module_id}/providers/{provider_id}/validate")
def validate_module_provider(module_id: str, provider_id: str) -> dict[str, Any]:
    _module_or_404(module_id)
    provider = row(
        "SELECT * FROM module_providers WHERE module_id = ? AND id = ?",
        (module_id, provider_id),
    )
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found for module")
    return {
        "module_id": module_id,
        "provider_id": provider_id,
        "accepted": False,
        "status": "not_configured",
        "reason": "Provider smoke validation requires a running Blender session and MCP client; no safe runner is configured yet.",
        "verifyCommands": _json_array(provider.get("verify_commands")),
    }


@router.post("/api/modules/runtime/verify-all")
def verify_all_module_runtimes(body: dict[str, Any] | None = None) -> dict[str, Any]:
    _sync_registry_once()
    actor = _safe_actor(str((body or {}).get("actor") or "operator"))
    section = str((body or {}).get("section") or "").strip() or None
    result = rows(
        "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
        (section, section),
    )
    records: list[dict[str, Any]] = []
    counts = {
        "ready": 0,
        "source_ready": 0,
        "setup_required": 0,
        "not_installed": 0,
        "blocked": 0,
    }
    for mod in result:
        synced = _sync_module_status(mod)
        runtime = _module_runtime_probe(synced, live=True)
        status = str(runtime.get("status") or "blocked")
        if status in counts:
            counts[status] += 1
        else:
            counts["blocked"] += 1
        records.append(
            {
                "module_id": synced["id"],
                "display": synced.get("display_name"),
                "section": synced.get("section"),
                "status": status,
                "runtime_ready": status == "ready",
                "verifier": runtime.get("verifier"),
                "kind": runtime.get("kind"),
                "path": runtime.get("path"),
                "capabilities": runtime.get("capabilities") or [],
                "reason": runtime.get("reason"),
                "setup_steps": (runtime.get("setup_steps") or [])[:4],
                "proof_source": runtime.get("proof_source"),
                "output_head_sha256": _sha256_text("\n".join(runtime.get("output_head") or [])),
            }
        )
    proof_event_id = _append_module_proof(
        "source_module.runtime_verification_batch.completed",
        actor,
        {
            "section": section,
            "count": len(records),
            "counts": counts,
            "records": records,
        },
    )
    return {
        "accepted": counts["blocked"] == 0,
        "status": "completed" if counts["blocked"] == 0 else "blocked",
        "section": section,
        "count": len(records),
        "counts": counts,
        "all_runtime_ready": counts["ready"] == len(records) and len(records) > 0,
        "records": records,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/runtime/setup-queue")
def create_module_runtime_setup_queue(body: dict[str, Any] | None = None) -> dict[str, Any]:
    actor = _safe_actor(str((body or {}).get("actor") or "operator"))
    section = str((body or {}).get("section") or "").strip() or None
    return _runtime_setup_queue_payload(section=section, actor=actor, append_proof=True)


@router.get("/api/modules/runtime/setup-queue")
def module_runtime_setup_queue_status(section: str | None = None) -> dict[str, Any]:
    return _runtime_setup_queue_payload(section=section, append_proof=False)


@router.get("/api/modules/runtime/gaps")
def module_runtime_gaps(section: str | None = None) -> dict[str, Any]:
    payload = _runtime_setup_queue_payload(section=section, append_proof=False)
    records = [record for record in payload["records"] if not record.get("runtime_ready")]
    by_launch_kind = Counter(str(record.get("launch_kind") or "unknown") for record in records)
    by_section = Counter(str(record.get("section") or "unknown") for record in records)
    return {
        "status": "ready",
        "section": section,
        "total_modules": payload["count"],
        "runtime_ready": payload["counts"]["runtime_ready"],
        "gap_count": len(records),
        "blocked": payload["counts"]["blocked"],
        "by_launch_kind": dict(sorted(by_launch_kind.items())),
        "by_section": dict(sorted(by_section.items())),
        "recommendations": [
            {
                "launch_kind": launch_kind,
                "count": count,
                "next_verifier": RUNNER_RECOMMENDATIONS.get(
                    launch_kind,
                    "Register a safe module-specific verifier before enabling runtime actions.",
                ),
            }
            for launch_kind, count in sorted(by_launch_kind.items())
        ],
        "records": [
            {
                "module_id": record["module_id"],
                "display": record.get("display"),
                "section": record.get("section"),
                "launch_kind": record.get("launch_kind"),
                "runner_status": record.get("runner_status"),
                "next_action": record.get("next_action"),
                "reason": record.get("reason"),
            }
            for record in records
        ],
        "agent_gate": payload["agent_gate"],
    }


@router.get("/api/modules/runtime/runner-contracts")
def module_runtime_runner_contracts(section: str | None = None) -> dict[str, Any]:
    """Return proof-backed Hermes Agent runner contracts for Source OS modules."""
    _sync_registry_once()
    result = rows(
        "SELECT * FROM modules WHERE (? IS NULL OR section = ?) ORDER BY section, display_name",
        (section, section),
    )
    contracts = module_runner_contracts([_sync_module_status(mod) for mod in result])
    return {
        **contracts,
        "section": section,
        "execution_mode": "contract_only_until_registered_runner_passes",
        "agent_gate": "Hermes Agents may execute app actions only when agent_executable=true. read_only_runner_available rows may re-run metadata/API proof only; executable_path_runner_available rows may read executable metadata only; python_import_repair_available rows may read source/dependency metadata only; cli_install_config_available rows may read Slic3r/SuperSlicer source/schema/profile metadata only; npm_package_preflight_available rows may read package metadata/script names only; every other row remains Verify/Setup Plan only.",
    }


@router.get("/api/modules/runtime/verifiers")
def module_runtime_verifiers() -> dict[str, Any]:
    """W18-A13 — response cached for ``RUNTIME_RESPONSE_CACHE_TTL_S``.

    Audit W18-A3 measured cold-start >20s here because the underlying
    ``_runtime_setup_queue_payload`` traverses 60 modules and probes
    each runtime status. The response cache keeps the FE side under
    the 15s AbortSignal timeout and the action-catalog under 8s.
    """
    return _cached_runtime_response("verifiers", _build_module_runtime_verifiers)


def _build_module_runtime_verifiers() -> dict[str, Any]:
    _sync_registry_once()
    verifier_rows = rows(
        """
        SELECT module_id, label, runner_kind, tool_key, executable_path,
               capabilities, execute, timeout_s, enabled, proof_gate_version,
               updated_at
          FROM module_runtime_verifiers
         ORDER BY module_id
        """
    )
    modules = rows("SELECT id, display_name, section FROM modules ORDER BY section, display_name")
    registered_ids = set(registered_runtime_probe_ids())
    setup_queue = _runtime_setup_queue_payload(section=None, append_proof=False)
    return {
        "status": "ready",
        "count": len(verifier_rows),
        "enabled_count": sum(1 for item in verifier_rows if item.get("enabled")),
        "registered_ids": sorted(registered_ids),
        "total_modules": len(modules),
        "runtime_ready": setup_queue["counts"]["runtime_ready"],
        "runner_gap": setup_queue["counts"]["runner_not_registered"],
        "blocked": setup_queue["counts"]["blocked"],
        "verifiers": [
            {
                "module_id": item["module_id"],
                "label": item["label"],
                "runner_kind": item["runner_kind"],
                "tool_key": item["tool_key"],
                "path": item["executable_path"],
                "capabilities": _json_array(item.get("capabilities")),
                "execute": bool(item["execute"]),
                "timeout_s": item["timeout_s"],
                "enabled": bool(item["enabled"]),
                "proof_gate_version": item["proof_gate_version"],
                "updated_at": item["updated_at"],
                "registered": item["module_id"] in registered_ids,
            }
            for item in verifier_rows
        ],
    }


@router.get("/api/modules/runtime/agent-cli-readiness")
def module_agent_cli_readiness() -> dict[str, Any]:
    """W18-A13 — response cached for ``RUNTIME_RESPONSE_CACHE_TTL_S``.

    Audit W18-A3 measured cold-start >20s because the handler probes
    runtime status for every module via ``_sync_module_status`` +
    ``_agent_cli_readiness_record``. The cache turns subsequent calls
    into a constant-time dictionary lookup.
    """
    return _cached_runtime_response("agent_cli_readiness", _build_module_agent_cli_readiness)


def _build_module_agent_cli_readiness() -> dict[str, Any]:
    _sync_registry_once()
    module_rows = rows(
        """
        SELECT id, display_name, section, launch_kind, install_state, local_path, repo_url
          FROM modules
         ORDER BY section, display_name
        """
    )
    records = [_agent_cli_readiness_record(_sync_module_status(mod)) for mod in module_rows]
    tier_counts = Counter(record["agent_execution_tier"] for record in records)
    verified_cli = [
        record["module_id"]
        for record in records
        if record["agent_execution_tier"] == "verified_agent_cli"
    ]
    launcher_only = [
        record["module_id"]
        for record in records
        if record["agent_execution_tier"] == "launcher_metadata_only"
    ]
    runner_gaps = [
        record["module_id"] for record in records if record["agent_execution_tier"].endswith("_gap")
    ]
    read_only_runners = [
        record["module_id"] for record in records if record["read_only_runner_available"]
    ]
    executable_path_runners = [
        record["module_id"] for record in records if record["executable_path_runner_available"]
    ]
    python_import_repair_runners = [
        record["module_id"] for record in records if record["python_import_repair_available"]
    ]
    cli_install_config_runners = [
        record["module_id"] for record in records if record["cli_install_config_available"]
    ]
    npm_package_preflight_runners = [
        record["module_id"] for record in records if record["npm_package_preflight_available"]
    ]
    return {
        "status": "ready",
        "count": len(records),
        "rule": "If an app offers a CLI, Hermes3D must prefer a bounded CLI verifier and Hermes Agent runner; desktop launcher metadata is not agent CLI readiness.",
        "counts": dict(sorted(tier_counts.items())),
        "verified_agent_cli": len(verified_cli),
        "read_only_runner_available": len(read_only_runners),
        "executable_path_runner_available": len(executable_path_runners),
        "python_import_repair_available": len(python_import_repair_runners),
        "cli_install_config_available": len(cli_install_config_runners),
        "npm_package_preflight_available": len(npm_package_preflight_runners),
        "launcher_metadata_only": len(launcher_only),
        "runner_gaps": len(runner_gaps),
        "verified_agent_cli_modules": verified_cli,
        "read_only_runner_modules": read_only_runners,
        "executable_path_runner_modules": executable_path_runners,
        "python_import_repair_modules": python_import_repair_runners,
        "cli_install_config_modules": cli_install_config_runners,
        "npm_package_preflight_modules": npm_package_preflight_runners,
        "launcher_metadata_only_modules": launcher_only,
        "records": records,
    }


def _agent_cli_readiness_record(mod: dict[str, Any]) -> dict[str, Any]:
    runtime = _module_runtime_probe(mod, live=False)
    contract = module_runner_contract(mod)
    runtime_status = str(runtime.get("status") or "blocked")
    kind = str(runtime.get("kind") or mod.get("launch_kind") or "unknown")
    proof_gate = str(runtime.get("proof_gate_version") or "")
    launch_kind = str(mod.get("launch_kind") or "unknown")
    executed = bool(runtime.get("executed"))
    execution_tier = "runner_gap"
    if runtime_status == "ready" and kind in {"cli", "python_module_cli"} and executed:
        execution_tier = "verified_agent_cli"
    elif runtime_status == "ready" and (
        proof_gate == "desktop-launcher-metadata-v1" or (kind == "desktop_app" and not executed)
    ):
        execution_tier = "launcher_metadata_only"
    elif runtime_status == "ready" and kind in {
        "python_import",
        "python_source_import",
        "node_package",
    }:
        execution_tier = "package_or_import_ready"
    elif runtime_status == "ready" and kind == "moonraker_fleet":
        execution_tier = "service_api_ready"
    elif runtime_status == "ready" and kind == "source_inventory":
        execution_tier = "source_reference_ready"
    elif launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        execution_tier = "cli_preferred_gap"
    elif launch_kind in CLI_POSSIBLE_LAUNCH_KINDS:
        execution_tier = f"{launch_kind}_gap"
    return {
        "module_id": mod["id"],
        "display": mod.get("display_name"),
        "section": mod.get("section"),
        "launch_kind": launch_kind,
        "agent_execution_tier": execution_tier,
        "runtime_status": runtime_status,
        "verifier": runtime.get("verifier"),
        "verifier_kind": kind,
        "proof_gate_version": proof_gate,
        "path": runtime.get("path") or mod.get("local_path"),
        "executed": executed,
        "return_code": runtime.get("return_code"),
        "capabilities": list(runtime.get("capabilities") or []),
        "reason": runtime.get("reason"),
        "read_only_runner_available": bool(contract.get("read_only_runner_available")),
        "read_only_runner_route": f"/api/modules/{mod['id']}/runtime/read-only-runner"
        if contract.get("read_only_runner_available")
        else None,
        "executable_path_runner_available": bool(contract.get("executable_path_runner_available")),
        "executable_path_runner_route": f"/api/modules/{mod['id']}/runtime/executable-path-runner"
        if contract.get("executable_path_runner_available")
        else None,
        "python_import_repair_available": bool(contract.get("python_import_repair_available")),
        "python_import_repair_route": f"/api/modules/{mod['id']}/runtime/python-import-repair-runner"
        if contract.get("python_import_repair_available")
        else None,
        "cli_install_config_available": bool(contract.get("cli_install_config_available")),
        "cli_install_config_route": f"/api/modules/{mod['id']}/runtime/cli-install-config-runner"
        if contract.get("cli_install_config_available")
        else None,
        "npm_package_preflight_available": bool(contract.get("npm_package_preflight_available")),
        "npm_package_preflight_route": f"/api/modules/{mod['id']}/runtime/npm-package-runner"
        if contract.get("npm_package_preflight_available")
        else None,
        "next_action": _agent_cli_next_action(
            execution_tier, launch_kind, str(runtime.get("verifier") or "")
        ),
    }


def _agent_cli_next_action(execution_tier: str, launch_kind: str, verifier: str) -> str:
    if execution_tier == "verified_agent_cli":
        return f"Expose bounded Hermes Agent runner using {verifier}; add dry-run smoke before mutating outputs."
    if execution_tier == "launcher_metadata_only":
        return "Do not call this agent CLI-ready; add CLI/API smoke or explicit desktop bridge before agent execution."
    if execution_tier in {"package_or_import_ready", "service_api_ready"}:
        return "Add a tiny non-mutating worker/API smoke gate before enabling write actions."
    if execution_tier == "source_reference_ready":
        return "Use as read-only reference data; do not expose runnable actions unless a real adapter exists."
    if launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        return "Locate/install the CLI executable or document no local CLI with proof; keep agent actions disabled."
    if launch_kind == "npm_package":
        return "Run npm package metadata preflight; keep install/run disabled until a sandboxed npm runner and node package verifier pass."
    return "Register a safe module-specific verifier and runner before Hermes Agents can execute this app."


@router.get("/api/modules/runtime/cli-surface")
def module_cli_surface_audit() -> dict[str, Any]:
    """Return the latest proof-backed CLI/service surface audit for the 60 Source OS apps."""
    if not SOURCE_CLI_SURFACE_AUDIT_PATH.exists():
        return {
            "status": "missing",
            "count": 0,
            "summary": {},
            "records": [],
            "proof_source": str(SOURCE_CLI_SURFACE_AUDIT_PATH),
            "reason": "Run scripts/audit_source_cli_surface.py before exposing CLI surface counts.",
        }
    try:
        payload = json.loads(SOURCE_CLI_SURFACE_AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="CLI surface audit proof is malformed."
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500, detail="CLI surface audit proof did not contain an object."
        )
    return {
        **payload,
        "status": "ready",
        "count": len(payload.get("records") or []),
        "proof_source": str(SOURCE_CLI_SURFACE_AUDIT_PATH),
    }


@router.post("/api/modules/{module_id}/runtime/verify")
def verify_module_runtime(module_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(str((body or {}).get("actor") or "operator"))
    runtime = _module_runtime_probe(mod, live=True)
    proof_event_id = _append_module_proof(
        "source_module.runtime_verification.completed",
        actor,
        {
            "module_id": module_id,
            "display": mod.get("display_name"),
            "runtime": {key: value for key, value in runtime.items() if key not in {"output_head"}},
            "output_head_sha256": _sha256_text("\n".join(runtime.get("output_head") or [])),
        },
    )
    return {
        "module_id": module_id,
        "accepted": runtime["status"] in {"ready", "source_ready"},
        "runtime_ready": runtime["status"] == "ready",
        "status": runtime["status"],
        "runtime": runtime,
        "proof_event_id": proof_event_id,
    }


@router.get("/api/modules/{module_id}/runtime/runner-contract")
def get_module_runtime_runner_contract(module_id: str) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    return {
        "status": "ready",
        "module_id": module_id,
        "contract": module_runner_contract(mod),
    }


@router.post("/api/modules/{module_id}/runtime/read-only-runner")
def create_module_runtime_read_only_runner(
    module_id: str,
    body: ModuleRuntimeReadOnlyRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    contract = module_read_only_runner_contract(mod, live_probe=True)
    proof_event_id = _append_module_proof(
        "source_module.runtime_read_only_runner.proved"
        if contract["accepted"]
        else "source_module.runtime_read_only_runner.blocked",
        actor,
        {
            "module_id": module_id,
            "accepted": contract["accepted"],
            "status": contract["status"],
            "runner_family": contract["runner_family"],
            "verifier_kind": contract["verifier_kind"],
            "proof_gate_version": contract.get("proof_gate_version"),
            "contract": contract,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(contract["accepted"]),
        "status": str(contract["status"]),
        "runtime_ready": bool(contract["runtime_ready"]),
        "execution_mode": str(contract["execution_mode"]),
        "contract": contract,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/executable-path-runner")
def create_module_runtime_executable_path_runner(
    module_id: str,
    body: ModuleRuntimeExecutablePathRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    contract = module_executable_path_runner_contract(mod)
    proof_event_id = _append_module_proof(
        "source_module.runtime_executable_path_runner.proved"
        if contract["accepted"]
        else "source_module.runtime_executable_path_runner.blocked",
        actor,
        {
            "module_id": module_id,
            "accepted": contract["accepted"],
            "status": contract["status"],
            "verifier_kind": contract["verifier_kind"],
            "proof_gate_version": contract.get("proof_gate_version"),
            "executable_sha256": (contract.get("executable") or {}).get("sha256"),
            "contract": contract,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(contract["accepted"]),
        "status": str(contract["status"]),
        "runtime_ready": bool(contract["runtime_ready"]),
        "execution_mode": str(contract["execution_mode"]),
        "contract": contract,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/python-import-repair-runner")
def create_module_runtime_python_import_repair_runner(
    module_id: str,
    body: ModuleRuntimePythonImportRepairRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    contract = module_python_import_repair_runner_contract(mod)
    manifest_hashes = [
        item.get("sha256")
        for item in contract.get("repair", {}).get("manifests", [])
        if item.get("sha256")
    ]
    proof_event_id = _append_module_proof(
        "source_module.runtime_python_import_repair.preflighted"
        if contract["accepted"]
        else "source_module.runtime_python_import_repair.blocked",
        actor,
        {
            "module_id": module_id,
            "accepted": contract["accepted"],
            "status": contract["status"],
            "verifier_kind": contract["verifier_kind"],
            "proof_gate_version": contract.get("proof_gate_version"),
            "import_module": contract.get("repair", {}).get("import_module"),
            "manifest_hashes": manifest_hashes,
            "contract": contract,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(contract["accepted"]),
        "status": str(contract["status"]),
        "runtime_ready": bool(contract["runtime_ready"]),
        "execution_mode": str(contract["execution_mode"]),
        "contract": contract,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/cli-install-config-runner")
def create_module_runtime_cli_install_config_runner(
    module_id: str,
    body: ModuleRuntimeCliInstallConfigRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    contract = module_cli_install_config_runner_contract(mod)
    candidate_hashes = [
        item.get("sha256")
        for item in contract.get("install_config", {}).get("detected_candidate_executables", [])
        if item.get("sha256")
    ]
    schema_hash = contract.get("install_config", {}).get("adapter_schema", {}).get("sha256")
    config_hashes = [
        item.get("sha256")
        for item in contract.get("install_config", {}).get("config_files", [])
        if item.get("sha256")
    ]
    proof_event_id = _append_module_proof(
        "source_module.runtime_cli_install_config.preflighted"
        if contract["accepted"]
        else "source_module.runtime_cli_install_config.blocked",
        actor,
        {
            "module_id": module_id,
            "accepted": contract["accepted"],
            "status": contract["status"],
            "verifier_kind": contract["verifier_kind"],
            "proof_gate_version": contract.get("proof_gate_version"),
            "schema_hash": schema_hash,
            "config_hashes": config_hashes,
            "candidate_executable_hashes": candidate_hashes,
            "contract": contract,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(contract["accepted"]),
        "status": str(contract["status"]),
        "runtime_ready": bool(contract["runtime_ready"]),
        "execution_mode": str(contract["execution_mode"]),
        "contract": contract,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/npm-package-runner")
def create_module_runtime_npm_package_runner(
    module_id: str,
    body: ModuleRuntimeNpmPackageRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    contract = module_npm_package_runner_contract(mod)
    package_json = contract.get("package", {}).get("package_json", {})
    lockfile_hashes = [
        item.get("sha256")
        for item in contract.get("package", {}).get("lockfiles", [])
        if item.get("sha256")
    ]
    proof_event_id = _append_module_proof(
        "source_module.runtime_npm_package.preflighted"
        if contract["accepted"]
        else "source_module.runtime_npm_package.blocked",
        actor,
        {
            "module_id": module_id,
            "accepted": contract["accepted"],
            "status": contract["status"],
            "verifier_kind": contract["verifier_kind"],
            "proof_gate_version": contract.get("proof_gate_version"),
            "package_name": package_json.get("name"),
            "package_version": package_json.get("version"),
            "package_json_hash": package_json.get("sha256"),
            "lockfile_hashes": lockfile_hashes,
            "script_names": package_json.get("script_names") or [],
            "contract": contract,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(contract["accepted"]),
        "status": str(contract["status"]),
        "runtime_ready": bool(contract["runtime_ready"]),
        "execution_mode": str(contract["execution_mode"]),
        "contract": contract,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/setup-plan")
def create_module_runtime_setup_plan(
    module_id: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(str((body or {}).get("actor") or "operator"))
    record = _runtime_setup_plan_record(mod)
    proof_event_id = _append_module_proof(
        "source_module.runtime_setup_plan.planned",
        actor,
        {
            "module_id": module_id,
            "record": record,
        },
    )
    return {
        "module_id": module_id,
        "accepted": record["runner_status"] != "blocked",
        "status": "planned" if record["runner_status"] != "blocked" else "blocked",
        "record": record,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/start-runner")
def create_module_runtime_start_runner(
    module_id: str,
    body: ModuleRuntimeStartRunnerRequest | None = None,
) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    execute_requested = bool(body.execute) if body else False
    contract = module_service_start_runner_contract(mod, live_probe=True)
    start_result = (
        start_source_service_runner(mod, contract, actor=actor)
        if execute_requested
        else {
            "status": contract["status"],
            "accepted": bool(
                contract.get("start_preflight_passed") or contract.get("runtime_ready")
            ),
            "runtime_ready": bool(contract.get("runtime_ready")),
            "execution_mode": contract["execution_mode"],
        }
    )
    proof_event_id = _append_module_proof(
        "source_module.runtime_start_runner.started"
        if execute_requested
        else "source_module.runtime_start_runner.preflighted",
        actor,
        {
            "module_id": module_id,
            "execute_requested": execute_requested,
            "contract": contract,
            "start_result": start_result,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(start_result.get("accepted")),
        "status": str(start_result.get("status") or contract["status"]),
        "runtime_ready": bool(start_result.get("runtime_ready")),
        "execution_mode": str(start_result.get("execution_mode") or contract["execution_mode"]),
        "contract": contract,
        "start_result": start_result,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/runtime/stop-runner")
def stop_module_runtime_runner(
    module_id: str,
    body: ModuleRuntimeStartRunnerRequest | None = None,
) -> dict[str, Any]:
    _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    stop_result = stop_source_service_runner(module_id, actor=actor)
    proof_event_id = _append_module_proof(
        "source_module.runtime_start_runner.stopped",
        actor,
        {
            "module_id": module_id,
            "stop_result": stop_result,
        },
    )
    return {
        "module_id": module_id,
        "accepted": bool(stop_result.get("accepted")),
        "status": str(stop_result.get("status") or "unknown"),
        "stop_result": stop_result,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/install")
async def install_module(module_id: str) -> dict[str, Any]:
    check_s1_lock(module_id)
    mod = _sync_module_status(_module_or_404(module_id))
    repo_url = mod.get("repo_url")
    local_path = mod.get("local_path")
    if not repo_url:
        raise HTTPException(
            status_code=409,
            detail="No verified source repository URL is available for this module.",
        )
    if not local_path:
        raise HTTPException(
            status_code=409, detail="No local source checkout path is configured for this module."
        )

    target = Path(str(local_path))
    if target.exists():
        status = inspect_source_path(str(target), str(repo_url))
        _write_source_status(module_id, status, synced=True)
        return {
            "module_id": module_id,
            "state": status["install_state"],
            "local_path": str(target),
            "repo": repo_url,
            "notes": "Existing local source checkout detected; no clone was started.",
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    execute(
        "UPDATE modules SET install_state = 'downloading', install_progress = 1, health = 'unknown', updated_at = datetime('now') WHERE id = ?",
        (module_id,),
    )
    cmd = ["git", "clone", "--depth", "1", str(repo_url), str(target)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        status = {
            "install_state": "failed",
            "install_progress": 0,
            "detected_version": None,
            "health": "failed",
        }
        _write_source_status(module_id, status)
        raise HTTPException(status_code=502, detail=f"git clone failed to start: {exc}") from exc

    if proc.returncode != 0:
        status = {
            "install_state": "failed",
            "install_progress": 0,
            "detected_version": None,
            "health": "failed",
        }
        _write_source_status(module_id, status)
        detail = (proc.stderr or proc.stdout or f"git clone exited {proc.returncode}")[-1200:]
        raise HTTPException(status_code=502, detail=detail)

    status = inspect_source_path(str(target), str(repo_url))
    _write_source_status(module_id, status, synced=True)
    return {
        "module_id": module_id,
        "state": status["install_state"],
        "local_path": str(target),
        "repo": repo_url,
        "detected_version": status["detected_version"],
    }


async def _install_stream(module_id: str) -> AsyncIterator[str]:
    while True:
        mod = _sync_module_status(_module_or_404(module_id))
        yield f"data: {json.dumps({'module_id': module_id, 'state': mod.get('install_state'), 'progress': mod.get('install_progress') or 0})}\n\n"
        if mod.get("install_state") not in {"downloading", "installing"}:
            return
        await asyncio.sleep(1)


@router.get("/api/modules/{module_id}/install/stream")
async def install_stream(module_id: str) -> StreamingResponse:
    _module_or_404(module_id)
    return StreamingResponse(_install_stream(module_id), media_type="text/event-stream")


@router.post("/api/modules/{module_id}/detect")
def detect_module(module_id: str) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    local_path = mod.get("local_path")
    status = inspect_source_path(local_path, mod.get("repo_url"))
    _write_source_status(
        module_id, status, synced=bool(local_path and Path(str(local_path)).exists())
    )
    found = status["install_state"] in {"installed", "detected", "healthy"}
    return {
        "module_id": module_id,
        "found": found,
        "version": status["detected_version"],
        "status": status["install_state"],
        "local_path": local_path,
        "repo": mod.get("repo_url"),
        "notes": None if found else "No local source checkout was detected at the configured path.",
    }


@router.post("/api/modules/{module_id}/launch")
def launch_module(module_id: str) -> dict[str, Any]:
    check_s1_lock(module_id)
    _module_or_404(module_id)
    if module_id == "printrun":
        result = PrintrunAdapter().open_external()
        return {
            "module_id": module_id,
            "success": result.ok,
            "status": "launched" if result.ok else "not_configured",
            "pid": result.pid,
            "notes": result.detail,
        }
    return {
        "module_id": module_id,
        "success": False,
        "status": "not_configured",
        "notes": "No real launch bridge is configured for this module.",
    }


@router.post("/api/modules/{module_id}/stop")
def stop_module(module_id: str) -> dict[str, Any]:
    _module_or_404(module_id)
    if module_id == "printrun":
        result = PrintrunAdapter().stop_external()
        return {
            "module_id": module_id,
            "stopped": result.ok,
            "status": "stopped" if result.ok else "not_running",
            "pid": result.pid,
            "reason": result.detail,
        }
    return {
        "module_id": module_id,
        "stopped": False,
        "status": "not_configured",
        "reason": "No launch bridge is configured.",
    }


@router.post("/api/modules/{module_id}/update/backup", status_code=201)
def backup_module_source(module_id: str, body: ModuleBackupRequest | None = None) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    backup = _create_source_backup(
        mod,
        actor=actor,
        note=(body.note if body else None) or "manual source app pre-update backup",
    )
    proof_event_id = _append_module_proof(
        "source_module.backup.created",
        actor,
        {
            "module_id": module_id,
            "backup": _public_backup(backup),
        },
    )
    _record_artifact(
        backup["backup_id"],
        "source_module_backup",
        actor,
        "SOURCE_UPDATE",
        module_id,
        f"{mod.get('display_name') or module_id} source backup",
        backup["bundle_path"],
        {"module_id": module_id, "proof_event_id": proof_event_id, "commit": backup.get("commit")},
    )
    return {**_public_backup(backup), "proof_event_id": proof_event_id}


@router.post("/api/modules/{module_id}/update/check")
def check_module_update(module_id: str, body: ModuleUpdateRequest | None = None) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    path = _module_git_path(mod)
    state = _git_state(path)
    if state["dirty"]:
        proof_event_id = _append_module_proof(
            "source_module.update_check.blocked",
            actor,
            {
                "module_id": module_id,
                "status": "blocked",
                "reason": "dirty_checkout",
                "dirty_entries": state["dirty_entries"][:20],
            },
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Source checkout has uncommitted changes; create a backup and clean/commit changes before update check.",
                "proof_event_id": proof_event_id,
            },
        )
    remote = _remote_target(path, state)
    status = "current"
    if remote["commit"] and remote["commit"] != state["commit"]:
        status = "outdated"
    payload = {
        "module_id": module_id,
        "status": status,
        "current_commit": state["commit"],
        "remote_commit": remote["commit"],
        "branch": state["branch"],
        "remote_ref": remote["ref"],
        "remote_url": _redact_url(state["remote"]),
        "backup_available": _latest_source_backup(module_id) is not None,
        "checked_at": _utc_stamp(),
    }
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (f"source_module.{module_id}.latest_update_check", json.dumps(payload, sort_keys=True)),
    )
    proof_event_id = _append_module_proof("source_module.update_check.completed", actor, payload)
    return {**payload, "proof_event_id": proof_event_id}


@router.post("/api/modules/{module_id}/update/apply")
def apply_module_update(module_id: str, body: ModuleUpdateRequest) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor)
    path = _module_git_path(mod)
    state = _git_state(path)
    if state["dirty"]:
        proof_event_id = _append_module_proof(
            "source_module.update.blocked",
            actor,
            {
                "module_id": module_id,
                "status": "blocked",
                "reason": "dirty_checkout",
                "dirty_entries": state["dirty_entries"][:20],
            },
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Source checkout has uncommitted changes; update blocked before mutation.",
                "proof_event_id": proof_event_id,
            },
        )
    backup = _select_source_backup(module_id, body.backup_id)
    if not backup:
        proof_event_id = _append_module_proof(
            "source_module.update.blocked",
            actor,
            {"module_id": module_id, "status": "blocked", "reason": "backup_required"},
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Create a source backup before applying an update.",
                "proof_event_id": proof_event_id,
            },
        )
    if backup.get("commit") != state["commit"]:
        proof_event_id = _append_module_proof(
            "source_module.update.blocked",
            actor,
            {
                "module_id": module_id,
                "status": "blocked",
                "reason": "stale_backup",
                "backup_commit": backup.get("commit"),
                "current_commit": state["commit"],
            },
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Latest backup does not match the current checkout commit; create a fresh backup.",
                "proof_event_id": proof_event_id,
            },
        )
    remote = _remote_target(path, state)
    if not remote["commit"]:
        proof_event_id = _append_module_proof(
            "source_module.update.blocked",
            actor,
            {"module_id": module_id, "status": "blocked", "reason": "remote_unavailable"},
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Could not resolve a remote update target for this checkout.",
                "proof_event_id": proof_event_id,
            },
        )
    if remote["commit"] == state["commit"]:
        proof_event_id = _append_module_proof(
            "source_module.update.noop",
            actor,
            {
                "module_id": module_id,
                "status": "current",
                "commit": state["commit"],
                "backup_id": backup["backup_id"],
            },
        )
        return {
            "accepted": True,
            "updated": False,
            "status": "current",
            "module_id": module_id,
            "backup_id": backup["backup_id"],
            "commit": state["commit"],
            "proof_event_id": proof_event_id,
        }
    fetch = _run_git(path, ["fetch", "origin", remote["ref"]], timeout=120)
    if fetch.returncode != 0:
        proof_event_id = _append_module_proof(
            "source_module.update.failed",
            actor,
            {
                "module_id": module_id,
                "status": "fetch_failed",
                "backup_id": backup["backup_id"],
                "stderr": _redact_text(fetch.stderr)[-1200:],
            },
        )
        raise HTTPException(
            status_code=502,
            detail={
                "reason": "git fetch failed; checkout was not updated.",
                "proof_event_id": proof_event_id,
            },
        )
    merge = _run_git(path, ["merge", "--ff-only", "FETCH_HEAD"], timeout=180)
    if merge.returncode != 0:
        proof_event_id = _append_module_proof(
            "source_module.update.failed",
            actor,
            {
                "module_id": module_id,
                "status": "fast_forward_failed",
                "backup_id": backup["backup_id"],
                "stderr": _redact_text(merge.stderr)[-1200:],
            },
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Fast-forward update failed; manual review is required before rollback.",
                "proof_event_id": proof_event_id,
            },
        )
    final_state = _git_state(path)
    gates = _source_update_gates(path, mod, before=state, after=final_state)
    passed = all(gate["status"] == "pass" for gate in gates)
    if not passed:
        rollback = _rollback_to_backup(path, backup)
        proof_event_id = _append_module_proof(
            "source_module.update.rolled_back_after_gate_failure",
            actor,
            {
                "module_id": module_id,
                "status": "rolled_back",
                "backup_id": backup["backup_id"],
                "gates": gates,
                "rollback": rollback,
            },
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Post-update gates failed; rollback attempted.",
                "gates": gates,
                "rollback": rollback,
                "proof_event_id": proof_event_id,
            },
        )
    status = inspect_source_path(mod.get("local_path"), mod.get("repo_url"))
    _write_source_status(module_id, status, synced=True)
    proof_event_id = _append_module_proof(
        "source_module.update.applied",
        actor,
        {
            "module_id": module_id,
            "status": "updated",
            "backup_id": backup["backup_id"],
            "before_commit": state["commit"],
            "after_commit": final_state["commit"],
            "remote_ref": remote["ref"],
            "gates": gates,
        },
    )
    return {
        "accepted": True,
        "updated": True,
        "status": "updated",
        "module_id": module_id,
        "backup_id": backup["backup_id"],
        "before_commit": state["commit"],
        "after_commit": final_state["commit"],
        "gates": gates,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/modules/{module_id}/rollback")
def rollback_module(module_id: str, body: ModuleRollbackRequest | None = None) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    actor = _safe_actor(body.actor if body else "operator")
    path = _module_git_path(mod)
    backup = _select_source_backup(module_id, body.backup_id if body else None)
    if not backup:
        proof_event_id = _append_module_proof(
            "source_module.rollback.blocked",
            actor,
            {"module_id": module_id, "status": "blocked", "reason": "backup_required"},
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "Rollback requires a recorded source module backup.",
                "proof_event_id": proof_event_id,
            },
        )
    current_backup = _create_source_backup(
        mod, actor=actor, note=f"automatic backup before rollback to {backup['backup_id']}"
    )
    result = _rollback_to_backup(path, backup)
    status = inspect_source_path(mod.get("local_path"), mod.get("repo_url"))
    _write_source_status(module_id, status, synced=True)
    proof_event_id = _append_module_proof(
        "source_module.rollback.completed" if result["ok"] else "source_module.rollback.failed",
        actor,
        {
            "module_id": module_id,
            "target_backup_id": backup["backup_id"],
            "pre_rollback_backup_id": current_backup["backup_id"],
            "result": result,
        },
    )
    return {
        "module_id": module_id,
        "rollback_started": True,
        "status": "rolled_back" if result["ok"] else "rollback_failed",
        "target_backup_id": backup["backup_id"],
        "pre_rollback_backup_id": current_backup["backup_id"],
        "proof_event_id": proof_event_id,
        **result,
    }


def _module_git_path(mod: dict[str, Any]) -> Path:
    local_path = mod.get("local_path")
    if not local_path:
        raise HTTPException(
            status_code=409, detail="No local source checkout path is configured for this module."
        )
    path = Path(str(local_path)).resolve()
    if not path.exists():
        raise HTTPException(status_code=409, detail="Local source checkout path is missing.")
    if not (path / ".git").exists():
        raise HTTPException(
            status_code=409,
            detail="Local source path is not a git checkout; update requires .git metadata.",
        )
    return path


def _create_source_backup(mod: dict[str, Any], *, actor: str, note: str) -> dict[str, Any]:
    path = _module_git_path(mod)
    state = _git_state(path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_id = f"{stamp}_{_safe_component(mod['id'])}_{state['commit'][:12]}"
    module_dir = SOURCE_UPDATE_BACKUP_ROOT / _safe_component(mod["id"])
    module_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = module_dir / f"{backup_id}.bundle"
    meta_path = module_dir / f"{backup_id}.json"
    bundle = _run_git(path, ["bundle", "create", str(bundle_path), "--all"], timeout=300)
    if bundle.returncode != 0 or not bundle_path.exists():
        raise HTTPException(
            status_code=502,
            detail=f"git bundle backup failed: {_redact_text(bundle.stderr or bundle.stdout)[-1000:]}",
        )
    dirty_zip_path = None
    if state["dirty_entries"]:
        dirty_zip_path = str(
            _zip_dirty_files(path, module_dir / f"{backup_id}.dirty.zip", state["dirty_entries"])
        )
    metadata = {
        "backup_id": backup_id,
        "module_id": mod["id"],
        "display": mod.get("display_name"),
        "checkout_path": str(path),
        "repo_url": _redact_url(mod.get("repo_url")),
        "remote": _redact_url(state["remote"]),
        "branch": state["branch"],
        "commit": state["commit"],
        "exact_tag": state["exact_tag"],
        "nearest_tag": state["nearest_tag"],
        "dirty": state["dirty"],
        "dirty_entries": state["dirty_entries"][:100],
        "bundle_path": str(bundle_path),
        "dirty_zip_path": dirty_zip_path,
        "actor": actor,
        "note": note,
        "created_at": _utc_stamp(),
    }
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (f"source_module.{mod['id']}.latest_backup", json.dumps(metadata, sort_keys=True)),
    )
    return metadata


def _zip_dirty_files(path: Path, target: Path, dirty_entries: list[str]) -> Path:
    root = path.resolve()
    with zipfile.ZipFile(target, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in dirty_entries:
            rel = entry[3:].strip() if len(entry) > 3 else entry.strip()
            if " -> " in rel:
                rel = rel.split(" -> ", 1)[1]
            rel = rel.strip('"')
            if not rel:
                continue
            candidate = (root / rel).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            if candidate.is_file():
                archive.write(candidate, rel)
            elif candidate.is_dir():
                for child in candidate.rglob("*"):
                    if child.is_file():
                        archive.write(child, child.relative_to(root))
    return target


def _git_state(path: Path) -> dict[str, Any]:
    commit = _git_text(path, ["rev-parse", "HEAD"])
    branch = _git_text(path, ["rev-parse", "--abbrev-ref", "HEAD"])
    upstream = _git_text(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    remote = _git_text(path, ["remote", "get-url", "origin"])
    exact_tag = _git_text(path, ["describe", "--tags", "--exact-match"])
    nearest_tag = _git_text(path, ["describe", "--tags", "--abbrev=0"])
    dirty_entries = (_git_text(path, ["status", "--porcelain=v1"]) or "").splitlines()
    return {
        "commit": commit or "",
        "branch": branch if branch and branch != "HEAD" else None,
        "upstream": upstream,
        "remote": remote,
        "exact_tag": exact_tag,
        "nearest_tag": nearest_tag,
        "dirty": bool(dirty_entries),
        "dirty_entries": dirty_entries,
    }


def _remote_target(path: Path, state: dict[str, Any]) -> dict[str, str | None]:
    branch = state.get("branch")
    upstream = state.get("upstream")
    ref = None
    if isinstance(upstream, str) and "/" in upstream:
        ref = "refs/heads/" + upstream.split("/", 1)[1]
    elif isinstance(branch, str):
        ref = "refs/heads/" + branch
    if not ref or not _safe_git_ref(ref):
        ref = "HEAD"
    remote = _run_git(path, ["ls-remote", "origin", ref], timeout=30)
    if remote.returncode != 0:
        return {"ref": ref, "commit": None}
    line = (remote.stdout or "").splitlines()[0] if remote.stdout.splitlines() else ""
    commit = line.split()[0] if line and len(line.split()) >= 2 else None
    return {"ref": ref, "commit": commit}


def _source_update_gates(
    path: Path, mod: dict[str, Any], *, before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    dirty_after = _git_state(path)["dirty_entries"]
    inspected = inspect_source_path(mod.get("local_path"), mod.get("repo_url"))
    return [
        {
            "name": "git_checkout_clean",
            "status": "pass" if not dirty_after else "fail",
            "detail": dirty_after[:20],
        },
        {
            "name": "commit_changed",
            "status": "pass" if before["commit"] != after["commit"] else "fail",
            "detail": {"before": before["commit"], "after": after["commit"]},
        },
        {
            "name": "source_detected",
            "status": "pass"
            if inspected["install_state"] in {"installed", "detected", "healthy"}
            else "fail",
            "detail": inspected["install_state"],
        },
    ]


def _rollback_to_backup(path: Path, backup: dict[str, Any]) -> dict[str, Any]:
    commit = str(backup.get("commit") or "")
    branch = backup.get("branch")
    if not commit:
        return {"ok": False, "reason": "Backup has no recorded commit."}
    pre = _run_git(path, ["rev-parse", "HEAD"], timeout=10)
    if isinstance(branch, str) and _safe_git_ref(branch):
        checkout = _run_git(path, ["checkout", branch], timeout=60)
        if checkout.returncode != 0:
            return {
                "ok": False,
                "reason": "Could not checkout recorded backup branch.",
                "stderr": _redact_text(checkout.stderr)[-800:],
            }
    reset = _run_git(path, ["reset", "--hard", commit], timeout=120)
    post = _run_git(path, ["rev-parse", "HEAD"], timeout=10)
    return {
        "ok": reset.returncode == 0 and (post.stdout or "").strip().startswith(commit[:12]),
        "from": (pre.stdout or "").strip(),
        "to": (post.stdout or "").strip(),
        "stderr": _redact_text(reset.stderr)[-800:],
    }


def _select_source_backup(module_id: str, backup_id: str | None) -> dict[str, Any] | None:
    return (
        _find_source_backup(module_id, backup_id) if backup_id else _latest_source_backup(module_id)
    )


def _latest_source_backup(module_id: str) -> dict[str, Any] | None:
    module_dir = SOURCE_UPDATE_BACKUP_ROOT / _safe_component(module_id)
    if not module_dir.exists():
        return None
    backups = sorted(module_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not backups:
        return None
    try:
        return json.loads(backups[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _find_source_backup(module_id: str, backup_id: str | None) -> dict[str, Any] | None:
    if not backup_id:
        return None
    if not BACKUP_ID_RE.match(backup_id):
        raise HTTPException(status_code=400, detail="Invalid backup_id format.")
    path = (SOURCE_UPDATE_BACKUP_ROOT / _safe_component(module_id) / f"{backup_id}.json").resolve()
    try:
        path.relative_to((SOURCE_UPDATE_BACKUP_ROOT / _safe_component(module_id)).resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid backup_id path.") from exc
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _latest_source_update_check(module_id: str) -> dict[str, Any] | None:
    setting = row(
        "SELECT value FROM settings WHERE key = ?",
        (f"source_module.{module_id}.latest_update_check",),
    )
    if not setting:
        return None
    try:
        parsed = json.loads(str(setting["value"]))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _public_backup(backup: dict[str, Any] | None) -> dict[str, Any] | None:
    if not backup:
        return None
    return {
        "backup_id": backup.get("backup_id"),
        "module_id": backup.get("module_id"),
        "commit": backup.get("commit"),
        "branch": backup.get("branch"),
        "exact_tag": backup.get("exact_tag"),
        "nearest_tag": backup.get("nearest_tag"),
        "dirty": backup.get("dirty"),
        "bundle_path": backup.get("bundle_path"),
        "dirty_zip_path": backup.get("dirty_zip_path"),
        "created_at": backup.get("created_at"),
    }


def _record_artifact(
    artifact_id: str,
    evidence_type: str,
    agent: str,
    stage: str,
    gate: str,
    label: str,
    file_path: str,
    notes: dict[str, Any],
) -> None:
    target = Path(file_path)
    execute(
        """
        INSERT OR REPLACE INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            evidence_type,
            agent,
            stage,
            gate,
            label,
            str(target),
            target.stat().st_size if target.exists() else 0,
            json.dumps(notes, sort_keys=True),
        ),
    )


def _append_module_proof(event_type: str, actor: str, payload: dict[str, Any]) -> str:
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (proof_event_id, event_type, actor, as_json({**payload, "ts_utc": _utc_stamp()})),
    )
    return proof_event_id


def _run_git(path: Path, args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    cmd = ["git", *args]
    try:
        return subprocess.run(
            cmd, cwd=path, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd, 124, stdout=str(exc.stdout or ""), stderr=f"git timed out after {timeout}s"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=str(exc))


def _git_text(path: Path, args: list[str]) -> str | None:
    proc = _run_git(path, args, timeout=10)
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _safe_git_ref(ref: str) -> bool:
    return (
        bool(GIT_REF_RE.match(ref))
        and ".." not in ref
        and not ref.startswith("/")
        and not ref.endswith("/")
    )


def _safe_actor(value: str | None) -> str:
    candidate = (value or "operator").strip()
    return _safe_component(candidate)[:80] or "operator"


def _safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[:180]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_text(value: str | None) -> str:
    return SECRET_RE.sub(
        lambda match: f"{match.group(1) or match.group(3) or ''}[REDACTED]", value or ""
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


@router.get("/api/modules/{module_id}/install-plan")
def install_plan(module_id: str) -> dict[str, Any]:
    mod = _sync_module_status(_module_or_404(module_id))
    repo_url = mod.get("repo_url")
    local_path = mod.get("local_path")
    runtime = _module_runtime_probe(mod)
    steps = ["detect configured local checkout"]
    if repo_url and local_path and mod.get("install_state") == "source_available":
        steps.append("clone full working tree from verified repository")
    if local_path:
        steps.append("verify checkout path exists on disk")
    steps.extend(runtime.get("setup_steps") or [])
    steps.append(
        "report detected git revision; do not claim health until a real runner/proof exists"
    )
    return {
        "module_id": module_id,
        "repo": repo_url,
        "local_path": local_path,
        "steps": steps,
        "checkpoint_strategy": "clone only into configured source checkout path",
        "launch_kind": mod.get("launch_kind"),
        "state": mod.get("install_state"),
        "runtime": runtime,
    }


@router.get("/api/modules/{module_id}/bridge-tasks")
def bridge_tasks(module_id: str) -> list[dict[str, Any]]:
    _module_or_404(module_id)
    return rows("SELECT * FROM bridge_tasks WHERE module_id = ? ORDER BY name", (module_id,))


@router.post("/api/modules/{module_id}/bridge-tasks/{task_id}/run")
def run_bridge_task(module_id: str, task_id: str) -> dict[str, Any]:
    check_s1_lock(module_id)
    _module_or_404(module_id)
    raise HTTPException(
        status_code=409,
        detail={
            "module_id": module_id,
            "task_id": task_id,
            "success": False,
            "status": "not_configured",
            "reason": "No real bridge runner is configured for this module.",
        },
    )
