"""Offline provider probe gateway substrate for Phase 3.4-B."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Callable

from hermes3d.gateways.budget import BudgetCaps, check_budget, estimate_cost_usd, record_actual
from hermes3d.gateways.redaction import redact_text
from hermes3d.orchestration.ledger import LedgerEvent, OrchestrationLedger
from hermes3d.orchestration.types import (
    BudgetState,
    CapabilityToken,
    Err,
    Ok,
    ProviderConfig,
    ProviderProbeResult,
    Result,
)

PROBE_TOOL = "provider.probe"


@dataclass(frozen=True)
class ProbeOutcome:
    http_status: int
    latency_ms: int
    body: str


ProbeCaller = Callable[[ProviderConfig], ProbeOutcome]


class ProviderProbeGateway:
    """Single token-gated provider probe entry point."""

    def __init__(
        self,
        *,
        ledger: OrchestrationLedger,
        providers: dict[str, ProviderConfig],
        probe_freshness_minutes: int = 15,
        probe_budget_usd_per_day: Decimal = Decimal("0.10"),
        probe_rate_per_minute: int = 1,
        probe_caller: ProbeCaller | None = None,
        cost_per_probe_usd: Decimal = Decimal("0.001"),
    ) -> None:
        self.ledger = ledger
        self._providers = dict(providers)
        self._probe_freshness_minutes = probe_freshness_minutes
        self._probe_budget_usd_per_day = probe_budget_usd_per_day
        self._probe_rate_per_minute = probe_rate_per_minute
        self._probe_caller = probe_caller
        self._cost_per_probe_usd = cost_per_probe_usd
        self._consumed_tokens: set[str] = set()

    def probe(
        self,
        provider_id: str,
        *,
        token: CapabilityToken | None,
        budget: BudgetState,
        probe_caller: ProbeCaller | None = None,
        now_utc: datetime | None = None,
    ) -> Result[ProviderProbeResult]:
        validation = self._validate_token(token)
        if isinstance(validation, Err):
            return validation
        self._consumed_tokens.add(validation.value.token_id)

        if provider_id not in self._providers:
            return Err("provider_not_in_allowlist", provider_id)

        resolved_caller = probe_caller or self._probe_caller
        if resolved_caller is None:
            return Err("probe_caller_missing", "provider probe requires an injected caller")

        now = _normalize_utc(now_utc)
        if self._rate_cap_exceeded(provider_id, now_utc=now):
            return Err("rate_cap_exceeded", provider_id)

        estimated_usd = estimate_cost_usd(
            tokens_in=1,
            tokens_out=0,
            input_usd_per_token=self._cost_per_probe_usd,
            output_usd_per_token=Decimal("0"),
        )
        decision = check_budget(
            budget,
            caps=BudgetCaps(
                cost_cap_usd_per_run=self._probe_budget_usd_per_day,
                cost_cap_usd_per_day=self._probe_budget_usd_per_day,
            ),
            estimated_usd=estimated_usd,
            now_utc=now,
        )
        if not decision.allowed:
            self._append_budget_exceeded(
                token=validation.value,
                provider_id=provider_id,
                decision_cap=decision.cap,
                attempted_usd=decision.attempted_usd,
                now_utc=now,
            )
            return Err("probe_budget_exceeded", decision.cap)

        config = self._providers[provider_id]
        try:
            outcome = resolved_caller(config)
        except Exception as exc:  # pragma: no cover - defensive caller boundary
            return Err("probe_upstream_failure", redact_text(str(exc)))

        excerpt = redact_text(outcome.body)[:200]
        response_sha256 = sha256(outcome.body.encode("utf-8")).hexdigest()
        probed_at_utc = _iso_utc(now)
        result = ProviderProbeResult(
            provider_id=provider_id,
            http_status=outcome.http_status,
            latency_ms=outcome.latency_ms,
            redacted_excerpt=excerpt,
            response_sha256=response_sha256,
            probed_at_utc=probed_at_utc,
            success=200 <= outcome.http_status < 300,
        )
        self.ledger.append(
            LedgerEvent(
                ts_utc=probed_at_utc,
                run_id=_run_id(validation.value),
                agent_id=validation.value.agent_id,
                tool=PROBE_TOOL,
                inputs_sha=_stable_sha({"provider_id": provider_id}),
                outputs_sha=_stable_sha(
                    {"http_status": outcome.http_status, "sha": response_sha256}
                ),
                verdict="pass" if result.success else "fail",
                message=(
                    f"provider={provider_id} status={outcome.http_status} "
                    f"latency_ms={outcome.latency_ms} token_id={validation.value.token_id} "
                    f"excerpt={excerpt}"
                ),
            )
        )
        _updated_budget = record_actual(budget, actual_usd=self._cost_per_probe_usd)
        return Ok(result, "provider probe completed")

    def _validate_token(self, token: CapabilityToken | None) -> Result[CapabilityToken]:
        if token is None:
            return Err("no_token", "provider probe requires a capability token")
        if token.token_id in self._consumed_tokens:
            return Err("token_unknown", "provider probe token is unknown or already consumed")
        if token.phase > 3:
            return Err("phase_violation", "provider probe token exceeds Phase 3")
        if PROBE_TOOL not in token.tools:
            return Err("tool_not_authorized", "token is not authorized for provider.probe")
        now = datetime.now(UTC)
        expires = datetime.fromisoformat(token.expires_at_utc.replace("Z", "+00:00"))
        if now >= expires:
            return Err("token_expired", "token has expired")
        return Ok(token)

    def _rate_cap_exceeded(self, provider_id: str, *, now_utc: datetime) -> bool:
        window_start = now_utc - timedelta(seconds=60)
        count = 0
        for event in self.ledger.events():
            if event.tool != PROBE_TOOL or f"provider={provider_id}" not in event.message:
                continue
            event_ts = datetime.fromisoformat(event.ts_utc.replace("Z", "+00:00"))
            if event_ts >= window_start:
                count += 1
        return count >= self._probe_rate_per_minute

    def _append_budget_exceeded(
        self,
        *,
        token: CapabilityToken,
        provider_id: str,
        decision_cap: str,
        attempted_usd: Decimal,
        now_utc: datetime,
    ) -> None:
        self.ledger.append(
            LedgerEvent(
                ts_utc=_iso_utc(now_utc),
                run_id=_run_id(token),
                agent_id=token.agent_id,
                tool="budget.exceeded",
                inputs_sha=_stable_sha({"provider_id": provider_id, "tool": PROBE_TOOL}),
                outputs_sha=_stable_sha(
                    {
                        "attempted_usd": str(attempted_usd),
                        "cap": decision_cap,
                    }
                ),
                verdict="fail",
                message=(
                    f"tool={PROBE_TOOL} provider={provider_id} cap={decision_cap} "
                    f"token_id={token.token_id}"
                ),
            )
        )


def _run_id(token: CapabilityToken) -> str:
    scopes = sorted(token.scopes)
    return scopes[0] if scopes else token.token_id


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _stable_sha(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()
