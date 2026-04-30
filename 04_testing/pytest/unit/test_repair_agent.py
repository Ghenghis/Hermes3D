"""Tests for RepairAgent strategy ladder."""

from __future__ import annotations

from hermes3d.core.memory.skill_store import (
    SkillKind,
    SkillScope,
    SkillStore,
)
from hermes3d.core.orchestration.repair_agent import RepairAgent, RepairResult
from hermes3d.core.orchestration.retry_controller import RepairEscalation


def _make_escalation(node_name: str = "slice") -> RepairEscalation:
    return RepairEscalation(
        cause=RuntimeError("first layer adhesion lost"),
        attempts=4,
        context={"node_name": node_name, "printer_id": "p1", "material": "PETG"},
    )


class _FakeNotifier:
    def __init__(self) -> None:
        self.events: list = []

    def notify(self, event):
        self.events.append(event)

        # Mimic NotificationResult shape (has .sent attr)
        class _R:
            sent = True
            channel = "fake"
            error = None

        return [_R()]


def test_skill_store_match_yields_fixed(tmp_path):
    store = SkillStore(tmp_path / "skills.json")
    store.add(
        skill_kind=SkillKind.FAILURE_PATTERN,
        name="petg_first_layer",
        scope=SkillScope(printer_id="p1", material="PETG"),
        body={"remedy": "raise bed temp +5C", "trigger": "first layer"},
        confidence=0.85,
        source="user_explicit",
    )
    notifier = _FakeNotifier()
    agent = RepairAgent(skill_store=store, notifier=notifier, llm_client=None)
    result = agent.repair(_make_escalation())
    assert isinstance(result, RepairResult)
    assert result.outcome == "fixed"
    assert result.strategy_used == "skill_store"
    assert result.suggested_action.get("body", {}).get("remedy") == "raise bed temp +5C"
    # No human escalation when fixed
    assert notifier.events == []


def test_no_skill_no_llm_escalates_and_notifies(tmp_path):
    store = SkillStore(tmp_path / "skills.json")  # empty
    notifier = _FakeNotifier()

    class _DeadLLM:
        def available(self):
            return False

    agent = RepairAgent(skill_store=store, notifier=notifier, llm_client=_DeadLLM())
    result = agent.repair(_make_escalation())
    assert result.outcome == "escalated"
    assert result.strategy_used == "human"
    assert len(notifier.events) == 1


def test_low_confidence_skill_escalates(tmp_path):
    store = SkillStore(tmp_path / "skills.json")
    store.add(
        skill_kind=SkillKind.FAILURE_PATTERN,
        name="weak_hint",
        scope=SkillScope(printer_id="p1", material="PETG"),
        body={"remedy": "maybe lower speed"},
        confidence=0.3,  # below default threshold of 0.6
    )
    notifier = _FakeNotifier()
    agent = RepairAgent(skill_store=store, notifier=notifier, llm_client=None)
    result = agent.repair(_make_escalation())
    assert result.outcome == "escalated"
    # Low-confidence path should still notify a human.
    assert len(notifier.events) == 1
    assert "low-confidence" in (result.notes or "").lower() or "low_confidence" in (
        result.strategy_used or ""
    )
