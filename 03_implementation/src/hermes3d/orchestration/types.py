"""DTOs for the offline orchestration supervisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Literal, Mapping, TypeAlias, TypeVar

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
