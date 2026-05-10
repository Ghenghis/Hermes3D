"""Slicer CLI verifier — safe read-only probe.

Checks each slicer's presence and version using --version / --help / help only.
NEVER slices a model. NEVER sends data to a printer.

Supported slicers:
  - PrusaSlicer   (prusa-slicer-console.exe / prusa-slicer / PrusaSlicer)
  - OrcaSlicer    (orca-slicer.exe / orca-slicer / OrcaSlicer)
  - FLSUN Slicer  (FlsunSlicer.exe / flsun-slicer)
  - CuraEngine    (CuraEngine.exe / CuraEngine)
  - SuperSlicer   (superslicer.exe / superslicer / SuperSlicer)
  - Slic3r        (slic3r.exe / slic3r / Slic3r)
  - BambuStudio   (bambu-studio.exe / bambu_studio / bambu-studio)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Slicer probe table
# NEVER add --export-gcode, --slice, or any output-producing flags.
# Each entry: (name, candidate_paths_or_commands, safe_args, version_re)
# ---------------------------------------------------------------------------

_PROBES: list[dict[str, Any]] = [
    {
        "id": "prusaslicer",
        "label": "PrusaSlicer",
        "candidates": [
            "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
            "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer.exe",
            "prusa-slicer-console",
            "prusa-slicer",
            "PrusaSlicer",
        ],
        # --help exits 0 and prints version; --version is not universally supported
        "args": ["--help"],
        "version_re": r"PrusaSlicer[- ]([\d.]+(?:-\w+\d*)?)",
        "timeout_s": 12,
    },
    {
        "id": "orcaslicer",
        "label": "OrcaSlicer",
        "candidates": [
            "C:/Program Files/OrcaSlicer/orca-slicer.exe",
            "orca-slicer",
            "OrcaSlicer",
        ],
        "args": ["--help"],
        "version_re": r"OrcaSlicer[- ]([\d.]+(?:\.\w+)?)",
        "timeout_s": 12,
    },
    {
        "id": "flsun_slicer",
        "label": "FLSUN Slicer",
        "candidates": [
            "C:/FlsunSlicer2.0/FlsunSlicer.exe",
            "C:/Program Files/FlsunSlicer/FlsunSlicer.exe",
            "flsun-slicer",
            "FlsunSlicer",
        ],
        "args": ["--help"],
        "version_re": r"FlsunSlicer[- ]([\d.]+(?:\.\w+)?)",
        "timeout_s": 12,
    },
    {
        "id": "curaengine",
        "label": "CuraEngine",
        "candidates": [
            "C:/Program Files/UltiMaker Cura 5.12.1/CuraEngine.exe",
            "C:/Program Files/Ultimaker Cura/CuraEngine.exe",
            "CuraEngine",
            "curaengine",
        ],
        # CuraEngine uses positional "help" not --help
        "args": ["help"],
        "version_re": r"Cura_SteamEngine version ([\d.]+)",
        "timeout_s": 12,
    },
    {
        "id": "superslicer",
        "label": "SuperSlicer",
        "candidates": [
            "C:/Program Files/SuperSlicer/superslicer-console.exe",
            "C:/Program Files/SuperSlicer/superslicer.exe",
            "superslicer-console",
            "superslicer",
            "SuperSlicer",
        ],
        "args": ["--help"],
        "version_re": r"SuperSlicer[- ]([\d.]+(?:\.\w+)?)",
        "timeout_s": 12,
    },
    {
        "id": "slic3r",
        "label": "Slic3r",
        "candidates": [
            "C:/Program Files/Slic3r/slic3r-console.exe",
            "C:/Program Files/Slic3r/slic3r.exe",
            "slic3r-console",
            "slic3r",
            "Slic3r",
        ],
        "args": ["--help"],
        "version_re": r"Slic3r[- ]([\d.]+(?:\.\w+)?)",
        "timeout_s": 12,
    },
    {
        "id": "bambustudio",
        "label": "BambuStudio",
        "candidates": [
            "C:/Program Files/Bambu Studio/bambu-studio.exe",
            "C:/Program Files/BambuStudio/bambu-studio.exe",
            "bambu-studio",
            "bambu_studio",
            "BambuStudio",
        ],
        # BambuStudio GUI does not expose a stable --version CLI; file metadata is
        # the only safe non-destructive check.
        "args": [],
        "version_re": r"",
        "timeout_s": 1,
        "metadata_only": True,
    },
]


def _resolve_exe(candidates: list[str]) -> str | None:
    """Return the first resolvable executable path from the candidate list."""
    for candidate in candidates:
        p = Path(candidate)
        if p.is_absolute():
            if p.is_file():
                return str(p)
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def _run_safe(exe: str, args: list[str], *, timeout_s: int) -> subprocess.CompletedProcess[str]:
    """Run the executable with safe read-only args; never raises."""
    cmd = [exe, *args]
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd, 124, stdout=str(exc.stdout or ""), stderr=f"probe timed out after {timeout_s}s"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=str(exc))


def _extract_version(text: str, pattern: str) -> str | None:
    if not pattern:
        return None
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


def probe_slicer(entry: dict[str, Any]) -> dict[str, Any]:
    """Probe a single slicer. Returns a standardised result dict."""
    slicer_id = str(entry["id"])
    label = str(entry["label"])
    candidates: list[str] = [str(c) for c in entry.get("candidates") or []]
    args: list[str] = [str(a) for a in entry.get("args") or []]
    version_re: str = str(entry.get("version_re") or "")
    timeout_s: int = int(entry.get("timeout_s") or 12)
    metadata_only: bool = bool(entry.get("metadata_only", False))

    exe = _resolve_exe(candidates)

    if exe is None:
        return {
            "id": slicer_id,
            "name": label,
            "status": "not_found",
            "version": None,
            "exe_path": None,
            "return_code": None,
            "output_head": [],
            "note": "No candidate executable found on this system.",
        }

    if metadata_only:
        # Safe file-existence check only; do NOT launch GUI slicer
        return {
            "id": slicer_id,
            "name": label,
            "status": "found",
            "version": None,
            "exe_path": exe,
            "return_code": None,
            "output_head": [],
            "note": "Detected via filesystem metadata; CLI version flag not available.",
        }

    proc = _run_safe(exe, args, timeout_s=timeout_s)
    combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    version = _extract_version(combined, version_re)

    # CuraEngine exits non-zero on "help" but still prints version — treat as found
    # if we can detect the version string or recognisable output
    is_ok = proc.returncode == 0 or version is not None or len(combined) > 10

    return {
        "id": slicer_id,
        "name": label,
        "status": "found" if is_ok else "not_found",
        "version": version,
        "exe_path": exe,
        "return_code": proc.returncode,
        "output_head": [line for line in combined.splitlines()[:12] if line.strip()],
        "note": None,
    }


def run_all_probes(probes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run all slicer probes and return a summary report."""
    if probes is None:
        probes = _PROBES

    results: list[dict[str, Any]] = []
    for entry in probes:
        result = probe_slicer(entry)
        results.append(result)

    found_count = sum(1 for r in results if r["status"] == "found")
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "read-only-version-check-only; never slices; never sends to printer",
        "probe_version": "slicer-verifier-v1",
        "summary": {
            "total": len(results),
            "found": found_count,
            "not_found": len(results) - found_count,
        },
        "slicers": results,
    }


def main() -> None:
    report = run_all_probes()
    print(json.dumps(report, indent=2))

    found = report["summary"]["found"]
    total = report["summary"]["total"]
    not_found_names = [r["name"] for r in report["slicers"] if r["status"] != "found"]

    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"Slicer CLI verification: {found}/{total} found", file=sys.stderr)
    if not_found_names:
        print(f"Not found: {', '.join(not_found_names)}", file=sys.stderr)
    print("Policy: read-only probe only — no slicing performed.", file=sys.stderr)


if __name__ == "__main__":
    main()
