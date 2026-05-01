"""Offline-only orchestration supervisor skeleton."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping

from .ledger import LedgerEvent, OrchestrationLedger
from .types import CapabilityToken, Err, Ok, PollRequest, PollResult, PrinterMirror, Result

OfflinePollHandler = Callable[[PollRequest], PrinterMirror | Result[PrinterMirror]]


class OfflineSupervisor:
    """Capability-token supervisor for Phase 3.1 offline dispatch."""

    def __init__(
        self,
        *,
        ledger: OrchestrationLedger | None = None,
        current_phase: int = 3,
        signing_secret: str | None = None,
    ) -> None:
        self.ledger = ledger
        self.current_phase = current_phase
        self._signing_secret = signing_secret or "hermes3d-phase-3-1-offline"
        self._tokens: dict[str, CapabilityToken] = {}
        self._consumed_tokens: set[str] = set()
        self._printer_locks: dict[str, threading.Lock] = {}
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

    def validate_token(
        self,
        token: CapabilityToken | None,
        *,
        tool: str,
        now_utc: datetime | None = None,
    ) -> Result[CapabilityToken]:
        if token is None:
            return Err("no_token", "dispatch requires a capability token")

        with self._registry_lock:
            registered = self._tokens.get(token.token_id)
            consumed = token.token_id in self._consumed_tokens

        if registered is None or consumed:
            return Err("token_unknown", "token is unknown or already consumed")
        if registered != token or not hmac.compare_digest(token.signature, self._sign(token)):
            return Err("token_unknown", "token signature does not match registry")
        if token.phase > self.current_phase:
            return Err("phase_not_allowed", "token phase exceeds supervisor phase")
        if tool not in token.tools:
            return Err("tool_not_authorized", "token is not authorized for this tool")

        now = _normalize_utc(now_utc)
        expires = datetime.fromisoformat(token.expires_at_utc.replace("Z", "+00:00"))
        if now >= expires:
            return Err("token_expired", "token has expired")

        return Ok(token)

    def dispatch_poll(
        self,
        request: PollRequest,
        *,
        token: CapabilityToken | None = None,
        handler: OfflinePollHandler | None = None,
        now_utc: datetime | None = None,
    ) -> PollResult:
        validation = self.validate_token(token, tool=request.tool, now_utc=now_utc)
        if isinstance(validation, Err):
            return self._refuse(request, validation, token)

        self._consume(validation.value)
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

    def mutex_for(self, printer_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._printer_locks.get(printer_id)
            if lock is None:
                lock = threading.Lock()
                self._printer_locks[printer_id] = lock
            return lock

    def _consume(self, token: CapabilityToken) -> None:
        with self._registry_lock:
            self._consumed_tokens.add(token.token_id)

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

    def _append_event(self, request: PollRequest, poll_result: PollResult) -> None:
        if self.ledger is None:
            return

        event = LedgerEvent(
            ts_utc=_iso_utc(_normalize_utc(None)),
            run_id=request.run_id,
            agent_id=request.agent_id,
            tool=request.tool,
            inputs_sha=stable_sha(
                {
                    "inputs": request.inputs,
                    "printer_id": request.printer_id,
                    "tool": request.tool,
                }
            ),
            outputs_sha=stable_sha(_result_payload(poll_result.result)),
            verdict="pass" if isinstance(poll_result.result, Ok) else "fail",
            message=poll_result.result.message,
        )
        self.ledger.append(event)

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


def _result_payload(result: Result[PrinterMirror]) -> Mapping[str, object]:
    if isinstance(result, Ok):
        return {"ok": True, "value": asdict(result.value), "message": result.message}
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
