"""Source-backed code history and Hermes Agent programming readiness."""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import subprocess
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
        label="Atomic Hermes agent desktop patterns",
        local_path=Path(r"G:\Github\atomic-hermes"),
        remote_url="https://github.com/AtomicBot-ai/atomic-hermes.git",
        role="file history, approvals, bridge, local runtime, UI history patterns",
        required_files=("README.md", "tools/approval.py", "desktop/src/main/files/snapshot-operations.ts", "desktop/src/main/files/snapshot-watcher.ts"),
    ),
)


def programming_readiness() -> dict[str, Any]:
    private_values = private_env()
    source_results = [_source_repo_status(source) for source in SOURCE_REPOS]
    provider_results = [_provider_status("minimax", private_values), _provider_status("deepseek", private_values)]
    missing_sources = [item["id"] for item in source_results if item["status"] != "ready"]
    missing_providers = [item["id"] for item in provider_results if item["status"] != "ready"]
    ready = not missing_sources and not missing_providers
    return {
        "status": "ready" if ready else "partial",
        "ready": ready,
        "source_inputs": source_results,
        "provider_lanes": provider_results,
        "required_capabilities": [
            "repo_map",
            "bounded_file_read",
            "snapshot_before_write",
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
            "providers": missing_providers,
            "code_history": _code_history_status(),
        },
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


def repo_tree(root: str = ".", limit: int = 400) -> dict[str, Any]:
    base = _resolve_project_subpath(root or ".", must_exist=True)
    if not base.is_dir():
        base = base.parent
    max_items = max(1, min(int(limit), 1200))
    items: list[dict[str, Any]] = []
    for child in sorted(base.rglob("*"), key=lambda p: p.as_posix().lower()):
        if _is_denied_path(child):
            if child.is_dir():
                continue
            continue
        try:
            rel = _relative_to_project(child)
        except ValueError:
            continue
        try:
            stat = child.stat()
        except OSError:
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
        str(base),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
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
        rel = _relative_to_project(Path(path_text))
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
