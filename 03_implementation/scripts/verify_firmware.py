#!/usr/bin/env python3
"""verify_firmware.py — Source/toolchain verifier for Hermes3D firmware lane.

Lane: H3D-CLAUDE-SOURCE-FIRMWARE
Owner: claude-source-firmware-05

HARD POLICY (enforced by code + asserted by tests):
  * NEVER flash firmware.
  * NEVER open serial / USB to a printer board.
  * NEVER call `make flash`, `make upload`, `avrdude`, `st-flash`, `dfu-util`,
    `openocd ... program`, `bossac`, or any equivalent.
  * Firmware sources are checked with `git ls-remote --heads <url>` (no clone).
  * Toolchains are checked with `<cmd> --version` only.
  * Network and subprocess timeouts are bounded at 5 seconds.

Output: JSON summary written to
  03_implementation/proof/FIRMWARE_VERIFY_<UTC_DATE>.json
The verifier exits 0 even when sources/toolchains are missing — absence is
honestly recorded, not fabricated.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Forbidden tokens — used both at runtime (refuse to dispatch) and by tests.
# ---------------------------------------------------------------------------
FORBIDDEN_FLASH_TOKENS: tuple[str, ...] = (
    "flash",
    "upload",
    "avrdude",
    "st-flash",
    "dfu-util",
    "bossac",
    "openocd",
    "stm32flash",
    "pio run -t upload",
    "platformio run -t upload",
    "make program",
)

PROBE_TIMEOUT_SECONDS = 5

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "03_implementation" / "adapter_registry" / "schemas"
PROOF_DIR = REPO_ROOT / "03_implementation" / "proof"

FIRMWARE_SCHEMAS: tuple[str, ...] = (
    "firmware_klipper.schema.json",
    "firmware_marlin.schema.json",
    "firmware_reprap.schema.json",
    "firmware_prusa.schema.json",
)

TOOLCHAIN_SCHEMAS: tuple[str, ...] = (
    "toolchain_avr_gcc.schema.json",
    "toolchain_arm_none_eabi.schema.json",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _default_value(schema: dict[str, Any], key: str) -> Any:
    """Return the schema-defined default or const for a field."""
    props = schema.get("properties", {})
    field = props.get(key, {})
    if "const" in field:
        return field["const"]
    return field.get("default")


def _is_flash_invocation(cmd: str) -> bool:
    """Return True if ``cmd`` looks like a flash/upload/program invocation."""
    if not cmd:
        return False
    lowered = cmd.lower()
    for tok in FORBIDDEN_FLASH_TOKENS:
        if tok in lowered:
            # Carve-out: allow innocuous substrings that contain "flash" only as
            # part of a benign word. Currently none of our defaults do, so the
            # strict match is intentional.
            return True
    return False


def _check_git_ls_remote(url: str) -> dict[str, Any]:
    """Read-only probe: list remote heads. Never clones."""
    if shutil.which("git") is None:
        return {
            "ok": False,
            "reason": "git_not_installed",
            "stdout_first_line": "",
            "head_count": 0,
        }
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "reason": "timeout",
            "stdout_first_line": "",
            "head_count": 0,
        }
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "reason": f"exec_error:{type(exc).__name__}",
            "stdout_first_line": "",
            "head_count": 0,
        }

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return {
        "ok": proc.returncode == 0 and bool(lines),
        "returncode": proc.returncode,
        "head_count": len(lines),
        "stdout_first_line": lines[0] if lines else "",
        "stderr_tail": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
    }


def _check_toolchain_version(install_check: str, version_pattern: str) -> dict[str, Any]:
    """Compile-only probe: <cmd> --version. Never flashes."""
    if _is_flash_invocation(install_check):
        return {
            "ok": False,
            "reason": "refused_flash_invocation",
            "version": None,
            "raw_first_line": "",
        }
    parts = install_check.split()
    if not parts:
        return {"ok": False, "reason": "empty_install_check", "version": None, "raw_first_line": ""}
    exe = parts[0]
    if shutil.which(exe) is None:
        return {
            "ok": False,
            "reason": "not_installed",
            "version": None,
            "raw_first_line": "",
        }
    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "version": None, "raw_first_line": ""}
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "reason": f"exec_error:{type(exc).__name__}",
            "version": None,
            "raw_first_line": "",
        }

    raw = proc.stdout or proc.stderr or ""
    first_line = raw.splitlines()[0] if raw.splitlines() else ""
    version = None
    try:
        match = re.search(version_pattern, raw)
        if match and match.groups():
            version = match.group(1)
        elif match:
            version = match.group(0)
    except re.error:
        version = None

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "version": version,
        "raw_first_line": first_line,
    }


# ---------------------------------------------------------------------------
# Verification driver
# ---------------------------------------------------------------------------
def verify_firmwares() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in FIRMWARE_SCHEMAS:
        schema = _load_schema(name)
        source_url = _default_value(schema, "source_url") or ""
        install_check = _default_value(schema, "install_check") or ""
        if _is_flash_invocation(install_check):
            results.append(
                {
                    "schema": name,
                    "name": _default_value(schema, "name"),
                    "source_url": source_url,
                    "install_check": install_check,
                    "probe": {"ok": False, "reason": "refused_flash_invocation"},
                    "no_flash": True,
                }
            )
            continue
        probe = _check_git_ls_remote(source_url)
        results.append(
            {
                "schema": name,
                "name": _default_value(schema, "name"),
                "source_url": source_url,
                "install_check": install_check,
                "probe": probe,
                "no_flash": True,
            }
        )
    return results


def verify_toolchains() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name in TOOLCHAIN_SCHEMAS:
        schema = _load_schema(name)
        install_check = _default_value(schema, "install_check") or ""
        version_pattern = _default_value(schema, "version_pattern") or r".*"
        probe = _check_toolchain_version(install_check, version_pattern)
        results.append(
            {
                "schema": name,
                "name": _default_value(schema, "name"),
                "install_check": install_check,
                "version_pattern": version_pattern,
                "probe": probe,
                "compile_only": True,
                "no_flash": True,
            }
        )
    return results


def build_proof(
    firmwares: list[dict[str, Any]], toolchains: list[dict[str, Any]]
) -> dict[str, Any]:
    now = _dt.datetime.now(_dt.timezone.utc)
    return {
        "lane": "H3D-CLAUDE-SOURCE-FIRMWARE",
        "owner": "claude-source-firmware-05",
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy": {
            "no_flash": True,
            "no_serial_to_printer": True,
            "no_usb_to_printer": True,
            "probe_timeout_seconds": PROBE_TIMEOUT_SECONDS,
            "forbidden_flash_tokens": list(FORBIDDEN_FLASH_TOKENS),
        },
        "firmwares": firmwares,
        "toolchains": toolchains,
        "summary": {
            "firmware_sources_reachable": [
                f["name"] for f in firmwares if f.get("probe", {}).get("ok")
            ],
            "firmware_sources_unreachable": [
                f["name"] for f in firmwares if not f.get("probe", {}).get("ok")
            ],
            "toolchains_present": [t["name"] for t in toolchains if t.get("probe", {}).get("ok")],
            "toolchains_absent": [
                t["name"] for t in toolchains if not t.get("probe", {}).get("ok")
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=PROOF_DIR / "FIRMWARE_VERIFY_2026-05-06.json",
        help="Output proof JSON path.",
    )
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Skip git ls-remote probes (still verifies toolchains and policy).",
    )
    args = parser.parse_args(argv)

    if args.no_network:
        firmwares = []
        for name in FIRMWARE_SCHEMAS:
            schema = _load_schema(name)
            firmwares.append(
                {
                    "schema": name,
                    "name": _default_value(schema, "name"),
                    "source_url": _default_value(schema, "source_url"),
                    "install_check": _default_value(schema, "install_check"),
                    "probe": {"ok": False, "reason": "skipped_no_network"},
                    "no_flash": True,
                }
            )
    else:
        firmwares = verify_firmwares()

    toolchains = verify_toolchains()
    proof = build_proof(firmwares, toolchains)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        json.dump(proof, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # Honest, terse stdout summary.
    print(json.dumps(proof["summary"], indent=2, sort_keys=True))
    print(f"proof_path={args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
