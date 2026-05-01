"""Offline orchestration skeleton for Phase 3.1.

This package exposes DTOs plus local-only supervisor and ledger primitives.
It does not import adapter implementations or perform live integrations.
"""

from .dag import TaskDAG, TaskEdge, TaskNode, topological_walk, validate_dag
from .ledger import LedgerEvent, OrchestrationLedger
from .supervisor import OfflineSupervisor
from .types import (
    CapabilityToken,
    Err,
    Gen3DRequest,
    Gen3DResult,
    Ok,
    PlanRequest,
    PlanResult,
    PollRequest,
    PollResult,
    PrinterMirror,
    Result,
    SimulatedModelArtifact,
)

__all__ = [
    "CapabilityToken",
    "Err",
    "Gen3DRequest",
    "Gen3DResult",
    "LedgerEvent",
    "OfflineSupervisor",
    "Ok",
    "OrchestrationLedger",
    "PlanRequest",
    "PlanResult",
    "PollRequest",
    "PollResult",
    "PrinterMirror",
    "Result",
    "SimulatedModelArtifact",
    "TaskDAG",
    "TaskEdge",
    "TaskNode",
    "topological_walk",
    "validate_dag",
]
