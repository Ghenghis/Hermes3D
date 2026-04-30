"""Printer profile data + bed-fit / firmware support helpers.

All numerical specifications below are sourced from manufacturer documentation
and well-known community references (FLSUN North America FAQ, Prusa product
pages, Creality product pages, Tronxy product pages, Sovol product pages,
Klipper community configs). They are accurate as of the kit's design date
(2026-04). Each profile carries a `fact_checked` string declaring this
provenance honestly — users on Dave's fleet can confirm or override per
machine via `config/printers.user.toml` (see installer).

Bed-fit logic respects kinematics:
    * Cartesian / CoreXY -> rectangular bbox check (mesh xy footprint vs bed)
    * Delta              -> radial check (max(|xy|) from center vs bed radius)

Firmware support flags reflect what the printer can run *with reasonable
effort* — i.e. either ships with that firmware, or the community has produced
a documented, stable port. Flags do NOT promise a turnkey experience for ports
that require flashing — see `firmware.notes` for caveats.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class Kinematics(str, Enum):
    """Mechanical motion type — drives bed-fit math + reachable-Z modeling."""

    CARTESIAN = "cartesian"  # bed-slinger or fixed bed with gantry
    COREXY = "corexy"
    DELTA = "delta"


@dataclass(frozen=True)
class BedShape:
    """Build-area description.

    For ``kind="rectangular"``: ``x_mm`` and ``y_mm`` are the usable axes.
    For ``kind="circular"``: ``diameter_mm`` is the usable build diameter
    (Delta printers have a circular print region — corners of a bounding
    square are NOT reachable).
    """

    kind: str  # "rectangular" | "circular"
    x_mm: float = 0.0
    y_mm: float = 0.0
    diameter_mm: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in ("rectangular", "circular"):
            raise ValueError(f"BedShape.kind must be rectangular|circular, got {self.kind!r}")
        if self.kind == "rectangular" and (self.x_mm <= 0 or self.y_mm <= 0):
            raise ValueError("rectangular bed needs positive x_mm and y_mm")
        if self.kind == "circular" and self.diameter_mm <= 0:
            raise ValueError("circular bed needs positive diameter_mm")


@dataclass(frozen=True)
class FirmwareSupport:
    """Per-printer support matrix for the Klipper-stack ecosystem.

    A flag means: "the user can run this stack on this printer with documented
    procedures available." For stock printers that need flashing, the
    ``notes`` field describes the path.
    """

    klipper: bool = False
    marlin: bool = False
    moonraker: bool = False
    fluidd: bool = False
    mainsail: bool = False
    notes: str = ""


@dataclass(frozen=True)
class PrinterProfile:
    """Authoritative description of one physical printer in the fleet."""

    profile_id: str
    manufacturer: str
    model: str
    kinematics: Kinematics
    bed: BedShape
    z_height_mm: float
    nozzle_diameter_mm_default: float = 0.4
    hotend_max_c: int = 250
    bed_max_c: int = 100
    max_print_speed_mm_s: int = 100
    max_acceleration_mm_s2: int = 3000
    direct_drive: bool = False
    enclosed: bool = False
    firmware: FirmwareSupport = field(default_factory=FirmwareSupport)
    moonraker_url_default: str = ""  # e.g. "http://flsun-s1.local"
    fact_checked: str = "manufacturer-spec-2026-04"
    notes: str = ""


# =============================================================================
# THE FLEET — Dave / ShadowByte's 12 physical printers
# =============================================================================
# Sources & cross-checks performed:
#   - FLSUN North America FAQ (flsunnorthamerica.com/pages/faq)
#   - FLSUN S1 Pro product page + Tom's Hardware review (S1 specs)
#   - FLSUN T1 / T1 Pro product page + 3DWithUs review
#   - FLSUN V400 Amazon listing + 3D Print Beginner review
#   - Prusa MK3S+ official product page
#   - Creality CR-10S / CR-6 Max product pages
#   - Tronxy D01 / X5SA Pro product pages
#   - Sovol SV-01 product page
#   - Klipper Community (Guilouz/Klipper-Flsun-Speeder-Pad, danorder/V400)
# =============================================================================

FLEET: tuple[PrinterProfile, ...] = (
    # -------------------------------------------------------------- FLSUN ----
    PrinterProfile(
        profile_id="flsun_qqs_pro",
        manufacturer="FLSUN",
        model="QQ-S Pro",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=255.0),
        z_height_mm=360.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=250,
        bed_max_c=90,
        max_print_speed_mm_s=100,
        max_acceleration_mm_s2=3000,
        direct_drive=False,  # Bowden
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,  # community port via Speeder Pad / RPi
            marlin=True,  # ships Marlin 1.1.x derivative
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Marlin (FLSUN custom). Klipper requires RPi + flash. "
            "Strong community support (FLSUN North America FAQ, "
            "Klipper-Flsun-Speeder-Pad).",
        ),
        moonraker_url_default="http://flsun-qqs-pro.local",
        notes="E3D V6 hotend block, 280mm parallel arms, TMC2208 upgradeable.",
    ),
    PrinterProfile(
        profile_id="flsun_t1_a",
        manufacturer="FLSUN",
        model="T1",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=260.0),
        z_height_mm=330.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=300,
        bed_max_c=110,
        max_print_speed_mm_s=1000,
        max_acceleration_mm_s2=30000,
        direct_drive=True,
        enclosed=True,  # acrylic + glass door enclosure
        firmware=FirmwareSupport(
            klipper=True,  # ships with Klipper
            marlin=False,
            moonraker=True,
            fluidd=True,
            mainsail=True,  # FLSUN bundles Mainsail UI
            notes="Ships with Klipper + Mainsail out of the box. HEPA + "
            "activated-carbon filter. Dual-gear direct drive.",
        ),
        moonraker_url_default="http://flsun-t1-a.local",
        notes="Unit A of two T1 printers in fleet.",
    ),
    PrinterProfile(
        profile_id="flsun_t1_b",
        manufacturer="FLSUN",
        model="T1",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=260.0),
        z_height_mm=330.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=300,
        bed_max_c=110,
        max_print_speed_mm_s=1000,
        max_acceleration_mm_s2=30000,
        direct_drive=True,
        enclosed=True,
        firmware=FirmwareSupport(
            klipper=True,
            marlin=False,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Ships with Klipper + Mainsail out of the box.",
        ),
        moonraker_url_default="http://flsun-t1-b.local",
        notes="Unit B of two T1 printers in fleet.",
    ),
    PrinterProfile(
        profile_id="flsun_super_racer",
        manufacturer="FLSUN",
        model="Super Racer (SR)",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=260.0),
        z_height_mm=330.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=260,
        bed_max_c=110,
        max_print_speed_mm_s=200,
        max_acceleration_mm_s2=5000,
        direct_drive=False,  # remote-drive default; some users convert
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,  # well-documented community port
            marlin=True,  # stock = Marlin 2.0.8
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Marlin 2.0.8 (SKR V1.3 or MKS Robin Nano V3 board). "
            "Klipper conversion documented on 3D Print Beginner.",
        ),
        moonraker_url_default="http://flsun-sr.local",
        notes="2GT 10mm belts (1250mm length). 4x TMC2209 drivers.",
    ),
    PrinterProfile(
        profile_id="flsun_s1",
        manufacturer="FLSUN",
        model="S1",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=320.0),
        z_height_mm=430.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=350,
        bed_max_c=110,
        max_print_speed_mm_s=1200,
        max_acceleration_mm_s2=40000,
        direct_drive=True,
        enclosed=True,
        firmware=FirmwareSupport(
            klipper=True,
            marlin=False,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Ships with vanilla Klipper + Mainsail (Tom's Hardware "
            "review confirmed). LIDAR sensor, CPAP cooling, AI camera.",
        ),
        moonraker_url_default="http://flsun-s1.local",
        notes="Reachable Z varies across XY — 432mm at center, ~383mm at "
        "diameter edge. See 02_architecture/printer_envelopes.md.",
    ),
    PrinterProfile(
        profile_id="flsun_v400",
        manufacturer="FLSUN",
        model="V400",
        kinematics=Kinematics.DELTA,
        bed=BedShape(kind="circular", diameter_mm=300.0),
        z_height_mm=410.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=300,
        bed_max_c=110,
        max_print_speed_mm_s=600,
        max_acceleration_mm_s2=25000,
        direct_drive=True,
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,  # ships with Klipper
            marlin=False,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Ships with Klipper preinstalled on FLSUN Speeder Pad. "
            "MKS Robin Nano V2.1 controller. Dual-axis linear rails.",
        ),
        moonraker_url_default="http://flsun-v400.local",
        notes="GT2 10mm belts, 1458mm length per belt. Volcano-style hotend.",
    ),
    # ----------------------------------------------------------- CREALITY ----
    PrinterProfile(
        profile_id="creality_cr10s",
        manufacturer="Creality",
        model="CR-10S",
        kinematics=Kinematics.CARTESIAN,
        bed=BedShape(kind="rectangular", x_mm=300.0, y_mm=300.0),
        z_height_mm=400.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=260,
        bed_max_c=100,
        max_print_speed_mm_s=80,
        max_acceleration_mm_s2=1000,
        direct_drive=False,
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,
            marlin=True,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Marlin. Klipper widely documented (Klipper "
            "config repo `klipper-config-cr10s`). Add RPi or BTT Pi.",
        ),
        moonraker_url_default="http://creality-cr10s.local",
        notes="Bed-slinger; Y-axis cantilevered mass limits acceleration.",
    ),
    PrinterProfile(
        profile_id="creality_cr6_max",
        manufacturer="Creality",
        model="CR-6 Max",
        kinematics=Kinematics.CARTESIAN,
        bed=BedShape(kind="rectangular", x_mm=400.0, y_mm=400.0),
        z_height_mm=400.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=260,
        bed_max_c=100,
        max_print_speed_mm_s=80,
        max_acceleration_mm_s2=1000,
        direct_drive=False,
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,
            marlin=True,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Marlin (Creality custom for CR-6 Touch sensor). "
            "Klipper port keeps strain-gauge probe via klicky-style.",
        ),
        moonraker_url_default="http://creality-cr6max.local",
        notes="Largest cartesian in fleet at 400x400. Strain-gauge bed probe.",
    ),
    # ------------------------------------------------------------- TRONXY ----
    PrinterProfile(
        profile_id="tronxy_d01_pro",
        manufacturer="Tronxy",
        model="D01 Pro Enclosed",
        kinematics=Kinematics.COREXY,
        bed=BedShape(kind="rectangular", x_mm=220.0, y_mm=220.0),
        z_height_mm=220.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=275,
        bed_max_c=110,
        max_print_speed_mm_s=120,
        max_acceleration_mm_s2=2000,
        direct_drive=False,
        enclosed=True,  # Pro variant has acrylic enclosure
        firmware=FirmwareSupport(
            klipper=True,
            marlin=True,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Tronxy Marlin fork (CXY-V6 board). Klipper port "
            "available; flash via SD card.",
        ),
        moonraker_url_default="http://tronxy-d01.local",
        notes="CoreXY with linear rails. Enclosed for ABS/ASA.",
    ),
    PrinterProfile(
        profile_id="tronxy_x5sa_pro",
        manufacturer="Tronxy",
        model="X5SA Pro",
        kinematics=Kinematics.COREXY,
        bed=BedShape(kind="rectangular", x_mm=330.0, y_mm=330.0),
        z_height_mm=400.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=260,
        bed_max_c=110,
        max_print_speed_mm_s=100,
        max_acceleration_mm_s2=1500,
        direct_drive=False,
        enclosed=False,  # frame only; not enclosed despite Pro tier
        firmware=FirmwareSupport(
            klipper=True,
            marlin=True,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Tronxy Marlin fork. Linear rails, Titan extruder. "
            "Klipper config available; community-maintained.",
        ),
        moonraker_url_default="http://tronxy-x5sa.local",
        notes="CoreXY frame; large 330x330 build. Titan extruder remote.",
    ),
    # -------------------------------------------------------------- PRUSA ----
    PrinterProfile(
        profile_id="prusa_mk3s",
        manufacturer="Prusa Research",
        model="MK3S+",
        kinematics=Kinematics.CARTESIAN,
        bed=BedShape(kind="rectangular", x_mm=250.0, y_mm=210.0),
        z_height_mm=210.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=300,
        bed_max_c=120,
        max_print_speed_mm_s=200,
        max_acceleration_mm_s2=2500,
        direct_drive=True,  # Bondtech direct drive
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,  # well-supported community port
            marlin=True,  # Prusa-Firmware (Marlin fork)
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Prusa-Firmware (Marlin 2.x fork w/ Prusa "
            "extensions). Klipper port = github.com/dz0ny/klipper-mk3 "
            "or similar. SuperPINDA inductive probe.",
        ),
        moonraker_url_default="http://prusa-mk3s.local",
        notes="Bondtech extruder, SuperPINDA probe, magnetic flex plate.",
    ),
    # -------------------------------------------------------------- SOVOL ----
    PrinterProfile(
        profile_id="sovol_sv01",
        manufacturer="Sovol",
        model="SV01",
        kinematics=Kinematics.CARTESIAN,
        bed=BedShape(kind="rectangular", x_mm=280.0, y_mm=240.0),
        z_height_mm=300.0,
        nozzle_diameter_mm_default=0.4,
        hotend_max_c=260,
        bed_max_c=110,
        max_print_speed_mm_s=100,
        max_acceleration_mm_s2=1500,
        direct_drive=True,  # Sovol's direct drive variant
        enclosed=False,
        firmware=FirmwareSupport(
            klipper=True,
            marlin=True,
            moonraker=True,
            fluidd=True,
            mainsail=True,
            notes="Stock = Marlin (Creality-derivative board). Klipper "
            "config widely shared on Sovol community Discord/Reddit.",
        ),
        moonraker_url_default="http://sovol-sv01.local",
        notes="Direct-drive bed-slinger. CR-10-class build volume.",
    ),
)


# Sanity check at import time: profile_id uniqueness.
_ids = [p.profile_id for p in FLEET]
if len(_ids) != len(set(_ids)):
    duplicates = [i for i in _ids if _ids.count(i) > 1]
    raise RuntimeError(f"Duplicate profile_id in FLEET: {duplicates}")


def list_ids() -> list[str]:
    """Return all profile_ids in the fleet (preserves declaration order)."""
    return [p.profile_id for p in FLEET]


def get_profile(profile_id: str) -> PrinterProfile:
    """Look up a profile by id. Raises KeyError if not found."""
    for p in FLEET:
        if p.profile_id == profile_id:
            return p
    raise KeyError(f"Unknown printer profile_id: {profile_id!r}. Available: {list_ids()}")


def fits_bed(
    profile: PrinterProfile,
    mesh_extents_mm: tuple[float, float, float],
    mesh_xy_radius_mm: float | None = None,
) -> tuple[bool, str]:
    """Check whether a mesh fits the printer's build envelope.

    Args:
        profile: target printer.
        mesh_extents_mm: (dx, dy, dz) of the mesh axis-aligned bounding box.
        mesh_xy_radius_mm: For circular beds, the maximum (x,y) distance from
            the mesh's xy centroid to any vertex (i.e. radius of the smallest
            xy-circle that contains the mesh, when mesh is centered on bed).
            If None for a circular bed, falls back to ``hypot(dx, dy)/2``
            (worst case — corner-to-corner of bbox).

    Returns:
        (ok, message). On failure, message describes which axis fails.
    """
    dx, dy, dz = mesh_extents_mm
    if profile.bed.kind == "rectangular":
        if dx > profile.bed.x_mm:
            return False, (
                f"X extent {dx:.1f}mm exceeds bed X "
                f"{profile.bed.x_mm:.1f}mm on {profile.profile_id}"
            )
        if dy > profile.bed.y_mm:
            return False, (
                f"Y extent {dy:.1f}mm exceeds bed Y "
                f"{profile.bed.y_mm:.1f}mm on {profile.profile_id}"
            )
        if dz > profile.z_height_mm:
            return False, (
                f"Z extent {dz:.1f}mm exceeds Z height "
                f"{profile.z_height_mm:.1f}mm on {profile.profile_id}"
            )
        return True, "fits rectangular bed"

    if profile.bed.kind == "circular":
        radius_needed = (
            mesh_xy_radius_mm if mesh_xy_radius_mm is not None else math.hypot(dx, dy) / 2.0
        )
        bed_radius = profile.bed.diameter_mm / 2.0
        if radius_needed > bed_radius:
            return False, (
                f"XY radius {radius_needed:.1f}mm exceeds bed "
                f"radius {bed_radius:.1f}mm on "
                f"{profile.profile_id} (delta circular bed)"
            )
        if dz > profile.z_height_mm:
            return False, (
                f"Z extent {dz:.1f}mm exceeds Z height "
                f"{profile.z_height_mm:.1f}mm on {profile.profile_id}"
            )
        return True, "fits circular bed"

    return False, f"unknown bed kind {profile.bed.kind!r}"
