"""Printer equivalence groups.

Status: runnable
Contract: 00-CONTRACT/MASTER_CONTRACT.md §22 (Equivalence Pools)

The user has two FLSUN T1 units (`flsun_t1_a` and `flsun_t1_b`). For
dispatch purposes they are interchangeable — same firmware, same nozzle,
same kinematics. This module groups them into a logical "pool" so the
dispatcher can:

  - treat the pool as a single capability (e.g. "any T1")
  - select the least-busy member of the pool
  - rotate evenly across members for wear-leveling

Equivalence groups are defined declaratively (no LLM judgement needed).
The user can extend the catalog by editing config/equivalence_groups.toml.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Iterable

from hermes3d.core.printers import FLEET, PrinterProfile


@dataclass(frozen=True)
class EquivalenceGroup:
    """A set of printers treated as interchangeable."""

    group_id: str
    members: tuple[str, ...]      # profile_ids
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# Built-in groups derived from the fleet. New groups can be added by the
# user in config/equivalence_groups.toml; runtime callers should extend
# DEFAULT_GROUPS via load_user_groups() below.
DEFAULT_GROUPS: tuple[EquivalenceGroup, ...] = (
    EquivalenceGroup(
        group_id="flsun_t1_pool",
        members=("flsun_t1_a", "flsun_t1_b"),
        description="Two FLSUN T1 units, identical firmware/nozzle/bed.",
    ),
)


def list_groups(extra: Iterable[EquivalenceGroup] = ()) -> list[EquivalenceGroup]:
    return list(DEFAULT_GROUPS) + list(extra)


def find_group_for(printer_id: str,
                   groups: Iterable[EquivalenceGroup] = DEFAULT_GROUPS,
                   ) -> EquivalenceGroup | None:
    for g in groups:
        if printer_id in g.members:
            return g
    return None


def least_busy_member(group: EquivalenceGroup,
                       live_state: dict[str, dict[str, Any]],
                       ) -> str:
    """Pick the least-busy member of a group given Moonraker live state.

    Order of preference:
      1. reachable + klippy ready
      2. reachable but unknown state
      3. reachable but printing
      4. unreachable

    Ties broken by lexical printer_id (deterministic).
    """
    if not group.members:
        raise ValueError("empty group")

    def rank(pid: str) -> tuple[int, str]:
        st = live_state.get(pid, {})
        if not st.get("reachable", False):
            return (3, pid)
        ks = st.get("klippy_state", "")
        if ks == "ready":
            return (0, pid)
        if ks in ("printing", "paused"):
            return (2, pid)
        return (1, pid)

    return min(group.members, key=rank)


def expand_pool_request(printer_id: str,
                         live_state: dict[str, dict[str, Any]] | None = None,
                         groups: Iterable[EquivalenceGroup] = DEFAULT_GROUPS,
                         ) -> str:
    """If ``printer_id`` names a group, resolve to a concrete printer.

    If ``printer_id`` names a real printer, return it unchanged.
    """
    if live_state is None:
        live_state = {}
    # Try as a group_id first
    for g in groups:
        if g.group_id == printer_id:
            return least_busy_member(g, live_state)
    # Fall through: assume it's already a real printer_id
    return printer_id


__all__ = [
    "DEFAULT_GROUPS",
    "EquivalenceGroup",
    "expand_pool_request",
    "find_group_for",
    "least_busy_member",
    "list_groups",
]
