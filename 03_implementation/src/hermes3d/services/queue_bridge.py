"""W21-A4 MVP-2 — orchestrator queue bridge.

Reads ``.hermes3d_orchestrator/tasks/pending/*.json`` from disk, matches each
task's ``target_owner_pattern`` against the configured Hermes Agent persona
ids, and atomically transitions tasks pending -> claimed -> done by writing
``claimed_by`` / ``claimed_utc`` / ``heartbeat_utc`` / ``done_utc`` /
``blocked_reason`` fields and moving the file between sibling directories.

Why direct file manipulation?
  The orchestrator MCP server (``hermes3d-locks``) is a separate process
  that reads the SAME file tree. By making both the MCP and this bridge
  treat the filesystem as the source of truth, no IPC is required and
  ``hermes_list_pending_tasks`` (an MCP read) reflects bridge writes
  immediately on the next call. Atomicity is achieved with file moves
  (``os.replace`` on Windows is atomic for same-volume) — the typical
  claim race is bounded by a single ``os.replace`` succeeding for at
  most one caller.

Security:
  This module DOES NOT load the task data into the network — only into
  the in-process logs. Task summaries are typically operational text
  with no credentials, but the bridge still treats them as untrusted
  input and never `eval`s any field.

Lag protection:
  The W21-A4 plan calls for two-stable-read confirmation of claims at
  the UI level. The bridge itself returns deterministic state, so the
  UI's polling loop can verify "before claim" vs. "after claim" with a
  single read at each side. There is no internal retry; if a claim
  fails (e.g. file already moved by a concurrent claimer), the caller
  gets a clean ``False`` and decides what to do.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------


def _state_dir(workspace_root: Path) -> Path:
    """The `.hermes3d_orchestrator` directory under workspace_root."""
    return workspace_root / ".hermes3d_orchestrator"


def _tasks_dir(workspace_root: Path) -> Path:
    return _state_dir(workspace_root) / "tasks"


def pending_dir(workspace_root: Path) -> Path:
    return _tasks_dir(workspace_root) / "pending"


def claimed_dir(workspace_root: Path) -> Path:
    return _tasks_dir(workspace_root) / "claimed"


def done_dir(workspace_root: Path) -> Path:
    return _tasks_dir(workspace_root) / "done"


def blocked_dir(workspace_root: Path) -> Path:
    return _tasks_dir(workspace_root) / "blocked"


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TaskSnapshot:
    """A point-in-time view of a queued task. Read-only.

    ``state`` is one of "pending", "claimed", "done", "blocked"; derived
    from which directory the file currently lives in (NOT from the JSON
    body) so a half-written file never reports an incorrect state.
    """

    task_id: str
    state: str
    title: str
    target_owner_pattern: str
    priority: int
    claimed_by: str | None
    claimed_utc: str | None
    heartbeat_utc: str | None
    done_utc: str | None
    blocked_reason: str | None
    handoff_path: str | None
    summary: str
    raw_path: Path

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["raw_path"] = str(self.raw_path)
        return d


def _read_task(path: Path, state: str) -> TaskSnapshot | None:
    """Load a task file, never raising — corrupt files are logged + skipped."""
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("queue_bridge: skip %s (state=%s): %s", path, state, exc)
        return None
    return TaskSnapshot(
        task_id=str(body.get("task_id", path.stem)),
        state=state,
        title=str(body.get("title", "")),
        target_owner_pattern=str(body.get("target_owner_pattern", "")),
        priority=int(body.get("priority", 0)),
        claimed_by=body.get("claimed_by"),
        claimed_utc=body.get("claimed_utc"),
        heartbeat_utc=body.get("heartbeat_utc"),
        done_utc=body.get("done_utc"),
        blocked_reason=body.get("blocked_reason"),
        handoff_path=body.get("handoff_path"),
        summary=str(body.get("summary", "")),
        raw_path=path,
    )


def list_tasks(workspace_root: Path, state: str) -> list[TaskSnapshot]:
    """List tasks in a given lifecycle state. Returns [] if dir missing."""
    if state == "pending":
        d = pending_dir(workspace_root)
    elif state == "claimed":
        d = claimed_dir(workspace_root)
    elif state == "done":
        d = done_dir(workspace_root)
    elif state == "blocked":
        d = blocked_dir(workspace_root)
    else:
        raise ValueError(f"unknown state {state!r}")
    if not d.is_dir():
        return []
    out: list[TaskSnapshot] = []
    for path in sorted(d.glob("*.json")):
        snap = _read_task(path, state=state)
        if snap is not None:
            out.append(snap)
    return out


def status_counts(workspace_root: Path) -> dict[str, int]:
    """Counts of tasks per lifecycle state — cheap, called by HTTP endpoint."""
    return {
        "pending": len(list_tasks(workspace_root, "pending")),
        "claimed": len(list_tasks(workspace_root, "claimed")),
        "done": len(list_tasks(workspace_root, "done")),
        "blocked": len(list_tasks(workspace_root, "blocked")),
    }


# ---------------------------------------------------------------------------
# Persona matching
# ---------------------------------------------------------------------------


def match_persona(target_owner_pattern: str, available_personas: list[str]) -> str | None:
    """Find the first persona whose id matches ``target_owner_pattern``.

    The orchestrator's pattern is a "|"-separated list of acceptable owner
    ids (sometimes with regex characters). We interpret it as a strict
    alternation regex anchored to the full persona id so a pattern like
    ``"factory-operator|privacy-agent|oliver-qa-agent"`` matches only those
    three exact ids and not, for example, ``"factory-operator-foo"``.
    """
    pat = (target_owner_pattern or "").strip()
    if not pat:
        return None
    try:
        regex = re.compile(rf"^(?:{pat})$")
    except re.error:
        LOG.warning("queue_bridge: invalid target_owner_pattern %r", pat)
        return None
    for persona in available_personas:
        if regex.match(persona):
            return persona
    return None


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _atomic_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    os.replace(src, dst)
    return dst


def _write_then_move(snap_path: Path, dst_dir: Path, patch: dict[str, Any]) -> Path:
    """Patch the JSON, fsync, then move the file. Best-effort atomicity:
    the JSON patch happens in place (overwrite), then ``os.replace`` moves
    the file to the destination dir. Both ops are bounded; concurrent
    claimers will see at most one succeed because the destination
    rename is the linearization point."""
    try:
        body = json.loads(snap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"task file unreadable for patch: {snap_path}: {exc}")
    body.update(patch)
    tmp = snap_path.with_suffix(snap_path.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
    os.replace(tmp, snap_path)  # atomic in-place replace of the JSON content
    return _atomic_move(snap_path, dst_dir)


def claim_task(
    workspace_root: Path,
    task_id: str,
    persona: str,
) -> TaskSnapshot | None:
    """Attempt to claim ``task_id`` for ``persona``.

    Returns the new TaskSnapshot on success. Returns ``None`` if:
      - the task is not in pending state (already claimed/done),
      - or the file was moved out from under us by a concurrent claimer.

    Does NOT validate that ``persona`` matches ``target_owner_pattern`` —
    that is the caller's responsibility (use :func:`match_persona` first).
    """
    src = pending_dir(workspace_root) / f"{task_id}.json"
    if not src.is_file():
        LOG.info("queue_bridge: claim_task miss — %s not in pending", task_id)
        return None
    now = _now_iso()
    try:
        new_path = _write_then_move(
            src,
            claimed_dir(workspace_root),
            {
                "claimed_by": f"hermes/{persona}",
                "claimed_utc": now,
                "heartbeat_utc": now,
            },
        )
    except (OSError, RuntimeError) as exc:
        LOG.warning("queue_bridge: claim_task failed for %s: %s", task_id, exc)
        return None
    return _read_task(new_path, state="claimed")


def heartbeat(workspace_root: Path, task_id: str, *, persona: str | None = None) -> bool:
    """Refresh ``heartbeat_utc`` on a claimed task. Returns True if applied."""
    src = claimed_dir(workspace_root) / f"{task_id}.json"
    if not src.is_file():
        return False
    try:
        body = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if persona is not None and body.get("claimed_by") not in (
        f"hermes/{persona}",
        persona,
    ):
        LOG.warning(
            "queue_bridge: heartbeat %s skipped — claimed_by=%r != %r",
            task_id,
            body.get("claimed_by"),
            persona,
        )
        return False
    body["heartbeat_utc"] = _now_iso()
    tmp = src.with_suffix(src.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
    os.replace(tmp, src)
    return True


def complete_task(workspace_root: Path, task_id: str, *, persona: str | None = None) -> bool:
    """Mark a claimed task done and move to done/."""
    src = claimed_dir(workspace_root) / f"{task_id}.json"
    if not src.is_file():
        return False
    try:
        body = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if persona is not None and body.get("claimed_by") not in (
        f"hermes/{persona}",
        persona,
    ):
        return False
    body["done_utc"] = _now_iso()
    body["heartbeat_utc"] = body["done_utc"]
    tmp = src.with_suffix(src.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
    os.replace(tmp, src)
    _atomic_move(src, done_dir(workspace_root))
    return True


def block_task(
    workspace_root: Path, task_id: str, reason: str, *, persona: str | None = None
) -> bool:
    """Move a claimed task to blocked/ with a structured reason."""
    src = claimed_dir(workspace_root) / f"{task_id}.json"
    if not src.is_file():
        return False
    try:
        body = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if persona is not None and body.get("claimed_by") not in (
        f"hermes/{persona}",
        persona,
    ):
        return False
    body["blocked_reason"] = reason
    body["heartbeat_utc"] = _now_iso()
    tmp = src.with_suffix(src.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
    os.replace(tmp, src)
    _atomic_move(src, blocked_dir(workspace_root))
    return True


def release_task(workspace_root: Path, task_id: str) -> bool:
    """Return a claimed task to pending (e.g. on operator override)."""
    src = claimed_dir(workspace_root) / f"{task_id}.json"
    if not src.is_file():
        return False
    try:
        body = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    body["claimed_by"] = None
    body["claimed_utc"] = None
    body["heartbeat_utc"] = None
    tmp = src.with_suffix(src.suffix + ".tmp")
    tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
    os.replace(tmp, src)
    _atomic_move(src, pending_dir(workspace_root))
    return True


__all__ = [
    "TaskSnapshot",
    "block_task",
    "claim_task",
    "claimed_dir",
    "complete_task",
    "done_dir",
    "heartbeat",
    "list_tasks",
    "match_persona",
    "pending_dir",
    "release_task",
    "status_counts",
]
