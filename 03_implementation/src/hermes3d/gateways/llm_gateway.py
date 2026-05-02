"""Offline-only LLM planner gateway for Phase 3.3-B.

This module contains no provider SDK imports and performs no network I/O. The
default completion provider is a deterministic local mock so CP3.3-B can prove
the budget/sanitize/redact/fallback surface without opening a live adapter.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Callable, Mapping

from hermes3d.orchestration.dag import (
    DEFAULT_FANOUT_CAP,
    MAX_DAG_DEPTH,
    TaskDAG,
    TaskEdge,
    TaskNode,
)
from hermes3d.orchestration.types import CapabilityToken, Err, Ok, Result

from .llm_budget import BudgetCaps, BudgetDecision, LLMBudgetTracker
from .llm_redactor import redact_text
from .llm_sanitizer import sanitize_prompt

LLM_TOOL = "llm.complete"
DEFAULT_PROVIDER = "openai-fixture"
WRITE_CLASS_TOOLS = frozenset(
    {
        "blender.execute",
        "gcode.send",
        "printer.move",
        "printer.print_start",
        "printer.write",
        "slicer.execute",
    }
)
_IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_SCHEMA_PATH = _IMPLEMENTATION_ROOT / "config" / "llm_policy.schema.json"
_ARCH_SCHEMA_PATH = _REPO_ROOT / "02_architecture" / "schemas" / "llm_policy.schema.json"
DEFAULT_SCHEMA_PATH = _ARCH_SCHEMA_PATH if _ARCH_SCHEMA_PATH.exists() else _CONFIG_SCHEMA_PATH
DEFAULT_POLICY_PATH = _IMPLEMENTATION_ROOT / "config" / "llm_policy.yaml"
CompletionProvider = Callable[[str, "LLMGatewayContext"], str]


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


@dataclass(frozen=True)
class LLMGatewayContext:
    run_id: str
    agent_id: str = "planner"
    provider: str = DEFAULT_PROVIDER
    token: CapabilityToken | None = None
    registered_tools: frozenset[str] = field(default_factory=lambda: frozenset({"gen3d.generate"}))
    now_utc: datetime | None = None
    mock_response: str | None = None


@dataclass(frozen=True)
class LLMGatewayResponse:
    redacted_text: str
    tokens_in: int
    tokens_out: int
    cost_usd_estimate: Decimal
    dag: TaskDAG


class PolicyValidationError(ValueError):
    """Raised when llm_policy.yaml does not match the committed schema."""


class LLMGateway:
    """Single offline LLM gateway entry point with deterministic mock completion."""

    def __init__(
        self,
        *,
        policy: LLMPolicy | None = None,
        policy_path: Path | str = DEFAULT_POLICY_PATH,
        schema_path: Path | str = DEFAULT_SCHEMA_PATH,
        budget: LLMBudgetTracker | None = None,
        completion_provider: CompletionProvider | None = None,
    ) -> None:
        self.policy = policy or load_policy(Path(policy_path), Path(schema_path))
        self.budget = budget or LLMBudgetTracker(self.policy.budget_caps)
        self._completion_provider = completion_provider or _deterministic_mock_completion
        self._last_call_by_token: dict[str, datetime] = {}

    def complete(
        self,
        prompt: str,
        context: LLMGatewayContext | Mapping[str, object],
    ) -> Result[LLMGatewayResponse]:
        ctx = _coerce_context(context)
        token_validation = self._validate_token(ctx)
        if isinstance(token_validation, Err):
            return token_validation
        if ctx.provider not in self.policy.provider_allowlist:
            return Err("host_not_allowed", f"LLM provider is not allowlisted: {ctx.provider}")

        rate_validation = self._validate_rate(ctx)
        if isinstance(rate_validation, Err):
            return rate_validation

        sanitized = sanitize_prompt(prompt, prompt_max_bytes=self.policy.prompt_max_bytes)
        tokens_in = _estimate_tokens(sanitized)
        preflight_cost = self._estimate_cost(
            tokens_in=tokens_in,
            tokens_out=self.policy.max_completion_tokens,
        )
        budget_validation = self.budget.would_exceed(
            run_id=ctx.run_id,
            estimated_usd=preflight_cost,
            now_utc=ctx.now_utc,
        )
        if not budget_validation.allowed:
            return _budget_error(budget_validation)

        raw_response: str | None = None
        last_error: Exception | None = None
        for _attempt in range(self.policy.retry_max + 1):
            started = time.monotonic()
            try:
                raw_response = ctx.mock_response or self._completion_provider(sanitized, ctx)
            except TimeoutError as exc:
                last_error = exc
                continue
            except Exception as exc:  # pragma: no cover - defensive mock boundary
                last_error = exc
                continue
            if time.monotonic() - started > self.policy.timeout_seconds:
                last_error = TimeoutError("LLM mock completion exceeded timeout")
                raw_response = None
                continue
            break

        if raw_response is None:
            message = "LLM mock completion failed"
            if last_error is not None:
                message = redact_text(str(last_error))
            return Err("upstream_failure", message)

        redacted_text = redact_text(raw_response)
        dag_result = _parse_validated_dag(
            redacted_text,
            run_id=ctx.run_id,
            registered_tools=ctx.registered_tools,
        )
        if isinstance(dag_result, Err):
            return dag_result

        tokens_out = _estimate_tokens(redacted_text)
        actual_cost = self._estimate_cost(tokens_in=tokens_in, tokens_out=tokens_out)
        actual_budget_validation = self.budget.would_exceed(
            run_id=ctx.run_id,
            estimated_usd=actual_cost,
            now_utc=ctx.now_utc,
        )
        if not actual_budget_validation.allowed:
            return _budget_error(actual_budget_validation)

        self.budget.consume(run_id=ctx.run_id, actual_usd=actual_cost, now_utc=ctx.now_utc)
        return Ok(
            LLMGatewayResponse(
                redacted_text=redacted_text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd_estimate=actual_cost,
                dag=dag_result.value,
            ),
            "LLM gateway produced validated DAG",
        )

    def _validate_token(self, context: LLMGatewayContext) -> Result[CapabilityToken]:
        token = context.token
        if token is None:
            return Err("no_token", "LLM completion requires a capability token")
        if token.phase > 3:
            return Err("phase_violation", "LLM completion token exceeds Phase 3")
        if LLM_TOOL not in token.tools:
            return Err("tool_not_authorized", "token is not authorized for llm.complete")
        now = (context.now_utc or datetime.now(UTC)).astimezone(UTC)
        expires = datetime.fromisoformat(token.expires_at_utc.replace("Z", "+00:00"))
        if now >= expires:
            return Err("token_expired", "token has expired")
        return Ok(token)

    def _validate_rate(self, context: LLMGatewayContext) -> Result[None]:
        token = context.token
        if token is None:
            return Ok(None)
        now = (context.now_utc or datetime.now(UTC)).astimezone(UTC)
        last_call = self._last_call_by_token.get(token.token_id)
        if last_call is not None:
            elapsed = (now - last_call).total_seconds()
            min_interval = 1 / self.policy.rate_per_second
            if elapsed < min_interval:
                return Err("rate_limited", "LLM gateway rate cap exceeded")
        self._last_call_by_token[token.token_id] = now
        return Ok(None)

    def _estimate_cost(self, *, tokens_in: int, tokens_out: int) -> Decimal:
        return (
            Decimal(tokens_in) * self.policy.input_usd_per_token
            + Decimal(tokens_out) * self.policy.output_usd_per_token
        )


def load_policy(
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
) -> LLMPolicy:
    policy_data = _parse_simple_yaml(Path(policy_path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    _validate_policy_data(policy_data, schema)
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


def _parse_validated_dag(
    redacted_text: str,
    *,
    run_id: str,
    registered_tools: frozenset[str],
) -> Result[TaskDAG]:
    try:
        payload = json.loads(redacted_text)
    except json.JSONDecodeError as exc:
        return Err("PlannerOutputRejected", f"invalid_json: {exc.msg}")
    if not isinstance(payload, dict):
        return Err("PlannerOutputRejected", "dag payload must be an object")

    nodes_payload = payload.get("nodes")
    if not isinstance(nodes_payload, list) or not nodes_payload:
        return Err("PlannerOutputRejected", "dag payload must include nodes")

    nodes: list[TaskNode] = []
    for item in nodes_payload:
        if not isinstance(item, dict):
            return Err("PlannerOutputRejected", "node payload must be an object")
        tool = str(item.get("tool", ""))
        if tool in WRITE_CLASS_TOOLS or _looks_write_class(tool):
            return Err("PlannerOutputRejected", f"write_tool: {tool}")
        if tool not in registered_tools:
            return Err("PlannerOutputRejected", f"unknown_tool: {tool}")
        nodes.append(
            TaskNode(
                node_id=str(item.get("node_id", "")),
                tool=tool,
                kind=str(item.get("kind", "")),
                inputs=_mapping_or_empty(item.get("inputs")),
                retry_budget=int(item.get("retry_budget", 0)),
                gate_set=frozenset(str(gate) for gate in item.get("gate_set", [])),
                depends_on=tuple(str(node_id) for node_id in item.get("depends_on", ())),
            )
        )

    edges = tuple(
        TaskEdge(
            from_node=str(item.get("from_node", "")),
            to_node=str(item.get("to_node", "")),
            condition=str(item.get("condition", "success")),
        )
        for item in payload.get("edges", [])
        if isinstance(item, dict)
    )
    metadata = _mapping_or_empty(payload.get("metadata"))
    metadata = {**metadata, "planner_mode": "llm"}
    dag = TaskDAG(
        dag_id=str(payload.get("dag_id", _stable_id({"nodes": nodes_payload, "run_id": run_id}))),
        run_id=str(payload.get("run_id", run_id)),
        nodes=tuple(nodes),
        edges=edges,
        max_depth=int(payload.get("max_depth", MAX_DAG_DEPTH)),
        max_fanout=int(payload.get("max_fanout", DEFAULT_FANOUT_CAP)),
        metadata=metadata,
    )
    validation = dag.validate()
    if isinstance(validation, Err):
        return Err("PlannerOutputRejected", validation.message)
    return Ok(dag, "validated LLM DAG")


def _deterministic_mock_completion(prompt: str, context: LLMGatewayContext) -> str:
    prompt_key = " ".join(prompt.strip().lower().split())
    digest = _stable_id({"prompt": prompt_key, "run_id": context.run_id})
    seed = int(digest[:8], 16)
    payload = {
        "dag_id": digest,
        "run_id": context.run_id,
        "nodes": [
            {
                "node_id": "gen3d-simulated",
                "tool": "gen3d.generate",
                "kind": "gen3d.fixture.llm_mock",
                "inputs": {"prompt": prompt, "seed": seed},
                "retry_budget": 0,
                "gate_set": ["phase3.3.llm-mock-only"],
                "depends_on": [],
            }
        ],
        "edges": [],
        "max_depth": MAX_DAG_DEPTH,
        "max_fanout": DEFAULT_FANOUT_CAP,
        "metadata": {"planner_mode": "llm", "provider": context.provider},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _validate_policy_data(policy_data: Mapping[str, object], schema: Mapping[str, object]) -> None:
    required = schema.get("required", [])
    missing = [key for key in required if key not in policy_data]
    if missing:
        raise PolicyValidationError(f"llm policy missing required key(s): {', '.join(missing)}")
    allowed = set(schema.get("properties", {}).keys())
    unknown = sorted(set(policy_data) - allowed)
    if unknown and schema.get("additionalProperties") is False:
        raise PolicyValidationError(f"llm policy has unknown key(s): {', '.join(unknown)}")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise PolicyValidationError("llm policy schema properties must be an object")
    for key, rules in properties.items():
        if key in policy_data and isinstance(rules, dict):
            _validate_policy_value(key, policy_data[key], rules)

    run_cap = Decimal(str(policy_data["cost_cap_usd_per_run"]))
    day_cap = Decimal(str(policy_data["cost_cap_usd_per_day"]))
    if day_cap < run_cap:
        raise PolicyValidationError("cost_cap_usd_per_day must be >= cost_cap_usd_per_run")


def _validate_policy_value(key: str, value: object, rules: Mapping[str, object]) -> None:
    expected_type = rules.get("type")
    if expected_type == "string" and not isinstance(value, str):
        raise PolicyValidationError(f"{key} must be a string")
    if expected_type == "integer" and not isinstance(value, int):
        raise PolicyValidationError(f"{key} must be an integer")
    if expected_type == "number" and not isinstance(value, int | float):
        raise PolicyValidationError(f"{key} must be a number")
    if expected_type == "array":
        if not isinstance(value, list):
            raise PolicyValidationError(f"{key} must be an array")
        if len(value) < int(rules.get("minItems", 0)):
            raise PolicyValidationError(f"{key} must not be empty")
        if rules.get("uniqueItems") and len(value) != len(set(str(item) for item in value)):
            raise PolicyValidationError(f"{key} must contain unique values")
    enum = rules.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise PolicyValidationError(
            f"{key} must be one of: {', '.join(str(item) for item in enum)}"
        )
    if isinstance(value, int | float):
        if "minimum" in rules and value < float(rules["minimum"]):
            raise PolicyValidationError(f"{key} is below minimum")
        if "exclusiveMinimum" in rules and value <= float(rules["exclusiveMinimum"]):
            raise PolicyValidationError(f"{key} must be greater than minimum")
        if "maximum" in rules and value > float(rules["maximum"]):
            raise PolicyValidationError(f"{key} exceeds maximum")


def _parse_simple_yaml(text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise PolicyValidationError(f"invalid policy line: {raw_line}")
        key, value = line.split(":", 1)
        data[key.strip()] = _parse_scalar(value.strip())
    return data


def _parse_scalar(value: str) -> object:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if value in {"template", "llm"}:
        return value
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _coerce_context(context: LLMGatewayContext | Mapping[str, object]) -> LLMGatewayContext:
    if isinstance(context, LLMGatewayContext):
        return context
    registered_tools = context.get("registered_tools", frozenset({"gen3d.generate"}))
    return LLMGatewayContext(
        run_id=str(context["run_id"]),
        agent_id=str(context.get("agent_id", "planner")),
        provider=str(context.get("provider", DEFAULT_PROVIDER)),
        token=context.get("token") if isinstance(context.get("token"), CapabilityToken) else None,
        registered_tools=frozenset(str(tool) for tool in registered_tools),
        now_utc=context.get("now_utc") if isinstance(context.get("now_utc"), datetime) else None,
        mock_response=context.get("mock_response")
        if isinstance(context.get("mock_response"), str)
        else None,
    )


def _budget_error(decision: BudgetDecision) -> Err:
    return Err(
        "budget_exceeded",
        f"{decision.cap} cap exceeded: attempted {decision.attempted_usd} USD",
    )


def _estimate_tokens(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 3) // 4)


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _looks_write_class(tool: str) -> bool:
    lowered = tool.lower()
    return any(
        marker in lowered for marker in (".write", ".move", ".execute", ".send", "print_start")
    )


def _stable_id(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()
