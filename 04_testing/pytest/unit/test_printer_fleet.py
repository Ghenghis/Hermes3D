"""Tests for hermes3d.core.printers — fleet metadata + Moonraker client."""
from __future__ import annotations

import math

import pytest

from hermes3d.core.printers import (
    FLEET,
    BedShape,
    FirmwareSupport,
    Kinematics,
    PrinterProfile,
    fits_bed,
    get_profile,
    list_ids,
)
from hermes3d.core.printers.moonraker_client import (
    MoonrakerClient,
    MoonrakerError,
    probe_fleet,
)


# ----------------------------------------------------------------------------
# Fleet structure
# ----------------------------------------------------------------------------

def test_fleet_has_exactly_twelve_printers():
    """Dave's actual fleet — must match exactly. If the fleet changes, this
    test must be updated *intentionally* alongside the data."""
    assert len(FLEET) == 12


def test_fleet_id_uniqueness():
    ids = [p.profile_id for p in FLEET]
    assert len(ids) == len(set(ids)), f"Duplicate ids: {ids}"


def test_fleet_kinematics_grouping():
    """6 deltas, 4 cartesian, 2 corexy."""
    counts: dict[Kinematics, int] = {}
    for p in FLEET:
        counts[p.kinematics] = counts.get(p.kinematics, 0) + 1
    assert counts[Kinematics.DELTA] == 6
    assert counts[Kinematics.CARTESIAN] == 4
    assert counts[Kinematics.COREXY] == 2


def test_every_printer_has_moonraker_default_url():
    for p in FLEET:
        assert p.moonraker_url_default.startswith("http"), p.profile_id


def test_every_printer_supports_moonraker_klipper_or_marlin():
    """Every printer must run at least one supported firmware stack."""
    for p in FLEET:
        assert p.firmware.klipper or p.firmware.marlin, p.profile_id
        assert p.firmware.moonraker, p.profile_id


def test_every_printer_supports_at_least_one_web_ui():
    for p in FLEET:
        assert p.firmware.fluidd or p.firmware.mainsail, p.profile_id


def test_get_profile_known():
    p = get_profile("flsun_s1")
    assert p.manufacturer == "FLSUN"
    assert p.bed.kind == "circular"
    assert p.bed.diameter_mm == 320.0
    assert p.z_height_mm == 430.0
    assert p.hotend_max_c == 350


def test_get_profile_unknown_raises():
    with pytest.raises(KeyError):
        get_profile("doesnotexist_xyz")


def test_list_ids_matches_fleet():
    assert list_ids() == [p.profile_id for p in FLEET]


# ----------------------------------------------------------------------------
# Bed-shape validation
# ----------------------------------------------------------------------------

def test_bed_shape_rejects_zero_dims():
    with pytest.raises(ValueError):
        BedShape(kind="rectangular", x_mm=0, y_mm=200)
    with pytest.raises(ValueError):
        BedShape(kind="circular", diameter_mm=0)


def test_bed_shape_rejects_unknown_kind():
    with pytest.raises(ValueError):
        BedShape(kind="hexagonal", x_mm=1, y_mm=1)


# ----------------------------------------------------------------------------
# Bed-fit logic
# ----------------------------------------------------------------------------

def test_fits_rectangular_pass():
    p = get_profile("prusa_mk3s")  # 250x210x210
    ok, _ = fits_bed(p, (180, 100, 55))
    assert ok


def test_fits_rectangular_fail_x():
    p = get_profile("prusa_mk3s")  # 250x210x210
    ok, msg = fits_bed(p, (300, 100, 55))
    assert not ok and "X extent" in msg


def test_fits_rectangular_fail_y():
    p = get_profile("prusa_mk3s")
    ok, msg = fits_bed(p, (200, 300, 55))
    assert not ok and "Y extent" in msg


def test_fits_rectangular_fail_z():
    p = get_profile("prusa_mk3s")
    ok, msg = fits_bed(p, (200, 100, 999))
    assert not ok and "Z extent" in msg


def test_fits_circular_uses_radius():
    """A 180x100 mesh has bbox-corner radius 103.4mm, but if its actual xy
    radius is e.g. 90mm (centered well), it should fit a Ø255 bed."""
    p = get_profile("flsun_qqs_pro")  # Ø255
    ok, _ = fits_bed(p, (180, 100, 55), mesh_xy_radius_mm=90.0)
    assert ok


def test_fits_circular_fail_radius():
    p = get_profile("flsun_qqs_pro")  # Ø255 -> radius 127.5
    ok, msg = fits_bed(p, (300, 300, 55), mesh_xy_radius_mm=200.0)
    assert not ok and "XY radius" in msg


def test_fits_circular_z_separate_from_xy():
    p = get_profile("flsun_qqs_pro")  # H 360
    ok, msg = fits_bed(p, (100, 100, 999), mesh_xy_radius_mm=70.0)
    assert not ok and "Z extent" in msg


def test_fits_circular_fallback_to_bbox_when_no_radius():
    """When the caller doesn't compute the true xy radius, fits_bed falls
    back to hypot(dx,dy)/2 which is a worst-case overestimate."""
    p = get_profile("flsun_t1_a")  # Ø260 -> radius 130
    # 200x200 corner-to-corner = sqrt(2)*200 = 282.84, /2 = 141.42 > 130 -> fail
    ok, _ = fits_bed(p, (200, 200, 55))
    assert not ok


# ----------------------------------------------------------------------------
# Moonraker client
# ----------------------------------------------------------------------------

def test_moonraker_client_construct_strips_trailing_slash():
    c = MoonrakerClient("http://example.local/")
    assert c.base_url == "http://example.local"


def test_moonraker_client_rejects_empty_url():
    with pytest.raises(ValueError):
        MoonrakerClient("")


def test_moonraker_client_unreachable_raises_moonraker_error():
    """Pointing at a guaranteed-unrouteable address must raise MoonrakerError
    (network error class), not a bare URLError."""
    c = MoonrakerClient("http://10.255.255.1", timeout_s=0.5)
    with pytest.raises(MoonrakerError) as exc_info:
        c.server_info()
    # Either a connection error OR a 403 from a captive proxy is acceptable;
    # the contract is that it's wrapped in MoonrakerError.
    assert exc_info.value.url is not None


def test_moonraker_upload_validates_path():
    c = MoonrakerClient("http://example.local")
    with pytest.raises(FileNotFoundError):
        c.upload_gcode("/no/such/file.gcode")


def test_moonraker_upload_rejects_non_gcode_extension(tmp_path):
    c = MoonrakerClient("http://example.local")
    f = tmp_path / "model.stl"
    f.write_bytes(b"solid")
    with pytest.raises(ValueError, match=".gcode"):
        c.upload_gcode(f)


def test_probe_fleet_returns_one_entry_per_printer():
    """probe_fleet must NEVER raise — it returns a structured list even when
    every printer is offline (which is the normal case in CI / sandbox)."""
    entries = probe_fleet(timeout_s=0.2)
    assert len(entries) == len(FLEET)
    expected_keys = {
        "profile_id", "manufacturer", "model", "moonraker_url",
        "reachable", "klippy_state", "moonraker_version", "error",
    }
    for e in entries:
        assert set(e.keys()) >= expected_keys
        # In sandbox/CI we expect zero printers reachable.
        assert e["reachable"] is False
        assert e["error"] is not None
