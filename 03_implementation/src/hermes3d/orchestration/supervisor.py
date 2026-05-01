"""Offline-only orchestration supervisor skeleton."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from dataclasses import asdict, is_dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping

from .dag import TaskDAG
from .ledger import LedgerEvent, OrchestrationLedger
from .types import (
    CapabilityToken,
    Err,
    Gen3DRequest,
    Gen3DResult,
    Ok,
    PlanRequest,
    PlanResult,
    PollRequest,
    PollResult,
    PrinterMirror,
    Result,
    SimulatedModelArtifact,
)

OfflinePollHandler = Callable[[PollRequest], PrinterMirror | Result[PrinterMirror]]
OfflinePlanHandler = Callable[[PlanRequest], TaskDAG | Result[TaskDAG]]
OfflineGen3DHandler = Callable[
    [Gen3DRequest], SimulatedModelArtifact | Result[SimulatedModelArtifact]
]
DEFAULT_REGISTERED_TOOLS = frozenset({"printer.poll", "planner.plan", "gen3d.generate"})


class OfflineSupervisor:
    """Capability-token supervisor for Phase 3.1 offline dispatch."""

    def __init__(
        self,
        *,
        ledger: OrchestrationLedger | None = None,
        current_phase: int = 3,
        signing_secret: str | None = None,
        registered_tools: frozenset[str] = DEFAULT_REGISTERED_TOOLS,
    ) -> None:
        self.ledger = ledger
        self.current_phase = current_phase
        self._signing_secret = signing_secret or "hermes3d-phase-3-1-offline"
        self._registered_tools = frozenset(registered_tools)
        self._tokens: dict[str, CapabilityToken] = {}
        self._consumed_tokens: set[str] = set()
        self._printer_locks: dict[str, threading.Lock] = {}
        self._run_locks: dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def issue_token(
        self,
        *,
        agent_id: str,
        tools: frozenset[str],
        scopes: frozenset[str] = frozenset(),
        ttl_seconds: int = 60,
        now_utc: datetime | None = None,
        phase: int | None = None,
    ) -> CapabilityToken:
        now = _normalize_utc(now_utc)
        token_phase = self.current_phase if phase is None else phase
        unsigned = CapabilityToken(
            token_id=str(uuid.uuid4()),
            agent_id=agent_id,
            tools=frozenset(tools),
            scopes=frozenset(scopes),
            issued_at_utc=_iso_utc(now),
            expires_at_utc=_iso_utc(now + timedelta(seconds=ttl_seconds)),
            phase=token_phase,
            signature="",
        )
        token = replace(unsigned, signature=self._sign(unsigned))
        with self._registry_lock:
            self._tokens[token.token_id] = token
        return token

    def _validate_token_unlocked(
        self,
        token: CapabilityToken | None,
        *,
        tool: str,
        now_utc: datetime | None = None,
    ) -> Result[CapabilityToken]:
        if token is None:
            return Err("no_token", "dispatch requires a capability token")

        registered = self._tokens.get(token.token_id)
        consumed = token.token_id in self._consumed_tokens
        if registered is None or consumed:
            return Err("token_unknown", "token is unknown or already consumed")
        if registered != token or not hmac.compare_digest(token.signature, self._sign(token)):
            return Err("token_unknown", "token signature does not match registry")
        if token.phase > self.current_phase:
            return Err("phase_violation", "token phase exceeds supervisor phase")
        if tool not in token.tools:
            return Err("tool_not_authorized", "token is not authorized for this tool")

        now = _normalize_utc(now_utc)
        expires = datetime.fromisoformat(token.expires_at_utc.replace("Z", "+00:00"))
        if now >= expires:
            return Err("token_expired", "token has expired")

        return Ok(token)

    def _validate_and_consume_token(
        self,
        token: CapabilityToken | None,
        *,
        tool: str,
        now_utc: datetime | None = None,
    ) -> Result[CapabilityToken]:
        with self._registry_lock:
            validation = self._validate_token_unlocked(token, tool=tool, now_utc=now_utc)
            if isinstance(validation, Err):
                return validation
            self._consumed_tokens.add(validation.value.token_id)
            return validation

    def dispatch_poll(
        self,
        request: PollRequest,
        *,
        token: CapabilityToken | None = None,
        handler: OfflinePollHandler | None = None,
        now_utc: datetime | None = None,
    ) -> PollResult:
        validation = self._validate_and_consume_token(token, tool=request.tool, now_utc=now_utc)
        if isinstance(validation, Err):
            return self._refuse(request, validation, token)

        lock = self.mutex_for(request.printer_id)
        with lock:
            if handler is None:
                result: Result[PrinterMirror] = Err(
                    "offline_handler_missing",
                    "no offline handler registered for dispatch",
                )
            else:
                handled = handler(request)
                if isinstance(handled, (Ok, Err)):
                    result = handled
                else:
                    result = Ok(handled, "offline dispatch completed")

        poll_result = PollResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            printer_id=request.printer_id,
            tool=request.tool,
            result=result,
            token_id=validation.value.token_id,
        )
        self._append_event(request, poll_result)
        return poll_result

    def dispatch_plan(
        self,
        request: PlanRequest,
        *,
        token: CapabilityToken | None = None,
        handler: OfflinePlanHandler | None = None,
        now_utc: datetime | None = None,
    ) -> PlanResult:
        validation = self._validate_and_consume_token(token, tool=request.tool, now_utc=now_utc)
        if isinstance(validation, Err):
            return self._refuse_plan(request, validation, token)

        lock = self.mutex_for_run(request.run_id)
        with lock:
            result: Result[TaskDAG]
            if handler is None:
                result = Err(
                    "offline_handler_missing",
                    "no offline planner registered for dispatch",
                )
            else:
                try:
                    handled = handler(request)
                except Exception as exc:  # pragma: no cover - defensive audit path
                    result = Err("offline_handler_failed", str(exc), recoverable=False)
                else:
                    if isinstance(handled, (Ok, Err)):
                        result = handled
                    else:
                        result = Ok(handled, "offline plan dispatch completed")

            if isinstance(result, Ok):
                dag_validation = result.value.validate()
                if isinstance(dag_validation, Err):
                    result = dag_validation
                else:
                    r6_validation = self._validate_dag_tools(result.value)
                    if isinstance(r6_validation, Err):
                        result = r6_validation

        plan_result = PlanResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            tool=request.tool,
            result=result,
            token_id=validation.value.token_id,
        )
        self._append_event(request, plan_result)
        return plan_result

    def dispatch_gen3d(
        self,
        request: Gen3DRequest,
        *,
        token: CapabilityToken | None = None,
        handler: OfflineGen3DHandler | None = None,
        now_utc: datetime | None = None,
    ) -> Gen3DResult:
        validation = self._validate_and_consume_token(token, tool=request.tool, now_utc=now_utc)
        if isinstance(validation, Err):
            return self._refuse_gen3d(request, validation, token)

        if request.tool not in self._registered_tools:
            result: Result[SimulatedModelArtifact] = Err(
                "tool_unregistered",
                f"tool is not registered: {request.tool}",
            )
        else:
            lock = self.mutex_for_run(request.run_id)
            with lock:
                if handler is None:
                    result = Err(
                        "offline_handler_missing",
                        "no offline Gen3D handler registered for dispatch",
                    )
                else:
                    try:
                        handled = handler(request)
                    except Exception as exc:  # pragma: no cover - defensive audit path
                        result = Err("offline_handler_failed", str(exc), recoverable=False)
                    else:
                        if isinstance(handled, (Ok, Err)):
                            result = handled
                        else:
                            result = Ok(handled, "offline Gen3D dispatch completed")

        gen3d_result = Gen3DResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            node_id=request.node_id,
            tool=request.tool,
            result=result,
            token_id=validation.value.token_id,
        )
        self._append_event(request, gen3d_result)
        return gen3d_result

    def mutex_for(self, printer_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._printer_locks.get(printer_id)
            if lock is None:
                lock = threading.Lock()
                self._printer_locks[printer_id] = lock
            return lock

    def mutex_for_run(self, run_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._run_locks.get(run_id)
            if lock is None:
                lock = threading.Lock()
                self._run_locks[run_id] = lock
            return lock

    def registered_tools(self) -> frozenset[str]:
        return self._registered_tools

    def _refuse(
        self,
        request: PollRequest,
        error: Err,
        token: CapabilityToken | None,
    ) -> PollResult:
        result = PollResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            printer_id=request.printer_id,
            tool=request.tool,
            result=error,
            token_id=None if token is None else token.token_id,
        )
        self._append_event(request, result)
        return result

    def _refuse_plan(
        self,
        request: PlanRequest,
        error: Err,
        token: CapabilityToken | None,
    ) -> PlanResult:
        result = PlanResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            tool=request.tool,
            result=error,
            token_id=None if token is None else token.token_id,
        )
        self._append_event(request, result)
        return result

    def _refuse_gen3d(
        self,
        request: Gen3DRequest,
        error: Err,
        token: CapabilityToken | None,
    ) -> Gen3DResult:
        result = Gen3DResult(
            run_id=request.run_id,
            agent_id=request.agent_id,
            node_id=request.node_id,
            tool=request.tool,
            result=error,
            token_id=None if token is None else token.token_id,
        )
        self._append_event(request, result)
        return result

    def _append_event(
        self,
        request: PollRequest | PlanRequest | Gen3DRequest,
        dispatch_result: PollResult | PlanResult | Gen3DResult,
    ) -> None:
        if self.ledger is None:
            return

        event = LedgerEvent(
            ts_utc=_iso_utc(_normalize_utc(None)),
            run_id=request.run_id,
            agent_id=request.agent_id,
            tool=request.tool,
            inputs_sha=stable_sha(_request_payload(request)),
            outputs_sha=stable_sha(_result_payload(dispatch_result.result)),
            verdict="pass" if isinstance(dispatch_result.result, Ok) else "fail",
            message=dispatch_result.result.message,
        )
        self.ledger.append(event)

    def _validate_dag_tools(self, dag: TaskDAG) -> Result[TaskDAG]:
        unregistered = sorted(
            {node.tool for node in dag.nodes if node.tool not in self._registered_tools}
        )
        if unregistered:
            return Err(
                "tool_unregistered",
                f"DAG contains unregistered tool(s): {', '.join(unregistered)}",
            )
        return Ok(dag, "DAG tools registered")

    def _sign(self, token: CapabilityToken) -> str:
        payload = {
            "agent_id": token.agent_id,
            "expires_at_utc": token.expires_at_utc,
            "issued_at_utc": token.issued_at_utc,
            "phase": token.phase,
            "scopes": sorted(token.scopes),
            "token_id": token.token_id,
            "tools": sorted(token.tools),
        }
        digest = hmac.new(
            self._signing_secret.encode("utf-8"),
            _canonical_json(payload).encode("utf-8"),
            hashlib.sha256,
        )
        return digest.hexdigest()


def stable_sha(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _request_payload(request: PollRequest | PlanRequest | Gen3DRequest) -> Mapping[str, object]:
    return asdict(request)


def _result_payload(result: Result[object]) -> Mapping[str, object]:
    if isinstance(result, Ok):
        value = result.value
        if is_dataclass(value):
            value_payload: object = asdict(value)
        else:
            value_payload = value
        return {"ok": True, "value": value_payload, "message": result.message}
    return {
        "ok": False,
        "code": result.code,
        "message": result.message,
        "recoverable": result.recoverable,
    }


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
