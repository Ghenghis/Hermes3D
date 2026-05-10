from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = IMPLEMENTATION_ROOT.parent
sys.path.insert(0, str(IMPLEMENTATION_ROOT / "src"))

from hermes3d.core.slicer.flsun_profiles import (  # noqa: E402
    FLSUN_PROFILE_REFS,
    FLSUN_SLICER_INSTALL,
    FLSUN_SOURCE_PROFILE_INI,
)

OUTPUT = IMPLEMENTATION_ROOT / "proof" / "FLSUN_PROFILE_SOURCE_AUDIT.json"
SLICER_EXE = FLSUN_SLICER_INSTALL / "FlsunSlicer.exe"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "slicer_executable": str(SLICER_EXE),
        "slicer_detected": SLICER_EXE.is_file(),
        "slicer_help_head": _slicer_help_head(),
        "source_profile_ini": str(FLSUN_SOURCE_PROFILE_INI),
        "source_profile_ini_detected": FLSUN_SOURCE_PROFILE_INI.is_file(),
        "official_wiki_refs": {
            "t1": "https://wiki.flsun3d.com/en/FlsunT1",
            "v400": "https://wiki.flsun3d.com/en/V400",
            "s1": "https://wiki.flsun3d.com/en/S1",
        },
        "printers": {
            printer_id: _printer_audit(printer_id, refs)
            for printer_id, refs in FLSUN_PROFILE_REFS.items()
        },
        "safety": {
            "s1_live_probe": "skipped_by_policy",
            "s1_upload_move_print": "blocked_by_backend_http_423",
        },
    }
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(OUTPUT)
    return 0


def _slicer_help_head() -> list[str]:
    if not SLICER_EXE.is_file():
        return []
    try:
        proc = subprocess.run(
            [str(SLICER_EXE), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    merged = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    return merged.splitlines()[:20]


def _printer_audit(printer_id: str, refs: dict[str, Any]) -> dict[str, Any]:
    installed_profiles = refs.get("installed_profiles", {})
    profiles: dict[str, dict[str, Any]] = {}
    for role, raw_path in installed_profiles.items():
        path = Path(str(raw_path))
        profiles[role] = {
            "path": str(path),
            "detected": path.is_file(),
            "summary": _json_profile_summary(path) if path.is_file() else None,
        }
    return {
        "official_wiki_url": refs.get("official_wiki_url"),
        "official_setup_topics": refs.get("official_setup_topics", []),
        "profiles": profiles,
        "source_profile_ini_contains_model": _source_ini_contains(printer_id),
        "safety": refs.get("safety"),
    }


def _json_profile_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = [
        "name",
        "type",
        "version",
        "printer_model",
        "gcode_flavor",
        "printable_height",
        "nozzle_diameter",
        "layer_height",
        "sparse_infill_density",
        "nozzle_temperature",
        "hot_plate_temp",
    ]
    summary = {key: data.get(key) for key in keys if key in data}
    if "machine_start_gcode" in data:
        summary["machine_start_gcode_head"] = str(data["machine_start_gcode"]).splitlines()[:8]
    if "machine_end_gcode" in data:
        summary["machine_end_gcode_head"] = str(data["machine_end_gcode"]).splitlines()[:8]
    return summary


def _source_ini_contains(printer_id: str) -> bool:
    if not FLSUN_SOURCE_PROFILE_INI.is_file():
        return False
    text = FLSUN_SOURCE_PROFILE_INI.read_text(encoding="utf-8", errors="replace")
    if printer_id in {"flsun_t1_a", "flsun_t1_b"}:
        return "[printer:FLSun T1]" in text
    if printer_id == "flsun_v400":
        return "V400" in text
    if printer_id == "flsun_s1":
        return "[printer:FLSun S1]" in text or "printer_model==\"S1\"" in text
    return False


if __name__ == "__main__":
    raise SystemExit(main())
