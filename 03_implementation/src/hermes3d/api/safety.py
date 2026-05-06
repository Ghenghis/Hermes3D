"""Hard backend safety checks for locked printers."""

from __future__ import annotations

from fastapi import HTTPException

from hermes3d.services.local_state import is_s1_printer

S1_PRINTER_ID = "flsun-s1"
S1_ALT_IDS = {"flsun-s1", "flsun_s1", "s1", "192.168.0.12"}
S1_LOCK_REASON = "Maintenance lock: do not test or move. Movement may damage the hotend."


def is_s1_target(printer_id: str | None) -> bool:
    return bool(printer_id and (printer_id.lower() in S1_ALT_IDS or is_s1_printer(printer_id)))


def check_s1_lock(printer_id: str | None) -> None:
    if is_s1_target(printer_id):
        raise HTTPException(
            status_code=423,
            detail={
                "error": "PRINTER_LOCKED",
                "reason": S1_LOCK_REASON,
                "printer_id": S1_PRINTER_ID,
            },
        )
