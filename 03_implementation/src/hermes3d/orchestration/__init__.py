"""Offline orchestration skeleton for Phase 3.1.

This package exposes DTOs plus local-only supervisor and ledger primitives.
It does not import adapter implementations or perform live integrations.
"""

from .ledger import LedgerEvent, OrchestrationLedger
from .supervisor import OfflineSupervisor
from .types import (
    CapabilityToken,
    Err,
    Ok,
    PollRequest,
    PollResult,
    PrinterMirror,
    Result,
)

__all__ = [
    "CapabilityToken",
    "Err",
    "LedgerEvent",
    "OfflineSupervisor",
    "Ok",
    "OrchestrationLedger",
    "PollRequest",
    "PollResult",
    "PrinterMirror",
    "Result",
]
