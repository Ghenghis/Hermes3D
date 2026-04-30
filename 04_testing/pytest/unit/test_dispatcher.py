"""Tests for the agentic dispatcher and material catalog."""
from __future__ import annotations

import pytest

from hermes3d.core.agents.dispatcher import (
    DispatchRequest,
    DispatchScore,
    DispatchStrategy,
    dispatch,
)
from hermes3d.core.agents.materials import MATERIALS, get_material, list_materials


# -- materials ----------------------------------------------------------------

def test_materials_catalog_has_core_set():
    names = set(list_materials())
    for required in {"PLA", "PETG", "ABS", "ASA", "TPU", "PA", "PC"}:
        assert required in names


def test_get_material_case_insensitive():
    assert get_material("pla").material == "PLA"
    assert get_material("PETG").material == "PETG"
    assert get_material("petg").material == "PETG"


def test_get_material_unknown_raises():
    with pytest.raises(KeyError):
        get_material("UNOBTAINIUM")


def test_asa_requires_enclosure():
    asa = get_material("ASA")
    assert asa.requires_enclosure is True


def test_tpu_requires_direct_drive():
    tpu = get_material("TPU")
    assert tpu.requires_direct_drive is True


def test_pa_cf_requires_hardened_nozzle():
    m = get_material("PA-CF")
    assert m.requires_hardened_nozzle is True


def test_pc_temperature_requirements_above_typical_printer():
    pc = get_material("PC")
    assert pc.hotend_typical_c >= 280  # Filters out 250°C printers like SR


# -- dispatcher ---------------------------------------------------------------

def _small_pla_request(strategy=DispatchStrategy.AUTO) -> DispatchRequest:
    return DispatchRequest(
        mesh_extents_mm=(180, 100, 55),
        mesh_xy_radius_mm=90.0,
        material="PLA",
        strategy=strategy,
    )


def test_dispatch_returns_a_decision():
    d = dispatch(_small_pla_request())
    assert d.has_selection
    assert len(d.candidates) == 12  # full fleet evaluated


def test_dispatch_eliminates_for_asa_when_no_enclosure():
    """ASA requires enclosure — only T1, S1, D01 Pro qualify."""
    req = DispatchRequest(
        mesh_extents_mm=(80, 80, 40),
        mesh_xy_radius_mm=56.6,
        material="ASA",
    )
    d = dispatch(req)
    eligible = [c.printer_id for c in d.candidates if c.eligible]
    enclosed_set = {"flsun_t1_a", "flsun_t1_b", "flsun_s1", "tronxy_d01_pro"}
    assert set(eligible) <= enclosed_set, f"ASA-eligible: {eligible}"


def test_dispatch_eliminates_for_tpu_when_no_direct_drive():
    """TPU requires direct drive — bowden machines must be eliminated."""
    req = DispatchRequest(
        mesh_extents_mm=(60, 60, 30),
        mesh_xy_radius_mm=42.4,
        material="TPU",
    )
    d = dispatch(req)
    eligible = [c.printer_id for c in d.candidates if c.eligible]
    direct_drive_set = {
        "prusa_mk3s", "sovol_sv01",
        "flsun_t1_a", "flsun_t1_b", "flsun_s1", "flsun_v400",
    }
    assert set(eligible) <= direct_drive_set


def test_dispatch_largest_bed_picks_cr6_max():
    """A 380x380 part can only fit on Creality CR-6 Max (400x400 bed)."""
    req = DispatchRequest(
        mesh_extents_mm=(380, 380, 100),
        mesh_xy_radius_mm=270.0,
        material="PLA",
        strategy=DispatchStrategy.LARGEST_BED,
    )
    d = dispatch(req)
    assert d.selected_printer_id == "creality_cr6_max"


def test_dispatch_tall_part_with_delta_strategy_prefers_delta():
    """A 380mm tall part — only flsun_s1 (Z=430) and flsun_v400 (Z=410) fit
    among delta. Cartesian printers max at 400mm Z."""
    req = DispatchRequest(
        mesh_extents_mm=(80, 80, 380),
        mesh_xy_radius_mm=56.6,
        material="PLA",
        strategy=DispatchStrategy.DELTA_PREFER,
    )
    d = dispatch(req)
    assert d.selected_printer_id in {"flsun_s1", "flsun_v400"}


def test_dispatch_pc_only_eligible_on_high_hotend_enclosed():
    """PC requires hotend >= 295°C AND enclosure.
    T1 (300°C, enclosed), S1 (350°C, enclosed) both qualify.
    MK3S has 300°C hotend but is NOT enclosed -> blocked."""
    req = DispatchRequest(
        mesh_extents_mm=(50, 50, 50),
        mesh_xy_radius_mm=35.4,
        material="PC",
    )
    d = dispatch(req)
    eligible = {c.printer_id for c in d.candidates if c.eligible}
    assert eligible <= {"flsun_t1_a", "flsun_t1_b", "flsun_s1"}
    assert "prusa_mk3s" not in eligible  # not enclosed
    assert "creality_cr10s" not in eligible  # neither enclosed nor hot enough


def test_dispatch_records_blockers_for_ineligible():
    req = DispatchRequest(
        mesh_extents_mm=(50, 50, 50),
        mesh_xy_radius_mm=35.4,
        material="PC",
    )
    d = dispatch(req)
    blocked = [c for c in d.candidates if not c.eligible]
    assert blocked, "Expected some blocked candidates"
    for c in blocked:
        assert c.blockers, f"{c.printer_id} blocked but no blockers recorded"


def test_dispatch_excluded_printers_are_skipped():
    req = DispatchRequest(
        mesh_extents_mm=(180, 100, 55),
        mesh_xy_radius_mm=90.0,
        material="PLA",
        excluded_printers=("prusa_mk3s",),
    )
    d = dispatch(req)
    assert d.selected_printer_id != "prusa_mk3s"
    ids = {c.printer_id for c in d.candidates}
    assert "prusa_mk3s" not in ids


def test_dispatch_allowed_printers_restricts_pool():
    req = DispatchRequest(
        mesh_extents_mm=(100, 100, 40),
        mesh_xy_radius_mm=70.7,
        material="PLA",
        allowed_printers=("flsun_t1_a", "flsun_s1"),
    )
    d = dispatch(req)
    assert d.selected_printer_id in {"flsun_t1_a", "flsun_s1"}
    assert {c.printer_id for c in d.candidates} == {"flsun_t1_a", "flsun_s1"}


def test_dispatch_no_eligible_returns_none():
    """Part too big for everyone -> no selection."""
    req = DispatchRequest(
        mesh_extents_mm=(900, 900, 900),
        mesh_xy_radius_mm=636.4,
        material="PLA",
    )
    d = dispatch(req)
    assert d.selected_printer_id is None
    assert "No eligible printer" in d.rationale
    assert all(not c.eligible for c in d.candidates)


def test_dispatch_quality_strategy_prefers_low_accel():
    """The 'quality' strategy should rank cartesian (low accel, direct drive)
    above the speed-demon FLSUN S1 for normal-quality prints."""
    req = DispatchRequest(
        mesh_extents_mm=(100, 100, 40),
        mesh_xy_radius_mm=70.7,
        material="PLA",
        strategy=DispatchStrategy.QUALITY,
    )
    d = dispatch(req)
    # Top scorer should NOT be the FLSUN S1 (40k accel)
    top = d.candidates[0]
    assert top.printer_id != "flsun_s1"


def test_dispatch_least_busy_uses_live_state():
    """If two printers are eligible and one is reachable+ready, prefer it."""
    live = {
        "prusa_mk3s": {"reachable": True, "klippy_state": "ready"},
        "sovol_sv01": {"reachable": True, "klippy_state": "printing"},
    }
    req = DispatchRequest(
        mesh_extents_mm=(180, 100, 55),
        mesh_xy_radius_mm=90.0,
        material="PLA",
        strategy=DispatchStrategy.LEAST_BUSY,
        live_state=live,
        allowed_printers=("prusa_mk3s", "sovol_sv01"),
    )
    d = dispatch(req)
    assert d.selected_printer_id == "prusa_mk3s"


def test_dispatch_decision_candidates_sorted_by_score():
    d = dispatch(_small_pla_request())
    scores = [c.score for c in d.candidates]
    assert scores == sorted(scores, reverse=True)


def test_dispatch_decision_is_immutable():
    """DispatchDecision is frozen; mutating attempts must raise."""
    from dataclasses import FrozenInstanceError
    d = dispatch(_small_pla_request())
    with pytest.raises((AttributeError, FrozenInstanceError)):
        d.selected_printer_id = "x"  # type: ignore[misc]

