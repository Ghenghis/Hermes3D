from __future__ import annotations

from fastapi import APIRouter

from hermes3d.api.routes._common import execute, rows

router = APIRouter()


@router.get("/api/ports")
def get_ports() -> dict[str, int]:
    result: dict[str, int] = {}
    for item in rows("SELECT key, value FROM settings WHERE key LIKE 'ports.%'"):
        result[item["key"].removeprefix("ports.")] = int(item["value"])
    return result


@router.put("/api/ports")
def put_ports(update: dict[str, int]) -> dict:
    current = get_ports()
    candidate = {**current, **update}
    conflicts = []
    seen: dict[int, str] = {}
    for name, port in candidate.items():
        if port in seen:
            conflicts.append(f"{name} port {port} conflicts with {seen[port]}")
        seen[port] = name
    if conflicts:
        return {"saved": False, "restart_required": False, "conflicts": conflicts}
    for name, port in update.items():
        execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))", (f"ports.{name}", str(port)))
    return {"saved": True, "restart_required": "api" in update, "conflicts": []}
