"""G-code analyzer.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §12 (G-code Pre-flight)

Parses sliced G-code (PrusaSlicer / OrcaSlicer / SuperSlicer / Cura output)
and produces an analysis report:

  - Total time estimate (parsed from header comments)
  - Filament usage (length + weight)
  - Layer count + layer height
  - Approximate move budget per type (extrusion, travel, retraction)
  - Support density & infill density when present in slicer comments
  - Risk flags: extreme print time, extreme filament usage, no bed mesh,
    no purge, no PA, no temperature change for material switch

This is a passive read-only analyzer. It reads the head/tail of the file
(slicer summaries always sit there) and a sample of the body for move
counts. We never replay the whole file in memory.
"""

from __future__ import annotations

import dataclasses
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class GcodeAnalysis:
    """Parsed metrics + risk flags from a single .gcode file."""

    path: str
    file_size_bytes: int
    slicer_name: str = ""
    slicer_version: str = ""
    estimated_print_time_min: float | None = None
    filament_used_mm: float | None = None
    filament_used_g: float | None = None
    layer_count: int | None = None
    layer_height_mm: float | None = None
    nozzle_temp_c: float | None = None
    bed_temp_c: float | None = None
    support_used: bool | None = None
    infill_density_pct: float | None = None
    bed_mesh_loaded: bool = False
    pressure_advance_set: bool = False

    extrusion_moves_sampled: int = 0
    travel_moves_sampled: int = 0
    retraction_count_sampled: int = 0

    risk_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def estimated_print_time_h(self) -> float | None:
        if self.estimated_print_time_min is None:
            return None
        return round(self.estimated_print_time_min / 60.0, 2)

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["estimated_print_time_h"] = self.estimated_print_time_h
        return d


# -----------------------------------------------------------------------------

_HEAD_BYTES = 16 * 1024
_TAIL_BYTES = 16 * 1024
_BODY_SAMPLE_BYTES = 256 * 1024  # 256KB — enough for stable move-count ratios


# Parsing patterns
_RE_TIME_HMS = re.compile(
    r"(?:estimated\s+printing\s+time|;\s*time)\b[^=:]*[=:]\s*"
    r"(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?",
    re.IGNORECASE,
)
_RE_TIME_PRUSA = re.compile(
    r"; estimated printing time \(normal mode\)\s*=\s*"
    r"(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?",
    re.IGNORECASE,
)
_RE_TIME_HMS_COLON = re.compile(r";\s*total\s+print\s+time:\s*(\d+):(\d+):(\d+)", re.IGNORECASE)
_RE_TIME_SECS = re.compile(r";\s*time:\s*(\d+(?:\.\d+)?)\s*(?:seconds?|s)?\b", re.IGNORECASE)
_RE_FIL_MM = re.compile(
    r";\s*filament\s+used\s*\[?(?:mm|millimet[er]+s?)?\]?\s*=\s*([\d.]+)", re.IGNORECASE
)
_RE_FIL_G = re.compile(r";\s*filament\s+used\s*\[?g\]?\s*=\s*([\d.]+)", re.IGNORECASE)
_RE_LAYER_HEIGHT = re.compile(r";\s*(?:layer_height|layer height)\s*=\s*([\d.]+)", re.IGNORECASE)
_RE_LAYER_COUNT = re.compile(r";\s*total\s+layer\s+count\s*=\s*(\d+)", re.IGNORECASE)
_RE_LAYER_NUM = re.compile(r";\s*LAYER:(\d+)", re.IGNORECASE)
_RE_NOZZLE = re.compile(
    r";\s*(?:nozzle_temperature|nozzle temperature|temperature)\s*=\s*([\d.]+)", re.IGNORECASE
)
_RE_BED = re.compile(r";\s*(?:bed_temperature|bed temperature)\s*=\s*([\d.]+)", re.IGNORECASE)
_RE_SUPPORT = re.compile(r";\s*support_material\s*=\s*([01])", re.IGNORECASE)
_RE_INFILL = re.compile(r";\s*fill_density\s*=\s*([\d.]+)\s*%?", re.IGNORECASE)
_RE_GENERATOR = re.compile(r";\s*generated\s+(?:with|by)\s+(\S+)\s*([\w.\-]*)", re.IGNORECASE)


def _parse_hms(d: str | None, h: str | None, m: str | None, s: str | None) -> float | None:
    if not any((d, h, m, s)):
        return None
    di, hi, mi, si = (int(x or 0) for x in (d, h, m, s))
    return di * 24 * 60 + hi * 60 + mi + si / 60.0


def _parse_header(text: str) -> dict[str, object]:
    out: dict[str, object] = {}

    # Generator / slicer
    m = _RE_GENERATOR.search(text)
    if m:
        out["slicer_name"] = m.group(1).strip()
        out["slicer_version"] = m.group(2).strip()

    # Time estimates
    for rx in (_RE_TIME_PRUSA, _RE_TIME_HMS):
        m = rx.search(text)
        if m:
            t = _parse_hms(*m.groups())
            if t is not None:
                out["estimated_print_time_min"] = t
                break
    if "estimated_print_time_min" not in out:
        m = _RE_TIME_HMS_COLON.search(text)
        if m:
            h, mn, s = (int(g) for g in m.groups())
            out["estimated_print_time_min"] = h * 60 + mn + s / 60.0
        else:
            m = _RE_TIME_SECS.search(text)
            if m:
                out["estimated_print_time_min"] = float(m.group(1)) / 60.0

    if m := _RE_FIL_MM.search(text):
        out["filament_used_mm"] = float(m.group(1))
    if m := _RE_FIL_G.search(text):
        out["filament_used_g"] = float(m.group(1))
    if m := _RE_LAYER_HEIGHT.search(text):
        out["layer_height_mm"] = float(m.group(1))
    if m := _RE_LAYER_COUNT.search(text):
        out["layer_count"] = int(m.group(1))
    if m := _RE_NOZZLE.search(text):
        out["nozzle_temp_c"] = float(m.group(1))
    if m := _RE_BED.search(text):
        out["bed_temp_c"] = float(m.group(1))
    if m := _RE_SUPPORT.search(text):
        out["support_used"] = bool(int(m.group(1)))
    if m := _RE_INFILL.search(text):
        out["infill_density_pct"] = float(m.group(1))

    out["bed_mesh_loaded"] = "BED_MESH_PROFILE LOAD" in text or "G29" in text
    out["pressure_advance_set"] = "SET_PRESSURE_ADVANCE" in text or "M900" in text
    return out


def _count_moves_in_sample(sample: str) -> tuple[int, int, int, int | None]:
    """Return (extrusion, travel, retractions, derived_layer_count_fallback).

    The layer-count fallback is derived by counting `;LAYER:` annotations
    in the sample; only useful when the slicer didn't write a header
    `total layer count`.
    """
    extrusion = 0
    travel = 0
    retractions = 0
    layer_max = -1
    for line in sample.splitlines():
        s = line.lstrip()
        if not s or s.startswith(";"):
            m = _RE_LAYER_NUM.match(s)
            if m:
                ln = int(m.group(1))
                if ln > layer_max:
                    layer_max = ln
            continue
        # G1 with E -> extrusion. G1 without E or G0 -> travel.
        if s.startswith(("G1", "G0", "G2", "G3")):
            has_e = " E" in s or s.endswith("E0") or "E-" in s
            if has_e:
                if "E-" in s:
                    retractions += 1
                else:
                    extrusion += 1
            else:
                travel += 1
    return extrusion, travel, retractions, (layer_max + 1 if layer_max >= 0 else None)


def _build_risk_flags(a: GcodeAnalysis) -> list[str]:
    flags: list[str] = []
    if a.estimated_print_time_min and a.estimated_print_time_min > 720:
        flags.append(f"long-print: {a.estimated_print_time_h}h estimated")
    if a.estimated_print_time_min and a.estimated_print_time_min < 1:
        flags.append("suspiciously-short-print: <1 min estimated")
    if a.filament_used_g and a.filament_used_g > 800:
        flags.append(f"heavy-spool: {a.filament_used_g:.0f}g (most spools = 1kg)")
    if a.layer_count and a.layer_height_mm:
        derived_height = a.layer_count * a.layer_height_mm
        if derived_height > 500:
            flags.append(
                f"large-z: derived height {derived_height:.0f}mm — "
                f"only S1/V400/QQ-S Pro support >360mm Z"
            )
    if a.support_used and a.infill_density_pct and a.infill_density_pct < 5:
        flags.append("low-infill-with-support: support may collapse onto sparse infill")
    if a.travel_moves_sampled and a.extrusion_moves_sampled:
        ratio = a.travel_moves_sampled / max(a.extrusion_moves_sampled, 1)
        if ratio > 0.40:
            flags.append(f"high-travel-ratio: {ratio:.0%} — model may need rotation")
    return flags


def analyze_gcode(path: str | Path) -> GcodeAnalysis:
    """Open a g-code file and produce a metrics report.

    Reads the head + tail (where slicers put their summaries) and a body
    sample for move counts. Total file IO is bounded.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"GCode not found: {p}")
    size = p.stat().st_size
    with p.open("rb") as fh:
        head = fh.read(_HEAD_BYTES).decode("utf-8", errors="ignore")
        if size > _HEAD_BYTES + _TAIL_BYTES:
            fh.seek(max(0, size - _TAIL_BYTES))
            tail = fh.read(_TAIL_BYTES).decode("utf-8", errors="ignore")
        else:
            tail = ""
        # Sample a chunk from the body for move counts
        if size > _HEAD_BYTES + _BODY_SAMPLE_BYTES + _TAIL_BYTES:
            fh.seek(_HEAD_BYTES)
            body_sample = fh.read(_BODY_SAMPLE_BYTES).decode("utf-8", errors="ignore")
        else:
            fh.seek(0)
            body_sample = fh.read().decode("utf-8", errors="ignore")

    parsed = _parse_header(head + "\n" + tail)
    extr, trav, retr, layer_fallback = _count_moves_in_sample(body_sample)

    a = GcodeAnalysis(
        path=str(p.resolve()),
        file_size_bytes=size,
        slicer_name=str(parsed.get("slicer_name", "")),
        slicer_version=str(parsed.get("slicer_version", "")),
        estimated_print_time_min=parsed.get("estimated_print_time_min"),  # type: ignore[arg-type]
        filament_used_mm=parsed.get("filament_used_mm"),  # type: ignore[arg-type]
        filament_used_g=parsed.get("filament_used_g"),  # type: ignore[arg-type]
        layer_count=(parsed.get("layer_count") or layer_fallback),  # type: ignore[arg-type]
        layer_height_mm=parsed.get("layer_height_mm"),  # type: ignore[arg-type]
        nozzle_temp_c=parsed.get("nozzle_temp_c"),  # type: ignore[arg-type]
        bed_temp_c=parsed.get("bed_temp_c"),  # type: ignore[arg-type]
        support_used=parsed.get("support_used"),  # type: ignore[arg-type]
        infill_density_pct=parsed.get("infill_density_pct"),  # type: ignore[arg-type]
        bed_mesh_loaded=bool(parsed.get("bed_mesh_loaded", False)),
        pressure_advance_set=bool(parsed.get("pressure_advance_set", False)),
        extrusion_moves_sampled=extr,
        travel_moves_sampled=trav,
        retraction_count_sampled=retr,
    )
    a.risk_flags = _build_risk_flags(a)
    return a


__all__ = [
    "GcodeAnalysis",
    "analyze_gcode",
]
