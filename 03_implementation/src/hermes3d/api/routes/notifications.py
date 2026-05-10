from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, new_id, row, rows

router = APIRouter()
_subscribers: set[asyncio.Queue[dict]] = set()

DEFAULT_PRIORITY = {
    "INFO": "low",
    "SUCCESS": "low",
    "WARNING": "medium",
    "PRINT_COMPLETE": "medium",
    "ACTION_REQUIRED": "high",
    "ANOMALY_DETECTED": "high",
    "AGENT_BLOCKED": "high",
    "SYSTEM_ERROR": "high",
    "WHILE_AWAY_ESCALATION": "critical",
}


class NotificationCreate(BaseModel):
    type: str
    title: str
    body: str
    priority: str | None = None
    source_agent_id: str | None = None
    source_tab: str | None = None
    action_url: str | None = None
    action_label: str | None = None


class MarkAllRead(BaseModel):
    source_tab: str | None = None


async def _publish(notification: dict) -> None:
    for queue in list(_subscribers):
        try:
            queue.put_nowait(notification)
        except asyncio.QueueFull:
            _subscribers.discard(queue)


@router.get("/api/notifications")
def list_notifications(
    unread: bool | None = None,
    priority: str | None = None,
    type: str | None = None,
    tab: str | None = None,
    limit: int = 50,
    offset: int = 0,
    include_dismissed: bool = False,
) -> dict:
    data = rows(
        """
        SELECT * FROM notifications
        WHERE (? IS NULL OR read_at IS NULL)
          AND (? IS NULL OR priority = ?)
          AND (? IS NULL OR type = ?)
          AND (? IS NULL OR source_tab = ?)
          AND (? OR dismissed_at IS NULL)
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (
            True if unread else None,
            priority,
            priority,
            type,
            type,
            tab,
            tab,
            include_dismissed,
            min(limit, 200),
            offset,
        ),
    )
    unread_count = row(
        "SELECT COUNT(*) AS count FROM notifications WHERE read_at IS NULL AND dismissed_at IS NULL"
    )
    total = row("SELECT COUNT(*) AS count FROM notifications WHERE dismissed_at IS NULL")
    return {
        "notifications": data,
        "total": (total or {}).get("count", 0),
        "unread": (unread_count or {}).get("count", 0),
    }


@router.get("/api/notifications/unread-count")
def unread_count() -> dict:
    total = row(
        "SELECT COUNT(*) AS count FROM notifications WHERE read_at IS NULL AND dismissed_at IS NULL"
    )
    by_tab = rows(
        """
        SELECT source_tab, COUNT(*) AS count FROM notifications
        WHERE read_at IS NULL AND dismissed_at IS NULL AND source_tab IS NOT NULL
        GROUP BY source_tab
        """
    )
    return {
        "total": (total or {}).get("count", 0),
        "by_tab": {item["source_tab"]: item["count"] for item in by_tab},
    }


@router.post("/api/notifications", status_code=201)
async def create_notification(body: NotificationCreate) -> dict:
    notification_id = new_id()
    priority = body.priority or DEFAULT_PRIORITY.get(body.type, "low")
    execute(
        """
        INSERT INTO notifications
            (id, type, priority, title, body, source_agent_id, source_tab, action_url, action_label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            notification_id,
            body.type,
            priority,
            body.title,
            body.body,
            body.source_agent_id,
            body.source_tab,
            body.action_url,
            body.action_label,
        ),
    )
    notification = row("SELECT * FROM notifications WHERE id = ?", (notification_id,)) or {}
    await _publish(notification)
    return notification


def _notification_or_404(notification_id: str) -> dict:
    notification = row("SELECT * FROM notifications WHERE id = ?", (notification_id,))
    if not notification:
        raise HTTPException(status_code=404, detail="notification not found")
    return notification


@router.patch("/api/notifications/{notification_id}/read")
def mark_read(notification_id: str) -> dict:
    _notification_or_404(notification_id)
    execute(
        "UPDATE notifications SET read_at = COALESCE(read_at, datetime('now')) WHERE id = ?",
        (notification_id,),
    )
    return _notification_or_404(notification_id)


@router.patch("/api/notifications/{notification_id}/dismiss")
def dismiss(notification_id: str) -> dict:
    _notification_or_404(notification_id)
    execute(
        "UPDATE notifications SET read_at = COALESCE(read_at, datetime('now')), dismissed_at = COALESCE(dismissed_at, datetime('now')) WHERE id = ?",
        (notification_id,),
    )
    return _notification_or_404(notification_id)


@router.post("/api/notifications/mark-all-read")
def mark_all_read(body: MarkAllRead = MarkAllRead()) -> dict:
    before = unread_count()["total"]
    execute(
        "UPDATE notifications SET read_at = COALESCE(read_at, datetime('now')) WHERE read_at IS NULL AND dismissed_at IS NULL AND (? IS NULL OR source_tab = ?)",
        (body.source_tab, body.source_tab),
    )
    return {"marked_read": before - unread_count()["total"]}


async def _stream(queue: asyncio.Queue[dict]) -> AsyncIterator[str]:
    try:
        while True:
            try:
                notification = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"event: notification\ndata: {json.dumps(notification)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(queue)


@router.get("/api/notifications/stream")
async def stream() -> StreamingResponse:
    queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)
    return StreamingResponse(_stream(queue), media_type="text/event-stream")
