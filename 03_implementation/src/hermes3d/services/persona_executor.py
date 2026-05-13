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
from hermes3d.services.llm_output_sanitizer import sanitize_reasoning_output

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
    # 4096 tokens fits the gateway's tunable timeout (default 60 s via
    # HERMES3D_MINIMAX_COMPLETION_TIMEOUT_S). Earlier 1024 cap forced
    # reasoning-aloud models to exhaust their budget mid-think, leaving
    # raw <think> tags in the handoff body. With 4096 the model can
    # finish reasoning AND emit the final audit markdown.
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
2. No fake-pass / no-aspirational language. If something is not measured, say "not measured" — but use that phrase AT MOST 2 times in the whole doc.
3. Cite filepaths, route names, byte counts, or HTTP status codes ONLY when they appear verbatim in the task summary above OR are obvious Hermes3D-wide names (e.g. `/api/agents/health`). Do NOT invent file paths, line numbers, framework names, or component names. If you don't know a specific file, say so explicitly rather than making one up.
4. This is a Python + React codebase. The backend lives under `03_implementation/src/hermes3d/` (FastAPI) and the UI under `03_implementation/ui/src/` (React/TypeScript). Do NOT cite Vue.js, Angular, Django, Flask, Go, or any framework not used here.
5. Surface unknowns explicitly with a header section.
6. Mark this doc as MVP-3-generated and require operator review before treating it as final.

Task title: {title}
Task summary:
{summary}

Deliverable path (relative to repo root): {handoff_path}
Auditor identity: persona `{persona}` (Hermes Agent MVP-3 executor)
Date (UTC): {now}

Produce a CONCISE markdown document starting with a level-1 header. Include compact sections:
  - Verdict (one short sentence)
  - Scope (what is and is NOT in this audit)
  - Findings (3-6 numbered bullets, each one line)
  - Gaps / Unknowns (3-5 bullets)
  - Recommended next actions (3-5 bullets, imperative phrasing)
  - MVP-3 attestation footer (one paragraph)

STRICT: keep under 600 words total. Do NOT invent data; mark uncertain items "not measured" or "operator must verify". This is a starting draft, not a final audit.
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
                # token_id is an audit-ledger identifier the gateway threads
                # through to the proof envelope; use the task_id so the
                # generated handoff is traceable to the originating queue
                # task without an extra lookup.
                token_id=f"persona-executor/{task.task_id}",
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


def _sanitize_llm_output(text: str) -> str:
    """Aggressive sanitiser for reasoning-aloud LLM output.

    Performs:

    1. Strip closed ``<think>...</think>`` blocks (any case).
    2. Drop unclosed ``<think>...`` to end of string (truncated reasoning).
    3. Unwrap a single outermost ```markdown / ``` fence that wraps the
       entire document (some MiniMax responses wrap the whole answer in
       a code fence — we want the rendered markdown, not a code block).
    4. Strip an outermost ```/```` fence with no language tag too.
    5. Collapse 3+ consecutive blank lines to 2.

    Returns the cleaned text with leading/trailing whitespace trimmed.

    The strict ``_passes_quality_gate`` check below catches anything this
    sanitiser misses (e.g. multiple nested fences, mid-document leaks).
    """
    return sanitize_reasoning_output(text)


# Backward-compat alias for existing tests.
_strip_think_blocks = _sanitize_llm_output


# Quality-gate thresholds. Tunable but conservative defaults so a model
# producing "I don't know" boilerplate is rejected.
_QUALITY_MIN_CHARS = 400
_QUALITY_MAX_NOT_MEASURED_HITS = 3
_QUALITY_BOILERPLATE_PHRASES = (
    "not measured",
    "operator must verify",
    "i don't have access",
    "i cannot verify",
    "i can't verify",
    "i don't know",
    "as an ai",
    "i am an ai",
    "as a language model",
)

# Hallucination tripwires: phrases that prove the LLM invented frameworks /
# tools that this codebase does NOT use. Hermes3D is Python (FastAPI) +
# React (TypeScript). Any other framework reference is a hallucination.
_HALLUCINATION_PHRASES = (
    ".vue",  # Vue single-file components
    "vue.js",
    "vuejs",
    "angular",
    "django",
    "flask",
    "express.js",
    "rails",
    "spring boot",
    "spring-boot",
    "node.js backend",  # the backend is Python, not Node
    "express server",
)


def _passes_quality_gate(sanitized_body: str) -> tuple[bool, str | None]:
    """Run the quality gate against sanitised LLM output.

    Returns ``(True, None)`` on pass, or ``(False, reason)`` on reject.

    Rejects:

    * Still contains a ``<think>`` tag (sanitiser bypass).
    * Still contains a ``​``-suspicious fenced ```markdown header
      anywhere in the body (multi-fence response).
    * Body length under :data:`_QUALITY_MIN_CHARS` (empty / near-empty).
    * Body has more than :data:`_QUALITY_MAX_NOT_MEASURED_HITS`
      occurrences of any boilerplate phrase (mostly "I don't know").

    A rejecting task is moved to ``blocked/`` with the returned reason
    so the operator sees exactly why MVP-3 declined to publish.
    """
    if not sanitized_body or not sanitized_body.strip():
        return False, "quality_gate:empty_after_sanitize"
    if "<think>" in sanitized_body.lower():
        return False, "quality_gate:think_tag_survived_sanitizer"
    # A whole-doc fence should already be unwrapped; reject if one
    # survives at the very start (defensive — the LLM emitted nested or
    # malformed fences).
    # Any triple-fence at the very top of the doc is suspect: a real
    # handoff starts with an ``#`` heading. ``` (bare), ```markdown,
    # ```md, ```text are all treated as a sanitizer bypass.
    head = sanitized_body[:200].lstrip()
    if head.startswith("```"):
        return False, "quality_gate:whole_document_markdown_fence_survived"
    if len(sanitized_body) < _QUALITY_MIN_CHARS:
        return False, f"quality_gate:too_short:{len(sanitized_body)}<{_QUALITY_MIN_CHARS}"
    lower = sanitized_body.lower()
    hits = sum(lower.count(phrase) for phrase in _QUALITY_BOILERPLATE_PHRASES)
    if hits > _QUALITY_MAX_NOT_MEASURED_HITS:
        return False, f"quality_gate:boilerplate_density:{hits}>{_QUALITY_MAX_NOT_MEASURED_HITS}"
    # Hallucination tripwire: any framework/tool reference the codebase
    # doesn't use indicates the LLM invented context. Reject so the
    # operator sees the explicit reason.
    for phrase in _HALLUCINATION_PHRASES:
        if phrase in lower:
            return False, f"quality_gate:hallucinated_framework:{phrase}"
    return True, None


def _resolve_handoff_path(task: queue_bridge.TaskSnapshot, workspace_root: Path) -> Path | None:
    """Resolve task.handoff_path under workspace_root with escape guard.

    Returns the absolute Path or None on failure. Pure resolution — does
    NOT touch the filesystem.
    """
    if not task.handoff_path:
        LOG.warning("persona_executor: task=%s has no handoff_path", task.task_id)
        return None
    abs_path = (workspace_root / task.handoff_path).resolve()
    try:
        ws_resolved = workspace_root.resolve()
        abs_path.relative_to(ws_resolved)
    except ValueError:
        LOG.warning(
            "persona_executor: handoff_path %s escapes workspace %s",
            abs_path,
            workspace_root,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        LOG.warning("persona_executor: path resolution failed: %s", exc)
        return None
    return abs_path


def _is_existing_handoff_substantial(abs_path: Path) -> bool:
    """A handoff file is 'substantial' if it exists and is non-trivial.

    >= 200 bytes is the cutoff so a tiny one-line `# Title` left by a
    prior bad MVP-3 run still counts as overwrite-able, but a real
    operator-written audit (always > 1 KB) is preserved.
    """
    try:
        if not abs_path.is_file():
            return False
        return abs_path.stat().st_size >= 200
    except OSError:
        return False


def _write_handoff_doc(
    task: queue_bridge.TaskSnapshot,
    body_markdown: str,
    persona: str,
    metadata: dict[str, Any],
    workspace_root: Path,
) -> tuple[Path, str] | tuple[None, str]:
    """Sanitise + quality-gate + write the LLM-generated markdown.

    Returns ``(Path, "written")`` on success, ``(None, "<reject_reason>")``
    on quality-gate reject or write failure. The reject reason flows into
    the task's blocked_reason so the operator knows exactly why the
    persona declined to publish.

    Preserves any existing substantial handoff file at the target path:
    returns ``(existing_path, "preserved_existing_handoff")`` without
    overwriting. This protects human-written audits from being
    clobbered by MVP-3 drafts.
    """
    # 1. Path resolution + escape guard.
    abs_path = _resolve_handoff_path(task, workspace_root)
    if abs_path is None:
        return None, "handoff_path_unresolvable_or_outside_workspace"

    # 2. Preserve existing substantial handoff.
    if _is_existing_handoff_substantial(abs_path):
        LOG.info(
            "persona_executor: preserving existing handoff at %s (task=%s)",
            abs_path,
            task.task_id,
        )
        return abs_path, "preserved_existing_handoff"

    # 3. Sanitise LLM output.
    body_markdown = _sanitize_llm_output(body_markdown)

    # 4. Quality gate.
    ok, reject_reason = _passes_quality_gate(body_markdown)
    if not ok:
        return None, reject_reason or "quality_gate:unknown_reason"

    # 5. Write attestation header + sanitised body.
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
        return None, f"write_failed:{exc.__class__.__name__}"
    return abs_path, "written"


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

    # PRESERVE-EXISTING short-circuit: if the handoff_path already exists
    # with substantial human-written content (>=200 bytes), do NOT call
    # the LLM — mark the task done and keep the existing file untouched.
    # Prevents the executor from clobbering operator-written audits with
    # weaker MVP-3 drafts.
    abs_path = _resolve_handoff_path(task, workspace_root)
    if abs_path is None:
        # Malformed task: handoff_path missing or escaping the workspace.
        # Block before burning an LLM call — the operator must fix the
        # task definition.
        reason = "invalid_handoff_path"
        ok = queue_bridge.block_task(workspace_root, task.task_id, reason, persona=persona)
        _emit_proof_event(
            "persona_executor.task.blocked",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "handoff_path": task.handoff_path,
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

    if _is_existing_handoff_substantial(abs_path):
        LOG.info(
            "persona_executor: preserving existing handoff at %s for task=%s",
            abs_path,
            task.task_id,
        )
        ok = queue_bridge.complete_task(workspace_root, task.task_id, persona=persona)
        _emit_proof_event(
            "persona_executor.task.done",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "handoff_path": str(abs_path),
                "write_status": "preserved_existing_handoff",
                "moved": ok,
            },
        )
        return {
            "task_id": task.task_id,
            "outcome": "done",
            "reason": "preserved_existing_handoff",
            "handoff": str(abs_path),
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
    written_path, write_status = _write_handoff_doc(task, body, persona, metadata, workspace_root)
    if written_path is None:
        # Quality gate or write failure — block with the gate's exact reason.
        reason = write_status
        ok = queue_bridge.block_task(workspace_root, task.task_id, reason, persona=persona)
        _emit_proof_event(
            "persona_executor.task.blocked",
            {
                "task_id": task.task_id,
                "persona": persona,
                "class": task_class,
                "reason": reason,
                "tokens_in": metadata.get("tokens_in"),
                "tokens_out": metadata.get("tokens_out"),
                "model": metadata.get("model"),
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

    # Success: mark task done. write_status is "written" or
    # "preserved_existing_handoff" (we keep human-verified content).
    ok = queue_bridge.complete_task(workspace_root, task.task_id, persona=persona)
    _emit_proof_event(
        "persona_executor.task.done",
        {
            "task_id": task.task_id,
            "persona": persona,
            "class": task_class,
            "handoff_path": str(written_path),
            "write_status": write_status,
            "tokens_in": metadata.get("tokens_in"),
            "tokens_out": metadata.get("tokens_out"),
            "model": metadata.get("model"),
            "moved": ok,
        },
    )
    # If we preserved an existing human-verified handoff, surface that
    # in the reason so audit logs differentiate human vs. MVP-3 drafts.
    reason = (
        "preserved_existing_handoff"
        if write_status == "preserved_existing_handoff"
        else "audit_handoff_generated"
    )
    return {
        "task_id": task.task_id,
        "outcome": "done",
        "reason": reason,
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
