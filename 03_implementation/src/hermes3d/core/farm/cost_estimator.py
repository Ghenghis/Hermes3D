"""Cost estimator — filament + electricity per print job.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §21 (Cost Estimation)

Computes the rough monetary + energy cost of a print:

  filament_cost = filament_g / 1000 * price_per_kg_usd
  energy_kwh    = (printer.power_w_typical_print * duration_h) / 1000
  energy_cost   = energy_kwh * price_per_kwh_usd
  total_cost    = filament_cost + energy_cost

Default price points:
  PLA              $20/kg
  PETG             $22/kg
  ABS / ASA        $24/kg
  TPU              $30/kg
  PA / PA-CF       $50/kg
  PC               $45/kg
  CF-PLA           $35/kg
  PVA              $60/kg
  Electricity:     $0.16/kWh (Arizona average mid-2026)

Printer wattages from manufacturer specs and community measurements
(verified for FLSUN T1 ~250W typical, S1 ~350W typical, MK3S ~120W).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.printers import FLEET, get_profile, PrinterProfile


# Default electricity price (USD/kWh)
DEFAULT_PRICE_PER_KWH_USD = 0.16


# Default filament prices (USD/kg) at retail, mid-2026 averages
DEFAULT_FILAMENT_PRICES_USD_PER_KG: dict[str, float] = {
    "PLA": 20.0,
    "PLA+": 24.0,
    "PETG": 22.0,
    "ABS": 24.0,
    "ASA": 28.0,
    "TPU": 30.0,
    "PA": 50.0,
    "PA-CF": 60.0,
    "PC": 45.0,
    "CF-PLA": 35.0,
    "PVA": 60.0,
}


# Typical wattage during normal printing (watts), per profile_id.
# These dominate when bed heater isn't cycling at peak; peak draw is
# higher (300-500W on big-bed printers) but averages are what matter
# for energy cost.
_PRINTER_WATTAGE_TYPICAL: dict[str, float] = {
    "flsun_qqs_pro":     200.0,
    "flsun_t1_a":        250.0,
    "flsun_t1_b":        250.0,
    "flsun_super_racer": 200.0,
    "flsun_s1":          350.0,
    "flsun_v400":        320.0,
    "creality_cr10s":    220.0,  # 300x300 heated bed dominates
    "creality_cr6_max":  330.0,  # 400x400 heated bed
    "tronxy_d01_pro":    180.0,
    "tronxy_x5sa_pro":   260.0,
    "prusa_mk3s":        120.0,
    "sovol_sv01":        220.0,
}


@dataclass
class CostEstimate:
    """Itemized cost breakdown for a print."""

    printer_id: str
    material: str
    filament_g: float
    duration_hours: float

    filament_cost_usd: float
    energy_kwh: float
    energy_cost_usd: float
    total_cost_usd: float

    price_per_kg_usd: float
    price_per_kwh_usd: float
    typical_wattage: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def get_typical_wattage(profile_id: str) -> float:
    """Return typical-print wattage for a printer.

    Falls back to a conservative 250W for unknown printers.
    """
    return _PRINTER_WATTAGE_TYPICAL.get(profile_id, 250.0)


def estimate_cost(*, printer_id: str, material: str, filament_g: float,
                  duration_hours: float,
                  price_per_kg_usd: float | None = None,
                  price_per_kwh_usd: float | None = None,
                  ) -> CostEstimate:
    """Compute cost components with sensible defaults.

    The user can override either price (e.g. they paid $35/kg for
    Polymaker PolyTerra PLA, or their Arizona-rate-locked solar setup
    runs them at $0.10/kWh).
    """
    profile = get_profile(printer_id)
    notes: list[str] = []

    mat_key = material.upper()
    if price_per_kg_usd is None:
        price_per_kg_usd = DEFAULT_FILAMENT_PRICES_USD_PER_KG.get(
            mat_key, 25.0)
        if mat_key not in DEFAULT_FILAMENT_PRICES_USD_PER_KG:
            notes.append(
                f"unknown material '{material}' — using $25/kg fallback"
            )
    if price_per_kwh_usd is None:
        price_per_kwh_usd = DEFAULT_PRICE_PER_KWH_USD

    if filament_g < 0:
        raise ValueError("filament_g must be non-negative")
    if duration_hours < 0:
        raise ValueError("duration_hours must be non-negative")

    wattage = get_typical_wattage(printer_id)
    energy_kwh = (wattage * duration_hours) / 1000.0
    energy_cost = energy_kwh * price_per_kwh_usd
    filament_cost = (filament_g / 1000.0) * price_per_kg_usd
    total = filament_cost + energy_cost

    return CostEstimate(
        printer_id=printer_id,
        material=material,
        filament_g=float(filament_g),
        duration_hours=float(duration_hours),
        filament_cost_usd=round(filament_cost, 2),
        energy_kwh=round(energy_kwh, 3),
        energy_cost_usd=round(energy_cost, 2),
        total_cost_usd=round(total, 2),
        price_per_kg_usd=float(price_per_kg_usd),
        price_per_kwh_usd=float(price_per_kwh_usd),
        typical_wattage=float(wattage),
        notes=notes,
    )


def estimate_from_gcode_analysis(analysis, printer_id: str, material: str,
                                  **prices: float) -> CostEstimate:
    """Convenience: take a GcodeAnalysis instead of raw numbers.

    Falls back to zero filament/duration for missing fields rather than
    raising — the caller can inspect ``notes`` for warnings.
    """
    notes_extra: list[str] = []
    fil_g = analysis.filament_used_g or 0.0
    dur_h = analysis.estimated_print_time_h or 0.0
    if fil_g == 0.0:
        notes_extra.append("g-code did not report filament weight; cost may be 0")
    if dur_h == 0.0:
        notes_extra.append("g-code did not report time; energy cost will be 0")
    estimate = estimate_cost(
        printer_id=printer_id, material=material,
        filament_g=fil_g, duration_hours=dur_h, **prices,
    )
    estimate.notes.extend(notes_extra)
    return estimate


__all__ = [
    "CostEstimate",
    "DEFAULT_FILAMENT_PRICES_USD_PER_KG",
    "DEFAULT_PRICE_PER_KWH_USD",
    "estimate_cost",
    "estimate_from_gcode_analysis",
    "get_typical_wattage",
]
