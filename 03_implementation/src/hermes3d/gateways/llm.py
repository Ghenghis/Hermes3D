"""Canonical offline LLM gateway for CP3.3-B."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Callable

import jsonschema
import yaml

from hermes3d.orchestration.ledger import LedgerEvent, OrchestrationLedger
from hermes3d.orchestration.types import (
    BudgetState,
    CapabilityToken,
    Err,
    LLMRequest,
    LLMResponse,
    Ok,
    Result,
)

from .budget import BudgetCaps, BudgetDecision, check_budget, estimate_cost_usd, record_actual
from .redaction import redact_text
from .sanitize import sanitize_prompt

LLM_TOOL = "llm.complete"
_IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = _IMPLEMENTATION_ROOT / "config" / "llm_policy.yaml"
DEFAULT_SCHEMA_PATH = _IMPLEMENTATION_ROOT / "config" / "llm_policy.schema.json"
LLMCaller = Callable[[LLMRequest], LLMResponse]


@dataclass(frozen=True)
class LLMPolicy:
    default_mode: str
    provider_allowlist: tuple[str, ...]
    cost_cap_usd_per_run: Decimal
    cost_cap_usd_per_day: Decimal
    timeout_seconds: int
    prompt_max_bytes: int
    retry_max: int
    rate_per_second: int
    input_usd_per_token: Decimal
    output_usd_per_token: Decimal
    max_completion_tokens: int = 1024
    fallback_mode: str = "template"

    @property
    def budget_caps(self) -> BudgetCaps:
        return BudgetCaps(
            cost_cap_usd_per_run=self.cost_cap_usd_per_run,
            cost_cap_usd_per_day=self.cost_cap_usd_per_day,
        )


class PolicyValidationError(ValueError):
    """Raised when the policy file does not validate against the committed schema."""


class LLMGateway:
    """Single injected-caller LLM gateway surface for Phase 3.3-B."""

    def __init__(
        self,
        *,
        ledger: OrchestrationLedger,
        policy: LLMPolicy | None = None,
        policy_path: Path | str = DEFAULT_POLICY_PATH,
        schema_path: Path | str = DEFAULT_SCHEMA_PATH,
        caller: LLMCaller | None = None,
    ) -> None:
        self.ledger = ledger
        self.policy = policy or load_policy(Path(policy_path), Path(schema_path))
        self._caller = caller
        self._consumed_tokens: set[str] = set()

    def complete(
        self,
        prompt: str,
        *,
        token: CapabilityToken,
        budget: BudgetState,
        caller: LLMCaller | None = None,
    ) -> Result[LLMResponse]:
        token_validation = self._validate_token(token)
        if isinstance(token_validation, Err):
            return token_validation

        sanitized = sanitize_prompt(prompt, prompt_max_bytes=self.policy.prompt_max_bytes)
        if isinstance(sanitized, Err):
            return sanitized

        request = LLMRequest(
            prompt=sanitized.value,
            max_completion_tokens=self.policy.max_completion_tokens,
            token_id=token.token_id,
        )
        tokens_in = _estimate_tokens(request.prompt)
        preflight_cost = estimate_cost_usd(
            tokens_in=tokens_in,
            tokens_out=request.max_completion_tokens,
            input_usd_per_token=self.policy.input_usd_per_token,
            output_usd_per_token=self.policy.output_usd_per_token,
        )
        budget_decision = check_budget(
            budget,
            caps=self.policy.budget_caps,
            estimated_usd=preflight_cost,
        )
        if not budget_decision.allowed:
            self._append_budget_exceeded(token=token, request=request, decision=budget_decision)
            return Err("budget_exceeded", f"{budget_decision.cap} budget cap exceeded")

        resolved_caller = caller or self._caller
        if resolved_caller is None:
            return Err("caller_missing", "LLM gateway requires an injected caller")

        response_result = self._call_with_retry(resolved_caller, request)
        if isinstance(response_result, Err):
            return response_result

        redacted = _redact_response(response_result.value)
        actual_cost = estimate_cost_usd(
            tokens_in=redacted.tokens_in,
            tokens_out=redacted.tokens_out,
            input_usd_per_token=self.policy.input_usd_per_token,
            output_usd_per_token=self.policy.output_usd_per_token,
        )
        actual_budget_decision = check_budget(
            budget,
            caps=self.policy.budget_caps,
            estimated_usd=actual_cost,
        )
        if not actual_budget_decision.allowed:
            self._append_budget_exceeded(
                token=token, request=request, decision=actual_budget_decision
            )
            return Err("budget_exceeded", f"{actual_budget_decision.cap} budget cap exceeded")

        redacted = LLMResponse(
            redacted_text=redacted.redacted_text,
            tokens_in=redacted.tokens_in,
            tokens_out=redacted.tokens_out,
            cost_usd_estimate=actual_cost,
        )
        record_actual(budget, actual_usd=actual_cost)
        self._append_success(token=token, request=request, response=redacted)
        self._consumed_tokens.add(token.token_id)
        return Ok(redacted, "LLM completion accepted")

    def _call_with_retry(self, caller: LLMCaller, request: LLMRequest) -> Result[LLMResponse]:
        last_message = "LLM caller failed"
        for _attempt in range(self.policy.retry_max + 1):
            try:
                response = caller(request)
            except TimeoutError as exc:
                last_message = redact_text(str(exc))
                continue
            except Exception as exc:  # pragma: no cover - defensive caller boundary
                last_message = redact_text(str(exc))
                continue
            if not isinstance(response, LLMResponse):
                return Err("invalid_llm_response", "caller must return LLMResponse")
            if not response.redacted_text.strip():
                return Err("invalid_llm_response", "LLM response text is empty")
            return Ok(response, "caller returned LLMResponse")
        return Err("upstream_failure", last_message)

    def _validate_token(self, token: CapabilityToken | None) -> Result[CapabilityToken]:
        if token is None:
            return Err("no_token", "LLM completion requires a capability token")
        if token.token_id in self._consumed_tokens:
            return Err("token_unknown", "LLM token is unknown or already consumed")
        if token.phase > 3:
            return Err("phase_violation", "LLM completion token exceeds Phase 3")
        if LLM_TOOL not in token.tools:
            return Err("tool_not_authorized", "token is not authorized for llm.complete")
        now = datetime.now(UTC)
        expires = datetime.fromisoformat(token.expires_at_utc.replace("Z", "+00:00"))
        if now >= expires:
            return Err("token_expired", "token has expired")
        return Ok(token)

    def _append_success(
        self,
        *,
        token: CapabilityToken,
        request: LLMRequest,
        response: LLMResponse,
    ) -> None:
        self.ledger.append(
            LedgerEvent(
                ts_utc=_iso_utc(datetime.now(UTC)),
                run_id=_run_id(token),
                agent_id=token.agent_id,
                tool=LLM_TOOL,
                inputs_sha=_stable_sha(_llm_request_payload(request)),
                outputs_sha=_stable_sha(response.redacted_text),
                verdict="pass",
                message=f"llm.complete accepted token_id={token.token_id}",
            )
        )

    def _append_budget_exceeded(
        self,
        *,
        token: CapabilityToken,
        request: LLMRequest,
        decision: BudgetDecision,
    ) -> None:
        self.ledger.append(
            LedgerEvent(
                ts_utc=_iso_utc(datetime.now(UTC)),
                run_id=_run_id(token),
                agent_id=token.agent_id,
                tool="budget.exceeded",
                inputs_sha=_stable_sha(_llm_request_payload(request)),
                outputs_sha=_stable_sha(
                    {
                        "cap": decision.cap,
                        "attempted_usd": str(decision.attempted_usd),
                    }
                ),
                verdict="fail",
                message=f"{decision.cap} budget cap exceeded token_id={token.token_id}",
            )
        )


def load_policy(
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
) -> LLMPolicy:
    policy_data = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    try:
        jsonschema.validate(policy_data, schema)
    except jsonschema.ValidationError as exc:
        raise PolicyValidationError(exc.message) from exc
    return LLMPolicy(
        default_mode=str(policy_data["default_mode"]),
        provider_allowlist=tuple(str(item) for item in policy_data["provider_allowlist"]),
        cost_cap_usd_per_run=Decimal(str(policy_data["cost_cap_usd_per_run"])),
        cost_cap_usd_per_day=Decimal(str(policy_data["cost_cap_usd_per_day"])),
        timeout_seconds=int(policy_data["timeout_seconds"]),
        prompt_max_bytes=int(policy_data["prompt_max_bytes"]),
        retry_max=int(policy_data["retry_max"]),
        rate_per_second=int(policy_data["rate_per_second"]),
        input_usd_per_token=Decimal(str(policy_data["input_usd_per_token"])),
        output_usd_per_token=Decimal(str(policy_data["output_usd_per_token"])),
        max_completion_tokens=int(policy_data.get("max_completion_tokens", 1024)),
        fallback_mode=str(policy_data.get("fallback_mode", "template")),
    )


def _redact_response(response: LLMResponse) -> LLMResponse:
    return LLMResponse(
        redacted_text=redact_text(response.redacted_text),
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_usd_estimate=response.cost_usd_estimate,
    )


def _llm_request_payload(request: LLMRequest) -> dict[str, object]:
    return asdict(request)


def _stable_sha(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _estimate_tokens(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 3) // 4)


def _run_id(token: CapabilityToken) -> str:
    scopes = sorted(token.scopes)
    return scopes[0] if scopes else token.token_id


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
