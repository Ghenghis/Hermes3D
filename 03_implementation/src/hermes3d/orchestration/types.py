"""DTOs for the offline orchestration supervisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, Literal, Mapping, TypeAlias, TypeVar

if TYPE_CHECKING:
    from .dag import TaskDAG

T = TypeVar("T")
Verdict: TypeAlias = Literal["pass", "fail", "skip"]


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
