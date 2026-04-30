"""Repair agent — strategy ladder for resolving ``RepairEscalation``.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §30 (Orchestration Brain)

When a workflow node exhausts its retry budget the orchestrator hands the
escalation to a ``RepairAgent``. The agent walks an ordered ladder of
strategies, stopping at the first one that produces a remedy:

    1. Lookup matching ``failure_pattern`` skill in :class:`SkillStore`.
    2. If a high-confidence (>= 0.6) skill exists, return its remedy.
    3. Optionally consult an LLM provider for a suggested patch
       (gracefully skipped if no provider is available offline).
    4. Notify a human operator via :class:`Notifier`.

This module is deliberately read-mostly: it never *applies* a fix — it
returns a structured ``RepairResult`` that the orchestration layer
inspects to decide whether to resume, escalate, or abort.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from .retry_controller import RepairEscalation

log = logging.getLogger(__name__)


@dataclass
class RepairResult:
    outcome: Literal["fixed", "escalated", "unfixable"]
    strategy_used: str
    notes: str = ""
    suggested_action: dict[str, Any] = field(default_factory=dict)


class RepairAgent:
    """Resolve escalations by walking a strategy ladder.

    Args:
        skill_store: optional ``SkillStore`` used to look up matching
            ``failure_pattern`` skills.
        notifier: optional ``Notifier`` used for human-escalation. A
            default ``Notifier()`` is constructed if ``None``.
        llm_client: optional pre-built LLM client. If ``None``, the agent
            will *attempt* to lazily construct one via
            ``select_provider`` and gracefully skip if no provider is
            reachable.
        confidence_threshold: minimum skill confidence to auto-apply a
            remedy; below this we still escalate.
    """

    def __init__(
        self,
        *,
        skill_store: Any = None,
        notifier: Any = None,
        llm_client: Any = None,
        confidence_threshold: float = 0.6,
    ) -> None:
        self.skill_store = skill_store
        self._notifier = notifier
        self._llm_client = llm_client
        self.confidence_threshold = float(confidence_threshold)

    # ---- Public ------------------------------------------------------------

    def repair(self, escalation: RepairEscalation) -> RepairResult:
        # 1+2: SkillStore lookup
        skill_result = self._try_skill_store(escalation)
        if skill_result is not None:
            return skill_result

        # 3: LLM-suggested patch (best effort, may be unavailable)
        llm_result = self._try_llm(escalation)
        if llm_result is not None:
            return llm_result

        # 4: Human escalation
        return self._escalate_to_human(escalation)

    # ---- Strategies --------------------------------------------------------

    def _try_skill_store(self, esc: RepairEscalation) -> RepairResult | None:
        if self.skill_store is None:
            return None
        try:
            from hermes3d.core.memory.skill_store import SkillKind
        except Exception:
            return None
        ctx = esc.context or {}
        # Optional scope hints — pull from context if available.
        try:
            matches = self.skill_store.lookup(
                kind=SkillKind.FAILURE_PATTERN,
                printer_id=ctx.get("printer_id"),
                material=ctx.get("material"),
                quality_level=ctx.get("quality_level"),
            )
        except Exception as exc:
            log.warning("SkillStore lookup failed: %s", exc)
            return None
        if not matches:
            return None
        best = matches[0]
        if best.confidence < self.confidence_threshold:
            # Found a hint, but not strong enough — record it and let the
            # ladder continue (we still escalate, but with a note).
            return (
                RepairResult(
                    outcome="escalated",
                    strategy_used="skill_store_low_confidence",
                    notes=(
                        f"matching skill {best.skill_id!r} found but "
                        f"confidence {best.confidence:.2f} < "
                        f"{self.confidence_threshold:.2f}"
                    ),
                    suggested_action={"skill_id": best.skill_id, "body": dict(best.body)},
                ).__post_attach_escalate__()
                if False
                else self._escalate_to_human(
                    esc,
                    pre_note=(
                        f"low-confidence skill {best.skill_id!r} "
                        f"(c={best.confidence:.2f}) suggests "
                        f"{best.body!r}"
                    ),
                )
            )
        return RepairResult(
            outcome="fixed",
            strategy_used="skill_store",
            notes=(
                f"applied failure_pattern skill {best.skill_id!r} "
                f"(confidence={best.confidence:.2f})"
            ),
            suggested_action={
                "skill_id": best.skill_id,
                "body": dict(best.body),
                "name": best.name,
            },
        )

    def _try_llm(self, esc: RepairEscalation) -> RepairResult | None:
        client = self._llm_client
        if client is None:
            try:
                from hermes3d.core.llm.providers import (
                    select_provider,
                )
            except Exception:
                return None
            try:
                client = select_provider()
            except Exception:
                return None
            if not getattr(client, "available", lambda: False)():
                return None
        # Build a tight prompt and ask for a JSON suggestion.
        try:
            ctx = esc.context or {}
            prompt = (
                "A workflow node failed. Suggest a concrete remedy as JSON "
                "with keys 'remedy' (string) and 'rationale' (string).\n"
                f"Node: {ctx.get('node_name')!r}\n"
                f"Error: {esc.cause!r}\n"
                f"Attempts: {esc.attempts}\n"
            )
            result = client.generate(prompt)
        except Exception as exc:
            log.info("LLM repair suggestion unavailable: %s", exc)
            return None
        # Try to extract JSON, but tolerate plain text.
        suggestion: dict[str, Any] = {"raw": getattr(result, "text", str(result))}
        try:
            from hermes3d.core.llm.providers import extract_json

            suggestion = extract_json(getattr(result, "text", "")) or suggestion
        except Exception:
            pass
        return RepairResult(
            outcome="fixed",
            strategy_used="llm_suggestion",
            notes="LLM-suggested remedy (review before re-running)",
            suggested_action=suggestion,
        )

    def _escalate_to_human(self, esc: RepairEscalation, *, pre_note: str = "") -> RepairResult:
        notifier = self._notifier
        sent_count = 0
        if notifier is None:
            try:
                from hermes3d.core.notifications.notifier import Notifier

                notifier = Notifier()
            except Exception:
                notifier = None
        if notifier is not None:
            try:
                from hermes3d.core.notifications.notifier import (
                    NotificationEvent,
                    NotificationLevel,
                )

                ctx = esc.context or {}
                evt = NotificationEvent(
                    title="Hermes3D repair escalation",
                    message=(
                        f"Node {ctx.get('node_name')!r} failed after "
                        f"{esc.attempts} attempts: {esc.cause!r}"
                    ),
                    level=NotificationLevel.ERROR,
                    printer_id=ctx.get("printer_id"),
                    job_id=ctx.get("job_id"),
                    extra={"pre_note": pre_note} if pre_note else {},
                )
                results = notifier.notify(evt)
                sent_count = sum(1 for r in results if getattr(r, "sent", False))
            except Exception as exc:
                log.warning("Notifier escalation failed: %s", exc)
        notes = (pre_note + " | " if pre_note else "") + (
            f"notified {sent_count} channel(s)" if notifier is not None else "no notifier available"
        )
        return RepairResult(
            outcome="escalated",
            strategy_used="human",
            notes=notes,
            suggested_action={
                "node_name": (esc.context or {}).get("node_name"),
                "cause": repr(esc.cause),
                "attempts": esc.attempts,
            },
        )


__all__ = ["RepairAgent", "RepairResult"]
