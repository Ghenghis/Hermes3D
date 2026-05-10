"""W6-7 (2026-05-09): unit tests for the 60-app registry extension fields.

Schema:
- 5 new columns per `MEMORY.md` task brief: ``tested_versions``,
  ``license_spdx``, ``rollback_supported``, ``rollback_runbook_url``,
  ``proof_command``, ``update_lane``.
- 2 ancillary columns: ``last_proof_status``, ``last_proof_at``.

These tests cover:
1. Schema migration adds all 8 columns with correct defaults.
2. Backward-compat: rows that lack the new fields read as defaults.
3. ``apply_app_extensions`` is idempotent.
4. ``app_extension_summary`` reports a sane breakdown.
5. ``fully_populated_app_ids`` returns only ids with all 5 fields.
6. The 60-row integrity invariant (count and extension overlap).
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def isolated_db(monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    """Spin up a fresh DB in a temp dir, fully bootstrapped via init_db()."""
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "registry_test.db"

    import hermes3d.db.init as dbinit
    import hermes3d.db.load_modules as lm

    monkeypatch.setattr(dbinit, "DB_PATH", db_path)
    monkeypatch.setattr(lm, "DB_PATH", db_path)
    dbinit.init_db()
    lm.load_modules()
    conn = dbinit.connect()
    try:
        yield conn
    finally:
        conn.close()


def test_schema_has_all_w6_7_columns(isolated_db: sqlite3.Connection) -> None:
    cols = {row["name"] for row in isolated_db.execute("PRAGMA table_info(modules)").fetchall()}
    expected = {
        "tested_versions",
        "license_spdx",
        "rollback_supported",
        "rollback_runbook_url",
        "proof_command",
        "update_lane",
        "last_proof_status",
        "last_proof_at",
    }
    missing = expected - cols
    assert not missing, f"missing columns: {missing}"


def test_defaults_for_unseen_modules(isolated_db: sqlite3.Connection) -> None:
    # Insert a brand-new row that touches none of the new columns.
    isolated_db.execute(
        """
        INSERT INTO modules (id, display_name, section, priority)
        VALUES ('test_new_app', 'Test New App', 'utilities', 'reference')
        """
    )
    isolated_db.commit()
    record = isolated_db.execute("SELECT * FROM modules WHERE id = 'test_new_app'").fetchone()
    assert record["tested_versions"] == "[]"
    assert record["license_spdx"] is None
    assert record["rollback_supported"] == 0
    assert record["rollback_runbook_url"] is None
    assert record["proof_command"] is None
    assert record["update_lane"] == "frozen"
    assert record["last_proof_status"] is None
    assert record["last_proof_at"] is None


def test_seeded_extension_values_present(isolated_db: sqlite3.Connection) -> None:
    """A few well-known apps must have their seeded extension values."""
    record = isolated_db.execute(
        "SELECT license_spdx, update_lane, tested_versions, proof_command, rollback_supported "
        "FROM modules WHERE id = 'hermes_agent'"
    ).fetchone()
    assert record["license_spdx"] == "Apache-2.0"
    assert record["update_lane"] == "canary"
    assert "v0.13" in record["tested_versions"]
    assert "hermes_cli" in record["proof_command"]
    assert record["rollback_supported"] == 1

    record = isolated_db.execute(
        "SELECT license_spdx, update_lane FROM modules WHERE id = 'cadquery'"
    ).fetchone()
    assert record["license_spdx"] == "Apache-2.0"
    assert record["update_lane"] == "stable"

    record = isolated_db.execute(
        "SELECT license_spdx, update_lane FROM modules WHERE id = 'marlin'"
    ).fetchone()
    assert record["license_spdx"] == "GPL-3.0-only"
    assert record["update_lane"] == "frozen"


def test_total_module_count_is_60(isolated_db: sqlite3.Connection) -> None:
    count = isolated_db.execute("SELECT COUNT(*) AS c FROM modules").fetchone()["c"]
    assert count == 60, f"expected 60-app registry, got {count}"


def test_apply_app_extensions_idempotent(isolated_db: sqlite3.Connection) -> None:
    from hermes3d.db.app_registry_extensions import apply_app_extensions

    apply_app_extensions(isolated_db)
    isolated_db.commit()
    snapshot1 = dict(
        isolated_db.execute(
            "SELECT id, license_spdx, update_lane, tested_versions FROM modules WHERE id='cadquery'"
        ).fetchone()
    )
    apply_app_extensions(isolated_db)
    isolated_db.commit()
    snapshot2 = dict(
        isolated_db.execute(
            "SELECT id, license_spdx, update_lane, tested_versions FROM modules WHERE id='cadquery'"
        ).fetchone()
    )
    assert snapshot1 == snapshot2


def test_extensions_survive_load_modules_re_run(isolated_db: sqlite3.Connection) -> None:
    """Re-running load_modules must NOT clobber the W6-7 extension fields.

    This regresses a real bug: pre-W6-7 the loader used
    ``INSERT OR REPLACE`` which re-wrote the entire row, blowing away
    license_spdx etc. The fix uses ``ON CONFLICT DO UPDATE`` listing
    the source columns explicitly.
    """
    import hermes3d.db.load_modules as lm

    isolated_db.close()
    lm.load_modules()
    import hermes3d.db.init as dbinit

    conn = dbinit.connect()
    record = conn.execute(
        "SELECT license_spdx, update_lane, tested_versions FROM modules WHERE id='hermes_agent'"
    ).fetchone()
    conn.close()
    assert record["license_spdx"] == "Apache-2.0"
    assert record["update_lane"] == "canary"
    versions = json.loads(record["tested_versions"])
    assert "v0.13" in versions


def test_summary_reports_sane_counts() -> None:
    from hermes3d.db.app_registry_extensions import app_extension_summary

    summary = app_extension_summary()
    assert summary["total"] >= 60
    # We should have AT LEAST 50/60 with SPDX licensing assigned.
    assert summary["with_license_spdx"] >= 50
    assert (
        summary["stable_lane"] + summary["canary_lane"] + summary["frozen_lane"] == summary["total"]
    )


def test_fully_populated_app_ids_returns_strict_subset() -> None:
    from hermes3d.db.app_registry_extensions import (
        APP_EXTENSIONS,
        fully_populated_app_ids,
    )

    full_ids = fully_populated_app_ids()
    assert all(app_id in APP_EXTENSIONS for app_id in full_ids)
    # Every fully-populated app must have a non-empty proof_command and tested_versions.
    for app_id in full_ids:
        ext = APP_EXTENSIONS[app_id]
        assert ext.get("proof_command")
        assert ext.get("tested_versions")
        assert ext.get("license_spdx")


def test_update_lane_values_are_canonical() -> None:
    from hermes3d.db.app_registry_extensions import APP_EXTENSIONS

    valid = {"stable", "canary", "frozen"}
    for app_id, ext in APP_EXTENSIONS.items():
        lane = ext.get("update_lane")
        assert lane in valid, f"{app_id} has invalid update_lane={lane!r}"


def test_proof_command_round_trip(isolated_db: sqlite3.Connection) -> None:
    """A proof_command written via UPDATE must read back unchanged."""
    isolated_db.execute(
        "UPDATE modules SET proof_command = ? WHERE id = ?",
        ("python -c \"print('round-trip ok')\"", "trimesh"),
    )
    isolated_db.commit()
    record = isolated_db.execute(
        "SELECT proof_command FROM modules WHERE id = 'trimesh'"
    ).fetchone()
    assert record["proof_command"] == "python -c \"print('round-trip ok')\""


def test_rollback_supported_is_boolean_int() -> None:
    """SQLite stores booleans as integers; ensure 0/1 only."""
    from hermes3d.db.app_registry_extensions import APP_EXTENSIONS

    for app_id, ext in APP_EXTENSIONS.items():
        flag = ext.get("rollback_supported")
        assert flag in (True, False), f"{app_id} rollback_supported must be bool"


def test_unfilled_fields_documented() -> None:
    """The UNFILLED_FIELDS persistence list must reference real apps."""
    from hermes3d.db.app_registry_extensions import APP_EXTENSIONS, UNFILLED_FIELDS

    for app_id, field, attempt, next_path in UNFILLED_FIELDS:
        assert app_id in APP_EXTENSIONS, f"UNFILLED_FIELDS lists unknown app {app_id}"
        assert field in {
            "tested_versions",
            "license_spdx",
            "rollback_supported",
            "rollback_runbook_url",
            "proof_command",
            "update_lane",
        }
        assert attempt and next_path
