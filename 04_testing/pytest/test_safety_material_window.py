"""Tests for hermes3d.core.safety.material_window."""

from __future__ import annotations

import pytest
from hermes3d.core.safety.material_window import (
    OVERRIDE_ENV_VAR,
    MaterialDB,
    MaterialWindow,
    build_violation_payload,
    check_material_window,
    load_material_db,
)


def test_default_db_has_required_materials() -> None:
    db = load_material_db()
    for mat in ("PLA", "PETG", "ABS", "TPU"):
        assert db.get(mat) is not None, mat


def test_pla_temps_within_window() -> None:
    db = load_material_db()
    result = check_material_window(material="PLA", nozzle_c=205.0, bed_c=60.0, db=db)
    assert result.passed
    assert "within" in result.reason


def test_pla_nozzle_too_hot_fails() -> None:
    db = load_material_db()
    result = check_material_window(material="PLA", nozzle_c=240.0, bed_c=60.0, db=db)
    assert not result.passed
    assert "nozzle 240" in result.reason


def test_petg_within_window() -> None:
    db = load_material_db()
    result = check_material_window(material="PETG", nozzle_c=235.0, bed_c=80.0, db=db)
    assert result.passed


def test_abs_bed_too_cold_fails() -> None:
    db = load_material_db()
    result = check_material_window(material="ABS", nozzle_c=240.0, bed_c=50.0, db=db)
    assert not result.passed
    assert "bed 50" in result.reason


def test_unknown_material_fails_without_override() -> None:
    db = load_material_db()
    result = check_material_window(material="Unobtanium", nozzle_c=200.0, bed_c=60.0, db=db)
    assert not result.passed
    assert "Unknown material" in result.reason


def test_override_env_var_allows_unknown_material() -> None:
    db = load_material_db()
    result = check_material_window(
        material="Unobtanium",
        nozzle_c=999.0,
        bed_c=999.0,
        db=db,
        env={OVERRIDE_ENV_VAR: "1"},
    )
    assert result.passed
    assert result.overridden


def test_override_env_var_allows_oob_known_material() -> None:
    db = load_material_db()
    result = check_material_window(
        material="PLA",
        nozzle_c=300.0,
        bed_c=60.0,
        db=db,
        env={OVERRIDE_ENV_VAR: "true"},
    )
    assert result.passed
    assert result.overridden
    assert "300" in result.reason


def test_override_env_var_disabled_does_not_pass_oob() -> None:
    db = load_material_db()
    result = check_material_window(
        material="PLA",
        nozzle_c=300.0,
        bed_c=60.0,
        db=db,
        env={OVERRIDE_ENV_VAR: "0"},
    )
    assert not result.passed


def test_case_insensitive_material_lookup() -> None:
    db = load_material_db()
    result = check_material_window(material="pla", nozzle_c=205.0, bed_c=60.0, db=db)
    assert result.passed


def test_violation_payload_shape() -> None:
    db = load_material_db()
    result = check_material_window(material="PLA", nozzle_c=300.0, bed_c=60.0, db=db)
    payload = build_violation_payload(job_id="j", printer_id="p", result=result)
    assert payload["kind"] == "safety.violation"
    assert payload["gate"] == "safety.material_temperature_window"
    assert payload["result"]["passed"] is False


def test_user_overrides_default_entries(tmp_path) -> None:
    # Build a tiny default DB shadowed by a user file that narrows PLA.
    default_path = tmp_path / "default.yaml"
    user_path = tmp_path / "user.yaml"
    default_path.write_text(
        "materials:\n"
        "  PLA:\n"
        "    nozzle_min_c: 180\n"
        "    nozzle_max_c: 220\n"
        "    bed_min_c: 0\n"
        "    bed_max_c: 65\n",
        encoding="utf-8",
    )
    user_path.write_text(
        "materials:\n  PLA:\n    nozzle_max_c: 200\n",  # override only this field
        encoding="utf-8",
    )
    db = load_material_db(default_path=default_path, user_path=user_path)
    pla = db.get("PLA")
    assert pla is not None
    assert pla.nozzle_max_c == 200.0
    assert pla.nozzle_min_c == 180.0  # inherited default


def test_material_window_contains() -> None:
    mw = MaterialWindow(name="X", nozzle_min_c=200, nozzle_max_c=220, bed_min_c=50, bed_max_c=70)
    assert mw.contains(nozzle_c=210, bed_c=60)
    assert not mw.contains(nozzle_c=199, bed_c=60)
    assert not mw.contains(nozzle_c=210, bed_c=80)


def test_malformed_entry_raises_clear_error(tmp_path) -> None:
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text(
        "materials:\n"
        "  Broken:\n"
        "    nozzle_min_c: 200\n"
        # missing nozzle_max_c, bed_min_c, bed_max_c
        "",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Broken"):
        load_material_db(default_path=bad_path, user_path=tmp_path / "nope.yaml")


def test_empty_db_get_returns_none() -> None:
    db = MaterialDB()
    assert db.get("PLA") is None
    assert db.names() == []
