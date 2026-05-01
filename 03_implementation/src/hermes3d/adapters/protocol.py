"""ToolAdapter Protocol per ADR-008.

Adapters satisfy this Protocol structurally (duck-typing); use
`isinstance(obj, ToolAdapter)` for runtime conformance checks (the Protocol is
`@runtime_checkable`).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import (
    Action,
    AdapterState,
    Confirmation,
    DetectResult,
    DryRunResult,
    ExecuteResult,
    HealthResult,
    LaunchResult,
    ValidateResult,
)


class NotImplementedYet(NotImplementedError):
    """Phase-1 skeleton method placeholder.

    Phase 3 implements read-only methods (validate/healthcheck/status/open_*).
    Phase 6 implements write methods (dry_run/execute) behind the
    dry_run_token + Confirmation envelope per ADR-008.
    """


@runtime_checkable
class ToolAdapter(Protocol):
    """Canonical 16-member adapter surface per ADR-008 §1."""

    # Identity (constants set at class level)
    key: str
    display_name: str
    category: str
    dangerous: bool

    # Lifecycle
    def version(self) -> str | None: ...
    def detect(self) -> DetectResult: ...
    def capabilities(self) -> frozenset[str]: ...
    def validate(self) -> ValidateResult: ...
    def healthcheck(self) -> HealthResult: ...
    def status(self) -> AdapterState: ...

    # Dock / undock / external (UI-bearing only)
    def open_docked(self) -> LaunchResult: ...
    def open_undocked(self) -> LaunchResult: ...
    def open_external(self) -> LaunchResult: ...
    def detach_ui(self) -> None: ...

    # Action plane
    def dry_run(self, action: Action) -> DryRunResult: ...
    def execute(self, action: Action, confirmation: Confirmation) -> ExecuteResult: ...
