"""W19-4/5 — /api/files real var/ scanner + orphan reconciliation.

Supersedes the honest-blocked interim implementation with a scanner that walks
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
    ".3mf": "3mf",
    ".gcode": "gcode",
    ".png": "thumbnail",
    ".jpg": "thumbnail",
    ".svg": "thumbnail",
    ".json": "proof_report",
}

_SIBLING_SUFFIXES: tuple[tuple[str, str], ...] = (
    (".proof.json", "proof"),
    (".preview.svg", "thumbnail"),
    (".preview.png", "thumbnail"),
    (".rembg.png", "processed_reference"),
    (".runtime.json", "runtime_evidence"),
    (".runtime_evidence.json", "runtime_evidence"),
    (".manual-test.3mf", "package_3mf"),
)


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
                    evidence_type = _evidence_type_for_file(f)
                    valid, invalid_reason = _artifact_validity(f)
                    notes_payload: dict[str, Any] = {
                        "reconciled": True,
                        "run_dir": run_dir.name,
                        "output_stem": _output_stem(f),
                        "sibling_role": _sibling_role(f),
                        "valid": valid,
                    }
                    if invalid_reason:
                        notes_payload["invalid_reason"] = invalid_reason
                    notes = json.dumps(notes_payload, sort_keys=True)
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
                _backlink_run_siblings(conn, run_dir)
            conn.commit()
            inserted[bucket] = count
    finally:
        conn.close()

    return inserted


def _evidence_type_for_file(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".proof.json"):
        return "proof_report"
    if name.endswith(".rembg.png"):
        return "processed_image"
    if name.endswith(".runtime.json") or name.endswith(".runtime_evidence.json"):
        return "runtime_evidence"
    if name.endswith(".preview.svg") or name.endswith(".preview.png"):
        return "thumbnail"
    return _EXT_EVIDENCE.get(path.suffix.lower(), "other")


def _sibling_role(path: Path) -> str:
    name = path.name.lower()
    for suffix, role in _SIBLING_SUFFIXES:
        if name.endswith(suffix):
            return role
    if path.suffix.lower() in {".stl", ".obj"}:
        return "mesh"
    if path.suffix.lower() == ".3mf":
        return "package_3mf"
    if path.suffix.lower() == ".gcode":
        return "gcode"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
        return "image"
    if path.suffix.lower() in {".json", ".txt"}:
        return "report"
    return "other"


def _output_stem(path: Path) -> str:
    name = path.name
    lower = name.lower()
    for suffix, _role in _SIBLING_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _artifact_validity(path: Path) -> tuple[bool, str | None]:
    try:
        size = path.stat().st_size
    except OSError:
        return False, "stat_failed"
    if size <= 0:
        return False, "zero_byte_artifact"
    return True, None


def _parse_notes(notes_raw: Any) -> dict[str, Any]:
    if not notes_raw:
        return {}
    if isinstance(notes_raw, dict):
        return dict(notes_raw)
    if isinstance(notes_raw, str):
        try:
            parsed = json.loads(notes_raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _merge_notes(notes_raw: Any, updates: dict[str, Any]) -> str:
    notes = _parse_notes(notes_raw)
    for key, value in updates.items():
        if value in (None, ""):
            continue
        if key not in notes:
            notes[key] = value
    return json.dumps(notes, sort_keys=True)


def _row_is_valid_artifact(artifact_row: Any) -> bool:
    notes = _parse_notes(artifact_row["notes"])
    if notes.get("valid") is False:
        return False
    try:
        return int(artifact_row["file_size"] or 0) > 0
    except (TypeError, ValueError):
        return False


def _backlink_run_siblings(conn: Any, run_dir: Path) -> int:
    """Merge one-step lineage keys onto sibling artifacts in a run directory.

    The reconciler sees files on disk after the producer has already written
    them. Older rows did not carry lineage notes, so the Files/Artifacts UI
    could list every file while the lineage endpoint still showed islands.
    This groups direct children by normalized output stem and adds the same
    lineage keys used by the live generators.
    """
    files = [f for f in sorted(run_dir.iterdir()) if f.is_file()]
    if not files:
        return 0
    paths = [str(f) for f in files]
    placeholders = ",".join("?" for _ in paths)
    rows = conn.execute(
        f"SELECT * FROM artifacts WHERE file_path IN ({placeholders})",
        tuple(paths),
    ).fetchall()
    by_path = {str(row["file_path"]): row for row in rows}
    groups: dict[str, dict[str, Any]] = {}
    for f in files:
        artifact_row = by_path.get(str(f))
        if artifact_row is None:
            continue
        groups.setdefault(_output_stem(f), {})[_sibling_role(f)] = artifact_row

    updates: list[tuple[str, str]] = []
    for grouped in groups.values():
        mesh = grouped.get("mesh")
        proof = grouped.get("proof")
        thumbnail = grouped.get("thumbnail")
        processed = grouped.get("processed_reference")
        package = grouped.get("package_3mf")
        runtime = grouped.get("runtime_evidence")
        gcode = grouped.get("gcode")

        mesh_id = mesh["id"] if mesh is not None else None
        proof_id = proof["id"] if proof is not None and _row_is_valid_artifact(proof) else None
        thumbnail_id = (
            thumbnail["id"] if thumbnail is not None and _row_is_valid_artifact(thumbnail) else None
        )
        processed_id = (
            processed["id"] if processed is not None and _row_is_valid_artifact(processed) else None
        )
        package_id = (
            package["id"] if package is not None and _row_is_valid_artifact(package) else None
        )
        runtime_id = (
            runtime["id"] if runtime is not None and _row_is_valid_artifact(runtime) else None
        )
        gcode_id = gcode["id"] if gcode is not None and _row_is_valid_artifact(gcode) else None

        if mesh is not None and _row_is_valid_artifact(mesh):
            updates.append(
                (
                    _merge_notes(
                        mesh["notes"],
                        {
                            "proof_artifact_id": proof_id,
                            "thumbnail_artifact_id": thumbnail_id,
                            "processed_reference_artifact_id": processed_id,
                            "package_3mf_artifact_id": package_id,
                            "runtime_evidence_artifact_id": runtime_id,
                            "gcode_artifact_id": gcode_id,
                        },
                    ),
                    mesh["id"],
                )
            )
        for role_row in (proof, thumbnail, processed, package, runtime, gcode):
            if role_row is None or mesh_id is None:
                continue
            edge_updates = {"mesh_artifact_id": mesh_id}
            if proof_id and role_row["id"] != proof_id:
                edge_updates["proof_artifact_id"] = proof_id
            updates.append((_merge_notes(role_row["notes"], edge_updates), role_row["id"]))

    changed = 0
    for notes, artifact_id in updates:
        conn.execute("UPDATE artifacts SET notes = ? WHERE id = ?", (notes, artifact_id))
        changed += 1
    return changed


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
    usable: bool = True
    invalid_reason: str | None = None


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
                usable, invalid_reason = _artifact_validity(f)
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
                        usable=usable,
                        invalid_reason=invalid_reason,
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
