"""Adapter-system types per ADR-008.

All dataclasses are frozen; immutability is part of the proof model. The enum
values use string literals so they round-trip cleanly through YAML/JSON without
needing custom encoders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Mapping


class AdapterState(str, Enum):
    """8 lifecycle states per ADR-008 §2."""

    UNINSTALLED = "uninstalled"
    DETECTED = "detected"
    CONFIGURED = "configured"
    READY = "ready"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"


class CapabilityFlag(str, Enum):
    """Closed capability vocabulary per ADR-008 §4."""

    CLI = "cli"
    GUI = "gui"
    HEADLESS_SMOKE = "headless_smoke"
    USB = "usb"
    WEBSOCKET = "websocket"
    REST_API = "rest_api"
    MCP = "mcp"
    DOCK_IFRAME = "dock_iframe"
    STREAMING_LOGS = "streaming_logs"
    DRY_RUN_SUPPORTED = "dry_run_supported"
    E_STOP = "e_stop"
    READ_ONLY = "read_only"


DockMode = Literal["docked", "undocked", "external"]
Severity = Literal["info", "warn", "error", "fatal"]


@dataclass(frozen=True)
class ProofRef:
    """Provenance metadata embedded in every AdapterResult."""

    timestamp_utc: str
    branch: str
    commit: str


@dataclass(frozen=True)
class LogEntry:
    """Structured log entry — adapters never emit freeform strings."""

    ts_utc: str
    severity: Severity
    source: str
    code: str | None
    msg: str
    redactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class AdapterResult:
    """Canonical envelope for adapter method returns.

    Phase 1 fields ensure error reporting is structured (error_code,
    severity, recoverable, user_action_required) so the proof bundle and
    the UI can surface actionable failure data instead of stack traces.
    """

    ok: bool
    adapter: str
    mode: str
    artifacts: tuple[ArtifactRef, ...]
    logs: tuple[LogEntry, ...]
    proof: ProofRef
    error_code: str | None = None
    severity: Severity | None = None
    recoverable: bool = True
    user_action_required: str | None = None
    dry_run_token: str | None = None  # set on ExecuteResult after token consumption


@dataclass(frozen=True)
class DetectResult:
    found: bool
    state: AdapterState
    detail: str = ""


@dataclass(frozen=True)
class ValidateResult:
    ok: bool
    state: AdapterState
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    state: AdapterState
    latency_ms: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class LaunchResult:
    ok: bool
    mode: DockMode
    pid: int | None = None
    detail: str = ""


@dataclass(frozen=True)
class Action:
    """Generic action sent to dry_run() / execute()."""

    kind: str
    payload: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DryRunResult:
    ok: bool
    dry_run_token: str
    summary: str
    detail: str = ""


@dataclass(frozen=True)
class ExecuteResult:
    ok: bool
    artifacts: tuple[ArtifactRef, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class Confirmation:
    """Required for execute() of any dangerous=True adapter (ADR-008 §5)."""

    user: str
    ts_utc: str
    printer_id: str | None
    reason_text: str
    dry_run_token: str
    signed_token: str
    policy_version: str
