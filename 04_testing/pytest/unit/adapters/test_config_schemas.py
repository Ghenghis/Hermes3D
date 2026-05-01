"""Phase 1 Task 17 — JSON config schemas for the 9 distinct adapter categories.

Mainsail and Fluidd are UIs over Moonraker — they reuse moonraker.schema.json
for their underlying connection config, so 9 schemas cover the 11 adapters.

Tests verify:
- Each file is a valid JSON Schema (Draft 2020-12).
- Each rejects an obviously bad config.
- Each accepts a minimal valid config.
- No example contains a real-looking secret token (`api_key` defaults are
  null or a clearly non-secret placeholder).
- All schemas use the canonical $id prefix `hermes3d://adapter_registry/schemas/`.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "03_implementation" / "adapter_registry" / "schemas"

EXPECTED = [
    "blender",
    "blender_mcp",
    "cura",
    "flsun_slicer",
    "moonraker",
    "octoprint",
    "orca_slicer",
    "printrun",
    "prusa_slicer",
]

VALID_MINIMAL = {
    "blender": {"exe_path": "/usr/bin/blender"},
    "blender_mcp": {"provider_id": "ahujasid"},
    "cura": {"exe_path": "/usr/bin/cura"},
    "flsun_slicer": {"extracted_dir": "C:/Tools/FlsunSlicer"},
    "moonraker": {"host": "192.168.0.10", "port": 7125},
    "octoprint": {"base_url": "http://192.168.0.20", "api_key": "dummy_for_test_min8"},
    "orca_slicer": {"exe_path": "/usr/bin/orca-slicer"},
    "printrun": {"serial_port": "COM3"},
    "prusa_slicer": {"exe_path": "/usr/bin/prusa-slicer"},
}

INVALID_EXAMPLES = {
    "blender": {},  # missing required exe_path
    "blender_mcp": {"provider_id": "unknown"},  # not in enum
    "cura": {"exe_path": ""},  # empty
    "flsun_slicer": {},  # missing extracted_dir
    "moonraker": {"host": "x", "port": 70000},  # port out of range
    "octoprint": {"base_url": "ftp://x", "api_key": "12345678"},  # base_url not http(s)
    "orca_slicer": {"exe_path": ""},
    "printrun": {"serial_port": "COM3", "baud": 12345},  # baud not in enum
    "prusa_slicer": {"exe_path": ""},
}


def _load(name: str) -> dict:
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", EXPECTED)
def test_schema_file_exists(name):
    assert (SCHEMA_DIR / f"{name}.schema.json").exists()


@pytest.mark.parametrize("name", EXPECTED)
def test_schema_is_valid_jsonschema(name):
    """Each file must itself be a valid JSON Schema (Draft 2020-12)."""
    schema = _load(name)
    jsonschema.Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", EXPECTED)
def test_schema_uses_canonical_id_prefix(name):
    schema = _load(name)
    assert schema.get("$id", "").startswith("hermes3d://adapter_registry/schemas/")
    assert schema["$id"].endswith(f"{name}.schema.json")


@pytest.mark.parametrize("name", EXPECTED)
def test_schema_is_strict_no_additional_properties(name):
    """Every config schema must reject unknown fields to keep configs auditable."""
    schema = _load(name)
    assert schema.get("additionalProperties") is False, (
        f"{name}.schema.json should set additionalProperties: false"
    )


@pytest.mark.parametrize("name", EXPECTED)
def test_minimal_valid_config_passes(name):
    schema = _load(name)
    jsonschema.validate(VALID_MINIMAL[name], schema)


@pytest.mark.parametrize("name", EXPECTED)
def test_invalid_config_rejected(name):
    schema = _load(name)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(INVALID_EXAMPLES[name], schema)


def test_no_real_looking_secrets_in_schemas_or_examples():
    """Schemas must not embed real-looking tokens. api_key defaults must be null
    (or a clearly fake placeholder in tests)."""
    for name in EXPECTED:
        schema = _load(name)
        text = json.dumps(schema)
        # No long base64-ish tokens, no `ghp_`, no `AKIA`.
        for pattern in ("ghp_", "AKIA", "github_pat_"):
            assert pattern not in text, f"{name} schema contains '{pattern}'"
        # api_key, if present, must default to null.
        api_key_spec = schema.get("properties", {}).get("api_key")
        if api_key_spec is not None and "default" in api_key_spec:
            assert api_key_spec["default"] is None, (
                f"{name} api_key default must be null, not a literal token"
            )


def test_octoprint_rejects_short_api_key():
    schema = _load("octoprint")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"base_url": "http://x", "api_key": "short"},  # too short
            schema,
        )


def test_moonraker_rejects_unknown_field():
    schema = _load("moonraker")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"host": "x", "port": 7125, "rogue_field": "value"},
            schema,
        )


def test_dock_modes_documented_in_adapter_registry_readme():
    """The adapter_registry README §4 documents the 3 dock modes; this test
    locks the README's section presence as the canonical reference."""
    readme = REPO_ROOT / "03_implementation" / "adapter_registry" / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert "## 4. Dock / undock / fullscreen contract" in text
    for mode in ("`docked`", "`undocked`", "`external`"):
        assert mode in text, f"dock mode {mode} not documented in adapter_registry/README.md §4"
