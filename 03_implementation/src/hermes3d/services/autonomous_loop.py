from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from hermes3d.api.routes._common import as_json, execute, new_id, utc_now


@dataclass
class AutonomousStateSnapshot:
    timestamp: str
    printers: list[dict[str, Any]] = field(default_factory=list)
    active_jobs: list[dict[str, Any]] = field(default_factory=list)
    queued_jobs: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: list[dict[str, Any]] = field(default_factory=list)
    agent_health: dict[str, str] = field(default_factory=dict)


@dataclass
class ActionProposal:
    persona_id: str
    action_type: str
    payload: dict[str, Any]
    risk_level: str
    safety_decision: str
    reason: str


class AutonomousLoop:
    def __init__(self, cadence_seconds: int = 60) -> None:
        self.cadence_seconds = cadence_seconds
        self.running = False
        self.session_id: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._in_action = False

    async def start(self, session_id: str, cadence_seconds: int | None = None) -> None:
        if self.running:
            return
        self.session_id = session_id
        self.cadence_seconds = cadence_seconds or self.cadence_seconds
        self.running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.running = False
        while self._in_action:
            await asyncio.sleep(0.01)
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _run(self) -> None:
        while self.running:
            await self._tick()
            await asyncio.sleep(self.cadence_seconds)

    async def _tick(self) -> AutonomousStateSnapshot:
        snapshot = self._gather_state()
        proposal = self._propose_action(
            "print-monitor-agent",
            "heartbeat",
            {"printer_id": "none", "timestamp": snapshot.timestamp},
            "low",
        )
        if self.session_id:
            self._execute_action(self.session_id, proposal)
        return snapshot

    def _gather_state(self) -> AutonomousStateSnapshot:
        return AutonomousStateSnapshot(
            timestamp=utc_now(),
            printers=[{"printer_id": "flsun-s1", "status": "locked"}],
            agent_health={"print-safety-agent": "idle", "print-monitor-agent": "idle"},
        )

    def _propose_action(
        self,
        persona_id: str,
        action_type: str,
        payload: dict[str, Any],
        risk_level: str,
    ) -> ActionProposal:
        printer_id = str(payload.get("printer_id", ""))
        if printer_id in {"flsun-s1", "flsun_s1", "s1"}:
            return ActionProposal(
                persona_id, action_type, payload, risk_level, "vetoed", "FLSUN S1 is locked."
            )
        return ActionProposal(
            persona_id, action_type, payload, risk_level, "approved", "Safe action scope."
        )

    def _execute_action(self, session_id: str, proposal: ActionProposal) -> dict[str, Any]:
        self._in_action = True
        try:
            outcome = "skipped" if proposal.safety_decision == "vetoed" else "success"
            action_id = new_id()
            execute(
                """
                INSERT INTO agent_autonomous_actions
                    (id, session_id, persona_id, action_type, action_payload,
                     safety_agent_status, veto_reason, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    session_id,
                    proposal.persona_id,
                    proposal.action_type,
                    as_json(proposal.payload),
                    proposal.safety_decision,
                    proposal.reason if proposal.safety_decision == "vetoed" else None,
                    outcome,
                ),
            )
            execute(
                "UPDATE agent_autonomous_sessions SET actions_taken = actions_taken + 1 WHERE id = ?",
                (session_id,),
            )
            self._emit_notification(
                "INFO" if outcome == "success" else "ACTION_REQUIRED",
                "Autonomous action recorded",
                f"{proposal.action_type}: {outcome}",
            )
            return {"action_id": action_id, "outcome": outcome}
        finally:
            self._in_action = False

    def _escalate(self, session_id: str, reason: str) -> dict[str, Any]:
        execute(
            "UPDATE agent_autonomous_sessions SET escalations = escalations + 1 WHERE id = ?",
            (session_id,),
        )
        return self._emit_notification("ACTION_REQUIRED", "Autonomous escalation", reason)

    def _emit_notification(self, notification_type: str, title: str, body: str) -> dict[str, Any]:
        notification_id = new_id()
        priority = "high" if notification_type == "ACTION_REQUIRED" else "low"
        execute(
            """
            INSERT INTO notifications
                (id, type, priority, title, body, source_agent_id, source_tab)
            VALUES (?, ?, ?, ?, ?, 'autonomous-loop', 'autopilot')
            """,
            (notification_id, notification_type, priority, title, body),
        )
        return {"id": notification_id, "type": notification_type, "priority": priority}
