"""DTOs for the offline orchestration supervisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Generic, Literal, Mapping, TypeAlias, TypeVar

if TYPE_CHECKING:
    from .dag import TaskDAG

T = TypeVar("T")
Verdict: TypeAlias = Literal["pass", "fail", "skip"]
PlannerMode: TypeAlias = Literal["llm", "template"]


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    message: str = ""


@dataclass(frozen=True)
class Err:
    code: str
    message: str
    recoverable: bool = True


Result: TypeAlias = Ok[T] | Err


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    max_completion_tokens: int
    token_id: str


@dataclass(frozen=True)
class LLMResponse:
    redacted_text: str
    tokens_in: int
    tokens_out: int
    cost_usd_estimate: Decimal


@dataclass(frozen=True)
class BudgetState:
    spent_usd_run: Decimal
    spent_usd_day: Decimal
    day_started_utc: str


@dataclass(frozen=True)
class PrinterMirror:
    """Read-only printer mirror shape shared by offline poll DTOs."""

    printer_id: str
    name: str
    status: str
    state: str
    progress: float = 0.0
    temperatures: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityToken:
    token_id: str
    agent_id: str
    tools: frozenset[str]
    scopes: frozenset[str]
    issued_at_utc: str
    expires_at_utc: str
    phase: int
    signature: str


@dataclass(frozen=True)
class PollRequest:
    run_id: str
    agent_id: str
    printer_id: str
    tool: str
    inputs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PollResult:
    run_id: str
    agent_id: str
    printer_id: str
    tool: str
    result: Result[PrinterMirror]
    token_id: str | None = None


@dataclass(frozen=True)
class PlanRequest:
    run_id: str
    agent_id: str
    prompt: str
    tool: str = "planner.plan"
    inputs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PlanResult:
    run_id: str
    agent_id: str
    tool: str
    result: Result["TaskDAG"]
    token_id: str | None = None


@dataclass(frozen=True)
class Gen3DRequest:
    run_id: str
    agent_id: str
    node_id: str
    prompt: str
    seed: int
    tool: str = "gen3d.generate"
    inputs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulatedModelArtifact:
    artifact_id: str
    sha256: str
    prompt: str
    seed: int
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Gen3DResult:
    run_id: str
    agent_id: str
    node_id: str
    tool: str
    result: Result[SimulatedModelArtifact]
    token_id: str | None = None


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    probe_path: str
    completion_path: str
    api_key_env: str
    cost_cap_usd_per_run: Decimal | None = None
    cost_cap_usd_per_day: Decimal | None = None


@dataclass(frozen=True)
class ProviderProbeResult:
    provider_id: str
    http_status: int
    latency_ms: int
    redacted_excerpt: str
    response_sha256: str
    probed_at_utc: str
    success: bool
