"""FLSUN printer and slicer source references.

This module keeps official FLSUN wiki links and local slicer profile paths in
one backend-owned place so the UI can show provenance instead of hard-coded
claims.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

FLSUN_SLICER_INSTALL = Path("C:/FlsunSlicer2.0")
FLSUN_SOURCE_PROFILE_INI = Path(
    "G:/Github/Hermes3D-OS/source-lab/sources/slicers/FLSUN-Slicer/resources/profiles/FLSun.ini"
)

FLSUN_PROFILE_REFS: dict[str, dict[str, Any]] = {
    "flsun_t1_a": {
        "official_wiki_url": "https://wiki.flsun3d.com/en/FlsunT1",
        "official_setup_topics": [
            "Power On Wizard",
            "First Print",
            "Network Connection Guidelines",
            "Orca import T1 configurationfile",
            "First Printing with Local Test Models",
        ],
        "installed_profiles": {
            "machine": "C:/FlsunSlicer2.0/resources/profiles/FLSun/machine/FLSun T1 0.4 nozzle.json",
            "process": "C:/FlsunSlicer2.0/resources/profiles/FLSun/process/0.20mm Standard @FLSun T1 Generic PLA.json",
            "filament": "C:/FlsunSlicer2.0/resources/profiles/FLSun/filament/FLSun T1 Generic PLA.json",
        },
    },
    "flsun_t1_b": {
        "official_wiki_url": "https://wiki.flsun3d.com/en/FlsunT1",
        "official_setup_topics": [
            "Power On Wizard",
            "First Print",
            "Network Connection Guidelines",
            "Orca import T1 configurationfile",
            "First Printing with Local Test Models",
        ],
        "installed_profiles": {
            "machine": "C:/FlsunSlicer2.0/resources/profiles/FLSun/machine/FLSun T1 0.4 nozzle.json",
            "process": "C:/FlsunSlicer2.0/resources/profiles/FLSun/process/0.20mm Standard @FLSun T1 Generic PLA.json",
            "filament": "C:/FlsunSlicer2.0/resources/profiles/FLSun/filament/FLSun T1 Generic PLA.json",
        },
    },
    "flsun_v400": {
        "official_wiki_url": "https://wiki.flsun3d.com/en/V400",
        "official_setup_topics": [
            "First print configuration",
            "Start printing from WEB page",
            "Automatic leveling",
            "Replace the printer configuration file",
            "Time-lapsephotography",
        ],
        "installed_profiles": {
            "machine": "C:/FlsunSlicer2.0/resources/profiles/FLSun/machine/FLSun V400 0.4 nozzle.json",
            "process": "C:/FlsunSlicer2.0/resources/profiles/FLSun/process/0.20mm Standard @FLSun V400.json",
            "filament": "C:/FlsunSlicer2.0/resources/profiles/FLSun/filament/FLSun V400 Generic PLA.json",
        },
    },
    "flsun_s1": {
        "official_wiki_url": "https://wiki.flsun3d.com/en/S1",
        "official_setup_topics": [
            "Power On Wizard",
            "First Print",
            "Network Connection Guidelines",
            "Orca import S1 configuration file",
            "The use and precautions of various calibration functions of S1",
        ],
        "installed_profiles": {
            "machine": "C:/FlsunSlicer2.0/resources/profiles/FLSun/machine/FLSun S1 0.4 nozzle.json",
            "process": "C:/FlsunSlicer2.0/resources/profiles/FLSun/process/0.20mm Standard @FLSun S1 Generic PLA.json",
            "filament": "C:/FlsunSlicer2.0/resources/profiles/FLSun/filament/FLSun S1 Generic PLA.json",
        },
        "safety": "S1 is offline/locked/no test/upload/move until the user clears the maintenance lane.",
    },
}


def printer_source_refs(printer_id: str) -> dict[str, Any]:
    refs = dict(FLSUN_PROFILE_REFS.get(printer_id, {}))
    if not refs:
        return {}
    installed_profiles = refs.get("installed_profiles", {})
    refs["source_profile_ini"] = str(FLSUN_SOURCE_PROFILE_INI)
    refs["flsun_slicer_install"] = str(FLSUN_SLICER_INSTALL)
    refs["profiles_detected"] = {
        name: Path(path).exists() for name, path in installed_profiles.items()
    }
    refs["source_profile_ini_detected"] = FLSUN_SOURCE_PROFILE_INI.exists()
    return refs


__all__ = [
    "FLSUN_PROFILE_REFS",
    "FLSUN_SLICER_INSTALL",
    "FLSUN_SOURCE_PROFILE_INI",
    "printer_source_refs",
]
