"""W17 — /api/files honest-blocked surface.

The Files tab (``03_implementation/ui/src/tabs/Files.tsx``) probes a
small set of candidate ``/api/files*`` paths and renders an honest
empty state when none of them answer. W17 audit (A1 + Codex) confirmed
that the bridge FastAPI app at port 8765 returns 404 for these paths,
which produces a noisy console + a permanently-degraded UI even though
the tab itself already knows how to render the "blocked" state.

This module ships the *minimum* honest surface so the Files tab can:

1. Stop seeing 404s in the console (W16-B no-allow-list contract).
2. Render the same deterministic empty state from a 200 envelope,
   keeping the UI behaviour identical until a real file store ships.
3. Discover the contract via OpenAPI once a future PR wires a real
   storage backend; the response model is the W15-A20 envelope so the
   shape is forward-compatible.

We deliberately do NOT fabricate file rows. ``items=[]`` + ``accepted=False``
+ ``reason="file_store_not_yet_configured"`` is the honest state. ``POST``
is gated identically with HTTP 501 so callers cannot accidentally rely on
write semantics that don't exist.

References:
- FastAPI bigger applications / routers pattern:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- W15-A20 honest-blocked envelope contract (see ``skills.py``,
  ``connectors.py``).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


_REASON_NOT_CONFIGURED = "file_store_not_yet_configured"


class FileItem(BaseModel):
    """Forward-compatible file row.

    Mirrors the artifact-style fields the UI already renders so the
    eventual implementation can drop in without breaking the consumer.
    """

    id: str
    name: str
    size_bytes: int = 0
    kind: Literal["model", "slice", "image", "log", "other"] = "other"
    modified_utc: str | None = None


class FilesResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "unknown", "blocked"]
    reason: str | None = None
    items: list[FileItem] = Field(default_factory=list)
    total: int = 0


class FileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    kind: Literal["model", "slice", "image", "log", "other"] = "other"


@router.get("/api/files", response_model=FilesResponse)
def list_files() -> FilesResponse:
    """Return the configured file store contents.

    No file store is wired in this build. Per the W15-A20 honest-blocked
    contract, return ``accepted=False`` + a stable ``reason`` token and
    an empty ``items`` list. The Files tab consumes this and renders the
    same deterministic empty state it currently shows for 404, without
    polluting the browser console.
    """
    return FilesResponse(
        accepted=False,
        status="unknown",
        reason=_REASON_NOT_CONFIGURED,
        items=[],
        total=0,
    )


@router.get("/api/files/{file_id}", response_model=FilesResponse)
def get_file(file_id: str) -> FilesResponse:
    """Return metadata for a single file id.

    Honest envelope: no store ⇒ no items ⇒ a deterministic 200 response
    rather than a 404. The ``reason`` token tells the UI exactly why the
    item is absent so it does not retry on a timer.
    """
    if not file_id.strip():
        raise HTTPException(status_code=400, detail="file_id must not be empty")
    return FilesResponse(
        accepted=False,
        status="unknown",
        reason=_REASON_NOT_CONFIGURED,
        items=[],
        total=0,
    )


@router.post("/api/files", status_code=501)
def create_file(body: FileCreate) -> dict[str, Any]:
    """Honest 501 Not-Implemented response for file creation.

    We accept and validate the body so OpenAPI documents the future
    contract, then return 501 Not Implemented with the W15-A20 reason
    token. This is preferable to returning 200 with a fabricated id —
    callers must not rely on writes that don't persist.
    """
    raise HTTPException(
        status_code=501,
        detail={
            "accepted": False,
            "status": "blocked",
            "reason": _REASON_NOT_CONFIGURED,
            "echo": {"name": body.name, "kind": body.kind},
        },
    )
