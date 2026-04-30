"""Parallel print planner.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §43 (Parallel Print Planning)

Given a *set* of meshes (parts of an assembly, or independent jobs) and
the current fleet state, plan a parallelized print across idle printers
to minimize total wall-clock time.

Strategy:
  - Each part is dispatched independently (so it gets the BEST printer
    for its material+size constraints)
  - When multiple parts could go to the same best printer, the next-best
    printer is used for parts 2..N
  - Optional: respect a maximum parallel-print count (e.g. user only
    wants 4 of 12 printers running at once for noise/heat reasons)

The planner does NOT actually start prints — it produces a Plan that
the user reviews and can apply. Each PlanItem links one part to one
printer with a justification.
"""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from hermes3d.core.agents.dispatcher import (
    DispatchRequest, DispatchStrategy, dispatch as run_dispatch,
)


log = logging.getLogger(__name__)


@dataclass
class PartRequest:
    """One part to print, with its constraints."""

    part_id: str                       # caller-chosen ID
    mesh_extents_mm: tuple[float, float, float]
    mesh_xy_radius_mm: float | None
    material: str
    quality_level: str = "normal"
    estimated_time_min: float = 0.0    # optional, helps total ETA estimate


@dataclass
class PlanItem:
    part_id: str
    selected_printer_id: str | None
    score: float = 0.0
    rationale: str = ""
    blockers: list[str] = field(default_factory=list)


@dataclass
class ParallelPlan:
    items: list[PlanItem] = field(default_factory=list)
    unscheduled: list[str] = field(default_factory=list)  # part_ids
    parallel_count: int = 0           # number of distinct printers used
    estimated_wallclock_min: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# =============================================================================


def plan_parallel_print(parts: Iterable[PartRequest], *,
                         max_parallel_printers: int | None = None,
                         excluded_printers: tuple[str, ...] = (),
                         strategy: DispatchStrategy = DispatchStrategy.AUTO,
                         ) -> ParallelPlan:
    """Pack parts onto distinct printers when possible.

    Each part runs through the regular dispatcher (with its own bed/
    material/quality constraints). Printers that have already been
    assigned for this plan are added to ``excluded_printers`` so the
    next part picks a different machine.
    """
    plan = ParallelPlan()
    busy_printers: set[str] = set(excluded_printers)
    parts_list = list(parts)
    times: list[float] = []

    for part in parts_list:
        # Already at parallel limit? — skip
        if (max_parallel_printers is not None and
                plan.parallel_count >= max_parallel_printers):
            plan.unscheduled.append(part.part_id)
            continue

        req = DispatchRequest(
            mesh_extents_mm=part.mesh_extents_mm,
            mesh_xy_radius_mm=part.mesh_xy_radius_mm,
            material=part.material,
            quality_level=part.quality_level,
            strategy=strategy,
            excluded_printers=tuple(busy_printers),
        )
        decision = run_dispatch(req)
        if decision.selected_printer_id is None:
            # Could not schedule this part on a fresh printer
            plan.items.append(PlanItem(
                part_id=part.part_id,
                selected_printer_id=None,
                rationale=decision.rationale,
                blockers=[
                    "no eligible idle printer (try shrinking exclusions)"],
            ))
            plan.unscheduled.append(part.part_id)
            continue

        # Find this printer's score
        chosen_score = 0.0
        for c in decision.candidates:
            if c.printer_id == decision.selected_printer_id:
                chosen_score = c.score
                break
        plan.items.append(PlanItem(
            part_id=part.part_id,
            selected_printer_id=decision.selected_printer_id,
            score=chosen_score,
            rationale=decision.rationale,
        ))
        busy_printers.add(decision.selected_printer_id)
        plan.parallel_count = len({i.selected_printer_id
                                    for i in plan.items
                                    if i.selected_printer_id})
        times.append(part.estimated_time_min)

    # Wall-clock estimate: max of the per-printer times (since they run
    # in parallel). If we have N printers and M parts each, the wall
    # clock is roughly max(time_per_printer_group). Simplification:
    # max(time per part) is a reasonable lower bound.
    if times:
        plan.estimated_wallclock_min = float(max(times))
    return plan


__all__ = [
    "ParallelPlan",
    "PartRequest",
    "PlanItem",
    "plan_parallel_print",
]
