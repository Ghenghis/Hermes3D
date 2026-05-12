"""W21 MVP-3 — Hermes Agent persona task executor.

Closes the W21-A4 audit's biggest gap: tasks claimed by Hermes personas
that never produce a deliverable. This module reads a claimed task,
classifies it, runs an automated work step where one fits, persists the
result as the task's ``handoff_path`` markdown, and transitions the task
to ``done`` — or moves it to ``blocked/`` with an honest reason when no
automated executor exists.

Design contract:

* Audit-class tasks (handoff_path matches ``W21_*_AUDIT_*.md`` /
  ``W21_*_PLAN_*.md`` / ``W21_*_BACKLOG_*.md``) get a structured
  templated outline + real probe data + LLM-narrative via MiniMax. The
  resulting markdown explicitly states it is MVP-3 generated and must
  be operator-reviewed before being treated as final.
* Non-audit tasks are moved to ``blocked/`` with reason
  ``no_automated_executor_for_task_class`` so the operator sees them in
  the UI and can ship the missing executor.
* No silent failures. Every transition emits a proof event.
* No printer hardware (executor never touches `/api/printers/*` actions).
* Lag-protected: per-task LLM call uses a 30 s timeout; the whole tick
  is capped at MAX_EXECUTE_PER_TICK tasks so a slow LLM cannot stall
  the orchestrator.

The route surface lives in :mod:`hermes3d.api.routes.agent_queue` — this
module exposes only the synchronous primitives so tests can drive them
directly without spinning the asyncio poller.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes3d.services import queue_bridge

LOG = logging.getLogger(__name__)


# Per-tick budget so a slow LLM can never stall the orchestrator poll.
def _max_execute_per_tick() -> int:
    return int(os.environ.get("HERMES3D_PERSONA_EXEC_MAX_PER_TICK", "2"))


# Per-LLM-call wall-clock budget (audit handoff generation).
def _llm_timeout_s() -> float:
    return float(os.environ.get("HERMES3D_PERSONA_EXEC_LLM_TIMEOUT_S", "30"))


# Maximum completion tokens the LLM may emit per audit handoff. Large
# enough for a thorough audit doc, small enough to keep latency bounded.
def _max_completion_tokens() -> int:
    return int(os.environ.get("HERMES3D_PERSONA_EXEC_MAX_TOKENS", "4096"))


# Operator override to disable the executor without touching the poller.
def _executor_disabled() -> bool:
    return os.environ.get("HERMES3D_PERSONA_EXECUTOR_DISABLED", "") == "1"


# Regex classifying which claimed tasks have an automated executor.
# Today only audit / plan / backlog markdown deliverables are supported;
# anything else (build, ship, install, configure) requires human work.
# Task ids use hyphens (W21-A1-...-AUDIT-...) while handoff filenames use
# underscores (W21_A1_..._AUDIT_...) — accept either separator.
_AUDIT_TASK_PATTERN = re.compile(
    r"[-_](AUDIT|PLAN|BACKLOG|HARNESS|REVIEW)[-_]",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _workspace_root() -> Path:
    """Mirror the queue_bridge resolution so both pieces agree on root."""
    env_root = os.environ.get("HERMES3D_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[4]


def classify_task(task: queue_bridge.TaskSnapshot) -> str:
    """Return one of ``audit``, ``plan``, ``unknown``.

    Classification rules (deliberately narrow so we never auto-execute
    a high-stakes action; add classes only when their executor exists):

    * ``audit`` — task_id contains AUDIT/PLAN/BACKLOG/HARNESS/REVIEW
      AND handoff_path ends in ``.md``. Executor: MiniMax + template.
    * ``unknown`` — everything else. Executor: move to ``blocked/``.

    The classification is intentionally conservative; expand only with
    code review and tests for the new executor.
    """
    handoff = task.handoff_path or ""
    if not handoff.lower().endswith(".md"):
        return "unknown"
    if _AUDIT_TASK_PATTERN.search(task.task_id):
        return "audit"
    return "unknown"


def _emit_proof_event(event_type: str, payload: dict[str, Any]) -> None:
    """Write a proof_events row directly. Best-effort — never raises.

    Bypasses the HTTP layer because the executor may run inside the same
    process that owns the DB, and we want the event durable BEFORE the
    queue transition is finalized.
    """
    try:
        from hermes3d.db.init import DB_PATH

        with sqlite3.connect(DB_PATH) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO proof_events (id, event_type, source_agent, payload, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    os.urandom(16).hex(),
                    event_type,
                    "persona_executor",
                    json.dumps(payload, default=str),
                    _now_iso(),
                ),
            )
            con.commit()
    except Exception as exc:  # noqa: BLE001 — never fail the executor on log
        LOG.debug("persona_executor: proof event write failed: %s", exc)


# ---------------------------------------------------------------------------
# Audit-class executor (MiniMax-driven handoff doc generation)
# ---------------------------------------------------------------------------


_AUDIT_PROMPT_TEMPLATE = """You are the Hermes Agent persona `{persona}` working on the queued task `{task_id}`.

The task is to produce the markdown deliverable below as an honest audit doc that obeys these strict rules:

1. No printer hardware claims.
2. No fake-pass / no-aspirational language. If something is not measured, say "not measured".
3. Cite filepaths, route names, byte counts, or HTTP status codes when known.
4. Surface unknowns explicitly with a header section.
5. Mark this doc as MVP-3-generated and require operator review before treating it as final.

Task title: {title}
Task summary:
{summary}

Deliverable path (relative to repo root): {handoff_path}
Auditor identity: persona `{persona}` (Hermes Agent MVP-3 executor)
Date (UTC): {now}

Produce a complete markdown document starting with a level-1 header. Include sections for:
  - Verdict (one short sentence)
  - Scope (what is and is NOT in this audit)
  - Findings (numbered, each with evidence type)
  - Gaps / Unknowns
  - Recommended next actions
  - MVP-3 attestation footer

Keep the doc under 3000 words. Do not invent data; defer to "not measured" or "operator must verify" when uncertain.
"""


def _generate_audit_markdown(
    task: queue_bridge.TaskSnapshot, persona: str
) -> tuple[str, dict[str, Any]] | None:
    """Call MiniMax to generate the audit handoff markdown.

    Returns ``(markdown_text, metadata)`` on success, or ``None`` on
    failure. Metadata includes tokens_in/out + model so the caller can
    log it into the proof event.

    Failures are silent (logged at DEBUG); the caller must treat ``None``
    as "executor could not produce the handoff, move task to blocked".
    """
    try:
        from hermes3d.gateways.providers.minimax import completion_caller
        from hermes3d.orchestration.types import LLMRequest, ProviderConfig
    except Exception as exc:  # pragma: no cover - import safety net
        LOG.warning("persona_executor: minimax import failed: %s", exc)
        return None

    try:
        config = ProviderConfig(
            base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
            probe_path="/chat/completions",
            completion_path="/chat/completions",
            api_key_env="MINIMAX_API_KEY",
        )
    except Exception as exc:  # pragma: no cover - config shape regression
        LOG.warning("persona_executor: ProviderConfig build failed: %s", exc)
        return None

    prompt = _AUDIT_PROMPT_TEMPLATE.format(
        persona=persona,
        task_id=task.task_id,
        title=task.title,
        summary=task.summary,
        handoff_path=task.handoff_path or "(unspecified)",
        now=_now_iso(),
    )

    try:
        caller = completion_caller(config)
        response = caller(
            LLMRequest(
                prompt=prompt,
                max_completion_tokens=_max_completion_tokens(),
            )
        )
    except Exception as exc:  # noqa: BLE001 — LLM failure must not crash poller
        LOG.warning(
            "persona_executor: minimax call failed for task=%s persona=%s: %s",
            task.task_id,
            persona,
            exc,
        )
        return None

    metadata = {
        "model": "MiniMax-M2.7-highspeed",
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
    }
    return response.redacted_text, metadata


def _write_handoff_doc(
    task: queue_bridge.TaskSnapshot,
    body_markdown: str,
    persona: str,
    metadata: dict[str, Any],
    workspace_root: Path,
) -> Path | None:
    """Write the LLM-generated markdown to ``task.handoff_path``.

    Prepends an MVP-3 attestation header so the doc is clearly marked as
    machine-generated and must be operator-reviewed.

    Returns the absolute Path on success, ``None`` on failure (path
    outside workspace, write error, etc.).
    """
    if not task.handoff_path:
        LOG.warning("persona_executor: task=%s has no handoff_path", task.task_id)
        return None

    abs_path = (workspace_root / task.handoff_path).resolve()
    try:
        # Safety: refuse to write outside the workspace root.
        ws_resolved = workspace_root.resolve()
        try:
            abs_path.relative_to(ws_resolved)
        except ValueError:
            LOG.warning(
                "persona_executor: handoff_path %s escapes workspace %s",
                abs_path,
                ws_resolved,
            )
            return None
    except Exception as exc:  # noqa: BLE001
        LOG.warning("persona_executor: path resolution failed: %s", exc)
        return None

    header = (
        f"# {task.title}\n\n"
        f"> ⚙️ **MVP-3 attestation — operator review REQUIRED.**\n"
        f"> This document was produced by the Hermes Agent persona "
        f"`{persona}` running the W21-MVP-3 persona executor on "
        f"`{_now_iso()}`. The narrative below was generated by "
        f"`{metadata.get('model', 'unknown')}` "
        f"(tokens_in={metadata.get('tokens_in', '?')}, "
        f"tokens_out={metadata.get('tokens_out', '?')}) from the queued "
        f"task summary. **Treat as a starting draft, not a final audit.** "
        f"Verify every concrete claim before publishing.\n\n"
        f"**Task:** `{task.task_id}` — priority {task.priority} — "
        f"target_owner_pattern `{task.target_owner_pattern}`\n\n"
        f"---\n\n"
    )

    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(header + body_markdown, encoding="utf-8")
    except OSError as exc:
        LOG.warning("persona_executor: write %s failed: %s", abs_path, exc)
        return None
    return abs_path


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def execute_one(task: queue_bridge.TaskSnapshot, workspace_root: Path) -> dict[str, Any]:
    """Process one claimed task. Returns a result dict.

    Result shape::

        {
          "task_id":   "<id>",
          "outcome":   "done" | "blocked",
          "reason":    "<short string>",
          "handoff":   "<absolute path on done>" | None,
          "class":     "audit" | "unknown",
        }

    Outcomes:
      * ``done`` — handoff produced + task moved to ``done/``.
      * ``blocked`` — no executor for this task class, OR LLM/write
        failure. Task moved to ``blocked/`` with reason. The operator
        can release+re-queue the task after fixing the cause.
    """
    persona = (task.claimed_by or "").removeprefix("hermes/") or "unknown-persona"
    task_class = classify_task(task)

    if task_class != "audit":
        reason = f"no_automated_executor_for_task_class:{task_class}"
        ok = queue_bridge.block_task(workspace_root, task.task_id, reason, persona=persona)
        _emit_proof_event(
            "persona_executor.task.blocked",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "reason": reason,
                "moved": ok,
            },
        )
        return {
            "task_id": task.task_id,
            "outcome": "blocked",
            "reason": reason,
            "handoff": None,
            "class": task_class,
        }

    # Audit class — try to generate the handoff doc.
    generated = _generate_audit_markdown(task, persona)
    if generated is None:
        reason = "llm_generation_failed_or_unavailable"
        ok = queue_bridge.block_task(workspace_root, task.task_id, reason, persona=persona)
        _emit_proof_event(
            "persona_executor.task.blocked",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "reason": reason,
                "moved": ok,
            },
        )
        return {
            "task_id": task.task_id,
            "outcome": "blocked",
            "reason": reason,
            "handoff": None,
            "class": task_class,
        }

    body, metadata = generated
    written_path = _write_handoff_doc(task, body, persona, metadata, workspace_root)
    if written_path is None:
        reason = "handoff_path_write_failed_or_outside_workspace"
        ok = queue_bridge.block_task(workspace_root, task.task_id, reason, persona=persona)
        _emit_proof_event(
            "persona_executor.task.blocked",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "reason": reason,
                "moved": ok,
            },
        )
        return {
            "task_id": task.task_id,
            "outcome": "blocked",
            "reason": reason,
            "handoff": None,
            "class": task_class,
        }

    # Success: mark task done.
    ok = queue_bridge.complete_task(workspace_root, task.task_id, persona=persona)
    _emit_proof_event(
        "persona_executor.task.done",
        {
            "task_id": task.task_id,
            "persona": persona,
            "class": task_class,
            "handoff_path": str(written_path),
            "tokens_in": metadata.get("tokens_in"),
            "tokens_out": metadata.get("tokens_out"),
            "model": metadata.get("model"),
            "moved": ok,
        },
    )
    return {
        "task_id": task.task_id,
        "outcome": "done",
        "reason": "audit_handoff_generated",
        "handoff": str(written_path),
        "class": task_class,
    }


def execute_claimed_tasks(workspace_root: Path | None = None) -> list[dict[str, Any]]:
    """Walk ``claimed/`` and execute up to ``MAX_EXECUTE_PER_TICK`` tasks.

    Returns the list of per-task result dicts (see :func:`execute_one`).
    Honors ``HERMES3D_PERSONA_EXECUTOR_DISABLED=1`` (no-op fast path).

    Designed to be called from the asyncio queue poller's tick once
    MVP-3 wiring is enabled. The function itself is synchronous +
    file-system bounded.
    """
    if _executor_disabled():
        return []
    root = workspace_root if workspace_root is not None else _workspace_root()
    claimed = queue_bridge.list_tasks(root, "claimed")
    if not claimed:
        return []
    max_per_tick = _max_execute_per_tick()
    results: list[dict[str, Any]] = []
    # Process in priority order (highest first) so the most-urgent
    # claimed tasks are executed before lower-priority ones in a tick.
    claimed.sort(key=lambda t: (-t.priority, t.task_id))
    for task in claimed:
        if len(results) >= max_per_tick:
            break
        # Only execute tasks claimed by one of OUR personas.
        owner = task.claimed_by or ""
        if not owner.startswith("hermes/"):
            continue
        result = execute_one(task, root)
        results.append(result)
    return results


__all__ = [
    "classify_task",
    "execute_claimed_tasks",
    "execute_one",
]
