"""W19-4/5 — /api/files real var/ scanner + orphan reconciliation.

Replaces the honest-blocked stub with a scanner that walks
var/generation/, var/designs/, and var/slicer/ and returns FileItem
rows for every file found.  POST write semantics remain 501 until a
real upload path is wired.

W19-5: reconcile_var_artifacts() backfills any var/ file not yet
registered in the artifacts DB (idempotent — INSERT OR IGNORE).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# parents[0]=routes [1]=api [2]=hermes3d [3]=src [4]=03_implementation
_VAR_DIR = Path(__file__).resolve().parents[4] / "var"

_BUCKETS = ("generation", "designs", "slicer")

_EXT_KIND: dict[str, Literal["model", "slice", "image", "log", "other"]] = {
    ".stl": "model",
    ".obj": "model",
    ".3mf": "model",
    ".gcode": "slice",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".svg": "image",
    ".json": "log",
    ".txt": "log",
}


def _file_id(path: Path) -> str:
    rel = path.relative_to(_VAR_DIR)
    return hashlib.sha1(str(rel).encode()).hexdigest()[:16]


_EXT_EVIDENCE: dict[str, str] = {
    ".stl": "mesh",
    ".obj": "mesh",
    ".3mf": "mesh",
    ".gcode": "gcode",
    ".png": "thumbnail",
    ".jpg": "thumbnail",
    ".svg": "thumbnail",
    ".json": "proof_report",
}


def reconcile_var_artifacts() -> dict[str, int]:
    """Backfill any var/ file not yet in the artifacts table.

    Idempotent — uses INSERT OR IGNORE keyed on file_path.
    Returns counts of inserted rows per bucket.
    """
    from hermes3d.db.init import connect, init_db

    init_db()
    inserted: dict[str, int] = {}

    if not _VAR_DIR.exists():
        return inserted

    conn = connect()
    try:
        existing = {
            row[0]
            for row in conn.execute(
                "SELECT file_path FROM artifacts WHERE file_path LIKE ?",
                (str(_VAR_DIR) + "%",),
            ).fetchall()
        }
        for bucket in _BUCKETS:
            bucket_dir = _VAR_DIR / bucket
            if not bucket_dir.exists():
                continue
            count = 0
            for run_dir in sorted(bucket_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                job_id = _resolve_job_id(conn, run_dir.name)
                for f in sorted(run_dir.iterdir()):
                    if not f.is_file():
                        continue
                    fp = str(f)
                    if fp in existing:
                        continue
                    evidence_type = _EXT_EVIDENCE.get(f.suffix.lower(), "other")
                    notes = json.dumps({"reconciled": True, "run_dir": run_dir.name})
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO artifacts
                          (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
                        VALUES (?, ?, ?, 'reconcile', 'MODELING', 'MODEL_APPROVAL', ?, ?, ?, ?)
                        """,
                        (
                            uuid.uuid4().hex,
                            job_id,
                            evidence_type,
                            f.name,
                            fp,
                            f.stat().st_size,
                            notes,
                        ),
                    )
                    count += 1
            conn.commit()
            inserted[bucket] = count
    finally:
        conn.close()

    return inserted


def _resolve_job_id(conn: Any, run_dir_name: str) -> str | None:
    """Look up the job_id matching a run directory name, or None."""
    row = conn.execute(
        "SELECT job_id FROM artifacts WHERE job_id = ? LIMIT 1",
        (run_dir_name,),
    ).fetchone()
    return row[0] if row else None


class FileItem(BaseModel):
    id: str
    name: str
    size_bytes: int = 0
    kind: Literal["model", "slice", "image", "log", "other"] = "other"
    modified_utc: str | None = None
    bucket: str = "other"
    run_id: str | None = None


class FilesResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "unknown", "blocked"]
    reason: str | None = None
    items: list[FileItem] = Field(default_factory=list)
    total: int = 0


class FileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    kind: Literal["model", "slice", "image", "log", "other"] = "other"


def _scan_var() -> list[FileItem]:
    if not _VAR_DIR.exists():
        return []
    items: list[FileItem] = []
    for bucket in _BUCKETS:
        bucket_dir = _VAR_DIR / bucket
        if not bucket_dir.exists():
            continue
        for run_dir in sorted(bucket_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            for f in sorted(run_dir.iterdir()):
                if not f.is_file():
                    continue
                stat = f.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                items.append(
                    FileItem(
                        id=_file_id(f),
                        name=f.name,
                        size_bytes=stat.st_size,
                        kind=_EXT_KIND.get(f.suffix.lower(), "other"),
                        modified_utc=mtime,
                        bucket=bucket,
                        run_id=run_dir.name,
                    )
                )
    return items


@router.get("/api/files", response_model=FilesResponse)
def list_files() -> FilesResponse:
    items = _scan_var()
    return FilesResponse(
        accepted=True,
        status="ready",
        items=items,
        total=len(items),
    )


# Backward-compat aliases: the Files tab probes /api/files/list and
# /api/files/index; these must return 200 (not 404) so the probe shows
# "available". Declared before {file_id} so FastAPI resolves them first.
@router.get("/api/files/list", response_model=FilesResponse)
def list_files_compat() -> FilesResponse:
    return list_files()


@router.get("/api/files/index", response_model=FilesResponse)
def list_files_index() -> FilesResponse:
    return list_files()


@router.get("/api/files/{file_id}", response_model=FilesResponse)
def get_file(file_id: str) -> FilesResponse:
    if not file_id.strip():
        raise HTTPException(status_code=400, detail="file_id must not be empty")
    items = _scan_var()
    match = [i for i in items if i.id == file_id]
    if not match:
        raise HTTPException(status_code=404, detail=f"file {file_id!r} not found in var/")
    return FilesResponse(
        accepted=True,
        status="ready",
        items=match,
        total=len(match),
    )


@router.post("/api/files", status_code=501)
def create_file(body: FileCreate) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail={
            "accepted": False,
            "status": "blocked",
            "reason": "write_not_implemented",
            "echo": {"name": body.name, "kind": body.kind},
        },
    )


@router.post("/api/files/reconcile")
def reconcile_files() -> dict[str, Any]:
    """Backfill orphan var/ files into the artifacts DB.

    Safe to call multiple times — INSERT OR IGNORE keeps it idempotent.
    """
    inserted = reconcile_var_artifacts()
    total = sum(inserted.values())
    return {"inserted": total, "by_bucket": inserted}
