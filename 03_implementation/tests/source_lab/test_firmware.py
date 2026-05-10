"""Tests for the H3D-CLAUDE-SOURCE-FIRMWARE lane verifier.

These tests assert:

1. Each owned schema is valid JSON, names itself with a ``$id``, and contains
   the four required fields (name, source_url, install_check, version_pattern).
2. No schema's defaults contain a flash/upload/program invocation.
3. The generated proof JSON has the expected shape.
4. The verifier helper :func:`_is_flash_invocation` correctly refuses every
   forbidden token.
5. The whole verifier source contains no ``make flash`` / ``avrdude`` /
   ``st-flash`` / ``dfu-util`` / ``bossac`` / ``stm32flash`` / ``program`` /
   ``upload`` *invocations* (i.e. they appear only in the forbidden-token list
   and refusal messages, never as live commands).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "03_implementation" / "adapter_registry" / "schemas"
SCRIPT_PATH = REPO_ROOT / "03_implementation" / "scripts" / "verify_firmware.py"

FIRMWARE_SCHEMAS = (
    "firmware_klipper.schema.json",
    "firmware_marlin.schema.json",
    "firmware_reprap.schema.json",
    "firmware_prusa.schema.json",
)
TOOLCHAIN_SCHEMAS = (
    "toolchain_avr_gcc.schema.json",
    "toolchain_arm_none_eabi.schema.json",
)
ALL_SCHEMAS = FIRMWARE_SCHEMAS + TOOLCHAIN_SCHEMAS

REQUIRED_FIELDS = ("name", "source_url", "install_check", "version_pattern")

FORBIDDEN_TOKENS_IN_DEFAULTS = (
    "make flash",
    "make upload",
    "avrdude",
    "st-flash",
    "dfu-util",
    "bossac",
    "stm32flash",
    "pio run -t upload",
    "platformio run -t upload",
)


def _load(name: str) -> dict:
    with (SCHEMA_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("schema_file", ALL_SCHEMAS)
def test_schema_is_valid_json_with_required_fields(schema_file: str) -> None:
    schema = _load(schema_file)
    assert schema.get("$schema", "").startswith("https://json-schema.org/")
    assert schema.get("$id", "").startswith("hermes3d://adapter_registry/schemas/")
    required = schema.get("required", [])
    for field in REQUIRED_FIELDS:
        assert field in required, f"{schema_file} missing required field {field}"
        assert field in schema.get("properties", {}), f"{schema_file} missing property {field}"


@pytest.mark.parametrize("schema_file", ALL_SCHEMAS)
def test_schema_defaults_have_no_flash_invocation(schema_file: str) -> None:
    """Forbidden tokens must NOT appear in any executable field (default value
    of name / source_url / install_check / version_pattern). They are allowed
    in human-readable description fields where they document the exclusion."""
    schema = _load(schema_file)
    props = schema.get("properties", {})
    executable_fields = ("name", "source_url", "install_check", "version_pattern")
    for field in executable_fields:
        spec = props.get(field, {})
        value = spec.get("const", spec.get("default", ""))
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        for tok in FORBIDDEN_TOKENS_IN_DEFAULTS:
            assert tok not in lowered, (
                f"{schema_file} field {field!r} contains forbidden flash token {tok!r}: {value!r}"
            )


@pytest.mark.parametrize("schema_file", ALL_SCHEMAS)
def test_schema_marks_no_flash(schema_file: str) -> None:
    schema = _load(schema_file)
    no_flash = schema.get("properties", {}).get("no_flash", {})
    assert no_flash.get("const") is True, f"{schema_file} must declare no_flash const true"


@pytest.mark.parametrize("schema_file", FIRMWARE_SCHEMAS)
def test_firmware_install_check_is_ls_remote(schema_file: str) -> None:
    schema = _load(schema_file)
    default = schema["properties"]["install_check"].get("default", "")
    assert default.startswith("git ls-remote"), (
        f"{schema_file} install_check must use git ls-remote, got {default!r}"
    )
    assert "clone" not in default.lower()


@pytest.mark.parametrize("schema_file", TOOLCHAIN_SCHEMAS)
def test_toolchain_install_check_is_version_only(schema_file: str) -> None:
    schema = _load(schema_file)
    default = schema["properties"]["install_check"].get("default", "")
    assert default.endswith("--version"), (
        f"{schema_file} install_check must end with --version, got {default!r}"
    )


def test_verify_firmware_module_imports_and_policy_constants() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("verify_firmware_mod", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert mod.PROBE_TIMEOUT_SECONDS == 5
    assert "avrdude" in mod.FORBIDDEN_FLASH_TOKENS
    assert "st-flash" in mod.FORBIDDEN_FLASH_TOKENS
    assert "dfu-util" in mod.FORBIDDEN_FLASH_TOKENS
    assert "bossac" in mod.FORBIDDEN_FLASH_TOKENS
    # Refusal logic must trip on every forbidden token.
    for tok in mod.FORBIDDEN_FLASH_TOKENS:
        assert mod._is_flash_invocation(f"some-tool {tok} foo") is True
    assert mod._is_flash_invocation("avr-gcc --version") is False
    assert mod._is_flash_invocation("git ls-remote --heads https://example/repo.git") is False


def test_verify_firmware_no_network_run_writes_valid_proof(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("verify_firmware_mod2", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    out = tmp_path / "proof.json"
    rc = mod.main(["--no-network", "--out", str(out)])
    assert rc == 0
    proof = json.loads(out.read_text(encoding="utf-8"))
    assert proof["lane"] == "H3D-CLAUDE-SOURCE-FIRMWARE"
    assert proof["policy"]["no_flash"] is True
    assert proof["policy"]["no_serial_to_printer"] is True
    assert proof["policy"]["no_usb_to_printer"] is True
    assert len(proof["firmwares"]) == len(FIRMWARE_SCHEMAS)
    assert len(proof["toolchains"]) == len(TOOLCHAIN_SCHEMAS)
    for entry in proof["firmwares"] + proof["toolchains"]:
        # Every recorded entry asserts no_flash and contains no flash token in
        # its install_check.
        assert entry.get("no_flash") is True
        ic = (entry.get("install_check") or "").lower()
        for tok in FORBIDDEN_TOKENS_IN_DEFAULTS:
            assert tok not in ic


def test_verifier_source_has_no_live_flash_command() -> None:
    """The verifier source must mention flash tokens only inside the forbidden
    list / refusal messages, never as a live shell invocation."""
    src = SCRIPT_PATH.read_text(encoding="utf-8")
    # Direct shell-call patterns we never want to see executing.
    bad_patterns = [
        r"subprocess\.[a-z_]+\(\s*\[?\s*[\"']avrdude",
        r"subprocess\.[a-z_]+\(\s*\[?\s*[\"']st-flash",
        r"subprocess\.[a-z_]+\(\s*\[?\s*[\"']dfu-util",
        r"subprocess\.[a-z_]+\(\s*\[?\s*[\"']bossac",
        r"subprocess\.[a-z_]+\(\s*\[?\s*[\"']openocd",
        r"os\.system\(\s*[\"'][^\"']*\b(?:make\s+flash|avrdude|st-flash|dfu-util|bossac)\b",
    ]
    for pat in bad_patterns:
        assert re.search(pat, src) is None, (
            f"verify_firmware.py contains live flash invocation matching {pat!r}"
        )
