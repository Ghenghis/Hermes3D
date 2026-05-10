from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from hermes3d.db.init import connect, init_db


def ensure_db() -> None:
    init_db()


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    ensure_db()
    conn = connect()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    result = rows(sql, params)
    return result[0] if result else None


def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    ensure_db()
    conn = connect()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


def as_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))
