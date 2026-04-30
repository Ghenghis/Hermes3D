"""Calibration agent.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §23 (Calibration)

Drives common Klipper calibration sequences via Moonraker:

  - PRESSURE_ADVANCE_TUNE   — Marlin/Klipper linear-advance tower
  - INPUT_SHAPER_CALIBRATE  — resonance + per-axis shaper
  - FLOW_RATIO_CALIBRATE    — single-wall extrusion-multiplier test
  - SHAPER_AUTOCALIBRATE    — Klipper3D's automated mode (if available)
  - BED_MESH_CALIBRATE      — KAMP-aware adaptive mesh

These wrap raw G-code/macro calls through Moonraker's `/printer/gcode/script`
endpoint. The agent is *initiation-only* — Klipper is responsible for the
actual probing. The agent records the request, and a follow-up call to
poll_calibration_status() reads the resulting log entries.

Real-world note: each calibration takes 5-30 minutes. The agent never
blocks; it returns immediately after sending the macro, and the caller
polls.
"""
from __future__ import annotations

import dataclasses
import enum
import time
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.printers.moonraker_client import MoonrakerClient


class CalibrationKind(str, enum.Enum):
    PRESSURE_ADVANCE = "pressure_advance"
    INPUT_SHAPER = "input_shaper"
    FLOW_RATIO = "flow_ratio"
    SHAPER_AUTOCALIBRATE = "shaper_autocalibrate"
    BED_MESH = "bed_mesh"


# Macros — most are stock Klipper. SHAPER_AUTOCALIBRATE assumes Dmitry's
# Klippain-shaketune or Klipper3D plugin is installed. The agent gracefully
# reports "macro not found" if it isn't.
_MACROS: dict[CalibrationKind, str] = {
    CalibrationKind.PRESSURE_ADVANCE:
        "TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE "
        "START=0 FACTOR=0.005",
    CalibrationKind.INPUT_SHAPER:
        "SHAPER_CALIBRATE",
    CalibrationKind.FLOW_RATIO:
        "TUNING_TOWER COMMAND=SET_FLOW PARAMETER=FLOW START=90 FACTOR=2",
    CalibrationKind.SHAPER_AUTOCALIBRATE:
        "AXES_SHAPER_CALIBRATION",
    CalibrationKind.BED_MESH:
        "BED_MESH_CALIBRATE ADAPTIVE=1",
}


@dataclass
class CalibrationRequest:
    printer_id: str
    moonraker_url: str
    kind: CalibrationKind
    extra_args: str = ""             # appended to the macro call


@dataclass
class CalibrationResult:
    printer_id: str
    kind: CalibrationKind
    requested_at_unix: float
    macro_sent: str
    moonraker_response: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    succeeded: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["kind"] = self.kind.value
        return d


def run_calibration(request: CalibrationRequest, *,
                     api_key: str | None = None,
                     timeout_s: float = 10.0,
                     ) -> CalibrationResult:
    """Send the calibration macro and return immediately.

    The actual calibration runs on the printer for several minutes;
    callers must poll Klipper's logs (or a follow-up GET on
    /server/info) to determine when it finishes.
    """
    macro = _MACROS[request.kind]
    if request.extra_args:
        macro = f"{macro} {request.extra_args}"
    client = MoonrakerClient(request.moonraker_url, api_key=api_key,
                              timeout_s=timeout_s)
    result = CalibrationResult(
        printer_id=request.printer_id,
        kind=request.kind,
        requested_at_unix=time.time(),
        macro_sent=macro,
    )
    try:
        # Klipper expects gcode commands at /printer/gcode/script
        resp = client._request("POST", "/printer/gcode/script",
                                params={"script": macro})
        result.moonraker_response = resp if isinstance(resp, dict) else {}
        result.succeeded = True
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)
        result.succeeded = False
    return result


def get_macro_for(kind: CalibrationKind) -> str:
    return _MACROS[kind]


__all__ = [
    "CalibrationKind",
    "CalibrationRequest",
    "CalibrationResult",
    "get_macro_for",
    "run_calibration",
]
