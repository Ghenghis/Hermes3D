"""Source-backed code history and Hermes Agent programming readiness."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows, utc_now
from hermes3d.db.init import DB_PATH
from hermes3d.services.agent_runtime import env_value, private_env

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = IMPLEMENTATION_ROOT.parent
HISTORY_ROOT = IMPLEMENTATION_ROOT / "var" / "code-history"
MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
MAX_DIFF_BYTES = 1024 * 1024
MAX_FILE_VIEW_BYTES = 512 * 1024
MAX_SEARCH_RESULTS = 200
MAX_PROPOSED_TEXT_BYTES = 1024 * 1024

DENIED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".venv",
    "venv",
}
DENIED_SUFFIXES = {
    ".env",
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".sqlite",
    ".db",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".zip",
    ".7z",
    ".rar",
}


@dataclass(frozen=True)
class SourceRepo:
    id: str
    label: str
    local_path: Path
    remote_url: str
    role: str
    required_files: tuple[str, ...]


SOURCE_REPOS = (
    SourceRepo(
        id="nous_hermes_agent",
        label="Nous Hermes Agent runtime",
        local_path=Path(r"G:\Github\hermes-agent-fresh"),
        remote_url="https://github.com/NousResearch/hermes-agent.git",
        role="primary agent runtime, tools, skills, MCP, delegation, terminal/code loop",
        required_files=("run_agent.py", "model_tools.py", "toolsets.py", "tools/registry.py", "tools/file_tools.py", "tools/terminal_tool.py"),
    ),
    SourceRepo(
        id="atomic_hermes",
        label="Atomic Hermes agent coding patterns",
        local_path=Path(r"G:\Github\atomic-hermes"),
        remote_url="https://github.com/AtomicBot-ai/atomic-hermes.git",
        role="approval bridge, MCP tool, patch parser, checkpoint manager, terminal/file tools, SWE environment, skills",
        required_files=(
            "README.md",
            "run_agent.py",
            "tools/approval.py",
            "tools/checkpoint_manager.py",
            "tools/file_tools.py",
            "tools/mcp_tool.py",
            "tools/patch_parser.py",
            "tools/terminal_tool.py",
            "environments/hermes_swe_env/hermes_swe_env.py",
            "acp_adapter/permissions.py",
        ),
    ),
)

LOCK_ORCHESTRATOR_ROOT = Path(r"G:\Github\hermes3d-mcp-lock-orchestrator")
LOCK_SERVER_ENTRY = LOCK_ORCHESTRATOR_ROOT / "src" / "server.mjs"
MCP_LOCK_WORKFLOW = (
    "hermes_claim_task",
    "hermes_lock_files",
    "hermes_heartbeat",
    "hermes_run_gate",
    "hermes_append_evidence",
    "hermes_release_files",
    "hermes_release_task",
)


def programming_readiness() -> dict[str, Any]:
    private_values = private_env()
    source_results = [_source_repo_status(source) for source in SOURCE_REPOS]
    provider_results = [_provider_status("minimax", private_values), _provider_status("deepseek", private_values)]
    lock_status = mcp_lock_readiness(private_values)
    missing_sources = [item["id"] for item in source_results if item["status"] == "missing"]
    source_warnings = [item["id"] for item in source_results if item["status"] == "source_tree"]
    missing_providers = [item["id"] for item in provider_results if item["status"] != "ready"]
    ready = not missing_sources and not missing_providers and lock_status["ready"]
    return {
        "status": "ready" if ready else "partial",
        "ready": ready,
        "source_inputs": source_results,
        "provider_lanes": provider_results,
        "mcp_locks": lock_status,
        "required_capabilities": [
            "repo_map",
            "bounded_file_read",
            "snapshot_before_write",
            "mcp_locks_claim_lock_heartbeat_gate_evidence_release",
            "patch_apply",
            "bounded_command_runner",
            "playwright_proof",
            "mcp_tool_boundary",
            "branch_commit_pr",
            "rollback_restore",
            "proof_ledger",
        ],
        "next_missing": {
            "source_inputs": missing_sources,
            "source_warnings": source_warnings,
            "providers": missing_providers,
            "mcp_locks": [] if lock_status["ready"] else [lock_status["blocked_reason"]],
            "code_history": _code_history_status(),
        },
    }


def mcp_lock_readiness(private_values: dict[str, str] | None = None) -> dict[str, Any]:
    values = private_values if private_values is not None else private_env()
    configured_workspace = (
        env_value("MCP_LOCK_WORKSPACE", values)
        or env_value("HERMES3D_WORKSPACE", values)
        or env_value("HERMES_LOCK_WORKSPACE", values)
    )
    configured_server = (
        env_value("MCP_LOCK_SERVER", values)
        or env_value("HERMES3D_MCP_SERVER", values)
        or str(LOCK_SERVER_ENTRY)
    )
    workspace_matches = False
    if configured_workspace:
        try:
            workspace_matches = Path(configured_workspace).resolve() == PROJECT_ROOT.resolve()
        except OSError:
            workspace_matches = False
    server_exists = Path(configured_server).exists() if configured_server else False
    source_exists = LOCK_ORCHESTRATOR_ROOT.exists()
    if not source_exists:
        blocked_reason = f"Hermes lock orchestrator source is missing at {LOCK_ORCHESTRATOR_ROOT}."
    elif not server_exists:
        blocked_reason = f"Hermes lock MCP server entry is missing at {configured_server}."
    elif not configured_workspace:
        blocked_reason = "MCP_LOCK_WORKSPACE is not configured for the Hermes Agent runtime."
    elif not workspace_matches:
        blocked_reason = "MCP lock workspace does not match the Hermes3D edit workspace."
    else:
        blocked_reason = None
    return {
        "status": "ready" if blocked_reason is None else "partial",
        "ready": blocked_reason is None,
        "server_name": "hermes3d-locks",
        "source_path": str(LOCK_ORCHESTRATOR_ROOT),
        "server_entry": configured_server,
        "server_entry_exists": server_exists,
        "configured_workspace": configured_workspace or None,
        "edit_workspace": str(PROJECT_ROOT),
        "workspace_matches": workspace_matches,
        "required_workflow": list(MCP_LOCK_WORKFLOW),
        "blocked_reason": blocked_reason,
    }


def repo_status() -> dict[str, Any]:
    branch = _git_value(["branch", "--show-current"])
    head = _git_value(["rev-parse", "--short", "HEAD"])
    status = _git_value(["status", "--short"], allow_multiline=True) or ""
    diff_summary = _git_value(["diff", "--stat"], allow_multiline=True) or ""
    return {
        "status": "ready",
        "workspace_root": str(PROJECT_ROOT),
        "branch": branch or "detached_or_unknown",
        "head": head,
        "dirty": bool(status.strip()),
        "status_short": status.splitlines()[:300],
        "diff_stat": diff_summary.splitlines()[:120],
    }


def code_write_readiness() -> dict[str, Any]:
    readiness = programming_readiness()
    repo = repo_status()
    blockers: list[str] = []
    warnings: list[str] = []
    if not readiness["mcp_locks"]["ready"]:
        blockers.append(str(readiness["mcp_locks"].get("blocked_reason") or "Hermes MCP locks are not ready."))
    missing_sources = readiness["next_missing"].get("source_inputs") or []
    if missing_sources:
        blockers.append(f"Missing required source inputs: {', '.join(missing_sources)}.")
    source_warnings = readiness["next_missing"].get("source_warnings") or []
    if source_warnings:
        warnings.append(f"Source trees without git metadata are usable but cannot report upstream ref: {', '.join(source_warnings)}.")
    missing_providers = readiness["next_missing"].get("providers") or []
    if missing_providers:
        blockers.append(f"Missing coding provider configuration: {', '.join(missing_providers)}.")
    if repo.get("dirty"):
        warnings.append("Current worktree is dirty; autonomous write lanes must snapshot/stage only owned files and avoid unrelated edits.")
    status = "ready" if not blockers else "blocked"
    return {
        "status": status,
        "ready": status == "ready",
        "safe_read_tools_ready": True,
        "write_tools_enabled": status == "ready",
        "blocked_reasons": blockers,
        "warnings": warnings,
        "required_before_apply": [
            "MCP_LOCK_WORKSPACE must match edit workspace",
            "hermes_claim_task must hold the task",
            "hermes_lock_files must hold every target file",
            "snapshot_file must record each target before patch",
            "patch must touch only allowed project-relative paths",
            "fixed gates must pass through hermes_run_gate or backend proof runner",
            "hermes_append_evidence must record result before release",
        ],
        "next_write_actions_when_ready": [
            "code.patch.propose",
            "code.patch.apply",
            "code.command.run_gate",
            "code.git.branch_commit_pr",
        ],
        "mcp_locks": readiness["mcp_locks"],
        "repo": {
            "branch": repo.get("branch"),
            "head": repo.get("head"),
            "dirty": repo.get("dirty"),
        },
    }


def propose_file_replacement(
    relative_path: str,
    proposed_text: str,
    *,
    agent_id: str,
    base_sha256: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    readiness = code_write_readiness()
    if not readiness["ready"]:
        raise ValueError("Code write readiness is blocked: " + "; ".join(readiness["blocked_reasons"]))
    target = _resolve_project_path(relative_path, write=False)
    proposed_bytes = proposed_text.encode("utf-8")
    if len(proposed_bytes) > MAX_PROPOSED_TEXT_BYTES:
        raise ValueError(f"Proposed file text is limited to {MAX_PROPOSED_TEXT_BYTES} bytes.")
    current_bytes = target.read_bytes()
    current_sha = hashlib.sha256(current_bytes).hexdigest()
    if base_sha256 and base_sha256.lower() != current_sha:
        raise ValueError("Base sha256 does not match the current file; refresh before proposing a patch.")
    proposed_sha = hashlib.sha256(proposed_bytes).hexdigest()
    rel = _relative_to_project(target)
    snapshot = snapshot_file(
        rel,
        agent_id=agent_id,
        action_id="code.patch.propose.pre",
        reason=reason or "Pre-proposal snapshot for Hermes Agent patch",
    )
    before = current_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
    after = proposed_text.splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=rel,
            tofile=f"{rel} (proposed)",
            n=3,
        )
    )
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise ValueError(f"Patch proposal diff is limited to {MAX_DIFF_BYTES} bytes.")
    proposal_id = new_id()
    proposal_dir = HISTORY_ROOT / "proposals" / _safe_bucket(rel)
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposal_dir / f"{proposal_id}.json"
    proposal_payload = {
        "id": proposal_id,
        "relative_path": rel,
        "agent_id": agent_id,
        "base_sha256": current_sha,
        "proposed_sha256": proposed_sha,
        "pre_snapshot_id": snapshot["id"],
        "reason": reason or "",
        "created_at": utc_now(),
        "diff": diff,
        "proposed_text": proposed_text,
    }
    tmp_path = proposal_path.with_suffix(proposal_path.suffix + f".tmp.{os.getpid()}.{new_id()[:8]}")
    tmp_path.write_text(as_json(proposal_payload), encoding="utf-8")
    os.replace(tmp_path, proposal_path)
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            proof_event_id,
            "code_patch.proposed",
            agent_id,
            as_json(
                {
                    "proposal_id": proposal_id,
                    "relative_path": rel,
                    "base_sha256": current_sha,
                    "proposed_sha256": proposed_sha,
                    "pre_snapshot_id": snapshot["id"],
                    "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
                    "diff_size_bytes": len(diff.encode("utf-8")),
                    "reason": reason or "",
                }
            ),
        ),
    )
    return {
        "status": "proposed",
        "id": proposal_id,
        "relative_path": rel,
        "base_sha256": current_sha,
        "proposed_sha256": proposed_sha,
        "pre_snapshot_id": snapshot["id"],
        "proposal_path": str(proposal_path),
        "proof_event_id": proof_event_id,
        "diff": diff,
    }


def apply_patch_proposal(
    proposal_id: str,
    *,
    agent_id: str,
    task_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    readiness = code_write_readiness()
    if not readiness["ready"]:
        raise ValueError("Code write readiness is blocked: " + "; ".join(readiness["blocked_reasons"]))
    _validate_owner(agent_id)
    _validate_task_id(task_id)
    proposal = _patch_proposal_payload(proposal_id)
    rel = str(proposal.get("relative_path") or "")
    proposed_text = proposal.get("proposed_text")
    if not isinstance(proposed_text, str):
        raise ValueError("Patch proposal is missing proposed_text; regenerate the proposal before applying.")
    target = _resolve_project_path(rel, write=True)
    rel = _relative_to_project(target)
    if rel != proposal.get("relative_path"):
        raise ValueError("Patch proposal path does not match the resolved target path.")
    current_bytes = target.read_bytes()
    current_sha = hashlib.sha256(current_bytes).hexdigest()
    base_sha = str(proposal.get("base_sha256") or "")
    if current_sha != base_sha:
        raise ValueError("Patch proposal base sha256 is stale; refresh and create a new proposal.")
    lock = _require_active_mcp_lock(rel, owner=agent_id, task_id=task_id)
    apply_reason = reason or str(proposal.get("reason") or "Hermes Agent patch apply")
    pre_snapshot = snapshot_file(
        rel,
        agent_id=agent_id,
        action_id="code.patch.apply.pre",
        reason=apply_reason,
    )
    proposed_bytes = proposed_text.encode("utf-8")
    tmp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}.{new_id()[:8]}")
    tmp_path.write_bytes(proposed_bytes)
    os.replace(tmp_path, target)
    post_bytes = target.read_bytes()
    post_sha = hashlib.sha256(post_bytes).hexdigest()
    proposed_sha = str(proposal.get("proposed_sha256") or "")
    if post_sha != proposed_sha:
        rollback_path = target.with_name(f"{target.name}.rollback.{os.getpid()}.{new_id()[:8]}")
        rollback_path.write_bytes(current_bytes)
        os.replace(rollback_path, target)
        raise RuntimeError("Applied patch sha256 did not match the proposal.")
    post_snapshot = snapshot_file(
        rel,
        agent_id=agent_id,
        action_id="code.patch.apply.post",
        reason=apply_reason,
    )
    proof_event_id = new_id()
    proof_payload = {
        "proposal_id": proposal_id,
        "relative_path": rel,
        "task_id": task_id,
        "owner": agent_id,
        "base_sha256": base_sha,
        "proposed_sha256": proposed_sha,
        "pre_apply_snapshot_id": pre_snapshot["id"],
        "post_apply_snapshot_id": post_snapshot["id"],
        "lock_id": lock.get("lock_id"),
        "reason": apply_reason,
    }
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (proof_event_id, "code_patch.applied", agent_id, as_json(proof_payload)),
    )
    evidence = append_mcp_evidence(
        owner=agent_id,
        task_id=task_id,
        kind="code_patch",
        summary=f"Applied Hermes Agent patch proposal {proposal_id[:12]} to {rel}",
        data={
            "proposal_id": proposal_id,
            "relative_path": rel,
            "base_sha256": base_sha,
            "proposed_sha256": proposed_sha,
            "pre_apply_snapshot_id": pre_snapshot["id"],
            "post_apply_snapshot_id": post_snapshot["id"],
            "proof_event_id": proof_event_id,
            "lock_id": lock.get("lock_id"),
        },
    )
    return {
        "status": "applied",
        "id": proposal_id,
        "relative_path": rel,
        "task_id": task_id,
        "owner": agent_id,
        "base_sha256": base_sha,
        "proposed_sha256": proposed_sha,
        "pre_apply_snapshot_id": pre_snapshot["id"],
        "post_apply_snapshot_id": post_snapshot["id"],
        "proof_event_id": proof_event_id,
        "mcp_evidence": evidence,
    }


def list_mcp_gates() -> dict[str, Any]:
    _require_mcp_locks_ready()
    payload = _call_mcp_tool("hermes_list_gates", {})
    gates = payload.get("gates") if isinstance(payload, dict) else None
    return {
        "status": "ready",
        "server_name": "hermes3d-locks",
        "workspace": str(PROJECT_ROOT),
        "count": len(gates or []),
        "gates": gates or [],
    }


def run_mcp_gate(gate_id: str, *, owner: str, cwd: str | None = None) -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", gate_id or ""):
        raise ValueError("Gate id must be 1-80 safe characters.")
    gate_cwd = _resolve_project_subpath(cwd or ".", must_exist=True)
    if gate_cwd.is_file():
        gate_cwd = gate_cwd.parent
    result = _call_mcp_tool(
        "hermes_run_gate",
        {"owner": owner, "gateId": gate_id, "cwd": str(gate_cwd)},
        timeout_s=260,
    )
    if not isinstance(result, dict):
        raise RuntimeError("Hermes MCP gate returned a non-object result.")
    return {
        "status": "pass" if result.get("ok") is True and result.get("status") == "pass" else str(result.get("status") or "failed"),
        "ok": result.get("ok") is True,
        "server_name": "hermes3d-locks",
        "workspace": str(PROJECT_ROOT),
        "gate_id": gate_id,
        "owner": owner,
        "result": result,
    }


def mcp_lock_state() -> dict[str, Any]:
    _require_mcp_locks_ready()
    result = _call_mcp_tool("hermes_get_state", {})
    if not isinstance(result, dict):
        raise RuntimeError("Hermes MCP state returned a non-object result.")
    return {
        "status": "ready" if result.get("ok") is True else str(result.get("status") or "partial"),
        "server_name": "hermes3d-locks",
        "workspace": str(PROJECT_ROOT),
        "state": result,
    }


def claim_mcp_task(*, owner: str, task_id: str, title: str = "", files: list[str] | None = None, reason: str = "", role: str = "agent") -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    _validate_task_id(task_id)
    result = _call_mcp_tool(
        "hermes_claim_task",
        {
            "owner": owner,
            "role": role or "agent",
            "taskId": task_id,
            "title": title or "",
            "files": _safe_mcp_files(files or [], must_exist=False),
            "reason": reason or "",
        },
    )
    return {"status": "claimed" if result.get("ok") is True else str(result.get("status") or "partial"), "workspace": str(PROJECT_ROOT), "result": result}


def lock_mcp_files(*, owner: str, files: list[str], task_id: str = "", reason: str = "", role: str = "agent", ttl_minutes: int = 90) -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    if task_id:
        _validate_task_id(task_id)
    safe_files = _safe_mcp_files(files, must_exist=False)
    result = _call_mcp_tool(
        "hermes_lock_files",
        {
            "owner": owner,
            "role": role or "agent",
            "taskId": task_id or "",
            "files": safe_files,
            "reason": reason or "",
            "ttlMinutes": max(5, min(int(ttl_minutes), 720)),
        },
    )
    return {"status": "locked" if result.get("ok") is True else str(result.get("status") or "blocked"), "workspace": str(PROJECT_ROOT), "files": safe_files, "result": result}


def heartbeat_mcp_task(*, owner: str, task_id: str = "") -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    if task_id:
        _validate_task_id(task_id)
    result = _call_mcp_tool("hermes_heartbeat", {"owner": owner, "taskId": task_id or ""})
    return {"status": str(result.get("status") or ("heartbeat" if result.get("ok") else "partial")), "workspace": str(PROJECT_ROOT), "result": result}


def release_mcp_files(*, owner: str, files: list[str], note: str = "") -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    safe_files = _safe_mcp_files(files, must_exist=False)
    result = _call_mcp_tool("hermes_release_files", {"owner": owner, "files": safe_files, "note": note or ""})
    return {"status": "released" if result.get("ok") is True else str(result.get("status") or "partial"), "workspace": str(PROJECT_ROOT), "files": safe_files, "result": result}


def release_mcp_task(*, owner: str, task_id: str, note: str = "") -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    _validate_task_id(task_id)
    result = _call_mcp_tool("hermes_release_task", {"owner": owner, "taskId": task_id, "note": note or ""})
    return {"status": "released" if result.get("ok") is True else str(result.get("status") or "partial"), "workspace": str(PROJECT_ROOT), "result": result}


def append_mcp_evidence(*, owner: str, summary: str, task_id: str = "", kind: str = "proof", data: dict[str, Any] | None = None) -> dict[str, Any]:
    _require_mcp_locks_ready()
    _validate_owner(owner)
    if task_id:
        _validate_task_id(task_id)
    if not summary or len(summary) > 400:
        raise ValueError("Evidence summary must be 1-400 characters.")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", kind or ""):
        raise ValueError("Evidence kind must be 1-80 safe characters.")
    result = _call_mcp_tool(
        "hermes_append_evidence",
        {"owner": owner, "taskId": task_id or "", "kind": kind, "summary": summary, "data": data or {}},
    )
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    return {
        "status": "recorded" if result.get("ok") is True else str(result.get("status") or "partial"),
        "workspace": str(PROJECT_ROOT),
        "evidence_id": evidence.get("id"),
        "result": result,
    }


def repo_tree(root: str = ".", limit: int = 400) -> dict[str, Any]:
    base = _resolve_project_subpath(root or ".", must_exist=True)
    if not base.is_dir():
        base = base.parent
    max_items = max(1, min(int(limit), 1200))
    items: list[dict[str, Any]] = []
    for current_root, dir_names, file_names in os.walk(base):
        current_path = Path(current_root)
        dir_names[:] = [name for name in sorted(dir_names, key=str.lower) if not _is_denied_path(current_path / name)]
        for name in [*dir_names, *sorted(file_names, key=str.lower)]:
            child = current_path / name
            if _is_denied_path(child):
                continue
            try:
                rel = _relative_to_project(child)
                stat = child.stat()
            except (OSError, ValueError):
                continue
            items.append(
                {
                    "path": rel,
                    "type": "dir" if child.is_dir() else "file",
                    "size_bytes": stat.st_size if child.is_file() else None,
                }
            )
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break
    return {"status": "ready", "root": _relative_to_project(base), "count": len(items), "limit": max_items, "items": items}


def search_text(pattern: str, root: str = ".", max_results: int = 100) -> dict[str, Any]:
    if not pattern or len(pattern) > 160:
        raise ValueError("Search pattern must be 1-160 characters.")
    base = _resolve_project_subpath(root or ".", must_exist=True)
    if not base.is_dir():
        base = base.parent
    max_items = max(1, min(int(max_results), MAX_SEARCH_RESULTS))
    command = [
        "rg",
        "--line-number",
        "--column",
        "--no-heading",
        "--color",
        "never",
        "--glob",
        "!node_modules/**",
        "--glob",
        "!.git/**",
        "--glob",
        "!dist/**",
        "--glob",
        "!build/**",
        "--glob",
        "!var/code-history/**",
        "--",
        pattern,
        "." if base == PROJECT_ROOT else _relative_to_project(base),
    ]
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=8, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("ripgrep is required for Hermes Agent repo search.") from exc
    lines = result.stdout.splitlines()[:max_items]
    matches = [_parse_rg_line(line) for line in lines]
    return {
        "status": "ready" if result.returncode in {0, 1} else "failed",
        "return_code": result.returncode,
        "pattern_sha256": hashlib.sha256(pattern.encode("utf-8")).hexdigest(),
        "root": _relative_to_project(base),
        "count": len(matches),
        "limit": max_items,
        "matches": matches,
        "stderr_head": result.stderr.splitlines()[:20],
    }


def read_file_slice(relative_path: str, start_line: int = 1, line_count: int = 120) -> dict[str, Any]:
    target = _resolve_project_path(relative_path, write=False)
    stat = target.stat()
    if stat.st_size > MAX_FILE_VIEW_BYTES:
        raise ValueError(f"File view is limited to files up to {MAX_FILE_VIEW_BYTES} bytes.")
    start = max(1, int(start_line))
    count = max(1, min(int(line_count), 240))
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    selected = [
        {"line": idx + 1, "text": text}
        for idx, text in enumerate(lines[start - 1 : start - 1 + count], start=start - 1)
    ]
    return {
        "status": "ready",
        "relative_path": _relative_to_project(target),
        "start_line": start,
        "line_count": len(selected),
        "total_lines": len(lines),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "lines": selected,
    }


def snapshot_file(relative_path: str, *, agent_id: str, action_id: str | None = None, reason: str | None = None) -> dict[str, Any]:
    target = _resolve_project_path(relative_path, write=False)
    stat = target.stat()
    if stat.st_size <= 0:
        raise ValueError("Refusing to snapshot an empty file.")
    if stat.st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError(f"Refusing to snapshot files larger than {MAX_SNAPSHOT_BYTES} bytes.")
    data = target.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    rel = _relative_to_project(target)
    snapshot_id = new_id()
    snapshot_dir = HISTORY_ROOT / _safe_bucket(rel)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / f"{snapshot_id}_{digest[:12]}.snap"
    tmp_path = snapshot_path.with_suffix(snapshot_path.suffix + f".tmp.{os.getpid()}.{new_id()[:8]}")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, snapshot_path)
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            proof_event_id,
            "code_history.snapshot",
            agent_id,
            as_json(
                {
                    "snapshot_id": snapshot_id,
                    "relative_path": rel,
                    "sha256": digest,
                    "size_bytes": stat.st_size,
                    "action_id": action_id,
                    "reason": reason or "",
                }
            ),
        ),
    )
    execute(
        """
        INSERT INTO code_history_snapshots
            (id, workspace_root, relative_path, snapshot_path, sha256, size_bytes,
             action_id, agent_id, proof_event_id, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            str(PROJECT_ROOT),
            rel,
            str(snapshot_path),
            digest,
            stat.st_size,
            action_id,
            agent_id,
            proof_event_id,
            reason or "",
        ),
    )
    return _snapshot_payload(snapshot_id)


def list_touched_files(limit: int = 200) -> dict[str, Any]:
    records = rows(
        """
        SELECT relative_path, COUNT(*) AS snapshot_count, MAX(created_at) AS latest_snapshot_at
        FROM code_history_snapshots
        GROUP BY workspace_root, relative_path
        ORDER BY latest_snapshot_at DESC
        LIMIT ?
        """,
        (max(1, min(limit, 1000)),),
    )
    return {"status": "ready", "count": len(records), "files": records}


def list_snapshots(relative_path: str, limit: int = 100) -> dict[str, Any]:
    rel = _relative_to_project(_resolve_project_path(relative_path, write=False))
    records = rows(
        """
        SELECT id, workspace_root, relative_path, sha256, size_bytes, action_id,
               agent_id, proof_event_id, reason, created_at
        FROM code_history_snapshots
        WHERE workspace_root = ? AND relative_path = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (str(PROJECT_ROOT), rel, max(1, min(limit, 500))),
    )
    return {"status": "ready", "relative_path": rel, "count": len(records), "snapshots": records}


def snapshot_diff(relative_path: str, snapshot_id: str) -> dict[str, Any]:
    target = _resolve_project_path(relative_path, write=False)
    rel = _relative_to_project(target)
    snapshot = _snapshot_row(snapshot_id, rel)
    snapshot_path = Path(snapshot["snapshot_path"])
    if not snapshot_path.exists():
        raise FileNotFoundError("Snapshot file is missing from code history storage.")
    if target.stat().st_size > MAX_DIFF_BYTES or snapshot_path.stat().st_size > MAX_DIFF_BYTES:
        raise ValueError(f"Diff is limited to files up to {MAX_DIFF_BYTES} bytes.")
    before = snapshot_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    after = target.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=f"{rel}@{snapshot_id}",
            tofile=rel,
            n=3,
        )
    )
    return {
        "status": "ready",
        "relative_path": rel,
        "snapshot_id": snapshot_id,
        "diff": diff,
        "diff_sha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
    }


def restore_snapshot(relative_path: str, snapshot_id: str, *, agent_id: str, reason: str | None = None) -> dict[str, Any]:
    target = _resolve_project_path(relative_path, write=True)
    rel = _relative_to_project(target)
    snapshot = _snapshot_row(snapshot_id, rel)
    snapshot_path = Path(snapshot["snapshot_path"])
    if not snapshot_path.exists():
        raise FileNotFoundError("Snapshot file is missing from code history storage.")
    pre_restore = snapshot_file(rel, agent_id=agent_id, action_id="code.history.restore.pre", reason="Pre-restore safety snapshot")
    data = snapshot_path.read_bytes()
    tmp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}.{new_id()[:8]}")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, target)
    digest = hashlib.sha256(data).hexdigest()
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            proof_event_id,
            "code_history.restore",
            agent_id,
            as_json(
                {
                    "relative_path": rel,
                    "restored_snapshot_id": snapshot_id,
                    "pre_restore_snapshot_id": pre_restore["id"],
                    "sha256": digest,
                    "reason": reason or "",
                }
            ),
        ),
    )
    return {
        "status": "restored",
        "relative_path": rel,
        "restored_snapshot_id": snapshot_id,
        "pre_restore_snapshot_id": pre_restore["id"],
        "proof_event_id": proof_event_id,
        "sha256": digest,
    }


def _source_repo_status(source: SourceRepo) -> dict[str, Any]:
    exists = source.local_path.exists() and source.local_path.is_dir()
    git_dir = source.local_path / ".git"
    missing_required = [
        item for item in source.required_files if not (source.local_path / item.replace("/", os.sep)).exists()
    ] if exists else list(source.required_files)
    head = _git_head(source.local_path) if git_dir.exists() else None
    status = "ready" if exists and not missing_required else "missing"
    if exists and not git_dir.exists():
        status = "source_tree"
    return {
        "id": source.id,
        "label": source.label,
        "role": source.role,
        "remote_url": source.remote_url,
        "local_path": str(source.local_path),
        "status": status,
        "exists": exists,
        "git_metadata": git_dir.exists(),
        "head": head,
        "missing_required_files": missing_required,
    }


def _provider_status(provider_id: str, private_values: dict[str, str]) -> dict[str, Any]:
    prefix = "MINIMAX" if provider_id == "minimax" else "DEEPSEEK"
    api_key = env_value(f"{prefix}_API_KEY", private_values)
    base_url = env_value(f"{prefix}_BASE_URL", private_values)
    model = env_value(f"{prefix}_MODEL", private_values)
    return {
        "id": provider_id,
        "status": "ready" if api_key and model else "missing_config",
        "api_key_configured": bool(api_key),
        "base_url_configured": bool(base_url),
        "model_configured": bool(model),
        "base_url_label": _host_label(base_url),
        "model": model or None,
    }


def _code_history_status() -> dict[str, Any]:
    count = 0
    if DB_PATH.exists():
        try:
            result = row("SELECT COUNT(*) AS count FROM code_history_snapshots")
            count = int((result or {}).get("count") or 0)
        except Exception:
            count = 0
    return {"snapshot_count": count, "history_root": str(HISTORY_ROOT)}


def _git_head(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _require_mcp_locks_ready() -> None:
    lock_status = mcp_lock_readiness()
    if not lock_status["ready"]:
        raise ValueError(str(lock_status.get("blocked_reason") or "Hermes MCP locks are not ready."))


def _validate_owner(owner: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", owner or ""):
        raise ValueError("Owner must match Hermes MCP owner policy.")


def _validate_task_id(task_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,128}", task_id or "") or ".." in task_id:
        raise ValueError("Task id must be 2-128 safe characters.")


def _safe_mcp_files(files: list[str], *, must_exist: bool) -> list[str]:
    if not files:
        return []
    safe: list[str] = []
    for item in files:
        path = _resolve_project_subpath(item, must_exist=must_exist)
        safe.append(_relative_to_project(path))
    return safe


def _call_mcp_tool(tool_name: str, arguments: dict[str, Any], *, timeout_s: int = 30) -> dict[str, Any]:
    private_values = private_env()
    server = env_value("MCP_LOCK_SERVER", private_values) or env_value("HERMES3D_MCP_SERVER", private_values) or str(LOCK_SERVER_ENTRY)
    workspace = env_value("MCP_LOCK_WORKSPACE", private_values) or env_value("HERMES3D_WORKSPACE", private_values) or str(PROJECT_ROOT)
    if Path(workspace).resolve() != PROJECT_ROOT.resolve():
        raise ValueError("MCP lock workspace does not match the Hermes3D edit workspace.")
    if not Path(server).exists():
        raise FileNotFoundError("Hermes MCP lock server entry is missing.")
    init_id = 1
    call_id = 2
    messages = [
        {"jsonrpc": "2.0", "id": init_id, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "hermes3d-code-operator", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": call_id, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}},
    ]
    stdin = "".join(json.dumps(message, separators=(",", ":")) + "\n" for message in messages)
    env = {
        **os.environ,
        "MCP_LOCK_WORKSPACE": str(PROJECT_ROOT),
        "MCP_LOCK_SERVER": server,
    }
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def collect(stream: Any, target: list[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                target.append(line)
        finally:
            try:
                stream.close()
            except OSError:
                pass

    try:
        process = subprocess.Popen(
            ["node", server],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
    except OSError as exc:
        raise RuntimeError(f"Hermes MCP tool {tool_name} could not start.") from exc
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    stdout_thread = threading.Thread(target=collect, args=(process.stdout, stdout_lines), daemon=True)
    stderr_thread = threading.Thread(target=collect, args=(process.stderr, stderr_lines), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        process.stdin.write(stdin)
        process.stdin.flush()
        deadline = time.monotonic() + timeout_s
        response: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            response = _jsonrpc_response("".join(stdout_lines), call_id)
            if response is not None:
                break
            if process.poll() is not None:
                break
            time.sleep(0.05)
        if response is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            stderr_head = "".join(stderr_lines).splitlines()[:5]
            raise RuntimeError(f"Hermes MCP tool {tool_name} returned no JSON-RPC response: {stderr_head}")
    finally:
        try:
            process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
    if response.get("error"):
        raise RuntimeError(f"Hermes MCP tool {tool_name} failed: {response['error']}")
    content = ((response.get("result") or {}).get("content") or [])
    text = content[0].get("text") if content and isinstance(content[0], dict) else "{}"
    try:
        return json.loads(text or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "status": "failed", "raw_text": text}


def _jsonrpc_response(stdout: str, request_id: int) -> dict[str, Any] | None:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if message.get("id") == request_id:
            return message
    return None


def _git_value(args: list[str], *, allow_multiline: bool = False) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode not in {0, 1}:
        return None
    value = result.stdout if allow_multiline else result.stdout.strip()
    return value[:12000]


def _host_label(url: str) -> str | None:
    if not url:
        return None
    match = re.match(r"^https?://([^/]+)", url.strip(), re.IGNORECASE)
    return match.group(1).lower() if match else "custom"


def _resolve_project_path(relative_path: str, *, write: bool) -> Path:
    if not relative_path or "\x00" in relative_path:
        raise ValueError("A non-empty project-relative path is required.")
    raw = relative_path.replace("\\", "/").lstrip("/")
    if re.match(r"^[A-Za-z]:", raw) or raw.startswith("../") or "/../" in f"/{raw}/":
        raise ValueError("Only Hermes3D project-relative paths are allowed.")
    target = (PROJECT_ROOT / raw).resolve()
    try:
        target.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("Path is outside the Hermes3D project root.") from exc
    _enforce_path_policy(target, write=write)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Target file does not exist.")
    return target


def _resolve_project_subpath(relative_path: str, *, must_exist: bool) -> Path:
    if not relative_path or "\x00" in relative_path:
        raise ValueError("A non-empty project-relative path is required.")
    raw = relative_path.replace("\\", "/").lstrip("/")
    if raw in {"", "."}:
        target = PROJECT_ROOT.resolve()
    else:
        if re.match(r"^[A-Za-z]:", raw) or raw.startswith("../") or "/../" in f"/{raw}/":
            raise ValueError("Only Hermes3D project-relative paths are allowed.")
        target = (PROJECT_ROOT / raw).resolve()
    try:
        target.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("Path is outside the Hermes3D project root.") from exc
    if _is_denied_path(target):
        raise ValueError("Path is blocked by Hermes Agent code policy.")
    if must_exist and not target.exists():
        raise FileNotFoundError("Target path does not exist.")
    return target


def _enforce_path_policy(path: Path, *, write: bool) -> None:
    relative_parts = path.relative_to(PROJECT_ROOT).parts
    lowered_parts = {part.lower() for part in relative_parts}
    if lowered_parts & DENIED_PARTS:
        raise ValueError("Path is blocked by Hermes Agent code policy.")
    name = path.name.lower()
    if name == ".env" or any(name.endswith(suffix) for suffix in DENIED_SUFFIXES):
        raise ValueError("Sensitive, binary, or generated file type is blocked by Hermes Agent code policy.")
    if write and "config" in lowered_parts and "printers.toml" in name:
        raise ValueError("Printer configuration writes require a dedicated printer-policy approval lane.")


def _is_denied_path(path: Path) -> bool:
    try:
        relative_parts = path.resolve().relative_to(PROJECT_ROOT).parts
    except ValueError:
        return True
    lowered_parts = {part.lower() for part in relative_parts}
    if lowered_parts & DENIED_PARTS:
        return True
    name = path.name.lower()
    return name == ".env" or any(name.endswith(suffix) for suffix in DENIED_SUFFIXES)


def _parse_rg_line(line: str) -> dict[str, Any]:
    # rg --line-number --column --no-heading yields path:line:column:text.
    parts = line.split(":", 3)
    if len(parts) != 4:
        return {"path": "", "line": None, "column": None, "text": line[:500]}
    path_text, line_text, column_text, text = parts
    try:
        parsed_path = Path(path_text)
        rel = _relative_to_project(parsed_path if parsed_path.is_absolute() else PROJECT_ROOT / parsed_path)
    except Exception:
        rel = path_text
    return {
        "path": rel,
        "line": int(line_text) if line_text.isdigit() else None,
        "column": int(column_text) if column_text.isdigit() else None,
        "text": text[:500],
    }


def _relative_to_project(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _safe_bucket(relative_path: str) -> str:
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()
    return f"{digest[:2]}/{digest[2:4]}/{digest}"


def _patch_proposal_payload(proposal_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{32}", proposal_id or ""):
        raise ValueError("Patch proposal id must be a 32-character hex id.")
    proposal_root = HISTORY_ROOT / "proposals"
    if not proposal_root.exists():
        raise FileNotFoundError("Patch proposal storage is empty.")
    matches = list(proposal_root.glob(f"*/*/*/{proposal_id}.json"))
    if len(matches) != 1:
        raise FileNotFoundError("Patch proposal was not found.")
    payload = json.loads(matches[0].read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("id") != proposal_id:
        raise ValueError("Patch proposal payload is malformed.")
    return payload


def _require_active_mcp_lock(relative_path: str, *, owner: str, task_id: str) -> dict[str, Any]:
    state = mcp_lock_state().get("state") or {}
    locks = state.get("locks") if isinstance(state, dict) else []
    if not isinstance(locks, list):
        raise RuntimeError("Hermes MCP lock state did not return a lock list.")
    for lock in locks:
        if not isinstance(lock, dict):
            continue
        if (
            lock.get("file") == relative_path
            and lock.get("owner") == owner
            and lock.get("task_id") == task_id
            and lock.get("is_stale") is not True
        ):
            return lock
    raise ValueError("Active Hermes MCP file lock is required before applying a patch.")


def _snapshot_row(snapshot_id: str, relative_path: str) -> dict[str, Any]:
    snapshot = row(
        """
        SELECT *
        FROM code_history_snapshots
        WHERE id = ? AND workspace_root = ? AND relative_path = ?
        """,
        (snapshot_id, str(PROJECT_ROOT), relative_path),
    )
    if not snapshot:
        raise FileNotFoundError("Snapshot record was not found for this file.")
    return snapshot


def _snapshot_payload(snapshot_id: str) -> dict[str, Any]:
    snapshot = row(
        """
        SELECT id, workspace_root, relative_path, sha256, size_bytes, action_id,
               agent_id, proof_event_id, reason, created_at
        FROM code_history_snapshots
        WHERE id = ?
        """,
        (snapshot_id,),
    )
    if not snapshot:
        raise FileNotFoundError("Snapshot record was not found.")
    return {"status": "ready", **snapshot}
