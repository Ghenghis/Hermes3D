"""Printer fleet definitions for the Hermes3D-OS Lite Contract Kit.

This package encodes the user's physical 3D-printer fleet as machine-readable
profiles, with firmware-stack support flags (Klipper / Marlin / Moonraker /
Fluidd / Mainsail) and bed kinematics so the Truth Gate can validate a model
against a *specific* target printer rather than a generic 220x220 default.

Public API:
    PrinterProfile, BedShape, FirmwareSupport, Kinematics
    FLEET                  -> tuple[PrinterProfile, ...]
    get_profile(id)        -> PrinterProfile
    list_ids()             -> list[str]
    fits_bed(spec, mesh)   -> tuple[bool, str]
"""
from __future__ import annotations

from .printer_profiles import (
    BedShape,
    FirmwareSupport,
    Kinematics,
    PrinterProfile,
    FLEET,
    get_profile,
    list_ids,
    fits_bed,
)

__all__ = [
    "BedShape",
    "FirmwareSupport",
    "Kinematics",
    "PrinterProfile",
    "FLEET",
    "get_profile",
    "list_ids",
    "fits_bed",
]
