"""Skeleton base class — Phase 1 detect-only adapters subclass this.

Subclasses MUST override `detect()`, `version()`, and `capabilities()`. All
other methods are inherited and raise `NotImplementedYet` with a message naming
the phase that will implement them. This keeps Phase 1 focused on detection
without accidentally shipping half-implemented read-only or write logic.

No method here invokes any external tool — Phase 1 is a foundation phase.
"""

from __future__ import annotations

from .protocol import NotImplementedYet
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


class SkeletonAdapter:
    """Subclass to add a new adapter. Override detect/version/capabilities."""

    # Identity — subclasses set these as class attributes.
    key: str = ""
    display_name: str = ""
    category: str = ""
    dangerous: bool = False

    # ------------------------------ helpers -------------------------------
    @staticmethod
    def _detect_result(
        found: bool,
        state: AdapterState,
        detail: str = "",
    ) -> DetectResult:
        return DetectResult(found=found, state=state, detail=detail)

    # -------- Phase 1 surface — subclasses MUST override these ------------
    def detect(self) -> DetectResult:
        raise NotImplementedYet(f"{self.__class__.__name__}.detect: subclass must override")

    def version(self) -> str | None:
        raise NotImplementedYet(f"{self.__class__.__name__}.version: subclass must override")

    def capabilities(self) -> frozenset[str]:
        raise NotImplementedYet(f"{self.__class__.__name__}.capabilities: subclass must override")

    # ------------- Phase 3 surface — read-only, ships in Phase 3 ----------
    def validate(self) -> ValidateResult:
        raise NotImplementedYet("validate — see Phase 3")

    def healthcheck(self) -> HealthResult:
        raise NotImplementedYet("healthcheck — see Phase 3")

    def status(self) -> AdapterState:
        raise NotImplementedYet("status — see Phase 3")

    def open_docked(self) -> LaunchResult:
        raise NotImplementedYet("open_docked — see Phase 3")

    def open_undocked(self) -> LaunchResult:
        raise NotImplementedYet("open_undocked — see Phase 3")

    def open_external(self) -> LaunchResult:
        raise NotImplementedYet("open_external — see Phase 3")

    def detach_ui(self) -> None:
        raise NotImplementedYet("detach_ui — see Phase 3")

    # ----------- Phase 6 surface — write actions, ships in Phase 6 --------
    def dry_run(self, action: Action) -> DryRunResult:
        raise NotImplementedYet("dry_run — see Phase 6")

    def execute(self, action: Action, confirmation: Confirmation) -> ExecuteResult:
        raise NotImplementedYet("execute — see Phase 6")
