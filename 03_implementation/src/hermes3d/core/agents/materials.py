"""Material profiles — filament-to-printer compatibility data.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §10 (Material-Aware Dispatch)

Encodes the temperature, enclosure, and extruder requirements for the
filaments the user prints with. The dispatcher uses this data to filter
out printers that can't handle a given material before scoring the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class MaterialProfile:
    """Requirements imposed on a printer by a filament type."""

    material: str
    hotend_min_c: int  # safe lower bound
    hotend_typical_c: int  # ~middle of recommended range
    hotend_max_c: int  # safe upper bound
    bed_min_c: int
    bed_typical_c: int
    bed_max_c: int

    requires_enclosure: bool = False
    requires_direct_drive: bool = False
    requires_hardened_nozzle: bool = False

    # Soft preferences (don't disqualify, but affect scoring)
    prefers_enclosure: bool = False
    prefers_high_flow: bool = False

    notes: str = ""


# -----------------------------------------------------------------------------
# Material catalog — values are cross-referenced from manufacturer datasheets
# (Prusa, Bambu, Polymaker, eSun) and the Klipper community wiki.
# -----------------------------------------------------------------------------

MATERIALS: Tuple[MaterialProfile, ...] = (
    MaterialProfile(
        material="PLA",
        hotend_min_c=190,
        hotend_typical_c=210,
        hotend_max_c=230,
        bed_min_c=0,
        bed_typical_c=60,
        bed_max_c=70,
        notes="Universal — any printer can run PLA.",
    ),
    MaterialProfile(
        material="PLA+",
        hotend_min_c=200,
        hotend_typical_c=215,
        hotend_max_c=235,
        bed_min_c=45,
        bed_typical_c=60,
        bed_max_c=70,
        notes="Toughened PLA — eSun, Polymaker variants.",
    ),
    MaterialProfile(
        material="PETG",
        hotend_min_c=225,
        hotend_typical_c=240,
        hotend_max_c=255,
        bed_min_c=70,
        bed_typical_c=80,
        bed_max_c=90,
        notes="Tough, slight stringing. Most printers handle it.",
    ),
    MaterialProfile(
        material="ABS",
        hotend_min_c=235,
        hotend_typical_c=250,
        hotend_max_c=270,
        bed_min_c=95,
        bed_typical_c=105,
        bed_max_c=110,
        prefers_enclosure=True,
        notes="Warps without enclosure. Strongly prefers enclosed printers "
        "(T1, S1, D01 Pro) but will run on open-frame with effort.",
    ),
    MaterialProfile(
        material="ASA",
        hotend_min_c=240,
        hotend_typical_c=255,
        hotend_max_c=270,
        bed_min_c=95,
        bed_typical_c=105,
        bed_max_c=115,
        requires_enclosure=True,
        notes="Worse than ABS for warping; enclosure required.",
    ),
    MaterialProfile(
        material="TPU",
        hotend_min_c=215,
        hotend_typical_c=230,
        hotend_max_c=250,
        bed_min_c=40,
        bed_typical_c=55,
        bed_max_c=70,
        requires_direct_drive=True,
        notes="Flexible; bowden tubes cause buckling. Direct-drive required.",
    ),
    MaterialProfile(
        material="PA",  # nylon
        hotend_min_c=240,
        hotend_typical_c=270,
        hotend_max_c=290,
        bed_min_c=80,
        bed_typical_c=95,
        bed_max_c=110,
        prefers_enclosure=True,
        notes="Hygroscopic — dry filament well. High hotend preferred.",
    ),
    MaterialProfile(
        material="PA-CF",
        hotend_min_c=250,
        hotend_typical_c=275,
        hotend_max_c=295,
        bed_min_c=80,
        bed_typical_c=100,
        bed_max_c=115,
        requires_hardened_nozzle=True,
        prefers_enclosure=True,
        notes="Carbon-fibre filled nylon. Abrasive — hardened nozzle required.",
    ),
    MaterialProfile(
        material="PC",
        hotend_min_c=275,
        hotend_typical_c=295,
        hotend_max_c=315,
        bed_min_c=100,
        bed_typical_c=110,
        bed_max_c=120,
        requires_enclosure=True,
        notes="Polycarbonate — needs very hot hotend + heated chamber.",
    ),
    MaterialProfile(
        material="CF-PLA",
        hotend_min_c=200,
        hotend_typical_c=220,
        hotend_max_c=240,
        bed_min_c=45,
        bed_typical_c=60,
        bed_max_c=70,
        requires_hardened_nozzle=True,
        notes="Carbon-fibre filled PLA. Abrasive — hardened nozzle required.",
    ),
    MaterialProfile(
        material="PVA",
        hotend_min_c=180,
        hotend_typical_c=200,
        hotend_max_c=220,
        bed_min_c=45,
        bed_typical_c=60,
        bed_max_c=70,
        notes="Water-soluble support. Sensitive to moisture.",
    ),
)


def list_materials() -> list[str]:
    """Names of all known materials in catalog order."""
    return [m.material for m in MATERIALS]


def get_material(name: str) -> MaterialProfile:
    """Look up a material by case-insensitive name; raises KeyError."""
    target = name.strip().upper().replace(" ", "")
    for m in MATERIALS:
        if m.material.upper().replace("-", "") == target.replace("-", ""):
            return m
    raise KeyError(f"Unknown material {name!r}. Known: {list_materials()}")


__all__ = [
    "MATERIALS",
    "MaterialProfile",
    "get_material",
    "list_materials",
]
