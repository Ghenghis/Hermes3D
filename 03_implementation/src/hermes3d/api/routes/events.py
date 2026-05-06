from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from hermes3d.api.routes._common import utc_now

router = APIRouter()
_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()


async def broadcast(event_type: str, payload: dict[str, Any]) -> None:
    event = {"type": event_type, "payload": payload, "ts": utc_now()}
    stale: list[asyncio.Queue[dict[str, Any]]] = []
    for queue in _subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            stale.append(queue)
    for queue in stale:
        _subscribers.discard(queue)


async def _event_generator(queue: asyncio.Queue[dict[str, Any]]) -> AsyncIterator[str]:
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        _subscribers.discard(queue)


@router.get("/api/events/stream")
async def event_stream() -> StreamingResponse:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)
    return StreamingResponse(
        _event_generator(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
